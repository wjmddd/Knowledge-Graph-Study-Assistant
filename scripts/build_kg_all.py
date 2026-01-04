"""
批量构建知识图谱 - 处理所有章节
扫描 md/ 目录下的所有 Markdown 文件，构建完整的知识图谱

用法: python scripts/build_kg_all.py
"""

import sys
import json
import time
import re
from pathlib import Path
from typing import List, Dict

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent))

import instructor
from openai import OpenAI

from config.settings import CLIENT_CONFIG, REQUEST_DELAY
from src.pipeline.parser import parse_markdown_with_context, ContextChunk
from src.pipeline.extractor import process_single_chunk
from src.pipeline.document_builder import build_document_structure, create_mentions_relationships
from src.models.schema import (
    CourseNode, ChapterNode, SectionNode, TextChunkNode,
    GraphRelationship, FullKnowledgeGraph
)

# ========== 配置 ==========
MD_DIR = Path("md")  # Markdown 文件目录
OUTPUT_DIR = Path("data/chapters")  # 每章单独输出目录
OUTPUT_FILE = "graph_data_all.json"  # 合并后的输出文件
OUTPUT_FLAT_FILE = "graph_data_all_flat.json"  # 扁平化输出
COURSE_NAME = "计算机系统基础"
# ==========================


def get_chapter_files() -> List[Path]:
    """
    获取所有章节文件，按章节顺序排序
    """
    md_files = list(MD_DIR.glob("*.md"))
    
    # 按章节序号排序
    def get_chapter_num(path: Path) -> int:
        # 从文件名提取章节号: "第一章.md" -> 1, "第二章.md" -> 2
        name = path.stem
        chapter_map = {
            "一": 1, "二": 2, "三": 3, "四": 4,
            "五": 5, "六": 6, "七": 7, "八": 8,
            "九": 9, "十": 10
        }
        match = re.search(r'第(.+)章', name)
        if match:
            ch = match.group(1)
            return chapter_map.get(ch, 99)
        return 99
    
    md_files.sort(key=get_chapter_num)
    return md_files


def parse_all_chapters(md_files: List[Path]) -> Dict[str, List[ContextChunk]]:
    """
    解析所有章节文件
    返回: {文件名: [ContextChunk列表]}
    """
    all_chunks = {}
    
    for md_file in md_files:
        print(f"   📖 解析: {md_file.name}...")
        chunks = parse_markdown_with_context(str(md_file))
        all_chunks[md_file.name] = chunks
        print(f"      → {len(chunks)} 个文本块")
    
    return all_chunks


def build_full_document_structure(
    all_chunks: Dict[str, List[ContextChunk]]
) -> tuple:
    """
    构建完整的文档结构层（包含所有章节）
    """
    # 课程节点
    course_id = "course_computer_system"
    course = CourseNode(id=course_id, name=COURSE_NAME)
    
    chapters = []
    sections = []
    text_chunks = []
    relationships = []
    chunk_id_map = {}  # (文件名, 块索引) -> chunk_id
    
    global_chunk_idx = 0
    seen_chapters = {}
    seen_sections = {}
    
    for file_name, chunks in all_chunks.items():
        for local_idx, chunk in enumerate(chunks):
            chapter_title = chunk.metadata.get("chapter", "未知章节")
            section_title = chunk.metadata.get("section", "未知小节")
            
            # --- 处理 Chapter ---
            if chapter_title not in seen_chapters:
                chapter_match = re.search(r'第(\d+)章', chapter_title)
                if not chapter_match:
                    # 尝试中文数字
                    ch_map = {"一":1,"二":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9,"十":10}
                    ch_match = re.search(r'第(.+?)章', chapter_title)
                    chapter_num = ch_map.get(ch_match.group(1), len(seen_chapters)+1) if ch_match else len(seen_chapters)+1
                else:
                    chapter_num = int(chapter_match.group(1))
                
                chapter_id = f"chapter_{chapter_num}"
                chapter_node = ChapterNode(
                    id=chapter_id,
                    title=chapter_title,
                    number=chapter_num
                )
                chapters.append(chapter_node)
                seen_chapters[chapter_title] = chapter_id
                
                # Course -> CONTAINS -> Chapter
                relationships.append(GraphRelationship(
                    source_id=course_id,
                    target_id=chapter_id,
                    type="CONTAINS",
                    properties={"order": chapter_num}
                ))
            
            chapter_id = seen_chapters[chapter_title]
            
            # --- 处理 Section ---
            section_key = f"{chapter_title}::{section_title}"
            if section_key not in seen_sections:
                section_match = re.match(r'^(\d+\.\d+)', section_title)
                section_num = section_match.group(1) if section_match else f"{len(seen_sections)+1}"
                
                section_id = f"section_{section_num.replace('.', '_')}"
                section_node = SectionNode(
                    id=section_id,
                    title=section_title,
                    number=section_num
                )
                sections.append(section_node)
                seen_sections[section_key] = section_id
                
                # Chapter -> CONTAINS -> Section
                relationships.append(GraphRelationship(
                    source_id=chapter_id,
                    target_id=section_id,
                    type="CONTAINS",
                    properties={"order": float(section_num.split('.')[1]) if '.' in section_num else len(seen_sections)}
                ))
            
            section_id = seen_sections[section_key]
            
            # --- 处理 TextChunk ---
            chunk_id = f"chunk_{global_chunk_idx:04d}"
            chunk_node = TextChunkNode(
                id=chunk_id,
                content=chunk.content[:500] + "..." if len(chunk.content) > 500 else chunk.content,
                chunk_index=global_chunk_idx,
                char_count=len(chunk.content)
            )
            text_chunks.append(chunk_node)
            chunk_id_map[(file_name, local_idx)] = chunk_id
            
            # Section -> CONTAINS -> TextChunk
            relationships.append(GraphRelationship(
                source_id=section_id,
                target_id=chunk_id,
                type="CONTAINS",
                properties={"order": global_chunk_idx}
            ))
            
            global_chunk_idx += 1
    
    return course, chapters, sections, text_chunks, relationships, chunk_id_map


