from .memory import memory
from .utils import atr
import numpy as np



def detect_vol_regime(ticker, timeframe="DAY", atr_period=20, lookback=100):
    bars = [b for b in memory.get_history(ticker, timeframe) if b["price_type"] == "bid"]
    if len(bars) < lookback:
        return "neutral"

    atr_vals = [atr(bars[i - atr_period:i]) for i in range(atr_period, len(bars))]
    curr_atr = atr_vals[-1]
    avg_atr = sum(atr_vals[-lookback:]) / lookback

    # Ratio of current to long-term volatility
    vol_ratio = curr_atr / avg_atr if avg_atr else 1

    if vol_ratio > 1.3:
        return "high_vol"
    elif vol_ratio < 0.7:
        return "low_vol"
    else:
        return "normal"


def detect_trend_regime(ticker, timeframe="DAY", fast=10, slow=40):
    bars = [b for b in memory.get_history(ticker, timeframe) if b["price_type"] == "bid"]
    closes = np.array([b["c"] for b in bars])

    if len(closes) < slow:
        return "neutral"

    ma_fast = closes[-fast:].mean()
    ma_slow = closes[-slow:].mean()

    if ma_fast > ma_slow * 1.002:  # small buffer to avoid chop
        return "bullish"
    elif ma_fast < ma_slow * 0.998:
        return "bearish"
    else:
        return "sideways"
    


def regime_bias(ticker):
    vol_state = detect_vol_regime(ticker)
    trend_state = detect_trend_regime(ticker)

    if vol_state == "high_vol":
        return "breakout"
    elif vol_state == "low_vol" and trend_state == "sideways":
        return "meanrev"
    else:
        return "neutral"

