"""
Configuration module for loading settings from .env file
"""
import os
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

# Binance API settings
# Note: For WebSocket orderbook streams API keys are not required (public data)
# They are only needed for REST API or private streams
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET', '')

# Telegram settings
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')

# Imbalance Ratio threshold
IMBALANCE_THRESHOLD = float(os.getenv('IMBALANCE_THRESHOLD', '0.5'))

# List of symbols to monitor
SYMBOLS = ['BTCUSDT', 'DOTUSDT', 'SOLUSDT']

# Number of top bids and asks for calculation
TOP_ORDERS_COUNT = 10

