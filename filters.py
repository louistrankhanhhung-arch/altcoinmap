# filters.py
# Bộ tiêu chí hạn chế bull/bear trap & quá mua/quá bán sâu.
from typing import Dict, Tuple, List

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
