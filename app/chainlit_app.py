"""
Chainlit 前端应用 - 增强版
专业的聊天界面，集成知识图谱问答 Agent
支持：思考过程可视化、图谱展示、智能追问
"""

import sys
import asyncio
from pathlib import Path
from typing import List, Dict, Optional

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent))

import chainlit as cl

from src.agent.langchain_agent import LangChainAgent, AgentResponse
from src.retrieval.graph_query import get_graph_query


# ==========================================
# 全局 Agent 实例
# ==========================================
agent: LangChainAgent = None


# ==========================================
# 图谱可视化辅助函数
# ==========================================

def generate_concept_graph_text(concept_name: str, max_relations: int = 8) -> Optional[str]:
    """
    生成概念相关的图谱关系文本描述
    
    Args:
        concept_name: 中心概念名称
        max_relations: 最大关系数
        
    Returns:
        Markdown 格式的关系描述
    """
    try:
        graph = get_graph_query()
        if not graph.is_connected():
            return None
        
        # 获取概念信息
        concept = graph.get_concept(concept_name)
        if not concept:
            return None
        
        actual_name = concept.get("name", concept_name)
        
        # 获取相关关系
        relations = graph.get_relations(actual_name, direction="both")
        if not relations:
            return None
        
        # 关系类型 emoji 映射
        rel_emoji = {
            "COMPOSED_OF": "🔧",
            "CONTAINS": "📦",
            "DEPENDS_ON": "⬅️",
            "IS_A": "📂",
            "USES": "🔗",
            "CONTRASTS_WITH": "⚖️",
            "IMPLEMENTED_BY": "⚙️",
            "PRECEDES": "➡️",
            "RELATED_TO": "🔄",
        }
        
        # 按关系类型分组
        grouped = {}
        for rel in relations[:max_relations]:
            rel_type = rel.get("relation_type", "RELATED")
            target = rel.get("target", "")
            if rel_type not in grouped:
                grouped[rel_type] = []
            if target and target not in grouped[rel_type]:
                grouped[rel_type].append(target)
        
        # 生成 Markdown
        lines = []
        lines.append(f"```")
        lines.append(f"        ┌─────────────┐")
        lines.append(f"        │  {actual_name:^9}  │")
        lines.append(f"        └──────┬──────┘")
        lines.append(f"               │")
        
        for rel_type, targets in list(grouped.items())[:4]:
            emoji = rel_emoji.get(rel_type, "•")
            rel_name = rel_type.replace("_", " ").lower()
            targets_str = ", ".join(targets[:3])
            if len(targets) > 3:
                targets_str += f" (+{len(targets)-3})"
            lines.append(f"    {emoji} {rel_name}: {targets_str}")
        
        lines.append(f"```")
        
        return "\n".join(lines)
        
    except Exception as e:
        print(f"生成图谱文本失败: {e}")
        return None


def generate_concept_graph_html(concept_name: str, max_nodes: int = 15) -> Optional[str]:
    """
    生成概念相关的局部知识图谱 HTML
    
    Args:
        concept_name: 中心概念名称
        max_nodes: 最大节点数
        
    Returns:
        HTML 字符串，或 None（如果无法生成）
    """
    try:
        from pyvis.network import Network
        
        graph = get_graph_query()
        if not graph.is_connected():
            return None
        
        # 获取概念信息
        concept = graph.get_concept(concept_name)
        if not concept:
            return None
        
        actual_name = concept.get("name", concept_name)
        
        # 获取相关关系
        relations = graph.get_relations(actual_name, direction="both")
        if not relations:
            return None
        
        # 创建网络图
        net = Network(
            height="300px",
            width="100%",
            bgcolor="#1a1a2e",
            font_color="white",
            directed=True
        )
        
        # 节点颜色映射
        color_map = {
            "Hardware": "#e74c3c",
            "Concept": "#3498db",
            "Instruction": "#2ecc71",
            "Principle": "#9b59b6",
            "CodeSnippet": "#f39c12",
        }
        
        # 添加中心节点
        center_label = concept.get("label", "Concept")
        net.add_node(
            actual_name,
            label=actual_name,
            color=color_map.get(center_label, "#3498db"),
            size=30,
            font={"size": 14, "color": "white"},
            borderWidth=3,
            borderWidthSelected=5
        )
        
        # 添加相关节点和边
        added_nodes = {actual_name}
        for i, rel in enumerate(relations[:max_nodes]):
            target = rel.get("target")
            rel_type = rel.get("relation_type", "RELATED")
            target_label = rel.get("target_label", "Concept")
            
            if target and target not in added_nodes:
                net.add_node(
                    target,
                    label=target,
                    color=color_map.get(target_label, "#95a5a6"),
                    size=20,
                    font={"size": 12, "color": "white"}
                )
                added_nodes.add(target)
            
            if target:
                # 简化关系名称
                short_rel = rel_type.replace("_", " ").title()
                if len(short_rel) > 12:
                    short_rel = short_rel[:10] + ".."
                
                net.add_edge(
                    actual_name,
                    target,
                    label=short_rel,
                    color="#666",
                    font={"size": 9, "color": "#aaa"}
                )
        
        # 配置物理布局
        net.set_options("""
        {
            "physics": {
                "enabled": true,
                "solver": "forceAtlas2Based",
                "forceAtlas2Based": {
                    "gravitationalConstant": -50,
                    "centralGravity": 0.01,
                    "springLength": 100
                },
                "stabilization": {"iterations": 100}
            },
            "interaction": {
                "hover": true,
                "tooltipDelay": 200
            }
        }
        """)
        
        # 生成 HTML
        html = net.generate_html()
        return html
        
    except Exception as e:
        print(f"生成图谱失败: {e}")
        return None


