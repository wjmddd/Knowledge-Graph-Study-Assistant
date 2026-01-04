"""
问答 Agent 主模块
协调意图识别、工具调用和答案生成
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from openai import OpenAI

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config.settings import CLIENT_CONFIG, QA_CONFIG
from src.agent.intent import classify_intent, IntentType, IntentResult, get_tool_for_intent
from src.agent.tools import get_tools, ToolResult


@dataclass
class Message:
    """对话消息"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QAResponse:
    """问答响应"""
    answer: str
    sources: List[Dict[str, str]]
    intent: str
    entities: List[str]
    tool_used: str
    success: bool


class QAAgent:
    """问答 Agent"""
    
    def __init__(self):
        self.tools = get_tools()
        self.llm_client = OpenAI(
            api_key=CLIENT_CONFIG["api_key"],
            base_url=CLIENT_CONFIG["base_url"]
        )
        self.model = CLIENT_CONFIG["model"]
        self.config = QA_CONFIG
        
        # 对话历史
        self.history: List[Message] = []
        self.max_history = 10  # 最多保留的历史消息数
    
    def chat(self, query: str) -> QAResponse:
        """
        处理用户问题
        
        Args:
            query: 用户问题
            
        Returns:
            QAResponse 包含答案、来源等信息
        """
        # 1. 意图识别
        intent_result = classify_intent(query)
        
        # 2. 工具选择与执行
        tool_name = get_tool_for_intent(intent_result.intent)
        tool_result = self._execute_tool(tool_name, intent_result)
        
        # 3. 生成答案
        answer, sources = self._generate_answer(query, intent_result, tool_result)
        
        # 4. 更新历史
        self.history.append(Message(role="user", content=query))
        self.history.append(Message(
            role="assistant",
            content=answer,
            metadata={"intent": intent_result.intent.value, "tool": tool_name}
        ))
        
        # 限制历史长度
        if len(self.history) > self.max_history * 2:
            self.history = self.history[-self.max_history * 2:]
        
        return QAResponse(
            answer=answer,
            sources=sources,
            intent=intent_result.intent.value,
            entities=intent_result.entities,
            tool_used=tool_name,
            success=tool_result.success if tool_result else False
        )
    
    def _execute_tool(
        self,
        tool_name: str,
        intent_result: IntentResult
    ) -> Optional[ToolResult]:
        """执行工具"""
        entities = intent_result.entities
        
        try:
            if tool_name == "get_concept_definition":
                if entities:
                    return self.tools.get_concept_definition(entities[0])
            
            elif tool_name == "get_concept_composition":
                if entities:
                    return self.tools.get_concept_composition(entities[0])
            
            elif tool_name == "get_learning_path":
                if entities:
                    return self.tools.get_learning_path(entities[0])
            
            elif tool_name == "compare_concepts":
                if len(entities) >= 2:
                    return self.tools.compare_concepts(entities[0], entities[1])
            
            elif tool_name == "find_path_between":
                if len(entities) >= 2:
                    return self.tools.find_path_between(entities[0], entities[1])
            
            elif tool_name == "hybrid_search":
                return self.tools.hybrid_search(
                    query=intent_result.raw_query,
                    entities=entities if entities else None
                )
            
            # 默认使用混合搜索
            return self.tools.hybrid_search(
                query=intent_result.raw_query,
                entities=entities if entities else None
            )
            
        except Exception as e:
            print(f"⚠️ 工具执行失败: {e}")
            return ToolResult(success=False, data=None, message=str(e))
    
    def _generate_answer(
        self,
        query: str,
        intent_result: IntentResult,
        tool_result: Optional[ToolResult]
    ) -> tuple[str, List[Dict[str, str]]]:
        """使用 LLM 生成答案"""
        
        # 构建上下文
        context_parts = []
        sources = []
        
        if tool_result and tool_result.success and tool_result.data:
            data = tool_result.data
            
            # 根据不同工具类型提取上下文
            if intent_result.intent == IntentType.CONCEPT_DEFINITION:
                if data.get("definition"):
                    context_parts.append(f"**{data.get('name')}** 的定义：{data['definition']}")
                if data.get("alias"):
                    context_parts.append(f"别名：{', '.join(data['alias'])}")
                if data.get("sources"):
                    for src in data["sources"]:
                        sources.append({
                            "chapter": src.get("chapter", "未知"),
                            "section": src.get("section", "未知")
                        })
                        if src.get("content"):
                            context_parts.append(f"相关内容：{src['content']}")
            
            elif intent_result.intent == IntentType.CONCEPT_COMPOSITION:
                if data.get("components"):
                    comp_list = [f"- {c['name']}" + (f": {c['definition']}" if c.get('definition') else "") 
                                for c in data["components"]]
                    context_parts.append(f"**{data.get('concept')}** 的组成部分：\n" + "\n".join(comp_list))
            
            elif intent_result.intent == IntentType.LEARNING_PATH:
                if data.get("learning_path"):
                    path_str = " → ".join(data["learning_path"])
                    context_parts.append(f"学习 **{data.get('target')}** 的建议路径：{path_str}")
            
            elif intent_result.intent == IntentType.COMPARE:
                a_info = data.get("concept_a", {})
                b_info = data.get("concept_b", {})
                if a_info.get("definition"):
                    context_parts.append(f"**{a_info.get('name')}**：{a_info['definition']}")
                if b_info.get("definition"):
                    context_parts.append(f"**{b_info.get('name')}**：{b_info['definition']}")
                if data.get("direct_relation"):
                    context_parts.append(f"它们之间的关系：{data['direct_relation'].get('type')}")
                if data.get("common_parent"):
                    context_parts.append(f"共同上级类别：{data['common_parent']}")
            
            elif intent_result.intent == IntentType.RELATION:
                if data.get("path"):
                    path_desc = []
                    for p in data["path"]:
                        path_desc.append(f"{p['from']} --[{p['relation']}]--> {p['to']}")
                    context_parts.append(f"关系路径：\n" + "\n".join(path_desc))
            
            else:  # GENERAL / hybrid_search
                if data.get("graph_results"):
                    for r in data["graph_results"]:
                        context_parts.append(r["content"])
                if data.get("vector_results"):
                    for r in data["vector_results"]:
                        context_parts.append(r["content"])
                        sources.append({
                            "chapter": r.get("chapter", "未知"),
                            "section": r.get("section", "未知")
                        })
        
        # 如果没有找到任何上下文，使用语义搜索兜底
        if not context_parts:
            fallback = self.tools.semantic_search(query)
            if fallback.success and fallback.data:
                for r in fallback.data.get("results", []):
                    context_parts.append(r["content"])
                    sources.append({
                        "chapter": r.get("chapter", "未知"),
                        "section": r.get("section", "未知")
                    })
        
        # 构建 Prompt
        context_text = "\n\n".join(context_parts) if context_parts else "未找到相关信息"
        
        # 包含对话历史
        history_text = ""
        if self.history:
            recent_history = self.history[-4:]  # 最近2轮对话
            history_parts = []
            for msg in recent_history:
                role_label = "用户" if msg.role == "user" else "助手"
                history_parts.append(f"{role_label}: {msg.content}")
            history_text = "\n".join(history_parts)
        
        system_prompt = """你是一个《计算机系统基础》课程的智能学习助手。请基于提供的知识库内容回答用户的问题。

要求：
1. 回答要准确、专业，基于提供的上下文
2. 如果上下文中没有相关信息，诚实说明并提供你所知道的一般性知识
3. 使用清晰的结构（如列表、分点）组织回答
4. 对于概念解释，先给出定义，再详细说明
5. 如果涉及对比，使用表格或对比列表
6. 保持友好、耐心的教学语气"""

        user_prompt = f"""## 历史对话
{history_text if history_text else "（无历史对话）"}

## 知识库检索结果
{context_text}

## 用户问题
{query}

请根据以上信息回答用户的问题。"""

        try:
            response = self.llm_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.config["temperature"],
                max_tokens=self.config["max_tokens"]
            )
            answer = response.choices[0].message.content
            
            # 处理某些模型返回的思考过程标记
            if "<think>" in answer:
                # 移除 <think>...</think> 部分
                import re
                answer = re.sub(r'<think>.*?</think>', '', answer, flags=re.DOTALL).strip()
            
        except Exception as e:
            print(f"⚠️ LLM 生成失败: {e}")
            answer = f"抱歉，生成答案时出现错误。根据检索到的信息：\n\n{context_text}"
        
        return answer, sources
    
    def clear_history(self):
        """清空对话历史"""
        self.history = []
    
    def get_history(self) -> List[Dict[str, Any]]:
        """获取对话历史"""
        return [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "metadata": msg.metadata
            }
            for msg in self.history
        ]


