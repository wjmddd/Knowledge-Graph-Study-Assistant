"""
图谱查询模块
封装 Neo4j 常用查询操作
"""

import sys
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from neo4j import GraphDatabase

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config.settings import NEO4J_CONFIG


class GraphQuery:
    """Neo4j 图谱查询封装"""
    
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
        except Exception as e:
            print(f"⚠️ Neo4j 连接失败: {e}")
            self.driver = None
    
    def close(self):
        """关闭连接"""
        if self.driver:
            self.driver.close()
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self.driver is not None
    
    # ==========================================
    # 1. 概念查询
    # ==========================================
    
    def get_concept(self, name: str) -> Optional[Dict[str, Any]]:
        """
        根据名称获取概念详情
        
        Args:
            name: 概念名称
            
        Returns:
            概念信息字典，包含定义、别名等
        """
        if not self.driver:
            return None
        
        query = """
        MATCH (c:Concept)
        WHERE c.name = $name OR $name IN c.alias
        RETURN c.id as id, c.name as name, c.definition as definition, 
               c.alias as alias, c.label as label
        LIMIT 1
        """
        
        with self.driver.session() as session:
            result = session.run(query, name=name)
            record = result.single()
            if record:
                return dict(record)
        return None
    
    def search_concepts(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        模糊搜索概念
        
        Args:
            keyword: 搜索关键词
            limit: 返回数量上限
            
        Returns:
            匹配的概念列表
        """
        if not self.driver:
            return []
        
        query = """
        MATCH (c:Concept)
        WHERE c.name CONTAINS $keyword 
           OR c.definition CONTAINS $keyword
           OR ANY(a IN c.alias WHERE a CONTAINS $keyword)
        RETURN c.id as id, c.name as name, c.definition as definition, c.alias as alias
        LIMIT $limit
        """
        
        results = []
        with self.driver.session() as session:
            result = session.run(query, keyword=keyword, limit=limit)
            for record in result:
                results.append(dict(record))
        return results
    
    # ==========================================
    # 2. 关系查询
    # ==========================================
    
    def get_relations(
        self,
        concept_name: str,
        relation_type: Optional[str] = None,
        direction: str = "both"
    ) -> List[Dict[str, Any]]:
        """
        获取概念的相关关系
        
        Args:
            concept_name: 概念名称
            relation_type: 关系类型 (可选，如 "COMPOSED_OF", "DEPENDS_ON")
            direction: 方向 ("out", "in", "both")
            
        Returns:
            关系列表，每个包含 source, target, type, properties
        """
        if not self.driver:
            return []
        
        # 构建查询
        if direction == "out":
            pattern = "(c)-[r]->(related)"
        elif direction == "in":
            pattern = "(c)<-[r]-(related)"
        else:
            pattern = "(c)-[r]-(related)"
        
        # 关系类型过滤
        if relation_type:
            pattern = pattern.replace("[r]", f"[r:{relation_type}]")
        
        query = f"""
        MATCH (c:Concept)
        WHERE c.name = $name OR $name IN c.alias
        MATCH {pattern}
        RETURN c.name as source, type(r) as relation_type, 
               related.name as target, related.definition as target_definition,
               labels(related)[0] as target_label, properties(r) as properties
        LIMIT 50
        """
        
        results = []
        with self.driver.session() as session:
            result = session.run(query, name=concept_name)
            for record in result:
                results.append(dict(record))
        return results
    
    def get_composed_of(self, concept_name: str) -> List[Dict[str, Any]]:
        """获取组成部分 (COMPOSED_OF 关系)"""
        return self.get_relations(concept_name, "COMPOSED_OF", "out")
    
    def get_depends_on(self, concept_name: str) -> List[Dict[str, Any]]:
        """获取前置依赖 (DEPENDS_ON 关系)"""
        return self.get_relations(concept_name, "DEPENDS_ON", "out")
    
    def get_is_a(self, concept_name: str) -> List[Dict[str, Any]]:
        """获取分类关系 (IS_A 关系)"""
        return self.get_relations(concept_name, "IS_A", "out")
    
    # ==========================================
    # 3. 路径查询
    # ==========================================
    
    def find_learning_path(
        self,
        target_concept: str,
        max_depth: int = 5
    ) -> List[List[str]]:
        """
        查找学习路径 (沿 DEPENDS_ON 回溯前置知识)
        
        Args:
            target_concept: 目标概念
            max_depth: 最大深度
            
        Returns:
            前置知识路径列表
        """
        if not self.driver:
            return []
        
        query = f"""
        MATCH (target:Concept)
        WHERE target.name = $name OR $name IN target.alias
        MATCH path = (target)-[:DEPENDS_ON*1..{max_depth}]->(prereq)
        RETURN [n IN nodes(path) | n.name] as learning_path
        ORDER BY length(path)
        LIMIT 10
        """
        
        paths = []
        with self.driver.session() as session:
            result = session.run(query, name=target_concept)
            for record in result:
                paths.append(record["learning_path"])
        return paths
    
    def find_path_between(
        self,
        concept_a: str,
        concept_b: str,
        max_depth: int = 4
    ) -> Optional[List[Tuple[str, str, str]]]:
        """
        查找两个概念之间的路径
        
        Returns:
            路径列表 [(node1, rel_type, node2), ...]
        """
        if not self.driver:
            return None
        
        query = f"""
        MATCH (a), (b)
        WHERE (a.name = $name_a OR $name_a IN a.alias)
          AND (b.name = $name_b OR $name_b IN b.alias)
        MATCH path = shortestPath((a)-[*..{max_depth}]-(b))
        RETURN [n IN nodes(path) | n.name] as nodes,
               [r IN relationships(path) | type(r)] as relations
        LIMIT 1
        """
        
        with self.driver.session() as session:
            result = session.run(query, name_a=concept_a, name_b=concept_b)
            record = result.single()
            if record:
                nodes = record["nodes"]
                relations = record["relations"]
                path = []
                for i in range(len(relations)):
                    path.append((nodes[i], relations[i], nodes[i+1]))
                return path
        return None
    
    # ==========================================
    # 4. 溯源查询 (TextChunk -> Concept)
    # ==========================================
    
    def get_concept_sources(self, concept_name: str) -> List[Dict[str, Any]]:
        """
        获取概念的文本来源 (通过 MENTIONS 关系)
        
        Returns:
            来源列表，包含章节、内容等
        """
        if not self.driver:
            return []
        
        query = """
        MATCH (c:Concept)
        WHERE c.name = $name OR $name IN c.alias
        MATCH (chunk:TextChunk)-[:MENTIONS]->(c)
        OPTIONAL MATCH (section:Section)-[:CONTAINS]->(chunk)
        OPTIONAL MATCH (chapter:Chapter)-[:CONTAINS]->(section)
        RETURN chunk.content as content, chunk.id as chunk_id,
               section.title as section, chapter.title as chapter
        LIMIT 5
        """
        
        results = []
        with self.driver.session() as session:
            result = session.run(query, name=concept_name)
            for record in result:
                results.append(dict(record))
        return results
    
    # ==========================================
    # 5. 对比查询
    # ==========================================
    
    def compare_concepts(
        self,
        concept_a: str,
        concept_b: str
    ) -> Dict[str, Any]:
        """
        对比两个概念
        
        Returns:
            包含两个概念的定义、共同关系、差异等
        """
        if not self.driver:
            return {}
        
        # 获取两个概念的信息
        info_a = self.get_concept(concept_a)
        info_b = self.get_concept(concept_b)
        
        # 查找它们之间的直接关系
        direct_relation = None
        query = """
        MATCH (a), (b)
        WHERE (a.name = $name_a OR $name_a IN a.alias)
          AND (b.name = $name_b OR $name_b IN b.alias)
        MATCH (a)-[r]-(b)
        RETURN type(r) as relation_type, properties(r) as properties
        LIMIT 1
        """
        
        with self.driver.session() as session:
            result = session.run(query, name_a=concept_a, name_b=concept_b)
            record = result.single()
            if record:
                direct_relation = {
                    "type": record["relation_type"],
                    "properties": record["properties"]
                }
        
        # 获取两者的共同上级 (IS_A)
        common_parent = None
        query = """
        MATCH (a)-[:IS_A]->(parent)<-[:IS_A]-(b)
        WHERE (a.name = $name_a OR $name_a IN a.alias)
          AND (b.name = $name_b OR $name_b IN b.alias)
        RETURN parent.name as parent_name
        LIMIT 1
        """
        
        with self.driver.session() as session:
            result = session.run(query, name_a=concept_a, name_b=concept_b)
            record = result.single()
            if record:
                common_parent = record["parent_name"]
        
        return {
            "concept_a": info_a,
            "concept_b": info_b,
            "direct_relation": direct_relation,
            "common_parent": common_parent
        }
    
    # ==========================================
    # 6. 统计查询
    # ==========================================
    
    def get_stats(self) -> Dict[str, Any]:
        """获取图谱统计信息"""
        if not self.driver:
            return {}
        
        stats = {"nodes": {}, "relationships": {}}
        
        with self.driver.session() as session:
            # 节点统计
            result = session.run("""
                MATCH (n) 
                RETURN labels(n)[0] AS label, count(*) AS count 
                ORDER BY count DESC
            """)
            for record in result:
                stats["nodes"][record["label"]] = record["count"]
            
            # 关系统计
            result = session.run("""
                MATCH ()-[r]->() 
                RETURN type(r) AS type, count(*) AS count 
                ORDER BY count DESC
            """)
            for record in result:
                stats["relationships"][record["type"]] = record["count"]
        
        return stats


# 全局单例
_graph_query: Optional[GraphQuery] = None


def get_graph_query() -> GraphQuery:
    """获取全局图谱查询实例"""
    global _graph_query
    if _graph_query is None:
        _graph_query = GraphQuery()
    return _graph_query


if __name__ == "__main__":
    # 测试
    print("测试 GraphQuery 模块...")
    gq = GraphQuery()
    
    if gq.is_connected():
        print("✓ Neo4j 连接成功")
        
        # 测试统计
        stats = gq.get_stats()
        print(f"\n📊 图谱统计:")
        print(f"   节点: {stats.get('nodes', {})}")
        print(f"   关系: {stats.get('relationships', {})}")
        
        # 测试概念查询
        concept = gq.get_concept("CPU")
        if concept:
            print(f"\n🔍 查询 'CPU':")
            print(f"   名称: {concept.get('name')}")
            print(f"   定义: {concept.get('definition', '无')[:100]}...")
        
        gq.close()
    else:
        print("❌ Neo4j 连接失败，请检查配置")

