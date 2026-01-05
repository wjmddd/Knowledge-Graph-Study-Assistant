"""
图谱查询与可视化服务模块
封装知识图谱相关的查询和可视化功能
"""

import sys
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.retrieval.graph_query import get_graph_query
from src.visualization.graph_viz import get_visualizer


# ==========================================
# 配置
# ==========================================
GRAPH_VIZ_DIR = Path("public/graphs")
GRAPH_VIZ_DIR.mkdir(parents=True, exist_ok=True)


# ==========================================
# 图谱统计
# ==========================================

def get_graph_stats() -> Dict:
    """
    获取知识图谱统计信息
    
    Returns:
        包含节点和关系统计的字典，出错时包含 error 键
    """
    try:
        graph = get_graph_query()
        if not graph.is_connected():
            return {"error": "Neo4j 未连接"}
        
        return graph.get_stats()
    except Exception as e:
        return {"error": str(e)}


# ==========================================
# 概念查询
# ==========================================

def query_concept_detail(concept_name: str) -> str:
    """
    查询概念详情（支持模糊匹配）
    
    使用 get_term_variants 进行中英文、别名的智能匹配
    
    Args:
        concept_name: 概念名称
        
    Returns:
        格式化的概念详情字符串
    """
    try:
        graph = get_graph_query()
        if not graph.is_connected():
            return "❌ Neo4j 数据库未连接"
        
        # 导入术语变体函数（用于显示匹配信息）
        from config.settings import get_term_variants, normalize_term
        
        # 标准化输入
        normalized_input = normalize_term(concept_name)
        variants = get_term_variants(concept_name)
        
        # get_concept 内部已使用 get_term_variants 进行模糊匹配
        concept = graph.get_concept(concept_name)
        
        if not concept:
            # 尝试更广泛的搜索
            similar = graph.search_concepts(concept_name, limit=5)
            if similar:
                names = [c["name"] for c in similar]
                search_hint = f"\n\n💡 尝试的匹配变体: {', '.join(variants[:5])}" if len(variants) > 1 else ""
                return f"未找到 **{concept_name}**，你是否想查询：\n" + "\n".join(f"- `/graph {n}`" for n in names) + search_hint
            return f"未找到与 **{concept_name}** 相关的概念\n\n💡 提示：可以尝试使用 `/stats` 查看所有概念类型"
        
        result = []
        actual_name = concept.get('name')
        
        # 如果匹配到的概念名与输入不同，显示匹配信息
        if actual_name.lower() != concept_name.lower():
            result.append(f"🔍 `{concept_name}` → 匹配到 **{actual_name}**\n")
        
        result.append(f"## 📖 {actual_name}")
        result.append(f"**类型**: {concept.get('label', '未知')}")
        
        if concept.get("definition"):
            result.append(f"\n**定义**: {concept['definition']}")
        
        if concept.get("alias"):
            aliases = concept["alias"]
            if isinstance(aliases, list) and aliases:
                result.append(f"\n**别名**: {', '.join(aliases)}")
        
        # 使用实际找到的概念名获取关系（而非用户输入）
        relations = graph.get_relations(actual_name, direction="both")
        if relations:
            result.append(f"\n### 🔗 相关关系 ({len(relations)}条)")
            
            # 按类型分组
            by_type = {}
            for rel in relations[:20]:  # 增加显示数量
                rt = rel.get("relation_type", "OTHER")
                if rt not in by_type:
                    by_type[rt] = []
                by_type[rt].append(rel.get("target"))
            
            for rt, targets in by_type.items():
                unique_targets = list(dict.fromkeys(targets))  # 去重保序
                result.append(f"- **{rt}**: {', '.join(unique_targets[:5])}" + (f" (+{len(unique_targets)-5})" if len(unique_targets) > 5 else ""))
        
        # 图谱文本可视化（使用实际名称）
        graph_text = generate_concept_graph_text(actual_name)
        if graph_text:
            result.append(f"\n### 📊 图谱关系")
            result.append(graph_text)
        
        # 添加相关查询建议
        if relations:
            related_concepts = list(set(r.get("target") for r in relations[:5] if r.get("target")))[:3]
            if related_concepts:
                result.append(f"\n---\n💡 **相关概念**: " + " | ".join(f"`/graph {c}`" for c in related_concepts))
        
        return "\n".join(result)
        
    except Exception as e:
        return f"❌ 查询失败: {str(e)}"


# ==========================================
# 图谱文本可视化
# ==========================================

def generate_concept_graph_text(concept_name: str, max_relations: int = 8) -> Optional[str]:
    """
    生成概念相关的图谱关系文本描述（ASCII 风格）
    
    Args:
        concept_name: 概念名称
        max_relations: 最大关系数量
        
    Returns:
        格式化的文本图谱，失败返回 None
    """
    try:
        graph = get_graph_query()
        if not graph.is_connected():
            return None
        
        concept = graph.get_concept(concept_name)
        if not concept:
            return None
        
        actual_name = concept.get("name", concept_name)
        
        relations = graph.get_relations(actual_name, direction="both")
        if not relations:
            return None
        
        rel_emoji = {
            "COMPOSED_OF": "🔧",
            "CONTAINS": "📦",
            "DEPENDS_ON": "⬅️",
            "IS_A": "📂",
            "USES": "🔗",
            "CONTRASTS_WITH": "⚖️",
            "IMPLEMENTED_BY": "⚙️",
            "PRECEDES": "➡️",
            "RELATED_TO": "🔄",
        }
        
        grouped = {}
        for rel in relations[:max_relations]:
            rel_type = rel.get("relation_type", "RELATED")
            target = rel.get("target", "")
            if rel_type not in grouped:
                grouped[rel_type] = []
            if target and target not in grouped[rel_type]:
                grouped[rel_type].append(target)
        
        lines = []
        lines.append(f"```")
        lines.append(f"        ┌─────────────┐")
        lines.append(f"        │  {actual_name:^9}  │")
        lines.append(f"        └──────┬──────┘")
        lines.append(f"               │")
        
        for rel_type, targets in list(grouped.items())[:4]:
            emoji = rel_emoji.get(rel_type, "•")
            rel_name = rel_type.replace("_", " ").lower()
            targets_str = ", ".join(targets[:3])
            if len(targets) > 3:
                targets_str += f" (+{len(targets)-3})"
            lines.append(f"    {emoji} {rel_name}: {targets_str}")
        
        lines.append(f"```")
        
        return "\n".join(lines)
        
    except Exception as e:
        print(f"生成图谱文本失败: {e}")
        return None


# ==========================================
# 交互式图谱可视化
# ==========================================

def generate_interactive_graph(concept_name: str) -> Optional[str]:
    """
    生成交互式图谱可视化 HTML 文件
    
    Args:
        concept_name: 概念名称
        
    Returns:
        HTML 文件路径，如果失败返回 None
    """
    try:
        visualizer = get_visualizer()
        
        # 先获取标准化的概念名
        graph = get_graph_query()
        concept = graph.get_concept(concept_name)
        if not concept:
            return None
        
        actual_name = concept.get("name", concept_name)
        
        # 生成 HTML
        html_content = visualizer.visualize_concept_neighborhood(
            actual_name,
            depth=2,
            max_nodes=50
        )
        
        if not html_content:
            return None
        
        # 保存到文件
        safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in actual_name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_name}_{timestamp}.html"
        filepath = GRAPH_VIZ_DIR / filename
        
        filepath.write_text(html_content, encoding="utf-8")
        
        return str(filepath)
        
    except Exception as e:
        print(f"生成交互式图谱失败: {e}")
        import traceback
        traceback.print_exc()
        return None