def get_related_questions(concept_name: str, current_query: str) -> List[str]:
    """
    基于知识图谱生成推荐追问
    
    Args:
        concept_name: 当前概念
        current_query: 当前问题
        
    Returns:
        推荐问题列表
    """
    questions = []
    
    try:
        graph = get_graph_query()
        if not graph.is_connected():
            return questions
        
        # 获取概念
        concept = graph.get_concept(concept_name)
        if not concept:
            return questions
        
        actual_name = concept.get("name", concept_name)
        
        # 获取相关关系
        relations = graph.get_relations(actual_name, direction="both")
        
        # 基于关系类型生成问题
        seen_targets = set()
        for rel in relations[:10]:
            target = rel.get("target")
            rel_type = rel.get("relation_type", "")
            
            if not target or target in seen_targets:
                continue
            seen_targets.add(target)
            
            # 根据关系类型生成问题
            if rel_type == "COMPOSED_OF":
                questions.append(f"{target}是什么？")
            elif rel_type == "DEPENDS_ON":
                questions.append(f"为什么需要{target}？")
            elif rel_type == "IS_A":
                questions.append(f"{target}有哪些类型？")
            elif rel_type == "CONTRASTS_WITH":
                questions.append(f"{actual_name}和{target}有什么区别？")
            elif rel_type in ["USES", "IMPLEMENTED_BY"]:
                questions.append(f"{target}是如何工作的？")
            
            if len(questions) >= 3:
                break
        
        # 如果问题不够，添加通用追问
        if len(questions) < 3:
            fallback = [
                f"学习{actual_name}需要什么基础？",
                f"{actual_name}的应用场景有哪些？",
                f"{actual_name}的工作原理是什么？"
            ]
            for q in fallback:
                if q not in questions and len(questions) < 3:
                    questions.append(q)
        
        return questions[:3]
        
    except Exception as e:
        print(f"生成推荐问题失败: {e}")
        return []


def extract_main_concept(query: str, tool_calls: List[Dict]) -> Optional[str]:
    """从查询或工具调用中提取主要概念"""
    # 从工具调用中提取
    for tc in tool_calls:
        input_data = tc.get("input", {})
        if isinstance(input_data, dict):
            for key in ["concept_name", "concept_a", "query"]:
                if key in input_data:
                    return input_data[key]
    
    # 从查询中提取（简单方法）
    keywords = ["什么是", "是什么", "什么叫", "解释", "介绍"]
    for kw in keywords:
        if kw in query:
            # 提取关键词后面的概念
            idx = query.find(kw)
            concept = query[idx + len(kw):].strip().rstrip("？?。.")
            if concept:
                return concept
    
    return None


# ==========================================
# Chainlit 事件处理
# ==========================================

@cl.on_chat_start
async def on_chat_start():
    """聊天开始时初始化"""
    global agent
    
    # 初始化 Agent
    agent = LangChainAgent()
    
    # 设置欢迎消息
    welcome_message = """
# 🎓 计算机系统基础 - 智能学习助手

欢迎使用基于**知识图谱**的智能问答系统！

## 💡 你可以问我：

| 类型 | 示例问题 |
|------|----------|
| 📖 概念解释 | 什么是CPU？缓存是什么？ |
| 🔧 组成结构 | CPU由什么组成？ |
| 📚 学习路径 | 学习流水线需要什么基础？ |
| ⚖️ 概念对比 | RISC和CISC有什么区别？ |
| 🔗 概念关系 | 虚拟内存和页表有什么关系？ |

---

> 📚 **知识来源**：《计算机系统基础》教材 (第1-8章)
> 
> 🔧 **技术栈**：Neo4j 知识图谱 + LangChain Agent + 向量检索

"""
    
    await cl.Message(content=welcome_message).send()
    
    # 存储会话信息
    cl.user_session.set("session_id", cl.context.session.id)
    cl.user_session.set("question_history", [])


