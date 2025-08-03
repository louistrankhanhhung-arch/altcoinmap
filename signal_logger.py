import json
from datetime import datetime, timezone

LOG_FILE = "signal_logger.json"

def save_signals(signals, all_symbols=None, raw_signals=None):
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "signals": signals,
        "all_symbols": all_symbols or [],
        "raw_signals": raw_signals or {}
    }

    try:
        with open(LOG_FILE, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = []

    data.insert(0, log_entry)  # log mới lên đầu

    try:
        with open(LOG_FILE, "w") as f:
            json.dump(data[:20], f, indent=2)
        print("✅ Signals logged.")
    except Exception as e:
        print(f"❌ Failed to write signal log: {e}")
