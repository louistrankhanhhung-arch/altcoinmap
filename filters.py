# filters.py
# Bộ tiêu chí hạn chế bull/bear trap & quá mua/quá bán sâu.
from typing import Dict, Tuple, List


# === Runtime filters configuration (centralized here to avoid circular imports) ===
FILTERS_CONFIG = {
    # Soft confirmations for hourly scanning
    "use_soft_4h": True,
    "debounce_1h_bars": 2,

    # Multi‑TF alignment (1H vs 4H)
    "multi_tf_confirm": True,
    "tf_confirm_main": "4H",
    "tf_confirm_threshold": 0.2,

    # Core anti-trap filters
    "enable_rsi_regime": True,
    "enable_anti_fomo": True,
    "enable_exhaustion_cooldown": True,
    "enable_sfp": True,

    # Breakout retest behavior
    "enable_breakout_retest": "auto",  # "auto" | "on" | "off"
    "slope_strong_threshold": 0.5,     # in AUTO mode, if |slope| > this, skip retest
    "retest_max_candles": 3,

    # Thresholds
    "anti_fomo_dist_atr": 1.5,
    "rsi_overheat": 75,
    "rsi_distance_atr": 1.2,
    "exhaustion_atr_spike": 1.8,
    "exhaustion_vol_spike": 1.8,
    "sfp_lookback": 20,
}

def anti_fomo_extension(snapshot: Dict, cfg: Dict) -> Tuple[bool, str]:
    close = snapshot.get("close"); atr = snapshot.get("atr14") or snapshot.get("atr"); ma20 = snapshot.get("ma20")
    if close is None or atr in (None, 0) or ma20 is None:
        return True, "insufficient"
    dist = (close - ma20) / atr
    if dist > cfg.get("anti_fomo_dist_atr", 1.5):
        return False, f"anti_fomo: dist={dist:.2f}ATR"
    return True, "ok"

def rsi_regime(snapshot: Dict, trend_1d: str, cfg: Dict) -> Tuple[bool, str]:
    rsi = snapshot.get("rsi14") or snapshot.get("rsi")
    close = snapshot.get("close"); atr = snapshot.get("atr14") or snapshot.get("atr"); ma20 = snapshot.get("ma20")
    if any(v is None for v in [rsi, close, atr, ma20]) or atr == 0:
        return True, "insufficient"
    dist_atr = abs((close - ma20)/atr)
    if trend_1d == "uptrend" and rsi > cfg.get("rsi_overheat", 75) and dist_atr > cfg.get("rsi_distance_atr", 1.2):
        return False, f"rsi_overheat:{rsi:.1f}|dist:{dist_atr:.2f}ATR"
    return True, "ok"

def exhaustion_cooldown(snapshot: Dict, cfg: Dict) -> Tuple[bool, str]:
    atr_sp = snapshot.get("atr_spike_ratio")
    vol_sp = snapshot.get("volume_spike_ratio")
    if atr_sp is None or vol_sp is None:
        return True, "insufficient"
    if atr_sp > cfg.get("exhaustion_atr_spike", 1.8) and vol_sp > cfg.get("exhaustion_vol_spike", 1.8):
        return False, "exhaustion"
    return True, "ok"

def sfp_check(candles_4h: List[Dict], cfg: Dict) -> Tuple[bool, str]:
    n = min(cfg.get("sfp_lookback", 20), len(candles_4h))
    if n < 5:
        return True, "insufficient"
    window = candles_4h[-n:]
    hi = max(c.get("high") for c in window if c.get("high") is not None)
    lo = min(c.get("low") for c in window if c.get("low") is not None)
    last = candles_4h[-1]
    if last.get("low") is None or last.get("high") is None or last.get("close") is None or last.get("open") is None:
        return True, "insufficient"
    if last["low"] < lo and last["close"] > lo:
        return False, "sfp_bullish"
    if last["high"] > hi and last["close"] < hi:
        return False, "sfp_bearish"
    return True, "ok"