def save_results(kg_data: dict, output_file: str, flat_file: str = None):
    """保存结果到文件"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(kg_data, f, ensure_ascii=False, indent=2)
    
    # 扁平化格式（可选）
    if flat_file:
        flat_data = {
            "nodes": kg_data.get("document_layer", {}).get("course") and [kg_data["document_layer"]["course"]] or [],
            "relationships": kg_data.get("relationships", [])
        }
        if "document_layer" in kg_data:
            flat_data["nodes"].extend(kg_data["document_layer"].get("chapters", []))
            flat_data["nodes"].extend(kg_data["document_layer"].get("sections", []))
            flat_data["nodes"].extend(kg_data["document_layer"].get("text_chunks", []))
        if "knowledge_layer" in kg_data:
            flat_data["nodes"].extend(kg_data["knowledge_layer"].get("nodes", []))
        # 简化格式（单章）
        if "nodes" in kg_data and "document_layer" not in kg_data:
            flat_data["nodes"] = kg_data["nodes"]
        
        with open(flat_file, 'w', encoding='utf-8') as f:
            json.dump(flat_data, f, ensure_ascii=False, indent=2)


def save_chapter_result(
    chapter_name: str,
    chapter_num: int,
    knowledge_nodes: list,
    knowledge_relationships: list,
    chunk_count: int,
    extraction_results: dict,
    output_dir: Path
):
    """
    保存单章的提取结果
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    chapter_data = {
        "metadata": {
            "chapter_name": chapter_name,
            "chapter_number": chapter_num,
            "chunk_count": chunk_count,
            "node_count": len(knowledge_nodes),
            "relationship_count": len(knowledge_relationships)
        },
        "nodes": knowledge_nodes,
        "relationships": knowledge_relationships
    }
    
    # 保存单章文件
    output_file = output_dir / f"chapter_{chapter_num:02d}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(chapter_data, f, ensure_ascii=False, indent=2)
    
    return output_file


def merge_all_chapters(output_dir: Path) -> dict:
    """
    合并所有章节的提取结果
    """
    all_nodes = []
    all_relationships = []
    
    chapter_files = sorted(output_dir.glob("chapter_*.json"))
    
    for cf in chapter_files:
        with open(cf, 'r', encoding='utf-8') as f:
            chapter_data = json.load(f)
        all_nodes.extend(chapter_data.get("nodes", []))
        all_relationships.extend(chapter_data.get("relationships", []))
    
    return {
        "nodes": all_nodes,
        "relationships": all_relationships
    }


