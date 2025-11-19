from .utils import ema, atr, check_cooldown, sma
from enums.trade import TradeSide
from .memory import memory
import numpy as np
from datetime import datetime


# EMA Crossover + ATR Filter (using mid price, ATR as % of price)
def ema_crossover(
    ticker: str,
    timeframe="MINUTE",
    fast=5,
    slow=13,
    slow_trend=300,
):
    try:
        bars = [b for b in memory.get_history(ticker, timeframe)]
        if len(bars) < max(slow_trend, slow, fast) + 1:
            return TradeSide.NEUTRAL

        closes = [b["c"] for b in bars]

        # Fast + slow EMA
        fast_ema = ema(closes, fast)
        slow_ema = ema(closes, slow)
        last_fast, prev_fast = fast_ema[-1], fast_ema[-2]
        last_slow, prev_slow = slow_ema[-1], slow_ema[-2]

        # Long-term trend filter
        trend_ema = ema(closes, slow_trend)
        if isinstance(trend_ema, (list, np.ndarray)):
            trend_ema = trend_ema[-1]

        # Bullish crossover
        if prev_fast < prev_slow and last_fast > last_slow:
            if closes[-1] > trend_ema:
                return TradeSide.LONG

        # Bearish crossover
        if prev_fast > prev_slow and last_fast < last_slow:
            if closes[-1] < trend_ema:
                return TradeSide.SHORT

        return TradeSide.NEUTRAL

    except Exception:
        return TradeSide.NEUTRAL






# Support/Resistance + Rejection
def signal_rejection(
    ticker: str,
    timeframe="MINUTE",
    lookback=15,
    wick_factor=1.0,
    level_percentile=35,
    trend_period=20,      # now EMA period
    slow_period=300,      # optional slow EMA filter
):
    bars = [b for b in memory.get_history(ticker, timeframe)]

    if len(bars) < max(lookback, trend_period, slow_period):
        return TradeSide.NEUTRAL

    last = bars[-1]
    recent = bars[-lookback:]
    closes = [b["c"] for b in recent]

    # Support / resistance via percentiles
    sorted_closes = sorted(closes)
    support = sorted_closes[int(len(sorted_closes) * (level_percentile / 100))]
    resistance = sorted_closes[int(len(sorted_closes) * (1 - level_percentile / 100))]

    # Candle structure
    body = abs(last["c"] - last["o"])
    upper_wick = last["h"] - max(last["c"], last["o"])
    lower_wick = min(last["c"], last["o"]) - last["l"]

    if body == 0:
        return TradeSide.NEUTRAL

    # --- Trend filters using EMA instead of SMA ---
    closes_full = [b["c"] for b in bars]

    fast_ema = ema(closes_full, trend_period)
    if isinstance(fast_ema, list) or isinstance(fast_ema, np.ndarray):
        fast_ema = fast_ema[-1]

    slow_ema = ema(closes_full, slow_period)
    if isinstance(slow_ema, list) or isinstance(slow_ema, np.ndarray):
        slow_ema = slow_ema[-1]

    entry = last["c"]

    # --- Bullish rejection ---
    if (
        last["l"] <= support
        and (lower_wick / body) > wick_factor
        and entry > fast_ema       # fast EMA trend
        and entry > slow_ema       # structural EMA filter
    ):
        return TradeSide.LONG

    # --- Bearish rejection ---
    if (
        last["h"] >= resistance
        and (upper_wick / body) > wick_factor
        and entry < fast_ema
        and entry < slow_ema
    ):
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
    trend_period=50,        # now used as EMA period
    slow_period=300,        # new slow EMA filter
):
    bars = [b for b in memory.get_history(ticker, timeframe)]

    if len(bars) < max(range_period + 2, atr_period + 1, slow_period):
        return TradeSide.NEUTRAL

    recent = bars[-(range_period+1):-1]  # consolidation candles
    last   = bars[-1]                    # breakout candle
    prev   = bars[-2]

    high_range = max(b["h"] for b in recent)
    low_range  = min(b["l"] for b in recent)

    # ATR buffer
    vol = atr(bars, atr_period)
    if isinstance(vol, list):
        vol = vol[-1]
    buffer = atr_mult * vol if vol else 0

    # Body filter
    bodies = [abs(b["c"] - b["o"]) for b in recent]
    avg_body = np.mean(bodies) if bodies else 1
    last_body = abs(last["c"] - last["o"])

    # Trend filters (EMA now)
    closes = [b["c"] for b in bars]

    fast_ema = ema(closes, trend_period)
    if isinstance(fast_ema, list) or isinstance(fast_ema, np.ndarray):
        fast_ema = fast_ema[-1]

    slow_ema = ema(closes, slow_period)
    if isinstance(slow_ema, list) or isinstance(slow_ema, np.ndarray):
        slow_ema = slow_ema[-1]

    # --- Breakout UP ---
    if (
        last["c"] > high_range + buffer
        and last_body > max(body_factor * avg_body, 0.5 * vol)
        and last["c"] > fast_ema            # fast trend filter (EMA)
        and last["c"] > slow_ema            # structural trend filter (300 EMA)
    ):
        if prev["c"] <= high_range:
            return TradeSide.LONG

    # --- Breakout DOWN ---
    if (
        last["c"] < low_range - buffer
        and last_body > max(body_factor * avg_body, 0.5 * vol)
        and last["c"] < fast_ema
        and last["c"] < slow_ema
    ):
        if prev["c"] >= low_range:
            return TradeSide.SHORT

    return TradeSide.NEUTRAL









