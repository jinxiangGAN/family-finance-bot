# Family Finance Telegram Bot

A smart Telegram bot for family expense tracking, powered by a **memory-augmented LLM agent** with MCP-style pluggable tools. Designed for a 2-person household to record, query, and analyze daily spending through natural language — with long-term memory that understands your habits and goals.

## Features

### 🧠 Intelligent Agent
- **Semantic Memory** — Remembers preferences, goals, and family decisions across conversations
- **Session-Aware Persona** — Warm and empathetic in private chat; objective in group chat
- **Proactive Engagement** — Friday evening check-ins, daily budget alerts, memory-augmented weekly reports

### 💰 Expense Tracking
- **Natural Language** — Send `lunch 35` or `taxi 18` to record instantly
- **Receipt OCR** — Send a photo of a receipt → vision model auto-extracts expenses
- **Multi-Currency** — Record in SGD, CNY, USD, AUD, JPY, etc. with automatic conversion
- **Three Query Views** — Check spending for yourself, your spouse, or the whole family
- **Event/Trip Tags** — Tag expenses for trips (e.g., "Japan Trip") with AA split summary

### 📊 Budget & Analysis
- **Budget Management** — Set monthly budgets per category with automatic overspend alerts
- **Financial Analysis & Advice** — Ask the bot for spending insights and saving tips
- **Weekly Summary** — Automated report pushed to all family members every Sunday

### 🔧 Infrastructure
- **MCP Tool Registry** — Pluggable tool architecture; add new skills by dropping a file
- **Multi-Provider LLM** — Switch between MiniMax, OpenAI, DeepSeek, Qwen, or any OpenAI-compatible API
- **API Cost Control** — Monthly token limit with automatic fallback to regex parsing
- **CSV Export** — `/export` to download expense data
- **Docker Ready** — One-command deployment with docker-compose

## Architecture

```
User Message (text / photo)
     ↓
Telegram Bot (polling mode, session-aware)
     ↓
Session Manager ← private vs group chat → persona adaptation
     ↓
Memory Layer ← recall relevant memories → inject into system prompt
     ↓
LLM Agent (function calling / regex fallback)
  ├── Text → MCP tool dispatch
  └── Photo → Vision OCR → MCP tool dispatch
     ↓
MCP Tool Registry (auto-discover & dispatch)
  ├── expense_tools  (record, delete, export)
  ├── query_tools    (totals, summary, budget, analysis)
  ├── event_tools    (start, stop, event summary)
  └── memory_tools   (store, recall, forget)
     ↓
SQLite Database (expenses, budgets, events, api_usage, memories + FTS5)
```

## Project Structure

