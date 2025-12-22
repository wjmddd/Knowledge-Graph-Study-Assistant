"""
文档解析模块
直接从原 pipeline.py 提取
"""

import re
from typing import List, Dict
from pydantic import BaseModel, Field


class ContextChunk(BaseModel):
    """
    带有层级上下文的文本块
    """
    content: str
    metadata: Dict[str, str] = Field(
        default_factory=lambda: {"chapter": "未知", "section": "前言"}
    )

    def to_prompt(self) -> str:
        """生成带上下文的 Prompt"""
        return f"""
        [上下文信息]
        所属章节: {self.metadata.get('chapter', '未知')}
        所属小节: {self.metadata.get('section', '未知')}
        
        [待分析文本]
        {self.content}
        """


def parse_markdown_with_context(file_path: str) -> List[ContextChunk]:
    """
    解析 Markdown，按章节切分，并注入层级上下文
    """
    chunks = []
    
    current_chapter = "第1章 计算机系统概述"  # 默认初始章节
    current_section = "概述"
    buffer = []
    
    # 正则匹配标题: # 1.1 或 # 第1章
    chapter_pattern = re.compile(r'^#\s+第.+章')
    section_pattern = re.compile(r'^#\s+\d+\.\d+')
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # 检查是否是新标题
        is_chapter = chapter_pattern.match(line)
        is_section = section_pattern.match(line)
        
        if line.startswith('#') and (is_chapter or is_section):
            # 1. 保存上一个缓冲区的内容（如果非空）
            if buffer:
                full_text = "\n".join(buffer)
                chunks.append(ContextChunk(
                    content=full_text,
                    metadata={
                        "chapter": current_chapter,
                        "section": current_section
                    }
                ))
                buffer = []
            
            # 2. 更新上下文指针
            if is_chapter:
                current_chapter = line.replace('#', '').strip()
                current_section = "概述"  # 重置小节
            elif is_section:
                current_section = line.replace('#', '').strip()
                
        else:
            # 普通文本，加入缓冲区
            buffer.append(line)
            
    # 处理文件末尾的最后一块
    if buffer:
        chunks.append(ContextChunk(
            content="\n".join(buffer),
            metadata={"chapter": current_chapter, "section": current_section}
        ))
        
    return chunks
