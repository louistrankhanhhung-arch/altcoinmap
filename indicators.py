import numpy as np

def sma(values, period):
    if len(values) < period:
        return [None] * len(values)
    return [None] * (period - 1) + [
        np.mean(values[i - period + 1:i + 1]) for i in range(period - 1, len(values))
    ]

def rsi(values, period=14):
    if len(values) < period:
        return [None] * len(values)

    deltas = np.diff(values)
    seed = deltas[:period]
    up = seed[seed > 0].sum() / period
    down = -seed[seed < 0].sum() / period
    rs = up / down if down != 0 else 0
    rsi_series = [100 - 100 / (1 + rs)]

    for delta in deltas[period:]:
        gain = max(delta, 0)
        loss = -min(delta, 0)
        up = (up * (period - 1) + gain) / period
        down = (down * (period - 1) + loss) / period
        rs = up / down if down != 0 else 0
        rsi_series.append(100 - 100 / (1 + rs))

    return [None] * period + rsi_series

def bollinger_bands(values, period=20):
    if len(values) < period:
        return [(None, None, None)] * len(values)

    bands = [(None, None, None)] * (period - 1)
    for i in range(period - 1, len(values)):
        window = values[i - period + 1:i + 1]
        mean = np.mean(window)
        std = np.std(window)
        upper = mean + 2 * std
        lower = mean - 2 * std
        bands.append((lower, mean, upper))
    return bands

def atr(candles, period=14):
    trs = []
    for i in range(1, len(candles)):
        high = candles[i]['high']
        low = candles[i]['low']
        prev_close = candles[i - 1]['close']
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)
    if len(trs) < period:
        return [None] * len(candles)
    atr_vals = [None] * (period - 1)
    atr_vals.append(np.mean(trs[:period]))
    for i in range(period, len(trs)):
        prev_atr = atr_vals[-1]
        new_atr = (prev_atr * (period - 1) + trs[i]) / period
        atr_vals.append(new_atr)
    return [None] + atr_vals  # align with candles

def detect_support_resistance(candles, window=20, tolerance=0.005):
    prices = [c["close"] for c in candles]
    levels = []
    for i in range(window, len(prices) - window):
        curr_price = prices[i]
        before = prices[i - window:i]
        after = prices[i + 1:i + 1 + window]

        if all(curr_price < x for x in before) and all(curr_price < x for x in after):
            levels.append((i, curr_price, 'support'))
        elif all(curr_price > x for x in before) and all(curr_price > x for x in after):
            levels.append((i, curr_price, 'resistance'))

    filtered = []
    for idx, price, level_type in levels:
        if not any(abs(price - p[1]) / price < tolerance for p in filtered if p[2] == level_type):
            filtered.append((idx, price, level_type))

    return filtered

def compute_indicators(candles):
    closes = [c['close'] for c in candles]

    rsi_vals = rsi(closes)
    ma20_vals = sma(closes, 20)
    ma50_vals = sma(closes, 50)
    bb_vals = bollinger_bands(closes, 20)
    atr_vals = atr(candles)

    for i in range(len(candles)):
        candles[i]['rsi'] = rsi_vals[i]
        candles[i]['ma20'] = ma20_vals[i]
        candles[i]['ma50'] = ma50_vals[i]
        candles[i]['bb_lower'], candles[i]['bb_mid'], candles[i]['bb_upper'] = bb_vals[i]
        candles[i]['atr'] = atr_vals[i]

    candles[-1]["sr_levels"] = detect_support_resistance(candles)

    return candles

def classify_trend(candles):
    if not candles or candles[-1].get("ma20") is None:
        return "unknown"
    price = candles[-1]["close"]
    ma20 = candles[-1]["ma20"]
    ma50 = candles[-1]["ma50"]

    if ma20 and ma50:
        if price > ma20 > ma50:
            return "uptrend"
        elif price < ma20 < ma50:
            return "downtrend"
        else:
            return "sideways"
    return "unknown"

def generate_take_profits(direction, entry_1, stop_loss, supports, resistances, trend_strength="moderate", confidence="medium"):
    levels = resistances if direction == "long" else supports
    unique_levels = []
    for lv in levels:
        if all(abs(lv - ulv) / ulv > 0.005 for ulv in unique_levels):
            unique_levels.append(lv)

    tps = []
    sorted_lv = sorted(unique_levels, reverse=(direction == "short"))
    for lv in sorted_lv:
        if (direction == "long" and lv > entry_1) or (direction == "short" and lv < entry_1):
            tps.append(round(lv, 2))
        if len(tps) >= 3:
            break

    allow_fib = (trend_strength in ["strong", "very_strong"]) and (confidence in ["medium", "high"])
    if allow_fib:
        risk_distance = abs(entry_1 - stop_loss)
        fib_ratios = [1.0, 1.618]
        for r in fib_ratios:
            ext = entry_1 + r * risk_distance if direction == "long" else entry_1 - r * risk_distance
            ext_rounded = round(ext, 2)
            if ext_rounded not in tps:
                tps.append(ext_rounded)

    tps = sorted(tps) if direction == "long" else sorted(tps, reverse=True)
    return tps[:5]

def generate_stop_loss(direction, entry_1, bb_lower, bb_upper, swing_low, swing_high, atr_val=None):
    sl = None
    if direction == "long":
        candidates = [val for val in [bb_lower, swing_low] if val is not None and val < entry_1]
        sl = min(candidates) if candidates else entry_1 * 0.98
        if atr_val:
            sl = min(sl, entry_1 - 1.5 * atr_val)
    elif direction == "short":
        candidates = [val for val in [bb_upper, swing_high] if val is not None and val > entry_1]
        sl = max(candidates) if candidates else entry_1 * 1.02
        if atr_val:
            sl = max(sl, entry_1 + 1.5 * atr_val)
    return round(sl, 2) if sl else round(entry_1 * 0.99, 2)
