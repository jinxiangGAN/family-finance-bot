"""MCP Tool: Expense management — record, delete, export."""

from app.skills import skill_delete_last, skill_export_csv, skill_record_expense
from app.config import CATEGORIES, CURRENCY

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "record_expense",
            "description": "记录一笔支出。用户说了具体花费时调用。支持多币种和事件标签。",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "支出分类", "enum": CATEGORIES},
                    "amount": {"type": "number", "description": "金额"},
                    "note": {"type": "string", "description": "备注说明"},
                    "currency": {"type": "string", "description": f"货币代码，默认 {CURRENCY}"},
                    "event_tag": {"type": "string", "description": "事件/旅行标签（留空则自动使用活跃标签）"},
                },
                "required": ["category", "amount", "note"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_last_expense",
            "description": "删除用户最近一条支出记录。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "export_csv",
            "description": "导出账单为CSV。用户说'导出账单'、'导出数据'时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "scope": {"type": "string", "description": "导出范围", "enum": ["me", "family"]},
                    "event_tag": {"type": "string", "description": "只导出指定事件的数据"},
                },
            },
        },
    },
]

HANDLERS = {
    "record_expense": skill_record_expense,
    "delete_last_expense": skill_delete_last,
    "export_csv": skill_export_csv,
}
