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








def signal_atr_momentum(
    ticker: str,
    timeframe="HOUR",
    atr_period=14,
    roc_period=5,
    roc_atr_thresh=1.5,
    range_atr_mult=1.0,
    stall_bars=3,
):
    bars = [b for b in memory.get_history(ticker, timeframe)]
    min_required = max(atr_period, roc_period) + stall_bars + 5
    if len(bars) < min_required:
        return TradeSide.NEUTRAL

    df = pd.DataFrame(bars)
    closes = df["c"].values
    highs  = df["h"].values
    lows   = df["l"].values

    # ---- ATR ----
    atr = atr_from_df_v2(df, atr_period)
    if atr is None or atr == 0 or np.isnan(atr):
        return TradeSide.NEUTRAL

    last_close = closes[-1]
    prev_close = closes[-(roc_period + 1)]

    # ---- Vol-adjusted momentum ----
    roc_atr = (last_close - prev_close) / atr

    # ---- Expansion candle ----
    bar_range = highs[-1] - lows[-1]
    expansion = bar_range > range_atr_mult * atr

    # ---- Directional close ----
    close_pos = (last_close - lows[-1]) / max(bar_range, 1e-6)

    # ---- ENTRY ----
    if roc_atr > roc_atr_thresh and expansion and close_pos > 0.7:
        return TradeSide.LONG

    if roc_atr < -roc_atr_thresh and expansion and close_pos < 0.3:
        return TradeSide.SHORT

    # ---- INFER RECENT MOMENTUM DIRECTION ----
    recent_dir = None
    for i in range(-stall_bars - 1, -1):
        roc_i = (closes[i] - closes[i - roc_period]) / atr
        if roc_i > roc_atr_thresh:
            recent_dir = TradeSide.LONG
            break
        if roc_i < -roc_atr_thresh:
            recent_dir = TradeSide.SHORT
            break

    # ---- EXIT: momentum decay ----
    if recent_dir == TradeSide.LONG:
        if roc_atr < 0.5:
            return TradeSide.EXIT_LONG

    if recent_dir == TradeSide.SHORT:
        if roc_atr > -0.5:
            return TradeSide.EXIT_SHORT

    return TradeSide.NEUTRAL


























def signal_gold_intraday(
    ticker: str,
    timeframe="15",
    atr_period=14,
    ema_bias_period=20,
    ema_exit_period=9,
    range_lookback=12,
    compression_lookback=20,
):
    bars = [b for b in memory.get_history(ticker, timeframe)]
    min_required = max(atr_period, ema_bias_period, compression_lookback) + 10
    if len(bars) < min_required:
        return TradeSide.NEUTRAL

    closes = np.array([b["c"] for b in bars])
    highs  = np.array([b["h"] for b in bars])
    lows   = np.array([b["l"] for b in bars])

    df = pd.DataFrame(bars)

    atr = atr_from_df_v2(df, atr_period)
    if atr is None or atr == 0:
        return TradeSide.NEUTRAL

    ema_bias = ema(closes, ema_bias_period)
    ema_exit = ema(closes, ema_exit_period)

    last_close = closes[-1]
    current_bias = ema_bias[-1]
    current_exit = ema_exit[-1]

    trend_up = last_close > current_bias
    trend_down = last_close < current_bias

    # --- VOL COMPRESSION ---
    atr_series = df["h"] - df["l"]
    atr_mean = atr_series[-compression_lookback:].mean()

    is_compressed = atr < atr_mean * 0.8  # gold tolerates mild compression

    # --- RANGE STRUCTURE ---
    recent_high = highs[-(range_lookback+1):-1].max()
    recent_low  = lows[-(range_lookback+1):-1].min()

    buffer = atr * 1.2  # gold needs commitment

    is_long = (
        is_compressed and
        trend_up and
        last_close > recent_high + buffer
    )

    is_short = (
        is_compressed and
        trend_down and
        last_close < recent_low - buffer
    )

    if is_long:
        return TradeSide.LONG

    if is_short:
        return TradeSide.SHORT

    # --- EXIT LOGIC ---
    # fast EMA exit
    if trend_up and last_close < current_exit:
        return TradeSide.EXIT_LONG

    if trend_down and last_close > current_exit:
        return TradeSide.EXIT_SHORT

    return TradeSide.NEUTRAL












def signal_silver_intraday(
    ticker: str,
    timeframe="15",
    atr_period=14,
    ema_bias_period=20,
    ema_exit_period=9,
    range_lookback=15,
    compression_lookback=25,
):
    bars = [b for b in memory.get_history(ticker, timeframe)]
    min_required = max(atr_period, ema_bias_period, compression_lookback) + 10
    if len(bars) < min_required:
        return TradeSide.NEUTRAL

    closes = np.array([b["c"] for b in bars])
    highs  = np.array([b["h"] for b in bars])
    lows   = np.array([b["l"] for b in bars])

    df = pd.DataFrame(bars)

    atr = atr_from_df_v2(df, atr_period)
    if atr is None or atr == 0:
        return TradeSide.NEUTRAL

    ema_bias = ema(closes, ema_bias_period)
    ema_exit = ema(closes, ema_exit_period)

    last_close = closes[-1]
    current_bias = ema_bias[-1]
    current_exit = ema_exit[-1]

    trend_up = last_close > current_bias
    trend_down = last_close < current_bias

    # --- STRONGER COMPRESSION REQUIRED ---
    atr_series = df["h"] - df["l"]
    atr_mean = atr_series[-compression_lookback:].mean()

    is_compressed = atr < atr_mean * 0.7  # silver needs tighter coil

    # --- RANGE ---
    recent_high = highs[-(range_lookback+1):-1].max()
    recent_low  = lows[-(range_lookback+1):-1].min()

    buffer = atr * 1.8  # silver needs bigger displacement

    is_long = (
        is_compressed and
        trend_up and
        last_close > recent_high + buffer
    )

    is_short = (
        is_compressed and
        trend_down and
        last_close < recent_low - buffer
    )

    if is_long:
        return TradeSide.LONG

    if is_short:
        return TradeSide.SHORT

    # --- EXIT ---
    if trend_up and last_close < current_exit:
        return TradeSide.EXIT_LONG

    if trend_down and last_close > current_exit:
        return TradeSide.EXIT_SHORT

    return TradeSide.NEUTRAL