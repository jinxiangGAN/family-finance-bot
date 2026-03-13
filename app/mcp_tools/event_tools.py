"""MCP Tool: Event/trip tag management."""

from app.skills import skill_query_event_summary, skill_start_event, skill_stop_event

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "start_event",
            "description": "Start an event/trip tag. Once active, all subsequent expenses are automatically tagged with this event. Call when user says 'start Japan trip', 'begin event XX', etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tag": {"type": "string", "description": "Event tag name, e.g., 'Japan Trip', 'Chinese New Year'"},
                    "description": {"type": "string", "description": "Optional event description"},
                },
                "required": ["tag"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "stop_event",
            "description": "Stop the currently active event/trip tag. Call when user says 'end trip', 'close event', etc.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_event_summary",
            "description": "Query the total spending summary and AA split for a specific event/trip.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tag": {"type": "string", "description": "Event tag name to query"},
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
