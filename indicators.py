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

    for i in range(len(candles)):
        candles[i]['rsi'] = rsi_vals[i]
        candles[i]['ma20'] = ma20_vals[i]
        candles[i]['ma50'] = ma50_vals[i]
        candles[i]['bb_lower'], candles[i]['bb_mid'], candles[i]['bb_upper'] = bb_vals[i]

    candles[-1]["sr_levels"] = detect_support_resistance(candles)

    return candles
