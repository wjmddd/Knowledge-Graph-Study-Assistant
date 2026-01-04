"""
将知识图谱数据导入 Neo4j
用法: python scripts/import_to_neo4j.py

前置条件:
1. 安装 Neo4j Desktop 或使用 Neo4j Aura (云版本)
2. pip install neo4j
3. 配置下方的连接信息
"""

import json
import sys
from pathlib import Path

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent))

from neo4j import GraphDatabase

# ========== Neo4j 连接配置 ==========
NEO4J_URI = "neo4j://localhost:7687"  # 本地 Neo4j
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "F9rSd7UAt2FkkNU"  # 替换为你的密码
INPUT_FILE = "graph_data_final.json"  # 最终去重后的图谱
# ====================================


class Neo4jImporter:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    def clear_database(self):
        """清空数据库（谨慎使用！）"""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            print("🗑️  数据库已清空")
    
    def create_indexes(self):
        """创建索引以提高查询性能"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS FOR (n:Course) ON (n.id)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Chapter) ON (n.id)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Section) ON (n.id)",
            "CREATE INDEX IF NOT EXISTS FOR (n:TextChunk) ON (n.id)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Concept) ON (n.id)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Concept) ON (n.name)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Hardware) ON (n.id)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Instruction) ON (n.id)",
            "CREATE INDEX IF NOT EXISTS FOR (n:CodeSnippet) ON (n.id)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Principle) ON (n.id)",
        ]
        with self.driver.session() as session:
            for idx in indexes:
                session.run(idx)
        print("📇 索引创建完成")
    
    def import_nodes(self, nodes: list):
        """导入所有节点"""
        with self.driver.session() as session:
            for node in nodes:
                label = node.get("label")
                if not label:
                    continue
                
                # 构建属性字符串（排除 label）
                props = {k: v for k, v in node.items() if k != "label" and v is not None}
                
                # 动态创建节点
                query = f"MERGE (n:{label} {{id: $id}}) SET n += $props"
                session.run(query, id=node["id"], props=props)
        
        print(f"📦 导入节点: {len(nodes)} 个")
    
    def import_relationships(self, relationships: list):
        """导入所有关系"""
        with self.driver.session() as session:
            for rel in relationships:
                source_id = rel.get("source_id")
                target_id = rel.get("target_id")
                rel_type = rel.get("type", "RELATED_TO")
                props = rel.get("properties", {})
                
                # 动态创建关系
                query = f"""
                MATCH (a {{id: $source_id}})
                MATCH (b {{id: $target_id}})
                MERGE (a)-[r:{rel_type}]->(b)
                SET r += $props
                """
                session.run(query, source_id=source_id, target_id=target_id, props=props)
        
        print(f"🔗 导入关系: {len(relationships)} 条")
    
    def get_stats(self):
        """获取数据库统计信息"""
        with self.driver.session() as session:
            # 节点统计
            result = session.run("""
                MATCH (n) 
                RETURN labels(n)[0] AS label, count(*) AS count 
                ORDER BY count DESC
            """)
            print("\n📊 节点统计:")
            for record in result:
                print(f"   {record['label']}: {record['count']}")
            
            # 关系统计
            result = session.run("""
                MATCH ()-[r]->() 
                RETURN type(r) AS type, count(*) AS count 
                ORDER BY count DESC
            """)
            print("\n🔗 关系统计:")
            for record in result:
                print(f"   {record['type']}: {record['count']}")


def main():
    print("=" * 60)
    print("🚀 Neo4j 知识图谱导入工具")
    print("=" * 60)
    
    # 1. 加载数据
    print(f"\n📂 加载数据: {INPUT_FILE}")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    nodes = data.get("nodes", [])
    relationships = data.get("relationships", [])
    print(f"   节点: {len(nodes)} 个")
    print(f"   关系: {len(relationships)} 条")
    
    # 2. 连接 Neo4j
    print(f"\n🔌 连接 Neo4j: {NEO4J_URI}")
    try:
        importer = Neo4jImporter(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        print("\n请检查:")
        print("1. Neo4j 是否已启动")
        print("2. 连接地址是否正确")
        print("3. 用户名密码是否正确")
        return
    
    try:
        # 3. 清空数据库（可选）
        confirm = input("\n⚠️  是否清空现有数据? (y/N): ")
        if confirm.lower() == 'y':
            importer.clear_database()
        
        # 4. 创建索引
        print("\n📇 创建索引...")
        importer.create_indexes()
        
        # 5. 导入数据
        print("\n📥 导入数据...")
        importer.import_nodes(nodes)
        importer.import_relationships(relationships)
        
        # 6. 显示统计
        importer.get_stats()
        
        print("\n" + "=" * 60)
        print("✅ 导入完成!")
        print("=" * 60)
        print("\n🎯 现在可以打开 Neo4j Browser 查看图谱了")
        print("   地址: http://localhost:7474")
        
    finally:
        importer.close()


if __name__ == "__main__":
    main()

