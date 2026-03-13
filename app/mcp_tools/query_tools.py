"""MCP Tool: Query & analytics — monthly totals, summaries, analysis."""

from app.config import CATEGORIES
from app.skills import (
    skill_get_spending_analysis,
    skill_query_budget,
    skill_query_category_total,
    skill_query_monthly_total,
    skill_query_summary,
    skill_set_budget,
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_monthly_total",
            "description": "查询本月总支出。",
            "parameters": {
                "type": "object",
                "properties": {
                    "scope": {"type": "string", "description": "查询范围", "enum": ["me", "spouse", "family"]},
                },
                "required": ["scope"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_category_total",
            "description": "查询本月某个分类的支出。",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "支出分类", "enum": CATEGORIES},
                    "scope": {"type": "string", "description": "查询范围", "enum": ["me", "spouse", "family"]},
                },
                "required": ["category", "scope"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_summary",
            "description": "查询本月按分类的支出汇总。",
            "parameters": {
                "type": "object",
                "properties": {
                    "scope": {"type": "string", "description": "查询范围", "enum": ["me", "spouse", "family"]},
                },
                "required": ["scope"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_budget",
            "description": "设置每月预算上限。category 为 '_total' 表示总预算。",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "预算分类，'_total' 表示总预算"},
                    "amount": {"type": "number", "description": "每月预算金额"},
                },
                "required": ["category", "amount"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_budget",
            "description": "查询预算使用情况。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_spending_analysis",
            "description": "获取消费数据用于分析和财务建议。",
            "parameters": {
                "type": "object",
                "properties": {
                    "scope": {"type": "string", "description": "分析范围", "enum": ["me", "spouse", "family"]},
                },
                "required": ["scope"],
            },
        },
    },
]

HANDLERS = {
    "query_monthly_total": skill_query_monthly_total,
    "query_category_total": skill_query_category_total,
    "query_summary": skill_query_summary,
    "set_budget": skill_set_budget,
    "query_budget": skill_query_budget,
    "get_spending_analysis": skill_get_spending_analysis,
}
