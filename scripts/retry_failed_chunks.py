"""
重试失败的文本块
从 failed_chunks.json 读取失败列表，重新处理并更新对应章节文件

用法: 
  python scripts/retry_failed_chunks.py              # 重试所有失败的块
  python scripts/retry_failed_chunks.py --chapter 3  # 只重试第3章的失败块
"""

import sys
import json
import time
import re
import argparse
from pathlib import Path

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent))

import instructor
from openai import OpenAI

from config.settings import CLIENT_CONFIG, REQUEST_DELAY
from src.pipeline.parser import parse_markdown_with_context
from src.pipeline.extractor import process_single_chunk

# ========== 配置 ==========
MD_DIR = Path("md")
CHAPTERS_DIR = Path("data/chapters")
FAILED_FILE = "failed_chunks.json"
# ==========================


def load_failed_chunks() -> list:
    """加载失败的块列表"""
    if not Path(FAILED_FILE).exists():
        print(f"❌ 未找到失败记录文件: {FAILED_FILE}")
        print("   请先运行 build_kg_all.py")
        return []
    
    with open(FAILED_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_chapter_num(file_name: str) -> int:
    """从文件名提取章节号"""
    ch_map = {"一":1,"二":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9,"十":10}
    match = re.search(r'第(.+?)章', file_name)
    if match:
        return ch_map.get(match.group(1), 0)
    return 0


def load_chapter_data(chapter_num: int) -> dict:
    """加载章节数据"""
    chapter_file = CHAPTERS_DIR / f"chapter_{chapter_num:02d}.json"
    if chapter_file.exists():
        with open(chapter_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"metadata": {}, "nodes": [], "relationships": []}


def save_chapter_data(chapter_num: int, data: dict):
    """保存章节数据"""
    chapter_file = CHAPTERS_DIR / f"chapter_{chapter_num:02d}.json"
    with open(chapter_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description="重试失败的文本块")
    parser.add_argument("--chapter", type=int, help="只重试指定章节")
    parser.add_argument("--max", type=int, default=100, help="最大重试数量")
    args = parser.parse_args()
    
    print("=" * 60)
    print("🔄 重试失败的文本块")
    print("=" * 60)
    
    # 1. 加载失败列表
    failed_chunks = load_failed_chunks()
    if not failed_chunks:
        return
    
    print(f"📋 找到 {len(failed_chunks)} 个失败的块")
    
    # 过滤指定章节
    if args.chapter:
        failed_chunks = [
            fc for fc in failed_chunks 
            if get_chapter_num(fc["file"]) == args.chapter
        ]
        print(f"   过滤后: {len(failed_chunks)} 个 (第{args.chapter}章)")
    
    if not failed_chunks:
        print("✅ 没有需要重试的块")
        return
    
    # 限制数量
    if len(failed_chunks) > args.max:
        failed_chunks = failed_chunks[:args.max]
        print(f"   限制为: {len(failed_chunks)} 个")
    
    # 2. 按文件分组
    chunks_by_file = {}
    for fc in failed_chunks:
        file_name = fc["file"]
        if file_name not in chunks_by_file:
            chunks_by_file[file_name] = []
        chunks_by_file[file_name].append(fc)
    
    print(f"\n📂 涉及 {len(chunks_by_file)} 个文件:")
    for fn, chunks in chunks_by_file.items():
        print(f"   - {fn}: {len(chunks)} 个块")
    
    # 3. 初始化 LLM 客户端
    print(f"\n🤖 使用模型: {CLIENT_CONFIG['model']}")
    client = instructor.from_openai(
        OpenAI(base_url=CLIENT_CONFIG["base_url"], api_key=CLIENT_CONFIG["api_key"]),
        mode=instructor.Mode.JSON
    )
    
    # 4. 逐文件重试
    total_success = 0
    total_failed = 0
    still_failed = []
    
    for file_name, failed_list in chunks_by_file.items():
        chapter_num = get_chapter_num(file_name)
        print(f"\n📘 处理: {file_name} (第{chapter_num}章)")
        
        # 解析该文件获取所有 chunks
        md_file = MD_DIR / file_name
        if not md_file.exists():
            print(f"   ⚠️ 文件不存在: {md_file}")
            continue
        
        all_chunks = parse_markdown_with_context(str(md_file))
        
        # 加载已有的章节数据
        chapter_data = load_chapter_data(chapter_num)
        
        # 重试失败的块
        for fc in failed_list:
            idx = fc["index"]
            section = fc.get("section", "未知")
            
            if idx >= len(all_chunks):
                print(f"   ⚠️ 索引超出范围: {idx}")
                still_failed.append(fc)
                continue
            
            chunk = all_chunks[idx]
            print(f"   [{idx}] {section[:30]}...", end=" ", flush=True)
            
            try:
                data = process_single_chunk(chunk, client)
                
                if data:
                    # 添加到章节数据
                    chapter_data["nodes"].extend(data.get("nodes", []))
                    chapter_data["relationships"].extend(data.get("relationships", []))
                    
                    node_count = len(data.get("nodes", []))
                    rel_count = len(data.get("relationships", []))
                    print(f"✓ 节点:{node_count} 关系:{rel_count}")
                    total_success += 1
                else:
                    print("✗ 仍然失败")
                    still_failed.append(fc)
                    total_failed += 1
                    
            except Exception as e:
                print(f"✗ 异常: {str(e)[:40]}")
                still_failed.append(fc)
                total_failed += 1
            
            time.sleep(REQUEST_DELAY)
        
        # 更新章节元数据
        chapter_data["metadata"]["node_count"] = len(chapter_data["nodes"])
        chapter_data["metadata"]["relationship_count"] = len(chapter_data["relationships"])
        
        # 保存更新后的章节数据
        save_chapter_data(chapter_num, chapter_data)
        print(f"   💾 已更新: chapter_{chapter_num:02d}.json")
    
    # 5. 更新失败列表
    if still_failed:
        with open(FAILED_FILE, 'w', encoding='utf-8') as f:
            json.dump(still_failed, f, ensure_ascii=False, indent=2)
        print(f"\n⚠️  仍有 {len(still_failed)} 个块失败，已更新 {FAILED_FILE}")
    else:
        # 删除失败文件
        Path(FAILED_FILE).unlink(missing_ok=True)
        print(f"\n✅ 所有块重试成功，已删除 {FAILED_FILE}")
    
    # 6. 统计
    print("\n" + "=" * 60)
    print("📊 重试统计")
    print("=" * 60)
    print(f"   成功: {total_success} 个")
    print(f"   失败: {total_failed} 个")
    print("=" * 60)


if __name__ == "__main__":
    main()