def breakout_retest_ok(candles_tf: list, breakout_zone: tuple, cfg: dict) -> tuple:
    """
    Kiểm tra breakout có retest hay không, với chế độ auto cho phép bỏ qua khi slope mạnh.
    candles_tf: danh sách nến của TF kiểm tra (thường 4H)
    breakout_zone: (low, high) vùng breakout
    cfg: FILTERS_CONFIG
    """
    mode = cfg.get("enable_breakout_retest", "auto")
    if mode == "off":
        return True, "skip"

    # Tính slope MA20 1D nếu có dữ liệu
    slope_threshold = cfg.get("slope_strong_threshold", 0.5)
    slope_val = None
    try:
        closes = [c.get("close") for c in candles_tf if c.get("close") is not None]
        ma20_vals = []
        if len(closes) >= 21:
            for i in range(len(closes)-20):
                ma20_vals.append(sum(closes[i:i+20])/20)
        if len(ma20_vals) >= 2:
            slope_val = (ma20_vals[-1] - ma20_vals[-2]) / ma20_vals[-2]
    except Exception:
        pass

    if mode == "auto" and slope_val is not None and abs(slope_val) > slope_threshold:
        return True, f"momentum strong skip slope={slope_val:.3f}"

    N = min(cfg.get("retest_max_candles", 3), len(candles_tf))
    lo, hi = breakout_zone
    for c in candles_tf[-N:]:
        if c.get("low") is None or c.get("high") is None or c.get("close") is None or c.get("open") is None:
            continue
        # Retest định nghĩa: low chạm vùng breakout + close > open (bull) hoặc high chạm vùng breakout + close < open (bear)
        if c["low"] <= hi and c["low"] >= lo and c["close"] > c["open"]:
            return True, "bull_retest"
        if c["high"] >= lo and c["high"] <= hi and c["close"] < c["open"]:
            return True, "bear_retest"
    return False, "no_retest"

def multi_tf_alignment_ok(candles_fast: list, candles_slow: list, cfg: dict) -> tuple:
    """
    Kiểm tra momentum của TF nhanh (vd: 1H) có cùng hướng TF chậm (vd: 4H) hay không.
    candles_fast: danh sách nến TF nhanh
    candles_slow: danh sách nến TF chậm
    cfg: FILTERS_CONFIG
    """
    if not cfg.get("multi_tf_confirm", False):
        return True, "skip"
    threshold = cfg.get("tf_confirm_threshold", 0.2)

    def slope_ma20(candles):
        closes = [c.get("close") for c in candles if c.get("close") is not None]
        if len(closes) >= 21:
            ma20_vals = [sum(closes[i:i+20])/20 for i in range(len(closes)-19)]
            if len(ma20_vals) >= 2:
                return (ma20_vals[-1] - ma20_vals[-2]) / ma20_vals[-2]
        return 0

        # Cho phép dùng 4H mềm nếu bật cấu hình hoặc không có 4H thật
    if cfg.get("use_soft_4h", True) and (not candles_slow or len(candles_slow) < 5):
        proxy = build_soft_htf_from_1h(candles_fast, group=4)
        candles_slow = proxy if proxy else candles_slow
    slope_fast = slope_ma20(candles_fast)
    slope_slow = slope_ma20(candles_slow)

    if slope_fast * slope_slow < 0:  # trái hướng
        return False, f"opposite slopes {slope_fast:.3f} vs {slope_slow:.3f}"
    if abs(slope_slow) < threshold:  # trend chậm chưa đủ mạnh
        return False, f"weak slow slope {slope_slow:.3f}"
    return True, f"aligned slopes {slope_fast:.3f} vs {slope_slow:.3f}"

def build_soft_htf_from_1h(candles_1h: list, group: int = 4, limit: int = 60) -> list:
    """
    Gộp 4 cây 1H đã đóng thành 1 cây 4H proxy (rolling).
    Trả về danh sách "nến 4H mềm" (không tính lại full indicator).
    """
    if not candles_1h or len(candles_1h) < group:
        return []
    soft = []
    # dùng các field: open, high, low, close
    n = len(candles_1h)
    start = max(0, n - limit*group)
    for i in range(start, n, group):
        chunk = candles_1h[max(0, i-group+1):i+1]  # rolling 4 nến gần nhất
        if len(chunk) < group:
            continue
        open_ = chunk[0].get("open")
        close_ = chunk[-1].get("close")
        highs = [c.get("high") for c in chunk if c.get("high") is not None]
        lows = [c.get("low") for c in chunk if c.get("low") is not None]
        if open_ is None or close_ is None or not highs or not lows:
            continue
        soft.append({"open": open_, "close": close_, "high": max(highs), "low": min(lows)})
    return soft

def debounce_1h_ok(candles_1h: list, bars: int = 2) -> tuple:
    """
    Yêu cầu 'bars' nến 1H gần nhất có slope MA20 cùng dấu (xấp xỉ bằng slope(close)).
    """
    closes = [c.get("close") for c in candles_1h if c.get("close") is not None]
    if len(closes) < max(21, bars+1):
        return True, "insufficient"
    # slope gần đúng: so sánh MA20 gần nhất với trước đó
    ma20_vals = [sum(closes[i:i+20])/20 for i in range(len(closes)-19)]
    if len(ma20_vals) < bars+1:
        return True, "insufficient"
    signs = []
    for k in range(1, bars+1):
        prev, cur = ma20_vals[-k-1], ma20_vals[-k]
        if prev == 0:
            signs.append(0)
        else:
            slope = (cur - prev) / abs(prev)
            signs.append(1 if slope > 0 else (-1 if slope < 0 else 0))
    if 0 in signs:
        return False, "flat momentum"
    if not all(s == signs[0] for s in signs):
        return False, f"mixed slopes {signs}"
    return True, "ok"
