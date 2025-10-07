import numpy as np
from collections import defaultdict
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
