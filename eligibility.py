# eligibility.py
# Short-bias guard dựa trên khung 1D để loại tạm thời các mã thiên giảm kéo dài.

from typing import List, Dict, Tuple

def _linreg_slope(y_vals: List[float]) -> float:
    """
    Trả về slope xấp xỉ cho chuỗi y theo chỉ số [0..n-1].
    Dùng cho ước lượng slope của MA50 mà không cần thay đổi indicators.py
    """
    n = len(y_vals)
    if n < 2:
        return 0.0
    x_vals = list(range(n))
    x_mean = sum(x_vals)/n
    y_mean = sum(y_vals)/n
    num = sum((x - x_mean)*(y - y_mean) for x, y in zip(x_vals, y_vals))
    den = sum((x - x_mean)**2 for x in x_vals) or 1.0
    return num / den

def _pct_below_ma(candles_1d: List[Dict], ma_key: str = "ma50", window: int = 60) -> float:
    last = candles_1d[-window:] if len(candles_1d) >= window else candles_1d[:]
    if not last:
        return 0.0
    cnt = 0
    for c in last:
        close = c.get("close")
        ma = c.get(ma_key)
        if close is not None and ma is not None and close < ma:
            cnt += 1
    return cnt / len(last)

def _has_higher_high(candles_1d: List[Dict], window: int = 60) -> bool:
    """
    Kiểm tra xem có đỉnh cao hơn (HH) trong cửa sổ gần nhất hay không.
    Triển khai đơn giản: so đỉnh cao nhất 1/2 sau > 1/2 trước trong cửa sổ.
    """
    if len(candles_1d) < 40:
        return False
    w = min(window, len(candles_1d))
    last = candles_1d[-w:]
    mid = w // 2
    a = last[:mid]
    b = last[mid:]
    high_a = max((c.get("high") or float("-inf")) for c in a) if a else float("-inf")
    high_b = max((c.get("high") or float("-inf")) for c in b) if b else float("-inf")
    return high_b > high_a

def _ma_series(candles_1d: List[Dict], ma_key: str = "ma50", window: int = 30) -> List[float]:
    s = []
    src = candles_1d[-window:] if len(candles_1d) >= window else candles_1d[:]
    for c in src:
        v = c.get(ma_key)
        if v is not None:
            s.append(float(v))
    return s

def check_short_bias(candles_1d: List[Dict], strict_window: int = 60) -> Tuple[bool, Dict]:
    """
    Trả về (eligible_for_two_way, diagnostics).
    eligible_for_two_way = False nếu thỏa điều kiện short-bias guard.
    Rules:
      - close < ma50 và slope(ma50) < 0
      - >=70% nến dưới ma50 trong strict_window (mặc định 60)
      - Không có Higher High trong strict_window
    """
    if not candles_1d:
        return True, {"reason": "no_data"}

    # Điều kiện 1
    last = candles_1d[-1]
    close = last.get("close")
    ma50 = last.get("ma50")
    cond1 = False
    slope_ma50 = None
    ma_seq = _ma_series(candles_1d, "ma50", window=30)
    if ma50 is not None and close is not None:
        slope_ma50 = _linreg_slope(ma_seq) if len(ma_seq) >= 5 else 0.0
        cond1 = (close < ma50) and (slope_ma50 < 0)

    # Điều kiện 2
    pct_below = _pct_below_ma(candles_1d, "ma50", window=strict_window)
    cond2 = pct_below >= 0.70

    # Điều kiện 3
    cond3 = not _has_higher_high(candles_1d, window=strict_window)

    short_bias = cond1 and cond2 and cond3
    eligible = not short_bias
    info = {
        "close": close,
        "ma50": ma50,
        "slope_ma50_est": slope_ma50,
        "pct_below_ma50_last60": pct_below,
        "has_higher_high_last60": not cond3,
        "short_bias": short_bias,
        "rules": {
            "cond1_close_lt_ma50_and_slope_lt0": cond1,
            "cond2_pct_below_ma50_ge_0_70": cond2,
            "cond3_no_higher_high_last60": cond3,
        },
    }
    return eligible, info
