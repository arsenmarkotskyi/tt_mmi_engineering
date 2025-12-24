"""
Module for connecting to Binance WebSocket API and receiving orderbook data
"""
import json
import logging
import requests
import threading
import time
import websocket
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class BinanceWebSocketClient:
    """Client for working with Binance WebSocket API"""
    
    REST_API_URL = "https://api.binance.com/api/v3/depth"
    
    def __init__(self, symbols: List[str], on_message_callback: Callable):
        """
        Initialize WebSocket client
        
        Args:
            symbols: List of symbols to monitor
            on_message_callback: Callback function for processing messages
        """
        self.symbols = symbols
        self.on_message_callback = on_message_callback
        self.is_running = False
        self.orderbooks: Dict[str, Dict] = {}  # Store current orderbook state
        self.last_sent_data: Dict[str, Dict] = {}  # Store last sent data for change detection
        self.last_sent_time: Dict[str, float] = {}  # Time of last data send
    
    def _get_initial_snapshot(self, symbol: str) -> Optional[Dict]:
        """Get initial orderbook snapshot via REST API"""
        try:
            params = {
                'symbol': symbol,
                'limit': 20  # Get top 20 to match WebSocket
            }
            response = requests.get(self.REST_API_URL, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            return {
                'symbol': symbol,
                'bids': data.get('bids', []),
                'asks': data.get('asks', [])
            }
        except Exception as e:
            logger.error(f"Error getting snapshot for {symbol}: {e}")
            return None
    
    def start(self):
        """Start WebSocket connection for all symbols"""
        # First get initial snapshots for all symbols
        logger.info(f"Getting initial orderbook snapshots for {len(self.symbols)} symbols...")
        self.is_running = True
        for symbol in self.symbols:
            logger.info(f"Getting snapshot for {symbol}...")
            snapshot = self._get_initial_snapshot(symbol)
            if snapshot:
                self.orderbooks[symbol] = {
                    'bids': {float(price): float(qty) for price, qty in snapshot['bids']},
                    'asks': {float(price): float(qty) for price, qty in snapshot['asks']}
                }
                # Send initial snapshot to handler
                self.on_message_callback({
                    'symbol': symbol,
                    'bids': snapshot['bids'],
                    'asks': snapshot['asks']
                })
                logger.info(f"✅ Snapshot received for {symbol}: {len(snapshot['bids'])} bids, {len(snapshot['asks'])} asks")
            else:
                logger.error(f"❌ Failed to get snapshot for {symbol}")
        
        # Use combined stream for updates
        def start_single_stream(symbol: str):
            """Start WebSocket for single symbol"""
            stream_name = f"{symbol.lower()}@depth20@100ms"
            url = f"wss://stream.binance.com:9443/ws/{stream_name}"
            
            logger.info(f"🔌 Connecting to {symbol}: {url}")
            
            def on_open_local(ws):
                logger.info(f"✅ WebSocket connected for {symbol}")
            
            def on_error_local(ws, error):
                logger.error(f"❌ WebSocket error for {symbol}: {error}")
            
            def on_close_local(ws, close_status_code, close_msg):
                logger.warning(f"⚠️ WebSocket closed for {symbol}: {close_status_code} - {close_msg}")
                # Don't auto-reconnect to avoid recursion
                # Reconnection can be added in the future via separate mechanism
            
            def on_message(ws, message):
                try:
                    data = json.loads(message)
                    # Log connection (only first time for diagnostics)
                    if not hasattr(on_message, '_log_count'):
                        on_message._log_count = {}
                    if symbol not in on_message._log_count:
                        logger.info(f"✅ Connected to WebSocket for {symbol}")
                        on_message._log_count[symbol] = 0
                    
                    # Update local orderbook
                    self._update_orderbook(symbol, data)
                    
                    # Send updated data to handler only if data exists
                    if symbol in self.orderbooks and len(self.orderbooks[symbol]['bids']) > 0:
                        orderbook = self.orderbooks[symbol]
                        # Get top 20 bids and asks
                        top_bids = sorted(orderbook['bids'].items(), reverse=True)[:20]
                        top_asks = sorted(orderbook['asks'].items())[:20]
                        
                        if top_bids and top_asks:
                            # Format data for sending
                            current_data = {
                                'symbol': symbol,
                                'bids': [[str(p), str(q)] for p, q in top_bids],
                                'asks': [[str(p), str(q)] for p, q in top_asks]
                            }
                            
                            current_time = time.time()
                            last_time = self.last_sent_time.get(symbol, 0)
                            time_since_last = current_time - last_time
                            
                            # Strategy: send data if:
                            # 1. First time for symbol
                            # 2. 5+ seconds passed (reasonable interval for monitoring)
                            # 3. Or data actually changed (compare top 10)
                            should_send = False
                            
                            if symbol not in self.last_sent_data:
                                # First time - always send
                                should_send = True
                            else:
                                # Check if data changed (compare top 10)
                                last_data = self.last_sent_data.get(symbol)
                                if last_data:
                                    # Compare top 10 bids and asks
                                    last_top_bids = last_data.get('bids', [])[:10]
                                    last_top_asks = last_data.get('asks', [])[:10]
                                    current_top_bids = current_data['bids'][:10]
                                    current_top_asks = current_data['asks'][:10]
                                    
                                    # Check if data changed
                                    if last_top_bids != current_top_bids or last_top_asks != current_top_asks:
                                        should_send = True
                                
                                # If data didn't change but 5+ seconds passed - send for freshness
                                if not should_send and time_since_last >= 5.0:
                                    should_send = True
                            
                            # Send if needed
                            if should_send:
                                self.last_sent_data[symbol] = current_data.copy()
                                self.last_sent_time[symbol] = current_time
                                self.on_message_callback(current_data)
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error for {symbol}: {e}")
                except Exception as e:
                    logger.error(f"Error processing message for {symbol}: {e}", exc_info=True)
            
            ws = websocket.WebSocketApp(
                url,
                on_message=on_message,
                on_error=on_error_local,
                on_close=on_close_local,
                on_open=on_open_local
            )
            
            ws.run_forever()
        
        # Start separate thread for each symbol
        # Use daemon threads - they automatically terminate when main thread ends
        logger.info("🚀 Starting WebSocket streams...")
        for symbol in self.symbols:
            thread = threading.Thread(target=start_single_stream, args=(symbol,), daemon=True)
            thread.start()
            logger.info(f"✅ Stream started for {symbol}")
            # Don't call join() - threads run in background
            # Main thread continues execution
        
        logger.info("✅ All WebSocket streams started, main thread continues execution")
    
    def _update_orderbook(self, symbol: str, update_data: Dict):
        """Update local orderbook based on delta updates"""
        if symbol not in self.orderbooks:
            self.orderbooks[symbol] = {'bids': {}, 'asks': {}}
        
        orderbook = self.orderbooks[symbol]
        
        # Check data format
        # Binance WebSocket depth20@100ms sends data in format:
        # {"lastUpdateId":123456789,"bids":[[price,qty],...],"asks":[[price,qty],...]}
        # This is NOT standard depthUpdate format, but snapshot-like format
        bids_data = update_data.get('bids', update_data.get('b', []))
        asks_data = update_data.get('asks', update_data.get('a', []))
        
        # Minimal logging - only if empty update (error)
        if len(bids_data) == 0 and len(asks_data) == 0:
            if not hasattr(self, '_empty_update_warned'):
                self._empty_update_warned = set()
            if symbol not in self._empty_update_warned:
                logger.warning(
                    f"⚠️ {symbol}: empty delta update! "
                    f"Keys in data: {list(update_data.keys())}"
                )
                self._empty_update_warned.add(symbol)
        
        # Update bids
        for price, qty in bids_data:
            try:
                price_f = float(price)
                qty_f = float(qty)
                if qty_f == 0:
                    # Remove order
                    orderbook['bids'].pop(price_f, None)
                else:
                    # Add or update order
                    orderbook['bids'][price_f] = qty_f
            except (ValueError, TypeError) as e:
                logger.error(f"Error processing bid for {symbol}: price={price}, qty={qty}, error={e}")
        
        # Update asks
        for price, qty in asks_data:
            try:
                price_f = float(price)
                qty_f = float(qty)
                if qty_f == 0:
                    # Remove order
                    orderbook['asks'].pop(price_f, None)
                else:
                    # Add or update order
                    orderbook['asks'][price_f] = qty_f
            except (ValueError, TypeError) as e:
                logger.error(f"Error processing ask for {symbol}: price={price}, qty={qty}, error={e}")
    
    def stop(self):
        """Stop WebSocket connection"""
        self.is_running = False
        logger.info("WebSocket connection stopped")


def parse_orderbook_data(data: Dict) -> Optional[Dict]:
    """
    Parse orderbook data (data is already processed in BinanceWebSocketClient)
    
    Args:
        data: Data from WebSocket (already processed)
        
    Returns:
        Dictionary with symbol, bids and asks, or None if error
    """
    try:
        symbol = data.get('symbol')
        bids = data.get('bids', [])
        asks = data.get('asks', [])
        
        if not symbol or not bids or not asks:
            return None
        
        return {
            'symbol': symbol,
            'bids': bids,
            'asks': asks
        }
    except Exception as e:
        logger.error(f"Error parsing orderbook data: {e}")
        return None

