from .utils import ema, atr
from enums.trade import TradeSide
from .memory import memory


# EMA Crossover + ATR Filter (using mid price, ATR as % of price)
def signal_ema_crossover(ticker: str, timeframe="MINUTE", fast=9, slow=21, atr_period=14, atr_mult=0.005):
    bars_bid = [b for b in memory.ohlc_history.get((ticker, timeframe), []) if b["price_type"] == "bid"]
    bars_ask = [b for b in memory.ohlc_history.get((ticker, timeframe), []) if b["price_type"] == "ask"]

    # Need enough data and alignment
    if len(bars_bid) < slow + atr_period or len(bars_ask) < slow + atr_period:
        return TradeSide.NEUTRAL

    # Construct mid-price bars
    bars_mid = []
    for b_bid, b_ask in zip(bars_bid, bars_ask):
        bars_mid.append({
            "o": (b_bid["o"] + b_ask["o"]) / 2,
            "h": (b_bid["h"] + b_ask["h"]) / 2,
            "l": (b_bid["l"] + b_ask["l"]) / 2,
            "c": (b_bid["c"] + b_ask["c"]) / 2,
        })

    closes = [b["c"] for b in bars_mid]

    fast_ema = ema(closes, fast)
    slow_ema = ema(closes, slow)

    # Latest EMA values
    last_fast, prev_fast = fast_ema[-1], fast_ema[-2]
    last_slow, prev_slow = slow_ema[-1], slow_ema[-2]

    # ATR on mid-price bars
    volatility = atr(bars_mid, atr_period)
    if volatility is None:
        return TradeSide.NEUTRAL

    # ATR filter (as % of price)
    atr_ratio = volatility / closes[-1]

    # Signal generation
    if prev_fast < prev_slow and last_fast > last_slow and atr_ratio > atr_mult:
        return TradeSide.LONG
    elif prev_fast > prev_slow and last_fast < last_slow and atr_ratio > atr_mult:
        return TradeSide.SHORT

    return TradeSide.NEUTRAL




# Support/Resistance + Rejection (Pin Bar / Wick) using mid price
def signal_rejection(ticker: str, timeframe="MINUTE", lookback=20, wick_ratio=2.0):
    bars_bid = [b for b in memory.ohlc_history.get((ticker, timeframe), []) if b["price_type"] == "bid"]
    bars_ask = [b for b in memory.ohlc_history.get((ticker, timeframe), []) if b["price_type"] == "ask"]

    # Need enough aligned bars
    if len(bars_bid) < lookback or len(bars_ask) < lookback:
        return TradeSide.NEUTRAL

    # Construct mid-price bars
    bars_mid = []
    for b_bid, b_ask in zip(bars_bid, bars_ask):
        bars_mid.append({
            "o": (b_bid["o"] + b_ask["o"]) / 2,
            "h": (b_bid["h"] + b_ask["h"]) / 2,
            "l": (b_bid["l"] + b_ask["l"]) / 2,
            "c": (b_bid["c"] + b_ask["c"]) / 2,
        })

    last = bars_mid[-1]
    closes = [b["c"] for b in bars_mid[-lookback:]]

    support = min(closes)
    resistance = max(closes)

    body = abs(last["c"] - last["o"])
    upper_wick = last["h"] - max(last["c"], last["o"])
    lower_wick = min(last["c"], last["o"]) - last["l"]

    # Bullish rejection at support (long lower wick, close near high)
    if last["l"] <= support and lower_wick > wick_ratio * body:
        return TradeSide.LONG

    # Bearish rejection at resistance (long upper wick, close near low)
    if last["h"] >= resistance and upper_wick > wick_ratio * body:
        return TradeSide.SHORT

    return TradeSide.NEUTRAL



# Breakout Scalping (Range Consolidation) using mid price
def signal_breakout(ticker: str, timeframe="MINUTE", range_period=10):
    bars_bid = [b for b in memory.ohlc_history.get((ticker, timeframe), []) if b["price_type"] == "bid"]
    bars_ask = [b for b in memory.ohlc_history.get((ticker, timeframe), []) if b["price_type"] == "ask"]

    # Need enough aligned bars
    if len(bars_bid) < range_period + 1 or len(bars_ask) < range_period + 1:
        return TradeSide.NEUTRAL

    # Construct mid-price bars
    bars_mid = []
    for b_bid, b_ask in zip(bars_bid, bars_ask):
        bars_mid.append({
            "o": (b_bid["o"] + b_ask["o"]) / 2,
            "h": (b_bid["h"] + b_ask["h"]) / 2,
            "l": (b_bid["l"] + b_ask["l"]) / 2,
            "c": (b_bid["c"] + b_ask["c"]) / 2,
        })

    recent = bars_mid[-(range_period+1):-1]  # consolidation range
    last = bars_mid[-1]  # breakout candle

    high_range = max(b["h"] for b in recent)
    low_range = min(b["l"] for b in recent)

    # Breakout above resistance
    if last["c"] > high_range:
        return TradeSide.LONG
    # Breakout below support
    elif last["c"] < low_range:
        return TradeSide.SHORT

    return TradeSide.NEUTRAL


