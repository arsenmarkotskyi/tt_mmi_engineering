# Imbalance Ratio Monitor

## Тестове завдання

### Вимоги:

1. **Підключення до Binance**
   - Підключитись до Binance для отримання реального часу даних з ордербука
   - Тікери: `BTC/USDT`, `DOT/USDT`, `SOL/USDT`

2. **Розрахунок Imbalance Ratio**
   - Розрахувати співвідношення обсягів на стороні покупців та продавців
   - Використовувати 10 кращих бід та 10 кращих аск
   - Формула:
     ```
     Imbalance Ratio = (Bid Volume - Ask Volume) / (Bid Volume + Ask Volume)
     ```

3. **Telegram оповіщення**
   - Налаштувати оповіщення в Telegram за допомогою Telegram бота
   - Умова оповіщення: `Imbalance Ratio > X`
   - Значення `X` має задаватись у конфігурації

link for bot: @my_imbalance_monitor_bot

## Overview

This project monitors the Imbalance Ratio for selected cryptocurrency pairs on Binance and sends Telegram notifications when the ratio exceeds a configured threshold. The system uses WebSocket connections for real-time data updates and calculates the imbalance based on top 10 bids and asks.

## Features

- ✅ Real-time orderbook monitoring via Binance WebSocket API
- ✅ Imbalance Ratio calculation for multiple symbols
- ✅ Telegram notifications when threshold is exceeded
- ✅ Configurable threshold and symbols
- ✅ Spam protection with cooldown mechanism
- ✅ Automatic reconnection handling
- ✅ Comprehensive logging

## Requirements

- Python 3.8+
- Binance account (API keys optional for public streams)
- Telegram bot token and chat ID

## Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd tt_mmi_engineering
```

2. Create and activate virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

1. Copy the example environment file:

```bash
cp .env.example .env
```

2. Edit `.env` file and fill in your credentials:

```env
# Binance API (optional for public WebSocket streams)
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Imbalance Ratio Threshold (default: 0.5)
IMBALANCE_THRESHOLD=0.5
```

3. Get Telegram Bot Token:
   - Open [@BotFather](https://t.me/botfather) on Telegram
   - Send `/newbot` and follow instructions
   - Copy the bot token to `.env` file

4. Get Telegram Chat ID:
   - Open [@userinfobot](https://t.me/userinfobot) on Telegram
   - Send any message and copy your chat ID
   - Or use [@getidsbot](https://t.me/getidsbot) for group chats

## Usage

### Run the monitor:

```bash
python main.py
```

### Run in background:

```bash
# Using nohup
nohup python main.py > output.log 2>&1 &

# Or use the provided script
./start.sh
```

### Check status:

```bash
./check_status.sh
```

## Project Structure

```
tt_mmi_engineering/
├── main.py                 # Main entry point
├── binance_client.py       # Binance WebSocket client
├── imbalance_calculator.py # Imbalance Ratio calculation
├── telegram_notifier.py    # Telegram notification handler
├── config.py              # Configuration loader
├── requirements.txt       # Python dependencies
├── .env                  # Environment variables (create this)
├── README.md             # This file
└── imbalance_monitor.log # Application logs
```