@cl.on_message
async def on_message(message: cl.Message):
    """处理用户消息"""
    global agent
    
    if agent is None:
        agent = LangChainAgent()
    
    session_id = cl.user_session.get("session_id", "default")
    
    try:
        # ==========================================
        # 步骤1: 显示思考过程
        # ==========================================
        async with cl.Step(name="🔍 理解问题", type="llm") as step:
            step.output = f"正在分析问题：「{message.content}」"
        
        # ==========================================
        # 步骤2: 工具调用（带进度显示）
        # ==========================================
        async with cl.Step(name="🛠️ 检索知识库", type="tool") as step:
            step.output = "正在调用知识图谱和向量检索..."
            
            # 调用 Agent（在线程池中执行避免阻塞）
            response: AgentResponse = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: agent.chat(message.content, session_id)
            )
            
            # 更新步骤输出
            if response.tool_calls:
                tool_info = []
                for tc in response.tool_calls:
                    tool_name = tc.get("tool", "unknown")
                    tool_input = tc.get("input", {})
                    if isinstance(tool_input, dict):
                        input_str = ", ".join(f"{k}={v}" for k, v in list(tool_input.items())[:2])
                    else:
                        input_str = str(tool_input)[:50]
                    tool_info.append(f"✓ `{tool_name}` ({input_str})")
                step.output = "\n".join(tool_info)
            else:
                step.output = "✓ 使用通用知识回答"
        
        # ==========================================
        # 步骤3: 生成回答
        # ==========================================
        async with cl.Step(name="💬 生成回答", type="llm") as step:
            step.output = "正在组织答案..."
        
        # ==========================================
        # 构建最终回复
        # ==========================================
        answer_parts = []
        
        # 主要回答（美化格式）
        formatted_answer = format_answer(response.answer)
        answer_parts.append(formatted_answer)
        
        # ==========================================
        # 添加知识图谱可视化（简化版）
        # ==========================================
        main_concept = extract_main_concept(message.content, response.tool_calls)
        
        if main_concept and response.sources:
            # 生成图谱关系的文本描述
            graph_text = generate_concept_graph_text(main_concept)
            if graph_text:
                answer_parts.append("\n\n---\n\n")
                answer_parts.append("### 📊 知识图谱关系\n")
                answer_parts.append(f"*以 **{main_concept}** 为中心的概念关联：*\n\n")
                answer_parts.append(graph_text)
        
        # ==========================================
        # 添加来源信息
        # ==========================================
        if response.sources:
            answer_parts.append("\n\n---\n\n")
            answer_parts.append("<details>\n<summary>📚 <b>参考来源</b> (点击展开)</summary>\n\n")
            seen = set()
            for src in response.sources[:5]:
                chapter = src.get("chapter", "未知")
                section = src.get("section", "未知")
                key = f"{chapter}/{section}"
                if key not in seen:
                    seen.add(key)
                    answer_parts.append(f"- 📖 {chapter} / {section}\n")
            answer_parts.append("\n</details>")
        
        # 发送主消息
        msg = cl.Message(content="".join(answer_parts))
        await msg.send()
        
        # ==========================================
        # 添加智能追问建议
        # ==========================================
        if main_concept:
            related_questions = get_related_questions(main_concept, message.content)
            
            if related_questions:
                # 使用文本方式显示推荐问题（更兼容）
                follow_up_parts = []
                follow_up_parts.append("\n\n---\n\n")
                follow_up_parts.append("### 🎯 继续探索\n")
                follow_up_parts.append("*基于知识图谱推荐的相关问题，点击可复制：*\n\n")
                
                for i, q in enumerate(related_questions, 1):
                    follow_up_parts.append(f"**{i}.** `{q}`\n\n")
                
                follow_up_msg = cl.Message(content="".join(follow_up_parts))
                await follow_up_msg.send()
        
        # 记录问题历史
        history = cl.user_session.get("question_history", [])
        history.append(message.content)
        cl.user_session.set("question_history", history[-10:])
        
    except Exception as e:
        error_msg = cl.Message(content=f"❌ 抱歉，处理您的问题时出现错误：{str(e)}")
        await error_msg.send()


def format_answer(answer: str) -> str:
    """
    美化答案格式
    - 高亮核心定义
    - 优化列表格式
    """
    import re
    
    # 如果已经有知识库未找到的提示，保持原样
    if "⚠️ **提示**" in answer:
        return answer
    
    # 高亮定义（"XXX是..." 或 "定义：..."）
    answer = re.sub(
        r'(定义[：:]\s*)([^。\n]+[。])',
        r'\1**\2**',
        answer
    )
    
    # 为核心概念添加 emoji
    concept_emojis = {
        "CPU": "🖥️ CPU",
        "ALU": "🔢 ALU",
        "缓存": "💾 缓存",
        "Cache": "💾 Cache",
        "内存": "📦 内存",
        "寄存器": "📝 寄存器",
        "流水线": "⚡ 流水线",
        "指令": "📋 指令",
        "总线": "🚌 总线",
    }
    
    for term, emoji_term in concept_emojis.items():
        # 只替换标题中的（避免过度替换）
        answer = re.sub(
            rf'^(#+\s*)({term})',
            rf'\1{emoji_term}',
            answer,
            flags=re.MULTILINE
        )
    
    return answer


@cl.on_chat_end
async def on_chat_end():
    """聊天结束时清理"""
    global agent
    
    if agent:
        session_id = cl.user_session.get("session_id", "default")
        agent.clear_history(session_id)


# ==========================================
# 设置面板
# ==========================================

@cl.on_settings_update
async def on_settings_update(settings):
    """设置更新回调"""
    pass
