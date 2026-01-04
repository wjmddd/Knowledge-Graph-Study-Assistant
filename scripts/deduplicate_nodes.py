"""
知识图谱节点去重与融合
解决 LLM 提取的重复实体问题，如 "缓存" vs "Cache"

用法: python scripts/deduplicate_nodes.py
"""

import json
import re
import sys
from pathlib import Path
from typing import List, Dict, Set, Tuple
from collections import defaultdict

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent))

# ========== 配置 ==========
INPUT_FILE = "graph_data_all_flat.json"  # 合并后的完整图谱
OUTPUT_FILE = "graph_data_rule_deduped.json"  # 规则去重后的输出
# ==========================

# ==========================================
# 1. 中英文计算机术语对照表 (针对《计算机系统基础》优化)
# ==========================================
TERM_MAPPINGS = {
    # ========== 硬件组件 ==========
    "cpu": ["中央处理器", "处理器", "central processing unit", "CPU"],
    "alu": ["算术逻辑单元", "运算器", "arithmetic logic unit", "ALU"],
    "cu": ["控制单元", "控制器", "control unit"],
    "pc": ["程序计数器", "program counter", "PC"],
    "ir": ["指令寄存器", "instruction register", "IR"],
    "mar": ["存储器地址寄存器", "memory address register", "MAR"],
    "mdr": ["存储器数据寄存器", "memory data register", "MDR"],
    "psw": ["程序状态字", "program status word", "PSW"],
    "cache": ["缓存", "高速缓存", "高速缓冲存储器", "Cache"],
    "ram": ["内存", "主存", "随机存取存储器", "主存储器", "random access memory", "RAM"],
    "rom": ["只读存储器", "read only memory", "ROM"],
    "sram": ["静态随机存取存储器", "static ram", "SRAM"],
    "dram": ["动态随机存取存储器", "dynamic ram", "DRAM"],
    "register": ["寄存器"],
    "bus": ["总线"],
    "mmu": ["内存管理单元", "memory management unit", "MMU"],
    "tlb": ["转换后备缓冲器", "页表缓存", "translation lookaside buffer", "TLB"],
    "gpu": ["图形处理器", "graphics processing unit", "GPU"],
    "ssd": ["固态硬盘", "solid state drive", "SSD"],
    "hdd": ["机械硬盘", "硬盘驱动器", "hard disk drive", "HDD"],
    
    # ========== 数据表示 ==========
    "two's complement": ["补码", "二进制补码", "2的补码"],
    "one's complement": ["反码", "1的补码"],
    "sign magnitude": ["原码", "符号-数值", "符号数值"],
    "floating point": ["浮点数", "浮点", "浮点表示"],
    "ieee 754": ["ieee754", "ieee 754标准", "浮点标准"],
    "mantissa": ["尾数", "有效数字"],
    "exponent": ["阶码", "指数"],
    "bias": ["偏置", "移码"],
    "big endian": ["大端", "大端法", "大端序"],
    "little endian": ["小端", "小端法", "小端序"],
    "sign extension": ["符号扩展"],
    "zero extension": ["零扩展"],
    "overflow": ["溢出", "上溢"],
    "underflow": ["下溢"],
    
    # ========== 指令与程序 ==========
    "instruction": ["指令"],
    "opcode": ["操作码", "op码"],
    "operand": ["操作数"],
    "immediate": ["立即数"],
    "program": ["程序"],
    "process": ["进程"],
    "thread": ["线程"],
    "isa": ["指令集架构", "instruction set architecture", "ISA"],
    "risc": ["精简指令集", "RISC"],
    "cisc": ["复杂指令集", "CISC"],
    "x86": ["x86架构", "x86指令集"],
    "mips": ["mips架构", "MIPS"],
    
    # ========== 存储层次 ==========
    "locality": ["局部性", "局部性原理"],
    "temporal locality": ["时间局部性"],
    "spatial locality": ["空间局部性"],
    "cache hit": ["缓存命中", "命中"],
    "cache miss": ["缓存未命中", "缓存缺失", "未命中"],
    "hit rate": ["命中率"],
    "miss rate": ["缺失率", "未命中率"],
    "write back": ["写回", "回写"],
    "write through": ["写直达", "直写"],
    "lru": ["最近最少使用", "least recently used", "LRU"],
    
    # ========== 虚拟存储 ==========
    "virtual memory": ["虚拟内存", "虚拟存储器", "虚存"],
    "virtual address": ["虚拟地址", "逻辑地址", "VA"],
    "physical address": ["物理地址", "实地址", "PA"],
    "page": ["页", "页面"],
    "page table": ["页表"],
    "page fault": ["缺页", "页故障", "缺页异常"],
    "page frame": ["页框", "物理页"],
    "segmentation": ["分段"],
    "paging": ["分页"],
    
    # ========== 流水线 ==========
    "pipeline": ["流水线"],
    "fetch": ["取指", "取指令"],
    "decode": ["译码", "解码"],
    "execute": ["执行"],
    "memory access": ["访存", "存储器访问"],
    "write back": ["写回"],
    "hazard": ["冒险", "冲突"],
    "data hazard": ["数据冒险", "数据冲突"],
    "control hazard": ["控制冒险", "控制冲突"],
    "structural hazard": ["结构冒险", "结构冲突"],
    "forwarding": ["转发", "旁路"],
    "stall": ["停顿", "阻塞"],
    "branch prediction": ["分支预测"],
    
    # ========== 程序转换 ==========
    "compiler": ["编译器", "编译程序"],
    "assembler": ["汇编器", "汇编程序"],
    "linker": ["链接器", "链接程序"],
    "loader": ["加载器", "装载器", "装入程序"],
    "preprocessor": ["预处理器"],
    "source code": ["源代码", "源程序"],
    "object code": ["目标代码", "目标程序"],
    "executable": ["可执行文件", "可执行程序"],
    
    # ========== 系统结构 ==========
    "von neumann": ["冯·诺依曼", "冯诺依曼", "冯·诺伊曼", "冯诺伊曼"],
    "stored program": ["存储程序", "存储程序原理"],
    "operating system": ["操作系统", "os", "OS"],
    "kernel": ["内核"],
    "system call": ["系统调用"],
    "interrupt": ["中断"],
    "exception": ["异常"],
    "trap": ["陷阱", "陷入"],
    
    # ========== I/O ==========
    "io": ["输入输出", "i/o", "I/O"],
    "dma": ["直接存储器存取", "direct memory access", "DMA"],
    "polling": ["轮询", "查询"],
    "interrupt driven": ["中断驱动"],
    
    # ========== 其他 ==========
    "stack": ["栈", "堆栈"],
    "heap": ["堆"],
    "amdahl's law": ["阿姆达尔定律", "amdahl定律"],
    "moore's law": ["摩尔定律", "moore定律"],
    "cpi": ["每条指令周期数", "cycles per instruction", "CPI"],
    "mips": ["每秒百万条指令", "million instructions per second"],
    "throughput": ["吞吐率", "吞吐量"],
    "latency": ["延迟", "时延"],
}

