from enums.trade import TradeSide
from typing import List, Dict, Optional
from memory import memory
import math
import statistics
import time


# === Utility helpers ===
def tail(bars: List[Dict], n: int) -> List[Dict]:
    return bars[-n:] if len(bars) >= n else bars[:]

def high_of(bars: List[Dict]) -> float:
    return max(b["h"] for b in bars) if bars else None

def low_of(bars: List[Dict]) -> float:
    return min(b["l"] for b in bars) if bars else None

def last_price(bars: List[Dict]) -> float:
    return bars[-1]["c"] if bars else None


# === Market Structure Bias (H4) ===
def market_structure_bias(bars: List[Dict], swing_lookback=20) -> str:
    """
    Very simple structure detector:
     - find sequence of swing highs and swing lows (local peaks/troughs)
     - if last two swings show HH/HL -> bullish; LL/LH -> bearish
     - else neutral
    """
    n = min(len(bars), swing_lookback)
    if n < 6:
        return "neutral"

    # detect local peaks/troughs by simple comparison with neighbors
    highs = []
    lows = []
    for i in range(2, n-2):
        center = bars[-n + i]
        prev1 = bars[-n + i - 1]
        next1 = bars[-n + i + 1]
        if center["h"] > prev1["h"] and center["h"] > next1["h"]:
            highs.append((center["h"], center["t"]))
        if center["l"] < prev1["l"] and center["l"] < next1["l"]:
            lows.append((center["l"], center["t"]))

    # need at least 2 swings of each type to form a sequence
    # build combined chronological swings keyed by time
    swings = []
    for h,p in highs:
        swings.append(("H", p, h))
    for l,p in lows:
        swings.append(("L", p, l))
    swings.sort(key=lambda x: x[1])  # sort by timestamp
    # compress to last few swings
    swings = swings[-6:]

    # derive simple pattern: look at last two meaningful swings
    if len(swings) < 3:
        return "neutral"

    # extract last price values for highs and lows
    # find last two highs and last two lows in the swings list
    last_highs = [v for typ,_,v in swings if typ == "H"][-2:]
    last_lows = [v for typ,_,v in swings if typ == "L"][-2:]

    try:
        if len(last_highs) >= 2 and len(last_lows) >= 2:
            # bullish if last high > prev high AND last low > prev low (HH & HL)
            if last_highs[-1] > last_highs[-2] and last_lows[-1] > last_lows[-2]:
                return "bullish"
            # bearish if last high < prev high AND last low < prev low (LL & LH)
            if last_highs[-1] < last_highs[-2] and last_lows[-1] < last_lows[-2]:
                return "bearish"
    except Exception:
        pass

    return "neutral"

# === Find SNR zones from setup timeframe ===
def find_snr_zones(bars: List[Dict], lookback=200, zone_radius_pct=0.003) -> List[Dict]:
    """
    Return list of SNR zones (recent prominent swings).
    Each zone: {"type": "support"/"resistance", "price": value, "from_idx": i, "to_idx": j}
    zone_radius_pct defines how wide the zone is relative to price (e.g., 0.3%)
    """
    n = min(len(bars), lookback)
    recent = bars[-n:]
    zones = []
    # find local highs/lows by simple neighborhood
    window = 5
    for i in range(window, len(recent)-window):
        center = recent[i]
        left = recent[i-window:i]
        right = recent[i+1:i+1+window]
        # local high
        if center["h"] >= max(b["h"] for b in left) and center["h"] >= max(b["h"] for b in right):
            price = center["h"]
            radius = price * zone_radius_pct
            zones.append({"type":"resistance","price":price,"low":price-radius,"high":price+radius,"idx":i})
        # local low
        if center["l"] <= min(b["l"] for b in left) and center["l"] <= min(b["l"] for b in right):
            price = center["l"]
            radius = price * zone_radius_pct
            zones.append({"type":"support","price":price,"low":price-radius,"high":price+radius,"idx":i})
    # sort by recency (most recent first)
    zones.sort(key=lambda z: z["idx"], reverse=True)
    return zones

def nearest_snr_zone(zones: List[Dict], price: float, max_dist_pct=0.01) -> Optional[Dict]:
    """
    Return nearest zone if within max_dist_pct (e.g., 1%).
    """
    if not zones:
        return None
    best = None
    for z in zones:
        dist = abs(price - z["price"]) / z["price"]
        if dist <= max_dist_pct:
            if best is None or dist < best[0]:
                best = (dist, z)
    return best[1] if best else None

# === Detect Liquidity Sweep on trigger timeframe ===
def detect_liquidity_sweep(trigger_bars: List[Dict], prev_extreme_lookback=6) -> Optional[str]:
    """
    Simple rule:
      - Bullish sweep: a low that is below the minimum of the previous prev_extreme_lookback lows
        AND the candle closes back above that previous min (a rejection)
      - Bearish sweep: a high that is above the max of the previous prev_extreme_lookback highs
        AND the candle closes back below that previous max
    Returns "bullish_sweep" or "bearish_sweep" or None.
    """
    if len(trigger_bars) < prev_extreme_lookback + 1:
        return None
    recent = trigger_bars[-(prev_extreme_lookback+1):]
    prev = recent[:-1]
    curr = recent[-1]
    prev_min = min(b["l"] for b in prev)
    prev_max = max(b["h"] for b in prev)

    # bullish sweep: new low below prev_min then close above prev_min (reject)
    if curr["l"] < prev_min and curr["c"] > prev_min:
        return "bullish_sweep"

    # bearish sweep: new high above prev_max then close below prev_max (reject)
    if curr["h"] > prev_max and curr["c"] < prev_max:
        return "bearish_sweep"

    return None

