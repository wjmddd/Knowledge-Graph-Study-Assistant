"""
LangChain 工具定义
将现有的工具转换为 LangChain Tool 格式
"""

import sys
from pathlib import Path
from typing import Optional, List

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from src.retrieval.hybrid import get_retriever
from src.retrieval.graph_query import get_graph_query


# ==========================================
# 工具输入 Schema
# ==========================================

class ConceptInput(BaseModel):
    """概念查询输入"""
    concept_name: str = Field(description="要查询的概念名称，如：CPU、缓存、补码")


class TwoConceptInput(BaseModel):
    """双概念查询输入"""
    concept_a: str = Field(description="第一个概念名称")
    concept_b: str = Field(description="第二个概念名称")


class SearchInput(BaseModel):
    """搜索查询输入"""
    query: str = Field(description="搜索查询文本")
    entities: Optional[List[str]] = Field(default=None, description="可选的实体列表，用于图谱过滤")


# ==========================================
# LangChain Tools
# ==========================================

@tool(args_schema=ConceptInput)
def get_concept_definition(concept_name: str) -> str:
    """
    获取概念的定义和基本信息。
    适用于回答"什么是X？"、"X是什么？"、"解释一下X"类问题。
    
    Args:
        concept_name: 要查询的概念名称
        
    Returns:
        概念的定义信息，包含别名和来源
    """
    graph = get_graph_query()
    
    if not graph.is_connected():
        return "❌ 图数据库未连接，无法查询概念定义"
    
    concept = graph.get_concept(concept_name)
    
    if concept:
        result_parts = []
        actual_name = concept.get('name', concept_name)
        result_parts.append(f"**{actual_name}**")
        
        if concept.get("definition"):
            result_parts.append(f"\n定义：{concept['definition']}")
        
        if concept.get("alias"):
            aliases = concept["alias"]
            if isinstance(aliases, list):
                result_parts.append(f"\n别名：{', '.join(aliases)}")
            else:
                result_parts.append(f"\n别名：{aliases}")
        
        # 获取来源（使用实际找到的概念名称）
        sources = graph.get_concept_sources(actual_name)
        if sources:
            result_parts.append("\n\n📚 来源章节:")
            for src in sources[:3]:
                chapter = src.get("chapter") or "未知章节"
                section = src.get("section") or "未知节"
                content_preview = (src.get("content") or "")[:150]
                result_parts.append(f"\n- **{chapter}/{section}**: {content_preview}...")
        else:
            # 没有找到来源时，尝试显示节点的其他信息
            if concept.get("label"):
                result_parts.append(f"\n\n📌 节点类型: {concept['label']}")
        
        return "".join(result_parts)
    
    # 尝试模糊搜索
    similar = graph.search_concepts(concept_name, limit=3)
    if similar:
        similar_names = [c["name"] for c in similar]
        return f"未找到'{concept_name}'的精确定义，但找到相似概念：{', '.join(similar_names)}。你可以尝试查询这些概念。"
    
    return f"未找到概念'{concept_name}'的相关信息"


@tool(args_schema=ConceptInput)
def get_concept_composition(concept_name: str) -> str:
    """
    获取概念的组成部分或结构。
    适用于回答"X由什么组成？"、"X包含哪些部分？"、"X的结构是什么？"类问题。
    
    Args:
        concept_name: 要查询的概念名称
        
    Returns:
        概念的组成信息
    """
    graph = get_graph_query()
    
    if not graph.is_connected():
        return "❌ 图数据库未连接"
    
    result_parts = []
    found_relations = False
    
    # 先获取概念本身的信息
    concept = graph.get_concept(concept_name)
    actual_name = concept.get("name", concept_name) if concept else concept_name
    
    # 查询 COMPOSED_OF 关系
    relations = graph.get_composed_of(actual_name)
    
    if relations:
        found_relations = True
        result_parts.append(f"**{actual_name}** 的组成部分：\n")
        for rel in relations:
            target = rel["target"]
            definition = rel.get("target_definition", "")
            if definition:
                result_parts.append(f"- **{target}**: {definition}")
            else:
                result_parts.append(f"- {target}")
    
    # 尝试 CONTAINS 关系
    if not found_relations:
        contains = graph.get_relations(actual_name, "CONTAINS", "out")
        if contains:
            found_relations = True
            result_parts.append(f"**{actual_name}** 包含的子项：\n")
            for rel in contains:
                result_parts.append(f"- {rel['target']}")
    
    # 添加来源信息
    if found_relations:
        sources = graph.get_concept_sources(actual_name)
        if sources:
            result_parts.append("\n\n📚 来源章节:")
            for src in sources[:3]:
                chapter = src.get("chapter") or "未知章节"
                section = src.get("section") or "未知节"
                content_preview = (src.get("content") or "")[:100]
                result_parts.append(f"\n- **{chapter}/{section}**: {content_preview}...")
        return "\n".join(result_parts)
    
    return f"未找到'{concept_name}'的组成信息"


