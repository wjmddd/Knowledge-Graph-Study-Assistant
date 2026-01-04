"""
知识图谱可视化组件
使用 Pyvis 生成交互式图谱可视化
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import json

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pyvis.network import Network
from src.retrieval.graph_query import get_graph_query


# ==========================================
# 颜色和样式配置
# ==========================================

# 节点类型对应的颜色
NODE_COLORS = {
    "Concept": "#4CAF50",       # 绿色 - 概念
    "Hardware": "#2196F3",      # 蓝色 - 硬件
    "Instruction": "#FF9800",   # 橙色 - 指令
    "Principle": "#9C27B0",     # 紫色 - 原理
    "CodeSnippet": "#607D8B",   # 灰蓝色 - 代码
    "Chapter": "#F44336",       # 红色 - 章节
    "Section": "#E91E63",       # 粉红色 - 节
    "TextChunk": "#795548",     # 棕色 - 文本块
    "Course": "#FF5722",        # 深橙色 - 课程
    "default": "#9E9E9E"        # 灰色 - 默认
}

# 关系类型对应的颜色
EDGE_COLORS = {
    "DEPENDS_ON": "#F44336",     # 红色
    "IS_A": "#4CAF50",           # 绿色
    "COMPOSED_OF": "#2196F3",    # 蓝色
    "CONTAINS": "#9C27B0",       # 紫色
    "MENTIONS": "#FF9800",       # 橙色
    "IMPLEMENTED_BY": "#00BCD4", # 青色
    "EXAMPLE_OF": "#FFEB3B",     # 黄色
    "default": "#9E9E9E"         # 灰色
}


class KnowledgeGraphVisualizer:
    """知识图谱可视化器"""
    
    def __init__(self):
        self.graph_query = get_graph_query()
    
    def create_network(
        self,
        height: str = "600px",
        width: str = "100%",
        directed: bool = True,
        notebook: bool = False
    ) -> Network:
        """创建 Pyvis 网络对象"""
        net = Network(
            height=height,
            width=width,
            directed=directed,
            notebook=notebook,
            bgcolor="#ffffff",
            font_color="#333333"
        )
        
        # 配置物理引擎
        net.set_options("""
        {
            "nodes": {
                "font": {"size": 14, "face": "Microsoft YaHei"},
                "borderWidth": 2,
                "shadow": true
            },
            "edges": {
                "font": {"size": 10, "face": "Microsoft YaHei"},
                "arrows": {"to": {"enabled": true, "scaleFactor": 0.5}},
                "smooth": {"type": "curvedCW", "roundness": 0.2}
            },
            "physics": {
                "enabled": true,
                "solver": "forceAtlas2Based",
                "forceAtlas2Based": {
                    "gravitationalConstant": -50,
                    "centralGravity": 0.01,
                    "springLength": 100,
                    "springConstant": 0.08
                },
                "stabilization": {
                    "enabled": true,
                    "iterations": 100
                }
            },
            "interaction": {
                "hover": true,
                "tooltipDelay": 100,
                "navigationButtons": true,
                "keyboard": true
            }
        }
        """)
        
        return net
    
    def visualize_concept_neighborhood(
        self,
        concept_name: str,
        depth: int = 2,
        max_nodes: int = 50
    ) -> Optional[str]:
        """
        可视化概念的邻域图
        
        Args:
            concept_name: 中心概念名称
            depth: 扩展深度
            max_nodes: 最大节点数
            
        Returns:
            HTML 字符串
        """
        if not self.graph_query.is_connected():
            return None
        
        # 查询邻域
        query = """
        MATCH path = (center)-[*1..%d]-(neighbor)
        WHERE center.name CONTAINS $name OR center.name =~ ('(?i).*' + $name + '.*')
        WITH center, neighbor, relationships(path) as rels, nodes(path) as path_nodes
        UNWIND path_nodes as n
        UNWIND rels as r
        WITH DISTINCT n, r
        RETURN 
            collect(DISTINCT {
                id: id(n), 
                name: n.name, 
                label: labels(n)[0],
                definition: n.definition
            }) as nodes,
            collect(DISTINCT {
                source: id(startNode(r)),
                target: id(endNode(r)),
                type: type(r)
            }) as relationships
        LIMIT %d
        """ % (depth, max_nodes)
        
        try:
            with self.graph_query.driver.session() as session:
                result = session.run(query, name=concept_name)
                record = result.single()
                
                if not record:
                    return None
                
                nodes = record["nodes"]
                relationships = record["relationships"]
                
                if not nodes:
                    return None
                
                # 创建网络
                net = self.create_network()
                
                # 添加节点
                node_id_map = {}
                for node in nodes:
                    if node["id"] is None:
                        continue
                    
                    node_id = str(node["id"])
                    node_id_map[node["id"]] = node_id
                    
                    label = node.get("label", "default")
                    name = node.get("name", "未知")
                    definition = node.get("definition", "")
                    
                    color = NODE_COLORS.get(label, NODE_COLORS["default"])
                    
                    # 中心节点特殊处理
                    is_center = concept_name.lower() in name.lower()
                    size = 30 if is_center else 20
                    
                    title = f"<b>{name}</b><br/>类型: {label}"
                    if definition:
                        title += f"<br/><br/>{definition[:200]}..."
                    
                    net.add_node(
                        node_id,
                        label=name,
                        title=title,
                        color=color,
                        size=size,
                        shape="dot" if not is_center else "star"
                    )
                
                # 添加边
                for rel in relationships:
                    if rel["source"] is None or rel["target"] is None:
                        continue
                    
                    source_id = node_id_map.get(rel["source"])
                    target_id = node_id_map.get(rel["target"])
                    
                    if source_id and target_id:
                        rel_type = rel.get("type", "RELATED")
                        color = EDGE_COLORS.get(rel_type, EDGE_COLORS["default"])
                        
                        net.add_edge(
                            source_id,
                            target_id,
                            title=rel_type,
                            label=rel_type,
                            color=color
                        )
                
                # 生成 HTML
                return net.generate_html()
                
        except Exception as e:
            print(f"⚠️ 可视化失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def visualize_learning_path(
        self,
        concept_name: str
    ) -> Optional[str]:
        """
        可视化学习路径
        
        Args:
            concept_name: 目标概念
            
        Returns:
            HTML 字符串
        """
        if not self.graph_query.is_connected():
            return None
        
        # 查询学习路径
        query = """
        MATCH path = (target)<-[:DEPENDS_ON*1..5]-(prereq)
        WHERE target.name CONTAINS $name
        WITH nodes(path) as path_nodes, relationships(path) as rels
        UNWIND path_nodes as n
        UNWIND rels as r
        WITH DISTINCT n, r
        RETURN 
            collect(DISTINCT {
                id: id(n), 
                name: n.name, 
                label: labels(n)[0]
            }) as nodes,
            collect(DISTINCT {
                source: id(startNode(r)),
                target: id(endNode(r)),
                type: type(r)
            }) as relationships
        """
        
        try:
            with self.graph_query.driver.session() as session:
                result = session.run(query, name=concept_name)
                record = result.single()
                
                if not record or not record["nodes"]:
                    return None
                
                nodes = record["nodes"]
                relationships = record["relationships"]
                
                # 创建网络
                net = self.create_network()
                
                # 计算节点层级 (用于布局)
                node_levels = {}
                # 目标概念在最右边
                for node in nodes:
                    if concept_name.lower() in node.get("name", "").lower():
                        node_levels[node["id"]] = 0
                
                # 添加节点
                node_id_map = {}
                for node in nodes:
                    if node["id"] is None:
                        continue
                    
                    node_id = str(node["id"])
                    node_id_map[node["id"]] = node_id
                    
                    name = node.get("name", "未知")
                    label = node.get("label", "default")
                    
                    is_target = concept_name.lower() in name.lower()
                    color = "#F44336" if is_target else NODE_COLORS.get(label, NODE_COLORS["default"])
                    
                    net.add_node(
                        node_id,
                        label=name,
                        title=f"{name} ({label})",
                        color=color,
                        size=30 if is_target else 20,
                        shape="star" if is_target else "dot"
                    )
                
                # 添加边
                for rel in relationships:
                    if rel["source"] is None or rel["target"] is None:
                        continue
                    
                    source_id = node_id_map.get(rel["source"])
                    target_id = node_id_map.get(rel["target"])
                    
                    if source_id and target_id:
                        net.add_edge(
                            source_id,
                            target_id,
                            title="DEPENDS_ON",
                            label="依赖",
                            color=EDGE_COLORS["DEPENDS_ON"]
                        )
                
                return net.generate_html()
                
        except Exception as e:
            print(f"⚠️ 学习路径可视化失败: {e}")
            return None
    
    def visualize_chapter_structure(
        self,
        chapter_name: str = None
    ) -> Optional[str]:
        """
        可视化章节结构
        
        Args:
            chapter_name: 章节名称，为 None 则显示全部
            
        Returns:
            HTML 字符串
        """
        if not self.graph_query.is_connected():
            return None
        
        if chapter_name:
            query = """
            MATCH (c:Chapter)-[:CONTAINS*1..2]->(child)
            WHERE c.title CONTAINS $name
            RETURN c, child, 'CONTAINS' as rel_type
            LIMIT 100
            """
            params = {"name": chapter_name}
        else:
            query = """
            MATCH (course:Course)-[:CONTAINS]->(chapter:Chapter)
            OPTIONAL MATCH (chapter)-[:CONTAINS]->(section:Section)
            RETURN course, chapter, section
            LIMIT 100
            """
            params = {}
        
        try:
            with self.graph_query.driver.session() as session:
                result = session.run(query, **params)
                records = list(result)
                
                if not records:
                    return None
                
                net = self.create_network()
                added_nodes = set()
                
                for record in records:
                    # 处理不同的查询结果格式
                    if "course" in record.keys():
                        course = record["course"]
                        chapter = record["chapter"]
                        section = record.get("section")
                        
                        if course and course.id not in added_nodes:
                            net.add_node(
                                str(course.id),
                                label=course.get("name", "课程"),
                                color=NODE_COLORS["Course"],
                                size=40,
                                shape="diamond"
                            )
                            added_nodes.add(course.id)
                        
                        if chapter and chapter.id not in added_nodes:
                            net.add_node(
                                str(chapter.id),
                                label=chapter.get("title", "章节"),
                                color=NODE_COLORS["Chapter"],
                                size=30
                            )
                            added_nodes.add(chapter.id)
                            if course:
                                net.add_edge(str(course.id), str(chapter.id), label="包含")
                        
                        if section and section.id not in added_nodes:
                            net.add_node(
                                str(section.id),
                                label=section.get("title", "节"),
                                color=NODE_COLORS["Section"],
                                size=20
                            )
                            added_nodes.add(section.id)
                            if chapter:
                                net.add_edge(str(chapter.id), str(section.id), label="包含")
                
                return net.generate_html()
                
        except Exception as e:
            print(f"⚠️ 章节结构可视化失败: {e}")
            return None
    
    def get_graph_stats(self) -> Dict[str, Any]:
        """获取图谱统计信息"""
        if not self.graph_query.is_connected():
            return {"error": "图数据库未连接"}
        
        stats = {}
        
        try:
            with self.graph_query.driver.session() as session:
                # 节点统计
                result = session.run("""
                    MATCH (n)
                    RETURN labels(n)[0] as label, count(*) as count
                    ORDER BY count DESC
                """)
                stats["nodes_by_type"] = {r["label"]: r["count"] for r in result}
                
                # 关系统计
                result = session.run("""
                    MATCH ()-[r]->()
                    RETURN type(r) as type, count(*) as count
                    ORDER BY count DESC
                """)
                stats["relationships_by_type"] = {r["type"]: r["count"] for r in result}
                
                # 总计
                result = session.run("MATCH (n) RETURN count(n) as total")
                stats["total_nodes"] = result.single()["total"]
                
                result = session.run("MATCH ()-[r]->() RETURN count(r) as total")
                stats["total_relationships"] = result.single()["total"]
                
        except Exception as e:
            stats["error"] = str(e)
        
        return stats


# ==========================================
# 全局单例
# ==========================================

_visualizer: Optional[KnowledgeGraphVisualizer] = None


def get_visualizer() -> KnowledgeGraphVisualizer:
    """获取全局可视化器"""
    global _visualizer
    if _visualizer is None:
        _visualizer = KnowledgeGraphVisualizer()
    return _visualizer


# ==========================================
# 测试
# ==========================================

if __name__ == "__main__":
    print("测试知识图谱可视化...")
    
    viz = KnowledgeGraphVisualizer()
    
    # 测试统计
    print("\n1. 图谱统计:")
    stats = viz.get_graph_stats()
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    # 测试概念邻域可视化
    print("\n2. 生成 CPU 邻域图...")
    html = viz.visualize_concept_neighborhood("CPU", depth=2)
    if html:
        output_path = Path("test_viz.html")
        output_path.write_text(html, encoding="utf-8")
        print(f"   已保存到: {output_path}")
    else:
        print("   生成失败")

