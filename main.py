"""
Main module for integrating all components of the Imbalance Ratio monitoring system
"""
import logging
import signal
import sys
import time
from typing import Dict, Optional

from config import (
    SYMBOLS,
    IMBALANCE_THRESHOLD,
    TOP_ORDERS_COUNT,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID
)
from binance_client import BinanceWebSocketClient, parse_orderbook_data
from imbalance_calculator import process_orderbook
from telegram_notifier import TelegramNotifier

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('imbalance_monitor.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class ImbalanceMonitor:
    """Main class for monitoring Imbalance Ratio"""
    
    def __init__(self):
        """Initialize monitor"""
        self.telegram_notifier = TelegramNotifier(
            TELEGRAM_BOT_TOKEN, 
            TELEGRAM_CHAT_ID,
            IMBALANCE_THRESHOLD
        )
        self.binance_client: Optional[BinanceWebSocketClient] = None
        self.is_running = False
        self.last_imbalance_ratios: Dict[str, float] = {}  # Store last values
        self.last_notification_time: Dict[str, float] = {}  # Time of last notification
        self.periodic_notification_interval = 30.0  # Interval for periodic notifications (seconds)
        
        # Validate configuration
        self._validate_config()
    
    def _validate_config(self):
        """Validate configuration correctness"""
        if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == 'your_telegram_bot_token':
            logger.warning("TELEGRAM_BOT_TOKEN not configured in .env file")
        
        if not TELEGRAM_CHAT_ID or TELEGRAM_CHAT_ID == 'your_chat_id':
            logger.warning("TELEGRAM_CHAT_ID not configured in .env file")
        
        if not SYMBOLS:
            logger.error("Symbol list is empty")
            raise ValueError("At least one symbol must be specified")
        
        logger.info(f"Configuration loaded: threshold={IMBALANCE_THRESHOLD}, symbols={SYMBOLS}")
    
    def _handle_orderbook_update(self, data: Dict):
        """
        Handle orderbook update
        
        Args:
            data: Data from WebSocket
        """
        try:
            # Parse orderbook data
            orderbook_data = parse_orderbook_data(data)
            
            if not orderbook_data:
                return
            
            # Process and calculate Imbalance Ratio
            result = process_orderbook(orderbook_data, TOP_ORDERS_COUNT)
            
            if not result:
                return
            
            symbol = result.get('symbol')
            imbalance_ratio = result.get('imbalance_ratio')
            
            # Check for None or invalid values
            if not symbol or imbalance_ratio is None:
                return
            
            # Check if value changed (with minimum threshold for sensitivity)
            # Use threshold 0.0001 (0.01%) to detect even small changes
            last_ratio = self.last_imbalance_ratios.get(symbol)
            if last_ratio is None:
                ratio_changed = True
            else:
                try:
                    current_ratio = float(imbalance_ratio)
                    last_ratio_val = float(last_ratio)
                    diff = abs(current_ratio - last_ratio_val)
                    ratio_changed = diff > 0.0001
                except (TypeError, ValueError):
                    ratio_changed = True
            
            # Check notification condition
            try:
                imbalance_ratio_val = float(imbalance_ratio)
                threshold_val = abs(float(IMBALANCE_THRESHOLD))
                exceeds_threshold = abs(imbalance_ratio_val) > threshold_val
            except (TypeError, ValueError):
                return
            
            if exceeds_threshold:
                current_time = time.time()
                last_notif_time = self.last_notification_time.get(symbol, 0)
                time_since_last = current_time - last_notif_time
                
                # Send notification if:
                # 1. Value changed (ratio_changed), OR
                # 2. Enough time passed since last notification (periodic_notification_interval)
                should_send = ratio_changed or time_since_last >= self.periodic_notification_interval
                
                if should_send:
                    # Send notification to Telegram
                    notification_sent = self.telegram_notifier.send_notification(symbol, imbalance_ratio_val)
                    
                    if notification_sent:
                        # Update last notification time and value ONLY after successful send
                        self.last_notification_time[symbol] = current_time
                        self.last_imbalance_ratios[symbol] = imbalance_ratio_val
                        # Format change information for log
                        if last_ratio is not None:
                            last_ratio_val = float(last_ratio)
                            change_info = f"{last_ratio_val:.4f} → {imbalance_ratio_val:.4f}"
                        else:
                            change_info = f"N/A → {imbalance_ratio_val:.4f}"
                        logger.info(
                            f"✅ Notification sent for {symbol}: "
                            f"|{imbalance_ratio_val:.4f}| > {threshold_val:.4f} "
                            f"(change: {change_info})"
                        )
                else:
                    # Value didn't change and not enough time passed
                    # DON'T update last_imbalance_ratios - keep old value for proper change detection
                    pass
            else:
                # Doesn't exceed threshold - update value for change tracking
                # This allows detecting when value exceeds threshold again
                self.last_imbalance_ratios[symbol] = imbalance_ratio_val
                
        except Exception as e:
            logger.error("Error processing orderbook update: " + str(e), exc_info=True)
    
    def start(self):
        """Start monitoring"""
        logger.info("Starting Imbalance Ratio monitoring...")
        
        try:
            # Create and start Binance WebSocket client
            self.binance_client = BinanceWebSocketClient(
                symbols=SYMBOLS,
                on_message_callback=self._handle_orderbook_update
            )
            
            self.is_running = True
            
            # Start WebSocket (blocking call)
            self.binance_client.start()
            
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, stopping monitoring...")
            self.stop()
        except Exception as e:
            logger.error(f"Critical error: {e}", exc_info=True)
            self.stop()
            sys.exit(1)
    
    def stop(self):
        """Stop monitoring"""
        logger.info("Stopping monitoring...")
        self.is_running = False
        
        if self.binance_client:
            self.binance_client.stop()
        
        logger.info("Monitoring stopped")


def signal_handler(sig, frame):
    """Signal handler for graceful shutdown"""
    logger.info("Received shutdown signal")
    sys.exit(0)


def main():
    """Main function"""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and start monitor
    monitor = ImbalanceMonitor()
    monitor.start()
    
    # Main thread must run indefinitely
    # so daemon threads don't terminate
    logger.info("✅ Monitor started, waiting for updates...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
        monitor.stop()
        sys.exit(0)


if __name__ == "__main__":
    main()

