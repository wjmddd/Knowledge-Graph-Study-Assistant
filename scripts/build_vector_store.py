"""
构建向量数据库
将教材的文本块向量化并存入 Neo4j

用法: python scripts/build_vector_store.py
"""

import sys
import time
from pathlib import Path
from typing import List, Dict

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import MD_INPUT_DIR
from src.pipeline.parser import parse_markdown_with_context
from src.retrieval.vector_store import VectorStore


def load_text_chunks_from_md(md_dir: Path) -> List[Dict]:
    """
    从 Markdown 文件加载文本块
    """
    chunks = []
    
    # 按章节顺序处理
    md_files = sorted(md_dir.glob("第*章.md"))
    
    for md_file in md_files:
        chapter_name = md_file.stem
        print(f"   📖 解析: {chapter_name}")
        
        # 使用已有的解析器
        context_chunks = parse_markdown_with_context(str(md_file))
        
        for i, chunk in enumerate(context_chunks):
            chunks.append({
                "content": chunk.content,
                "chapter": chunk.metadata.get("chapter", chapter_name),
                "section": chunk.metadata.get("section", "未知"),
                "chunk_id": f"{chapter_name}_chunk_{i+1}"
            })
    
    return chunks


def build_vector_store(
    clear_existing: bool = False,
    batch_size: int = 10
) -> None:
    """
    构建向量存储
    
    Args:
        clear_existing: 是否清空已有向量
        batch_size: 每批处理的文档数量
    """
    print("=" * 60)
    print("🔧 构建向量数据库 (Neo4j 向量索引)")
    print("=" * 60)
    
    # 1. 初始化向量存储
    print(f"\n📂 连接 Neo4j...")
    store = VectorStore()
    
    if not store.is_connected():
        print("❌ 无法连接到 Neo4j，请确保 Neo4j 已启动")
        return
    
    # 2. 创建向量索引
    print("\n📇 创建向量索引...")
    store.create_vector_index()
    
    existing_count = store.count()
    print(f"   已有向量化文档: {existing_count}")
    
    if clear_existing and existing_count > 0:
        confirm = input("⚠️  是否清空已有向量? (y/N): ")
        if confirm.lower() == 'y':
            store.clear()
            print("   ✓ 已清空")
    
    # 3. 加载文本块
    print(f"\n📖 加载 Markdown 文本块...")
    chunks = load_text_chunks_from_md(MD_INPUT_DIR)
    
    if not chunks:
        print("❌ 未找到任何文本块")
        store.close()
        return
    
    print(f"   总计: {len(chunks)} 个文本块")
    
    # 4. 批量添加到向量库
    print(f"\n🔄 生成向量并存储 (批次大小: {batch_size})...")
    
    total_batches = (len(chunks) - 1) // batch_size + 1
    total_success = 0
    
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        batch_num = i // batch_size + 1
        
        print(f"   [{batch_num}/{total_batches}] 处理 {len(batch)} 个文档...", end=" ", flush=True)
        
        documents = [c["content"] for c in batch]
        metadatas = [
            {
                "chapter": c["chapter"],
                "section": c["section"],
            }
            for c in batch
        ]
        ids = [c["chunk_id"] for c in batch]
        
        try:
            success = store.add_documents(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            total_success += success
            print(f"✓ ({success}/{len(batch)})")
        except Exception as e:
            print(f"✗ 错误: {e}")
        
        # 避免 API 限流
        if batch_num < total_batches:
            time.sleep(1)
    
    # 5. 验证
    print(f"\n📊 构建完成!")
    print(f"   成功向量化: {total_success} 个文档")
    print(f"   当前向量总数: {store.count()}")
    
    # 测试搜索
    print("\n🔍 测试搜索 '什么是补码'...")
    try:
        results = store.search("什么是补码", top_k=3)
        if results:
            for i, r in enumerate(results):
                print(f"\n   [{i+1}] 分数: {r.get('score', 0):.4f}")
                print(f"       章节: {r['metadata'].get('chapter', '未知')}")
                print(f"       内容: {r['document'][:80]}...")
        else:
            print("   未找到结果")
    except Exception as e:
        print(f"   搜索测试失败: {e}")
    
    store.close()
    
    print("\n" + "=" * 60)
    print("✅ 向量数据库构建完成!")
    print("=" * 60)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="构建 Neo4j 向量数据库")
    parser.add_argument(
        "--clear",
        action="store_true",
        help="清空已有向量"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="批处理大小 (默认10，避免API限流)"
    )
    
    args = parser.parse_args()
    
    build_vector_store(
        clear_existing=args.clear,
        batch_size=args.batch_size
    )


if __name__ == "__main__":
    main()
