"""
Streamlit Web 界面 - Phase 2 升级版
计算机系统基础 - 智能学习助手

新增功能:
- LangChain Agent 支持多轮对话
- 知识图谱可视化
- 问题澄清机制
- 工具调用透明展示

用法: streamlit run app/streamlit_app_v2.py
"""

import sys
from pathlib import Path

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import streamlit.components.v1 as components
from src.agent.langchain_agent import LangChainAgent, AgentResponse
from src.visualization.graph_viz import get_visualizer


# ==========================================
# 页面配置
# ==========================================

st.set_page_config(
    page_title="计算机系统基础 - 智能学习助手 V2",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义 CSS
st.markdown("""
<style>
    /* 主题色 - 深蓝绿配色 */
    :root {
        --primary: #0d9488;
        --primary-light: #14b8a6;
        --secondary: #1e293b;
        --accent: #f97316;
        --bg: #f8fafc;
        --card-bg: #ffffff;
        --text: #1e293b;
        --text-muted: #64748b;
    }
    
    .stApp {
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
    }
    
    /* 标题样式 */
    .main-title {
        text-align: center;
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    
    .sub-title {
        text-align: center;
        color: var(--text-muted);
        font-size: 1rem;
        margin-bottom: 2rem;
    }
    
    /* 聊天消息样式 */
    .chat-container {
        max-width: 900px;
        margin: 0 auto;
    }
    
    /* 工具调用展示 */
    .tool-call {
        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
        padding: 0.75rem 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        font-size: 0.85rem;
        border-left: 4px solid var(--accent);
    }
    
    /* 来源标签 */
    .source-tag {
        display: inline-block;
        background: linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%);
        color: #166534;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-size: 0.8rem;
        margin: 0.25rem;
    }
    
    /* 可视化容器 */
    .viz-container {
        background: var(--card-bg);
        border-radius: 1rem;
        padding: 1rem;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        margin: 1rem 0;
    }
    
    /* 统计卡片 */
    .stat-card {
        background: var(--card-bg);
        border-radius: 0.75rem;
        padding: 1rem;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    .stat-number {
        font-size: 2rem;
        font-weight: 700;
        color: var(--primary);
    }
    
    .stat-label {
        font-size: 0.85rem;
        color: var(--text-muted);
    }
    
    /* 侧边栏样式 */
    .sidebar .stButton button {
        width: 100%;
        border-radius: 0.5rem;
        margin: 0.25rem 0;
    }
    
    /* 隐藏 Streamlit 默认元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Tab 样式 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: var(--card-bg);
        border-radius: 0.5rem 0.5rem 0 0;
        padding: 0.5rem 1rem;
    }
</style>
""", unsafe_allow_html=True)


# ==========================================
# 初始化 Session State
# ==========================================

def init_session_state():
    """初始化会话状态"""
    if "agent" not in st.session_state:
        st.session_state.agent = LangChainAgent()
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "session_id" not in st.session_state:
        import uuid
        st.session_state.session_id = str(uuid.uuid4())[:8]
    
    if "show_debug" not in st.session_state:
        st.session_state.show_debug = False
    
    if "current_viz_concept" not in st.session_state:
        st.session_state.current_viz_concept = None


# ==========================================
# 侧边栏
# ==========================================

def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        st.markdown("## 🎓 智能学习助手 V2")
        st.markdown("*基于 LangChain Agent*")
        st.markdown("---")
        
        # 功能说明
        with st.expander("📌 支持的问题类型", expanded=False):
            st.markdown("""
            - **概念解释**: 什么是补码？
            - **组成结构**: CPU由什么组成？
            - **学习路径**: 学虚拟内存需要什么基础？
            - **概念对比**: SRAM和DRAM有什么区别？
            - **关系查询**: CPU和ALU有什么关系？
            - **通用问答**: 流水线冒险怎么解决？
            - **追问深入**: 继续上面的话题...
            """)
        
        st.markdown("---")
        
        # 示例问题
        st.markdown("### 💡 快速提问")
        example_questions = [
            "什么是补码？",
            "CPU由哪些部分组成？",
            "SRAM和DRAM有什么区别？",
            "什么是流水线冒险？",
            "Cache是如何工作的？",
            "存储器层次结构是什么？"
        ]
        
        cols = st.columns(2)
        for i, q in enumerate(example_questions):
            with cols[i % 2]:
                if st.button(q, key=f"ex_{i}", use_container_width=True):
                    st.session_state.pending_question = q
        
        st.markdown("---")
        
        # 可视化入口
        st.markdown("### 🔍 图谱探索")
        viz_concept = st.text_input(
            "输入概念名称",
            placeholder="如: CPU, 缓存, 补码",
            key="viz_input"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🌐 查看图谱", use_container_width=True):
                if viz_concept:
                    st.session_state.current_viz_concept = viz_concept
                    st.session_state.show_viz = True
        with col2:
            if st.button("📊 统计信息", use_container_width=True):
                st.session_state.show_stats = True
        
        st.markdown("---")
        
        # 操作按钮
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ 清空对话", use_container_width=True):
                st.session_state.messages = []
                st.session_state.agent.clear_history(st.session_state.session_id)
                st.rerun()
        
        with col2:
            st.session_state.show_debug = st.checkbox(
                "🔧 调试",
                value=st.session_state.show_debug
            )
        
        st.markdown("---")
        
        # 系统状态
        st.markdown("### 📊 系统状态")
        try:
            from src.retrieval.graph_query import get_graph_query
            from src.retrieval.vector_store import get_vector_store
            
            gq = get_graph_query()
            vs = get_vector_store()
            
            neo4j_status = "🟢 已连接" if gq.is_connected() else "🔴 未连接"
            vector_count = vs.count()
            
            st.markdown(f"""
            - **Neo4j**: {neo4j_status}
            - **向量库**: {vector_count} 个文档
            - **会话 ID**: `{st.session_state.session_id}`
            - **对话轮数**: {len(st.session_state.messages) // 2}
            """)
        except Exception as e:
            st.markdown(f"⚠️ 状态检查失败")


# ==========================================
# 图谱可视化
# ==========================================

def render_visualization():
    """渲染可视化页面"""
    st.markdown("### 🌐 知识图谱可视化")
    
    viz = get_visualizer()
    concept = st.session_state.get("current_viz_concept", "CPU")
    
    if concept:
        with st.spinner(f"正在生成 '{concept}' 的知识图谱..."):
            html = viz.visualize_concept_neighborhood(concept, depth=2)
            
            if html:
                # 显示图谱
                components.html(html, height=500, scrolling=True)
                
                st.markdown(f"""
                <div style="text-align: center; color: #666; margin-top: 0.5rem;">
                    💡 提示: 拖拽节点查看关系，滚轮缩放，双击节点可固定
                </div>
                """, unsafe_allow_html=True)
            else:
                st.warning(f"未找到与 '{concept}' 相关的知识图谱数据")
    
    if st.button("← 返回对话"):
        st.session_state.show_viz = False
        st.rerun()


def render_stats():
    """渲染统计信息"""
    st.markdown("### 📊 知识图谱统计")
    
    viz = get_visualizer()
    stats = viz.get_graph_stats()
    
    if "error" in stats:
        st.error(f"获取统计信息失败: {stats['error']}")
    else:
        # 总体统计
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number">{stats.get('total_nodes', 0)}</div>
                <div class="stat-label">总节点数</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number">{stats.get('total_relationships', 0)}</div>
                <div class="stat-label">总关系数</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # 节点类型分布
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 节点类型分布")
            nodes_by_type = stats.get("nodes_by_type", {})
            if nodes_by_type:
                for node_type, count in nodes_by_type.items():
                    st.markdown(f"- **{node_type}**: {count}")
        
        with col2:
            st.markdown("#### 关系类型分布")
            rels_by_type = stats.get("relationships_by_type", {})
            if rels_by_type:
                for rel_type, count in rels_by_type.items():
                    st.markdown(f"- **{rel_type}**: {count}")
    
    if st.button("← 返回对话"):
        st.session_state.show_stats = False
        st.rerun()


# ==========================================
# 主聊天区域
# ==========================================

def render_chat():
    """渲染聊天区域"""
    st.markdown('<h1 class="main-title">🎓 计算机系统基础 - 智能学习助手</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">基于知识图谱的 AI 问答系统 · 支持多轮对话 · LangChain Agent</p>', unsafe_allow_html=True)
    
    # 聊天历史
    chat_container = st.container()
    
    with chat_container:
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                with st.chat_message("user", avatar="👤"):
                    st.markdown(msg["content"])
            else:
                with st.chat_message("assistant", avatar="🤖"):
                    st.markdown(msg["content"])
                    
                    # 显示工具调用 (调试模式)
                    if st.session_state.show_debug and msg.get("tool_calls"):
                        st.markdown("---")
                        st.markdown("**🔧 工具调用:**")
                        for tc in msg["tool_calls"]:
                            tool_name = tc.get("tool", "未知")
                            tool_input = tc.get("input", {})
                            st.markdown(f"""
                            <div class="tool-call">
                                <strong>{tool_name}</strong>: {tool_input}
                            </div>
                            """, unsafe_allow_html=True)
                    
                    # 显示来源
                    if msg.get("sources"):
                        st.markdown("---")
                        st.markdown("**📚 参考来源:**")
                        for src in msg["sources"][:3]:
                            chapter = src.get("chapter", "未知")
                            section = src.get("section", "未知")
                            st.markdown(f'<span class="source-tag">{chapter} / {section}</span>', unsafe_allow_html=True)
    
    # 处理示例问题点击
    if hasattr(st.session_state, 'pending_question'):
        question = st.session_state.pending_question
        del st.session_state.pending_question
        process_question(question)
        st.rerun()
    
    # 输入框
    if prompt := st.chat_input("输入你的问题... (支持追问和多轮对话)"):
        process_question(prompt)
        st.rerun()


def process_question(question: str):
    """处理用户问题"""
    # 添加用户消息
    st.session_state.messages.append({
        "role": "user",
        "content": question
    })
    
    # 获取回答
    try:
        response: AgentResponse = st.session_state.agent.chat(
            question,
            st.session_state.session_id
        )
        
        # 添加助手消息
        st.session_state.messages.append({
            "role": "assistant",
            "content": response.answer,
            "sources": response.sources,
            "tool_calls": response.tool_calls
        })
        
        # 如果回答中提到了某个概念，可以提示用户查看图谱
        # (简单的启发式检测)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"抱歉，处理您的问题时出现错误：{str(e)}",
            "sources": [],
            "tool_calls": []
        })


# ==========================================
# 主程序
# ==========================================

def main():
    init_session_state()
    render_sidebar()
    
    # 根据状态显示不同页面
    if st.session_state.get("show_viz"):
        render_visualization()
    elif st.session_state.get("show_stats"):
        render_stats()
    else:
        render_chat()


if __name__ == "__main__":
    main()

