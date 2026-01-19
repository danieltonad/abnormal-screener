import numpy as np
import pandas as pd
from memory import memory
from enums.trade import TradeSide


def atr_from_df_v2(df, period=14, smooth=3):
    highs = df["h"].values
    lows  = df["l"].values
    closes = df["c"].values

    tr = np.maximum(
        highs - lows,
        np.maximum(
            np.abs(highs - np.roll(closes, 1)),
            np.abs(lows - np.roll(closes, 1))
        )
    )
    tr[0] = highs[0] - lows[0]

    atr = pd.Series(tr).rolling(period).mean()

    if smooth > 1:
        atr = atr.ewm(span=smooth, adjust=False).mean()

    val = atr.iloc[-1]
    return None if np.isnan(val) or val == 0 else val



# ATR (smoothed, CFD-safe)
def build_sr_zones(
    df,
    atr,
    swing_lookback=10,
    zone_mult=0.75,
    max_zones=3,
):
    highs = df["h"].values
    lows  = df["l"].values
    closes = df["c"].values

    zone_width = atr * zone_mult

    swing_highs = []
    swing_lows  = []

    for i in range(swing_lookback, len(df) - swing_lookback):
        if highs[i] == max(highs[i - swing_lookback:i + swing_lookback]):
            swing_highs.append(closes[i])

        if lows[i] == min(lows[i - swing_lookback:i + swing_lookback]):
            swing_lows.append(closes[i])

    def cluster(levels):
        clusters = []
        for lvl in sorted(levels):
            added = False
            for c in clusters:
                if abs(lvl - c[0]) <= zone_width:
                    c.append(lvl)
                    added = True
                    break
            if not added:
                clusters.append([lvl])
        return clusters

    support_clusters = cluster(swing_lows)
    resistance_clusters = cluster(swing_highs)

    support_zones = [
        (min(c) - zone_width / 2, max(c) + zone_width / 2)
        for c in support_clusters
    ]

    resistance_zones = [
        (min(c) - zone_width / 2, max(c) + zone_width / 2)
        for c in resistance_clusters
    ]

    return support_zones[-max_zones:], resistance_zones[-max_zones:]


# Support & Resistance Zones (ATR-scaled)
# def build_sr_zones(
#     df,
#     atr,
#     swing_lookback=10,
#     zone_mult=0.75,
#     max_zones=3,
# ):
#     highs = df["h"].values
#     lows  = df["l"].values
#     closes = df["c"].values

#     zone_width = atr * zone_mult

#     swing_highs = []
#     swing_lows  = []

#     for i in range(swing_lookback, len(df) - swing_lookback):
#         if highs[i] == max(highs[i - swing_lookback:i + swing_lookback]):
#             swing_highs.append(closes[i])

#         if lows[i] == min(lows[i - swing_lookback:i + swing_lookback]):
#             swing_lows.append(closes[i])

#     def cluster(levels):
#         clusters = []
#         for lvl in sorted(levels):
#             added = False
#             for c in clusters:
#                 if abs(lvl - c[0]) <= zone_width:
#                     c.append(lvl)
#                     added = True
#                     break
#             if not added:
#                 clusters.append([lvl])
#         return clusters

#     support_clusters = cluster(swing_lows)
#     resistance_clusters = cluster(swing_highs)

#     support_zones = [
#         (min(c) - zone_width / 2, max(c) + zone_width / 2)
#         for c in support_clusters
#     ]

#     resistance_zones = [
#         (min(c) - zone_width / 2, max(c) + zone_width / 2)
#         for c in resistance_clusters
#     ]

#     return support_zones[-max_zones:], resistance_zones[-max_zones:]




def breaks_resistance(price, zones, buffer):
    return any(price > high + buffer for _, high in zones)

def breaks_support(price, zones, buffer):
    return any(price < low - buffer for low, _ in zones)

def loses_support(price, zones):
    return any(price < low for low, _ in zones)

def loses_resistance(price, zones):
    return any(price > high for _, high in zones)









def signal_atr_sr_breakout(
    ticker: str,
    timeframe="30MIN",
    atr_period=14,
    atr_mult=1.0,
    ema_period=21,
    swing_lookback=10,
):
    bars = [b for b in memory.get_history(ticker, timeframe)]
    min_required = max(atr_period, ema_period, swing_lookback) + 30
    if len(bars) < min_required:
        return TradeSide.NEUTRAL

    df = pd.DataFrame(bars)
    closes = df["c"].values

    # ---- ATR ----
    atr = atr_from_df_v2(df, atr_period)
    if atr is None:
        return TradeSide.NEUTRAL

    buffer = atr_mult * atr
    exit_buffer = 0.4 * atr

    # ---- EMA trend ----
    ema_vals = ema(closes, ema_period)
    last_close = closes[-1]
    current_ema = ema_vals[-1]

    trend_up = last_close > current_ema
    trend_down = last_close < current_ema

    # ---- Support / Resistance zones ----
    support_zones, resistance_zones = build_sr_zones(
        df,
        atr,
        swing_lookback=swing_lookback,
        zone_mult=0.75,
    )

    # ---- ENTRY ----
    if trend_up and breaks_resistance(last_close, resistance_zones, buffer):
        return TradeSide.LONG

    if trend_down and breaks_support(last_close, support_zones, buffer):
        return TradeSide.SHORT

    # ---- INFER LAST DIRECTION ----
    recent_direction = None
    lookback = swing_lookback * 3

    for i in range(-lookback, -1):
        if closes[i] > ema_vals[i]:
            if breaks_resistance(closes[i], resistance_zones, buffer):
                recent_direction = TradeSide.LONG
                break

        if closes[i] < ema_vals[i]:
            if breaks_support(closes[i], support_zones, buffer):
                recent_direction = TradeSide.SHORT
                break

    # ---- EXIT ----
    if recent_direction == TradeSide.LONG:
        if last_close < current_ema - exit_buffer or loses_support(last_close, support_zones):
            return TradeSide.EXIT_LONG

    if recent_direction == TradeSide.SHORT:
        if last_close > current_ema + exit_buffer or loses_resistance(last_close, resistance_zones):
            return TradeSide.EXIT_SHORT

    return TradeSide.NEUTRAL
