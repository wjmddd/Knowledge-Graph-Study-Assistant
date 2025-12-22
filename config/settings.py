"""
全局配置
直接从原 pipeline.py 提取，保持原有风格
"""

# ================= 配置区域 =================
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

INPUT_FILE = "第一章.md"
OUTPUT_FILE = "graph_data_full.json"
MAX_WORKERS = 1  # 并发线程数 (建议设为1，避免触发速率限制)
REQUEST_DELAY = 2  # 每次请求后等待秒数 (防止 RPM 限制)
CHUNK_SIZE = 1000  # 每个切片的大致字符数
# ===========================================
