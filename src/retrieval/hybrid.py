"""
混合检索模块
结合向量检索和图谱查询，提供融合的检索结果
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config.settings import QA_CONFIG
from src.retrieval.vector_store import get_vector_store
from src.retrieval.graph_query import get_graph_query


@dataclass
class RetrievalResult:
    """检索结果"""
    content: str  # 内容
    source: str  # 来源类型: "vector" 或 "graph"
    score: float  # 相关度分数 (0-1, 越高越相关)
    metadata: Dict[str, Any]  # 元数据


class HybridRetriever:
    """混合检索器"""
    
    def __init__(self):
        self.vector_store = get_vector_store()
        self.graph_query = get_graph_query()
        self.config = QA_CONFIG
    
    def retrieve(
        self,
        query: str,
        entities: Optional[List[str]] = None,
        strategy: str = "hybrid"
    ) -> List[RetrievalResult]:
        """
        执行混合检索
        
        Args:
            query: 查询文本
            entities: 从问题中提取的实体 (可选)
            strategy: 检索策略 ("vector", "graph", "hybrid")
            
        Returns:
            检索结果列表
        """
        results = []
        
        # 1. 向量检索
        if strategy in ["vector", "hybrid"]:
            vector_results = self._vector_search(query)
            results.extend(vector_results)
        
        # 2. 图谱检索
        if strategy in ["graph", "hybrid"] and entities:
            graph_results = self._graph_search(entities)
            results.extend(graph_results)
        
        # 3. 融合排序
        results = self._merge_and_rank(results)
        
        return results
    
    def _vector_search(self, query: str) -> List[RetrievalResult]:
        """向量语义检索"""
        results = []
        
        try:
            search_results = self.vector_store.search(
                query=query,
                top_k=self.config["max_context_chunks"]
            )
            
            for r in search_results:
                # 将距离转换为相似度分数 (ChromaDB 使用余弦距离)
                # 距离越小越相似，转换为 0-1 的分数
                score = 1 - min(r["distance"], 1.0)
                
                results.append(RetrievalResult(
                    content=r["document"],
                    source="vector",
                    score=score,
                    metadata={
                        "chapter": r["metadata"].get("chapter", "未知"),
                        "section": r["metadata"].get("section", "未知"),
                        "chunk_id": r["id"]
                    }
                ))
        except Exception as e:
            print(f"⚠️ 向量检索失败: {e}")
        
        return results
    
    def _graph_search(self, entities: List[str]) -> List[RetrievalResult]:
        """图谱结构检索"""
        results = []
        
        if not self.graph_query.is_connected():
            return results
        
        for entity in entities:
            # 1. 查询概念定义
            concept = self.graph_query.get_concept(entity)
            if concept and concept.get("definition"):
                results.append(RetrievalResult(
                    content=f"**{concept['name']}**: {concept['definition']}",
                    source="graph",
                    score=0.95,  # 精确匹配给高分
                    metadata={
                        "type": "concept_definition",
                        "concept_name": concept["name"],
                        "alias": concept.get("alias", [])
                    }
                ))
            
            # 2. 查询相关关系
            relations = self.graph_query.get_relations(entity, direction="both")
            if relations:
                # 按关系类型分组
                by_type = {}
                for rel in relations[:self.config["max_graph_results"]]:
                    rel_type = rel["relation_type"]
                    if rel_type not in by_type:
                        by_type[rel_type] = []
                    by_type[rel_type].append(rel["target"])
                
                # 构建关系描述
                for rel_type, targets in by_type.items():
                    rel_desc = self._format_relation(entity, rel_type, targets)
                    if rel_desc:
                        results.append(RetrievalResult(
                            content=rel_desc,
                            source="graph",
                            score=0.85,
                            metadata={
                                "type": "relation",
                                "concept_name": entity,
                                "relation_type": rel_type
                            }
                        ))
            
            # 3. 查询文本来源
            sources = self.graph_query.get_concept_sources(entity)
            for src in sources[:2]:  # 最多取2个
                if src.get("content"):
                    results.append(RetrievalResult(
                        content=src["content"],
                        source="graph",
                        score=0.8,
                        metadata={
                            "type": "source",
                            "chapter": src.get("chapter", "未知"),
                            "section": src.get("section", "未知")
                        }
                    ))
        
        return results
    
    def _format_relation(
        self,
        entity: str,
        rel_type: str,
        targets: List[str]
    ) -> Optional[str]:
        """格式化关系描述"""
        rel_templates = {
            "COMPOSED_OF": f"**{entity}** 由以下部分组成：{', '.join(targets)}",
            "DEPENDS_ON": f"学习 **{entity}** 需要先掌握：{', '.join(targets)}",
            "IS_A": f"**{entity}** 是一种 {', '.join(targets)}",
            "CONTAINS": f"**{entity}** 包含：{', '.join(targets)}",
            "IMPLEMENTED_BY": f"**{entity}** 通过 {', '.join(targets)} 实现",
            "EXAMPLE_OF": f"**{entity}** 是 {', '.join(targets)} 的例子",
            "CONTRASTS_WITH": f"**{entity}** 与 {', '.join(targets)} 形成对比",
            "RELATED_TO": f"**{entity}** 与 {', '.join(targets)} 相关"
        }
        
        return rel_templates.get(rel_type, None)
    
    def _merge_and_rank(
        self,
        results: List[RetrievalResult]
    ) -> List[RetrievalResult]:
        """融合排序"""
        if not results:
            return []
        
        # 去重 (基于内容相似)
        seen_contents = set()
        unique_results = []
        for r in results:
            # 简单的内容指纹
            content_key = r.content[:100].strip().lower()
            if content_key not in seen_contents:
                seen_contents.add(content_key)
                unique_results.append(r)
        
        # 按分数排序
        unique_results.sort(key=lambda x: x.score, reverse=True)
        
        # 限制数量
        max_results = self.config["max_context_chunks"] + self.config["max_graph_results"]
        return unique_results[:max_results]
    
    # ==========================================
    # 便捷方法
    # ==========================================
    
    def search_concept(self, concept_name: str) -> List[RetrievalResult]:
        """搜索特定概念"""
        return self.retrieve(
            query=concept_name,
            entities=[concept_name],
            strategy="graph"
        )
    
    def search_text(self, query: str) -> List[RetrievalResult]:
        """纯文本语义搜索"""
        return self.retrieve(
            query=query,
            strategy="vector"
        )
    
    def get_learning_path(self, concept_name: str) -> List[str]:
        """获取学习路径"""
        if not self.graph_query.is_connected():
            return []
        
        paths = self.graph_query.find_learning_path(concept_name)
        if paths:
            # 返回最长的路径
            return max(paths, key=len)
        return []
    
    def compare(self, concept_a: str, concept_b: str) -> Dict[str, Any]:
        """对比两个概念"""
        if not self.graph_query.is_connected():
            return {}
        
        return self.graph_query.compare_concepts(concept_a, concept_b)


# 全局单例
_retriever: Optional[HybridRetriever] = None


def get_retriever() -> HybridRetriever:
    """获取全局检索器实例"""
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever()
    return _retriever


if __name__ == "__main__":
    # 测试
    print("测试 HybridRetriever 模块...")
    retriever = HybridRetriever()
    
    # 测试混合检索
    query = "什么是补码"
    print(f"\n🔍 测试查询: '{query}'")
    
    results = retriever.retrieve(query, entities=["补码"])
    print(f"   检索到 {len(results)} 个结果:")
    
    for i, r in enumerate(results[:5]):
        print(f"\n   [{i+1}] 来源: {r.source}, 分数: {r.score:.2f}")
        print(f"       内容: {r.content[:100]}...")

