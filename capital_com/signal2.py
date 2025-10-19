from .utils import atr, ema, rsi, sma
from enums.trade import TradeSide
from .memory import memory
import numpy as np
from datetime import datetime


# Trend-Following (Donchian / Turtle style)
def signal_trend_following(
    ticker: str,
    timeframe="DAY",
    breakout_period=20,
    exit_period=10,
):
    bars = [b for b in memory.get_history(ticker, timeframe) if b["price_type"] == "bid"]

    if len(bars) < breakout_period + exit_period:
        return TradeSide.NEUTRAL

    closes = [b["c"] for b in bars]
    highs = [b["h"] for b in bars]
    lows = [b["l"] for b in bars]

    last = bars[-1]

    high_range = max(highs[-breakout_period:])
    low_range = min(lows[-breakout_period:])
    exit_high = max(highs[-exit_period:])
    exit_low = min(lows[-exit_period:])

    # --- Breakout Up ---
    if last["c"] > high_range:
        return TradeSide.LONG

    # --- Breakout Down ---
    if last["c"] < low_range:
        return TradeSide.SHORT

    # --- Exit Conditions ---
    if last["c"] < exit_low:
        return TradeSide.SHORT
    if last["c"] > exit_high:
        return TradeSide.LONG

    return TradeSide.NEUTRAL



# Momentum Rotation (single-ticker version)
def signal_momentum(
    ticker: str,
    timeframe="DAY",
    lookback=60,
):
    bars = [b for b in memory.get_history(ticker, timeframe) if b["price_type"] == "bid"]

    if len(bars) < lookback + 1:
        return TradeSide.NEUTRAL

    closes = [b["c"] for b in bars]

    momentum = closes[-1] / closes[-lookback] - 1

    if momentum > 0:
        return TradeSide.LONG
    elif momentum < 0:
        return TradeSide.SHORT
    else:
        return TradeSide.NEUTRAL
    











# Mean Reversion (RSI(2))
def signal_mean_reversion(
    ticker: str,
    timeframe="DAY",
    rsi_period=2,
    base_oversold=10,
    base_overbought=90,
    trend_len=50,
    vol_window=14,
):
    try:
        bars = [b for b in memory.get_history(ticker, timeframe) if b["price_type"] == "bid"]
        if len(bars) < max(rsi_period, trend_len) + 1:
            return TradeSide.NEUTRAL

        closes = [b["c"] for b in bars]

        # --- Safe extractors ---
        def safe_last(val):
            """Handles None, float, list, np.ndarray safely"""
            if val is None:
                return None
            if isinstance(val, (list, tuple, np.ndarray)):
                return val[-1] if len(val) > 0 else None
            return val  # scalar (float/int)
        
        # --- Indicator values ---
        rsi_val = safe_last(rsi(closes, rsi_period))
        ema_50 = safe_last(ema(closes, trend_len))
        atr_val = safe_last(atr(bars, vol_window))

        # If any core indicator couldn't be computed yet, skip
        if rsi_val is None or ema_50 is None or atr_val is None:
            return TradeSide.NEUTRAL

        avg_range = sum([b["h"] - b["l"] for b in bars[-vol_window:]]) / vol_window

        # --- Trend Soft Bias ---
        trend_bias = (closes[-1] - ema_50) / ema_50 if ema_50 else 0
        bias = 1 if trend_bias > 0 else (-1 if trend_bias < 0 else 0)
        
        # --- Adaptive RSI thresholds ---
        oversold = base_oversold + (5 if bias > 0 else 0)
        overbought = base_overbought - (5 if bias < 0 else 0)

        # --- Volatility sanity check ---
        if atr_val > avg_range * 1.5:  # skip during high volatility bursts
            return TradeSide.NEUTRAL

        # --- Entry logic ---
        if rsi_val < oversold and bias >= 0:
            return TradeSide.LONG
        elif rsi_val > overbought and bias <= 0:
            return TradeSide.SHORT
        else:
            return TradeSide.NEUTRAL

    except Exception as e:
        print("Error in mean reversion signal:", str(e))
        return TradeSide.NEUTRAL




# Breakout + ATR Buffer
def signal_atr_breakout(
    ticker: str,
    timeframe="DAY",
    atr_period=20,
    atr_mult=1.0,
):
    bars = [b for b in memory.get_history(ticker, timeframe) if b["price_type"] == "bid"]

    if len(bars) < atr_period + 2:
        return TradeSide.NEUTRAL

    last = bars[-1]
    prev = bars[-2]

    vol = atr(bars, atr_period)
    if isinstance(vol, list):
        vol = vol[-1]
    buffer = atr_mult * vol if vol else 0

    if last["c"] > prev["h"] + buffer:
        return TradeSide.LONG
    elif last["c"] < prev["l"] - buffer:
        return TradeSide.SHORT

    return TradeSide.NEUTRAL





