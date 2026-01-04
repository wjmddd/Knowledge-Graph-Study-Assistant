"""
全局配置
包含 LLM、Neo4j、ChromaDB、OpenAI Embedding 等配置
以及中英文术语映射表
"""

import re
from pathlib import Path

# ================= 项目路径 =================
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
MD_INPUT_DIR = PROJECT_ROOT / "md"
CHAPTER_OUTPUT_DIR = DATA_DIR / "chapters"
CHROMA_DB_DIR = DATA_DIR / "chroma_db"

# 确保目录存在
DATA_DIR.mkdir(exist_ok=True)
CHAPTER_OUTPUT_DIR.mkdir(exist_ok=True)
CHROMA_DB_DIR.mkdir(exist_ok=True)

# ================= LLM 配置 (用于问答生成) =================
# 推荐使用 DeepSeek 官方 API (更稳定、更便宜)
# 获取 Key: https://platform.deepseek.com

CLIENT_CONFIG = {
    # === 方案1: DeepSeek 官方 (推荐) ===
    # "api_key": "sk-xxx",  # 替换为你的 DeepSeek API Key
    # "base_url": "https://api.deepseek.com/v1",
    # "model": "deepseek-chat"
    
    # === 方案2: SiliconFlow 免费模型 ===
    "api_key": "sk-pGezF366dyAXhRktmeRXkWs4XEQ8h5TH8xUb9vyDl2pSFP0I",
    "base_url": "https://sg.uiuiapi.com/v1",
    "model": "qwen3-30b-a3b-instruct-2507"  
}

# ================= OpenAI Embedding 配置 =================
# 用于向量检索，需要 OpenAI API Key
# 获取 Key: https://platform.openai.com

OPENAI_CONFIG = {
    "api_key": "sk-pGezF366dyAXhRktmeRXkWs4XEQ8h5TH8xUb9vyDl2pSFP0I",  # 替换为你的 OpenAI API Key
    "base_url": "https://sg.uiuiapi.com/v1",  # 或使用代理地址
    "embedding_model": "text-embedding-3-small",
    "embedding_dimensions": 1536  # text-embedding-3-small 默认维度
}

# ================= Neo4j 配置 =================
NEO4J_CONFIG = {
    "uri": "neo4j://localhost:7687",  # 单机版用 bolt://
    "user": "neo4j",
    "password": "F9rSd7UAt2FkkNU"  # 替换为你的密码
}

# ================= ChromaDB 配置 =================
CHROMA_CONFIG = {
    "collection_name": "textchunks",
    "persist_directory": str(CHROMA_DB_DIR)
}

# ================= 知识抽取配置 =================
INPUT_FILE = "第一章.md"
OUTPUT_FILE = "graph_data_full.json"
MAX_WORKERS = 1  # 并发线程数 (建议设为1，避免触发速率限制)
REQUEST_DELAY = 2  # 每次请求后等待秒数 (防止 RPM 限制)
CHUNK_SIZE = 1000  # 每个切片的大致字符数

# ================= 问答系统配置 =================
QA_CONFIG = {
    "max_context_chunks": 5,  # 最多检索多少个文本块
    "max_graph_results": 10,  # 最多返回多少个图谱结果
    "similarity_threshold": 0.7,  # 向量相似度阈值
    "temperature": 0.1,  # LLM 生成温度 (越低越确定)
    "max_tokens": 2000  # 最大生成长度
}

# ================= Agent 提示词配置 =================

# 答案生成系统提示词
ANSWER_SYSTEM_PROMPT = """你是一个《计算机系统基础》课程的智能学习助手。

## 核心原则【最重要】
你**只能**基于提供的知识库检索结果来回答问题，**严禁**使用你自己的知识直接回答。
- 如果检索结果中有相关信息，基于它来组织回答
- 如果检索结果中没有相关信息，诚实告知"知识库中未找到相关内容"
- **绝对不要**编造或补充检索结果中没有的信息

## 回答格式要求
1. **结构化**：使用列表、分点清晰组织回答
2. **教学性**：通俗易懂，保持友好耐心的教学语气
3. **标注来源**：如果检索结果包含章节信息，在回答中提及来源

## 多轮对话
- 结合之前的对话上下文理解用户问题
- 如果用户说"它"、"这个"等代词，要联系上下文"""

# 工具选择系统提示词
TOOL_SELECTION_SYSTEM_PROMPT = "你是一个知识检索助手。你必须调用工具来检索知识库，不能直接回答问题。"

