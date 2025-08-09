# trade_policy.py
# Chính sách giao dịch cấp cao. Lưu ý: FILTERS_CONFIG đã được chuyển sang filters.py để tránh circular import.
# File này cung cấp các hàm tiện ích về policy mà không phụ thuộc module khác.

from typing import Optional
from datetime import datetime, timezone

# --- R:R tối thiểu ---
DEFAULT_MIN_RR = 1.2  # an toàn chung
MIN_RR_BY_STRATEGY = {
    "trend-follow": 1.8,
    "breakout anticipation": 1.6,
    "technical bounce": 1.5,
    "trap setup": 1.6,
}

def min_rr(strategy_type: Optional[str]) -> float:
    if not strategy_type:
        return DEFAULT_MIN_RR
    return float(MIN_RR_BY_STRATEGY.get(strategy_type, DEFAULT_MIN_RR))

# --- Leverage gợi ý theo risk level (nếu cần) ---
LEVERAGE_BY_RISK = {
    "Low": "3x",
    "Medium": "5x",
    "High": "10x",
}

def leverage_for(risk_level: Optional[str]) -> str:
    if not risk_level:
        return LEVERAGE_BY_RISK["Medium"]
    return LEVERAGE_BY_RISK.get(risk_level, LEVERAGE_BY_RISK["Medium"])

# --- Cooldown giữa các tín hiệu ---
def cooldown_ok(last_signal_ts: Optional[float], now_ts: Optional[float] = None, hours: float = 1.0) -> bool:
    """
    Trả về True nếu đã qua thời gian cooldown (giờ). last_signal_ts/now_ts là epoch seconds.
    """
    if last_signal_ts is None:
        return True
    if now_ts is None:
        now_ts = datetime.now(timezone.utc).timestamp()
    return (now_ts - last_signal_ts) >= hours * 3600.0
