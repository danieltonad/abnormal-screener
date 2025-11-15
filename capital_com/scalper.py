import numpy as np
from .utils import atr, ema, sma
from enums.trade import TradeSide
from .memory import memory


# === Utility Functions ===

def get_tf_trend_strength(ticker, timeframe, fast=20, slow=50, atr_period=14):
    """Measure higher timeframe trend strength as normalized EMA distance."""
    bars = memory.get_history(ticker, timeframe)
    if not bars or len(bars) < slow + 5:
        return 0.0

    bars = [b for b in bars if b["price_type"] == "bid"]
    c = np.array([b["c"] for b in bars], dtype=float)
    h = np.array([b["h"] for b in bars], dtype=float)
    l = np.array([b["l"] for b in bars], dtype=float)

    ema_fast_val = ema(c, fast)[-1]
    ema_slow_val = ema(c, slow)[-1]
    atr_now = atr(h, l, c, atr_period)[-1]
    if atr_now == 0 or np.isnan(atr_now):
        return 0.0

    return np.clip((ema_fast_val - ema_slow_val) / atr_now, -3.0, 3.0)


def estimate_dynamic_ema_periods(o, h, l, c, base_fast=9, base_slow=34, lookback=100):
    """
    Estimate EMA periods adaptively based on market structure:
    - Trendiness (directional persistence)
    - Candle efficiency (body/range)
    - Volatility ratio
    """
    returns = np.diff(c[-lookback:])
    abs_returns = np.abs(returns)
    trend_strength = np.abs(np.sum(returns)) / (np.sum(abs_returns) + 1e-8)

    true_ranges = np.maximum(h[-lookback:] - l[-lookback:], 1e-8)
    avg_range = np.mean(true_ranges)
    price_std = np.std(c[-lookback:])
    vol_ratio = np.clip(price_std / (avg_range + 1e-8), 0, 2)

    bodies = np.abs(c[-lookback:] - o[-lookback:])
    body_eff = np.mean(bodies / (true_ranges + 1e-8))

    structure_score = 0.5 * trend_strength + 0.3 * body_eff + 0.2 * vol_ratio
    structure_score = np.clip(structure_score, 0.05, 1.0)

    fast_mult = 1.0 - 0.4 * structure_score
    slow_mult = 1.0 - 0.2 * structure_score

    ema_fast = max(3, int(base_fast * fast_mult))
    ema_slow = max(ema_fast + 5, int(base_slow * slow_mult))

    return ema_fast, ema_slow, structure_score


def smooth_series(x, alpha=0.2):
    """Simple EMA smoother for ATR or score stability."""
    smoothed = np.zeros_like(x)
    smoothed[0] = x[0]
    for i in range(1, len(x)):
        smoothed[i] = alpha * x[i] + (1 - alpha) * smoothed[i - 1]
    return smoothed


# === Main Adaptive Scalper ===

def signal_scalper_robust(
    ticker: str,
    timeframe="MINUTE",
    higher_tfs=("MINUTE_5", "MINUTE_15"),
    min_history=150,
    base_fast=9,
    base_slow=34,
    atr_period=14,
    atr_long=50,
    higher_tf_weight=0.5,
    min_hold_bars=3,  # prevent flip-flopping
):
    """Robust adaptive scalper using OHLC-structure tuning + multi-TF bias."""

    bars = [b for b in memory.get_history(ticker, timeframe) if b["price_type"] == "bid"]
    if len(bars) < min_history:
        return TradeSide.NEUTRAL

    o = np.array([b["o"] for b in bars], dtype=float)
    h = np.array([b["h"] for b in bars], dtype=float)
    l = np.array([b["l"] for b in bars], dtype=float)
    c = np.array([b["c"] for b in bars], dtype=float)

    # --- Adaptive EMA tuning from OHLC lookback ---
    ema_fast, ema_slow, structure_score = estimate_dynamic_ema_periods(o, h, l, c, base_fast, base_slow)

    # --- Multi-timeframe trend confirmation (cached if possible) ---
    tf_strengths = [get_tf_trend_strength(ticker, tf) for tf in higher_tfs]
    avg_tf_strength = np.mean(tf_strengths)
    avg_tf_strength = np.clip(avg_tf_strength, -3.0, 3.0)

    # --- Core Indicators ---
    ema_fast_val = ema(c, ema_fast)[-1]
    ema_slow_val = ema(c, ema_slow)[-1]

    atr_vals = atr(h, l, c, atr_period)
    atr_now = smooth_series(atr_vals, alpha=0.25)[-1]
    atr_long_avg = sma(list(atr_vals[-atr_long:]), atr_long)

    if atr_now is None or atr_long_avg is None or atr_long_avg == 0:
        return TradeSide.NEUTRAL

    # --- Derived metrics ---
    trend = (ema_fast_val - ema_slow_val) / atr_now
    momentum = (c[-1] - c[-4]) / atr_now
    wick_top = (h[-1] - max(o[-1], c[-1])) / atr_now
    wick_bot = (min(o[-1], c[-1]) - l[-1]) / atr_now
    wick_imb = 0 if (wick_top + wick_bot) == 0 else (wick_top - wick_bot) / (wick_top + wick_bot)

    vol_regime = max(min(atr_now / atr_long_avg, 2.5), 0.4)  # tighter cap

    # --- Weighted score ---
    w_trend, w_mom, w_wick = 0.6, 0.3, 0.1
    if vol_regime < 0.8:
        w_trend *= 0.6
        w_mom *= 0.6

    base_score = (w_trend * trend + w_mom * momentum - w_wick * wick_imb) / vol_regime

    # --- Higher-TF bias integration (dynamic weighting) ---
    higher_tf_conf = 1.0 - np.exp(-abs(avg_tf_strength))  # stronger TF → more weight
    weight = higher_tf_weight * higher_tf_conf
    score = (1 - weight) * base_score + weight * avg_tf_strength

    # --- Adaptive thresholds ---
    base_thresh = 0.18 * (1.0 + 0.4 * (1 - structure_score))
    up_thresh = base_thresh / vol_regime
    down_thresh = -up_thresh

    # --- Market quiet/chop filter ---
    if (vol_regime < 0.7 and abs(score) < 0.3) or structure_score < 0.15:
        return TradeSide.NEUTRAL

    # --- Confirmation: candle close only (no intrabar flip) ---
    # Assuming this function is called per new closed candle
    # Add a simple state memory to prevent immediate flip-flop
    prev_signal = getattr(signal_scalper_robust, "_last_signal", TradeSide.NEUTRAL)
    prev_count = getattr(signal_scalper_robust, "_hold_count", 0)

    if score > up_thresh and avg_tf_strength > 0:
        signal = TradeSide.LONG
    elif score < down_thresh and avg_tf_strength < 0:
        signal = TradeSide.SHORT
    else:
        signal = TradeSide.NEUTRAL

    # --- Hold filter ---
    if signal != prev_signal:
        if prev_count < min_hold_bars and prev_signal != TradeSide.NEUTRAL:
            # Maintain previous direction until hold expires
            signal = prev_signal
            prev_count += 1
        else:
            prev_count = 0
    else:
        prev_count = min_hold_bars  # reset counter if consistent

    # store state
    signal_scalper_robust._last_signal = signal
    signal_scalper_robust._hold_count = prev_count

    return signal
