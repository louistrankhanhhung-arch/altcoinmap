import json
import os
from datetime import datetime, timedelta
from kucoin_api import fetch_realtime_price
from telegram_bot import send_message
from indicators import classify_trend, compute_indicators
from kucoin_api import fetch_coin_data

ACTIVE_FILE = "active_signals.json"

def load_active_signals():
    if not os.path.exists(ACTIVE_FILE):
        return []
    with open(ACTIVE_FILE, "r") as f:
        content = f.read().strip()
        if not content:
            return []
        return json.loads(content)

def save_active_signals(signals):
    with open(ACTIVE_FILE, "w") as f:
        json.dump(signals, f, indent=2)

def is_duplicate_signal(signal):
    try:
        with open("active_signals.json", "r") as f:
            active = json.load(f)
        for sig in active:
            if sig["pair"] == signal["pair"] and sig["status"] == "open":
                # Nếu trùng hướng -> là duplicate
                if sig["direction"].lower() == signal["direction"].lower():
                    return True
                # Nếu ngược hướng -> có thể là conflict (tuỳ bạn muốn reject hay cho qua)
                else:
                    print(f"⚠️ {signal['pair']} có tín hiệu mở theo hướng ngược lại ({sig['direction']} vs {signal['direction']})")
                    return True  # hoặc False nếu bạn cho phép ngược hướng
    except:
        pass
    return False


def check_signals():
    active_signals = load_active_signals()
    updated_signals = []
    now = datetime.utcnow()

    for signal in active_signals:
        try:
            pair = signal["pair"]
            symbol = pair.replace("/", "-")
            price = fetch_realtime_price(pair)
            direction = signal["direction"].lower()
            entry_1 = signal["entry_1"]
            entry_2 = signal["entry_2"]
            sl = signal["stop_loss"]
            tps = signal["tp"]
            sent_time = datetime.fromisoformat(signal["sent_at"])
            status = signal.get("status", "open")
            hit_tp = signal.get("hit_tp", [])
            message_id = signal.get("message_id")

            if status != "open":
                updated_signals.append(signal)
                continue

            if now - sent_time > timedelta(hours=12):
                if not (min(entry_1, entry_2) <= price <= max(entry_1, entry_2)):
                    signal["status"] = "timeout"
                    send_message(f"⚠️ <b>{pair}</b> đã timeout sau 12 giờ không vào lệnh.", reply_to_id=message_id)
                    updated_signals.append(signal)
                    continue

            if (direction == "long" and price <= sl) or (direction == "short" and price >= sl):
                signal["status"] = "stopped"
                send_message(f"🛑 <b>{pair}</b> đã hit Stop Loss ở {price:,.2f}", reply_to_id=message_id)
                updated_signals.append(signal)
                continue

            try:
                raw_candles = fetch_coin_data(pair, interval="4hour")
                enriched = compute_indicators(raw_candles)
                new_trend = classify_trend(enriched)
                if (direction == "long" and new_trend == "downtrend") or (direction == "short" and new_trend == "uptrend"):
                    signal["status"] = "reversed"
                    send_message(f"↩️ <b>{pair}</b> đã đảo chiều xu hướng. Lệnh {direction.title()} bị huỷ.", reply_to_id=message_id)
                    updated_signals.append(signal)
                    continue
            except Exception as err:
                print(f"⚠️ Không thể kiểm tra đảo chiều cho {pair}: {err}")

            tp_hit = False
            for i, tp in enumerate(tps):
                if i+1 in hit_tp:
                    continue
                if (direction == "long" and price >= tp) or (direction == "short" and price <= tp):
                    hit_tp.append(i+1)
                    send_message(f"✅ <b>{pair}</b> đã đạt TP{i+1} ở {price:,.2f}", reply_to_id=message_id)
                    tp_hit = True

            if tp_hit:
                signal["hit_tp"] = hit_tp
                if len(hit_tp) == len(tps):
                    signal["status"] = "closed"
                    send_message(f"🎯 <b>{pair}</b> đã hoàn thành tất cả mục tiêu và đóng lệnh.", reply_to_id=message_id)

            updated_signals.append(signal)

        except Exception as e:
            print(f"❌ Lỗi khi xử lý tín hiệu {signal.get('pair')}: {e}")
            updated_signals.append(signal)

    save_active_signals(updated_signals)

if __name__ == "__main__":
    check_signals()
