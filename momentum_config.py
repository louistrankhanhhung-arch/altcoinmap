# momentum_config.py
# Nhóm & ngưỡng momentum theo quy mô/thanh khoản để giảm nhiễu.
# Bạn có thể tinh chỉnh các threshold này khi chạy thực tế.

GROUPS = {
    "MAJORS": {
        "symbols": {"BTC","ETH","BNB","SOL","ADA","TRX"},
        "thresholds": {
            "pct_change_1h": 1.0,
            "atr_spike_ratio": 1.3,
            "volume_spike_ratio": 1.4,
            "bb_width_ratio": 1.3,
        },
    },
    "LARGE_CAP_ALTS": {
        "symbols": {"LINK","AVAX","NEAR","INJ","ATOM","AAVE","UNI","FIL","RNDR"},
        "thresholds": {
            "pct_change_1h": 1.5,
            "atr_spike_ratio": 1.4,
            "volume_spike_ratio": 1.5,
            "bb_width_ratio": 1.35,
        },
    },
    "MID_CAP_ALTS": {
        "symbols": {"ARB","SUI","PENDLE","APT","OP","STRK","DYDX","GMX","TIA","ENS","FET","RPL"},
        "thresholds": {
            "pct_change_1h": 2.0,
            "atr_spike_ratio": 1.5,
            "volume_spike_ratio": 1.6,
            "bb_width_ratio": 1.4,
        },
    },
}

TRADE_POLICY = {
    "MAJORS":        ["trend-follow","technical bounce"],
    "LARGE_CAP_ALTS":["trend-follow","breakout anticipation","technical bounce"],
    "MID_CAP_ALTS":  ["breakout anticipation","technical bounce","trap setup"],
}

def get_group(symbol: str) -> str:
    s = symbol.upper()
    for g, cfg in GROUPS.items():
        if s in cfg["symbols"]:
            return g
    return "MID_CAP_ALTS"

def thresholds_for(symbol: str) -> dict:
    return GROUPS[get_group(symbol)]["thresholds"]

def allowed_policies_for(symbol: str) -> list:
    return TRADE_POLICY.get(get_group(symbol), ["trend-follow","technical bounce"])

# Backward-compat shim: if old code calls get_thresholds(symbol)
def get_thresholds(symbol: str) -> dict:
    return thresholds_for(symbol)
