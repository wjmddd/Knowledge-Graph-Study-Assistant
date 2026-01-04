"""
Agent 工具定义
定义问答系统可用的各种工具函数
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.retrieval.hybrid import get_retriever, RetrievalResult
from src.retrieval.graph_query import get_graph_query


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    data: Any
    message: str = ""


class QATools:
    """问答系统工具集"""
    
    def __init__(self):
        self.retriever = get_retriever()
        self.graph = get_graph_query()
    
    # ==========================================
    # 工具 1: 获取概念定义
    # ==========================================
    
    def get_concept_definition(self, concept_name: str) -> ToolResult:
        """
        获取概念的定义和基本信息
        
        适用问题: "什么是X？", "X是什么？", "解释一下X"
        """
        if not self.graph.is_connected():
            return ToolResult(
                success=False,
                data=None,
                message="图数据库未连接"
            )
        
        concept = self.graph.get_concept(concept_name)
        
        if concept:
            # 同时获取相关来源
            sources = self.graph.get_concept_sources(concept_name)
            
            return ToolResult(
                success=True,
                data={
                    "name": concept.get("name"),
                    "definition": concept.get("definition"),
                    "alias": concept.get("alias", []),
                    "sources": [
                        {
                            "chapter": s.get("chapter"),
                            "section": s.get("section"),
                            "content": s.get("content", "")[:200]
                        }
                        for s in sources[:2]
                    ]
                },
                message=f"找到概念 '{concept_name}' 的定义"
            )
        
        # 尝试模糊搜索
        similar = self.graph.search_concepts(concept_name, limit=3)
        if similar:
            return ToolResult(
                success=False,
                data={"similar_concepts": [c["name"] for c in similar]},
                message=f"未找到 '{concept_name}'，但找到相似概念"
            )
        
        return ToolResult(
            success=False,
            data=None,
            message=f"未找到概念 '{concept_name}'"
        )
    
    # ==========================================
    # 工具 2: 获取概念组成
    # ==========================================
    
    def get_concept_composition(self, concept_name: str) -> ToolResult:
        """
        获取概念的组成部分
        
        适用问题: "X由什么组成？", "X包含哪些部分？", "X的结构是什么？"
        """
        if not self.graph.is_connected():
            return ToolResult(success=False, data=None, message="图数据库未连接")
        
        # 查询 COMPOSED_OF 关系
        relations = self.graph.get_composed_of(concept_name)
        
        if relations:
            components = []
            for rel in relations:
                components.append({
                    "name": rel["target"],
                    "definition": rel.get("target_definition", "")
                })
            
            return ToolResult(
                success=True,
                data={
                    "concept": concept_name,
                    "components": components
                },
                message=f"'{concept_name}' 包含 {len(components)} 个组成部分"
            )
        
        # 也尝试 CONTAINS 关系
        contains = self.graph.get_relations(concept_name, "CONTAINS", "out")
        if contains:
            return ToolResult(
                success=True,
                data={
                    "concept": concept_name,
                    "components": [{"name": r["target"], "definition": r.get("target_definition", "")} for r in contains]
                },
                message=f"'{concept_name}' 包含 {len(contains)} 个子项"
            )
        
        return ToolResult(
            success=False,
            data=None,
            message=f"未找到 '{concept_name}' 的组成信息"
        )
    
    # ==========================================
    # 工具 3: 获取学习路径
    # ==========================================
    
    def get_learning_path(self, concept_name: str) -> ToolResult:
        """
        获取学习某概念的前置知识路径
        
        适用问题: "学X需要什么基础？", "X的前置知识是什么？", "学X之前要学什么？"
        """
        if not self.graph.is_connected():
            return ToolResult(success=False, data=None, message="图数据库未连接")
        
        paths = self.graph.find_learning_path(concept_name, max_depth=5)
        
        if paths:
            # 取最完整的路径
            best_path = max(paths, key=len)
            
            return ToolResult(
                success=True,
                data={
                    "target": concept_name,
                    "learning_path": best_path,
                    "all_paths": paths[:3]  # 最多返回3条路径
                },
                message=f"找到学习 '{concept_name}' 的 {len(paths)} 条路径"
            )
        
        # 直接依赖
        depends = self.graph.get_depends_on(concept_name)
        if depends:
            return ToolResult(
                success=True,
                data={
                    "target": concept_name,
                    "learning_path": [concept_name] + [d["target"] for d in depends],
                    "direct_dependencies": [d["target"] for d in depends]
                },
                message=f"'{concept_name}' 直接依赖 {len(depends)} 个概念"
            )
        
        return ToolResult(
            success=False,
            data=None,
            message=f"未找到 '{concept_name}' 的学习路径"
        )
    
    # ==========================================
    # 工具 4: 对比概念
    # ==========================================
    
    def compare_concepts(self, concept_a: str, concept_b: str) -> ToolResult:
        """
        对比两个概念的异同
        
        适用问题: "X和Y有什么区别？", "X与Y的不同？", "比较X和Y"
        """
        if not self.graph.is_connected():
            return ToolResult(success=False, data=None, message="图数据库未连接")
        
        comparison = self.graph.compare_concepts(concept_a, concept_b)
        
        info_a = comparison.get("concept_a")
        info_b = comparison.get("concept_b")
        
        if info_a or info_b:
            return ToolResult(
                success=True,
                data={
                    "concept_a": {
                        "name": info_a.get("name") if info_a else concept_a,
                        "definition": info_a.get("definition") if info_a else None
                    },
                    "concept_b": {
                        "name": info_b.get("name") if info_b else concept_b,
                        "definition": info_b.get("definition") if info_b else None
                    },
                    "direct_relation": comparison.get("direct_relation"),
                    "common_parent": comparison.get("common_parent")
                },
                message=f"对比 '{concept_a}' 和 '{concept_b}'"
            )
        
        return ToolResult(
            success=False,
            data=None,
            message=f"未找到 '{concept_a}' 或 '{concept_b}' 的信息"
        )
    
    # ==========================================
    # 工具 5: 语义搜索
    # ==========================================
    
    def semantic_search(self, query: str, top_k: int = 5) -> ToolResult:
        """
        语义搜索相关内容
        
        适用问题: 通用问题、需要详细解释的问题
        """
        results = self.retriever.search_text(query)
        
        if results:
            return ToolResult(
                success=True,
                data={
                    "query": query,
                    "results": [
                        {
                            "content": r.content,
                            "chapter": r.metadata.get("chapter", "未知"),
                            "section": r.metadata.get("section", "未知"),
                            "score": r.score
                        }
                        for r in results[:top_k]
                    ]
                },
                message=f"找到 {len(results)} 个相关结果"
            )
        
        return ToolResult(
            success=False,
            data=None,
            message="未找到相关内容"
        )
    
    # ==========================================
    # 工具 6: 混合检索
    # ==========================================
    
    def hybrid_search(
        self,
        query: str,
        entities: Optional[List[str]] = None
    ) -> ToolResult:
        """
        混合检索（向量+图谱）
        
        适用问题: 复杂问题、需要多来源信息
        """
        results = self.retriever.retrieve(
            query=query,
            entities=entities,
            strategy="hybrid"
        )
        
        if results:
            # 按来源分组
            vector_results = [r for r in results if r.source == "vector"]
            graph_results = [r for r in results if r.source == "graph"]
            
            return ToolResult(
                success=True,
                data={
                    "query": query,
                    "entities": entities,
                    "vector_results": [
                        {
                            "content": r.content,
                            "chapter": r.metadata.get("chapter"),
                            "section": r.metadata.get("section"),
                            "score": r.score
                        }
                        for r in vector_results[:3]
                    ],
                    "graph_results": [
                        {
                            "content": r.content,
                            "type": r.metadata.get("type"),
                            "score": r.score
                        }
                        for r in graph_results[:5]
                    ]
                },
                message=f"检索到 {len(vector_results)} 个文本结果, {len(graph_results)} 个图谱结果"
            )
        
        return ToolResult(
            success=False,
            data=None,
            message="未找到相关内容"
        )
    
    # ==========================================
    # 工具 7: 查找概念关系
    # ==========================================
    
    def find_path_between(self, concept_a: str, concept_b: str) -> ToolResult:
        """
        查找两个概念之间的关系路径
        
        适用问题: "X和Y有什么关系？", "X怎么和Y联系的？"
        """
        if not self.graph.is_connected():
            return ToolResult(success=False, data=None, message="图数据库未连接")
        
        path = self.graph.find_path_between(concept_a, concept_b)
        
        if path:
            return ToolResult(
                success=True,
                data={
                    "from": concept_a,
                    "to": concept_b,
                    "path": [
                        {"from": p[0], "relation": p[1], "to": p[2]}
                        for p in path
                    ]
                },
                message=f"找到 '{concept_a}' 到 '{concept_b}' 的路径"
            )
        
        return ToolResult(
            success=False,
            data=None,
            message=f"未找到 '{concept_a}' 和 '{concept_b}' 之间的路径"
        )


# 工具描述（用于 Agent 选择工具）
TOOL_DESCRIPTIONS = {
    "get_concept_definition": {
        "name": "获取概念定义",
        "description": "获取某个概念的定义、别名和来源，用于回答'什么是X'类问题",
        "keywords": ["什么是", "是什么", "解释", "定义", "含义"]
    },
    "get_concept_composition": {
        "name": "获取概念组成",
        "description": "查询概念的组成部分或包含关系，用于回答'X由什么组成'类问题",
        "keywords": ["组成", "包含", "构成", "结构", "部分", "组件"]
    },
    "get_learning_path": {
        "name": "获取学习路径",
        "description": "查询学习某概念的前置知识，用于回答'学X需要什么基础'类问题",
        "keywords": ["前置", "基础", "先学", "依赖", "路径", "顺序"]
    },
    "compare_concepts": {
        "name": "对比概念",
        "description": "对比两个概念的异同，用于回答'X和Y有什么区别'类问题",
        "keywords": ["区别", "不同", "对比", "比较", "差异", "异同"]
    },
    "semantic_search": {
        "name": "语义搜索",
        "description": "在教材内容中进行语义搜索，用于通用问题",
        "keywords": []  # 作为兜底工具
    },
    "hybrid_search": {
        "name": "混合检索",
        "description": "结合向量和图谱的混合检索，用于复杂问题",
        "keywords": ["详细", "具体", "深入"]
    },
    "find_path_between": {
        "name": "查找关系路径",
        "description": "查找两个概念之间的关系，用于回答'X和Y什么关系'类问题",
        "keywords": ["关系", "联系", "关联", "相关"]
    }
}


# 全局单例
_tools: Optional[QATools] = None


def get_tools() -> QATools:
    """获取全局工具实例"""
    global _tools
    if _tools is None:
        _tools = QATools()
    return _tools


if __name__ == "__main__":
    # 测试
    print("测试 QATools 模块...")
    tools = QATools()
    
    # 测试概念定义
    print("\n1. 测试获取概念定义:")
    result = tools.get_concept_definition("CPU")
    print(f"   成功: {result.success}")
    print(f"   消息: {result.message}")
    if result.data:
        print(f"   数据: {result.data.get('name')}: {str(result.data.get('definition', ''))[:100]}...")
    
    # 测试组成
    print("\n2. 测试获取组成:")
    result = tools.get_concept_composition("CPU")
    print(f"   成功: {result.success}")
    print(f"   消息: {result.message}")

