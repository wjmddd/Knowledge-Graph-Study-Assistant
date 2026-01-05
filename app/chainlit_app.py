"""
Chainlit 前端应用 - 增强版
专业的聊天界面，集成知识图谱问答 Agent

模块化设计：
- app/services/history.py - 对话历史管理
- app/services/graph_service.py - 图谱查询服务
- app/services/recommendation.py - 智能推荐
"""

import sys
import asyncio
import webbrowser
from pathlib import Path
from datetime import datetime

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent))

import chainlit as cl

from src.agent.langchain_agent import LangChainAgent, AgentResponse

# 导入服务模块
from app.services import (
    # 历史记录
    save_conversation,
    list_conversations,
    # 图谱服务
    get_graph_stats,
    query_concept_detail,
    generate_concept_graph_text,
    generate_interactive_graph,
    GRAPH_VIZ_DIR,
    # 推荐
    get_related_questions,
    extract_main_concept,
)


# ==========================================
# 全局 Agent 实例
# ==========================================
agent: LangChainAgent = None


# ==========================================
# Chainlit 事件处理
# ==========================================

@cl.on_chat_start
async def on_chat_start():
    """聊天开始时初始化"""
    global agent
    
    agent = LangChainAgent()
    
    # 获取系统状态
    stats = get_graph_stats()
    neo4j_status = "🟢 已连接" if "error" not in stats else "🔴 未连接"
    node_count = sum(stats.get("nodes", {}).values()) if "nodes" in stats else 0
    
    welcome_message = f"""
# 🎓 计算机系统基础 - 智能学习助手

欢迎使用基于**知识图谱**的智能问答系统！

## 💡 你可以问我：

| 类型 | 示例问题 |
|------|----------|
| 📖 概念解释 | 什么是CPU？缓存是什么？ |
| 🔧 组成结构 | CPU由什么组成？ |
| 📚 学习路径 | 学习流水线需要什么基础？ |
| ⚖️ 概念对比 | RISC和CISC有什么区别？ |

## 🔍 特殊命令：

| 命令 | 说明 |
|------|------|
| `/graph 概念名` | 查询概念的图谱关系（文本） |
| `/viz 概念名` | 🎨 **交互式图谱**（可拖拽缩放！） |
| `/stats` | 查看知识图谱统计 |
| `/history` | 查看历史对话列表 |
| `/help` | 显示帮助信息 |

---

> 📊 **系统状态**: Neo4j {neo4j_status} | 知识节点: {node_count} 个

"""
    
    await cl.Message(content=welcome_message).send()
    
    # 存储会话信息
    session_id = cl.context.session.id
    cl.user_session.set("session_id", session_id)
    cl.user_session.set("messages", [])


@cl.on_message
async def on_message(message: cl.Message):
    """处理用户消息"""
    global agent
    
    if agent is None:
        agent = LangChainAgent()
    
    session_id = cl.user_session.get("session_id", "default")
    content = message.content.strip()
    
    # ==========================================
    # 处理特殊命令
    # ==========================================
    
    # /graph 命令 - 查询概念图谱（文本）
    if content.startswith("/graph"):
        await handle_graph_command(content)
        return
    
    # /viz 命令 - 生成交互式图谱可视化
    if content.startswith("/viz"):
        await handle_viz_command(content)
        return
    
    # /stats 命令 - 查看统计
    if content == "/stats":
        await handle_stats_command()
        return
    
    # /history 命令 - 查看历史对话
    if content == "/history":
        await handle_history_command()
        return
    
    # /help 命令
    if content == "/help":
        await handle_help_command()
        return
    
    # ==========================================
    # 正常问答处理
    # ==========================================
    await handle_chat(content, session_id)


@cl.on_chat_end
async def on_chat_end():
    """聊天结束时清理"""
    global agent
    
    if agent:
        session_id = cl.user_session.get("session_id", "default")
        agent.clear_history(session_id)


