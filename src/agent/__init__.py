"""
Agent 模块
提供问答 Agent、工具和意图分类功能
支持两种模式：简单路由 (Phase 1) 和 LangChain Agent (Phase 2)
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

# Phase 2: LangChain Agent
from src.agent.langchain_tools import (
    get_langchain_tools,
    get_concept_definition,
    get_concept_composition,
    get_learning_path,
    compare_concepts,
    find_concept_relation,
    semantic_search,
    hybrid_search
)

from src.agent.langchain_agent import (
    LangChainAgent,
    AgentResponse,
    get_agent as get_langchain_agent,
    chat as langchain_chat
)

__all__ = [
    # Intent
    "IntentType",
    "IntentResult",
    "IntentClassifier",
    "classify_intent",
    "get_tool_for_intent",
    # Tools (Phase 1)
    "QATools",
    "ToolResult",
    "get_tools",
    "TOOL_DESCRIPTIONS",
    # Agent (Phase 1)
    "QAAgent",
    "QAResponse",
    "Message",
    "get_agent",
    "chat",
    # LangChain Tools (Phase 2)
    "get_langchain_tools",
    "get_concept_definition",
    "get_concept_composition", 
    "get_learning_path",
    "compare_concepts",
    "find_concept_relation",
    "semantic_search",
    "hybrid_search",
    # LangChain Agent (Phase 2)
    "LangChainAgent",
    "AgentResponse",
    "get_langchain_agent",
    "langchain_chat"
]
