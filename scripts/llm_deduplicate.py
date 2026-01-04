"""
使用 LLM 智能识别重复节点并合并
比规则匹配更智能，能识别语义相似的实体

用法: python scripts/llm_deduplicate.py
"""

import json
import sys
import time
from pathlib import Path
from typing import List, Dict, Tuple
from collections import defaultdict

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent))

import instructor
from openai import OpenAI
from pydantic import BaseModel, Field

from config.settings import CLIENT_CONFIG

# ========== 配置 ==========
INPUT_FILE = "graph_data_rule_deduped.json"  # 规则去重后的图谱（来自 deduplicate_nodes.py）
OUTPUT_FILE = "graph_data_final.json"  # 最终去重后的图谱
BATCH_SIZE = 25  # 每批发送给 LLM 的节点数量（避免 token 超限）
REQUEST_DELAY = 2  # 每次请求间隔（秒）
# ==========================


# ==========================================
# 1. LLM 输出的数据结构
# ==========================================

class DuplicatePair(BaseModel):
    """一对重复的节点"""
    node_id_1: str = Field(..., description="第一个节点的 ID")
    node_id_2: str = Field(..., description="第二个节点的 ID")
    canonical_id: str = Field(..., description="应该保留的标准节点 ID（通常选择更规范的那个）")
    reason: str = Field(..., description="判断为重复的原因")
    confidence: float = Field(..., description="置信度 0-1，1 表示确定是重复")


class DeduplicationResult(BaseModel):
    """LLM 去重结果"""
    duplicates: List[DuplicatePair] = Field(
        default_factory=list,
        description="识别出的重复节点对列表"
    )


# ==========================================
# 2. Prompt 模板
# ==========================================

DEDUP_SYSTEM_PROMPT = """你是一位计算机科学领域的知识图谱专家。你的任务是从一组实体节点中识别出**语义重复**的节点对。

## 重复的判断标准

以下情况应判定为重复：
1. **同一概念的中英文表达**: 如 "CPU" 和 "中央处理器"
2. **同一概念的不同写法**: 如 "冯·诺依曼" 和 "冯诺依曼"
3. **概念与其定义混淆**: 如 "存储程序" 和 "存储程序工作方式"
4. **缩写与全称**: 如 "ALU" 和 "算术逻辑单元"
5. **同义词**: 如 "主存" 和 "内存" 和 "RAM"

以下情况**不是**重复：
1. **相关但不同的概念**: 如 "CPU" 和 "GPU" 是不同的处理器
2. **包含关系**: 如 "CPU" 包含 "ALU"，但它们不是重复
3. **同类但不同实例**: 如 "SRAM" 和 "DRAM" 都是存储器，但不是重复

## 输出要求

1. 只输出你**高度确信**是重复的节点对
2. canonical_id 应选择更规范、更常用的那个（优先英文缩写或标准术语）
3. confidence 表示你的确信程度：
   - 1.0: 绝对确定（如 CPU = 中央处理器）
   - 0.9: 非常确定（如 冯·诺依曼 = 冯诺依曼）
   - 0.8: 比较确定（如 存储程序 ≈ 存储程序概念）
   - < 0.8: 不够确定，不要输出

4. 如果没有发现重复，返回空列表
"""

def create_dedup_prompt(nodes: List[dict]) -> str:
    """创建去重 Prompt"""
    node_list = []
    for node in nodes:
        node_id = node.get("id", "")
        name = node.get("name", "")
        label = node.get("label", "")
        alias = node.get("alias", [])
        definition = node.get("definition", "") or node.get("description", "")
        
        node_info = f"- ID: {node_id}\n  名称: {name}\n  类型: {label}"
        if alias:
            node_info += f"\n  别名: {', '.join(alias)}"
        if definition:
            node_info += f"\n  定义: {definition[:100]}..."
        node_list.append(node_info)
    
    return f"""请分析以下 {len(nodes)} 个知识节点，找出其中语义重复的节点对：

{chr(10).join(node_list)}

请识别出所有重复的节点对。如果没有重复，返回空列表。"""


# ==========================================
# 3. LLM 去重逻辑
# ==========================================