@cl.on_settings_update
async def on_settings_update(settings):
    """设置更新回调"""
    pass


# ==========================================
# 命令处理函数
# ==========================================

async def handle_graph_command(content: str):
    """处理 /graph 命令"""
    parts = content.split(maxsplit=1)
    if len(parts) > 1:
        concept = parts[1].strip()
        await cl.Message(content=f"🔍 正在查询 **{concept}** 的图谱信息...").send()
        result = query_concept_detail(concept)
        await cl.Message(content=result + f"\n\n💡 **提示**: 使用 `/viz {concept}` 可以查看交互式图谱").send()
    else:
        await cl.Message(content="用法: `/graph 概念名`\n例如: `/graph CPU`").send()


async def handle_viz_command(content: str):
    """处理 /viz 命令 - 生成交互式图谱"""
    parts = content.split(maxsplit=1)
    if len(parts) > 1:
        concept = parts[1].strip()
        await cl.Message(content=f"🎨 正在生成 **{concept}** 的交互式图谱...").send()
        
        # 在后台生成图谱
        filepath = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: generate_interactive_graph(concept)
        )
        
        if filepath:
            # 使用绝对路径
            abs_path = str(Path(filepath).absolute())
            file_url = f"file:///{abs_path.replace(chr(92), '/')}"
            
            result = f"""
## 🎨 交互式图谱已生成

**概念**: {concept}

📁 **文件位置**: `{filepath}`

### 查看方式

1. **自动打开** (推荐)：正在尝试用浏览器打开...

2. **手动打开**: 复制以下路径到浏览器地址栏:
```
{file_url}
```

3. **文件管理器**: 双击打开文件 `{abs_path}`

---

⚠️ **注意**: 图谱文件使用 Pyvis 生成，支持:
- 🖱️ 拖拽移动节点
- 🔍 滚轮缩放
- 📌 悬停查看详情
- 🎯 点击聚焦节点
"""
            await cl.Message(content=result).send()
            
            # 尝试自动打开浏览器
            try:
                webbrowser.open(file_url)
            except Exception as e:
                await cl.Message(content=f"⚠️ 自动打开浏览器失败，请手动打开文件").send()
        else:
            await cl.Message(content=f"❌ 未找到概念 **{concept}**，请检查名称是否正确\n\n💡 提示: 使用 `/graph {concept}` 查看相似概念").send()
    else:
        await cl.Message(content="用法: `/viz 概念名`\n例如: `/viz CPU`\n\n这将生成一个交互式的图谱可视化HTML文件").send()


async def handle_stats_command():
    """处理 /stats 命令"""
    stats = get_graph_stats()
    if "error" in stats:
        await cl.Message(content=f"❌ 获取统计失败: {stats['error']}").send()
    else:
        nodes = stats.get("nodes", {})
        rels = stats.get("relationships", {})
        total_nodes = sum(nodes.values())
        total_rels = sum(rels.values())
        
        result = f"""
## 📊 知识图谱统计

### 节点统计 (共 {total_nodes} 个)
| 类型 | 数量 |
|------|------|
"""
        for node_type, count in sorted(nodes.items(), key=lambda x: -x[1]):
            result += f"| {node_type} | {count} |\n"
        
        result += f"""
### 关系统计 (共 {total_rels} 条)
| 类型 | 数量 |
|------|------|
"""
        for rel_type, count in sorted(rels.items(), key=lambda x: -x[1])[:10]:
            result += f"| {rel_type} | {count} |\n"
        
        if len(rels) > 10:
            result += f"| ... | 还有 {len(rels) - 10} 种关系类型 |\n"
        
        await cl.Message(content=result).send()


