"""检查 MENTIONS 关系方向"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from neo4j import GraphDatabase
from config.settings import NEO4J_CONFIG

driver = GraphDatabase.driver(NEO4J_CONFIG['uri'], auth=(NEO4J_CONFIG['user'], NEO4J_CONFIG['password']))
with driver.session() as session:
    # 检查 MENTIONS 关系方向
    result = session.run('''
        MATCH (a)-[r:MENTIONS]->(b)
        RETURN labels(a)[0] as source_label, labels(b)[0] as target_label
        LIMIT 5
    ''')
    print('MENTIONS 关系方向:')
    for r in result:
        print(f"  ({r['source_label']}) -[:MENTIONS]-> ({r['target_label']})")
    
    # 检查是否有 TextChunk -> CPU 的 MENTIONS
    result = session.run('''
        MATCH (t:TextChunk)-[:MENTIONS]->(c)
        WHERE c.name = 'CPU' OR 'CPU' IN coalesce(c.alias, [])
        RETURN t.id as chunk_id, c.name as concept_name
        LIMIT 3
    ''')
    mentions = list(result)
    print(f'\nTextChunk -[:MENTIONS]-> CPU 数量: {len(mentions)}')
    for m in mentions:
        print(f"  {m['chunk_id']} -> {m['concept_name']}")
    
    # 如果没有，检查反向
    if not mentions:
        result = session.run('''
            MATCH (c)-[:MENTIONS]->(t:TextChunk)
            WHERE c.name = 'CPU' OR 'CPU' IN coalesce(c.alias, [])
            RETURN t.id as chunk_id, c.name as concept_name
            LIMIT 3
        ''')
        mentions = list(result)
        print(f'\nCPU -[:MENTIONS]-> TextChunk 数量 (反向): {len(mentions)}')
        for m in mentions:
            print(f"  {m['concept_name']} -> {m['chunk_id']}")

driver.close()

