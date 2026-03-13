# Family Finance Telegram Bot

A smart Telegram bot for family expense tracking, powered by an LLM agent with function calling. Designed for a 2-person household to record, query, and analyze daily spending through natural language.

## Features

- **Natural Language Expense Tracking** — Send `lunch 35` or `taxi 18` to record instantly
- **Receipt OCR** — Send a photo of a receipt and the bot auto-extracts expenses via vision model
- **Multi-Currency** — Record in SGD, CNY, USD, AUD, JPY, etc. with automatic conversion
- **Three Query Views** — Check spending for yourself, your spouse, or the whole family
- **Budget Management** — Set monthly budgets per category with automatic overspend alerts
- **Event/Trip Tags** — Tag expenses for trips (e.g., "Japan Trip") with AA split summary
- **Weekly Summary** — Automated weekly report pushed to all family members
- **Financial Analysis & Advice** — Ask the bot for spending insights and saving tips
- **CSV Export** — `/export` to download expense data as CSV file
- **Multi-Provider LLM** — Switch between MiniMax, OpenAI, DeepSeek, Qwen, or any OpenAI-compatible API
- **API Cost Control** — Monthly token limit with automatic fallback to regex parsing
- **Docker Ready** — One-command deployment with docker-compose

## Architecture

```
User Message (text / photo)
     ↓
Telegram Bot (polling mode)
     ↓
LLM Agent (function calling / regex fallback)
  ├── Text → tool dispatch
  └── Photo → Vision OCR → tool dispatch
     ↓
Skills Layer (record, query, budget, event, export, ...)
     ↓
SQLite Database (expenses, budgets, events, api_usage)
```

## Project Structure

```
family-finance-bot/
├── app/
│   ├── main.py              # Entry point
│   ├── telegram_bot.py      # Bot handlers, commands, photo handler
│   ├── agent.py             # LLM agent: text + image handling
│   ├── llm_provider.py      # Abstract LLM interface (OpenAI-compatible)
│   ├── skills.py            # All operations as callable skill functions
│   ├── api_tracker.py       # Token usage tracking and cost control
│   ├── scheduler.py         # Weekly summary job
│   ├── config.py            # Configuration from environment
│   ├── database.py          # SQLite initialization and migrations
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
