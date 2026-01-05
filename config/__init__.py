"""
配置模块

包含：
- settings.py: 全局配置（API密钥、数据库连接等）
- logger.py: 日志配置
- env.template: 环境变量模板
"""

from .settings import (
    # 路径配置
    PROJECT_ROOT,
    DATA_DIR,
    MD_INPUT_DIR,
    CHAPTER_OUTPUT_DIR,
    CHROMA_DB_DIR,
    LOG_DIR,
    # API 配置
    CLIENT_CONFIG,
    OPENAI_CONFIG,
    NEO4J_CONFIG,
    CHROMA_CONFIG,
    APP_CONFIG,
    QA_CONFIG,
    # 知识抽取配置
    INPUT_FILE,
    OUTPUT_FILE,
    MAX_WORKERS,
    REQUEST_DELAY,
    CHUNK_SIZE,
    # 提示词
    ANSWER_SYSTEM_PROMPT,
    TOOL_SELECTION_SYSTEM_PROMPT,
    TOOL_SELECTION_USER_PROMPT,
    USER_QUERY_WITH_CONTEXT_TEMPLATE,
    FALLBACK_SYSTEM_PROMPT,
    KB_NOT_FOUND_PREFIX,
    # 术语映射
    TERM_MAPPINGS,
    ALIAS_TO_CANONICAL,
    normalize_term,
    get_term_variants,
    # 配置工具
    validate_config,
    print_config_summary,
)

from .logger import (
    logger,
    get_logger,
    setup_logger,
    log_function_call,
    log_api_call,
    log_error_with_context,
)

__all__ = [
    # 路径
    "PROJECT_ROOT",
    "DATA_DIR",
    "MD_INPUT_DIR",
    "CHAPTER_OUTPUT_DIR",
    "CHROMA_DB_DIR",
    "LOG_DIR",
    # 配置
    "CLIENT_CONFIG",
    "OPENAI_CONFIG",
    "NEO4J_CONFIG",
    "CHROMA_CONFIG",
    "APP_CONFIG",
    "QA_CONFIG",
    # 知识抽取
    "INPUT_FILE",
    "OUTPUT_FILE",
    "MAX_WORKERS",
    "REQUEST_DELAY",
    "CHUNK_SIZE",
    # 提示词
    "ANSWER_SYSTEM_PROMPT",
    "TOOL_SELECTION_SYSTEM_PROMPT",
    "TOOL_SELECTION_USER_PROMPT",
    "USER_QUERY_WITH_CONTEXT_TEMPLATE",
    "FALLBACK_SYSTEM_PROMPT",
    "KB_NOT_FOUND_PREFIX",
    # 术语
    "TERM_MAPPINGS",
    "ALIAS_TO_CANONICAL",
    "normalize_term",
    "get_term_variants",
    # 配置工具
    "validate_config",
    "print_config_summary",
    # 日志
    "logger",
    "get_logger",
    "setup_logger",
    "log_function_call",
    "log_api_call",
    "log_error_with_context",
]
