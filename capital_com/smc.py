import numpy as np
import pandas as pd
from enums.trade import TradeSide
from .memory import memory


# ----------------------------
# Utils
# ----------------------------
def atr_from_df(df, period=14):
    if len(df) < period + 1:
        return None
    high, low, close = df["h"], df["l"], df["c"]
    tr = np.maximum(high - low,
            np.maximum(abs(high - close.shift(1)), abs(low - close.shift(1))))
    return tr.rolling(window=period, min_periods=1).mean().iloc[-1]


def is_consolidating(df, lookback=20, range_pct_threshold=0.015):
    if len(df) < lookback:
        return False
    recent = df[-lookback:]
    high, low, mid = recent["h"].max(), recent["l"].min(), recent["c"].mean()
    range_pct = (high - low) / max(1e-8, mid)
    return range_pct < range_pct_threshold


# ----------------------------
# SMC Detectors
# ----------------------------
def detect_break_of_structure(df, lookback_swing=30):
    if len(df) < lookback_swing + 2:
        return None
    recent = df[-(lookback_swing+1):]
    prev_high = recent["h"][:-1].max()
    prev_low = recent["l"][:-1].min()
    last_high, last_low = recent["h"].iloc[-1], recent["l"].iloc[-1]
    pct_buffer = 0.0001
    if last_high > prev_high * (1 + pct_buffer):
        return TradeSide.LONG
    if last_low < prev_low * (1 - pct_buffer):
        return TradeSide.SHORT
    return None


def detect_order_block(df, lookback=50):
    if len(df) < 10:
        return None
    recent = df[-lookback:]
    bodies = (recent["c"] - recent["o"]).abs()
    ranges = (recent["h"] - recent["l"])
    body_ratio = bodies / (ranges.replace(0, np.nan))
    candidates = (body_ratio > 0.4).to_numpy().nonzero()[0]
    if len(candidates) == 0:
        return None
    cand = recent.iloc[candidates[-1]]
    if cand["o"] > cand["c"]:  # bearish OB
        return {"side": "BEARISH_OB", "zone": (float(cand["c"]), float(cand["h"]))}
    else:  # bullish OB
        return {"side": "BULLISH_OB", "zone": (float(cand["l"]), float(cand["c"]))}


def detect_fvg(df):
    if len(df) < 3:
        return None
    recent = df[-30:]
    for i in range(len(recent) - 2):
        a, b, c = recent.iloc[i], recent.iloc[i+1], recent.iloc[i+2]
        if b["l"] > a["h"]:
            return {"type": "BULL_FVG", "zone": (float(a["h"]), float(b["l"]))}
        if b["h"] < a["l"]:
            return {"type": "BEAR_FVG", "zone": (float(b["h"]), float(a["l"]))}
    return None


def detect_liquidity_sweep(df, lookback=40, wick_pct=0.35):
    if len(df) < lookback + 1:
        return None
    recent = df[-(lookback+1):]
    local_high, local_low = recent["h"][:-1].max(), recent["l"][:-1].min()
    last = recent.iloc[-1]
    lower_wick = min(last["c"], last["o"]) - last["l"]
    upper_wick = last["h"] - max(last["c"], last["o"])
    if last["l"] < local_low and lower_wick > wick_pct * (last["h"] - last["l"]) and last["c"] > local_low:
        return {"type": "LIQ_SWEEP_LONG"}
    if last["h"] > local_high and upper_wick > wick_pct * (last["h"] - last["l"]) and last["c"] < local_high:
        return {"type": "LIQ_SWEEP_SHORT"}
    return None


# ----------------------------
# Main SMC Signal
# ----------------------------
def signal_smc(
    ticker: str,
    timeframe="MINUTE",
    min_bars=200,
    atr_period=14,
    consolidation_lookback=20,
    confirmation_required=2,
):
    """
    Returns LONG / SHORT / NEUTRAL based on SMC logic.
    Uses bid bars only.
    """
    bars = [b for b in memory.get_history(ticker, timeframe, 200) if b["price_type"] == "bid"]
    if len(bars) < min_bars:
        return TradeSide.NEUTRAL

    df = pd.DataFrame(bars)[["t", "o", "h", "l", "c"]]

    # ATR filter
    atr_val = atr_from_df(df, atr_period)
    if atr_val is None:
        return TradeSide.NEUTRAL

    # Consolidation filter
    if is_consolidating(df, lookback=consolidation_lookback, range_pct_threshold=0.02):
        return TradeSide.NEUTRAL

    # Core SMC detectors
    bos_signal = detect_break_of_structure(df, lookback_swing=20)
    ob = detect_order_block(df, 60)
    fvg = detect_fvg(df)
    sweep = detect_liquidity_sweep(df, 50, 0.25)

    last = df.iloc[-1]
    price = float(last["c"])
    confirmations = 0

    # Candle impulse
    candle_range = last["h"] - last["l"]
    avg_range = df["h"].sub(df["l"]).rolling(50).mean().iloc[-1]
    impulse_ok = candle_range > 1.02 * avg_range

    # --- Long logic ---
    if bos_signal == TradeSide.LONG:
        if ob and ob["side"] == "BULLISH_OB" and ob["zone"][0] <= price <= ob["zone"][1]:
            confirmations += 1
        if fvg and fvg["type"] == "BULL_FVG" and fvg["zone"][0] <= price <= fvg["zone"][1]:
            confirmations += 1
        if sweep and sweep["type"] == "LIQ_SWEEP_LONG":
            confirmations += 1
        lower_wick = min(last["c"], last["o"]) - last["l"]
        if impulse_ok and lower_wick > 0.5 * abs(last["c"] - last["o"]):
            confirmations += 1
        if confirmations > confirmation_required:
            return TradeSide.LONG

    # --- Short logic ---
    if bos_signal == TradeSide.SHORT:
        if ob and ob["side"] == "BEARISH_OB" and ob["zone"][0] <= price <= ob["zone"][1]:
            confirmations += 1
        if fvg and fvg["type"] == "BEAR_FVG" and fvg["zone"][0] <= price <= fvg["zone"][1]:
            confirmations += 1
        if sweep and sweep["type"] == "LIQ_SWEEP_SHORT":
            confirmations += 1
        upper_wick = last["h"] - max(last["c"], last["o"])
        if impulse_ok and upper_wick > 0.5 * abs(last["c"] - last["o"]):
            confirmations += 1
        if confirmations > confirmation_required:
            return TradeSide.SHORT

    return TradeSide.NEUTRAL
