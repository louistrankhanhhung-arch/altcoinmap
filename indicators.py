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

def detect_support_resistance(candles, window=20, tol_atr_mul=0.6):
    """
    Pivot HH/LL dựa trên high/low, gom cụm theo ngưỡng tol ~ ATR.
    Trả về [(idx, price, 'support'|'resistance')].
    """
    if not candles or len(candles) < window * 2 + 3:
        return []

    highs = [c["high"] for c in candles]
    lows  = [c["low"]  for c in candles]
    atrs  = [c.get("atr") for c in candles]
    atr_ref = None
    hist_atr = [x for x in atrs[-(window*2+50):] if x is not None]
    if hist_atr:
        atr_ref = sum(hist_atr) / len(hist_atr)

    levels = []
    n = len(candles)
    for i in range(window, n - window):
        h = highs[i]; l = lows[i]
        left_h  = max(highs[i-window:i]) if i-window>=0 else None
        right_h = max(highs[i+1:i+1+window]) if i+1+window<=n else None
        left_l  = min(lows[i-window:i]) if i-window>=0 else None
        right_l = min(lows[i+1:i+1+window]) if i+1+window<=n else None

        # pivot high / pivot low
        if left_h is not None and right_h is not None and h >= left_h and h >= right_h:
            levels.append((i, h, 'resistance'))
        if left_l is not None and right_l is not None and l <= left_l and l <= right_l:
            levels.append((i, l, 'support'))

    # gom cụm theo tolerance dựa trên ATR (fallback 0.5% nếu thiếu ATR)
    filtered = []
    def too_close(p, q):
        if atr_ref and atr_ref > 0:
            return abs(p - q) < tol_atr_mul * atr_ref
        # fallback %
        return abs(p - q) / ((p+q)/2.0) < 0.005

    for idx, price, typ in sorted(levels, key=lambda x: x[1]):
        merged = False
        for j, (ii, pp, tt) in enumerate(filtered):
            if tt == typ and too_close(price, pp):
                # giữ mức “mạnh” hơn bằng cách chọn xa giá hiện tại hơn
                filtered[j] = (idx, (pp + price)/2.0, typ)
                merged = True
                break
        if not merged:
            filtered.append((idx, price, typ))

    return filtered
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

def generate_suggested_tps(entry_1, direction, sr_levels, atr_val=None,
                           min_atr_mul=0.8, min_step_atr=0.5, max_levels=5):
    """
    Lọc SR quá gần bằng ATR, đảm bảo khoảng cách tối thiểu giữa các TP.
    Nếu thiếu, sinh TP tổng hợp theo bội số ATR.
    """
    if atr_val is None or atr_val <= 0:
        atr_val = None  # cho fallback theo % nếu cần

    supports    = [lvl for _, lvl, typ in sr_levels if typ == 'support']
    resistances = [lvl for _, lvl, typ in sr_levels if typ == 'resistance']

    raw_levels = []
    if direction == "long":
        raw_levels = sorted([lvl for lvl in resistances if lvl > entry_1])
    else:
        raw_levels = sorted([lvl for lvl in supports if lvl < entry_1], reverse=True)

    def far_enough(a, b):
        if atr_val:
            return abs(a - b) >= min_step_atr * atr_val
        return abs(a - b) / ((a+b)/2.0) >= 0.004  # fallback ~0.4%

    # lọc mức quá gần entry
    levels = []
    for lvl in raw_levels:
        if atr_val:
            if abs(lvl - entry_1) < min_atr_mul * atr_val:
                continue
        else:
            if abs(lvl - entry_1) / entry_1 < 0.006:  # ~0.6% nếu thiếu ATR
                continue
        if not levels or far_enough(lvl, levels[-1]):
            levels.append(lvl)
        if len(levels) >= max_levels:
            break

    # nếu thiếu thì sinh TP tổng hợp theo ATR
    if len(levels) < max_levels:
        if atr_val:
            muls = [1.0, 1.5, 2.0, 3.0, 4.0]
            synth = []
            for m in muls:
                tp = entry_1 + (m * atr_val if direction == "long" else -m * atr_val)
                # bỏ TP quá gần entry
                if abs(tp - entry_1) < min_atr_mul * (atr_val or 1):
                    continue
                if not levels or far_enough(tp, (levels + synth)[-1]):
                    synth.append(tp)
                if len(levels) + len(synth) >= max_levels:
                    break
            levels += synth

    return [round(x, 4) for x in levels[:max_levels]]
    resistances = [lvl for _, lvl, typ in sr_levels if typ == 'resistance']
    if direction == "long":
        levels = sorted([lvl for lvl in resistances if lvl > entry_1])
    else:
        levels = sorted([lvl for lvl in supports if lvl < entry_1], reverse=True)
    return levels[:5]

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


