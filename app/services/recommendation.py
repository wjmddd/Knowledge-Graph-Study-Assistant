"""
智能推荐模块
基于知识图谱生成相关问题推荐
"""

import sys
from pathlib import Path
from typing import List, Dict, Optional

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.retrieval.graph_query import get_graph_query


def get_related_questions(concept_name: str, current_query: str = "") -> List[str]:
    """
    基于知识图谱生成推荐追问
    
    根据概念的关系类型生成不同类型的追问：
    - COMPOSED_OF → "xxx是什么？"
    - DEPENDS_ON → "为什么需要xxx？"
    - IS_A → "xxx有哪些类型？"
    - CONTRASTS_WITH → "A和B有什么区别？"
    
    Args:
        concept_name: 当前概念名称
        current_query: 当前用户问题（用于避免重复）
        
    Returns:
        推荐问题列表（最多3个）
    """
    questions = []
    
    try:
        graph = get_graph_query()
        if not graph.is_connected():
            return questions
        
        concept = graph.get_concept(concept_name)
        if not concept:
            return questions
        
        actual_name = concept.get("name", concept_name)
        relations = graph.get_relations(actual_name, direction="both")
        
        seen_targets = set()
        for rel in relations[:10]:
            target = rel.get("target")
            rel_type = rel.get("relation_type", "")
            
            if not target or target in seen_targets:
                continue
            seen_targets.add(target)
            
            # 根据关系类型生成不同问题
            if rel_type == "COMPOSED_OF":
                questions.append(f"{target}是什么？")
            elif rel_type == "DEPENDS_ON":
                questions.append(f"为什么需要{target}？")
            elif rel_type == "IS_A":
                questions.append(f"{target}有哪些类型？")
            elif rel_type == "CONTRASTS_WITH":
                questions.append(f"{actual_name}和{target}有什么区别？")
            elif rel_type in ["USES", "IMPLEMENTED_BY"]:
                questions.append(f"{target}是如何工作的？")
            
            if len(questions) >= 3:
                break
        
        # 如果问题不足，添加通用问题
        if len(questions) < 3:
            fallback = [
                f"学习{actual_name}需要什么基础？",
                f"{actual_name}的应用场景有哪些？",
                f"{actual_name}的工作原理是什么？"
            ]
            for q in fallback:
                if q not in questions and len(questions) < 3:
                    questions.append(q)
        
        return questions[:3]
        
    except Exception as e:
        print(f"生成推荐问题失败: {e}")
        return []


def extract_main_concept(query: str, tool_calls: List[Dict]) -> Optional[str]:
    """
    从查询或工具调用中提取主要概念
    
    优先从工具调用参数中提取，其次从用户查询中识别关键词
    
    Args:
        query: 用户原始问题
        tool_calls: 工具调用列表
        
    Returns:
        主要概念名称，未找到返回 None
    """
    # 1. 优先从工具调用中提取
    for tc in tool_calls:
        input_data = tc.get("input", {})
        if isinstance(input_data, dict):
            for key in ["concept_name", "concept_a", "query"]:
                if key in input_data:
                    return input_data[key]
    
    # 2. 从查询中识别关键词
    keywords = ["什么是", "是什么", "什么叫", "解释", "介绍"]
    for kw in keywords:
        if kw in query:
            idx = query.find(kw)
            concept = query[idx + len(kw):].strip().rstrip("？?。.")
            if concept:
                return concept
    
    # 3. 尝试提取查询中的主要名词（简单策略）
    # 移除常见的问句词
    stop_words = ["什么", "怎么", "如何", "为什么", "哪些", "哪个", "是", "的", "吗", "呢", "？", "?"]
    clean_query = query
    for sw in stop_words:
        clean_query = clean_query.replace(sw, " ")
    
    # 取最长的词作为概念
    words = [w.strip() for w in clean_query.split() if len(w.strip()) > 1]
    if words:
        return max(words, key=len)
    
    return None


def get_learning_suggestions(concept_name: str, depth: int = 2) -> Dict:
    """
    获取学习建议
    
    基于知识图谱的依赖关系，生成学习路径建议
    
    Args:
        concept_name: 目标概念
        depth: 依赖深度
        
    Returns:
        学习建议字典，包含前置知识和后续学习
    """
    suggestions = {
        "prerequisites": [],  # 前置知识
        "next_topics": [],    # 后续可学习内容
        "related": []         # 相关概念
    }
    
    try:
        graph = get_graph_query()
        if not graph.is_connected():
            return suggestions
        
        concept = graph.get_concept(concept_name)
        if not concept:
            return suggestions
        
        actual_name = concept.get("name", concept_name)
        relations = graph.get_relations(actual_name, direction="both")
        
        for rel in relations:
            rel_type = rel.get("relation_type", "")
            target = rel.get("target", "")
            direction = rel.get("direction", "")
            
            if not target:
                continue
            
            if rel_type == "DEPENDS_ON":
                if direction == "outgoing":
                    # 当前概念依赖的（前置知识）
                    if target not in suggestions["prerequisites"]:
                        suggestions["prerequisites"].append(target)
                else:
                    # 依赖当前概念的（后续学习）
                    if target not in suggestions["next_topics"]:
                        suggestions["next_topics"].append(target)
            elif rel_type in ["RELATED_TO", "USES", "COMPOSED_OF"]:
                if target not in suggestions["related"]:
                    suggestions["related"].append(target)
        
        # 限制数量
        suggestions["prerequisites"] = suggestions["prerequisites"][:5]
        suggestions["next_topics"] = suggestions["next_topics"][:5]
        suggestions["related"] = suggestions["related"][:5]
        
    except Exception as e:
        print(f"获取学习建议失败: {e}")
    
    return suggestions

