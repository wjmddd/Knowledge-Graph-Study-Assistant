"""
服务模块
提供对话历史、图谱查询、推荐等功能
"""

from .history import (
    save_conversation,
    load_conversation,
    list_conversations,
    HISTORY_DIR
)

from .graph_service import (
    get_graph_stats,
    query_concept_detail,
    generate_concept_graph_text,
    generate_interactive_graph,
    GRAPH_VIZ_DIR
)

from .recommendation import (
    get_related_questions,
    extract_main_concept
)

__all__ = [
    # 历史记录
    "save_conversation",
    "load_conversation", 
    "list_conversations",
    "HISTORY_DIR",
    # 图谱服务
    "get_graph_stats",
    "query_concept_detail",
    "generate_concept_graph_text",
    "generate_interactive_graph",
    "GRAPH_VIZ_DIR",
    # 推荐
    "get_related_questions",
    "extract_main_concept",
]

