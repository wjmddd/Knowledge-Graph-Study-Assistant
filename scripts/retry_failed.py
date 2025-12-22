"""
重试失败的文本块
用法: python scripts/retry_failed.py [块索引]
例如: python scripts/retry_failed.py 16  (重试第16块)
直接从原 retry_failed.py 提取
"""

import sys
import json
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import instructor
from openai import OpenAI

from config.settings import CLIENT_CONFIG, INPUT_FILE, OUTPUT_FILE
from config.prompts import SYSTEM_PROMPT
from src.pipeline.parser import parse_markdown_with_context
from src.models.schema import ExtractionResult


def retry_chunk(chunk_number: int):
    """
    重试指定的文本块并追加到结果文件
    chunk_number: 从1开始的块编号
    """
    chunk_idx = chunk_number - 1  # 转换为0索引
    
    print(f"🔄 准备重试第 {chunk_number} 块...")
    
    # 1. 解析获取所有块
    chunks = parse_markdown_with_context(INPUT_FILE)
    print(f"📦 共有 {len(chunks)} 个文本块")
    
    if chunk_idx < 0 or chunk_idx >= len(chunks):
        print(f"❌ 错误: 块编号 {chunk_number} 超出范围 (1-{len(chunks)})")
        return
    
    target_chunk = chunks[chunk_idx]
    print(f"📍 目标块: {target_chunk.metadata['section']}")
    print(f"📝 内容长度: {len(target_chunk.content)} 字符")
    
    # 2. 初始化 LLM 客户端
    client = instructor.from_openai(
        OpenAI(base_url=CLIENT_CONFIG["base_url"], api_key=CLIENT_CONFIG["api_key"]),
        mode=instructor.Mode.JSON
    )
    
    # 3. 调用 LLM 提取
    print(f"\n⚡ 正在调用 LLM 提取...")
    try:
        resp = client.chat.completions.create(
            model=CLIENT_CONFIG["model"],
            response_model=ExtractionResult,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": target_chunk.to_prompt()},
            ],
            max_tokens=4000,
            temperature=0.0
        )
        data = resp.model_dump()
        print(f"✅ 提取成功! 节点: {len(data['nodes'])}, 关系: {len(data['relationships'])}")
        
    except Exception as e:
        print(f"❌ 提取失败: {e}")
        return
    
    # 4. 读取现有结果文件
    try:
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
        print(f"📂 读取现有结果: {len(existing_data['nodes'])} 节点, {len(existing_data['relationships'])} 关系")
    except FileNotFoundError:
        existing_data = {"nodes": [], "relationships": []}
        print("📂 结果文件不存在，创建新文件")
    
    # 5. 追加新结果
    existing_data["nodes"].extend(data["nodes"])
    existing_data["relationships"].extend(data["relationships"])
    
    # 6. 保存结果
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(existing_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*50}")
    print(f"✅ 结果已追加到 {OUTPUT_FILE}")
    print(f"📊 当前总计: {len(existing_data['nodes'])} 节点, {len(existing_data['relationships'])} 关系")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python scripts/retry_failed.py [块编号]")
        print("例如: python scripts/retry_failed.py 16")
        sys.exit(1)
    
    try:
        chunk_num = int(sys.argv[1])
        retry_chunk(chunk_num)
    except ValueError:
        print(f"❌ 无效的块编号: {sys.argv[1]}")
