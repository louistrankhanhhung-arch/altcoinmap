import json
import os
from datetime import datetime, timedelta
from kucoin_api import fetch_realtime_price
from telegram_bot import send_message

ACTIVE_FILE = "active_signals.json"

# Load active signals
def load_active_signals():
    if not os.path.exists(ACTIVE_FILE):
        return []
    with open(ACTIVE_FILE, "r") as f:
        return json.load(f)

# Save active signals
def save_active_signals(signals):
    with open(ACTIVE_FILE, "w") as f:
        json.dump(signals, f, indent=2)

def check_signals():
    active_signals = load_active_signals()
    updated_signals = []
    now = datetime.utcnow()

    for signal in active_signals:
        try:
            pair = signal["pair"]
            symbol = pair.replace("/", "-")
            price = fetch_realtime_price(pair)
            direction = signal["direction"]
            entry_1 = signal["entry_1"]
            entry_2 = signal["entry_2"]
            sl = signal["stop_loss"]
            tps = signal["tp"]
            sent_time = datetime.fromisoformat(signal["sent_at"])
            status = signal.get("status", "open")

            # Skip if already closed
            if status != "open":
                updated_signals.append(signal)
                continue

            # Timeout if >12h and price never entered
            if now - sent_time > timedelta(hours=12):
                if not (min(entry_1, entry_2) <= price <= max(entry_1, entry_2)):
                    signal["status"] = "timeout"
                    send_message(f"⚠️ <b>{pair}</b> đã timeout sau 12 giờ không vào lệnh.")
                    updated_signals.append(signal)
                    continue

            # Check SL hit
            if (direction == "Long" and price <= sl) or (direction == "Short" and price >= sl):
                signal["status"] = "stopped"
                send_message(f"🛑 <b>{pair}</b> đã hit Stop Loss ở {price:,.2f}")
                updated_signals.append(signal)
                continue

            # Check TP hit
            for i, tp in enumerate(tps):
                if (direction == "Long" and price >= tp) or (direction == "Short" and price <= tp):
                    signal["status"] = f"tp{i+1}"
                    send_message(f"✅ <b>{pair}</b> đã đạt TP{i+1} ở {price:,.2f}")
                    break

            updated_signals.append(signal)

        except Exception as e:
            print(f"❌ Lỗi khi xử lý tín hiệu {signal.get('pair')}: {e}")
            updated_signals.append(signal)

    save_active_signals(updated_signals)

if __name__ == "__main__":
    check_signals()