def find_duplicates_with_llm(
    nodes: List[dict], 
    client,
    node_type: str
) -> List[DuplicatePair]:
    """
    使用 LLM 识别一批节点中的重复项
    """
    if len(nodes) < 2:
        return []
    
    prompt = create_dedup_prompt(nodes)
    
    try:
        result = client.chat.completions.create(
            model=CLIENT_CONFIG["model"],
            response_model=DeduplicationResult,
            messages=[
                {"role": "system", "content": DEDUP_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.0
        )
        
        # 过滤低置信度的结果
        valid_duplicates = [d for d in result.duplicates if d.confidence >= 0.8]
        return valid_duplicates
        
    except Exception as e:
        print(f"      ⚠️ LLM 调用失败: {e}")
        return []


def batch_find_duplicates(
    nodes: List[dict],
    client,
    node_type: str,
    batch_size: int = BATCH_SIZE
) -> List[DuplicatePair]:
    """
    分批处理节点，避免 Token 超限
    包含跨批次检查逻辑
    """
    all_duplicates = []
    
    # 如果节点数量较少，直接处理
    if len(nodes) <= batch_size:
        return find_duplicates_with_llm(nodes, client, node_type)
    
    # ========== 阶段 1: 批次内检查 ==========
    total_batches = (len(nodes) - 1) // batch_size + 1
    batch_representatives = []  # 每批的代表性节点
    
    for i in range(0, len(nodes), batch_size):
        batch = nodes[i:i + batch_size]
        batch_num = i // batch_size + 1
        print(f"      批次内检查 {batch_num}/{total_batches} ({len(batch)} 个节点)...", end=" ", flush=True)
        
        duplicates = find_duplicates_with_llm(batch, client, node_type)
        all_duplicates.extend(duplicates)
        
        # 收集该批的代表性节点（取前3个 + 检测出重复的节点）
        found_ids = set()
        for d in duplicates:
            found_ids.add(d.node_id_1)
            found_ids.add(d.node_id_2)
        
        # 每批取前3个作为代表
        for node in batch[:3]:
            if node.get("id") not in found_ids:
                batch_representatives.append(node)
        
        if duplicates:
            print(f"发现 {len(duplicates)} 组重复")
        else:
            print("✓")
        
        # 添加延迟
        if batch_num < total_batches:
            time.sleep(REQUEST_DELAY)
    
    # ========== 阶段 2: 跨批次检查 ==========
    if len(batch_representatives) > batch_size and total_batches > 1:
        print(f"      跨批次检查 ({len(batch_representatives)} 个代表节点)...")
        
        # 对代表性节点再做一轮检查
        cross_batch_duplicates = []
        cross_batches = (len(batch_representatives) - 1) // batch_size + 1
        
        for i in range(0, len(batch_representatives), batch_size):
            cross_batch = batch_representatives[i:i + batch_size]
            cb_num = i // batch_size + 1
            print(f"         跨批次 {cb_num}/{cross_batches}...", end=" ", flush=True)
            
            duplicates = find_duplicates_with_llm(cross_batch, client, node_type)
            
            # 过滤已发现的重复
            existing_pairs = set()
            for d in all_duplicates:
                pair = tuple(sorted([d.node_id_1, d.node_id_2]))
                existing_pairs.add(pair)
            
            new_duplicates = []
            for d in duplicates:
                pair = tuple(sorted([d.node_id_1, d.node_id_2]))
                if pair not in existing_pairs:
                    new_duplicates.append(d)
                    existing_pairs.add(pair)
            
            cross_batch_duplicates.extend(new_duplicates)
            
            if new_duplicates:
                print(f"发现 {len(new_duplicates)} 组新重复")
            else:
                print("✓")
            
            time.sleep(REQUEST_DELAY)
        
        all_duplicates.extend(cross_batch_duplicates)
        
        if cross_batch_duplicates:
            print(f"      跨批次共发现 {len(cross_batch_duplicates)} 组新重复")
    
    return all_duplicates


# ==========================================
# 4. 合并逻辑
# ==========================================

def merge_nodes(node1: dict, node2: dict, keep_id: str) -> dict:
    """合并两个节点，保留更完整的信息"""
    keep_node = node1 if node1.get("id") == keep_id else node2
    other_node = node2 if node1.get("id") == keep_id else node1
    
    merged = dict(keep_node)
    
    # 合并别名
    aliases = set(keep_node.get("alias", []))
    aliases.update(other_node.get("alias", []))
    aliases.add(other_node.get("name", ""))
    aliases.discard(keep_node.get("name", ""))
    merged["alias"] = list(aliases)
    
    # 合并定义（保留更长的）
    for field in ["definition", "description"]:
        val1 = keep_node.get(field) or ""
        val2 = other_node.get(field) or ""
        if len(val2) > len(val1):
            merged[field] = val2
    
    return merged


def apply_deduplication(data: dict, duplicates: List[DuplicatePair]) -> dict:
    """应用去重结果到图谱数据"""
    
    # 构建合并映射
    merge_map = {}  # old_id -> canonical_id
    for dup in duplicates:
        if dup.node_id_1 != dup.canonical_id:
            merge_map[dup.node_id_1] = dup.canonical_id
        if dup.node_id_2 != dup.canonical_id:
            merge_map[dup.node_id_2] = dup.canonical_id
    
    # 构建节点字典
    nodes_dict = {n.get("id"): n for n in data.get("nodes", [])}
    
    # 合并节点
    for dup in duplicates:
        canonical_id = dup.canonical_id
        other_id = dup.node_id_1 if dup.node_id_2 == canonical_id else dup.node_id_2
        
        if canonical_id in nodes_dict and other_id in nodes_dict:
            nodes_dict[canonical_id] = merge_nodes(
                nodes_dict[canonical_id],
                nodes_dict[other_id],
                canonical_id
            )
    
    # 过滤被合并的节点
    new_nodes = [
        node for node in data.get("nodes", [])
        if node.get("id") not in merge_map or merge_map[node.get("id")] == node.get("id")
    ]
    
    # 更新节点内容
    for i, node in enumerate(new_nodes):
        node_id = node.get("id")
        if node_id in nodes_dict:
            new_nodes[i] = nodes_dict[node_id]
    
    # 更新关系
    new_relationships = []
    seen_rels = set()
    
    for rel in data.get("relationships", []):
        source_id = rel.get("source_id")
        target_id = rel.get("target_id")
        rel_type = rel.get("type")
        
        # 替换被合并的 ID
        new_source = merge_map.get(source_id, source_id)
        new_target = merge_map.get(target_id, target_id)
        
        # 避免自环和重复
        if new_source == new_target:
            continue
        
        rel_key = (new_source, new_target, rel_type)
        if rel_key in seen_rels:
            continue
        seen_rels.add(rel_key)
        
        new_rel = dict(rel)
        new_rel["source_id"] = new_source
        new_rel["target_id"] = new_target
        new_relationships.append(new_rel)
    
    return {
        "nodes": new_nodes,
        "relationships": new_relationships
    }


# ==========================================
# 5. 主程序
# ==========================================

def main():
    print("=" * 60)
    print("🤖 LLM 智能节点去重")
    print("=" * 60)
    print(f"📡 使用模型: {CLIENT_CONFIG['model']}")
    
    # 1. 加载数据
    print(f"\n📂 加载数据: {INPUT_FILE}")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    nodes = data.get("nodes", [])
    relationships = data.get("relationships", [])
    print(f"   节点: {len(nodes)} 个")
    print(f"   关系: {len(relationships)} 条")
    
    # 2. 初始化 LLM 客户端
    client = instructor.from_openai(
        OpenAI(base_url=CLIENT_CONFIG["base_url"], api_key=CLIENT_CONFIG["api_key"]),
        mode=instructor.Mode.JSON
    )
    
    # 3. 按类型分组（只对知识语义层去重）
    knowledge_labels = ["Concept", "Hardware", "Instruction", "Principle", "CodeSnippet"]
    nodes_by_type = defaultdict(list)
    
    for node in nodes:
        label = node.get("label", "")
        if label in knowledge_labels:
            nodes_by_type[label].append(node)
    
    # 4. 逐类型查找重复
    print(f"\n🔍 开始 LLM 智能去重...")
    all_duplicates = []
    
    for node_type, type_nodes in nodes_by_type.items():
        if len(type_nodes) < 2:
            continue
            
        print(f"\n   📦 处理 {node_type} ({len(type_nodes)} 个节点)...")
        duplicates = batch_find_duplicates(type_nodes, client, node_type)
        
        if duplicates:
            print(f"      发现 {len(duplicates)} 组重复:")
            for dup in duplicates:
                print(f"      - {dup.node_id_1} ≈ {dup.node_id_2}")
                print(f"        原因: {dup.reason}")
                print(f"        保留: {dup.canonical_id} (置信度: {dup.confidence})")
            all_duplicates.extend(duplicates)
        else:
            print(f"      ✓ 未发现重复")
    
    # 5. 应用去重
    if all_duplicates:
        print(f"\n🔧 应用去重 ({len(all_duplicates)} 组)...")
        deduped_data = apply_deduplication(data, all_duplicates)
        
        new_nodes = deduped_data.get("nodes", [])
        new_relationships = deduped_data.get("relationships", [])
        
        print(f"\n📊 去重统计:")
        print(f"   节点: {len(nodes)} → {len(new_nodes)} (减少 {len(nodes) - len(new_nodes)})")
        print(f"   关系: {len(relationships)} → {len(new_relationships)} (减少 {len(relationships) - len(new_relationships)})")
        
        # 保存结果
        print(f"\n💾 保存到: {OUTPUT_FILE}")
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(deduped_data, f, ensure_ascii=False, indent=2)
        
        # 保存去重报告
        report_file = OUTPUT_FILE.replace('.json', '_report.json')
        report = {
            "total_duplicates": len(all_duplicates),
            "duplicates": [d.model_dump() for d in all_duplicates]
        }
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"📄 去重报告: {report_file}")
        
    else:
        print(f"\n✓ 未发现需要合并的重复节点")
    
    print("\n" + "=" * 60)
    print("✅ LLM 去重完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()

