"""MCP-style pluggable tool registry.

Each tool module in this package defines:
  - TOOLS: list[dict]  — OpenAI-compatible function schemas
  - HANDLERS: dict[str, Callable]  — skill_name → handler(user_id, user_name, params) -> dict

The registry auto-discovers all modules and merges their definitions.
To add a new tool: just create a .py file in this directory following the pattern.
"""
