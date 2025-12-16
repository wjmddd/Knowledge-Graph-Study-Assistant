import os
import re
import json
import time
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed

import instructor
from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError

# 引入您定义好的数据模型
from model.model import ExtractionResult

# ================= 配置区域 =================
# 推荐使用 DeepSeek 官方 API (更稳定、更便宜)
# 获取 Key: https://platform.deepseek.com

CLIENT_CONFIG = {
    # === 方案1: DeepSeek 官方 (推荐) ===
    # "api_key": "sk-xxx",  # 替换为你的 DeepSeek API Key
    # "base_url": "https://api.deepseek.com/v1",
    # "model": "deepseek-chat"
    
    # === 方案2: SiliconFlow 免费模型 ===
    "api_key": "sk-hvddzbgdsripcadgvqozwnhsyfkedgbbqaqlcagawltfxnxd",
    "base_url": "https://api.siliconflow.cn/v1",
    "model": "Qwen/Qwen3-VL-32B-Instruct"  # 免费
}

INPUT_FILE = "第一章.md"
OUTPUT_FILE = "graph_data_full.json"
MAX_WORKERS = 1  # 并发线程数 (建议设为1，避免触发速率限制)
REQUEST_DELAY = 2  # 每次请求后等待秒数 (防止 RPM 限制)
CHUNK_SIZE = 1000  # 每个切片的大致字符数
# ===========================================

# --- 1. 数据结构定义 ---

class ContextChunk(BaseModel):
    """
    带有层级上下文的文本块
    """
    content: str
    metadata: Dict[str, str] = Field(
        default_factory=lambda: {"chapter": "未知", "section": "前言"}
    )

    def to_prompt(self) -> str:
        """生成带上下文的 Prompt"""
        return f"""
        [上下文信息]
        所属章节: {self.metadata.get('chapter', '未知')}
        所属小节: {self.metadata.get('section', '未知')}
        
        [待分析文本]
        {self.content}
        """

# --- 2. Markdown 层级解析器 ---

def parse_markdown_with_context(file_path: str) -> List[ContextChunk]:
    """
    解析 Markdown，按章节切分，并注入层级上下文
    """
    chunks = []
    
    current_chapter = "第1章 计算机系统概述" # 默认初始章节
    current_section = "概述"
    buffer = []
    
    # 正则匹配标题: # 1.1 或 # 第1章
    # 注意：您的 Markdown 全是 # 开头，所以我们需要靠内容区分
    chapter_pattern = re.compile(r'^#\s+第.+章')
    section_pattern = re.compile(r'^#\s+\d+\.\d+')
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # 检查是否是新标题
        is_chapter = chapter_pattern.match(line)
        is_section = section_pattern.match(line)
        
        if line.startswith('#') and (is_chapter or is_section):
            # 1. 保存上一个缓冲区的内容（如果非空）
            if buffer:
                full_text = "\n".join(buffer)
                # 如果文本太长，还可以进行二次切分 (这里简化处理，直接作为一个块)
                chunks.append(ContextChunk(
                    content=full_text,
                    metadata={
                        "chapter": current_chapter,
                        "section": current_section
                    }
                ))
                buffer = []
            
            # 2. 更新上下文指针
            if is_chapter:
                current_chapter = line.replace('#', '').strip()
                current_section = "概述" # 重置小节
            elif is_section:
                current_section = line.replace('#', '').strip()
                
        else:
            # 普通文本，加入缓冲区
            buffer.append(line)
            
    # 处理文件末尾的最后一块
    if buffer:
        chunks.append(ContextChunk(
            content="\n".join(buffer),
            metadata={"chapter": current_chapter, "section": current_section}
        ))
        
    return chunks

# --- 3. LLM 提取工作流 ---

# System Prompt 模板：与 model.py 中的 Schema 严格对齐
SYSTEM_PROMPT = """
你是一位计算机系统领域的专家。你的任务是从给定的教材文本中提取结构化的知识图谱数据。

## 实体类型 (label)
请识别以下 5 种实体类型：
- Concept: 核心概念，如 "存储程序"、"冯·诺依曼结构"、"时钟周期"
- Hardware: 硬件组件，如 "CPU"、"ALU"、"主存"、"总线"
- Instruction: 机器/汇编指令，如 "movq"、"lw"、"sw"
- CodeSnippet: 代码示例片段
- Principle: 重要原理/定律，如 "摩尔定律"、"局部性原理"

## 实体 ID 格式
ID 必须使用格式: `{类型前缀}_{英文名小写}`
- Concept → concept_xxx，如 concept_stored_program
- Hardware → hw_xxx，如 hw_cpu, hw_alu
- Instruction → inst_xxx，如 inst_movq
- CodeSnippet → code_xxx，如 code_hello_world
- Principle → principle_xxx，如 principle_moore_law

## 关系类型 (type) - 针对《计算机系统基础》优化
只能使用以下关系类型：

### 分类与组成
- IS_A: 分类关系，A 是 B 的一种 (如: SRAM IS_A 存储器)
- COMPOSED_OF: 组成关系，A 由 B 组成 (如: CPU COMPOSED_OF ALU)

### 依赖与实现
- DEPENDS_ON: 学习依赖，学 A 前需先懂 B (如: 虚拟内存 DEPENDS_ON 页表)
- IMPLEMENTED_BY: 实现关系，A 由 B 实现 (如: 加法运算 IMPLEMENTED_BY 加法器)
- USES: 使用关系，A 使用 B (如: 程序 USES 寄存器)

### 对比与等价 (计算机系统中非常常见!)
- CONTRASTS_WITH: 对比关系，A 与 B 形成对比 (如: 大端法 CONTRASTS_WITH 小端法)
- EQUIVALENT_TO: 等价关系，A 与 B 在某层面等价 (如: 补码加法 EQUIVALENT_TO 无符号加法)

### 转换与流程
- CONVERTS_TO: 转换关系，A 转换为 B (如: 虚拟地址 CONVERTS_TO 物理地址)
- PRECEDES: 顺序关系，A 在 B 之前 (如: 取指阶段 PRECEDES 译码阶段)

### 因果与优化
- CAUSES: 因果关系，A 导致 B (如: 整数溢出 CAUSES 程序错误)
- OPTIMIZES: 优化关系，A 优化 B (如: Cache OPTIMIZES 内存访问速度)

### 指令与示例
- OPERATES_ON: 指令操作概念 (如: movq OPERATES_ON 寄存器)
- EXAMPLE_OF: 举例关系 (如: hello.c EXAMPLE_OF C语言程序)

### 兜底
- RELATED_TO: 通用关联（仅当以上都不适用时使用）

## 提取原则
1. **原子性**: 实体名称应简洁，如 "CPU" 而非 "中央处理器CPU"
2. **去代词化**: 不要提取 "它"、"该系统" 等模糊指代
3. **关系完整**: source_id 和 target_id 必须是你提取的节点的 id
4. **优先级**: 优先使用具体关系(如 CONTRASTS_WITH)，而非 RELATED_TO
5. **对比敏感**: 遇到 "vs"、"而"、"相反" 等词时，考虑使用 CONTRASTS_WITH
"""

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

# --- 4. 主程序 ---

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