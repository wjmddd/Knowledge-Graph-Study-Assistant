"""
知识图谱构建主入口
构建两层结构：
1. 文档结构层 (自动生成): Course -> Chapter -> Section -> TextChunk
2. 知识语义层 (LLM提取): Concept, Hardware, Instruction, CodeSnippet, Principle
3. 连接层: TextChunk -> MENTIONS -> 知识节点

用法: python scripts/build_kg.py
"""

import sys
import json
import time
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import instructor
from openai import OpenAI

from config.settings import CLIENT_CONFIG, INPUT_FILE, OUTPUT_FILE, REQUEST_DELAY
from src.pipeline.parser import parse_markdown_with_context
from src.pipeline.extractor import process_single_chunk
from src.pipeline.document_builder import build_document_structure, create_mentions_relationships
from src.models.schema import FullKnowledgeGraph, GraphRelationship


def main():
    print("=" * 60)
    print("🏗️  知识图谱构建流水线 (双层结构)")
    print("=" * 60)
    print(f"📄 输入文件: {INPUT_FILE}")
    print(f"📡 使用模型: {CLIENT_CONFIG['model']}")
    print(f"🔗 API 地址: {CLIENT_CONFIG['base_url']}")
    print("=" * 60)
    
    # ========================================
    # 阶段 1: 解析 Markdown
    # ========================================
    print("\n📖 阶段 1: 解析 Markdown 文件...")
    chunks = parse_markdown_with_context(INPUT_FILE)
    print(f"   ✓ 解析完成，共 {len(chunks)} 个文本块")
    
    # ========================================
    # 阶段 2: 构建文档结构层 (自动)
    # ========================================
    print("\n📚 阶段 2: 构建文档结构层...")
    kg, chunk_id_map = build_document_structure(chunks, course_name="计算机系统基础")
    
    # ========================================
    # 阶段 3: LLM 提取知识语义层
    # ========================================
    print(f"\n🤖 阶段 3: LLM 提取知识语义层 (每次请求间隔 {REQUEST_DELAY} 秒)...")
    
    client = instructor.from_openai(
        OpenAI(base_url=CLIENT_CONFIG["base_url"], api_key=CLIENT_CONFIG["api_key"]),
        mode=instructor.Mode.JSON
    )
    
    extraction_results = []  # 保存每个 chunk 的提取结果
    failed_chunks = []
    start_time = time.time()
    
    for i, chunk in enumerate(chunks):
        print(f"   [{i+1}/{len(chunks)}] 处理: {chunk.metadata['section'][:30]}...", end=" ")
        
        try:
            data = process_single_chunk(chunk, client)
            extraction_results.append(data)
            
            if data:
                # 将知识节点添加到图谱
                for node_dict in data.get("nodes", []):
                    # 直接存储字典，后续统一处理
                    kg.knowledge_nodes.append(node_dict)
                
                # 将知识层关系添加到图谱
                for rel_dict in data.get("relationships", []):
                    kg.relationships.append(GraphRelationship(**rel_dict))
                
                print(f"✓ 节点:{len(data.get('nodes', []))} 关系:{len(data.get('relationships', []))}")
            else:
                extraction_results.append(None)
                failed_chunks.append((i, chunk))
                print("✗ 失败")
                
        except Exception as exc:
            print(f"✗ 异常: {str(exc)[:50]}")
            extraction_results.append(None)
            failed_chunks.append((i, chunk))
        
        if i < len(chunks) - 1:
            time.sleep(REQUEST_DELAY)
    
    duration = time.time() - start_time
    print(f"\n   ✓ LLM 提取完成! 耗时: {duration:.1f}秒")
    
    # ========================================
    # 阶段 4: 创建 MENTIONS 关系
    # ========================================
    print("\n🔗 阶段 4: 创建 MENTIONS 关系 (连接文档层与知识层)...")
    mentions_rels = create_mentions_relationships(chunk_id_map, extraction_results, chunks)
    kg.relationships.extend(mentions_rels)
    
    # ========================================
    # 阶段 5: 统计与保存
    # ========================================
    print("\n" + "=" * 60)
    print("📊 构建统计")
    print("=" * 60)
    
    # 统计节点
    doc_layer_count = 1 + len(kg.chapters) + len(kg.sections) + len(kg.text_chunks)
    knowledge_layer_count = len(kg.knowledge_nodes)
    
    print(f"📚 文档结构层:")
    print(f"   - Course: 1")
    print(f"   - Chapter: {len(kg.chapters)}")
    print(f"   - Section: {len(kg.sections)}")
    print(f"   - TextChunk: {len(kg.text_chunks)}")
    print(f"   - 小计: {doc_layer_count} 个节点")
    
    print(f"\n🧠 知识语义层:")
    print(f"   - 知识节点: {knowledge_layer_count} 个")
    
    # 统计关系
    contains_count = sum(1 for r in kg.relationships if r.type == "CONTAINS")
    mentions_count = sum(1 for r in kg.relationships if r.type == "MENTIONS")
    knowledge_rel_count = len(kg.relationships) - contains_count - mentions_count
    
    print(f"\n🔗 关系统计:")
    print(f"   - CONTAINS (层级): {contains_count} 条")
    print(f"   - MENTIONS (溯源): {mentions_count} 条")
    print(f"   - 知识关系: {knowledge_rel_count} 条")
    print(f"   - 总计: {len(kg.relationships)} 条")
    
    if failed_chunks:
        print(f"\n⚠️  失败的块 ({len(failed_chunks)} 个):")
        for idx, fc in failed_chunks:
            print(f"   - [{idx+1}] {fc.metadata['section']}")
    
    # 保存结果
    print(f"\n💾 保存结果到: {OUTPUT_FILE}")
    
    # 转换为可序列化的格式
    output_data = {
        "metadata": {
            "course_name": "计算机系统基础",
            "total_chunks": len(chunks),
            "failed_chunks": len(failed_chunks),
            "build_time_seconds": round(duration, 2)
        },
        "document_layer": {
            "course": kg.course.model_dump() if kg.course else None,
            "chapters": [c.model_dump() for c in kg.chapters],
            "sections": [s.model_dump() for s in kg.sections],
            "text_chunks": [t.model_dump() for t in kg.text_chunks]
        },
        "knowledge_layer": {
            "nodes": kg.knowledge_nodes  # 已经是字典格式
        },
        "relationships": [r.model_dump() for r in kg.relationships]
    }
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    # 同时保存一份扁平化格式 (方便导入 Neo4j)
    flat_output_file = OUTPUT_FILE.replace('.json', '_flat.json')
    flat_data = {
        "nodes": [],
        "relationships": output_data["relationships"]
    }
    
    # 合并所有节点
    if kg.course:
        flat_data["nodes"].append(kg.course.model_dump())
    flat_data["nodes"].extend([c.model_dump() for c in kg.chapters])
    flat_data["nodes"].extend([s.model_dump() for s in kg.sections])
    flat_data["nodes"].extend([t.model_dump() for t in kg.text_chunks])
    flat_data["nodes"].extend(kg.knowledge_nodes)
    
    with open(flat_output_file, 'w', encoding='utf-8') as f:
        json.dump(flat_data, f, ensure_ascii=False, indent=2)
    
    print(f"💾 扁平化格式保存到: {flat_output_file}")
    print("\n" + "=" * 60)
    print("✅ 知识图谱构建完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