@tool(args_schema=ConceptInput)
def get_learning_path(concept_name: str) -> str:
    """
    获取学习某概念的前置知识路径。
    适用于回答"学X需要什么基础？"、"X的前置知识是什么？"类问题。
    
    Args:
        concept_name: 要学习的目标概念
        
    Returns:
        学习路径建议
    """
    graph = get_graph_query()
    
    if not graph.is_connected():
        return "❌ 图数据库未连接"
    
    # 先获取概念本身
    concept = graph.get_concept(concept_name)
    actual_name = concept.get("name", concept_name) if concept else concept_name
    
    result_parts = []
    
    paths = graph.find_learning_path(actual_name, max_depth=5)
    
    if paths:
        # 取最完整的路径
        best_path = max(paths, key=len)
        path_str = " → ".join(best_path)
        
        result_parts.append(f"学习 **{actual_name}** 的建议路径：\n\n{path_str}\n\n")
        result_parts.append(f"（共找到 {len(paths)} 条学习路径，这是最完整的一条）")
    else:
        # 查找直接依赖
        depends = graph.get_depends_on(actual_name)
        if depends:
            deps = [d["target"] for d in depends]
            result_parts.append(f"学习 **{actual_name}** 需要先了解：{', '.join(deps)}")
        else:
            return f"未找到'{concept_name}'的前置知识依赖，可能这是一个基础概念"
    
    # 添加来源信息
    sources = graph.get_concept_sources(actual_name)
    if sources:
        result_parts.append("\n\n📚 来源章节:")
        for src in sources[:2]:
            chapter = src.get("chapter") or "未知章节"
            section = src.get("section") or "未知节"
            result_parts.append(f"\n- **{chapter}/{section}**")
    
    return "".join(result_parts)


@tool(args_schema=TwoConceptInput)
def compare_concepts(concept_a: str, concept_b: str) -> str:
    """
    对比两个概念的异同。
    适用于回答"X和Y有什么区别？"、"比较X和Y"类问题。
    
    Args:
        concept_a: 第一个概念
        concept_b: 第二个概念
        
    Returns:
        两个概念的对比信息
    """
    graph = get_graph_query()
    
    if not graph.is_connected():
        return "❌ 图数据库未连接"
    
    comparison = graph.compare_concepts(concept_a, concept_b)
    
    info_a = comparison.get("concept_a")
    info_b = comparison.get("concept_b")
    
    result_parts = []
    actual_names = []
    
    if info_a:
        actual_name_a = info_a.get('name', concept_a)
        actual_names.append(actual_name_a)
        result_parts.append(f"### {actual_name_a}")
        if info_a.get("definition"):
            result_parts.append(f"{info_a['definition']}")
    else:
        result_parts.append(f"### {concept_a}\n未找到定义")
    
    result_parts.append("")
    
    if info_b:
        actual_name_b = info_b.get('name', concept_b)
        actual_names.append(actual_name_b)
        result_parts.append(f"### {actual_name_b}")
        if info_b.get("definition"):
            result_parts.append(f"{info_b['definition']}")
    else:
        result_parts.append(f"### {concept_b}\n未找到定义")
    
    # 直接关系
    if comparison.get("direct_relation"):
        rel = comparison["direct_relation"]
        result_parts.append(f"\n**直接关系**: {concept_a} --[{rel.get('type')}]--> {concept_b}")
    
    # 共同上级
    if comparison.get("common_parent"):
        result_parts.append(f"\n**共同上级类别**: {comparison['common_parent']}")
    
    # 添加来源信息
    all_sources = []
    for name in actual_names:
        sources = graph.get_concept_sources(name)
        for src in sources[:2]:
            if src not in all_sources:
                all_sources.append(src)
    
    if all_sources:
        result_parts.append("\n\n📚 来源章节:")
        for src in all_sources[:4]:
            chapter = src.get("chapter") or "未知章节"
            section = src.get("section") or "未知节"
            result_parts.append(f"\n- **{chapter}/{section}**")
    
    return "\n".join(result_parts)


