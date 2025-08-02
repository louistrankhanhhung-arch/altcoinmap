import json
from datetime import datetime

LOG_FILE = "signal_logger.json"

def save_signals(signals, all_symbols=None, raw_signals=None):
    # Ghi lại mọi phiên quét dù signals rỗng
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "signals": signals,
        "all_symbols": all_symbols or [],
        "raw_signals": raw_signals or []
    }

    try:
        with open(LOG_FILE, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = []

    data.insert(0, log_entry)  # thêm log mới vào đầu

    with open(LOG_FILE, "w") as f:
        json.dump(data[:20], f, indent=2)  # giữ lại 20 bản quét gần nhất