# === Candle reaction / confirmation ===
def candle_rejection(curr: Dict, prev: Dict, wick_body_ratio=1.2) -> bool:
    """
    Return True if current candle shows a clear rejection or engulfing:
     - Bullish rejection: long lower wick relative to body OR bullish engulfing previous
     - Bearish rejection: long upper wick relative to body OR bearish engulfing previous
    This function does not consider direction; caller should compare close vs open for bull/bear.
    """
    # body sizes
    curr_body = abs(curr["c"] - curr["o"])
    prev_body = abs(prev["c"] - prev["o"])
    # wicks
    lower_wick = min(curr["o"], curr["c"]) - curr["l"]
    upper_wick = curr["h"] - max(curr["o"], curr["c"])

    # engulfing
    engulfing = (curr["c"] > curr["o"] and curr["c"] > prev["c"] and curr["o"] < prev["o"]) or \
                (curr["c"] < curr["o"] and curr["c"] < prev["c"] and curr["o"] > prev["o"])

    # strong wick rejection
    strong_lower_wick = lower_wick > curr_body * wick_body_ratio and curr["c"] > curr["o"]
    strong_upper_wick = upper_wick > curr_body * wick_body_ratio and curr["c"] < curr["o"]

    return bool(engulfing or strong_lower_wick or strong_upper_wick)

# === ATR helper for optional stops (simple) ===
def simple_atr(bars: List[Dict], period=14) -> Optional[float]:
    if len(bars) < period+1:
        return None
    trs = []
    for i in range(1, period+1):
        hi = bars[-i]["h"]
        lo = bars[-i]["l"]
        prev_close = bars[-i-1]["c"]
        tr = max(hi-lo, abs(hi-prev_close), abs(lo-prev_close))
        trs.append(tr)
    return sum(trs)/len(trs) if trs else None


# === The main signal function ===
def signal_lit_snr(
    ticker: str,
    bias_tf="HOUR_4",
    setup_tf="HOUR",
    trigger_tf="MINUTE_15",
    min_bars_bias=40,
    min_bars_setup=60,
    min_bars_trigger=8,
    snr_lookback=200,
    snr_zone_maxdist_pct=0.01,
    allow_neutral_if_no_bias=True,
) -> TradeSide:
    """
    Returns TradeSide.LONG / SHORT / NEUTRAL based on L.I.T + Malaysia SNR logic.
    """
    # --- fetch bars from memory, like your pipeline ---
    bias_bars = [b for b in memory.ohlc_history.get((ticker, bias_tf), []) if b.get("price_type","bid") == "bid"]
    setup_bars = [b for b in memory.ohlc_history.get((ticker, setup_tf), []) if b.get("price_type","bid") == "bid"]
    trigger_bars = [b for b in memory.ohlc_history.get((ticker, trigger_tf), []) if b.get("price_type","bid") == "bid"]

    # basic availability checks
    if len(bias_bars) < min_bars_bias or len(setup_bars) < min_bars_setup or len(trigger_bars) < min_bars_trigger:
        return TradeSide.NEUTRAL

    # --- Step 1: determine bias on H4 ---
    bias = market_structure_bias(bias_bars, swing_lookback=60)  # bullish / bearish / neutral
    if bias == "neutral" and allow_neutral_if_no_bias:
        return TradeSide.NEUTRAL

    # --- Step 2: find SNR zones on H1 and nearest zone to price ---
    zones = find_snr_zones(setup_bars, lookback=snr_lookback)
    current_price = last_price(trigger_bars)
    snr = nearest_snr_zone(zones, current_price, max_dist_pct=snr_zone_maxdist_pct)
    if snr is None:
        # no meaningful SNR nearby -> no trade
        return TradeSide.NEUTRAL

    # --- Step 3: detect liquidity sweep on trigger frame (M15) ---
    sweep = detect_liquidity_sweep(trigger_bars, prev_extreme_lookback=6)
    if sweep is None:
        return TradeSide.NEUTRAL

    # --- Step 4: confirmation candle rejection (compare last two trigger bars) ---
    confirmed = candle_rejection(trigger_bars[-1], trigger_bars[-2])
    if not confirmed:
        return TradeSide.NEUTRAL

    # --- Step 5: Combine rules with bias & snr type ---
    # bullish case
    if bias == "bullish" and snr["type"] == "support" and sweep == "bullish_sweep":
        return TradeSide.LONG

    # bearish case
    if bias == "bearish" and snr["type"] == "resistance" and sweep == "bearish_sweep":
        return TradeSide.SHORT

    # by default neutral
    return TradeSide.NEUTRAL





# === Optional: helper to produce trade params (stop/targets) ===
def generate_risk_parameters(trigger_bars: List[Dict], side: TradeSide, atr_period=14, atr_mult=1.5):
    """
    Suggests stop distance (price) and a sample target based on ATR and nearest swing.
    Returns (stop_price, suggested_target_price, stop_pips_or_amt)
    """
    if not trigger_bars:
        return (None, None, None)
    atr = simple_atr(trigger_bars[:-1], period=atr_period)  # use prior bars for ATR
    last = trigger_bars[-1]
    if atr is None:
        return (None, None, None)
    if side == TradeSide.LONG:
        stop_price = last["l"] - atr * atr_mult
        target = last["c"] + atr * atr_mult * 2  # example 1:2
        return (stop_price, target, abs(last["c"] - stop_price))
    if side == TradeSide.SHORT:
        stop_price = last["h"] + atr * atr_mult
        target = last["c"] - atr * atr_mult * 2
        return (stop_price, target, abs(last["c"] - stop_price))
    return (None, None, None)

