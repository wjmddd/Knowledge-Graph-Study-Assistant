"""
对话历史管理模块
负责对话记录的保存、加载和列表
"""

import json
from pathlib import Path
from typing import List, Dict
from datetime import datetime


# ==========================================
# 配置
# ==========================================
HISTORY_DIR = Path("data/chat_history")
HISTORY_DIR.mkdir(parents=True, exist_ok=True)


# ==========================================
# 对话历史管理函数
# ==========================================

def save_conversation(session_id: str, messages: List[Dict]) -> bool:
    """
    保存对话历史到文件
    
    Args:
        session_id: 会话 ID
        messages: 消息列表
        
    Returns:
        是否保存成功
    """
    try:
        history_file = HISTORY_DIR / f"{session_id}.json"
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump({
                "session_id": session_id,
                "updated_at": datetime.now().isoformat(),
                "messages": messages
            }, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存对话历史失败: {e}")
        return False


def load_conversation(session_id: str) -> List[Dict]:
    """
    加载对话历史
    
    Args:
        session_id: 会话 ID
        
    Returns:
        消息列表
    """
    try:
        history_file = HISTORY_DIR / f"{session_id}.json"
        if history_file.exists():
            with open(history_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("messages", [])
    except Exception as e:
        print(f"加载对话历史失败: {e}")
    return []


def list_conversations(limit: int = 20) -> List[Dict]:
    """
    列出所有对话历史
    
    Args:
        limit: 最多返回的对话数量
        
    Returns:
        对话列表，按更新时间降序排列
    """
    conversations = []
    try:
        for f in HISTORY_DIR.glob("*.json"):
            with open(f, "r", encoding="utf-8") as file:
                data = json.load(file)
                # 获取第一条用户消息作为标题
                messages = data.get("messages", [])
                title = "新对话"
                for msg in messages:
                    if msg.get("role") == "user":
                        title = msg.get("content", "")[:30]
                        if len(msg.get("content", "")) > 30:
                            title += "..."
                        break
                conversations.append({
                    "session_id": data.get("session_id"),
                    "title": title,
                    "updated_at": data.get("updated_at"),
                    "message_count": len(messages)
                })
        # 按更新时间排序
        conversations.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    except Exception as e:
        print(f"列出对话历史失败: {e}")
    return conversations[:limit]


def delete_conversation(session_id: str) -> bool:
    """
    删除指定的对话历史
    
    Args:
        session_id: 会话 ID
        
    Returns:
        是否删除成功
    """
    try:
        history_file = HISTORY_DIR / f"{session_id}.json"
        if history_file.exists():
            history_file.unlink()
            return True
    except Exception as e:
        print(f"删除对话历史失败: {e}")
    return False


def clear_all_conversations() -> int:
    """
    清除所有对话历史
    
    Returns:
        删除的对话数量
    """
    count = 0
    try:
        for f in HISTORY_DIR.glob("*.json"):
            f.unlink()
            count += 1
    except Exception as e:
        print(f"清除对话历史失败: {e}")
    return count

