"""
Streamlit Web 界面
计算机系统基础 - 智能学习助手

用法: streamlit run app/streamlit_app.py
"""

import sys
from pathlib import Path

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from src.agent.qa_agent import QAAgent, QAResponse


# ==========================================
# 页面配置
# ==========================================

st.set_page_config(
    page_title="计算机系统基础 - 智能学习助手",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义 CSS
st.markdown("""
<style>
    /* 主题色调整 */
    .stApp {
        background-color: #f8f9fa;
    }
    
    /* 聊天消息样式 */
    .user-message {
        background-color: #e3f2fd;
        padding: 1rem;
        border-radius: 1rem;
        margin: 0.5rem 0;
        border-left: 4px solid #1976d2;
    }
    
    .assistant-message {
        background-color: #ffffff;
        padding: 1rem;
        border-radius: 1rem;
        margin: 0.5rem 0;
        border-left: 4px solid #4caf50;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    /* 来源标签 */
    .source-tag {
        display: inline-block;
        background-color: #e8f5e9;
        color: #2e7d32;
        padding: 0.2rem 0.5rem;
        border-radius: 0.3rem;
        font-size: 0.8rem;
        margin: 0.2rem;
    }
    
    /* 侧边栏 */
    .sidebar-info {
        background-color: #fff;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    
    /* 标题样式 */
    .main-title {
        text-align: center;
        color: #1976d2;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)


# ==========================================
# 初始化 Session State
# ==========================================

def init_session_state():
    """初始化会话状态"""
    if "agent" not in st.session_state:
        st.session_state.agent = QAAgent()
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "show_debug" not in st.session_state:
        st.session_state.show_debug = False


# ==========================================
# 侧边栏
# ==========================================

def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        st.markdown("## 🎓 学习助手")
        st.markdown("---")
        
        # 功能说明
        st.markdown("### 📌 支持的问题类型")
        st.markdown("""
        - **概念解释**: 什么是补码？
        - **组成结构**: CPU由什么组成？
        - **学习路径**: 学虚拟内存需要什么基础？
        - **概念对比**: SRAM和DRAM有什么区别？
        - **关系查询**: CPU和ALU有什么关系？
        - **通用问答**: 流水线冒险怎么解决？
        """)
        
        st.markdown("---")
        
        # 示例问题
        st.markdown("### 💡 试试这些问题")
        example_questions = [
            "什么是补码？",
            "CPU由哪些部分组成？",
            "学习虚拟内存需要什么前置知识？",
            "SRAM和DRAM有什么区别？",
            "什么是流水线冒险？",
            "Cache是如何工作的？"
        ]
        
        for q in example_questions:
            if st.button(q, key=f"example_{q}", use_container_width=True):
                st.session_state.pending_question = q
        
        st.markdown("---")
        
        # 操作按钮
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ 清空对话", use_container_width=True):
                st.session_state.messages = []
                st.session_state.agent.clear_history()
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
            - **对话轮数**: {len(st.session_state.messages) // 2}
            """)
        except Exception as e:
            st.markdown(f"⚠️ 状态检查失败: {e}")


# ==========================================
# 主聊天区域
# ==========================================

def render_chat():
    """渲染聊天区域"""
    st.markdown('<h1 class="main-title">🎓 计算机系统基础 - 智能学习助手</h1>', unsafe_allow_html=True)
    
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
                    
                    # 显示来源
                    if msg.get("sources"):
                        st.markdown("---")
                        st.markdown("**📚 参考来源:**")
                        for src in msg["sources"][:3]:
                            chapter = src.get("chapter", "未知")
                            section = src.get("section", "未知")
                            st.markdown(f'<span class="source-tag">{chapter} / {section}</span>', unsafe_allow_html=True)
                    
                    # 调试信息
                    if st.session_state.show_debug and msg.get("debug"):
                        with st.expander("🔧 调试信息"):
                            st.json(msg["debug"])
    
    # 处理示例问题点击
    if hasattr(st.session_state, 'pending_question'):
        question = st.session_state.pending_question
        del st.session_state.pending_question
        process_question(question)
        st.rerun()
    
    # 输入框
    if prompt := st.chat_input("输入你的问题..."):
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
        response: QAResponse = st.session_state.agent.chat(question)
        
        # 添加助手消息
        st.session_state.messages.append({
            "role": "assistant",
            "content": response.answer,
            "sources": response.sources,
            "debug": {
                "intent": response.intent,
                "entities": response.entities,
                "tool": response.tool_used,
                "success": response.success
            }
        })
    except Exception as e:
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"抱歉，处理您的问题时出现错误：{str(e)}",
            "sources": [],
            "debug": {"error": str(e)}
        })


# ==========================================
# 主程序
# ==========================================

def main():
    init_session_state()
    render_sidebar()
    render_chat()


if __name__ == "__main__":
    main()