# 构建反向索引: 任意别名 -> 标准名称
ALIAS_TO_CANONICAL = {}
for canonical, aliases in TERM_MAPPINGS.items():
    ALIAS_TO_CANONICAL[canonical.lower()] = canonical
    for alias in aliases:
        ALIAS_TO_CANONICAL[alias.lower()] = canonical


def normalize_name(name: str) -> str:
    """
    标准化节点名称
    1. 转小写
    2. 移除空格和特殊字符
    3. 查找标准名称
    """
    if not name:
        return name
    
    # 清理名称
    clean_name = name.lower().strip()
    clean_name = re.sub(r'[·\-_\s]+', '', clean_name)  # 移除 · - _ 空格
    
    # 查找是否有对应的标准名称
    if clean_name in ALIAS_TO_CANONICAL:
        return ALIAS_TO_CANONICAL[clean_name]
    
    # 尝试原始名称（带空格）
    original_lower = name.lower().strip()
    if original_lower in ALIAS_TO_CANONICAL:
        return ALIAS_TO_CANONICAL[original_lower]
    
    return name  # 未找到映射，返回原名


def find_duplicate_candidates(nodes: List[dict]) -> List[Tuple[dict, dict, str]]:
    """
    查找潜在重复的节点对
    
    Returns:
        List of (node1, node2, reason) tuples
    """
    duplicates = []
    
    # 按节点类型分组
    nodes_by_type = defaultdict(list)
    for node in nodes:
        label = node.get("label", "Unknown")
        nodes_by_type[label].append(node)
    
    # 只对知识语义层节点进行去重
    knowledge_labels = ["Concept", "Hardware", "Instruction", "Principle", "CodeSnippet"]
    
    for label in knowledge_labels:
        type_nodes = nodes_by_type.get(label, [])
        
        for i, node1 in enumerate(type_nodes):
            name1 = node1.get("name", "")
            norm1 = normalize_name(name1)
            
            for j, node2 in enumerate(type_nodes):
                if j <= i:  # 避免重复比较
                    continue
                
                name2 = node2.get("name", "")
                norm2 = normalize_name(name2)
                
                # 检查标准化后是否相同
                if norm1 == norm2 and norm1 != name1:
                    duplicates.append((node1, node2, f"术语映射: {name1} ≈ {name2} → {norm1}"))
                    continue
                
                # 检查别名是否匹配
                aliases1 = set(a.lower() for a in node1.get("alias", []))
                aliases2 = set(a.lower() for a in node2.get("alias", []))
                
                if name1.lower() in aliases2 or name2.lower() in aliases1:
                    duplicates.append((node1, node2, f"别名匹配: {name1} ↔ {name2}"))
                    continue
                
                if aliases1 & aliases2:
                    common = aliases1 & aliases2
                    duplicates.append((node1, node2, f"共同别名: {common}"))
    
    return duplicates


