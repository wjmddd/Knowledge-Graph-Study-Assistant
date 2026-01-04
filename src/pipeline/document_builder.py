"""
文档结构层构建器
自动从 Markdown 结构生成 Course -> Chapter -> Section -> TextChunk 节点和关系
"""

import re
from typing import List, Tuple, Dict
from src.models.schema import (
    CourseNode, ChapterNode, SectionNode, TextChunkNode,
    GraphRelationship, FullKnowledgeGraph
)
from src.pipeline.parser import ContextChunk


def generate_id(prefix: str, name: str) -> str:
    """
    生成节点 ID
    格式: {prefix}_{英文或拼音}
    """
    # 简单处理：移除特殊字符，空格转下划线
    clean_name = re.sub(r'[^\w\s]', '', name)
    clean_name = clean_name.replace(' ', '_').lower()
    # 如果是纯中文，用拼音或序号
    if not clean_name or clean_name.isdigit():
        clean_name = name.replace(' ', '_')
    return f"{prefix}_{clean_name}"


def build_document_structure(
    chunks: List[ContextChunk],
    course_name: str = "计算机系统基础"
) -> Tuple[FullKnowledgeGraph, Dict[int, str]]:
    """
    从解析后的 ContextChunk 构建文档结构层
    
    Args:
        chunks: 解析后的文本块列表
        course_name: 课程名称
    
    Returns:
        - FullKnowledgeGraph: 包含文档结构层的图谱
        - chunk_id_map: {chunk_index: text_chunk_id} 映射，用于后续建立 MENTIONS 关系
    """
    kg = FullKnowledgeGraph()
    relationships = []
    chunk_id_map = {}  # chunk索引 -> TextChunk节点ID
    
    # 用于去重
    seen_chapters = {}  # chapter_title -> chapter_id
    seen_sections = {}  # section_title -> section_id
    
    # 1. 创建课程节点
    course_id = generate_id("course", course_name)
    kg.course = CourseNode(id=course_id, name=course_name)
    
    # 2. 遍历所有 chunk，提取章节信息
    for idx, chunk in enumerate(chunks):
        chapter_title = chunk.metadata.get("chapter", "未知章节")
        section_title = chunk.metadata.get("section", "未知小节")
        
        # --- 处理 Chapter ---
        if chapter_title not in seen_chapters:
            # 提取章节序号 (如 "第1章 计算机系统概述" -> 1)
            chapter_match = re.search(r'第(\d+)章', chapter_title)
            chapter_num = int(chapter_match.group(1)) if chapter_match else len(seen_chapters) + 1
            
            chapter_id = generate_id("chapter", f"ch{chapter_num}")
            chapter_node = ChapterNode(
                id=chapter_id,
                title=chapter_title,
                number=chapter_num
            )
            kg.chapters.append(chapter_node)
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
            # 提取节序号 (如 "1.2 计算机基本工作原理" -> "1.2")
            section_match = re.match(r'^(\d+\.\d+)', section_title)
            section_num = section_match.group(1) if section_match else f"{len(seen_sections) + 1}"
            
            section_id = generate_id("section", section_num.replace('.', '_'))
            section_node = SectionNode(
                id=section_id,
                title=section_title,
                number=section_num
            )
            kg.sections.append(section_node)
            seen_sections[section_key] = section_id
            
            # Chapter -> CONTAINS -> Section
            relationships.append(GraphRelationship(
                source_id=chapter_id,
                target_id=section_id,
                type="CONTAINS",
                properties={"order": float(section_num) if section_match else len(seen_sections)}
            ))
        
        section_id = seen_sections[section_key]
        
        # --- 处理 TextChunk ---
        chunk_id = f"chunk_{idx + 1:03d}"  # chunk_001, chunk_002, ...
        chunk_node = TextChunkNode(
            id=chunk_id,
            content=chunk.content[:500] + "..." if len(chunk.content) > 500 else chunk.content,  # 截断长内容
            chunk_index=idx,
            char_count=len(chunk.content)
        )
        kg.text_chunks.append(chunk_node)
        chunk_id_map[idx] = chunk_id
        
        # Section -> CONTAINS -> TextChunk
        relationships.append(GraphRelationship(
            source_id=section_id,
            target_id=chunk_id,
            type="CONTAINS",
            properties={"order": idx}
        ))
    
    kg.relationships = relationships
    
    print(f"📚 文档结构层构建完成:")
    print(f"   - 课程: 1 个")
    print(f"   - 章: {len(kg.chapters)} 个")
    print(f"   - 节: {len(kg.sections)} 个")
    print(f"   - 文本块: {len(kg.text_chunks)} 个")
    print(f"   - CONTAINS 关系: {len(relationships)} 条")
    
    return kg, chunk_id_map


def create_mentions_relationships(
    chunk_id_map: Dict[int, str],
    extraction_results: List[dict],
    chunks: List[ContextChunk]
) -> List[GraphRelationship]:
    """
    创建 TextChunk -> MENTIONS -> 知识节点 的关系
    
    Args:
        chunk_id_map: {chunk_index: text_chunk_id} 映射
        extraction_results: 每个 chunk 的 LLM 提取结果列表
        chunks: 原始文本块列表 (用于获取索引)
    
    Returns:
        MENTIONS 关系列表
    """
    mentions_relationships = []
    
    for idx, result in enumerate(extraction_results):
        if result is None:
            continue
            
        chunk_id = chunk_id_map.get(idx)
        if not chunk_id:
            continue
        
        # 为该 chunk 提取出的每个知识节点创建 MENTIONS 关系
        for node in result.get("nodes", []):
            node_id = node.get("id")
            if node_id:
                mentions_relationships.append(GraphRelationship(
                    source_id=chunk_id,
                    target_id=node_id,
                    type="MENTIONS",
                    properties={"source_chunk_index": idx}
                ))
    
    print(f"🔗 MENTIONS 关系创建完成: {len(mentions_relationships)} 条")
    return mentions_relationships

