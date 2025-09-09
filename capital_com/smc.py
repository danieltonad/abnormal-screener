from collections import defaultdict, deque
from enums.trade import TradeSide
from .memory import memory
import numpy as np
import pandas as pd


# ----------------------------
# Utils
# ----------------------------
def bars_to_mid_df(bars_bid, bars_ask):
    """Merge bid & ask bars into mid-price OHLC DataFrame."""
    df_bid = pd.DataFrame(bars_bid)
    df_ask = pd.DataFrame(bars_ask)
    if df_bid.empty or df_ask.empty:
        return pd.DataFrame(columns=["t","o","h","l","c"])

    merged = pd.merge(df_bid, df_ask, on="t", suffixes=("_bid","_ask"))
    merged["o"] = (merged["o_bid"] + merged["o_ask"]) / 2
    merged["h"] = (merged["h_bid"] + merged["h_ask"]) / 2
    merged["l"] = (merged["l_bid"] + merged["l_ask"]) / 2
    merged["c"] = (merged["c_bid"] + merged["c_ask"]) / 2
    return merged[["t","o","h","l","c"]]


def atr_from_df(df, period=14):
    if len(df) < period+1:
        return None
    high, low, close = df["h"], df["l"], df["c"]
    tr = np.maximum(high - low,
            np.maximum(abs(high - close.shift(1)), abs(low - close.shift(1))))
    return tr.rolling(window=period, min_periods=1).mean().iloc[-1]


def true_range_array(df):
    high, low, close = df["h"], df["l"], df["c"]
    tr = np.maximum(high - low,
            np.maximum((high - close.shift(1)).abs(), (low - close.shift(1)).abs()))
    return tr.fillna(high - low)


def is_consolidating(df, lookback=20, range_pct_threshold=0.003, atr_mult=0.5):
    if len(df) < lookback:
        return False
    recent = df[-lookback:]
    high, low, mid = recent["h"].max(), recent["l"].min(), recent["c"].mean()
    range_pct = (high - low) / max(1e-8, mid)
    atr = true_range_array(df).rolling(lookback).mean().iloc[-1]
    if np.isnan(atr):
        return range_pct < range_pct_threshold
    return (range_pct < range_pct_threshold) and (atr < atr_mult * mid)


# ----------------------------
# SMC Detectors
# ----------------------------
def detect_break_of_structure(df, lookback_swing=30):
    if len(df) < lookback_swing + 2:
        return None, {}
    recent = df[-(lookback_swing+1):]
    prev_high = recent["h"][:-1].max()
    prev_low = recent["l"][:-1].min()
    last_high, last_low = recent["h"].iloc[-1], recent["l"].iloc[-1]
    pct_buffer = 0.0005
    if last_high > prev_high * (1 + pct_buffer):
        return TradeSide.LONG, {"type":"BOS","prev_high":prev_high,"break":last_high}
    if last_low < prev_low * (1 - pct_buffer):
        return TradeSide.SHORT, {"type":"BOS","prev_low":prev_low,"break":last_low}
    return None, {}


def detect_order_block(df, lookback=50):
    if len(df) < 10:
        return None
    recent = df[-lookback:]
    bodies = (recent["c"] - recent["o"]).abs()
    ranges = (recent["h"] - recent["l"])
    body_ratio = bodies / (ranges.replace(0, np.nan))
    candidates = (body_ratio > 0.6).to_numpy().nonzero()[0]
    # candidates = (body_ratio > 0.6).to_numpy().nonzero()[0]
    if len(candidates) == 0:
        return None
    cand = recent.loc[candidates[-1]]
    if cand["o"] > cand["c"]:  # bearish candle
        return {"side":"BEARISH_OB", "zone":(float(cand["c"]), float(cand["h"]))}
    else:  # bullish candle
        return {"side":"BULLISH_OB", "zone":(float(cand["l"]), float(cand["c"]))}


def detect_fvg(df):
    if len(df) < 3:
        return None
    recent = df[-30:]
    for i in range(len(recent)-2):
        a, b, c = recent.iloc[i], recent.iloc[i+1], recent.iloc[i+2]
        if b["l"] > a["h"]:
            return {"type":"BULL_FVG","zone":(float(a["h"]), float(b["l"]))}
        if b["h"] < a["l"]:
            return {"type":"BEAR_FVG","zone":(float(b["h"]), float(a["l"]))}
    return None


