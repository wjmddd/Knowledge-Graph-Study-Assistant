"""
合并所有章节的知识图谱数据
将 data/chapters/chapter_XX.json 合并为完整的图谱文件

用法: python scripts/merge_chapters.py
"""

import sys
import json
import re
from pathlib import Path

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pipeline.parser import parse_markdown_with_context
from src.models.schema import (
    CourseNode, ChapterNode, SectionNode, TextChunkNode, GraphRelationship
)

# ========== 配置 ==========
MD_DIR = Path("md")
CHAPTERS_DIR = Path("data/chapters")
OUTPUT_FILE = "graph_data_all.json"
OUTPUT_FLAT_FILE = "graph_data_all_flat.json"
COURSE_NAME = "计算机系统基础"
# ==========================


def get_chapter_num(file_name: str) -> int:
    """从文件名提取章节号"""
    ch_map = {"一":1,"二":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9,"十":10}
    match = re.search(r'第(.+?)章', file_name)
    if match:
        return ch_map.get(match.group(1), 0)
    # 尝试从 chapter_XX.json 格式提取
    match = re.search(r'chapter_(\d+)', file_name)
    if match:
        return int(match.group(1))
    return 0


def build_document_structure():
    """
    重建文档结构层
    """
    course_id = "course_computer_system"
    course = CourseNode(id=course_id, name=COURSE_NAME)
    
    chapters = []
    sections = []
    text_chunks = []
    doc_relationships = []
    chunk_id_map = {}  # (file_name, local_idx) -> chunk_id
    
    seen_chapters = {}
    seen_sections = {}
    global_chunk_idx = 0
    
    # 扫描所有 MD 文件
    md_files = sorted(MD_DIR.glob("*.md"), key=lambda x: get_chapter_num(x.name))
    
    for md_file in md_files:
        chunks = parse_markdown_with_context(str(md_file))
        
        for local_idx, chunk in enumerate(chunks):
            chapter_title = chunk.metadata.get("chapter", "未知章节")
            section_title = chunk.metadata.get("section", "未知小节")
            
            # 处理 Chapter
            if chapter_title not in seen_chapters:
                ch_map = {"一":1,"二":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9,"十":10}
                ch_match = re.search(r'第(.+?)章', chapter_title)
                chapter_num = ch_map.get(ch_match.group(1), len(seen_chapters)+1) if ch_match else len(seen_chapters)+1
                
                chapter_id = f"chapter_{chapter_num}"
                chapter_node = ChapterNode(id=chapter_id, title=chapter_title, number=chapter_num)
                chapters.append(chapter_node)
                seen_chapters[chapter_title] = chapter_id
                
                doc_relationships.append(GraphRelationship(
                    source_id=course_id, target_id=chapter_id,
                    type="CONTAINS", properties={"order": chapter_num}
                ))
            
            chapter_id = seen_chapters[chapter_title]
            
            # 处理 Section
            section_key = f"{chapter_title}::{section_title}"
            if section_key not in seen_sections:
                section_match = re.match(r'^(\d+\.\d+)', section_title)
                section_num = section_match.group(1) if section_match else f"{len(seen_sections)+1}"
                
                section_id = f"section_{section_num.replace('.', '_')}"
                section_node = SectionNode(id=section_id, title=section_title, number=section_num)
                sections.append(section_node)
                seen_sections[section_key] = section_id
                
                doc_relationships.append(GraphRelationship(
                    source_id=chapter_id, target_id=section_id,
                    type="CONTAINS", properties={"order": float(section_num.split('.')[1]) if '.' in section_num else len(seen_sections)}
                ))
            
            section_id = seen_sections[section_key]
            
            # 处理 TextChunk
            chunk_id = f"chunk_{global_chunk_idx:04d}"
            chunk_node = TextChunkNode(
                id=chunk_id,
                content=chunk.content[:500] + "..." if len(chunk.content) > 500 else chunk.content,
                chunk_index=global_chunk_idx,
                char_count=len(chunk.content)
            )
            text_chunks.append(chunk_node)
            chunk_id_map[(md_file.name, local_idx)] = chunk_id
            
            doc_relationships.append(GraphRelationship(
                source_id=section_id, target_id=chunk_id,
                type="CONTAINS", properties={"order": global_chunk_idx}
            ))
            
            global_chunk_idx += 1
    
    return course, chapters, sections, text_chunks, doc_relationships, chunk_id_map


def merge_knowledge_layers():
    """
    合并所有章节的知识语义层数据
    """
    all_nodes = []
    all_relationships = []
    
    chapter_files = sorted(CHAPTERS_DIR.glob("chapter_*.json"))
    
    print(f"📂 找到 {len(chapter_files)} 个章节文件:")
    
    for cf in chapter_files:
        with open(cf, 'r', encoding='utf-8') as f:
            chapter_data = json.load(f)
        
        nodes = chapter_data.get("nodes", [])
        rels = chapter_data.get("relationships", [])
        
        all_nodes.extend(nodes)
        all_relationships.extend(rels)
        
        chapter_name = chapter_data.get("metadata", {}).get("chapter_name", cf.stem)
        print(f"   - {cf.name}: {len(nodes)} 节点, {len(rels)} 关系")
    
    return all_nodes, all_relationships


