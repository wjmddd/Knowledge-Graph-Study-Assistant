"""
知识图谱构建主入口
用法: python scripts/build_kg.py
直接从原 pipeline.py 的 main() 函数提取
"""

import sys
import json
import time
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import instructor
from openai import OpenAI

from config.settings import CLIENT_CONFIG, INPUT_FILE, OUTPUT_FILE, REQUEST_DELAY
from src.pipeline.parser import parse_markdown_with_context
from src.pipeline.extractor import process_single_chunk


def main():
    print(f"🚀 开始处理文件: {INPUT_FILE}")
    print(f"📡 使用模型: {CLIENT_CONFIG['model']}")
    print(f"🔗 API 地址: {CLIENT_CONFIG['base_url']}")
    
    # 1. 解析与切分
    chunks = parse_markdown_with_context(INPUT_FILE)
    print(f"📦 解析完成，共切分为 {len(chunks)} 个带有上下文的文本块。")
    
    # 2. 初始化 LLM 客户端
    client = instructor.from_openai(
        OpenAI(base_url=CLIENT_CONFIG["base_url"], api_key=CLIENT_CONFIG["api_key"]),
        mode=instructor.Mode.JSON
    )
    
    all_results = {"nodes": [], "relationships": []}
    failed_chunks = []  # 记录失败的块，便于后续重试
    
    # 3. 串行处理 (避免触发 RPM 限制)
    print(f"⚡ 开始串行提取 (每次请求间隔 {REQUEST_DELAY} 秒)...")
    start_time = time.time()
    
    for i, chunk in enumerate(chunks):
        print(f"[{i+1}/{len(chunks)}] 处理中: {chunk.metadata['section']}...", end=" ")
        
        try:
            data = process_single_chunk(chunk, client)
            
            if data:
                all_results["nodes"].extend(data["nodes"])
                all_results["relationships"].extend(data["relationships"])
                print(f"✓ 提取了 {len(data['nodes'])} 个节点")
            else:
                failed_chunks.append(chunk)
                print("✗ 失败")
                
        except Exception as exc:
            print(f"✗ 异常: {exc}")
            failed_chunks.append(chunk)
        
        # 添加延迟，避免触发 RPM 限制
        if i < len(chunks) - 1:  # 最后一个不需要等待
            time.sleep(REQUEST_DELAY)

    duration = time.time() - start_time
    print(f"\n{'='*50}")
    print(f"✅ 处理完毕! 耗时: {duration:.2f}秒")
    print(f"📊 提取统计: 节点 {len(all_results['nodes'])} 个, 关系 {len(all_results['relationships'])} 条")
    
    if failed_chunks:
        print(f"⚠️  失败的块: {len(failed_chunks)} 个")
        for fc in failed_chunks:
            print(f"   - {fc.metadata['section']}")
    
    # 4. 保存结果
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"💾 结果已保存至: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
