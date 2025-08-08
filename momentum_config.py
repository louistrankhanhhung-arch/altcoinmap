# Centralized momentum thresholds per-coin (base symbol before '/')
# You can tune these values in one place.
# Metrics:
# - pct_change_1h: absolute % move over last hour
# - atr_spike_ratio: ATR(1H, last) / ATR(1H, avg lookback)
# - volume_spike_ratio: Vol(1H, last) / Vol(1H, avg lookback)
# - bb_width_ratio: BB width(1H, last) / BB width(1H, avg lookback)

DEFAULTS = {
    "pct_change_1h": 2.0,
    "atr_spike_ratio": 1.5,
    "volume_spike_ratio": 1.5,
    "bb_width_ratio": 1.4,
}

GROUPS = {
    "MAJORS": {
        "symbols": {"BTC", "ETH", "BNB", "SOL"},
        "thresholds": {
            "pct_change_1h": 1.0,
            "atr_spike_ratio": 1.3,
            "volume_spike_ratio": 1.4,
            "bb_width_ratio": 1.3,
        },
    },
    "LARGE_CAP_ALTS": {
        "symbols": {"LINK", "AVAX", "NEAR"},
        "thresholds": {
            "pct_change_1h": 1.5,
            "atr_spike_ratio": 1.4,
            "volume_spike_ratio": 1.5,
            "bb_width_ratio": 1.35,
        },
    },
    "MID_CAP_ALTS": {
        "symbols": {"ARB", "SUI", "PENDLE"},
        "thresholds": {
            "pct_change_1h": 2.0,
            "atr_spike_ratio": 1.5,
            "volume_spike_ratio": 1.6,
            "bb_width_ratio": 1.4,
        },
    },
}

def get_thresholds(symbol: str) -> dict:
    """Return thresholds for a base symbol (e.g., 'BTC' from 'BTC/USDT')."""
    base = symbol.split('/')[0].upper() if symbol else ""
    for spec in GROUPS.values():
        if base in spec["symbols"]:
            th = DEFAULTS.copy()
            th.update(spec["thresholds"])
            return th
    return DEFAULTS.copy()
