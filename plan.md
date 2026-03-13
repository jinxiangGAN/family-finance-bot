You are a senior Python backend engineer.

Generate a complete production-ready project.

Project name:
family-finance-telegram-bot

Goal:
Build a Telegram bot that allows a small family (2 people) to track expenses using natural language.

Users send messages like:

午饭 35
奶茶 20
打车 18

The bot parses the message using MiniMax API and saves the expense to a SQLite database.

The bot should also support queries such as:

本月花了多少
餐饮花了多少

------------------------------------------------

Tech Stack

Python 3.10+

FastAPI

python-telegram-bot

SQLite

MiniMax API

dotenv for configuration

------------------------------------------------

Architecture

Telegram User
     ↓
Telegram Bot
     ↓
FastAPI backend
     ↓
Expense Parser (MiniMax)
     ↓
Expense Service
     ↓
SQLite database

------------------------------------------------

Project Structure

family-finance-bot/

app/
main.py
telegram_bot.py
parser.py
database.py
config.py

services/
expense_service.py
stats_service.py

models/
expense.py

requirements.txt
.env.example
README.md

------------------------------------------------

Database Schema

SQLite table: expenses

columns:

id INTEGER PRIMARY KEY AUTOINCREMENT
user TEXT
category TEXT
amount REAL
note TEXT
date TEXT

------------------------------------------------

Expense Categories

餐饮
交通
购物
娱乐
生活
医疗
其他

------------------------------------------------

MiniMax Parsing

Implement function:

parse_expense(text: str) -> dict

Use MiniMax API to convert text into JSON.

Expected output:

{
"category": "餐饮",
"amount": 35,
"note": "午饭"
}

Prompt template used for LLM:

"You are a family finance assistant.
Convert the input text into JSON with category, amount and note."

------------------------------------------------

Telegram Bot Features

Handle normal text messages.

Flow:

1 receive message
2 parse expense using MiniMax
3 store in database
4 reply confirmation

Example reply:

已记录
餐饮 35 元

------------------------------------------------

Query Features

User messages:

本月花了多少

Response:

本月总支出：3820 元


User message:

餐饮花了多少

Response:

本月餐饮支出：1200 元

------------------------------------------------

Functions to implement

parse_expense(text)

save_expense(user, expense)

get_month_total()

get_category_total(category)

------------------------------------------------

Environment Variables

Create .env.example

TELEGRAM_BOT_TOKEN=
MINIMAX_API_KEY=

------------------------------------------------

Requirements.txt

Include all dependencies.

------------------------------------------------

README.md

Include:

project description

setup instructions

how to run the bot

example commands

------------------------------------------------

Quality Requirements

Code must be clean and modular.

Use Python type hints.

Handle parsing errors gracefully.

Project must run with:

pip install -r requirements.txt

python app/main.py

------------------------------------------------

Optional (nice to have)

Dockerfile

monthly summary command

------------------------------------------------

Output the full project with all files.