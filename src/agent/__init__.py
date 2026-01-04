"""
Agent 模块
提供问答 Agent、工具和意图分类功能
"""

from src.agent.intent import (
    IntentType,
    IntentResult,
    IntentClassifier,
    classify_intent,
    get_tool_for_intent
)

from src.agent.tools import (
    QATools,
    ToolResult,
    get_tools,
    TOOL_DESCRIPTIONS
)

from src.agent.qa_agent import (
    QAAgent,
    QAResponse,
    Message,
    get_agent,
    chat
)

__all__ = [
    # Intent
    "IntentType",
    "IntentResult",
    "IntentClassifier",
    "classify_intent",
    "get_tool_for_intent",
    # Tools
    "QATools",
    "ToolResult",
    "get_tools",
    "TOOL_DESCRIPTIONS",
    # Agent
    "QAAgent",
    "QAResponse",
    "Message",
    "get_agent",
    "chat"
]
