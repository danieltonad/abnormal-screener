import numpy as np
from .utils import atr, ema, sma, adx
from enums.trade import TradeSide
from .memory import memory
from datetime import datetime, time

def is_high_activity_session(ticker: str) -> bool:
    """Detect high-liquidity sessions (UTC-based) — customize per ticker if needed."""
    now = datetime.utcnow().time()
    
    # Default: FX major pairs — focus on London-NY overlap (12:00–16:00 UTC)
    # For equities: use market open (e.g., 14:30–21:00 UTC for US)
    if "USD" in ticker or "EUR" in ticker or "JPY" in ticker:
        # London open: ~07:00–08:00 UTC, NY open: ~12:30 UTC, Overlap: 12:00–16:00 UTC
        high_session = time(12, 0) <= now <= time(16, 0)
        return high_session
    elif "SPX" in ticker or "US" in ticker.upper():
        # US equity session: 14:30–21:00 UTC
        return time(14, 30) <= now <= time(21, 0)
    else:
        # fallback: allow all but penalize low-volume times
        return True
    


def get_mid_bars(ticker: str, timeframe: str):
    asks = [b for b in memory.get_history(ticker, timeframe, "ask")]
    bids = [b for b in memory.get_history(ticker, timeframe, "bid")]
    if len(asks) != len(bids) or len(asks) == 0:
        return []
    return [
        {
            "t": a["t"],
            "o": (a["o"] + b["o"]) / 2,
            "h": (a["h"] + b["h"]) / 2,
            "l": (a["l"] + b["l"]) / 2,
            "c": (a["c"] + b["c"]) / 2,
            "v": a.get("v", b.get("v", 0)),  # prefer ask vol, fallback to bid
            "ask": a["c"],  # store raw for execution
            "bid": b["c"],
        }
        for a, b in zip(asks, bids)
    ]


def regime_detect(bars, lookback=50):
    """Return regime: 'trend_up', 'trend_down', 'chop', 'high_vol_breakout'"""
    if len(bars) < lookback + 10:
        return "chop"

    closes = np.array([b["c"] for b in bars])
    highs = np.array([b["h"] for b in bars])
    lows = np.array([b["l"] for b in bars])

    # ADX for trend strength
    adx_val, di_plus, di_minus = adx(highs, lows, closes, period=14)
    adx_recent = adx_val[-1] if len(adx_val) else 0

    # Volatility expansion (ATR ratio)
    atr_10 = atr(highs, lows, closes, period=10)[-1]
    atr_50 = atr(highs, lows, closes, period=50)[-1]
    vol_ratio = atr_10 / atr_50 if atr_50 > 0 else 1.0

    # Price vs EMA(20)
    ema_20 = ema(closes, period=20)[-1]
    price_vs_ema = (closes[-1] - ema_20) / ema_20

    # Regime logic
    if adx_recent > 25 and di_plus[-1] > di_minus[-1] + 3:
        return "trend_up"
    elif adx_recent > 25 and di_minus[-1] > di_plus[-1] + 3:
        return "trend_down"
    elif vol_ratio > 1.8 and abs(price_vs_ema) > 0.005:  # >0.5% move + vol spike
        return "high_vol_breakout"
    else:
        return "chop"