@tool(args_schema=TwoConceptInput)
def find_concept_relation(concept_a: str, concept_b: str) -> str:
    """
    查找两个概念之间的关系路径。
    适用于回答"X和Y有什么关系？"、"X怎么和Y联系的？"类问题。
    
    Args:
        concept_a: 起始概念
        concept_b: 目标概念
        
    Returns:
        两个概念间的关系路径
    """
    graph = get_graph_query()
    
    if not graph.is_connected():
        return "❌ 图数据库未连接"
    
    # 获取实际概念名称
    info_a = graph.get_concept(concept_a)
    info_b = graph.get_concept(concept_b)
    actual_a = info_a.get("name", concept_a) if info_a else concept_a
    actual_b = info_b.get("name", concept_b) if info_b else concept_b
    
    path = graph.find_path_between(actual_a, actual_b)
    
    if path:
        result_parts = []
        path_desc = []
        for p in path:
            path_desc.append(f"{p[0]} --[{p[1]}]--> {p[2]}")
        result_parts.append(f"**{actual_a}** 到 **{actual_b}** 的关系路径：\n\n" + "\n".join(path_desc))
        
        # 添加来源信息
        all_sources = []
        for name in [actual_a, actual_b]:
            sources = graph.get_concept_sources(name)
            for src in sources[:2]:
                if src not in all_sources:
                    all_sources.append(src)
        
        if all_sources:
            result_parts.append("\n\n📚 来源章节:")
            for src in all_sources[:4]:
                chapter = src.get("chapter") or "未知章节"
                section = src.get("section") or "未知节"
                result_parts.append(f"\n- **{chapter}/{section}**")
        
        return "\n".join(result_parts)
    
    return f"未找到'{concept_a}'和'{concept_b}'之间的直接关系路径"


@tool(args_schema=SearchInput)
def semantic_search(query: str, entities: Optional[List[str]] = None) -> str:
    """
    在知识库中进行语义搜索。
    适用于通用问题、需要详细解释的问题。当其他工具找不到答案时使用此工具。
    
    Args:
        query: 搜索查询
        entities: 可选的实体列表
        
    Returns:
        相关的文本内容
    """
    retriever = get_retriever()
    
    results = retriever.search_text(query)
    
    if results:
        result_parts = [f"找到 {len(results)} 个相关结果：\n"]
        for i, r in enumerate(results[:5], 1):
            chapter = r.metadata.get("chapter", "未知")
            section = r.metadata.get("section", "未知")
            content = r.content[:300]
            result_parts.append(f"\n**[{i}] {chapter}/{section}**\n{content}...")
        return "\n".join(result_parts)
    
    return "未找到与查询相关的内容"


@tool(args_schema=SearchInput)
def hybrid_search(query: str, entities: Optional[List[str]] = None) -> str:
    """
    结合向量搜索和图谱查询的混合检索。
    适用于复杂问题、需要多来源信息的问题。
    
    Args:
        query: 搜索查询
        entities: 可选的实体列表，用于图谱检索
        
    Returns:
        混合检索结果
    """
    retriever = get_retriever()
    
    results = retriever.retrieve(
        query=query,
        entities=entities,
        strategy="hybrid"
    )
    
    if results:
        # 按来源分组
        vector_results = [r for r in results if r.source == "vector"]
        graph_results = [r for r in results if r.source == "graph"]
        
        result_parts = []
        
        if graph_results:
            result_parts.append("### 📊 知识图谱结果：\n")
            for r in graph_results[:3]:
                result_parts.append(f"- {r.content}")
        
        if vector_results:
            result_parts.append("\n### 📚 文档检索结果：\n")
            for r in vector_results[:3]:
                chapter = r.metadata.get("chapter", "未知")
                section = r.metadata.get("section", "未知")
                result_parts.append(f"**[{chapter}/{section}]**\n{r.content[:200]}...")
        
        return "\n".join(result_parts)
    
    return "未找到相关内容"


# ==========================================
# 获取所有工具
# ==========================================

def get_langchain_tools():
    """获取所有 LangChain 工具"""
    return [
        get_concept_definition,
        get_concept_composition,
        get_learning_path,
        compare_concepts,
        find_concept_relation,
        semantic_search,
        hybrid_search
    ]


# 工具名称到描述的映射 (用于 Agent 选择)
TOOL_DESCRIPTIONS = {
    "get_concept_definition": "获取概念定义，用于'什么是X'类问题",
    "get_concept_composition": "获取概念组成，用于'X由什么组成'类问题",
    "get_learning_path": "获取学习路径，用于'学X需要什么基础'类问题",
    "compare_concepts": "对比两个概念，用于'X和Y有什么区别'类问题",
    "find_concept_relation": "查找概念关系，用于'X和Y什么关系'类问题",
    "semantic_search": "语义搜索，用于通用问题",
    "hybrid_search": "混合检索，用于复杂问题"
}


if __name__ == "__main__":
    # 测试
    print("测试 LangChain Tools...")
    
    # 测试概念定义
    print("\n1. 测试 get_concept_definition:")
    result = get_concept_definition.invoke({"concept_name": "CPU"})
    print(result[:200] if len(result) > 200 else result)
    
    # 测试语义搜索
    print("\n2. 测试 semantic_search:")
    result = semantic_search.invoke({"query": "什么是补码"})
    print(result[:200] if len(result) > 200 else result)