# 工具选择用户提示词模板 (使用 {query} 作为占位符)
TOOL_SELECTION_USER_PROMPT = """请根据用户问题选择合适的工具进行知识检索。

用户问题: {query}

你必须调用至少一个工具来检索知识库。根据问题类型选择：
- 概念定义问题 → get_concept_definition
- 组成结构问题 → get_concept_composition  
- 学习路径问题 → get_learning_path
- 概念比较问题 → compare_concepts
- 概念关系问题 → find_concept_relation
- 其他问题 → hybrid_search 或 semantic_search

请立即调用工具。"""

# 用户问题模板 (包含检索结果)
USER_QUERY_WITH_CONTEXT_TEMPLATE = """【知识库检索结果】
{context}

【我的问题】
{query}

请基于上述检索结果回答我的问题。"""

# 知识库未找到时的系统提示词
FALLBACK_SYSTEM_PROMPT = """你是一个《计算机系统基础》课程的智能学习助手。

⚠️ 注意：知识库中没有找到与用户问题相关的内容。

请基于你自己的知识来回答这个问题。回答时请：
1. 保持专业、准确
2. 使用通俗易懂的语言
3. 如果不确定，请诚实说明
4. 结构化组织答案（使用列表、分点）

请直接回答用户的问题。"""

# 知识库未找到的提示前缀
KB_NOT_FOUND_PREFIX = """⚠️ **提示**：知识库中未找到与您的问题直接相关的内容，以下回答基于AI的通用知识：

---

"""

# ==========================================
# 中英文计算机术语对照表 (针对《计算机系统基础》优化)
# 用于：节点去重、智能查询匹配
# ==========================================
TERM_MAPPINGS = {
    # ========== 硬件组件 ==========
    "cpu": ["中央处理器", "处理器", "central processing unit", "CPU"],
    "alu": ["算术逻辑单元", "运算器", "arithmetic logic unit", "ALU"],
    "cu": ["控制单元", "控制器", "control unit"],
    "pc": ["程序计数器", "program counter", "PC"],
    "ir": ["指令寄存器", "instruction register", "IR"],
    "mar": ["存储器地址寄存器", "memory address register", "MAR"],
    "mdr": ["存储器数据寄存器", "memory data register", "MDR"],
    "psw": ["程序状态字", "program status word", "PSW"],
    "cache": ["缓存", "高速缓存", "高速缓冲存储器", "Cache"],
    "ram": ["内存", "主存", "随机存取存储器", "主存储器", "random access memory", "RAM"],
    "rom": ["只读存储器", "read only memory", "ROM"],
    "sram": ["静态随机存取存储器", "static ram", "SRAM"],
    "dram": ["动态随机存取存储器", "dynamic ram", "DRAM"],
    "register": ["寄存器"],
    "bus": ["总线"],
    "mmu": ["内存管理单元", "memory management unit", "MMU"],
    "tlb": ["转换后备缓冲器", "页表缓存", "translation lookaside buffer", "TLB"],
    "gpu": ["图形处理器", "graphics processing unit", "GPU"],
    "ssd": ["固态硬盘", "solid state drive", "SSD"],
    "hdd": ["机械硬盘", "硬盘驱动器", "hard disk drive", "HDD"],
    
    # ========== 数据表示 ==========
    "two's complement": ["补码", "二进制补码", "2的补码"],
    "one's complement": ["反码", "1的补码"],
    "sign magnitude": ["原码", "符号-数值", "符号数值"],
    "floating point": ["浮点数", "浮点", "浮点表示"],
    "ieee 754": ["ieee754", "ieee 754标准", "浮点标准"],
    "mantissa": ["尾数", "有效数字"],
    "exponent": ["阶码", "指数"],
    "bias": ["偏置", "移码"],
    "big endian": ["大端", "大端法", "大端序"],
    "little endian": ["小端", "小端法", "小端序"],
    "sign extension": ["符号扩展"],
    "zero extension": ["零扩展"],
    "overflow": ["溢出", "上溢"],
    "underflow": ["下溢"],
    
    # ========== 指令与程序 ==========
    "instruction": ["指令"],
    "opcode": ["操作码", "op码"],
    "operand": ["操作数"],
    "immediate": ["立即数"],
    "program": ["程序"],
    "process": ["进程"],
    "thread": ["线程"],
    "isa": ["指令集架构", "instruction set architecture", "ISA"],
    "risc": ["精简指令集", "RISC"],
    "cisc": ["复杂指令集", "CISC"],
    "x86": ["x86架构", "x86指令集"],
    "mips": ["mips架构", "MIPS"],
    
    # ========== 存储层次 ==========
    "locality": ["局部性", "局部性原理"],
    "temporal locality": ["时间局部性"],
    "spatial locality": ["空间局部性"],
    "cache hit": ["缓存命中", "命中"],
    "cache miss": ["缓存未命中", "缓存缺失", "未命中"],
    "hit rate": ["命中率"],
    "miss rate": ["缺失率", "未命中率"],
    "write back": ["写回", "回写"],
    "write through": ["写直达", "直写"],
    "lru": ["最近最少使用", "least recently used", "LRU"],
    
    # ========== 虚拟存储 ==========
    "virtual memory": ["虚拟内存", "虚拟存储器", "虚存"],
    "virtual address": ["虚拟地址", "逻辑地址", "VA"],
    "physical address": ["物理地址", "实地址", "PA"],
    "page": ["页", "页面"],
    "page table": ["页表"],
    "page fault": ["缺页", "页故障", "缺页异常"],
    "page frame": ["页框", "物理页"],
    "segmentation": ["分段"],
    "paging": ["分页"],
    
    # ========== 流水线 ==========
    "pipeline": ["流水线"],
    "fetch": ["取指", "取指令"],
    "decode": ["译码", "解码"],
    "execute": ["执行"],
    "memory access": ["访存", "存储器访问"],
    "write back stage": ["写回阶段"],
    "hazard": ["冒险", "冲突"],
    "data hazard": ["数据冒险", "数据冲突"],
    "control hazard": ["控制冒险", "控制冲突"],
    "structural hazard": ["结构冒险", "结构冲突"],
    "forwarding": ["转发", "旁路"],
    "stall": ["停顿", "阻塞"],
    "branch prediction": ["分支预测"],
    
    # ========== 程序转换 ==========
    "compiler": ["编译器", "编译程序"],
    "assembler": ["汇编器", "汇编程序"],
    "linker": ["链接器", "链接程序"],
    "loader": ["加载器", "装载器", "装入程序"],
    "preprocessor": ["预处理器"],
    "source code": ["源代码", "源程序"],
    "object code": ["目标代码", "目标程序"],
    "executable": ["可执行文件", "可执行程序"],
    
    # ========== 系统结构 ==========
    "von neumann": ["冯·诺依曼", "冯诺依曼", "冯·诺伊曼", "冯诺伊曼"],
    "stored program": ["存储程序", "存储程序原理"],
    "operating system": ["操作系统", "os", "OS"],
    "kernel": ["内核"],
    "system call": ["系统调用"],
    "interrupt": ["中断"],
    "exception": ["异常"],
    "trap": ["陷阱", "陷入"],
    
    # ========== I/O ==========
    "io": ["输入输出", "i/o", "I/O"],
    "dma": ["直接存储器存取", "direct memory access", "DMA"],
    "polling": ["轮询", "查询"],
    "interrupt driven": ["中断驱动"],
    
    # ========== 其他 ==========
    "stack": ["栈", "堆栈"],
    "heap": ["堆"],
    "amdahl's law": ["阿姆达尔定律", "amdahl定律"],
    "moore's law": ["摩尔定律", "moore定律"],
    "cpi": ["每条指令周期数", "cycles per instruction", "CPI"],
    "mips_metric": ["每秒百万条指令", "million instructions per second"],
    "throughput": ["吞吐率", "吞吐量"],
    "latency": ["延迟", "时延"],
}

