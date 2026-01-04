"""
知识图谱数据模型
包含文档结构层和知识语义层两层设计
"""

from typing import List, Optional, Union, Literal, Annotated
from pydantic import BaseModel, Field, Discriminator
from enum import Enum


# ==========================================
# 1. 枚举定义 (对应 2.1 和 2.2 节)
# ==========================================

class NodeType(str, Enum):
    """对应 2.1 核心节点设计"""
    # A. 文档结构层 (自动生成，用于 RAG 检索和溯源)
    COURSE = "Course"
    CHAPTER = "Chapter"
    SECTION = "Section"
    TEXT_CHUNK = "TextChunk"
    
    # B. 知识语义层 (LLM 提取)
    CONCEPT = "Concept"
    HARDWARE = "Hardware"
    INSTRUCTION = "Instruction"
    CODE_SNIPPET = "CodeSnippet"
    PRINCIPLE = "Principle"


class RelationType(str, Enum):
    """对应 2.2 核心关系设计 - 针对《计算机系统基础》优化"""
    
    # A. 层级与包含关系 (文档结构)
    CONTAINS = "CONTAINS"           # Course->Chapter->Section->TextChunk
    MENTIONS = "MENTIONS"           # TextChunk->Concept
    
    # B. 分类与组成关系
    IS_A = "IS_A"                   # 分类关系: SRAM IS_A 存储器
    COMPOSED_OF = "COMPOSED_OF"     # 组成关系: CPU COMPOSED_OF ALU
    
    # C. 依赖与实现关系
    DEPENDS_ON = "DEPENDS_ON"       # 学习依赖: 虚拟内存 DEPENDS_ON 页表
    IMPLEMENTED_BY = "IMPLEMENTED_BY" # 实现关系: 加法 IMPLEMENTED_BY 加法器
    USES = "USES"                   # 使用关系: 程序 USES 寄存器
    
    # D. 对比与等价关系 (计算机系统特有，非常重要!)
    CONTRASTS_WITH = "CONTRASTS_WITH" # 对比关系: 大端法 CONTRASTS_WITH 小端法
    EQUIVALENT_TO = "EQUIVALENT_TO"   # 等价关系: 补码加法 EQUIVALENT_TO 无符号加法(位级)
    
    # E. 转换与流程关系 (编译、地址转换等)
    CONVERTS_TO = "CONVERTS_TO"     # 转换关系: 虚拟地址 CONVERTS_TO 物理地址
    PRECEDES = "PRECEDES"           # 顺序关系: 取指 PRECEDES 译码 (流水线阶段)
    
    # F. 因果与优化关系
    CAUSES = "CAUSES"               # 因果关系: 溢出 CAUSES 程序错误
    OPTIMIZES = "OPTIMIZES"         # 优化关系: Cache OPTIMIZES 内存访问
    
    # G. 指令与代码关系
    OPERATES_ON = "OPERATES_ON"     # 指令操作: movq OPERATES_ON 寄存器
    EXAMPLE_OF = "EXAMPLE_OF"       # 举例关系: 代码片段 EXAMPLE_OF 缓冲区溢出
    
    # H. 执行与运行关系 (LLM 高频使用)
    EXECUTES = "EXECUTES"           # 执行关系: CPU EXECUTES 指令
    RUNS_ON = "RUNS_ON"             # 运行于: 程序 RUNS_ON 操作系统
    DEFINES = "DEFINES"             # 定义关系: ISA DEFINES 指令格式
    DERIVED_FROM = "DERIVED_FROM"   # 派生关系: 程序 DERIVED_FROM 算法
    
    # I. 兜底关系
    RELATED_TO = "RELATED_TO"       # 通用关联 (仅当以上都不适用时使用)


# ==========================================
# 2. 基础模型类
# ==========================================

class GraphNode(BaseModel):
    """所有节点的基类"""
    id: str = Field(..., description="全局唯一标识符，格式为 '{类型前缀}_{英文名}'")
    label: NodeType = Field(..., description="节点类型标签")


class GraphRelationship(BaseModel):
    """对应 2.2 的关系定义"""
    source_id: str = Field(..., description="起始节点ID")
    target_id: str = Field(..., description="目标节点ID")
    type: str = Field(..., description="关系类型")
    properties: dict = Field(default_factory=dict, description="关系属性")


# ==========================================
# 3. 具体节点模型 (对应 2.4 具体属性设计)
# ==========================================

class ConceptNode(GraphNode):
    """概念节点"""
    label: Literal[NodeType.CONCEPT] = NodeType.CONCEPT
    name: str = Field(..., description="概念名称")
    alias: List[str] = Field(default_factory=list, description="别名列表")
    definition: Optional[str] = Field(default=None, description="概念定义")


