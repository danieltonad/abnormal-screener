from enums.trade import TradeSide
from typing import List, Dict, Optional, Tuple, Any
from .memory import memory
import math

# === Utility helpers ===
def is_number(x) -> bool:
    return isinstance(x, (int, float)) and not (x is None or (isinstance(x, float) and math.isnan(x)))

def safe_get_num(b: Dict, key: str, default: Optional[float] = None) -> Optional[float]:
    v = b.get(key, default)
    return v if is_number(v) else default

def tail(bars: List[Dict], n: int) -> List[Dict]:
    return bars[-n:] if len(bars) >= n else bars[:]

def high_of(bars: List[Dict]) -> Optional[float]:
    values = [safe_get_num(b, "h") for b in bars]
    values = [v for v in values if is_number(v)]
    return max(values) if values else None

def low_of(bars: List[Dict]) -> Optional[float]:
    values = [safe_get_num(b, "l") for b in bars]
    values = [v for v in values if is_number(v)]
    return min(values) if values else None

def last_price(bars: List[Dict]) -> Optional[float]:
    if not bars:
        return None
    return safe_get_num(bars[-1], "c")

# === Market Structure Bias (H4) ===
def market_structure_bias(bars: List[Dict], swing_lookback=20) -> str:
    """
    Very simple structure detector:
     - find sequence of swing highs and swing lows (local peaks/troughs)
     - if last two swings show HH/HL -> bullish; LL/LH -> bearish
     - else neutral

    Returns one of: "bullish", "bearish", "neutral"
    """
    n = min(len(bars), swing_lookback)
    if n < 6:
        return "neutral"

    highs = []
    lows = []
    # detect local peaks/troughs by simple comparison with neighbors (requires numeric safety)
    for i in range(2, n-2):
        center = bars[-n + i]
        prev1 = bars[-n + i - 1]
        next1 = bars[-n + i + 1]

        ch = safe_get_num(center, "h")
        ph = safe_get_num(prev1, "h")
        nh = safe_get_num(next1, "h")
        cl = safe_get_num(center, "l")
        pl = safe_get_num(prev1, "l")
        nl = safe_get_num(next1, "l")

        if ch is None or ph is None or nh is None or cl is None or pl is None or nl is None:
            continue

        if ch > ph and ch > nh:
            highs.append((ch, center.get("t")))
        if cl < pl and cl < nl:
            lows.append((cl, center.get("t")))

    # build combined chronological swings keyed by time
    swings = []
    for h, p in highs:
        swings.append(("H", p, h))
    for l, p in lows:
        swings.append(("L", p, l))

    # require timestamps to sort; if missing, use insertion order as fallback
    swings.sort(key=lambda x: (x[1] is None, x[1]))  # place None at end but keep stable

    # compress to last few swings
    swings = swings[-6:]

    # need at least a couple of highs and lows to compare
    last_highs = [v for typ, _, v in swings if typ == "H"]
    last_lows = [v for typ, _, v in swings if typ == "L"]

    if len(last_highs) < 2 or len(last_lows) < 2:
        return "neutral"

    # bullish if last high > prev high AND last low > prev low (HH & HL)
    try:
        if last_highs[-1] > last_highs[-2] and last_lows[-1] > last_lows[-2]:
            return "bullish"
        # bearish if last high < prev high AND last low < prev low (LL & LH)
        if last_highs[-1] < last_highs[-2] and last_lows[-1] < last_lows[-2]:
            return "bearish"
    except Exception:
        # fallback to neutral rather than silently breaking
        return "neutral"

    return "neutral"

