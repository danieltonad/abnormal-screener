import numpy as np

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
    return np.mean(trs[-period:]) if len(trs) >= period else None