def merge_nodes(node1: dict, node2: dict) -> dict:
    """
    合并两个节点，保留更完整的信息
    """
    merged = dict(node1)  # 以 node1 为基础
    
    # 合并别名
    aliases = set(node1.get("alias", []))
    aliases.update(node2.get("alias", []))
    aliases.add(node2.get("name", ""))  # 把 node2 的名称作为别名
    aliases.discard(node1.get("name", ""))  # 移除主名称
    merged["alias"] = list(aliases)
    
    # 合并定义（保留更长的）
    def1 = node1.get("definition") or ""
    def2 = node2.get("definition") or ""
    if len(def2) > len(def1):
        merged["definition"] = def2
    
    # 合并描述（保留更长的）
    desc1 = node1.get("description") or ""
    desc2 = node2.get("description") or ""
    if len(desc2) > len(desc1):
        merged["description"] = desc2
    
    return merged


def deduplicate_graph(data: dict, merge_map: Dict[str, str]) -> dict:
    """
    根据合并映射去重整个图谱
    
    Args:
        data: 原始图谱数据
        merge_map: {old_id: new_id} 映射表
    """
    # 1. 过滤并合并节点
    new_nodes = []
    seen_ids = set()
    
    for node in data.get("nodes", []):
        node_id = node.get("id")
        
        # 如果这个节点被合并到其他节点
        if node_id in merge_map and merge_map[node_id] != node_id:
            continue  # 跳过被合并的节点
        
        # 避免重复添加
        if node_id in seen_ids:
            continue
        
        seen_ids.add(node_id)
        new_nodes.append(node)
    
    # 2. 更新关系中的 ID
    new_relationships = []
    seen_rels = set()
    
    for rel in data.get("relationships", []):
        source_id = rel.get("source_id")
        target_id = rel.get("target_id")
        rel_type = rel.get("type")
        
        # 替换被合并的 ID
        new_source = merge_map.get(source_id, source_id)
        new_target = merge_map.get(target_id, target_id)
        
        # 避免自环
        if new_source == new_target:
            continue
        
        # 避免重复关系
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