# === Find SNR zones from setup timeframe ===
def find_snr_zones(bars: List[Dict], lookback=200, zone_radius_pct=0.003, merge_pct=0.001) -> List[Dict]:
    """
    Return list of SNR zones (recent prominent swings).
    Each zone: {"type": "support"/"resistance", "price": value, "low": low_price, "high": high_price, "idx": i}
    zone_radius_pct defines how wide the zone is relative to price (e.g., 0.3%)
    merge_pct: if two zones are within merge_pct relative difference, they will be merged/filtered
    """
    n = min(len(bars), lookback)
    recent = bars[-n:]
    zones: List[Dict] = []
    window = 5
    if len(recent) < window * 2 + 1:
        return zones

    for i in range(window, len(recent)-window):
        center = recent[i]
        left = recent[i-window:i]
        right = recent[i+1:i+1+window]

        ch = safe_get_num(center, "h")
        cl = safe_get_num(center, "l")
        if ch is None or cl is None:
            continue

        try:
            left_max_h = max(safe_get_num(b, "h") or float("-inf") for b in left)
            right_max_h = max(safe_get_num(b, "h") or float("-inf") for b in right)
            left_min_l = min(safe_get_num(b, "l") or float("inf") for b in left)
            right_min_l = min(safe_get_num(b, "l") or float("inf") for b in right)
        except Exception:
            continue

        # local high -> resistance
        if ch >= left_max_h and ch >= right_max_h:
            price = ch
            if not is_number(price) or price == 0:
                continue
            radius = price * zone_radius_pct
            zones.append({"type":"resistance","price":price,"low":price-radius,"high":price+radius,"idx":i})

        # local low -> support
        if cl <= left_min_l and cl <= right_min_l:
            price = cl
            if not is_number(price) or price == 0:
                continue
            radius = price * zone_radius_pct
            zones.append({"type":"support","price":price,"low":price-radius,"high":price+radius,"idx":i})

    # sort by recency (most recent first)
    zones.sort(key=lambda z: z["idx"], reverse=True)

    # merge/filter near-duplicate zones (by relative price distance)
    merged: List[Dict] = []
    for z in zones:
        if not merged:
            merged.append(z)
            continue
        last = merged[-1]
        # relative distance
        if abs(z["price"] - last["price"]) / max(abs(last["price"]), 1e-12) <= merge_pct and z["type"] == last["type"]:
            # merge by keeping the more recent index and expanding low/high
            merged[-1] = {
                "type": last["type"],
                "price": (last["price"] + z["price"]) / 2,
                "low": min(last["low"], z["low"]),
                "high": max(last["high"], z["high"]),
                "idx": max(last["idx"], z["idx"]),
            }
        else:
            merged.append(z)

    return merged

def nearest_snr_zone(zones: List[Dict], price: float, max_dist_pct=0.01) -> Optional[Dict]:
    """
    Return nearest zone if within max_dist_pct (e.g., 1%).
    """
    if not zones or not is_number(price):
        return None
    best = None
    for z in zones:
        zp = z.get("price")
        if not is_number(zp) or zp == 0:
            continue
        dist = abs(price - zp) / zp
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

    # ensure all prev have valid highs/lows
    prev_lows = [safe_get_num(b, "l") for b in prev]
    prev_highs = [safe_get_num(b, "h") for b in prev]
    if not all(is_number(x) for x in prev_lows) or not all(is_number(x) for x in prev_highs):
        return None

    prev_min = min(prev_lows)
    prev_max = max(prev_highs)

    curr_l = safe_get_num(curr, "l")
    curr_h = safe_get_num(curr, "h")
    curr_c = safe_get_num(curr, "c")
    if curr_l is None or curr_h is None or curr_c is None:
        return None

    # bullish sweep: new low below prev_min then close above prev_min (reject)
    if curr_l < prev_min and curr_c > prev_min:
        return "bullish_sweep"

    # bearish sweep: new high above prev_max then close below prev_max (reject)
    if curr_h > prev_max and curr_c < prev_max:
        return "bearish_sweep"

    return None