def create_mentions_relationships(chunk_id_map, knowledge_nodes):
    """
    创建 MENTIONS 关系
    这里简化处理：为每个章节文件中的节点创建与对应 TextChunk 的关系
    """
    mentions = []
    
    # 按章节分组节点
    chapter_files = sorted(CHAPTERS_DIR.glob("chapter_*.json"))
    
    for cf in chapter_files:
        chapter_num = get_chapter_num(cf.name)
        
        # 找到该章对应的 MD 文件
        ch_map_rev = {1:"一",2:"二",3:"三",4:"四",5:"五",6:"六",7:"七",8:"八",9:"九",10:"十"}
        md_name = f"第{ch_map_rev.get(chapter_num, chapter_num)}章.md"
        
        with open(cf, 'r', encoding='utf-8') as f:
            chapter_data = json.load(f)
        
        # 获取该章的所有节点
        nodes = chapter_data.get("nodes", [])
        
        # 找到该章对应的所有 chunk
        chapter_chunks = [(fn, idx, cid) for (fn, idx), cid in chunk_id_map.items() if fn == md_name]
        
        if chapter_chunks and nodes:
            # 简单策略：将节点平均分配给各个 chunk
            nodes_per_chunk = max(1, len(nodes) // len(chapter_chunks))
            
            for i, node in enumerate(nodes):
                chunk_idx = min(i // nodes_per_chunk, len(chapter_chunks) - 1)
                _, _, chunk_id = chapter_chunks[chunk_idx]
                
                mentions.append(GraphRelationship(
                    source_id=chunk_id,
                    target_id=node.get("id"),
                    type="MENTIONS",
                    properties={}
                ))
    
    return mentions


def main():
    print("=" * 60)
    print("📑 合并所有章节知识图谱数据")
    print("=" * 60)
    
    # 1. 检查章节目录
    if not CHAPTERS_DIR.exists():
        print(f"❌ 章节目录不存在: {CHAPTERS_DIR}")
        return
    
    # 2. 重建文档结构层
    print("\n📚 重建文档结构层...")
    course, chapters, sections, text_chunks, doc_relationships, chunk_id_map = build_document_structure()
    
    print(f"   - 课程: 1 个")
    print(f"   - 章: {len(chapters)} 个")
    print(f"   - 节: {len(sections)} 个")
    print(f"   - 文本块: {len(text_chunks)} 个")
    print(f"   - CONTAINS 关系: {len(doc_relationships)} 条")
    
    # 3. 合并知识语义层
    print("\n🧠 合并知识语义层...")
    knowledge_nodes, knowledge_relationships = merge_knowledge_layers()
    print(f"   总计: {len(knowledge_nodes)} 节点, {len(knowledge_relationships)} 关系")
    
    # 4. 创建 MENTIONS 关系
    print("\n🔗 创建 MENTIONS 关系...")
    mentions_relationships = create_mentions_relationships(chunk_id_map, knowledge_nodes)
    print(f"   MENTIONS: {len(mentions_relationships)} 条")
    
    # 5. 汇总统计
    total_nodes = 1 + len(chapters) + len(sections) + len(text_chunks) + len(knowledge_nodes)
    total_relationships = len(doc_relationships) + len(knowledge_relationships) + len(mentions_relationships)
    
    print("\n" + "=" * 60)
    print("📊 合并统计")
    print("=" * 60)
    print(f"📦 节点总计: {total_nodes} 个")
    print(f"   - 文档结构层: {1 + len(chapters) + len(sections) + len(text_chunks)}")
    print(f"   - 知识语义层: {len(knowledge_nodes)}")
    print(f"🔗 关系总计: {total_relationships} 条")
    print(f"   - CONTAINS: {len(doc_relationships)}")
    print(f"   - MENTIONS: {len(mentions_relationships)}")
    print(f"   - 知识关系: {len(knowledge_relationships)}")
    
    # 6. 保存结果
    print(f"\n💾 保存结果...")
    
    # 分层格式
    final_data = {
        "metadata": {
            "course_name": COURSE_NAME,
            "total_chapters": len(chapters),
            "total_sections": len(sections),
            "total_chunks": len(text_chunks),
            "total_knowledge_nodes": len(knowledge_nodes),
            "total_relationships": total_relationships
        },
        "document_layer": {
            "course": course.model_dump(),
            "chapters": [c.model_dump() for c in chapters],
            "sections": [s.model_dump() for s in sections],
            "text_chunks": [t.model_dump() for t in text_chunks]
        },
        "knowledge_layer": {
            "nodes": knowledge_nodes
        },
        "relationships": [r.model_dump() for r in doc_relationships] + \
                        knowledge_relationships + \
                        [r.model_dump() for r in mentions_relationships]
    }
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
    print(f"   分层格式: {OUTPUT_FILE}")
    
    # 扁平化格式
    flat_data = {
        "nodes": [course.model_dump()],
        "relationships": final_data["relationships"]
    }
    flat_data["nodes"].extend([c.model_dump() for c in chapters])
    flat_data["nodes"].extend([s.model_dump() for s in sections])
    flat_data["nodes"].extend([t.model_dump() for t in text_chunks])
    flat_data["nodes"].extend(knowledge_nodes)
    
    with open(OUTPUT_FLAT_FILE, 'w', encoding='utf-8') as f:
        json.dump(flat_data, f, ensure_ascii=False, indent=2)
    print(f"   扁平格式: {OUTPUT_FLAT_FILE}")
    
    print("\n" + "=" * 60)
    print("✅ 合并完成!")
    print("=" * 60)
    print("\n🎯 下一步:")
    print("   1. (可选) 去重: python scripts/llm_deduplicate.py")
    print("   2. 导入 Neo4j: python scripts/import_to_neo4j.py")


if __name__ == "__main__":
    main()