# 构建反向索引: 任意别名 -> 标准名称
ALIAS_TO_CANONICAL = {}
for _canonical, _aliases in TERM_MAPPINGS.items():
    ALIAS_TO_CANONICAL[_canonical.lower()] = _canonical
    for _alias in _aliases:
        ALIAS_TO_CANONICAL[_alias.lower()] = _canonical


def normalize_term(name: str) -> str:
    """
    标准化术语名称
    1. 转小写
    2. 移除空格和特殊字符
    3. 查找标准名称
    """
    if not name:
        return name
    
    # 清理名称
    clean_name = name.lower().strip()
    clean_name = re.sub(r'[·\-_\s]+', '', clean_name)  # 移除 · - _ 空格
    
    # 查找是否有对应的标准名称
    if clean_name in ALIAS_TO_CANONICAL:
        return ALIAS_TO_CANONICAL[clean_name]
    
    # 尝试原始名称（带空格）
    original_lower = name.lower().strip()
    if original_lower in ALIAS_TO_CANONICAL:
        return ALIAS_TO_CANONICAL[original_lower]
    
    return name  # 未找到映射，返回原名


def get_term_variants(term: str) -> list:
    """
    获取术语的所有变体（中英文转换）
    
    Args:
        term: 输入术语
        
    Returns:
        该术语的所有已知变体列表
    """
    term_lower = term.lower().strip()
    variants = [term, term_lower, term.upper()]
    
    # 查找映射表
    for key, values in TERM_MAPPINGS.items():
        all_forms = [key] + [v.lower() for v in values]
        if term_lower in all_forms or any(term_lower in f for f in all_forms):
            variants.extend([key] + values)
            break
    
    # 去重
    return list(set(variants))
