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
    bars = [b for b in memory.get_history(ticker, timeframe) ]

    if len(bars) < breakout_period + exit_period:
        return TradeSide.NEUTRAL

    closes = [b["c"] for b in bars]
    highs = [b["h"] for b in bars]
    lows = [b["l"] for b in bars]

    last = bars[-1]

    high_range = max(highs[-breakout_period:])
    low_range  = min(lows[-breakout_period:])
    exit_high  = max(highs[-exit_period:])
    exit_low   = min(lows[-exit_period:])

    # --- Breakout Up ---
    if last["c"] > high_range:
        return TradeSide.LONG

    # --- Breakout Down ---
    if last["c"] < low_range:
        return TradeSide.SHORT

    # --- Exit Conditions: go neutral, not flip ---
    # If price crosses the exit band, we signal NEUTRAL (exit), not the opposite side.
    if last["c"] < exit_low or last["c"] > exit_high:
        return TradeSide.NEUTRAL

    return TradeSide.NEUTRAL




# Momentum Rotation (single-ticker version)
def signal_momentum(
    ticker: str,
    timeframe="DAY",
    lookback=60,
):
    bars = [b for b in memory.get_history(ticker, timeframe) ]

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
    rsi_period=14,
    base_oversold=35,       # ← slightly higher, more frequent buy signals
    base_overbought=65,     # ← slightly lower, more frequent sell signals
    ema_fast=20,
    ema_slow=50,
    vol_window=14,
):
    bars = [b for b in memory.get_history(ticker, timeframe) ]
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

    # --- Softer trend filter ---
    # Instead of blocking trades *against* a trend, just reduce conviction.
    in_uptrend = ema_fast_val > ema_slow_val * 1.01
    in_downtrend = ema_fast_val < ema_slow_val * 0.99

    # --- Mean Reversion Logic ---
    # Allow countertrend trades, but within reason.
    if rsi_val < base_oversold:
        if in_downtrend:  # countertrend, but okay if mild
            return TradeSide.LONG
        return TradeSide.LONG

    if rsi_val > base_overbought:
        if in_uptrend:
            return TradeSide.SHORT
        return TradeSide.SHORT

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
    buffer = atr_mult * vol * 0.8

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




def signal_unified(
    ticker: str,
    timeframe="DAY",
    regime_lookback=20,
    mr_rsi_period=2,
    mr_oversold=10,
    mr_overbought=90,
    atr_period=20,
    atr_mult=1.0,
    swing_lookback=5,
    ema_trend_period=50,
):
    bars = [b for b in memory.get_history(ticker, timeframe)]
    if len(bars) < max(regime_lookback, atr_period, ema_trend_period) + 5:
        return TradeSide.NEUTRAL

    df = pd.DataFrame(bars)
    closes = df["c"].values
    highs  = df["h"].values
    lows   = df["l"].values

    # -------------------------
    # 1. Regime Classification
    # -------------------------
    # Volatility compression → MR
    # Volatility expansion   → ATR breakout
    atr_vals = df["h"].sub(df["l"]).rolling(regime_lookback).mean()
    curr_range = (df["h"].iloc[-1] - df["l"].iloc[-1])
    avg_range  = atr_vals.iloc[-1] if not pd.isna(atr_vals.iloc[-1]) else None

    if avg_range is None:
        return TradeSide.NEUTRAL

    # Simple but effective classifier
    # low vol → MR mode
    # high vol → Trend mode
    is_low_vol = curr_range < 0.9 * avg_range
    is_high_vol = curr_range > 1.2 * avg_range

    # -------------------------
    # 2. Mean Reversion Block
    # -------------------------
    if is_low_vol:
        rsi_val = rsi(closes, mr_rsi_period)[-1]
        sma100 = sma(closes, 100)[-1]
        price = closes[-1]

        # uptrend → only long oversold
        if price > sma100 and rsi_val < mr_oversold:
            return TradeSide.LONG

        # downtrend → only short overbought
        if price < sma100 and rsi_val > mr_overbought:
            return TradeSide.SHORT

        return TradeSide.NEUTRAL

    # -------------------------
    # 3. ATR Breakout Block
    # -------------------------
    if is_high_vol:
        vol = atr_from_df(df, atr_period)
        if vol is None or vol == 0:
            return TradeSide.NEUTRAL

        buffer = atr_mult * vol * 0.8

        ema_val = ema(closes, ema_trend_period)[-1]
        price = closes[-1]

        trend_up = price > ema_val
        trend_down = price < ema_val

        recent_high = highs[-(swing_lookback+1):-1].max()
        recent_low  = lows[-(swing_lookback+1):-1].min()

        if price > recent_high + buffer and trend_up:
            return TradeSide.LONG

        if price < recent_low - buffer and trend_down:
            return TradeSide.SHORT

        return TradeSide.NEUTRAL

    # -------------------------
    # Neutral regime (transition)
    # -------------------------
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
    bars = [b for b in memory.get_history(ticker, timeframe) ]

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
    atr_mult=2.0,    # stop-loss multiple of ATR
    rr=2.0,          # reward multiple
    notional=1000.0
):
    """
    Returns (TP$, SL$, trail_range$)
    Spread-aware: expands volatility when spreads widen.
    Trail range adapts dynamically to volatility and spread context.
    """
    bids = [b for b in memory.get_history(ticker, timeframe, price_type="bid")]
    asks = [b for b in memory.get_history(ticker, timeframe, price_type="ask")]
    

    if len(bids) < atr_period + 1 or len(asks) < atr_period + 1:
        print(f"{ticker} ATR calculation failed.")
        return 100, 50, 25

    entry = (bids[-1]["c"] + asks[-1]["c"]) / 2

    vol = atr(bids, atr_period)
    if isinstance(vol, list):
        vol = vol[-1]

    if vol is None:
        print(f"{ticker} Vol calculation failed.")
        return 100, 50, 25

    spreads = [a["c"] - b["c"] for a, b in zip(asks[-atr_period:], bids[-atr_period:])]
    mids = [(a["c"] + b["c"]) / 2 for a, b in zip(asks[-atr_period:], bids[-atr_period:])]
    spread_pcts = [s / m for s, m in zip(spreads, mids)]

    current_spread_pct = spread_pcts[-1]
    avg_spread_pct = sum(spread_pcts) / len(spread_pcts)
    spread_ratio = current_spread_pct / max(avg_spread_pct, 1e-6)
    dynamic_mult = min(1.0 + 0.5 * (spread_ratio - 1), 2.0) if spread_ratio > 1 else 1.0

    adj_vol = vol * dynamic_mult

    sl_dist = atr_mult * adj_vol
    tp_dist = sl_dist * rr

    sl_pnl = notional * (sl_dist / entry)
    tp_pnl = notional * (tp_dist / entry)

    # --- SMART TRAIL RANGE ---
    # Base trail = halfway between SL and TP in terms of distance
    base_trail = (tp_dist - sl_dist) * 0.5

    # Add spread influence: if spread_ratio > 1, widen trail proportionally
    trail_adj = base_trail * (0.8 + 0.2 * min(spread_ratio, 3))  # mild widening up to +60%

    trail_pnl = notional * (trail_adj / entry)
    
    # print(f"{ticker} | TP: {int(tp_pnl)}, SL: {int(sl_pnl)}, Trail: {int(trail_pnl)}")
    return int(tp_pnl), int(sl_pnl), int(trail_pnl)





