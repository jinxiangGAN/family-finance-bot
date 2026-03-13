"""MCP Tool: Event/trip tag management."""

from app.skills import skill_query_event_summary, skill_start_event, skill_stop_event

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "start_event",
            "description": "开启一个事件/旅行标签。开启后所有记账自动附带此标签。用户说'开始日本旅行'、'开启XX事件'时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "tag": {"type": "string", "description": "事件标签名，如'日本旅行'、'春节'"},
                    "description": {"type": "string", "description": "事件描述"},
                },
                "required": ["tag"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "stop_event",
            "description": "关闭当前活跃的事件标签。用户说'结束旅行'、'关闭事件'时调用。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_event_summary",
            "description": "查询某个事件/旅行的花费汇总和AA结算。",
            "parameters": {
                "type": "object",
                "properties": {
                    "tag": {"type": "string", "description": "事件标签名"},
                },
                "required": ["tag"],
            },
        },
    },
]

HANDLERS = {
    "start_event": skill_start_event,
    "stop_event": skill_stop_event,
    "query_event_summary": skill_query_event_summary,
}
