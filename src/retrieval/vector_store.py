"""
向量存储模块
使用 ChromaDB 存储和检索文本向量
"""

import sys
from pathlib import Path
from typing import List, Dict, Optional, Any
import chromadb
from chromadb.config import Settings

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config.settings import CHROMA_CONFIG, CHROMA_DB_DIR
from src.retrieval.embeddings import embed_query, embed_documents


class VectorStore:
    """ChromaDB 向量存储封装"""
    
    def __init__(
        self,
        collection_name: Optional[str] = None,
        persist_directory: Optional[str] = None
    ):
        self.collection_name = collection_name or CHROMA_CONFIG["collection_name"]
        self.persist_directory = persist_directory or CHROMA_CONFIG["persist_directory"]
        
        # 初始化 ChromaDB 客户端 (持久化模式)
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # 获取或创建集合
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}  # 使用余弦相似度
        )
    
    def add_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> None:
        """
        添加文档到向量存储
        
        Args:
            documents: 文档内容列表
            metadatas: 元数据列表 (可选)
            ids: 文档ID列表 (可选，不提供则自动生成)
        """
        if not documents:
            return
        
        # 生成向量
        print(f"   正在生成 {len(documents)} 个文档的向量...")
        embeddings = embed_documents(documents)
        
        # 生成 ID
        if ids is None:
            # 使用集合中已有文档数量作为起始ID
            existing_count = self.collection.count()
            ids = [f"doc_{existing_count + i}" for i in range(len(documents))]
        
        # 处理元数据 (ChromaDB 只支持基本类型)
        if metadatas:
            clean_metadatas = []
            for meta in metadatas:
                clean_meta = {}
                for k, v in meta.items():
                    if isinstance(v, (str, int, float, bool)):
                        clean_meta[k] = v
                    elif isinstance(v, list):
                        # 列表转为字符串
                        clean_meta[k] = ", ".join(str(x) for x in v)
                    else:
                        clean_meta[k] = str(v)
                clean_metadatas.append(clean_meta)
            metadatas = clean_metadatas
        
        # 添加到集合
        self.collection.add(
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        print(f"   ✓ 已添加 {len(documents)} 个文档")
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        where: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        语义搜索
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            where: 过滤条件 (可选)
            
        Returns:
            搜索结果列表，每个结果包含 document, metadata, distance
        """
        # 生成查询向量
        query_embedding = embed_query(query)
        
        # 执行搜索
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"]
        )
        
        # 格式化结果
        formatted_results = []
        if results and results["documents"]:
            for i in range(len(results["documents"][0])):
                formatted_results.append({
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else 0,
                    "id": results["ids"][0][i] if results["ids"] else None
                })
        
        return formatted_results
    
    def get_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """根据 ID 获取文档"""
        try:
            result = self.collection.get(
                ids=[doc_id],
                include=["documents", "metadatas"]
            )
            if result and result["documents"]:
                return {
                    "document": result["documents"][0],
                    "metadata": result["metadatas"][0] if result["metadatas"] else {}
                }
        except Exception:
            pass
        return None
    
    def count(self) -> int:
        """获取文档数量"""
        return self.collection.count()
    
    def clear(self) -> None:
        """清空集合"""
        # 删除并重建集合
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        print(f"   🗑️ 集合 {self.collection_name} 已清空")


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
    print("测试 VectorStore 模块...")
    store = VectorStore()
    
    print(f"当前文档数: {store.count()}")
    
    # 测试搜索
    if store.count() > 0:
        results = store.search("什么是补码", top_k=3)
        print(f"\n搜索 '什么是补码' 的结果:")
        for i, r in enumerate(results):
            print(f"\n[{i+1}] 距离: {r['distance']:.4f}")
            print(f"    章节: {r['metadata'].get('chapter', '未知')}")
            print(f"    内容: {r['document'][:100]}...")