def detect_liquidity_sweep(df, lookback=40, wick_pct=0.3):
    if len(df) < lookback + 1:
        return None
    recent = df[-(lookback+1):]
    local_high, local_low = recent["h"][:-1].max(), recent["l"][:-1].min()
    last = recent.iloc[-1]
    body = abs(last["c"] - last["o"])
    lower_wick = min(last["c"], last["o"]) - last["l"]
    upper_wick = last["h"] - max(last["c"], last["o"])
    if last["l"] < local_low and lower_wick > wick_pct * (last["h"] - last["l"]) and last["c"] > local_low:
        return {"type":"LIQ_SWEEP_LONG","sweep":last["l"]}
    if last["h"] > local_high and upper_wick > wick_pct * (last["h"] - last["l"]) and last["c"] < local_high:
        return {"type":"LIQ_SWEEP_SHORT","sweep":last["h"]}
    return None


# ----------------------------
# Main SMC Signal
# ----------------------------
def signal_smc(ticker: str,
               timeframe="MINUTE",
               min_bars=200,
               atr_period=14,
               atr_mult_entry=0.6,
               consolidation_lookback=20,
               confirmation_required=1):
    """
    Returns LONG / SHORT / NEUTRAL based on SMC logic.
    Uses mid-price OHLC built from bid & ask.
    """
    bars_bid = [b for b in memory.ohlc_history.get((ticker, timeframe), []) if b["price_type"]=="bid"]
    bars_ask = [b for b in memory.ohlc_history.get((ticker, timeframe), []) if b["price_type"]=="ask"]

    df = bars_to_mid_df(bars_bid, bars_ask)
    if len(df) < min_bars:
        return TradeSide.NEUTRAL

    atr_val = atr_from_df(df, atr_period)
    if atr_val is None:
        return TradeSide.NEUTRAL
    if is_consolidating(df, lookback=consolidation_lookback, range_pct_threshold=0.002, atr_mult=0.3):
        return TradeSide.NEUTRAL

    bos_signal, _ = detect_break_of_structure(df, lookback_swing=40)
    ob, fvg, sweep = detect_order_block(df,60), detect_fvg(df), detect_liquidity_sweep(df,50,0.35)

    last, price = df.iloc[-1], float(df["c"].iloc[-1])
    confirmations = 0

    # Candle impulse check
    candle_range = last["h"] - last["l"]
    avg_range = df["h"].sub(df["l"]).rolling(50).mean().iloc[-1]
    impulse_ok = candle_range > 1.2 * avg_range

    # Long logic
    if bos_signal == TradeSide.LONG and atr_val > atr_mult_entry * price:
        if ob and ob["side"]=="BULLISH_OB" and (ob["zone"][0]-atr_val <= price <= ob["zone"][1]+atr_val):
            confirmations += 1
        if fvg and fvg["type"]=="BULL_FVG" and (fvg["zone"][0]-atr_val <= price <= fvg["zone"][1]+atr_val):
            confirmations += 1
        if sweep and sweep["type"]=="LIQ_SWEEP_LONG":
            confirmations += 1
        lower_wick = min(last["c"], last["o"]) - last["l"]
        if impulse_ok and lower_wick > 0.5*abs(last["c"]-last["o"]):
            confirmations += 1
        if confirmations >= confirmation_required:
            return TradeSide.LONG

    # Short logic
    if bos_signal == TradeSide.SHORT and atr_val > atr_mult_entry * price:
        if ob and ob["side"]=="BEARISH_OB" and (ob["zone"][0]-atr_val <= price <= ob["zone"][1]+atr_val):
            confirmations += 1
        if fvg and fvg["type"]=="BEAR_FVG" and (fvg["zone"][0]-atr_val <= price <= fvg["zone"][1]+atr_val):
            confirmations += 1
        if sweep and sweep["type"]=="LIQ_SWEEP_SHORT":
            confirmations += 1
        upper_wick = last["h"] - max(last["c"], last["o"])
        if impulse_ok and upper_wick > 0.5*abs(last["c"]-last["o"]):
            confirmations += 1
        if confirmations >= confirmation_required:
            return TradeSide.SHORT

    return TradeSide.NEUTRAL
