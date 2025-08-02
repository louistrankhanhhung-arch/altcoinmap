# signal_logger.py
import json
import os
from datetime import datetime

LOG_FILE = "data/signals_log.json"

def save_signals(signals):
    if not signals:
        return

    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "signals": signals
    }

    try:
        if not os.path.exists(LOG_FILE):
            os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
            with open(LOG_FILE, "w") as f:
                json.dump([log_entry], f, indent=2)
        else:
            with open(LOG_FILE, "r+") as f:
                data = json.load(f)
                data.insert(0, log_entry)  # thêm vào đầu
                f.seek(0)
                json.dump(data[:20], f, indent=2)  # giữ lại 20 lần gần nhất
    except Exception as e:
        print("❌ Lỗi khi lưu log:", e)
