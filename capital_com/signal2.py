from .utils import atr, ema, rsi, sma, atr_from_df, atr_from_df_v2
from enums.trade import TradeSide
from .memory import memory
import numpy as np
import pandas as pd
from datetime import datetime




# ATR Breakout exit

def signal_atr_breakout_exit(
    ticker: str,
    timeframe="DAY",
    atr_period=20,
    atr_mult=1.0,
    ema_period=50,
    swing_lookback=5,
):
    bars = [b for b in memory.get_history(ticker, timeframe)]
    min_required = max(atr_period, ema_period, swing_lookback) + 10
    if len(bars) < min_required:
        return TradeSide.NEUTRAL

    closes = np.array([b["c"] for b in bars])
    highs  = np.array([b["h"] for b in bars])
    lows   = np.array([b["l"] for b in bars])

    vol = atr_from_df_v2(pd.DataFrame(bars), atr_period)
    if vol is None or vol == 0:
        return TradeSide.NEUTRAL

    buffer = atr_mult * vol


    ema_vals = ema(closes, ema_period)
    last_close = closes[-1]
    current_ema = ema_vals[-1]

    trend_up = last_close > current_ema
    trend_down = last_close < current_ema

    recent_high = highs[-(swing_lookback + 1):-1].max()
    recent_low  = lows[-(swing_lookback + 1):-1].min()

    # ---- CURRENT DIRECTION ----
    is_long = last_close > recent_high + buffer and trend_up
    is_short = last_close < recent_low - buffer and trend_down

    if is_long:
        return TradeSide.LONG

    if is_short:
        return TradeSide.SHORT

    # ---- INFER RECENT DIRECTION ----
    recent_direction = None
    lookback = swing_lookback * 3

    for i in range(-lookback, -1):
        price = closes[i]
        ema_i = ema_vals[i]

        if price > ema_i:
            rh = highs[i-(swing_lookback+1):i].max()
            if price > rh + buffer:
                recent_direction = TradeSide.LONG
                break

        if price < ema_i:
            rl = lows[i-(swing_lookback+1):i].min()
            if price < rl - buffer:
                recent_direction = TradeSide.SHORT
                break

    # ---- EXIT CONDITIONS ----
    if recent_direction == TradeSide.LONG:
        if last_close < current_ema:
            return TradeSide.EXIT_LONG

    if recent_direction == TradeSide.SHORT:
        if last_close > current_ema:
            return TradeSide.EXIT_SHORT

    return TradeSide.NEUTRAL


























# 
def signal_atr_hilo_breakout(
    ticker: str,
    timeframe="DAY",
    atr_period=20,
    atr_mult=1.0,
    ema_period=50,
    swing_lookback=5,
    exit_buffer_mult=0.25
):
    bars = [b for b in memory.get_history(ticker, timeframe)]
    min_required = max(atr_period, ema_period, swing_lookback) + 20
    if len(bars) < min_required:
        return TradeSide.NEUTRAL

    df = pd.DataFrame(bars)
    closes = df["c"].values
    highs  = df["h"].values
    lows   = df["l"].values

    # ---- ATR (volatility buffer) ----
    atr = atr_from_df_v2(df, atr_period)
    if atr is None or np.isnan(atr) or atr == 0:
        return TradeSide.NEUTRAL

    buffer = atr_mult * atr

    # ---- EMA trend ----
    ema_vals = ema(closes, ema_period)
    last_close = closes[-1]
    current_ema = ema_vals[-1]

    trend_up = last_close > current_ema
    trend_down = last_close < current_ema

    # ---- Swing levels (spike-resistant) ----
    window_highs = highs[-(swing_lookback + 1):-1]
    window_lows  = lows[-(swing_lookback + 1):-1]

    swing_high = np.percentile(window_highs, 90)
    swing_low  = np.percentile(window_lows, 10)

    # ---- ENTRY CONDITIONS ----
    if trend_up and last_close > swing_high + buffer:
        return TradeSide.LONG

    if trend_down and last_close < swing_low - buffer:
        return TradeSide.SHORT

    # ---- INFER LAST DIRECTION ----
    recent_direction = None
    lookback = swing_lookback * 3

    for i in range(-lookback, -1):
        price = closes[i]
        ema_i = ema_vals[i]

        if price > ema_i:
            rh = np.percentile(highs[i-(swing_lookback+1):i], 90)
            if price > rh + buffer:
                recent_direction = TradeSide.LONG
                break

        if price < ema_i:
            rl = np.percentile(lows[i-(swing_lookback+1):i], 10)
            if price < rl - buffer:
                recent_direction = TradeSide.SHORT
                break

    # ---- EXIT CONDITIONS ----
    exit_buffer = exit_buffer_mult * atr

    if recent_direction == TradeSide.LONG:
        if last_close < current_ema - exit_buffer:
            return TradeSide.EXIT_LONG

    if recent_direction == TradeSide.SHORT:
        if last_close > current_ema + exit_buffer:
            return TradeSide.EXIT_SHORT

    return TradeSide.NEUTRAL













