"""
LLM 知识抽取模块
直接从原 pipeline.py 提取
"""

from src.models.schema import ExtractionResult
from src.pipeline.parser import ContextChunk
from config.prompts import SYSTEM_PROMPT
from config.settings import CLIENT_CONFIG


def process_single_chunk(chunk: ContextChunk, client) -> dict:
    """
    调用 LLM 处理单个文本块
    """
    try:
        resp = client.chat.completions.create(
            model=CLIENT_CONFIG["model"],
            response_model=ExtractionResult,  # 核心：Pydantic 约束
            messages=[
                {
                    "role": "system", 
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user", 
                    "content": chunk.to_prompt()  # 注入带上下文的文本
                },
            ],
            max_tokens=4000,  # 增大 token 限制，防止输出被截断
            temperature=0.0
        )
        # 返回字典格式，方便后续合并
        return resp.model_dump()
        
    except Exception as e:
        print(f"Error processing chunk: {chunk.metadata} - {e}")
        return None
