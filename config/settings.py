"""
全局配置
包含 LLM、Neo4j、ChromaDB、OpenAI Embedding 等配置
"""

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
