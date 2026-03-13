# Family Finance Telegram Bot

A smart Telegram bot for family expense tracking, powered by an LLM agent (MiniMax API) with function calling. Designed for a 2-person household to record, query, and analyze daily spending through natural language.

## Features

- **Natural Language Expense Tracking** — Send messages like `lunch 35` or `taxi 18` to record expenses instantly
- **LLM Agent with Function Calling** — MiniMax API understands intent and dispatches the right skill automatically
- **Three Query Views** — Check spending for yourself, your spouse, or the whole family
- **Budget Management** — Set monthly budgets per category with automatic overspend alerts
- **Weekly Summary** — Automated weekly report pushed to all family members
- **Financial Analysis & Advice** — Ask the bot for spending insights and saving tips
- **API Cost Control** — Monthly token limit with automatic fallback to regex parsing when exceeded
- **Regex Fallback** — Works without LLM API using pattern matching for basic operations

## Architecture

```
User Message
     ↓
Telegram Bot (polling mode)
     ↓
LLM Agent (MiniMax function calling / regex fallback)
     ↓
Skills (record_expense, query_summary, set_budget, ...)
     ↓
SQLite Database (expenses, budgets, api_usage)
```

## Project Structure

```
family-finance-bot/
├── app/
│   ├── main.py              # Entry point
│   ├── telegram_bot.py      # Bot handlers, commands, scheduler
│   ├── agent.py             # LLM agent with function calling + regex fallback
│   ├── skills.py            # All DB operations as callable skill functions
│   ├── api_tracker.py       # API token usage tracking and cost control
│   ├── scheduler.py         # Weekly summary job
│   ├── config.py            # Environment variable configuration
│   ├── database.py          # SQLite initialization and connection
│   ├── models/
│   │   └── expense.py       # Data models
│   └── services/
│       ├── expense_service.py   # Expense CRUD operations
│       └── stats_service.py     # Statistics and query logic
├── requirements.txt
├── .env.example
└── README.md
```

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/jinxiangGAN/family-finance-bot.git
cd family-finance-bot
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in your credentials:

```env
# Required
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Optional (falls back to regex parsing if not set)
MINIMAX_API_KEY=your_api_key_here

# Recommended: restrict access to family members only
ALLOWED_USER_IDS=123456789,987654321

# Family member mapping
FAMILY_MEMBERS=123456789:Husband,987654321:Wife
```

### 4. Run the bot

```bash
python -m app.main
```

## How to Get a Telegram Bot Token

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the instructions
3. Copy the token and paste it into your `.env` file

## How to Get Your Telegram User ID

Send any message to **@userinfobot** on Telegram — it will reply with your user ID.

## Usage Examples

### Recording Expenses

| Message | Result |
|:--|:--|
| `lunch 35` | Records ¥35 under "餐饮" (Food) |
| `taxi 18` | Records ¥18 under "交通" (Transport) |
| `bubble tea 12` | Records ¥12 under "餐饮" (Food) |

### Querying Expenses

| Message | What it does |
|:--|:--|
| `How much did I spend this month?` | Your monthly total |
| `How much did my wife spend?` | Spouse's monthly total |
| `Total family spending?` | Combined family total |
| `How much on food?` | Your food category total |
| `Monthly summary` | Breakdown by category |
| `Family summary` | Family breakdown by category |

> **Note:** The bot understands both Chinese and English when the LLM API is active. With regex fallback, only Chinese patterns are supported.

### Budget Management

| Message | What it does |
|:--|:--|
| `Set food budget to 1000` | Set monthly budget for food |
| `Set total budget to 5000` | Set overall monthly budget |
| `How much budget left?` | Check budget status |

### Financial Advice

| Message | What it does |
|:--|:--|
| `Analyze my spending` | Get spending analysis |
| `How to save money?` | Get saving tips based on your data |
| `Help me plan my finances` | Get a financial plan |

### Bot Commands

| Command | Description |
|:--|:--|
| `/start` | Welcome message and quick guide |
| `/help` | Detailed usage instructions |
| `/delete` | Delete the most recent expense |
| `/usage` | Check MiniMax API token consumption |

## Expense Categories

| Category | Chinese |
|:--|:--|
| Food & Drink | 餐饮 |
| Transport | 交通 |
| Shopping | 购物 |
| Entertainment | 娱乐 |
| Living | 生活 |
| Medical | 医疗 |
| Other | 其他 |

## Configuration Reference

| Variable | Required | Default | Description |
|:--|:--|:--|:--|
| `TELEGRAM_BOT_TOKEN` | Yes | — | Telegram bot token from BotFather |
| `MINIMAX_API_KEY` | No | — | MiniMax API key for LLM features |
| `MINIMAX_MODEL` | No | `abab6.5s-chat` | MiniMax model name |
| `MINIMAX_MONTHLY_TOKEN_LIMIT` | No | `500000` | Monthly token cap (0 = unlimited) |
| `DATABASE_PATH` | No | `data/expenses.db` | SQLite database file path |
| `ALLOWED_USER_IDS` | No | — | Comma-separated Telegram user IDs |
| `FAMILY_MEMBERS` | No | — | `user_id:name` pairs, comma-separated |
| `TIMEZONE` | No | `Asia/Singapore` | Timezone for date calculations |
| `CURRENCY` | No | `SGD` | Default currency label |
| `WEEKLY_SUMMARY_DAY` | No | `6` (Sunday) | Day of week for weekly report |
| `WEEKLY_SUMMARY_HOUR` | No | `20` | Hour for weekly report (24h format) |

## API Cost Control

The bot tracks every MiniMax API call in the `api_usage` table. When the monthly token usage exceeds `MINIMAX_MONTHLY_TOKEN_LIMIT`, the bot automatically switches to regex-based parsing — no additional charges will occur.

- Default limit: **500,000 tokens/month** (~¥0.5 for abab6.5s-chat)
- Check usage anytime with `/usage`
- Set to `0` for unlimited

## Deployment

### Using tmux (simple)

```bash
tmux new -s bot
python -m app.main
# Press Ctrl+B then D to detach
```

### Using systemd (recommended for servers)

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

sudo systemctl daemon-reload
sudo systemctl enable finance-bot
sudo systemctl start finance-bot
```

## License

MIT