```
family-finance-bot/
├── app/
│   ├── main.py              # Entry point
│   ├── telegram_bot.py      # Bot handlers, commands, scheduled jobs
│   ├── agent.py             # LLM agent v3: memory + session + MCP
│   ├── llm_provider.py      # Abstract LLM interface (OpenAI-compatible)
│   ├── skills.py            # Core skill implementations
│   ├── memory.py            # Semantic memory: store, recall, FTS5 search
│   ├── session.py           # Session management: private vs group context
│   ├── api_tracker.py       # Token usage tracking and cost control
│   ├── scheduler.py         # Scheduled jobs: weekly report, nudge, alerts
│   ├── config.py            # Configuration from environment
│   ├── database.py          # SQLite init, migrations, FTS5
│   ├── mcp_tools/           # MCP-style pluggable tool registry
│   │   ├── registry.py      # Auto-discover + dispatch
│   │   ├── expense_tools.py # Record, delete, export (3 tools)
│   │   ├── query_tools.py   # Query, budget, analysis (6 tools)
│   │   ├── event_tools.py   # Event/trip management (3 tools)
│   │   └── memory_tools.py  # Memory management (3 tools)
│   ├── models/
│   │   └── expense.py       # Data models
│   └── services/
│       ├── expense_service.py   # Expense CRUD + CSV export
│       └── stats_service.py     # Statistics and query logic
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## Quick Start

### Option A: Direct

```bash
git clone https://github.com/jinxiangGAN/family-finance-bot.git
cd family-finance-bot
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your tokens
python -m app.main
```

### Option B: Docker

```bash
git clone https://github.com/jinxiangGAN/family-finance-bot.git
cd family-finance-bot
cp .env.example .env
# Edit .env with your tokens
docker-compose up -d
```

## Configuration

### LLM Provider Examples

**MiniMax** (default):
```env
LLM_PROVIDER=minimax
LLM_API_KEY=your_minimax_key
LLM_MODEL=abab6.5s-chat
```

**OpenAI**:
```env
LLM_PROVIDER=openai
LLM_API_KEY=sk-xxx
LLM_MODEL=gpt-4o-mini
LLM_VISION_MODEL=gpt-4o
```

**DeepSeek**:
```env
LLM_PROVIDER=deepseek
LLM_API_KEY=your_deepseek_key
LLM_MODEL=deepseek-chat
```

**Qwen (Alibaba)**:
```env
LLM_PROVIDER=qwen
LLM_API_KEY=your_qwen_key
LLM_MODEL=qwen-plus
LLM_VISION_MODEL=qwen-vl-plus
```

**Custom (any OpenAI-compatible)**:
```env
LLM_PROVIDER=custom
LLM_API_KEY=your_key
LLM_BASE_URL=https://your-endpoint.com/v1
LLM_MODEL=your-model
```

### Full Configuration Reference

| Variable | Required | Default | Description |
|:--|:--|:--|:--|
| `TELEGRAM_BOT_TOKEN` | Yes | — | Telegram bot token from BotFather |
| `LLM_PROVIDER` | No | `minimax` | LLM provider: openai/minimax/deepseek/qwen/custom |
| `LLM_API_KEY` | No | — | LLM API key (falls back to regex without it) |
| `LLM_MODEL` | No | `abab6.5s-chat` | Model name for text processing |
| `LLM_VISION_MODEL` | No | same as LLM_MODEL | Model for receipt OCR |
| `LLM_BASE_URL` | No | auto | Custom API endpoint |
| `LLM_MONTHLY_TOKEN_LIMIT` | No | `500000` | Monthly token cap (0 = unlimited) |
| `DATABASE_PATH` | No | `data/expenses.db` | SQLite file path |
| `ALLOWED_USER_IDS` | No | — | Comma-separated Telegram user IDs |
| `FAMILY_MEMBERS` | No | — | `uid:name` pairs, comma-separated |
| `TIMEZONE` | No | `Asia/Singapore` | Timezone for date calculations |
| `CURRENCY` | No | `SGD` | Default currency |
| `WEEKLY_SUMMARY_DAY` | No | `6` (Sunday) | Day for weekly report |
| `WEEKLY_SUMMARY_HOUR` | No | `20` | Hour for weekly report |

## Usage Examples

### Basic Expense Tracking

| Message | Result |
|:--|:--|
| `午饭 35` | Records 35 SGD under Food |
| `taxi 18` | Records 18 SGD under Transport |
| `lunch 50 CNY` | Records 50 CNY → auto-converts to SGD |

### Receipt OCR

Send a photo of any receipt, taxi screenshot, or food delivery bill. The bot will:
1. Use the vision model to extract items, amounts, and currency
2. Auto-categorize and record each expense
3. Reply with a summary of what was recorded

### Multi-Currency

| Message | What happens |
|:--|:--|
| `午饭 50 人民币` | Records 50 CNY, converts to ~9.50 SGD |
| `hotel 120 AUD` | Records 120 AUD, converts to ~105.60 SGD |
| `新干线 15000 日元` | Records 15000 JPY, converts to ~135 SGD |

### Semantic Memory

```
User: 这个月要减少打车开支
Bot:  好的，我记住了。你的目标是这个月减少打车开支，我会帮你留意的！

User: 打车 30
Bot:  ✅ 已记录：交通 30.00 SGD（打车）
      💡 提醒一下，你之前说过这个月要减少打车。
      本月打车已经花了 180 SGD，注意控制哦。
```

### Private Chat vs Group Chat

```
[Private Chat with Wife]
Bot: 老婆，这周餐饮预算还有富裕，周末想出去吃点好的吗？🍽️

[Family Group Chat]
Bot: 📊 家庭本月支出：2,450.00 SGD
     餐饮 980 | 交通 520 | 生活 450 | 购物 300 | 其他 200
```

### Event/Trip Tags

```
User: 开始日本旅行
Bot:  ✅ 已开启事件标签「日本旅行」，后续记账将自动标记

User: 拉面 1500 日元
Bot:  ✅ 已记录 餐饮 1500.00 JPY (拉面) → 13.50 SGD [日本旅行]

