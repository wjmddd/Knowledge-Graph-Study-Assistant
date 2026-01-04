"""
LLM 知识抽取模块
"""

from src.models.schema import ExtractionResult
from src.pipeline.parser import ContextChunk
from config.prompts import SYSTEM_PROMPT
from config.settings import CLIENT_CONFIG

# 最大输入字符数（避免输入太长导致输出被截断）
MAX_CONTENT_CHARS = 2000


def process_single_chunk(chunk: ContextChunk, client, max_retries: int = 2) -> dict:
    """
    调用 LLM 处理单个文本块
    
    Args:
        chunk: 待处理的文本块
        client: instructor 客户端
        max_retries: 最大重试次数
    """
    # 如果内容过长，截断以避免输出被截断
    content = chunk.content
    if len(content) > MAX_CONTENT_CHARS:
        content = content[:MAX_CONTENT_CHARS] + "\n\n[内容已截断，请基于以上内容提取]"
    
    # 构建 prompt
    prompt = f"""
    [上下文信息]
    所属章节: {chunk.metadata.get('chapter', '未知')}
    所属小节: {chunk.metadata.get('section', '未知')}
    
    [待分析文本]
    {content}
    """
    
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            resp = client.chat.completions.create(
                model=CLIENT_CONFIG["model"],
                response_model=ExtractionResult,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=8000,  # 增大到 8000
                temperature=0.0
            )
            return resp.model_dump()
            
        except Exception as e:
            last_error = e
            error_msg = str(e).lower()
            
            # 如果是 token 限制错误，进一步截断内容重试
            if "max_tokens" in error_msg or "length limit" in error_msg:
                if attempt < max_retries:
                    # 进一步截断内容
                    truncate_len = MAX_CONTENT_CHARS // (attempt + 2)
                    content = chunk.content[:truncate_len] + "\n\n[内容已截断]"
                    prompt = f"""
                    [上下文信息]
                    所属章节: {chunk.metadata.get('chapter', '未知')}
                    所属小节: {chunk.metadata.get('section', '未知')}
                    
                    [待分析文本]
                    {content}
                    """
                    continue
            
            # 其他错误直接返回
            break
    
    # 所有重试都失败
    print(f"\n      ⚠️ 提取失败: {last_error}")
    return None