# === Candle reaction / confirmation ===
def candle_rejection(curr: Dict, prev: Dict, wick_body_ratio=1.2, min_body_absolute=1e-8) -> bool:
    """
    Return True if current candle shows a clear rejection or engulfing:
     - Bullish rejection: long lower wick relative to body OR bullish engulfing previous
     - Bearish rejection: long upper wick relative to body OR bearish engulfing previous

    This function does not consider direction; caller should compare close vs open for bull/bear.
    """
    curr_o = safe_get_num(curr, "o")
    curr_c = safe_get_num(curr, "c")
    curr_h = safe_get_num(curr, "h")
    curr_l = safe_get_num(curr, "l")
    prev_o = safe_get_num(prev, "o")
    prev_c = safe_get_num(prev, "c")

    if not all(is_number(x) for x in (curr_o, curr_c, curr_h, curr_l, prev_o, prev_c)):
        return False

    curr_body = abs(curr_c - curr_o)
    prev_body = abs(prev_c - prev_o)

    # ignore candles with near-zero body to avoid doji false positives
    if curr_body < min_body_absolute:
        return False

    lower_wick = min(curr_o, curr_c) - curr_l
    upper_wick = curr_h - max(curr_o, curr_c)

    # engulfing
    engulfing = False
    if curr_c > curr_o and curr_c > prev_c and curr_o < prev_o:
        engulfing = True
    if curr_c < curr_o and curr_c < prev_c and curr_o > prev_o:
        engulfing = True

    strong_lower_wick = lower_wick > curr_body * wick_body_ratio and curr_c > curr_o
    strong_upper_wick = upper_wick > curr_body * wick_body_ratio and curr_c < curr_o

    return bool(engulfing or strong_lower_wick or strong_upper_wick)

# === ATR helper for optional stops (simple) ===
def simple_atr(bars: List[Dict], period=14) -> Optional[float]:
    """
    Compute ATR using the last `period` bars (excluding the most recent if that's intended).
    Returns None if insufficient or invalid data.
    """
    if len(bars) < period + 1:
        return None
    trs = []
    # compute true ranges using backwards indexing safely
    for i in range(1, period+1):
        hi = safe_get_num(bars[-i], "h")
        lo = safe_get_num(bars[-i], "l")
        prev_close = safe_get_num(bars[-i-1], "c")
        if not all(is_number(v) for v in (hi, lo, prev_close)):
            return None
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
    debug: bool = False,
) -> Any:
    """
    Returns TradeSide.LONG / SHORT / NEUTRAL based on L.I.T + Malaysia SNR logic.

    If debug=True, returns (TradeSide, diagnostics_dict) where diagnostics_dict explains
    why the signal was produced (useful for testing/backtesting).
    """
    diagnostics = {"ticker": ticker, "steps": []}

    # --- fetch bars from memory, like your pipeline ---
    raw_bias = memory.get_history(ticker, bias_tf, 200) or []
    raw_setup = memory.get_history(ticker, setup_tf, 200) or []
    raw_trigger = memory.get_history(ticker, trigger_tf, 200) or []

    # optionally filter by price_type but fallback to all if filtering removes everything
    bias_bars = [b for b in raw_bias if b.get("price_type", "bid") == "bid"] or raw_bias
    setup_bars = [b for b in raw_setup if b.get("price_type", "bid") == "bid"] or raw_setup
    trigger_bars = [b for b in raw_trigger if b.get("price_type", "bid") == "bid"] or raw_trigger

    diagnostics["counts"] = {
        "bias_bars": len(bias_bars),
        "setup_bars": len(setup_bars),
        "trigger_bars": len(trigger_bars),
    }

    # basic availability checks
    if len(bias_bars) < min_bars_bias or len(setup_bars) < min_bars_setup or len(trigger_bars) < min_bars_trigger:
        diagnostics["steps"].append("insufficient_bars")
        if debug:
            return TradeSide.NEUTRAL, diagnostics
        return TradeSide.NEUTRAL

    # --- Step 1: determine bias on H4 ---
    bias = market_structure_bias(bias_bars, swing_lookback=60)  # bullish / bearish / neutral
    diagnostics["bias"] = bias
    if bias == "neutral" and allow_neutral_if_no_bias:
        diagnostics["steps"].append("neutral_bias")
        if debug:
            return TradeSide.NEUTRAL, diagnostics
        return TradeSide.NEUTRAL

    # --- Step 2: find SNR zones on H1 and nearest zone to price ---
    zones = find_snr_zones(setup_bars, lookback=snr_lookback)
    diagnostics["zones_found"] = len(zones)
    current_price = last_price(trigger_bars)
    diagnostics["current_price"] = current_price
    snr = nearest_snr_zone(zones, current_price, max_dist_pct=snr_zone_maxdist_pct) if current_price is not None else None
    diagnostics["snr_nearby"] = bool(snr)
    diagnostics["snr"] = snr

    if snr is None:
        diagnostics["steps"].append("no_snr_nearby")
        if debug:
            return TradeSide.NEUTRAL, diagnostics
        return TradeSide.NEUTRAL

    # --- Step 3: detect liquidity sweep on trigger frame (M15) ---
    sweep = detect_liquidity_sweep(trigger_bars, prev_extreme_lookback=6)
    diagnostics["sweep"] = sweep
    if sweep is None:
        diagnostics["steps"].append("no_sweep")
        if debug:
            return TradeSide.NEUTRAL, diagnostics
        return TradeSide.NEUTRAL

    # --- Step 4: confirmation candle rejection (compare last two trigger bars) ---
    # ensure we have at least 2 trigger bars
    if len(trigger_bars) < 2:
        diagnostics["steps"].append("insufficient_trigger_bars_for_confirmation")
        if debug:
            return TradeSide.NEUTRAL, diagnostics
        return TradeSide.NEUTRAL

    confirmed = candle_rejection(trigger_bars[-1], trigger_bars[-2])
    diagnostics["confirmed"] = confirmed
    if not confirmed:
        diagnostics["steps"].append("no_confirmation_rejection")
        if debug:
            return TradeSide.NEUTRAL, diagnostics
        return TradeSide.NEUTRAL

    # --- Step 5: Combine rules with bias & snr type ---
    result = TradeSide.NEUTRAL
    reason = None
    # bullish case
    if bias == "bullish" and snr.get("type") == "support" and sweep == "bullish_sweep":
        result = TradeSide.LONG
        reason = "bias_bullish + support + bullish_sweep + confirmed"
    # bearish case
    elif bias == "bearish" and snr.get("type") == "resistance" and sweep == "bearish_sweep":
        result = TradeSide.SHORT
        reason = "bias_bearish + resistance + bearish_sweep + confirmed"
    else:
        diagnostics["steps"].append("rules_not_satisfied_for_bias_snr_sweep_combo")

    diagnostics["result_reason"] = reason
    diagnostics["result"] = result

    if debug:
        return result, diagnostics
    return result