User: 结束旅行
Bot:  ✅ 已关闭事件标签「日本旅行」

User: 日本旅行汇总
Bot:  📊 日本旅行
      👤 Husband: 450.00 SGD
      👫 Wife: 380.00 SGD
      💰 Total: 830.00 SGD
      📐 AA each: 415.00 SGD
```

### CSV Export

| Command | What it does |
|:--|:--|
| `/export` | Export your own expenses as CSV |
| `/export family` | Export all family expenses as CSV |

### Bot Commands

| Command | Description |
|:--|:--|
| `/start` | Welcome message |
| `/help` | Detailed usage guide |
| `/delete` | Delete most recent expense |
| `/export` | Export CSV file |
| `/usage` | Check LLM API token usage |
| `/memory` | View stored memories |

### Proactive Scheduled Messages

| Time | What happens |
|:--|:--|
| Friday 6PM | Budget-aware weekend check-in with personalized suggestions |
| Daily 9PM | Alert if any budget exceeds 80% |
| Sunday 8PM | Comprehensive weekly financial report with memory insights |

## Adding New Tools (MCP Pattern)

Create a new file in `app/mcp_tools/`, e.g. `calendar_tools.py`:

```python
"""MCP Tool: Calendar reminders."""

def _handle_set_reminder(user_id, user_name, params):
    # your implementation
    return {"success": True, "message": "Reminder set!"}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "set_reminder",
            "description": "Set a financial reminder (e.g., rent due date)",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Reminder text"},
                    "date": {"type": "string", "description": "Date (YYYY-MM-DD)"},
                },
                "required": ["text", "date"],
            },
        },
    },
]

HANDLERS = {
    "set_reminder": _handle_set_reminder,
}
```

The tool is automatically discovered and available to the LLM agent — no other code changes needed.

## Database Schema

### expenses
| Column | Type | Description |
|:--|:--|:--|
| id | INTEGER | Primary key |
| user_id | INTEGER | Telegram user ID |
| user_name | TEXT | Display name |
| category | TEXT | Expense category |
| amount | REAL | Original amount |
| currency | TEXT | Original currency code |
| amount_sgd | REAL | Converted SGD amount |
| note | TEXT | Description |
| event_tag | TEXT | Event/trip tag |
| created_at | TIMESTAMP | Creation time |

### budgets
| Column | Type | Description |
|:--|:--|:--|
| user_id | INTEGER | Telegram user ID |
| category | TEXT | Category or '_total' |
| monthly_limit | REAL | Monthly budget limit |

### events
| Column | Type | Description |
|:--|:--|:--|
| user_id | INTEGER | Telegram user ID |
| tag | TEXT | Event tag name |
| is_active | INTEGER | Currently active (1/0) |

### memories
| Column | Type | Description |
|:--|:--|:--|
| id | INTEGER | Primary key |
| user_id | INTEGER | Owner (0 = family-shared) |
| content | TEXT | Memory text |
| category | TEXT | preference/goal/decision/habit/reminder/general |
| importance | INTEGER | 1-10 scale |
| created_at | TIMESTAMP | When it was stored |

> FTS5 virtual table `memories_fts` provides full-text search over memory content.

### api_usage
| Column | Type | Description |
|:--|:--|:--|
| user_id | INTEGER | Telegram user ID |
| prompt_tokens | INTEGER | Prompt tokens used |
| completion_tokens | INTEGER | Completion tokens used |
| total_tokens | INTEGER | Total tokens |
| model | TEXT | Model name |
| created_at | TIMESTAMP | Timestamp |

## Deployment

### tmux
```bash
tmux new -s bot
python -m app.main
# Ctrl+B then D to detach
```

### systemd
```bash
sudo tee /etc/systemd/system/finance-bot.service << EOF
[Unit]
Description=Family Finance Telegram Bot
After=network.target
[Service]
Type=simple
User=ubuntu
WorkingDirectory=/path/to/family-finance-bot
ExecStart=/path/to/python -m app.main
Restart=always
RestartSec=10
[Install]
WantedBy=multi-user.target
EOF
sudo systemctl enable --now finance-bot
```

### Docker
```bash
docker-compose up -d

# View logs
docker-compose logs -f

# Restart
docker-compose restart

# Stop
docker-compose down
```

## License

MIT
