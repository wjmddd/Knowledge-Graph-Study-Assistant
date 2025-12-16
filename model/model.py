from typing import List, Optional, Union, Literal
from pydantic import BaseModel, Field, HttpUrl
from enum import Enum
from datetime import datetime

# ==========================================
# 1. 枚举定义 (对应 2.1 和 2.2 节)
# ==========================================

class NodeType(str, Enum):
    """对应 2.1 核心节点设计"""
    # A. 文档结构层
    COURSE = "Course"
    CHAPTER = "Chapter"
    SECTION = "Section"
    TEXT_CHUNK = "TextChunk"
    
    # B. 知识语义层
    CONCEPT = "Concept"
    HARDWARE = "Hardware"
    INSTRUCTION = "Instruction"
    CODE_SNIPPET = "CodeSnippet"
    PRINCIPLE = "Principle"

class RelationType(str, Enum):
    """对应 2.2 核心关系设计"""
    # A. 层级与包含关系
    CONTAINS = "CONTAINS"       # Course->Chapter->Section->TextChunk
    MENTIONS = "MENTIONS"       # TextChunk->Concept
    
    # B. 知识逻辑关系
    DEPENDS_ON = "DEPENDS_ON"       # 学习 B 之前必须懂 A
    IS_A = "IS_A"                   # 分类关系 (SRAM is a 存储器)
    COMPOSED_OF = "COMPOSED_OF"     # 组成关系 (CPU composed of ALU)
    IMPLEMENTED_BY = "IMPLEMENTED_BY" # 实现关系 (加法 implemented by 加法器)
    EXAMPLE_OF = "EXAMPLE_OF"       # 举例关系 (代码 example of 缓冲区溢出)
    OPERATES_ON = "OPERATES_ON"     # (补充 2.3 图解) 指令操作概念
    USES = "USES"                   # (补充 2.3 图解) 代码使用指令

# ==========================================
# 2. 基础模型类
# ==========================================

class GraphNode(BaseModel):
    """所有节点的基类"""
    id: str = Field(..., description="全局唯一标识符")
    label: NodeType = Field(..., description="节点类型标签")

class GraphRelationship(BaseModel):
    """对应 2.2 的关系定义"""
    source_id: str = Field(..., description="起始节点ID")
    target_id: str = Field(..., description="目标节点ID")
    type: RelationType = Field(..., description="关系类型")
    properties: Optional[dict] = Field(default={}, description="关系的额外属性，如 weight")

# ==========================================
# 3. 具体节点模型 (对应 2.4 具体属性设计)
# ==========================================

# --- A. 文档结构层节点 ---

class CourseNode(GraphNode):
    label: Literal[NodeType.COURSE] = NodeType.COURSE
    name: str = Field(..., description="课程名称，如 '计算机系统基础'")

class ChapterNode(GraphNode):
    label: Literal[NodeType.CHAPTER] = NodeType.CHAPTER
    title: str = Field(..., description="章标题，如 '信息的表示和处理'")
    number: int = Field(..., description="章序号，如 2")

class SectionNode(GraphNode):
    label: Literal[NodeType.SECTION] = NodeType.SECTION
    title: str = Field(..., description="节标题，如 '整数表示'")
    number: str = Field(..., description="节序号，如 '2.2'")

class TextChunkNode(GraphNode):
    """对应 2.1.A 和 2.4.2 中提到的 TextChunk"""
    label: Literal[NodeType.TEXT_CHUNK] = NodeType.TEXT_CHUNK
    content: str = Field(..., description="文本块的具体内容，约500字")
    page_number: int = Field(..., description="所在的页码")
    embedding: Optional[List[float]] = Field(None, description="向量表示，用于 RAG 检索")
    chapter_id: str = Field(..., description="所属章节ID")

# --- B. 知识语义层节点 ---

class ConceptNode(GraphNode):
    """对应 2.1.B 和 2.4.1 的 Concept"""
    label: Literal[NodeType.CONCEPT] = NodeType.CONCEPT
    name: str = Field(..., description="概念名称，如 '补码'")
    alias: Optional[List[str]] = Field(default=[], description="别名列表，如 ['Two’s Complement']")
    definition: Optional[str] = Field(None, description="概念的简要定义")

class HardwareNode(GraphNode):
    """对应 2.1.B Hardware"""
    label: Literal[NodeType.HARDWARE] = NodeType.HARDWARE
    name: str = Field(..., description="硬件名称，如 'ALU'")
    hw_type: str = Field(..., description="硬件类型，如 '组合逻辑电路'")

class InstructionNode(GraphNode):
    """对应 2.1.B Instruction"""
    label: Literal[NodeType.INSTRUCTION] = NodeType.INSTRUCTION
    name: str = Field(..., description="指令名称，如 'movq'")
    syntax: str = Field(..., description="指令语法，如 'movq S, D'")

class CodeSnippetNode(GraphNode):
    """对应 2.1.B CodeSnippet"""
    label: Literal[NodeType.CODE_SNIPPET] = NodeType.CODE_SNIPPET
    language: str = Field(default="C", description="编程语言，如 'C' 或 'Assembly'")
    content: str = Field(..., description="代码具体内容")

class PrincipleNode(GraphNode):
    """对应 2.1.B Principle"""
    label: Literal[NodeType.PRINCIPLE] = NodeType.PRINCIPLE
    name: str = Field(..., description="原理名称，如 '局部性原理'")

# ==========================================
# 4. 统一数据容器 (用于 LLM 输出)
# ==========================================

class ExtractionResult(BaseModel):
    """用于接收 LLM 从文本中提取的结构化数据"""
    
    # 使用 Union 允许列表中包含不同类型的节点
    nodes: List[Union[
        ConceptNode, 
        HardwareNode, 
        InstructionNode, 
        CodeSnippetNode, 
        PrincipleNode,
        # 文档结构节点通常由解析器生成，LLM主要提取上述知识节点
    ]] = Field(..., description="提取出的所有实体节点")
    
    relationships: List[GraphRelationship] = Field(..., description="提取出的所有关系")

    class Config:
        json_schema_extra = {
            "example": {
                "nodes": [
                    {
                        "id": "concept_twos_comp",
                        "label": "Concept",
                        "name": "补码",
                        "alias": ["Two's Complement"]
                    },
                    {
                        "id": "hw_alu",
                        "label": "Hardware",
                        "name": "ALU",
                        "hw_type": "组合逻辑电路"
                    }
                ],
                "relationships": [
                    {
                        "source_id": "concept_twos_comp",
                        "target_id": "hw_alu",
                        "type": "IMPLEMENTED_BY"
                    }
                ]
            }
        }