"""
向量嵌入模块
使用 OpenAI text-embedding-3-small 模型生成文本向量
"""

import sys
from pathlib import Path
from typing import List, Optional
from openai import OpenAI

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config.settings import OPENAI_CONFIG

# text-embedding-3-small 最大支持 8191 tokens
# 中文大约 1-2 token/字，保守设置 4000 字符限制
MAX_TEXT_CHARS = 4000


def truncate_text(text: str, max_chars: int = MAX_TEXT_CHARS) -> str:
    """
    截断过长的文本
    
    Args:
        text: 原始文本
        max_chars: 最大字符数
        
    Returns:
        截断后的文本
    """
    if len(text) <= max_chars:
        return text
    
    # 尝试在句子边界截断
    truncated = text[:max_chars]
    
    # 查找最后一个句子结束符
    last_period = max(
        truncated.rfind('。'),
        truncated.rfind('！'),
        truncated.rfind('？'),
        truncated.rfind('.'),
        truncated.rfind('\n')
    )
    
    if last_period > max_chars * 0.7:  # 如果找到的位置在70%之后，使用它
        return truncated[:last_period + 1]
    
    return truncated


class EmbeddingModel:
    """OpenAI Embedding 封装"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.api_key = api_key or OPENAI_CONFIG["api_key"]
        self.base_url = base_url or OPENAI_CONFIG["base_url"]
        self.model = model or OPENAI_CONFIG["embedding_model"]
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    def embed_text(self, text: str) -> List[float]:
        """
        将单个文本转换为向量
        
        Args:
            text: 输入文本
            
        Returns:
            向量列表
        """
        # 清理和截断文本
        text = text.replace("\n", " ").strip()
        text = truncate_text(text)
        
        if not text:
            # 返回零向量
            return [0.0] * OPENAI_CONFIG["embedding_dimensions"]
        
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"⚠️ Embedding 生成失败: {e}")
            return [0.0] * OPENAI_CONFIG["embedding_dimensions"]
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        批量将文本转换为向量
        
        Args:
            texts: 文本列表
            
        Returns:
            向量列表的列表
        """
        # 清理和截断文本
        cleaned_texts = []
        for text in texts:
            cleaned = text.replace("\n", " ").strip()
            cleaned = truncate_text(cleaned)
            if not cleaned:
                cleaned = " "  # 空文本替换为空格，避免API报错
            cleaned_texts.append(cleaned)
        
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=cleaned_texts
            )
            # 按原顺序返回
            embeddings = [None] * len(cleaned_texts)
            for item in response.data:
                embeddings[item.index] = item.embedding
            return embeddings
        except Exception as e:
            print(f"⚠️ 批量 Embedding 生成失败: {e}")
            # 回退：逐个处理
            print("   尝试逐个处理...")
            embeddings = []
            for text in cleaned_texts:
                emb = self.embed_text(text)
                embeddings.append(emb)
            return embeddings


# 全局单例
_embedding_model: Optional[EmbeddingModel] = None


def get_embedding_model() -> EmbeddingModel:
    """获取全局 Embedding 模型实例"""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = EmbeddingModel()
    return _embedding_model


def embed_query(text: str) -> List[float]:
    """便捷函数：嵌入查询文本"""
    return get_embedding_model().embed_text(text)


def embed_documents(texts: List[str]) -> List[List[float]]:
    """便捷函数：批量嵌入文档"""
    return get_embedding_model().embed_texts(texts)


if __name__ == "__main__":
    # 测试
    print("测试 Embedding 模块...")
    model = EmbeddingModel()
    
    test_text = "什么是补码？"
    embedding = model.embed_text(test_text)
    print(f"文本: {test_text}")
    print(f"向量维度: {len(embedding)}")
    print(f"前5个值: {embedding[:5]}")
    
    # 测试长文本截断
    long_text = "这是一段很长的测试文本。" * 500
    print(f"\n测试长文本截断:")
    print(f"原始长度: {len(long_text)} 字符")
    truncated = truncate_text(long_text)
    print(f"截断后长度: {len(truncated)} 字符")
