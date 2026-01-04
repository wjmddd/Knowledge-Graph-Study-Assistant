"""
诊断知识图谱结构
检查节点、关系和溯源能力
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from neo4j import GraphDatabase
from config.settings import NEO4J_CONFIG

def diagnose():
    print("=" * 60)
    print("🔍 知识图谱结构诊断")
    print("=" * 60)
    
    driver = GraphDatabase.driver(
        NEO4J_CONFIG["uri"],
        auth=(NEO4J_CONFIG["user"], NEO4J_CONFIG["password"])
    )
    
    with driver.session() as session:
        # 1. 检查 CPU 节点
        print("\n📌 1. 检查 CPU 节点:")
        result = session.run("""
            MATCH (n {name: 'CPU'})
            RETURN labels(n) as labels, n.name as name, n.definition as definition,
                   n.alias as alias, n.source_chunk as source_chunk
        """)
        for record in result:
            print(f"   标签: {record['labels']}")
            print(f"   名称: {record['name']}")
            print(f"   定义: {(record['definition'] or '')[:100]}...")
            print(f"   别名: {record['alias']}")
            print(f"   source_chunk: {record['source_chunk']}")
        
        # 2. 检查 CPU 的关系
        print("\n📌 2. 检查 CPU 的出边关系:")
        result = session.run("""
            MATCH (n {name: 'CPU'})-[r]->(m)
            RETURN type(r) as rel_type, m.name as target, labels(m)[0] as target_label
            LIMIT 10
        """)
        rels = list(result)
        if rels:
            for record in rels:
                print(f"   CPU --[{record['rel_type']}]--> {record['target']} ({record['target_label']})")
        else:
            print("   ❌ CPU 没有出边关系!")
        
        # 3. 检查 TextChunk 节点
        print("\n📌 3. 检查 TextChunk 节点:")
        result = session.run("""
            MATCH (t:TextChunk)
            RETURN count(t) as count
        """)
        count = result.single()["count"]
        print(f"   TextChunk 节点数量: {count}")
        
        # 4. 检查 MENTIONS 关系
        print("\n📌 4. 检查 MENTIONS 关系:")
        result = session.run("""
            MATCH ()-[r:MENTIONS]->()
            RETURN count(r) as count
        """)
        count = result.single()["count"]
        print(f"   MENTIONS 关系数量: {count}")
        
        # 5. 检查 COMPOSED_OF 关系
        print("\n📌 5. 检查 COMPOSED_OF 关系:")
        result = session.run("""
            MATCH ()-[r:COMPOSED_OF]->()
            RETURN count(r) as count
        """)
        count = result.single()["count"]
        print(f"   COMPOSED_OF 关系数量: {count}")
        
        # 6. 检查与 CPU 相关的 COMPOSED_OF
        print("\n📌 6. 检查 CPU 的 COMPOSED_OF 关系:")
        result = session.run("""
            MATCH (n)-[r:COMPOSED_OF]->(m)
            WHERE toLower(n.name) CONTAINS 'cpu' OR toLower(m.name) CONTAINS 'cpu'
            RETURN n.name as source, m.name as target
            LIMIT 10
        """)
        rels = list(result)
        if rels:
            for record in rels:
                print(f"   {record['source']} --[COMPOSED_OF]--> {record['target']}")
        else:
            print("   ❌ 没有与 CPU 相关的 COMPOSED_OF 关系!")
        
        # 7. 检查 TextChunk 中提到 CPU 的内容
        print("\n📌 7. 检查 TextChunk 中提到 CPU 的内容:")
        result = session.run("""
            MATCH (t:TextChunk)
            WHERE toLower(t.content) CONTAINS 'cpu'
            OPTIONAL MATCH (s:Section)-[:CONTAINS]->(t)
            OPTIONAL MATCH (c:Chapter)-[:CONTAINS]->(s)
            RETURN t.id as chunk_id, c.title as chapter, s.title as section,
                   substring(t.content, 0, 100) as preview
            LIMIT 3
        """)
        chunks = list(result)
        if chunks:
            for record in chunks:
                print(f"   章节: {record['chapter']}/{record['section']}")
                print(f"   内容: {record['preview']}...")
                print()
        else:
            print("   ❌ 没有 TextChunk 提到 CPU!")
        
        # 8. 统计所有关系类型
        print("\n📌 8. 所有关系类型统计:")
        result = session.run("""
            MATCH ()-[r]->()
            RETURN type(r) as rel_type, count(r) as count
            ORDER BY count DESC
        """)
        for record in result:
            print(f"   {record['rel_type']}: {record['count']}")
    
    driver.close()
    print("\n" + "=" * 60)
    print("✅ 诊断完成!")


if __name__ == "__main__":
    diagnose()