def main():
    print("=" * 70)
    print("🏗️  批量知识图谱构建 - 全部章节")
    print("=" * 70)
    print(f"📂 输入目录: {MD_DIR}")
    print(f"📡 使用模型: {CLIENT_CONFIG['model']}")
    print(f"🔗 API 地址: {CLIENT_CONFIG['base_url']}")
    print("=" * 70)
    
    # ========================================
    # 阶段 1: 扫描文件
    # ========================================
    print("\n📁 阶段 1: 扫描 Markdown 文件...")
    md_files = get_chapter_files()
    
    if not md_files:
        print(f"❌ 未找到 Markdown 文件，请检查 {MD_DIR} 目录")
        return
    
    print(f"   找到 {len(md_files)} 个文件:")
    for f in md_files:
        print(f"   - {f.name}")
    
    # ========================================
    # 阶段 2: 解析所有文件
    # ========================================
    print("\n📖 阶段 2: 解析所有章节...")
    all_chunks = parse_all_chapters(md_files)
    
    total_chunks = sum(len(chunks) for chunks in all_chunks.values())
    print(f"   ✓ 总计 {total_chunks} 个文本块")
    
    # ========================================
    # 阶段 3: 构建文档结构层
    # ========================================
    print("\n📚 阶段 3: 构建文档结构层...")
    course, chapters, sections, text_chunks, doc_relationships, chunk_id_map = \
        build_full_document_structure(all_chunks)
    
    print(f"   - 课程: 1 个 ({course.name})")
    print(f"   - 章: {len(chapters)} 个")
    print(f"   - 节: {len(sections)} 个")
    print(f"   - 文本块: {len(text_chunks)} 个")
    print(f"   - CONTAINS 关系: {len(doc_relationships)} 条")
    
    # ========================================
    # 阶段 4: LLM 提取知识语义层
    # ========================================
    print(f"\n🤖 阶段 4: LLM 提取知识语义层...")
    print(f"   ⚠️  预计耗时较长，共 {total_chunks} 个文本块")
    print(f"   💡 每章单独保存到 {OUTPUT_DIR}/\n")
    
    # 创建输出目录
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    client = instructor.from_openai(
        OpenAI(base_url=CLIENT_CONFIG["base_url"], api_key=CLIENT_CONFIG["api_key"]),
        mode=instructor.Mode.JSON
    )
    
    all_knowledge_nodes = []
    all_knowledge_relationships = []
    all_extraction_results = {}  # (file_name, local_idx) -> result
    failed_chunks = []
    
    start_time = time.time()
    processed_count = 0
    
    for file_idx, (file_name, chunks) in enumerate(all_chunks.items()):
        # 提取章节序号
        ch_map = {"一":1,"二":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9,"十":10}
        ch_match = re.search(r'第(.+?)章', file_name)
        chapter_num = ch_map.get(ch_match.group(1), file_idx+1) if ch_match else file_idx+1
        
        print(f"\n   📘 [{file_idx+1}/{len(all_chunks)}] 处理: {file_name} (第{chapter_num}章)")
        chapter_start = time.time()
        
        # 本章的提取结果
        chapter_nodes = []
        chapter_relationships = []
        
        for local_idx, chunk in enumerate(chunks):
            processed_count += 1
            progress = f"[{processed_count}/{total_chunks}]"
            section_name = chunk.metadata['section'][:25]
            print(f"      {progress} {section_name}...", end=" ", flush=True)
            
            try:
                data = process_single_chunk(chunk, client)
                
                if data:
                    all_extraction_results[(file_name, local_idx)] = data
                    # 添加到本章结果
                    chapter_nodes.extend(data.get("nodes", []))
                    chapter_relationships.extend(data.get("relationships", []))
                    # 添加到总结果
                    all_knowledge_nodes.extend(data.get("nodes", []))
                    all_knowledge_relationships.extend(data.get("relationships", []))
                    print(f"✓ 节点:{len(data.get('nodes', []))} 关系:{len(data.get('relationships', []))}")
                else:
                    all_extraction_results[(file_name, local_idx)] = None
                    failed_chunks.append((file_name, local_idx, chunk))
                    print("✗ 失败")
                    
            except Exception as exc:
                print(f"✗ 异常: {str(exc)[:40]}")
                all_extraction_results[(file_name, local_idx)] = None
                failed_chunks.append((file_name, local_idx, chunk))
            
            time.sleep(REQUEST_DELAY)
        
        chapter_duration = time.time() - chapter_start
        
        # 保存本章结果
        chapter_file = save_chapter_result(
            chapter_name=file_name.replace('.md', ''),
            chapter_num=chapter_num,
            knowledge_nodes=chapter_nodes,
            knowledge_relationships=chapter_relationships,
            chunk_count=len(chunks),
            extraction_results={k: v for k, v in all_extraction_results.items() if k[0] == file_name},
            output_dir=OUTPUT_DIR
        )
        
        print(f"      ✓ {file_name} 完成! 耗时: {chapter_duration:.1f}秒")
        print(f"      💾 已保存: {chapter_file}")
        print(f"         节点: {len(chapter_nodes)} 个, 关系: {len(chapter_relationships)} 条")
    
    total_duration = time.time() - start_time
    
    # ========================================
    # 阶段 4.5: 合并所有章节
    # ========================================
    print(f"\n📑 合并所有章节结果...")
    merged_knowledge = merge_all_chapters(OUTPUT_DIR)
    print(f"   ✓ 合并完成: {len(merged_knowledge['nodes'])} 个节点, {len(merged_knowledge['relationships'])} 条关系")
    
    # ========================================
    # 阶段 5: 创建 MENTIONS 关系
    # ========================================
    print(f"\n🔗 阶段 5: 创建 MENTIONS 关系...")
    mentions_relationships = []
    for (fn, idx), result in all_extraction_results.items():
        if result is None:
            continue
        chunk_id = chunk_id_map.get((fn, idx))
        if not chunk_id:
            continue
        for node in result.get("nodes", []):
            node_id = node.get("id")
            if node_id:
                mentions_relationships.append(GraphRelationship(
                    source_id=chunk_id,
                    target_id=node_id,
                    type="MENTIONS",
                    properties={}
                ))
    
    print(f"   ✓ MENTIONS 关系: {len(mentions_relationships)} 条")
    
    # ========================================
    # 阶段 6: 统计与保存
    # ========================================
    print("\n" + "=" * 70)
    print("📊 构建统计")
    print("=" * 70)
    
    doc_layer_count = 1 + len(chapters) + len(sections) + len(text_chunks)
    knowledge_layer_count = len(all_knowledge_nodes)
    total_relationships = len(doc_relationships) + len(all_knowledge_relationships) + len(mentions_relationships)
    
    print(f"📚 文档结构层: {doc_layer_count} 个节点")
    print(f"   - Course: 1")
    print(f"   - Chapter: {len(chapters)}")
    print(f"   - Section: {len(sections)}")
    print(f"   - TextChunk: {len(text_chunks)}")
    
    print(f"\n🧠 知识语义层: {knowledge_layer_count} 个节点")
    
    print(f"\n🔗 关系统计: {total_relationships} 条")
    print(f"   - CONTAINS: {len(doc_relationships)}")
    print(f"   - MENTIONS: {len(mentions_relationships)}")
    print(f"   - 知识关系: {len(all_knowledge_relationships)}")
    
    print(f"\n⏱️  总耗时: {total_duration/60:.1f} 分钟")
    
    if failed_chunks:
        print(f"\n⚠️  失败的块: {len(failed_chunks)} 个")
        # 保存失败列表
        failed_file = "failed_chunks.json"
        with open(failed_file, 'w', encoding='utf-8') as f:
            json.dump([
                {"file": fn, "index": idx, "section": chunk.metadata.get("section")}
                for fn, idx, chunk in failed_chunks
            ], f, ensure_ascii=False, indent=2)
        print(f"   详情已保存到: {failed_file}")
    
    # 最终保存
    final_data = {
        "metadata": {
            "course_name": COURSE_NAME,
            "total_chapters": len(chapters),
            "total_sections": len(sections),
            "total_chunks": len(text_chunks),
            "total_knowledge_nodes": knowledge_layer_count,
            "total_relationships": total_relationships,
            "failed_chunks": len(failed_chunks),
            "build_time_minutes": round(total_duration/60, 2)
        },
        "document_layer": {
            "course": course.model_dump(),
            "chapters": [c.model_dump() for c in chapters],
            "sections": [s.model_dump() for s in sections],
            "text_chunks": [t.model_dump() for t in text_chunks]
        },
        "knowledge_layer": {
            "nodes": all_knowledge_nodes
        },
        "relationships": [r.model_dump() for r in doc_relationships] + \
                        all_knowledge_relationships + \
                        [r.model_dump() for r in mentions_relationships]
    }
    
    print(f"\n💾 保存结果...")
    save_results(final_data, OUTPUT_FILE, OUTPUT_FLAT_FILE)
    print(f"   分层格式: {OUTPUT_FILE}")
    print(f"   扁平格式: {OUTPUT_FLAT_FILE}")
    
    print("\n" + "=" * 70)
    print("✅ 全部章节知识图谱构建完成!")
    print("=" * 70)


if __name__ == "__main__":
    main()

