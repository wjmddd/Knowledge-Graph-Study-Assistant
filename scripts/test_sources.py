"""测试 get_concept_sources"""
import sys
sys.path.insert(0, '.')
from src.retrieval.graph_query import get_graph_query

gq = get_graph_query()
print('测试 get_concept_sources("CPU"):')
sources = gq.get_concept_sources('CPU')
print(f'找到来源数量: {len(sources)}')
for s in sources[:3]:
    print(f"  章节: {s.get('chapter')}/{s.get('section')}")
    content = (s.get('content') or '')[:80]
    print(f"  内容: {content}...")
    print()

print('\n测试 get_concept_composition 工具:')
from src.agent.langchain_tools import get_concept_composition
result = get_concept_composition.invoke({"concept_name": "CPU"})
print(result[:500] if len(result) > 500 else result)

