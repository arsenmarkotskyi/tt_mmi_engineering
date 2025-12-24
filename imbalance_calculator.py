"""
Module for calculating Imbalance Ratio based on orderbook data
"""
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def calculate_imbalance_ratio(
    bids: List[List[str]], 
    asks: List[List[str]], 
    top_n: int = 10
) -> Optional[float]:
    """
    Calculate Imbalance Ratio based on top N bids and asks
    
    Args:
        bids: List of bids in format [[price, quantity], ...]
        asks: List of asks in format [[price, quantity], ...]
        top_n: Number of top orders for calculation (default 10)
        
    Returns:
        Imbalance Ratio or None if error
    """
    try:
        # Get top N bids and asks
        top_bids = bids[:top_n] if len(bids) >= top_n else bids
        top_asks = asks[:top_n] if len(asks) >= top_n else asks
        
        # Calculate total volume for bids
        bid_volume = sum(float(price) * float(quantity) for price, quantity in top_bids)
        
        # Calculate total volume for asks
        ask_volume = sum(float(price) * float(quantity) for price, quantity in top_asks)
        
        # Check for division by zero
        total_volume = bid_volume + ask_volume
        if total_volume == 0:
            logger.warning("Total volume is zero, cannot calculate Imbalance Ratio")
            return None
        
        # Calculate Imbalance Ratio
        imbalance_ratio = (bid_volume - ask_volume) / total_volume
        
        return imbalance_ratio
        
    except (ValueError, TypeError, IndexError) as e:
        logger.error(f"Error calculating Imbalance Ratio: {e}")
        return None


def process_orderbook(orderbook_data: Dict, top_n: int = 10) -> Optional[Dict]:
    """
    Process orderbook data and calculate Imbalance Ratio
    
    Args:
        orderbook_data: Orderbook data with symbol, bids and asks
        top_n: Number of top orders for calculation
        
    Returns:
        Dictionary with symbol and Imbalance Ratio, or None if error
    """
    try:
        symbol = orderbook_data.get('symbol')
        bids = orderbook_data.get('bids', [])
        asks = orderbook_data.get('asks', [])
        
        if not symbol or not bids or not asks:
            logger.warning(f"Insufficient data for processing: symbol={symbol}")
            return None
        
        imbalance_ratio = calculate_imbalance_ratio(bids, asks, top_n)
        
        if imbalance_ratio is None:
            return None
        
        return {
            'symbol': symbol,
            'imbalance_ratio': imbalance_ratio,
            'bids_count': len(bids),
            'asks_count': len(asks)
        }
        
    except Exception as e:
        logger.error(f"Error processing orderbook: {e}")
        return None

