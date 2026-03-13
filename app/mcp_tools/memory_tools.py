"""MCP Tool: Semantic memory — store and recall long-term knowledge."""

from app.memory import delete_memory, recall_memories, store_memory


def _handle_store_memory(user_id: int, user_name: str, params: dict) -> dict:
    """Store a new memory about the user/family."""
    content = params.get("content", "").strip()
    if not content:
        return {"success": False, "message": "记忆内容不能为空"}

    category = params.get("category", "general")
    importance = int(params.get("importance", 5))
    # user_id=0 means family-shared memory
    target_uid = 0 if params.get("shared", False) else user_id

    memory_id = store_memory(target_uid, content, category, importance)
    return {
        "success": True,
        "memory_id": memory_id,
        "message": f"已记住：{content[:50]}{'...' if len(content) > 50 else ''}",
    }


def _handle_recall_memories(user_id: int, user_name: str, params: dict) -> dict:
    """Recall relevant memories."""
    query = params.get("query", "").strip()
    if not query:
        return {"success": False, "memories": [], "message": "请提供检索关键词"}

    memories = recall_memories(user_id, query, limit=5)
    return {
        "success": True,
        "memories": [m["content"] for m in memories],
        "count": len(memories),
    }


def _handle_forget_memory(user_id: int, user_name: str, params: dict) -> dict:
    """Delete a specific memory."""
    memory_id = int(params.get("memory_id", 0))
    if memory_id <= 0:
        return {"success": False, "message": "请提供记忆ID"}
    deleted = delete_memory(memory_id)
    if deleted:
        return {"success": True, "message": f"已遗忘记忆 #{memory_id}"}
    return {"success": False, "message": f"未找到记忆 #{memory_id}"}


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "store_memory",
            "description": (
                "记住一条重要信息。当用户表达偏好、设定目标、做出决定、或提到重要家庭事项时调用。"
                "例如：'这个月要减少打车'、'周末不在外面吃饭'、'下个月要存3000'"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "要记住的内容"},
                    "category": {
                        "type": "string",
                        "description": "分类",
                        "enum": ["preference", "goal", "decision", "habit", "reminder", "general"],
                    },
                    "importance": {
                        "type": "integer",
                        "description": "重要程度 1-10（10=非常重要）",
                    },
                    "shared": {
                        "type": "boolean",
                        "description": "是否为家庭共享记忆（true=两人都能看到）",
                    },
                },
                "required": ["content", "category", "importance"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recall_memories",
            "description": "回忆相关的历史信息。当需要参考之前的讨论、决定或偏好时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "forget_memory",
            "description": "忘记一条记忆。用户说'忘掉XX'时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "memory_id": {"type": "integer", "description": "记忆的ID"},
                },
                "required": ["memory_id"],
            },
        },
    },
]

HANDLERS = {
    "store_memory": _handle_store_memory,
    "recall_memories": _handle_recall_memories,
    "forget_memory": _handle_forget_memory,
}
