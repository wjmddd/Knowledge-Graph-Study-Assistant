"""
构建向量数据库
将教材的文本块嵌入到 ChromaDB 中

用法: python scripts/build_vector_store.py
"""

import sys
import json
import time
from pathlib import Path
from typing import List, Dict

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import MD_INPUT_DIR, CHROMA_DB_DIR
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


def load_text_chunks_from_json(json_file: Path) -> List[Dict]:
    """
    从已构建的知识图谱 JSON 加载 TextChunk 节点
    """
    chunks = []
    
    if not json_file.exists():
        print(f"⚠️ 文件不存在: {json_file}")
        return chunks
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 查找 TextChunk 节点
    nodes = data.get("nodes", [])
    for node in nodes:
        if node.get("label") == "TextChunk":
            content = node.get("content", "")
            if content and len(content) > 50:  # 过滤太短的
                chunks.append({
                    "content": content,
                    "chapter": node.get("chapter_id", "未知").replace("chapter_", "第").replace("_", " "),
                    "section": "未知",
                    "chunk_id": node.get("id", "")
                })
    
    return chunks


def build_vector_store(
    source: str = "md",
    clear_existing: bool = False,
    batch_size: int = 20
) -> None:
    """
    构建向量存储
    
    Args:
        source: 数据来源 ("md" 或 "json")
        clear_existing: 是否清空已有数据
        batch_size: 每批处理的文档数量
    """
    print("=" * 60)
    print("🔧 构建向量数据库 (ChromaDB)")
    print("=" * 60)
    
    # 1. 初始化向量存储
    print(f"\n📂 向量数据库路径: {CHROMA_DB_DIR}")
    store = VectorStore()
    
    existing_count = store.count()
    print(f"   已有文档数: {existing_count}")
    
    if clear_existing and existing_count > 0:
        confirm = input("⚠️  是否清空已有数据? (y/N): ")
        if confirm.lower() == 'y':
            store.clear()
            print("   ✓ 已清空")
    
    # 2. 加载文本块
    print(f"\n📖 加载文本块 (来源: {source})...")
    
    if source == "md":
        chunks = load_text_chunks_from_md(MD_INPUT_DIR)
    else:
        # 尝试从 JSON 加载
        json_file = Path("graph_data_final.json")
        if not json_file.exists():
            json_file = Path("graph_data_all_flat.json")
        chunks = load_text_chunks_from_json(json_file)
    
    if not chunks:
        print("❌ 未找到任何文本块")
        return
    
    print(f"   总计: {len(chunks)} 个文本块")
    
    # 3. 批量添加到向量库
    print(f"\n🔄 生成向量并存储 (批次大小: {batch_size})...")
    
    total_batches = (len(chunks) - 1) // batch_size + 1
    
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        batch_num = i // batch_size + 1
        
        print(f"   [{batch_num}/{total_batches}] 处理 {len(batch)} 个文档...", end=" ", flush=True)
        
        documents = [c["content"] for c in batch]
        metadatas = [
            {
                "chapter": c["chapter"],
                "section": c["section"],
                "chunk_id": c["chunk_id"]
            }
            for c in batch
        ]
        ids = [c["chunk_id"] for c in batch]
        
        try:
            store.add_documents(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            print("✓")
        except Exception as e:
            print(f"✗ 错误: {e}")
        
        # 避免 API 限流
        if batch_num < total_batches:
            time.sleep(1)
    
    # 4. 验证
    print(f"\n📊 构建完成!")
    print(f"   文档总数: {store.count()}")
    
    # 测试搜索
    print("\n🔍 测试搜索 '什么是补码'...")
    results = store.search("什么是补码", top_k=3)
    for i, r in enumerate(results):
        print(f"\n   [{i+1}] 距离: {r['distance']:.4f}")
        print(f"       章节: {r['metadata'].get('chapter', '未知')}")
        print(f"       内容: {r['document'][:100]}...")
    
    print("\n" + "=" * 60)
    print("✅ 向量数据库构建完成!")
    print("=" * 60)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="构建向量数据库")
    parser.add_argument(
        "--source",
        choices=["md", "json"],
        default="md",
        help="数据来源: md (Markdown文件) 或 json (知识图谱JSON)"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="清空已有数据"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=20,
        help="批处理大小"
    )
    
    args = parser.parse_args()
    
    build_vector_store(
        source=args.source,
        clear_existing=args.clear,
        batch_size=args.batch_size
    )


if __name__ == "__main__":
    main()

