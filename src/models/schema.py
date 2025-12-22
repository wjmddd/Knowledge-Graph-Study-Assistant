"""
知识图谱数据模型
直接从原 model/model.py 复制，保持完全一致
"""

from typing import List, Optional, Union, Literal, Annotated
from pydantic import BaseModel, Field, Discriminator
from enum import Enum


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


# ==========================================
# 4. 统一数据容器 (用于 LLM 输出)
# ==========================================

KnowledgeNode = Annotated[
    Union[ConceptNode, HardwareNode, InstructionNode, CodeSnippetNode, PrincipleNode],
    Discriminator('label')
]


class ExtractionResult(BaseModel):
    """用于接收 LLM 从文本中提取的结构化数据"""
    nodes: List[KnowledgeNode] = Field(default_factory=list, description="节点列表")
    relationships: List[GraphRelationship] = Field(default_factory=list, description="关系列表")