# 全局单例
_agent: Optional[QAAgent] = None


def get_agent() -> QAAgent:
    """获取全局 Agent 实例"""
    global _agent
    if _agent is None:
        _agent = QAAgent()
    return _agent


def chat(query: str) -> QAResponse:
    """便捷函数：对话"""
    return get_agent().chat(query)


if __name__ == "__main__":
    # 测试
    print("=" * 60)
    print("🤖 计算机系统基础 - 智能学习助手 (CLI 模式)")
    print("=" * 60)
    print("输入问题开始对话，输入 'quit' 退出\n")
    
    agent = QAAgent()
    
    while True:
        try:
            query = input("👤 你: ").strip()
            if not query:
                continue
            if query.lower() in ['quit', 'exit', 'q']:
                print("再见！")
                break
            
            print("🤖 助手: 思考中...", end="\r")
            response = agent.chat(query)
            
            print(f"🤖 助手:\n{response.answer}")
            
            if response.sources:
                print("\n📚 来源:")
                for src in response.sources[:3]:
                    print(f"   - {src.get('chapter', '未知')} / {src.get('section', '未知')}")
            
            print(f"\n[意图: {response.intent}, 实体: {response.entities}, 工具: {response.tool_used}]")
            print("-" * 40)
            
        except KeyboardInterrupt:
            print("\n再见！")
            break
        except Exception as e:
            print(f"❌ 错误: {e}")