def compute_short_term_momentum(candles_1h, lookback=20, pct_window=1):
    """
    Tính các thước đo động lượng ngắn hạn trên khung 1H để phát hiện breakout intraday.
    Trả về dict với 4 trường:
      - pct_change_1h: % thay đổi giá của nến gần nhất so với pct_window nến trước (mặc định 1 nến = 1h).
      - bb_width_ratio: tỉ lệ độ rộng Bollinger Bands (nến cuối) so với trung bình lookback.
      - atr_spike_ratio: ATR(nến cuối) / ATR trung bình lookback.
      - volume_spike_ratio: khối lượng(nến cuối) / khối lượng trung bình lookback.
    """
    if not candles_1h or len(candles_1h) < max(lookback+2, 22):
        return {
            "pct_change_1h": None,
            "bb_width_ratio": None,
            "atr_spike_ratio": None,
            "volume_spike_ratio": None
        }

    closes = [c["close"] for c in candles_1h]
    last_close = closes[-1]
    prev_idx = -1 - max(1, pct_window)
    prev_close = closes[prev_idx]

    try:
        pct_change_1h = (last_close - prev_close) / prev_close * 100.0 if prev_close else None
    except Exception:
        pct_change_1h = None

    # Chuẩn bị BB width series (ưu tiên dùng bb có sẵn nếu đã tính)
    bb_width_series = []
    for c in candles_1h:
        lo = c.get("bb_lower")
        up = c.get("bb_upper")
        mid = c.get("bb_mid") or c.get("ma20") or c.get("close")
        if lo is None or up is None or mid is None or mid == 0:
            bb_width_series.append(None)
        else:
            bb_width_series.append((up - lo) / mid)

    last_bb_width = bb_width_series[-1] if bb_width_series else None
    hist_bb = [x for x in bb_width_series[-(lookback+1):-1] if x is not None]
    bb_width_avg = sum(hist_bb) / len(hist_bb) if hist_bb else None
    bb_width_ratio = (last_bb_width / bb_width_avg) if (last_bb_width and bb_width_avg and bb_width_avg != 0) else None

    # ATR spike
    atr_series = [c.get("atr") for c in candles_1h]
    last_atr = atr_series[-1]
    hist_atr = [x for x in atr_series[-(lookback+1):-1] if x is not None]
    atr_avg = sum(hist_atr) / len(hist_atr) if hist_atr else None
    atr_spike_ratio = (last_atr / atr_avg) if (last_atr and atr_avg and atr_avg != 0) else None

    # Volume spike
    vols = [c.get("volume") for c in candles_1h]
    last_vol = vols[-1]
    hist_vol = [x for x in vols[-(lookback+1):-1] if x not in (None, 0)]
    vol_avg = sum(hist_vol) / len(hist_vol) if hist_vol else None
    volume_spike_ratio = (last_vol / vol_avg) if (last_vol and vol_avg and vol_avg != 0) else None

    return {
        "pct_change_1h": round(pct_change_1h, 3) if pct_change_1h is not None else None,
        "bb_width_ratio": round(bb_width_ratio, 3) if bb_width_ratio is not None else None,
        "atr_spike_ratio": round(atr_spike_ratio, 3) if atr_spike_ratio is not None else None,
        "volume_spike_ratio": round(volume_spike_ratio, 3) if volume_spike_ratio is not None else None
    }


def _safe_series(candles, key):
    return [c.get(key) for c in candles]

def _bb_width_series(candles):
    out = []
    for c in candles:
        lo = c.get("bb_lower")
        up = c.get("bb_upper")
        mid = c.get("bb_mid") or c.get("ma20") or c.get("close")
        if lo is None or up is None or mid in (None, 0):
            out.append(None)
        else:
            out.append((up - lo) / mid)
    return out

def _slope_from_series(series, window=5):
    if series is None or len(series) < window + 1:
        return None
    tail = series[-(window+1):]
    if any(v is None for v in tail):
        return None
    # simple per-bar slope (delta / window)
    return (tail[-1] - tail[0]) / float(window)

def compute_slopes(candles, window=5):
    """
    Tính slope (độ nghiêng) của một số chỉ báo từ chuỗi nến đã qua compute_indicators().
    Slope = (giá trị hiện tại - giá trị cách đây 'window' nến) / window
    Trả về: dict { 'slope_ma20', 'slope_ma50', 'slope_rsi', 'slope_bb_width', 'slope_atr' }
    """
    ma20_series = _safe_series(candles, "ma20")
    ma50_series = _safe_series(candles, "ma50")
    rsi_series = _safe_series(candles, "rsi")
    atr_series = _safe_series(candles, "atr")
    bb_width = _bb_width_series(candles)

    slopes = {
        "slope_ma20": _slope_from_series(ma20_series, window),
        "slope_ma50": _slope_from_series(ma50_series, window),
        "slope_rsi": _slope_from_series(rsi_series, window),
        "slope_bb_width": _slope_from_series(bb_width, window),
        "slope_atr": _slope_from_series(atr_series, window),
    }
    # round for compactness
    for k, v in slopes.items():
        if v is not None:
            slopes[k] = round(float(v), 6 if "ma" in k else 4)
    return slopes