def signal_regime_adaptive_scalper(
    ticker: str,
    timeframe="MINUTE_5",  # also works well on MINUTE_1
    ema_fast=9,
    ema_slow=21,
    rsi_period=6,
    volume_factor=1.5,
    atr_mult_tp=1.2,
    atr_mult_sl=2.0,
):
    bars = get_mid_bars(ticker, timeframe)
    if len(bars) < 50:
        return TradeSide.NEUTRAL

    # 🔹 Regime filter
    regime = regime_detect(bars)
    if regime == "chop":
        return TradeSide.NEUTRAL  # avoid scalping noise

    # 🔹 Session filter (low-activity = reduce risk)
    if not is_high_activity_session(ticker):
        # only allow strongest signals (e.g., high-vol breakouts)
        if regime not in ["high_vol_breakout"]:
            return TradeSide.NEUTRAL

    # Data
    closes = np.array([b["c"] for b in bars])
    highs = np.array([b["h"] for b in bars])
    lows = np.array([b["l"] for b in bars])
    volumes = np.array([b.get("v", 1) for b in bars])

    # Indicators
    ema_f = ema(closes, ema_fast)
    ema_s = ema(closes, ema_slow)
    atr_vals = atr(highs, lows, closes, period=14)
    atr_now = atr_vals[-1] if len(atr_vals) else 0.001 * closes[-1]

    # RSI (fast, for overbought/oversold pullbacks)
    # Simple RSI implementation (replace with utils.rsi if available)
    def rsi(prices, period=rsi_period):
        deltas = np.diff(prices)
        gain = np.where(deltas > 0, deltas, 0)
        loss = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.array([np.mean(gain[:period])])
        avg_loss = np.array([np.mean(loss[:period])])
        for i in range(period, len(gain)):
            avg_gain = np.append(avg_gain, (avg_gain[-1] * (period - 1) + gain[i]) / period)
            avg_loss = np.append(avg_loss, (avg_loss[-1] * (period - 1) + loss[i]) / period)
        rs = avg_gain / np.where(avg_loss == 0, 1e-6, avg_loss)
        return 100 - (100 / (1 + rs))
    
    rsi_vals = rsi(closes)
    rsi_now = rsi_vals[-1] if len(rsi_vals) else 50

    # Volume confirmation: current volume > avg(volume last 20) * factor
    vol_ma = sma(volumes, 20)[-1]
    high_volume = volumes[-1] > vol_ma * volume_factor

    # Price & microstructure
    mid = closes[-1]
    prev_mid = closes[-2]
    bid = bars[-1]["bid"]
    ask = bars[-1]["ask"]

    # 🔹 Trend filter
    trend_up = ema_f[-1] > ema_s[-1] and ema_f[-2] > ema_s[-2]
    trend_down = ema_f[-1] < ema_s[-1] and ema_f[-2] < ema_s[-2]

    # 🔹 Strategy 1: Pullback in Trend (most robust scalper)
    if regime in ["trend_up", "trend_down"] and high_volume:
        # LONG: pullback to EMA(9) in uptrend, RSI > 45 (not oversold), price > EMA(21)
        if (trend_up and
            mid > ema_s[-1] and
            bid < ema_f[-1] < ask and      # price crossing *up* through EMA9
            rsi_now > 45 and rsi_now < 65 and
            closes[-1] > closes[-3] * 0.999):  # no sharp drop

            return TradeSide.LONG

        # SHORT: bounce off EMA(9) in downtrend, RSI < 55, price < EMA(21)
        if (trend_down and
            mid < ema_s[-1] and
            bid < ema_f[-1] < ask and      # price crossing *down* through EMA9
            rsi_now < 55 and rsi_now > 35 and
            closes[-1] < closes[-3] * 1.001):

            return TradeSide.SHORT

    # 🔹 Strategy 2: High-Volatility Breakout (session-aware)
    if regime == "high_vol_breakout" and high_volume:
        # Break above recent 5-bar high with volume + close > open
        recent_high_5 = max(highs[-6:-1])
        recent_low_5 = min(lows[-6:-1])
        bar_open = bars[-1]["o"]
        bar_close = closes[-1]

        # LONG breakout
        if (ask > recent_high_5 and
            bar_close > bar_open and
            (bar_close - bar_open) > 0.5 * (highs[-1] - lows[-1]) and
            volumes[-1] > vol_ma * 2.0):
            return TradeSide.LONG

        # SHORT breakout
        if (bid < recent_low_5 and
            bar_close < bar_open and
            (bar_open - bar_close) > 0.5 * (highs[-1] - lows[-1]) and
            volumes[-1] > vol_ma * 2.0):
            return TradeSide.SHORT

    return TradeSide.NEUTRAL