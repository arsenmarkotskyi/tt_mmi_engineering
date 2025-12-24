"""
Module for sending notifications via Telegram bot
"""
import asyncio
import datetime
import logging
import time
from typing import Dict, Optional
from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Class for sending Telegram notifications"""
    
    def __init__(self, bot_token: str, chat_id: str, threshold: float = 0.5):
        """
        Initialize Telegram notifier
        
        Args:
            bot_token: Telegram bot token
            chat_id: Chat ID for sending messages
            threshold: Alert threshold
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.threshold = threshold
        self.bot: Optional[Bot] = None
        self.last_notification_time: Dict[str, float] = {}
        self.last_notification_value: Dict[str, float] = {}  # Store last value
        self.notification_cooldown = 10  # Spam protection: 10 seconds between messages for one symbol
        
    def _initialize_bot(self):
        """Initialize Telegram bot"""
        if not self.bot:
            try:
                self.bot = Bot(token=self.bot_token)
                logger.info("Telegram bot initialized")
            except Exception as e:
                logger.error(f"Error initializing Telegram bot: {e}")
                raise
    
    def _format_message(self, symbol: str, imbalance_ratio: float, threshold: float) -> str:
        """
        Format message for Telegram
        
        Args:
            symbol: Symbol ticker
            imbalance_ratio: Imbalance Ratio value
            threshold: Alert threshold
            
        Returns:
            Formatted message
        """
        # Format symbol for display (BTCUSDT -> BTC/USDT)
        display_symbol = symbol.replace('USDT', '/USDT')
        
        # Determine imbalance direction
        if imbalance_ratio > 0:
            direction = "🟢 Buyers advantage"
        else:
            direction = "🔴 Sellers advantage"
        
        # Event time
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        
        message = (
            f"⚠️ Imbalance Alert\n\n"
            f"Symbol: {display_symbol}\n"
            f"Imbalance Ratio: {imbalance_ratio:.4f}\n"
            f"Direction: {direction}\n"
            f"Threshold: |{imbalance_ratio:.4f}| > {abs(threshold):.4f}\n"
            f"Time: {current_time}"
        )
        
        return message
    
    async def _send_message_async(self, message: str) -> bool:
        """
        Async message sending
        
        Args:
            message: Message text
            
        Returns:
            True if message sent successfully, False otherwise
        """
        try:
            self._initialize_bot()
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message
            )
            return True
        except TelegramError as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending message: {e}")
            return False
    
    def send_notification(self, symbol: str, imbalance_ratio: float) -> bool:
        """
        Send notification about threshold exceedance
        
        Args:
            symbol: Symbol ticker
            imbalance_ratio: Imbalance Ratio value
            
        Returns:
            True if notification sent, False otherwise
        """
        # Spam protection check
        current_time = time.time()
        last_time = self.last_notification_time.get(symbol, 0)
        last_value = self.last_notification_value.get(symbol)
        
        # Cooldown check
        if current_time - last_time < self.notification_cooldown:
            return False
        
        # Check if value changed (to avoid spamming same values)
        # Use smaller threshold for telegram_notifier, since main.py already checked
        if last_value is not None:
            value_diff = abs(imbalance_ratio - last_value)
            if value_diff < 0.0005:  # Reduced threshold to 0.0005 for higher sensitivity
                return False
        
        # Format and send message
        message = self._format_message(symbol, imbalance_ratio, self.threshold)
        
        # Use asyncio for sending
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        success = loop.run_until_complete(self._send_message_async(message))
        
        if success:
            self.last_notification_time[symbol] = current_time
            self.last_notification_value[symbol] = imbalance_ratio
            logger.info(
                f"Notification sent for {symbol}: "
                f"Imbalance Ratio = {imbalance_ratio:.4f} (threshold: {self.threshold:.4f})"
            )
        
        return success

