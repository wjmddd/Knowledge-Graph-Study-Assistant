"""
向量存储模块
使用 Neo4j 内置向量索引存储和检索文本向量
(Neo4j 5.11+ 支持)
"""

import sys
from pathlib import Path
from typing import List, Dict, Optional, Any
from neo4j import GraphDatabase

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config.settings import NEO4J_CONFIG, OPENAI_CONFIG
from src.retrieval.embeddings import embed_query, embed_documents


class VectorStore:
    """Neo4j 向量存储封装"""
    
    VECTOR_INDEX_NAME = "textchunk_embeddings"
    VECTOR_DIMENSION = 1536  # text-embedding-3-small 维度
    
    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None
    ):
        self.uri = uri or NEO4J_CONFIG["uri"]
        self.user = user or NEO4J_CONFIG["user"]
        self.password = password or NEO4J_CONFIG["password"]
        
        self.driver = None
        self._connect()
    
    def _connect(self):
        """建立连接"""
        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password)
            )
            # 验证连接
            with self.driver.session() as session:
                session.run("RETURN 1")
            print("   ✓ Neo4j 连接成功")
        except Exception as e:
            print(f"   ⚠️ Neo4j 连接失败: {e}")
            self.driver = None
    
    def close(self):
        """关闭连接"""
        if self.driver:
            self.driver.close()
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self.driver is not None
    
    def create_vector_index(self):
        """
        创建向量索引 (Neo4j 5.11+)
        """
        if not self.driver:
            print("   ❌ 未连接到 Neo4j")
            return False
        
        try:
            with self.driver.session() as session:
                # 检查索引是否已存在
                result = session.run("SHOW INDEXES")
                existing_indexes = [r["name"] for r in result]
                
                if self.VECTOR_INDEX_NAME in existing_indexes:
                    print(f"   ✓ 向量索引 '{self.VECTOR_INDEX_NAME}' 已存在")
                    return True
                
                # 创建向量索引
                session.run(f"""
                    CREATE VECTOR INDEX {self.VECTOR_INDEX_NAME} IF NOT EXISTS
                    FOR (n:TextChunk) ON (n.embedding)
                    OPTIONS {{
                        indexConfig: {{
                            `vector.dimensions`: {self.VECTOR_DIMENSION},
                            `vector.similarity_function`: 'cosine'
                        }}
                    }}
                """)
                print(f"   ✓ 向量索引 '{self.VECTOR_INDEX_NAME}' 创建成功")
                return True
                
        except Exception as e:
            print(f"   ⚠️ 创建向量索引失败: {e}")
            print("   提示: 确保 Neo4j 版本 >= 5.11")
            return False
    
    def add_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> int:
        """
        添加文档到向量存储
        将文本向量化后存储到 TextChunk 节点的 embedding 属性
        
        Args:
            documents: 文档内容列表
            metadatas: 元数据列表 (可选)
            ids: 文档ID列表 (可选)
            
        Returns:
            成功添加的文档数量
        """
        if not self.driver or not documents:
            return 0
        
        # 生成向量
        print(f"   正在生成 {len(documents)} 个文档的向量...")
        embeddings = embed_documents(documents)
        
        # 生成 ID
        if ids is None:
            ids = [f"chunk_{i}" for i in range(len(documents))]
        
        if metadatas is None:
            metadatas = [{} for _ in documents]
        
        success_count = 0
        
        with self.driver.session() as session:
            for i, (doc, emb, meta, doc_id) in enumerate(zip(documents, embeddings, metadatas, ids)):
                try:
                    # 创建或更新 TextChunk 节点，添加 embedding 属性
                    session.run("""
                        MERGE (n:TextChunk {id: $id})
                        SET n.content = $content,
                            n.embedding = $embedding,
                            n.chapter = $chapter,
                            n.section = $section
                    """, 
                        id=doc_id,
                        content=doc,
                        embedding=emb,
                        chapter=meta.get("chapter", "未知"),
                        section=meta.get("section", "未知")
                    )
                    success_count += 1
                except Exception as e:
                    print(f"   ⚠️ 添加文档 {doc_id} 失败: {e}")
        
        return success_count
    
    def search(
        self,
        query: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        语义搜索
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            
        Returns:
            搜索结果列表，每个结果包含 document, metadata, score
        """
        if not self.driver:
            return []
        
        # 生成查询向量
        query_embedding = embed_query(query)
        
        results = []
        
        try:
            with self.driver.session() as session:
                # 使用向量索引搜索
                result = session.run("""
                    CALL db.index.vector.queryNodes($index_name, $top_k, $query_vector)
                    YIELD node, score
                    RETURN node.id as id, 
                           node.content as content, 
                           node.chapter as chapter,
                           node.section as section,
                           score
                """,
                    index_name=self.VECTOR_INDEX_NAME,
                    top_k=top_k,
                    query_vector=query_embedding
                )
                
                for record in result:
                    results.append({
                        "id": record["id"],
                        "document": record["content"],
                        "metadata": {
                            "chapter": record["chapter"],
                            "section": record["section"]
                        },
                        "distance": 1 - record["score"],  # 转换为距离 (余弦相似度 -> 距离)
                        "score": record["score"]
                    })
                    
        except Exception as e:
            print(f"   ⚠️ 向量搜索失败: {e}")
            # 如果向量索引不可用，回退到文本搜索
            results = self._fallback_text_search(query, top_k)
        
        return results
    
    def _fallback_text_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """回退：使用文本包含搜索"""
        results = []
        
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (n:TextChunk)
                    WHERE n.content CONTAINS $query
                    RETURN n.id as id, n.content as content, 
                           n.chapter as chapter, n.section as section
                    LIMIT $top_k
                """, query=query, top_k=top_k)
                
                for record in result:
                    results.append({
                        "id": record["id"],
                        "document": record["content"],
                        "metadata": {
                            "chapter": record["chapter"],
                            "section": record["section"]
                        },
                        "distance": 0.5,  # 默认距离
                        "score": 0.5
                    })
        except Exception as e:
            print(f"   ⚠️ 文本搜索也失败: {e}")
        
        return results
    
    def count(self) -> int:
        """获取已向量化的文档数量"""
        if not self.driver:
            return 0
        
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (n:TextChunk)
                    WHERE n.embedding IS NOT NULL
                    RETURN count(n) as count
                """)
                record = result.single()
                return record["count"] if record else 0
        except Exception:
            return 0
    
    def clear(self) -> None:
        """清空所有 TextChunk 的 embedding"""
        if not self.driver:
            return
        
        try:
            with self.driver.session() as session:
                session.run("""
                    MATCH (n:TextChunk)
                    REMOVE n.embedding
                """)
            print("   ✓ 已清空所有向量")
        except Exception as e:
            print(f"   ⚠️ 清空失败: {e}")


# 全局单例
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """获取全局向量存储实例"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store


if __name__ == "__main__":
    # 测试
    print("测试 Neo4j VectorStore 模块...")
    store = VectorStore()
    
    if store.is_connected():
        print(f"\n当前向量化文档数: {store.count()}")
        
        # 测试搜索
        if store.count() > 0:
            results = store.search("什么是补码", top_k=3)
            print(f"\n搜索 '什么是补码' 的结果:")
            for i, r in enumerate(results):
                print(f"\n[{i+1}] 分数: {r['score']:.4f}")
                print(f"    章节: {r['metadata'].get('chapter', '未知')}")
                print(f"    内容: {r['document'][:100]}...")
        
        store.close()
    else:
        print("❌ Neo4j 连接失败")
