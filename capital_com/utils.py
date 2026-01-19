import numpy as np
from collections import defaultdict
import pandas as pd
from datetime import datetime

last_signal_time = defaultdict(lambda: None)  # cooldown memory



def sma(values, period):
    if len(values) < period:
        return None
    return sum(values[-period:]) / period

def ema(values, period):
    """Exponential Moving Average"""
    weights = np.exp(np.linspace(-1., 0., period))
    weights /= weights.sum()
    return np.convolve(values, weights, mode='full')[:len(values)]

def atr(bars, period=14):
    """Average True Range"""
    trs = []
    for i in range(1, len(bars)):
        high = bars[i]["h"]
        low = bars[i]["l"]
        prev_close = bars[i-1]["c"]
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)
    return np.mean(trs[-period:]) if len(trs) >= period else []

def atr_v2(high, low, close, period=14):
    """
    ATR that matches the expected signature:
    atr(high, low, close, period) -> ATR array
    """

    high = np.asarray(high)
    low = np.asarray(low)
    close = np.asarray(close)

    if len(high) < period + 1:
        return np.array([])

    tr1 = high[1:] - low[1:]
    tr2 = np.abs(high[1:] - close[:-1])
    tr3 = np.abs(low[1:] - close[:-1])

    tr = np.maximum.reduce([tr1, tr2, tr3])

    # Wilder's smoothing
    atr = np.zeros_like(tr)
    atr[period-1] = np.mean(tr[:period])

    for i in range(period, len(tr)):
        atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period

    return atr


def atr_from_df(df, period=14):
    if len(df) < period + 1:
        return None
    high, low, close = df["h"], df["l"], df["c"]
    tr = np.maximum(high - low,
            np.maximum(abs(high - close.shift(1)), abs(low - close.shift(1))))
    return tr.rolling(window=period, min_periods=1).mean().iloc[-1]



def atr_from_df_v2(df, period=20, smooth=3):
    """
    df: DataFrame with 'h', 'l', 'c'
    period: ATR lookback
    smooth: EMA smoothing factor for CFD feed quirks
    """
    highs = df['h'].values
    lows  = df['l'].values
    closes = df['c'].values
    
    tr = np.maximum(highs - lows, np.maximum(np.abs(highs - np.roll(closes, 1)), np.abs(lows - np.roll(closes, 1))))
    tr[0] = highs[0] - lows[0]  # first candle
    
    # Standard ATR (rolling mean)
    atr = pd.Series(tr).rolling(period).mean()
    
    # Smooth ATR to reduce CFD noise
    if smooth > 1:
        atr = atr.ewm(span=smooth, adjust=False).mean()
    
    return atr.values[-1] if len(atr) > 0 else None



def check_cooldown(ticker, now, cooldown=5):
    """Prevent multiple trades within cooldown minutes."""
    global last_signal_time
    if last_signal_time[ticker] is not None:
        delta = (now - last_signal_time[ticker]).total_seconds() / 60
        if delta < cooldown:
            return False
    last_signal_time[ticker] = now
    return True



def rsi(closes, period=14):
    if len(closes) < period + 1:
        return None

    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    rsi_values = []

    if avg_loss == 0:
        rsi_values.append(100.0)
    else:
        rs = avg_gain / avg_loss
        rsi_values.append(100.0 - (100.0 / (1.0 + rs)))

    # Wilder’s smoothing
    for i in range(period, len(deltas)):
        gain = gains[i]
        loss = losses[i]

        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

        if avg_loss == 0:
            rsi_values.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi_values.append(100.0 - (100.0 / (1.0 + rs)))

    return rsi_values if len(rsi_values) > 1 else rsi_values[0]




def adx(high, low, close, period=14):
    """
    Returns:
        adx, plus_di, minus_di  — each is a numpy array
    """

    high = np.asarray(high)
    low = np.asarray(low)
    close = np.asarray(close)

    if len(high) <= period + 2:
        return np.array([]), np.array([]), np.array([])

    # True Range
    tr1 = high[1:] - low[1:]
    tr2 = np.abs(high[1:] - close[:-1])
    tr3 = np.abs(low[1:] - close[:-1])
    tr = np.maximum.reduce([tr1, tr2, tr3])

    # Directional Movement
    up_move = high[1:] - high[:-1]
    down_move = low[:-1] - low[1:]

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    # Wilder smoothing
    def wilder_smooth(values):
        smoothed = np.zeros_like(values)
        smoothed[period-1] = np.sum(values[:period])
        for i in range(period, len(values)):
            smoothed[i] = smoothed[i-1] - (smoothed[i-1] / period) + values[i]
        return smoothed

    tr_smooth = wilder_smooth(tr)
    plus_dm_smooth = wilder_smooth(plus_dm)
    minus_dm_smooth = wilder_smooth(minus_dm)

    # DI
    plus_di = 100 * (plus_dm_smooth / (tr_smooth + 1e-10))
    minus_di = 100 * (minus_dm_smooth / (tr_smooth + 1e-10))


    # DX
    dx = 100 * (np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10))

    # ADX: Wilder smoothing of DX
    adx_vals = np.zeros_like(dx)
    adx_vals[period*2-2] = np.mean(dx[period-1:period*2-1])

    for i in range(period*2-1, len(dx)):
        adx_vals[i] = ((adx_vals[i-1] * (period - 1)) + dx[i]) / period

    return adx_vals, plus_di, minus_di
