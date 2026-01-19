from .utils import atr, ema, rsi, sma, atr_from_df, atr_from_df_v2
from enums.trade import TradeSide
from .memory import memory
import numpy as np
import pandas as pd
from datetime import datetime




# Breakout + ATR Buffer
def signal_atr_breakout(
    ticker: str,
    timeframe="DAY",
    atr_period=20,
    atr_mult=1.0,
    ema_period=50,
    swing_lookback=5,  # recent swing high/low window
):
    bars = [b for b in memory.get_history(ticker, timeframe) ]
    min_required = max(atr_period, ema_period, swing_lookback) + 2
    if len(bars) < min_required:
        return TradeSide.NEUTRAL

    closes = np.array([b["c"] for b in bars])
    highs = np.array([b["h"] for b in bars])
    lows = np.array([b["l"] for b in bars])

    vol = atr_from_df(pd.DataFrame(bars), atr_period)
    if vol is None or vol == 0:
        return TradeSide.NEUTRAL

    # make buffer slightly smaller for equities to be more reactive
    buffer = atr_mult * atr_from_df_v2(pd.DataFrame(bars), atr_period)


    ema_vals = ema(closes, ema_period)
    current_price = closes[-1]
    current_ema = ema_vals[-1]
    trend_up = current_price > current_ema
    trend_down = current_price < current_ema

    recent_high = highs[-(swing_lookback+1):-1].max()
    recent_low  = lows[-(swing_lookback+1):-1].min()

    last_close = closes[-1]

    if last_close > recent_high + buffer and trend_up:
        return TradeSide.LONG

    if last_close < recent_low - buffer and trend_down:
        return TradeSide.SHORT

    return TradeSide.NEUTRAL














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
