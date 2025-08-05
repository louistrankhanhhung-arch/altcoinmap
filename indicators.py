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
    return [None] + atr_vals

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

def generate_entries(price, atr_val, direction="long", ma20=None, rsi=None, sr_levels=[]):
    nearest_supports = sorted([lvl for _, lvl, typ in sr_levels if typ == 'support'], reverse=True)
    nearest_resistances = sorted([lvl for _, lvl, typ in sr_levels if typ == 'resistance'])

    entry_1 = price
    if direction == "long":
        for lvl in nearest_supports:
            if lvl < price:
                entry_1 = lvl
                break
    else:
        for lvl in nearest_resistances:
            if lvl > price:
                entry_1 = lvl
                break

    if not entry_1:
        entry_1 = round(price, 2)

    if direction == "long":
        entry_2 = entry_1 - min(1.5 * atr_val, 0.02 * entry_1)
    else:
        entry_2 = entry_1 + min(1.5 * atr_val, 0.02 * entry_1)

    # Giới hạn chênh lệch entry không quá 5%
    max_gap_pct = 0.05
    if abs(entry_1 - entry_2) / entry_1 > max_gap_pct:
        if direction == "long":
            entry_2 = entry_1 * (1 - max_gap_pct)
        else:
            entry_2 = entry_1 * (1 + max_gap_pct)

    return round(entry_1, 4), round(entry_2, 4)

def generate_stop_loss(direction, entry_1, bb_lower, bb_upper, swing_low, swing_high, atr_val, entry_2):
    if direction == "long":
        sl = min(entry_2 - 1.5 * atr_val, bb_lower or entry_2, swing_low or entry_2)
        if sl > entry_2:
            sl = entry_2 - 0.5 * atr_val
    else:
        sl = max(entry_2 + 1.5 * atr_val, bb_upper or entry_2, swing_high or entry_2)
        if sl < entry_2:
            sl = entry_2 + 0.5 * atr_val
    return round(sl, 4)

def generate_take_profits(direction, entry_1, stop_loss, supports, resistances, trend_strength="moderate", confidence="medium"):
    tps = []
    rr_min = 1.2
    if direction == "long":
        base_tp = entry_1 + (entry_1 - stop_loss) * rr_min
        levels = sorted([lvl for lvl in resistances if lvl > entry_1])
        if base_tp not in levels:
            levels.insert(0, round(base_tp, 2))
        tps = levels[:5]
    else:
        base_tp = entry_1 - (stop_loss - entry_1) * rr_min
        levels = sorted([lvl for lvl in supports if lvl < entry_1], reverse=True)
        if base_tp not in levels:
            levels.insert(0, round(base_tp, 2))
        tps = levels[:5]

    # Lọc TP nếu vượt quá 10% so với Entry1
    max_tp_pct = 0.1
    filtered = [tp for tp in tps if abs(tp - entry_1) / entry_1 <= max_tp_pct]
    return filtered[:5] if filtered else tps[:3]