async def handle_history_command():
    """处理 /history 命令"""
    conversations = list_conversations()
    if not conversations:
        await cl.Message(content="📭 暂无历史对话记录").send()
    else:
        result = "## 📜 历史对话\n\n"
        for i, conv in enumerate(conversations[:10], 1):
            updated = conv.get("updated_at", "")[:10]
            count = conv.get("message_count", 0)
            title = conv.get("title", "未知")
            result += f"{i}. **{title}** ({count}条消息, {updated})\n"
        await cl.Message(content=result).send()


async def handle_help_command():
    """处理 /help 命令"""
    help_text = """
## 📚 帮助信息

### 问答功能
直接输入问题即可，例如：
- 什么是CPU？
- Cache的工作原理是什么？
- SRAM和DRAM有什么区别？

### 特殊命令
| 命令 | 说明 |
|------|------|
| `/graph 概念名` | 查询概念的图谱关系（文本形式） |
| `/viz 概念名` | 🎨 生成**交互式图谱**（推荐！） |
| `/stats` | 查看知识图谱统计信息 |
| `/history` | 查看历史对话列表 |
| `/help` | 显示此帮助信息 |

### 示例
```
/graph CPU      # 文本形式查看 CPU 相关信息
/viz CPU        # 生成交互式图谱可视化
/viz 缓存       # 生成缓存概念的可视化图谱
/stats
```

### 交互式图谱功能
使用 `/viz` 命令可以生成交互式图谱，支持：
- 🖱️ 拖拽节点调整布局
- 🔍 滚轮缩放画布
- 📌 悬停查看节点详情
- 🎯 点击节点聚焦
"""
    await cl.Message(content=help_text).send()


# ==========================================
# 问答处理
# ==========================================

async def handle_chat(content: str, session_id: str):
    """处理正常问答"""
    global agent
    
    try:
        # 步骤1: 显示思考过程
        async with cl.Step(name="🔍 理解问题", type="llm") as step:
            step.output = f"正在分析问题：「{content}」"
        
        # 步骤2: 工具调用
        async with cl.Step(name="🛠️ 检索知识库", type="tool") as step:
            step.output = "正在调用知识图谱和向量检索..."
            
            response: AgentResponse = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: agent.chat(content, session_id)
            )
            
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
        
        # 步骤3: 生成回答
        async with cl.Step(name="💬 生成回答", type="llm") as step:
            step.output = "正在组织答案..."
        
        # 构建最终回复
        answer_parts = []
        answer_parts.append(response.answer)
        
        # 添加知识图谱可视化
        main_concept = extract_main_concept(content, response.tool_calls)
        
        if main_concept and response.sources:
            graph_text = generate_concept_graph_text(main_concept)
            if graph_text:
                answer_parts.append("\n\n---\n\n")
                answer_parts.append("### 📊 知识图谱关系\n")
                answer_parts.append(f"*以 **{main_concept}** 为中心的概念关联：*\n\n")
                answer_parts.append(graph_text)
        
        # 添加来源信息
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
        await cl.Message(content="".join(answer_parts)).send()
        
        # 添加智能追问建议
        if main_concept:
            related_questions = get_related_questions(main_concept, content)
            
            if related_questions:
                follow_up_parts = []
                follow_up_parts.append("\n\n---\n\n")
                follow_up_parts.append("### 🎯 继续探索\n")
                follow_up_parts.append("*基于知识图谱推荐的相关问题：*\n\n")
                
                for i, q in enumerate(related_questions, 1):
                    follow_up_parts.append(f"**{i}.** `{q}`\n\n")
                
                await cl.Message(content="".join(follow_up_parts)).send()
        
        # 保存对话历史
        messages = cl.user_session.get("messages", [])
        messages.append({"role": "user", "content": content, "timestamp": datetime.now().isoformat()})
        messages.append({"role": "assistant", "content": response.answer, "timestamp": datetime.now().isoformat()})
        cl.user_session.set("messages", messages)
        save_conversation(session_id, messages)
        
    except Exception as e:
        await cl.Message(content=f"❌ 抱歉，处理您的问题时出现错误：{str(e)}").send()
