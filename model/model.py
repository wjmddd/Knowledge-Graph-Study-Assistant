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
    
    # H. 兜底关系
    RELATED_TO = "RELATED_TO"       # 通用关联 (仅当以上都不适用时使用)

# ==========================================
# 2. 基础模型类
# ==========================================

class GraphNode(BaseModel):
    """所有节点的基类"""
    id: str = Field(..., description="全局唯一标识符，格式为 '{类型前缀}_{英文名}'，如 'concept_cpu', 'hw_alu', 'principle_locality'")
    label: NodeType = Field(..., description="节点类型标签")

class GraphRelationship(BaseModel):
    """对应 2.2 的关系定义"""
    source_id: str = Field(..., description="起始节点ID，必须与某个节点的 id 匹配")
    target_id: str = Field(..., description="目标节点ID，必须与某个节点的 id 匹配")
    type: RelationType = Field(..., description="关系类型")
    properties: dict = Field(default_factory=dict, description="关系的额外属性，如 weight")

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
    page_number: int = Field(default=0, description="所在的页码")
    embedding: Optional[List[float]] = Field(default=None, description="向量表示，用于 RAG 检索")
    chapter_id: str = Field(default="", description="所属章节ID")

# --- B. 知识语义层节点 (LLM 主要提取这些) ---

class ConceptNode(GraphNode):
    """对应 2.1.B 和 2.4.1 的 Concept"""
    label: Literal[NodeType.CONCEPT] = NodeType.CONCEPT
    name: str = Field(..., description="概念名称，如 '补码'、'存储程序'")
    alias: List[str] = Field(default_factory=list, description="别名列表，如 ['Two's Complement']")
    definition: Optional[str] = Field(default=None, description="概念的简要定义")

class HardwareNode(GraphNode):
    """对应 2.1.B Hardware - 计算机硬件组件"""
    label: Literal[NodeType.HARDWARE] = NodeType.HARDWARE
    name: str = Field(..., description="硬件名称，如 'ALU'、'CPU'、'主存'")
    hw_type: str = Field(default="通用硬件", description="硬件类型，如 '组合逻辑电路'、'存储器'")

class InstructionNode(GraphNode):
    """对应 2.1.B Instruction - 机器/汇编指令"""
    label: Literal[NodeType.INSTRUCTION] = NodeType.INSTRUCTION
    name: str = Field(..., description="指令名称，如 'movq'、'lw'")
    syntax: Optional[str] = Field(default=None, description="指令语法，如 'movq S, D'")

class CodeSnippetNode(GraphNode):
    """对应 2.1.B CodeSnippet - 代码示例"""
    label: Literal[NodeType.CODE_SNIPPET] = NodeType.CODE_SNIPPET
    name: str = Field(default="代码片段", description="代码片段的简短描述，如 'hello world 示例'")
    language: str = Field(default="C", description="编程语言，如 'C' 或 'Assembly'")
    content: str = Field(..., description="代码具体内容")

class PrincipleNode(GraphNode):
    """对应 2.1.B Principle - 重要原理/定理"""
    label: Literal[NodeType.PRINCIPLE] = NodeType.PRINCIPLE
    name: str = Field(..., description="原理名称，如 '局部性原理'、'存储程序工作方式'")
    description: Optional[str] = Field(default=None, description="原理的简要描述")

# ==========================================
# 4. 统一数据容器 (用于 LLM 输出)
# ==========================================

# 定义一个带鉴别器的联合类型，让 Pydantic 根据 'label' 字段自动选择正确的子类
KnowledgeNode = Annotated[
    Union[ConceptNode, HardwareNode, InstructionNode, CodeSnippetNode, PrincipleNode],
    Discriminator('label')
]

class ExtractionResult(BaseModel):
    """用于接收 LLM 从文本中提取的结构化数据"""
    
    nodes: List[KnowledgeNode] = Field(
        default_factory=list, 
        description="提取出的所有实体节点列表"
    )
    
    relationships: List[GraphRelationship] = Field(
        default_factory=list, 
        description="提取出的所有关系列表"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "nodes": [
                    {
                        "id": "concept_stored_program",
                        "label": "Concept",
                        "name": "存储程序",
                        "alias": ["stored-program"],
                        "definition": "将程序和数据存入主存后自动执行的工作方式"
                    },
                    {
                        "id": "hw_cpu",
                        "label": "Hardware",
                        "name": "CPU",
                        "hw_type": "处理器"
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
                        "source_id": "hw_cpu",
                        "target_id": "hw_alu",
                        "type": "COMPOSED_OF",
                        "properties": {}
                    }
                ]
            }
        }
    }