def main():
    print("=" * 60)
    print("🔍 知识图谱节点去重与融合")
    print("=" * 60)
    
    # 1. 加载数据
    print(f"\n📂 加载数据: {INPUT_FILE}")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    nodes = data.get("nodes", [])
    relationships = data.get("relationships", [])
    print(f"   原始节点: {len(nodes)} 个")
    print(f"   原始关系: {len(relationships)} 条")
    
    # 2. 查找重复候选
    print("\n🔍 查找潜在重复节点...")
    duplicates = find_duplicate_candidates(nodes)
    
    if not duplicates:
        print("   ✓ 未发现明显重复节点")
        return
    
    print(f"   发现 {len(duplicates)} 组潜在重复:")
    print("-" * 60)
    
    merge_map = {}  # old_id -> new_id
    merged_nodes = {}  # new_id -> merged_node
    
    for i, (node1, node2, reason) in enumerate(duplicates):
        id1, name1 = node1.get("id"), node1.get("name")
        id2, name2 = node2.get("id"), node2.get("name")
        
        print(f"\n   [{i+1}] {reason}")
        print(f"       A: {name1} (id: {id1})")
        print(f"       B: {name2} (id: {id2})")
        
        # 自动决策：保留 ID 更短的那个（通常是更规范的）
        # 或者可以改成交互式让用户选择
        keep_id = id1 if len(id1) <= len(id2) else id2
        remove_id = id2 if keep_id == id1 else id1
        keep_node = node1 if keep_id == id1 else node2
        remove_node = node2 if keep_id == id1 else node1
        
        print(f"       → 保留: {keep_id}, 移除: {remove_id}")
        
        # 记录合并映射
        merge_map[remove_id] = keep_id
        
        # 合并节点信息
        if keep_id not in merged_nodes:
            merged_nodes[keep_id] = keep_node
        merged_nodes[keep_id] = merge_nodes(merged_nodes[keep_id], remove_node)
    
    print("\n" + "-" * 60)
    
    # 3. 更新节点
    print(f"\n📝 更新节点信息...")
    for i, node in enumerate(data["nodes"]):
        node_id = node.get("id")
        if node_id in merged_nodes:
            data["nodes"][i] = merged_nodes[node_id]
    
    # 4. 执行去重
    print(f"🔧 执行去重...")
    deduped_data = deduplicate_graph(data, merge_map)
    
    # 5. 统计
    new_nodes = deduped_data.get("nodes", [])
    new_relationships = deduped_data.get("relationships", [])
    
    print(f"\n📊 去重统计:")
    print(f"   节点: {len(nodes)} → {len(new_nodes)} (减少 {len(nodes) - len(new_nodes)})")
    print(f"   关系: {len(relationships)} → {len(new_relationships)} (减少 {len(relationships) - len(new_relationships)})")
    
    # 6. 保存
    print(f"\n💾 保存到: {OUTPUT_FILE}")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(deduped_data, f, ensure_ascii=False, indent=2)
    
    # 7. 保存合并报告
    report_file = OUTPUT_FILE.replace('.json', '_report.json')
    report = {
        "total_duplicates_found": len(duplicates),
        "merge_mappings": merge_map,
        "details": [
            {
                "node1_id": d[0].get("id"),
                "node1_name": d[0].get("name"),
                "node2_id": d[1].get("id"),
                "node2_name": d[1].get("name"),
                "reason": d[2]
            }
            for d in duplicates
        ]
    }
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"📄 合并报告: {report_file}")
    
    print("\n" + "=" * 60)
    print("✅ 去重完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()

