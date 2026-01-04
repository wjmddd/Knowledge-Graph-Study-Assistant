"""
LangChain Agent 实现
支持多轮对话、工具调用、问题澄清
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
import logging
import time

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# ==========================================
# 日志配置
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("Agent")

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.chat_history import InMemoryChatMessageHistory

from config.settings import (
    CLIENT_CONFIG, 
    QA_CONFIG,
    ANSWER_SYSTEM_PROMPT,
    TOOL_SELECTION_SYSTEM_PROMPT,
    TOOL_SELECTION_USER_PROMPT,
    USER_QUERY_WITH_CONTEXT_TEMPLATE,
    FALLBACK_SYSTEM_PROMPT,
    KB_NOT_FOUND_PREFIX
)
from src.agent.langchain_tools import get_langchain_tools


@dataclass
class AgentResponse:
    """Agent 响应"""
    answer: str
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    sources: List[Dict[str, str]] = field(default_factory=list)
    needs_clarification: bool = False
    clarification_options: List[str] = field(default_factory=list)


class LangChainAgent:
    """基于 LangChain 的问答 Agent"""
    
    def __init__(self):
        # 初始化 LLM
        self.llm = ChatOpenAI(
            api_key=CLIENT_CONFIG["api_key"],
            base_url=CLIENT_CONFIG["base_url"],
            model=CLIENT_CONFIG["model"],
            temperature=QA_CONFIG["temperature"],
            max_tokens=QA_CONFIG["max_tokens"]
        )
        
        # 获取工具
        self.tools = get_langchain_tools()
        
        # 创建工具名称到工具对象的映射
        self.tool_map = {tool.name: tool for tool in self.tools}
        
        # 绑定工具到 LLM
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        
        # 会话历史存储
        self.session_histories: Dict[str, InMemoryChatMessageHistory] = {}
        
        # 最大迭代次数
        self.max_iterations = 5
    
    def _get_session_history(self, session_id: str) -> InMemoryChatMessageHistory:
        """获取或创建会话历史"""
        if session_id not in self.session_histories:
            self.session_histories[session_id] = InMemoryChatMessageHistory()
        return self.session_histories[session_id]
    
    def _execute_tool(self, tool_name: str, tool_args: Dict) -> tuple[str, List[Dict]]:
        """执行工具并返回结果和来源"""
        if tool_name not in self.tool_map:
            return f"错误: 未知工具 '{tool_name}'", []
        
        tool = self.tool_map[tool_name]
        sources = []
        
        try:
            result = tool.invoke(tool_args)
            
            # 从结果中提取来源信息
            sources = self._extract_sources(result)
            
            return result, sources
        except Exception as e:
            return f"工具执行错误: {str(e)}", []
    
    def _extract_sources(self, result: str) -> List[Dict]:
        """从工具结果中提取来源信息"""
        import re
        sources = []
        
        # 多种匹配模式
        patterns = [
            # **[1] 第一章 计算机系统概述/1.1 计算机基本组成**
            r'\*\*\[\d+\]\s*([^/\n]+)/([^\*\n]+)\*\*',
            # 来源章节后的 - xxx/xxx: 格式
            r'-\s*([^/\n:]+)/([^:\n]+):',
            # 第X章/X.X节 格式
            r'(第[一二三四五六七八九十\d]+章[^/\n]*)/([^\n\*:]+)',
            # [章/节] 格式
            r'\[([^\]/]+)/([^\]]+)\]',
            # **[章/节]** 格式  
            r'\*\*\[?([^/\]\*]+)/([^\]\*\n]+)\]?\*\*',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, result)
            for match in matches:
                if len(match) >= 2:
                    chapter = match[0].strip() if match[0] else ""
                    section = match[1].strip() if match[1] else ""
                    
                    # 清理章节名称
                    chapter = chapter.strip('*').strip()
                    section = section.strip('*').strip().rstrip('.').rstrip(':')
                    
                    # 过滤无效来源
                    if chapter and len(chapter) > 1 and not chapter.isdigit():
                        source = {"chapter": chapter, "section": section if section else "未知"}
                        if source not in sources:
                            sources.append(source)
        
        return sources[:5]  # 最多返回5个来源
    
    def chat(
        self,
        query: str,
        session_id: str = "default"
    ) -> AgentResponse:
        """
        处理用户问题 - LLM 智能选择工具 + 强制检索兜底
        
        1. 让 LLM 智能选择并调用工具
        2. 如果 LLM 不调用工具，强制执行 hybrid_search
        3. 基于检索结果生成最终答案
        """
        start_time = time.time()
        logger.info(f"=" * 50)
        logger.info(f"📥 收到问题: {query[:50]}{'...' if len(query) > 50 else ''}")
        
        try:
            # 获取会话历史
            history = self._get_session_history(session_id)
            
            tool_calls_info = []
            all_sources = []
            all_context = []
            
            # ==========================================
            # 步骤1: 让 LLM 智能选择工具
            # ==========================================
            logger.info("🔍 步骤1: 请求 LLM 选择工具...")
            step1_start = time.time()
            
            # 构建消息，引导 LLM 调用工具
            messages = [
                SystemMessage(content=TOOL_SELECTION_SYSTEM_PROMPT),
                HumanMessage(content=TOOL_SELECTION_USER_PROMPT.format(query=query))
            ]
            
            # 调用 LLM（带工具）
            try:
                response = self.llm_with_tools.invoke(messages)
                has_tool_calls = hasattr(response, 'tool_calls') and response.tool_calls
                logger.info(f"   ✅ LLM 响应完成 ({time.time() - step1_start:.2f}s)")
                if has_tool_calls:
                    tool_names = [tc["name"] for tc in response.tool_calls]
                    logger.info(f"   🛠️  LLM 选择的工具: {tool_names}")
                else:
                    logger.info("   ⚠️  LLM 未选择任何工具")
            except Exception as e:
                logger.error(f"   ❌ LLM 工具调用失败: {e}")
                has_tool_calls = False
            
            # ==========================================
            # 步骤2: 执行工具调用
            # ==========================================
            logger.info("🔧 步骤2: 执行工具调用...")
            
            if has_tool_calls:
                # LLM 选择了工具，执行它们
                for i, tool_call in enumerate(response.tool_calls, 1):
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    
                    logger.info(f"   [{i}] 执行 {tool_name}({tool_args})...")
                    tool_start = time.time()
                    
                    tool_calls_info.append({
                        "tool": tool_name,
                        "input": tool_args
                    })
                    
                    # 执行工具
                    tool_result, sources = self._execute_tool(tool_name, tool_args)
                    all_sources.extend([s for s in sources if s not in all_sources])
                    all_context.append(f"【{tool_name}】\n{tool_result}")
                    
                    logger.info(f"       ✅ 完成 ({time.time() - tool_start:.2f}s), 找到 {len(sources)} 个来源")
            
            # ==========================================
            # 步骤3: 强制兜底检索（确保一定有检索结果）
            # ==========================================
            
            # 如果没有调用工具，或者调用的工具不是搜索类，补充一次 hybrid_search
            search_tools = ["hybrid_search", "semantic_search"]
            called_search = any(tc["tool"] in search_tools for tc in tool_calls_info)
            
            if not tool_calls_info or not called_search:
                logger.info("🔄 步骤3: 执行兜底检索...")
                fallback_start = time.time()
                
                fallback_result, fallback_sources = self._execute_tool(
                    "hybrid_search",
                    {"query": query}
                )
                tool_calls_info.append({
                    "tool": "hybrid_search" + (" (补充检索)" if tool_calls_info else " (自动检索)"),
                    "input": {"query": query}
                })
                all_sources.extend([s for s in fallback_sources if s not in all_sources])
                all_context.append(f"【hybrid_search 补充】\n{fallback_result}")
                
                logger.info(f"   ✅ 兜底检索完成 ({time.time() - fallback_start:.2f}s)")
            else:
                logger.info("⏭️  步骤3: 跳过 (已有搜索结果)")
            
            # ==========================================
            # 步骤4: 基于检索结果生成答案
            # ==========================================
            context_text = "\n\n".join(all_context)
            
            # 简单判断：是否有来源
            has_valid_content = len(all_sources) > 0
            
            if has_valid_content:
                logger.info("💬 步骤4: 基于知识库生成答案...")
            else:
                logger.info("💬 步骤4: 知识库无相关内容，使用LLM通用知识...")
            
            step4_start = time.time()
            
            if has_valid_content:
                # 有检索结果，基于知识库回答
                user_message = USER_QUERY_WITH_CONTEXT_TEMPLATE.format(
                    context=context_text,
                    query=query
                )
                
                answer_messages = [
                    SystemMessage(content=ANSWER_SYSTEM_PROMPT),
                ]
                # 添加历史对话
                if history.messages:
                    answer_messages.extend(history.messages[-4:])
                answer_messages.append(HumanMessage(content=user_message))
            else:
                # 无检索结果，让 LLM 用自己的知识回答
                answer_messages = [
                    SystemMessage(content=FALLBACK_SYSTEM_PROMPT),
                ]
                if history.messages:
                    answer_messages.extend(history.messages[-4:])
                answer_messages.append(HumanMessage(content=query))
            
            # 生成答案
            response = self.llm.invoke(answer_messages)
            logger.info(f"   ✅ 答案生成完成 ({time.time() - step4_start:.2f}s)")
            
            # 提取最终答案
            answer = response.content if hasattr(response, 'content') else str(response)
            
            # 如果是兜底回答，添加提示前缀
            if not has_valid_content:
                answer = KB_NOT_FOUND_PREFIX + answer
                all_sources = []  # 清空来源，因为是 LLM 自己的知识
            
            # 处理可能的思考标记
            if answer and "<think>" in answer:
                import re
                answer = re.sub(r'<think>.*?</think>', '', answer, flags=re.DOTALL).strip()
            
            # 更新会话历史
            history.add_user_message(query)
            history.add_ai_message(answer)
            
            # 检测是否需要澄清
            needs_clarification = False
            clarification_phrases = [
                "请问你想了解",
                "你是想问",
                "你指的是",
                "能否具体说明",
                "请具体说明"
            ]
            
            for phrase in clarification_phrases:
                if phrase in answer:
                    needs_clarification = True
                    break
            
            # 完成日志
            total_time = time.time() - start_time
            logger.info(f"✅ 处理完成! 总耗时: {total_time:.2f}s, 工具调用: {len(tool_calls_info)}, 来源: {len(all_sources)}")
            logger.info(f"📤 答案长度: {len(answer)} 字符")
            logger.info(f"=" * 50)
            
            return AgentResponse(
                answer=answer,
                tool_calls=tool_calls_info,
                sources=all_sources,
                needs_clarification=needs_clarification,
                clarification_options=[]
            )
            
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"❌ Agent 执行失败 (耗时 {total_time:.2f}s): {e}")
            import traceback
            traceback.print_exc()
            
            return AgentResponse(
                answer=f"抱歉，处理您的问题时出现错误：{str(e)}",
                tool_calls=[],
                sources=[],
                needs_clarification=False
            )
    
    def clear_history(self, session_id: str = "default"):
        """清空指定会话的历史"""
        if session_id in self.session_histories:
            self.session_histories[session_id].clear()
    
    def get_history(self, session_id: str = "default") -> List[Dict[str, str]]:
        """获取会话历史"""
        if session_id not in self.session_histories:
            return []
        
        history = self.session_histories[session_id]
        return [
            {
                "role": "user" if isinstance(msg, HumanMessage) else "assistant",
                "content": msg.content
            }
            for msg in history.messages
        ]
    
    def get_all_sessions(self) -> List[str]:
        """获取所有会话 ID"""
        return list(self.session_histories.keys())


# ==========================================
# 简化的问题澄清检测
# ==========================================

class ClarificationDetector:
    """检测问题是否需要澄清"""
    
    VAGUE_PATTERNS = [
        "这个", "那个", "它", "他们",
        "怎么样", "如何", "什么情况"
    ]
    
    INCOMPLETE_PATTERNS = [
        r"^.{1,5}$",  # 过短的问题
    ]
    
    @classmethod
    def needs_clarification(cls, query: str, context: List[str] = None) -> tuple[bool, str]:
        """
        检测是否需要澄清
        
        Returns:
            (是否需要澄清, 建议的澄清提示)
        """
        import re
        
        # 如果问题过短
        if len(query.strip()) < 3:
            return True, "您的问题太简短了，能否详细描述一下您想了解什么？"
        
        # 如果问题只有代词且没有上下文
        has_pronoun_only = any(p in query for p in ["这个", "那个", "它"]) and len(query) < 10
        if has_pronoun_only and not context:
            return True, "您说的是哪个概念呢？请具体说明一下。"
        
        return False, ""


# ==========================================
# 全局单例
# ==========================================

_agent: Optional[LangChainAgent] = None


def get_agent() -> LangChainAgent:
    """获取全局 Agent 实例"""
    global _agent
    if _agent is None:
        _agent = LangChainAgent()
    return _agent


def chat(query: str, session_id: str = "default") -> AgentResponse:
    """便捷函数：对话"""
    return get_agent().chat(query, session_id)


# ==========================================
# CLI 测试
# ==========================================

if __name__ == "__main__":
    print("=" * 60)
    print("🤖 计算机系统基础 - 智能学习助手 (LangChain Agent)")
    print("=" * 60)
    print("输入问题开始对话，输入 'quit' 退出, 'clear' 清空历史\n")
    
    agent = LangChainAgent()
    session_id = "cli_test"
    
    while True:
        try:
            query = input("👤 你: ").strip()
            if not query:
                continue
            if query.lower() in ['quit', 'exit', 'q']:
                print("再见！")
                break
            if query.lower() == 'clear':
                agent.clear_history(session_id)
                print("✅ 对话历史已清空")
                continue
            
            print("🤖 助手: 思考中...", end="\r")
            response = agent.chat(query, session_id)
            
            print(f"🤖 助手:\n{response.answer}")
            
            if response.tool_calls:
                print("\n🔧 工具调用:")
                for tc in response.tool_calls:
                    print(f"   - {tc['tool']}: {tc.get('input', {})}")
            
            print("-" * 40)
            
        except KeyboardInterrupt:
            print("\n再见！")
            break
        except Exception as e:
            print(f"❌ 错误: {e}")