# Hybrid (Trend + Mean Reversion)
def signal_hybrid(
    ticker: str,
    timeframe="DAY",
    sma_period=100,
    rsi_period=2,
    oversold=10,
    overbought=90,
):
    bars = [b for b in memory.get_history(ticker, timeframe) if b["price_type"] == "bid"]

    if len(bars) < max(sma_period, rsi_period + 1):
        return TradeSide.NEUTRAL

    closes = [b["c"] for b in bars]
    sma_val = sma(closes, sma_period)
    if isinstance(sma_val, list):
        sma_val = sma_val[-1]

    rsi_val = rsi(closes, rsi_period)
    if isinstance(rsi_val, list):
        rsi_val = rsi_val[-1]

    last = bars[-1]

    # Uptrend → only long oversold
    if last["c"] > sma_val and rsi_val < oversold:
        return TradeSide.LONG

    # Downtrend → only short overbought
    if last["c"] < sma_val and rsi_val > overbought:
        return TradeSide.SHORT

    return TradeSide.NEUTRAL






# Candlestick Pattern Based Signal
def signal_candle_patterns(
    ticker: str,
    timeframe="DAY",
    sma_period=20
):
    bars = [
        b for b in memory.get_history(ticker, timeframe)
        if b["price_type"] == "bid"
    ]

    if len(bars) < sma_period + 3:
        return TradeSide.NEUTRAL

    closes = [b["c"] for b in bars]
    opens  = [b["o"] for b in bars]
    highs  = [b["h"] for b in bars]
    lows   = [b["l"] for b in bars]

    ma = sma(closes, sma_period)
    ma = ma[-1] if isinstance(ma, list) else ma

    last   = bars[-1]
    prev1  = bars[-2]
    prev2  = bars[-3]

    body     = abs(last["c"] - last["o"])
    avg_body = sum(abs(c - o) for c, o in zip(closes[-sma_period:], opens[-sma_period:])) / sma_period

    is_bull = last["c"] > last["o"]
    is_bear = last["c"] < last["o"]

    # === Bullish Patterns ===
    bull_engulf = (
        is_bull
        and last["c"] > prev1["o"]
        and last["o"] < prev1["c"]
        and last["c"] > prev1["c"]
        and last["o"] <= prev1["o"]
        and body > avg_body
        and last["c"] < ma
    )

    hammer = (
        is_bull
        and (last["h"] - last["l"]) > 3.0 * body
        and (last["c"] - last["l"]) / (0.001 + last["h"] - last["l"]) > 0.6
        and body > avg_body
        and last["c"] < ma
    )

    morning_star = (
        prev2["c"] < prev2["o"]
        and abs(prev1["c"] - prev1["o"]) < avg_body
        and is_bull
        and last["c"] > (prev2["o"] + prev2["c"]) / 2
        and last["c"] < ma
    )

    bullish = bull_engulf or hammer or morning_star

    # === Bearish Patterns ===
    bear_engulf = (
        is_bear
        and last["c"] < prev1["o"]
        and last["o"] > prev1["c"]
        and last["c"] < prev1["c"]
        and last["o"] >= prev1["o"]
        and body > avg_body
        and last["c"] > ma
    )

    shooting_star = (
        is_bear
        and (last["h"] - last["l"]) > 3.0 * body
        and (last["h"] - last["c"]) / (0.001 + last["h"] - last["l"]) > 0.6
        and body > avg_body
        and last["c"] > ma
    )

    evening_star = (
        prev2["c"] > prev2["o"]
        and abs(prev1["c"] - prev1["o"]) < avg_body
        and is_bear
        and last["c"] < (prev2["o"] + prev2["c"]) / 2
        and last["c"] > ma
    )

    bearish = bear_engulf or shooting_star or evening_star

    # === Return trade side ===
    if bullish:
        return TradeSide.LONG
    elif bearish:
        return TradeSide.SHORT
    else:
        return TradeSide.NEUTRAL










def get_levels(
    ticker: str,
    timeframe="DAY",
    atr_period=14,
    atr_mult=2.0,     # for SL
    rr=4.0,           # reward multiplier
    notional=1000.0
):
    """
    Returns (SL$, TP$) tuple at chosen RR.
    """
    bars = [b for b in memory.get_history(ticker, timeframe) if b["price_type"] == "bid"]
    if len(bars) < atr_period + 1:
        return 50, 50 # default

    entry = bars[-1]["c"]

    vol = atr(bars, atr_period)
    if isinstance(vol, list):
        vol = vol[-1]
    if vol is None:
        return 50, 50 # default

    # price distances
    sl_dist = atr_mult * vol
    tp_dist = sl_dist * rr

    # convert to dollar PnL
    sl_pnl = notional * (sl_dist / entry)
    tp_pnl = notional * (tp_dist / entry)

    return (int(tp_pnl), int(sl_pnl))