# === Optional: helper to produce trade params (stop/targets) ===
def generate_risk_parameters(trigger_bars: List[Dict], side: TradeSide, atr_period=14, atr_mult=1.5):
    """
    Suggests stop distance (price) and a sample target based on ATR and nearest swing.
    Returns (stop_price, suggested_target_price, stop_pips_or_amt)
    """
    if not trigger_bars:
        return (None, None, None)
    # use prior bars for ATR (exclude last)
    atr = simple_atr(trigger_bars[:-1], period=atr_period)
    last = trigger_bars[-1]
    if atr is None or not is_number(atr) or atr <= 0:
        return (None, None, None)

    last_c = safe_get_num(last, "c")
    last_l = safe_get_num(last, "l")
    last_h = safe_get_num(last, "h")
    if not all(is_number(v) for v in (last_c, last_l, last_h)):
        return (None, None, None)

    if side == TradeSide.LONG:
        stop_price = last_l - atr * atr_mult
        # ensure stop is sensible (not negative)
        if stop_price <= 0:
            stop_price = max(1e-8, last_c - atr * atr_mult)
        target = last_c + atr * atr_mult * 2  # example 1:2
        return (stop_price, target, abs(last_c - stop_price))
    if side == TradeSide.SHORT:
        stop_price = last_h + atr * atr_mult
        if stop_price <= 0:
            stop_price = max(1e-8, last_c + atr * atr_mult)
        target = last_c - atr * atr_mult * 2
        return (stop_price, target, abs(last_c - stop_price))
    return (None, None, None)