class HardwareNode(GraphNode):
    """硬件节点"""
    label: Literal[NodeType.HARDWARE] = NodeType.HARDWARE
    name: str = Field(..., description="硬件名称")
    hw_type: str = Field(default="通用硬件", description="硬件类型")


class InstructionNode(GraphNode):
    """指令节点"""
    label: Literal[NodeType.INSTRUCTION] = NodeType.INSTRUCTION
    name: str = Field(..., description="指令名称")
    syntax: Optional[str] = Field(default=None, description="指令语法")


class CodeSnippetNode(GraphNode):
    """代码片段节点"""
    label: Literal[NodeType.CODE_SNIPPET] = NodeType.CODE_SNIPPET
    name: str = Field(default="代码片段", description="代码描述")
    language: str = Field(default="C", description="编程语言")
    content: str = Field(..., description="代码内容")


class PrincipleNode(GraphNode):
    """原理节点"""
    label: Literal[NodeType.PRINCIPLE] = NodeType.PRINCIPLE
    name: str = Field(..., description="原理名称")
    description: Optional[str] = Field(default=None, description="原理描述")


# --- A. 文档结构层节点 (自动生成，用于 RAG) ---

class CourseNode(GraphNode):
    """课程节点 - 最顶层"""
    label: Literal[NodeType.COURSE] = NodeType.COURSE
    name: str = Field(..., description="课程名称，如 '计算机系统基础'")


class ChapterNode(GraphNode):
    """章节点"""
    label: Literal[NodeType.CHAPTER] = NodeType.CHAPTER
    title: str = Field(..., description="章标题，如 '计算机系统概述'")
    number: int = Field(..., description="章序号，如 1")


class SectionNode(GraphNode):
    """小节节点"""
    label: Literal[NodeType.SECTION] = NodeType.SECTION
    title: str = Field(..., description="节标题，如 '计算机基本工作原理'")
    number: str = Field(..., description="节序号，如 '1.2'")


class TextChunkNode(GraphNode):
    """文本块节点 - 用于 RAG 检索和溯源"""
    label: Literal[NodeType.TEXT_CHUNK] = NodeType.TEXT_CHUNK
    content: str = Field(..., description="文本块内容")
    chunk_index: int = Field(..., description="在文档中的顺序索引")
    char_count: int = Field(default=0, description="字符数")


# ==========================================
# 4. 统一数据容器 (用于 LLM 输出)
# ==========================================

KnowledgeNode = Annotated[
    Union[ConceptNode, HardwareNode, InstructionNode, CodeSnippetNode, PrincipleNode],
    Discriminator('label')
]


class ExtractionResult(BaseModel):
    """用于接收 LLM 从文本中提取的结构化数据（知识语义层）"""
    nodes: List[KnowledgeNode] = Field(default_factory=list, description="节点列表")
    relationships: List[GraphRelationship] = Field(default_factory=list, description="关系列表")


# ==========================================
# 5. 完整知识图谱容器 (包含两层)
# ==========================================

# 所有节点类型的联合（用于完整图谱）
AllNodeTypes = Union[
    # 文档结构层
    CourseNode, ChapterNode, SectionNode, TextChunkNode,
    # 知识语义层
    ConceptNode, HardwareNode, InstructionNode, CodeSnippetNode, PrincipleNode
]


class FullKnowledgeGraph(BaseModel):
    """
    完整的知识图谱数据结构
    包含文档结构层 + 知识语义层
    """
    # 文档结构层
    course: Optional[CourseNode] = None
    chapters: List[ChapterNode] = Field(default_factory=list)
    sections: List[SectionNode] = Field(default_factory=list)
    text_chunks: List[TextChunkNode] = Field(default_factory=list)
    
    # 知识语义层 (LLM 提取)
    knowledge_nodes: List[KnowledgeNode] = Field(default_factory=list)
    
    # 所有关系 (包含 CONTAINS 和 MENTIONS)
    relationships: List[GraphRelationship] = Field(default_factory=list)
    
    def to_flat_dict(self) -> dict:
        """
        转换为扁平化的字典格式，方便导入 Neo4j
        """
        all_nodes = []
        
        # 添加文档结构层节点
        if self.course:
            all_nodes.append(self.course.model_dump())
        all_nodes.extend([c.model_dump() for c in self.chapters])
        all_nodes.extend([s.model_dump() for s in self.sections])
        all_nodes.extend([t.model_dump() for t in self.text_chunks])
        
        # 添加知识语义层节点
        all_nodes.extend([n.model_dump() for n in self.knowledge_nodes])
        
        return {
            "nodes": all_nodes,
            "relationships": [r.model_dump() for r in self.relationships]
        }
