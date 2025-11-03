from .utils import atr, ema, rsi, sma, atr_from_df
from enums.trade import TradeSide
from .memory import memory
import numpy as np
import pandas as pd
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
    rsi_period=14,          # ← changed from 2
    base_oversold=30,       # ← changed from 10
    base_overbought=70,     # ← changed from 90
    ema_fast=20,
    ema_slow=50,
    vol_window=14,
):
    bars = [b for b in memory.get_history(ticker, timeframe) if b["price_type"] == "bid"]
    min_bars = max(rsi_period, ema_slow, vol_window) + 5
    if len(bars) < min_bars:
        return TradeSide.NEUTRAL

    closes = [b["c"] for b in bars]

    def safe_last(val):
        if val is None:
            return None
        if isinstance(val, (list, tuple, np.ndarray)):
            return val[-1] if len(val) > 0 else None
        return val

    rsi_val = safe_last(rsi(closes, rsi_period))
    ema_fast_val = safe_last(ema(closes, ema_fast))
    ema_slow_val = safe_last(ema(closes, ema_slow))
    atr_val = safe_last(atr(bars, vol_window))

    if None in (rsi_val, ema_fast_val, ema_slow_val, atr_val):
        return TradeSide.NEUTRAL

    # --- Stronger trend filter ---
    in_uptrend = ema_fast_val > ema_slow_val
    in_downtrend = ema_fast_val < ema_slow_val

    # --- Volatility filter (keep your logic) ---
    avg_range = sum(b["h"] - b["l"] for b in bars[-vol_window:]) / vol_window
    if atr_val > avg_range * 1.5:
        return TradeSide.NEUTRAL

    # --- Mean Reversion Logic ---
    # Only buy oversold if NOT in strong uptrend
    if rsi_val < base_oversold and not in_uptrend:
        return TradeSide.LONG

    # Only sell overbought if NOT in strong downtrend
    if rsi_val > base_overbought and not in_downtrend:
        return TradeSide.SHORT

    return TradeSide.NEUTRAL




# Enhanced Mean Reversion (RSI + Trend + Volatility-Adaptive)
def signal_mean_reversion_v2(
    ticker: str,
    timeframe="DAY",
    rsi_period=3,               # Slightly longer RSI for smoother signals
    base_oversold=15,           # Slightly wider zones
    base_overbought=85,
    trend_len=50,
    vol_window=14,
    smooth_rsi=True,            # Option to smooth RSI
    rsi_smooth_period=3,        # RSI smoothing factor
    atr_filter=2.0,             # ATR burst threshold
    bias_sensitivity=0.005,     # Minimum bias magnitude for trend filter
):
    try:
        bars = [b for b in memory.get_history(ticker, timeframe) if b["price_type"] == "bid"]
        if len(bars) < max(rsi_period, trend_len, vol_window) + 2:
            return TradeSide.NEUTRAL

        closes = [b["c"] for b in bars]
        highs = [b["h"] for b in bars]
        lows = [b["l"] for b in bars]

        def safe_last(val):
            if val is None:
                return None
            if isinstance(val, (list, tuple, np.ndarray)):
                return val[-1] if len(val) > 0 else None
            return val

        # --- Core indicators ---
        raw_rsi = rsi(closes, rsi_period)
        if smooth_rsi and len(raw_rsi) >= rsi_smooth_period:
            # Simple moving average smoothing on RSI
            rsi_vals = [np.mean(raw_rsi[i - rsi_smooth_period + 1 : i + 1]) 
                        for i in range(rsi_smooth_period - 1, len(raw_rsi))]
            rsi_val = safe_last(rsi_vals)
        else:
            rsi_val = safe_last(raw_rsi)

        ema_50 = safe_last(ema(closes, trend_len))
        atr_val = safe_last(atr(bars, vol_window))
        avg_range = np.mean([h - l for h, l in zip(highs[-vol_window:], lows[-vol_window:])])

        if rsi_val is None or ema_50 is None or atr_val is None:
            return TradeSide.NEUTRAL

        # --- Trend bias calculation ---
        trend_bias = (closes[-1] - ema_50) / ema_50 if ema_50 else 0
        bias = 1 if trend_bias > bias_sensitivity else (-1 if trend_bias < -bias_sensitivity else 0)

        # --- Adaptive RSI thresholds ---
        # Wider bands when volatility is high, narrower when calm
        vol_factor = min(1.5, max(0.5, atr_val / avg_range))
        oversold = base_oversold + (5 if bias > 0 else 0) * vol_factor
        overbought = base_overbought - (5 if bias < 0 else 0) * vol_factor

        # --- Volatility filter ---
        if atr_val > avg_range * atr_filter:
            return TradeSide.NEUTRAL

        # --- Entry logic ---
        if rsi_val < oversold and bias >= 0:
            return TradeSide.LONG
        elif rsi_val > overbought and bias <= 0:
            return TradeSide.SHORT
        else:
            return TradeSide.NEUTRAL

    except Exception as e:
        print("Error in mean reversion signal v2:", str(e))
        return TradeSide.NEUTRAL



# Breakout + ATR Buffer
def signal_atr_breakout(
    ticker: str,
    timeframe="DAY",
    atr_period=20,
    atr_mult=1.0,
    ema_period=50,
    swing_lookback=5,  # recent swing high/low window
):
    bars = [b for b in memory.get_history(ticker, timeframe) if b["price_type"] == "bid"]
    min_required = max(atr_period, ema_period, swing_lookback) + 2
    if len(bars) < min_required:
        return TradeSide.NEUTRAL

    # Extract price series
    closes = np.array([b["c"] for b in bars])
    highs = np.array([b["h"] for b in bars])
    lows = np.array([b["l"] for b in bars])

    # ATR
    vol = atr_from_df(pd.DataFrame(bars), atr_period)
    if vol is None or vol == 0:
        return TradeSide.NEUTRAL
    buffer = atr_mult * vol

    # EMA trend filter
    ema_vals = ema(closes, ema_period)
    current_price = closes[-1]
    current_ema = ema_vals[-1]
    trend_up = current_price > current_ema
    trend_down = current_price < current_ema

    # Recent swing high/low (excluding current bar)
    recent_high = highs[-(swing_lookback+1):-1].max()
    recent_low = lows[-(swing_lookback+1):-1].min()

    last_close = closes[-1]

    # Long: breakout above swing high + buffer AND in uptrend
    if last_close > recent_high + buffer and trend_up:
        return TradeSide.LONG

    # Short: breakdown below swing low - buffer AND in downtrend
    if last_close < recent_low - buffer and trend_down:
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
    sl_pnl = notional * (sl_dist / entry)  # min $20 SL
    tp_pnl = notional * (tp_dist / entry)

    return (int(tp_pnl), int(sl_pnl))