# def signal_atr_momentum(
#     ticker: str,
#     timeframe="HOUR",
#     atr_period=14,
#     roc_period=5,
#     roc_atr_thresh=1.5,
#     range_atr_mult=1.0,
#     stall_bars=3,
# ):
#     bars = [b for b in memory.get_history(ticker, timeframe)]
#     min_required = max(atr_period, roc_period) + stall_bars + 5
#     if len(bars) < min_required:
#         return TradeSide.NEUTRAL

#     df = pd.DataFrame(bars)
#     closes = df["c"].values
#     highs  = df["h"].values
#     lows   = df["l"].values

#     # ---- ATR ----
#     atr = atr_from_df_v2(df, atr_period)
#     if atr is None or atr == 0 or np.isnan(atr):
#         return TradeSide.NEUTRAL

#     last_close = closes[-1]
#     prev_close = closes[-(roc_period + 1)]

#     # ---- Vol-adjusted momentum ----
#     roc_atr = (last_close - prev_close) / atr

#     # ---- Expansion candle ----
#     bar_range = highs[-1] - lows[-1]
#     expansion = bar_range > range_atr_mult * atr

#     # ---- Directional close ----
#     close_pos = (last_close - lows[-1]) / max(bar_range, 1e-6)

#     # ---- ENTRY ----
#     if roc_atr > roc_atr_thresh and expansion and close_pos > 0.7:
#         return TradeSide.LONG

#     if roc_atr < -roc_atr_thresh and expansion and close_pos < 0.3:
#         return TradeSide.SHORT

#     # ---- INFER RECENT MOMENTUM DIRECTION ----
#     recent_dir = None
#     for i in range(-stall_bars - 1, -1):
#         roc_i = (closes[i] - closes[i - roc_period]) / atr
#         if roc_i > roc_atr_thresh:
#             recent_dir = TradeSide.LONG
#             break
#         if roc_i < -roc_atr_thresh:
#             recent_dir = TradeSide.SHORT
#             break

#     # ---- EXIT: momentum decay ----
#     if recent_dir == TradeSide.LONG:
#         if roc_atr < 0.5:
#             return TradeSide.EXIT_LONG

#     if recent_dir == TradeSide.SHORT:
#         if roc_atr > -0.5:
#             return TradeSide.EXIT_SHORT

#     return TradeSide.NEUTRAL






def signal_atr_momentum(
    ticker: str,
    timeframe="HOUR",          # Critical: match your actual trading TF
    atr_period=14,
    roc_period=5,
    entry_thresh=1.5,
    exit_thresh=0.4,
    persistence=2,              # ← Require N consecutive bars of decay
):
    bars = list(memory.get_history(ticker, timeframe))
    min_required = max(atr_period, roc_period) + 10
    if len(bars) < min_required:
        return TradeSide.NEUTRAL

    df = pd.DataFrame(bars)
    closes = df["c"].values
    highs = df["h"].values
    lows = df["l"].values

    atr = atr_from_df_v2(df, atr_period)
    if not atr or atr == 0 or np.isnan(atr):
        return TradeSide.NEUTRAL

    # ---- Momentum series (ROC normalized by ATR) ----
    roc_series = np.array([
        (closes[i] - closes[i - roc_period]) / atr
        for i in range(roc_period, len(closes))
    ])

    last_roc = roc_series[-1]

    # ---- Expansion + close position (entry filters) ----
    bar_range = highs[-1] - lows[-1]
    expansion = bar_range > 0.8 * atr
    close_pos = (closes[-1] - lows[-1]) / max(bar_range, 1e-6)

    # ---- ENTRY: Require strong, confirmed momentum (2-bar) ----
    if (len(roc_series) >= 2 and
        roc_series[-1] > entry_thresh and roc_series[-2] > entry_thresh and
        expansion and close_pos > 0.65):
        return TradeSide.LONG

    if (len(roc_series) >= 2 and
        roc_series[-1] < -entry_thresh and roc_series[-2] < -entry_thresh and
        expansion and close_pos < 0.35):
        return TradeSide.SHORT

    # ---- EXIT: Only if momentum was strong recently AND decayed persistently ----
    # 1. Was momentum strong enough to have triggered an entry recently?
    recent_peak = max(abs(roc_series[-5:])) if len(roc_series) >= 5 else 0
    was_strong = recent_peak > entry_thresh * 0.8

    if not was_strong:
        return TradeSide.NEUTRAL  # No trade likely existed → no exit

    # 2. Has momentum decayed for N consecutive bars?
    decayed_long = all(roc < exit_thresh for roc in roc_series[-persistence:])
    decayed_short = all(roc > -exit_thresh for roc in roc_series[-persistence:])

    # 3. Optional but recommended: price confirms decay via swing break
    swing_high = highs[-6:-1].max() if len(highs) >= 7 else highs[-1]
    swing_low = lows[-6:-1].min() if len(lows) >= 7 else lows[-1]
    broke_swing_long = closes[-1] < swing_low
    broke_swing_short = closes[-1] > swing_high

    # ---- EXIT LOGIC ----
    if decayed_long and broke_swing_long:
        return TradeSide.EXIT_LONG

    if decayed_short and broke_swing_short:
        return TradeSide.EXIT_SHORT

    return TradeSide.NEUTRAL
