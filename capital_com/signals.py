from .utils import ema, atr, check_cooldown, sma
from enums.trade import TradeSide
from .memory import memory
import numpy as np
from datetime import datetime


# EMA Crossover + ATR Filter (using mid price, ATR as % of price)
def signal_ema_crossover(
    ticker: str,
    timeframe="MINUTE",
    fast=5,
    slow=13,
    atr_period=14,
    lookback=50,
    atr_factor=0.7,
):
    try:
        bars = [b for b in memory.ohlc_history.get((ticker, timeframe), []) if b["price_type"] == "bid"]

        if len(bars) < max(slow, atr_period) + 1:
            return TradeSide.NEUTRAL

        closes = [b["c"] for b in bars]

        # EMA crossover
        fast_ema = ema(closes, fast)
        slow_ema = ema(closes, slow)
        last_fast, prev_fast = fast_ema[-1], fast_ema[-2]
        last_slow, prev_slow = slow_ema[-1], slow_ema[-2]

        # ATR ratios (vectorized if atr supports it)
        atr_values = atr(bars, atr_period)  # assume it returns list aligned with bars
        atr_ratios = [a / c for a, c in zip(atr_values, closes) if a]

        if not atr_ratios:
            return TradeSide.NEUTRAL

        recent_ratios = atr_ratios[-lookback:]
        mean_ratio = sum(recent_ratios) / len(recent_ratios)

        if atr_ratios[-1] <= atr_factor * mean_ratio:
            return TradeSide.NEUTRAL

        # Crossovers
        if prev_fast < prev_slow and last_fast > last_slow:
            return TradeSide.LONG
        if prev_fast > prev_slow and last_fast < last_slow:
            return TradeSide.SHORT

        return TradeSide.NEUTRAL
    
    except Exception as e:
        # print(f"EMA Crossover Error for {ticker}: {str(e)}")
        return TradeSide.NEUTRAL





# Support/Resistance + Rejection
def signal_rejection(
    ticker: str,
    timeframe="MINUTE",
    lookback=15,
    wick_factor=1.0,
    level_percentile=35,
    trend_period=20,
):
    bars = [b for b in memory.ohlc_history.get((ticker, timeframe), []) if b["price_type"] == "bid"]

    if len(bars) < max(lookback, trend_period):
        return TradeSide.NEUTRAL

    last = bars[-1]
    recent = bars[-lookback:]
    closes = [b["c"] for b in recent]

    sorted_closes = sorted(closes)
    support = sorted_closes[int(len(sorted_closes) * (level_percentile / 100))]
    resistance = sorted_closes[int(len(sorted_closes) * (1 - level_percentile / 100))]

    body = abs(last["c"] - last["o"])
    upper_wick = last["h"] - max(last["c"], last["o"])
    lower_wick = min(last["c"], last["o"]) - last["l"]

    if body == 0:
        return TradeSide.NEUTRAL

    trend_ma = sma(closes, trend_period)
    if trend_ma is None:
        return TradeSide.NEUTRAL

    entry = last["c"]

    # --- Bullish rejection ---
    if last["l"] <= support and (lower_wick / body) > wick_factor and entry > trend_ma:
        return TradeSide.LONG

    # --- Bearish rejection ---
    if last["h"] >= resistance and (upper_wick / body) > wick_factor and entry < trend_ma:
        return TradeSide.SHORT

    return TradeSide.NEUTRAL





# Breakout Scalping (Range Consolidation) using mid price
def signal_breakout(
    ticker: str,
    timeframe="MINUTE",
    range_period=18,
    atr_period=14,
    atr_mult=0.8,
    body_factor=1.5,
    trend_period=50,
):
    bars = [b for b in memory.ohlc_history.get((ticker, timeframe), []) if b["price_type"] == "bid"]

    if len(bars) < max(range_period + 2, atr_period + 1, trend_period):
        return TradeSide.NEUTRAL

    recent = bars[-(range_period+1):-1]  # consolidation candles
    last = bars[-1]                      # breakout candle
    prev = bars[-2]

    high_range = max(b["h"] for b in recent)
    low_range = min(b["l"] for b in recent)
    range_size = high_range - low_range

    # ATR buffer
    vol = atr(bars, atr_period)
    if isinstance(vol, list):
        vol = vol[-1]
    buffer = atr_mult * vol if vol else 0

    # Body filter
    bodies = [abs(b["c"] - b["o"]) for b in recent]
    avg_body = np.mean(bodies) if bodies else 1
    last_body = abs(last["c"] - last["o"])

    # Trend filter
    closes = [b["c"] for b in bars]
    trend_ma = sma(closes, trend_period)
    if trend_ma is None:
        return TradeSide.NEUTRAL
    if isinstance(trend_ma, list):
        trend_ma = trend_ma[-1]

    # --- Breakout UP ---
    if (
        last["c"] > high_range + buffer
        and last_body > max(body_factor * avg_body, 0.5 * vol)
        and last["c"] > trend_ma
    ):
        if prev["c"] <= high_range:
            return TradeSide.LONG

    # --- Breakout DOWN ---
    if (
        last["c"] < low_range - buffer
        and last_body > max(body_factor * avg_body, 0.5 * vol)
        and last["c"] < trend_ma
    ):
        if prev["c"] >= low_range:
            return TradeSide.SHORT

    return TradeSide.NEUTRAL








