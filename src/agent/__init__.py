"""
Agent 模块
提供问答 Agent 和工具功能

当前使用 LangChain Agent (Phase 2)
"""

# LangChain Tools
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

# LangChain Agent
from src.agent.langchain_agent import (
    LangChainAgent,
    AgentResponse,
    get_agent,
    chat
)

__all__ = [
    # LangChain Tools
    "get_langchain_tools",
    "get_concept_definition",
    "get_concept_composition", 
    "get_learning_path",
    "compare_concepts",
    "find_concept_relation",
    "semantic_search",
    "hybrid_search",
    # LangChain Agent
    "LangChainAgent",
    "AgentResponse",
    "get_agent",
    "chat"
]
