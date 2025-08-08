# Centralized policy for trading filters

# RR thresholds by ATR%% (4H) regime.
# Interpret as: if atr_pct < limit -> require at least rr_min
ATR_RR_THRESHOLDS = [
    (0.7, 1.3),   # low vol
    (1.5, 1.5),   # mid vol
    (999, 1.8),   # high vol (catch-all upper)
]

# Fallback RR minimum if ATR%% can't be computed
DEFAULT_MIN_RR = 1.4

# Cooldown window (hours) after a losing/invalidated trade per symbol
COOLDOWN_HOURS = 3

# Minimal volume spike ratio on 1H to accept a trade (liquidity floor)
VOLUME_SPIKE_FLOOR = 0.8


def atr_regime_rr_min(atr_value, price):
    """Return minimal RR required based on ATR%% regime using the thresholds above."""
    try:
        atr_pct = (atr_value / price) * 100.0 if (atr_value is not None and price) else None
    except Exception:
        atr_pct = None

    if atr_pct is None:
        return DEFAULT_MIN_RR

    for limit, rr_min in ATR_RR_THRESHOLDS:
        if atr_pct < limit:
            return rr_min
    return DEFAULT_MIN_RR
