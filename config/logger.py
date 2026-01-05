"""
日志配置模块
使用 loguru 提供统一的日志管理
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# 尝试导入 loguru，如果不存在则使用标准 logging
try:
    from loguru import logger
    LOGURU_AVAILABLE = True
except ImportError:
    import logging
    LOGURU_AVAILABLE = False
    logger = logging.getLogger("kg_assistant")


# ==========================================
# 日志配置
# ==========================================

# 日志目录
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# 日志级别（从环境变量读取）
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# 日志格式
LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)

# 简洁格式（用于控制台）
LOG_FORMAT_SIMPLE = (
    "<green>{time:HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<level>{message}</level>"
)


def setup_logger():
    """配置日志系统"""
    
    if LOGURU_AVAILABLE:
        # 移除默认处理器
        logger.remove()
        
        # 添加控制台处理器（简洁格式）
        logger.add(
            sys.stderr,
            format=LOG_FORMAT_SIMPLE,
            level=LOG_LEVEL,
            colorize=True,
            backtrace=True,
            diagnose=True
        )
        
        # 添加文件处理器（详细格式，按天轮转）
        log_file = LOG_DIR / "app_{time:YYYY-MM-DD}.log"
        logger.add(
            str(log_file),
            format=LOG_FORMAT,
            level="DEBUG",  # 文件记录所有级别
            rotation="00:00",  # 每天轮转
            retention="7 days",  # 保留7天
            compression="zip",  # 压缩旧日志
            encoding="utf-8",
            enqueue=True  # 异步写入
        )
        
        # 添加错误日志文件（只记录错误）
        error_log_file = LOG_DIR / "error_{time:YYYY-MM-DD}.log"
        logger.add(
            str(error_log_file),
            format=LOG_FORMAT,
            level="ERROR",
            rotation="00:00",
            retention="30 days",
            compression="zip",
            encoding="utf-8",
            enqueue=True
        )
        
        logger.info(f"日志系统已初始化 | 级别: {LOG_LEVEL} | 目录: {LOG_DIR}")
        
    else:
        # 使用标准 logging 作为后备
        logging.basicConfig(
            level=getattr(logging, LOG_LEVEL, logging.INFO),
            format="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s",
            handlers=[
                logging.StreamHandler(sys.stderr),
                logging.FileHandler(
                    LOG_DIR / f"app_{datetime.now().strftime('%Y-%m-%d')}.log",
                    encoding="utf-8"
                )
            ]
        )
        logger.info(f"日志系统已初始化（标准模式）| 级别: {LOG_LEVEL}")


def get_logger(name: str = None):
    """
    获取日志记录器
    
    Args:
        name: 模块名称（用于日志标识）
        
    Returns:
        logger 实例
    """
    if LOGURU_AVAILABLE:
        if name:
            return logger.bind(name=name)
        return logger
    else:
        return logging.getLogger(name or "kg_assistant")


# ==========================================
# 便捷函数
# ==========================================

def log_function_call(func_name: str, **kwargs):
    """记录函数调用"""
    params = ", ".join(f"{k}={v}" for k, v in kwargs.items())
    logger.debug(f"调用 {func_name}({params})")


def log_api_call(endpoint: str, method: str = "GET", status: int = None, duration: float = None):
    """记录 API 调用"""
    msg = f"API {method} {endpoint}"
    if status:
        msg += f" | 状态: {status}"
    if duration:
        msg += f" | 耗时: {duration:.2f}s"
    logger.info(msg)


def log_error_with_context(error: Exception, context: dict = None):
    """记录错误及上下文"""
    if context:
        context_str = " | ".join(f"{k}={v}" for k, v in context.items())
        logger.error(f"{type(error).__name__}: {error} | 上下文: {context_str}")
    else:
        logger.exception(f"{type(error).__name__}: {error}")


# ==========================================
# 初始化
# ==========================================

# 模块导入时自动初始化
setup_logger()


# 导出
__all__ = [
    "logger",
    "get_logger",
    "setup_logger",
    "log_function_call",
    "log_api_call",
    "log_error_with_context",
    "LOG_DIR",
    "LOG_LEVEL"
]

