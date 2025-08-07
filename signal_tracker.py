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


def resolve_duplicate_signal(new_signal):
    active_signals = load_active_signals()
    updated_signals = []
    new_pair = new_signal.get("pair")
    new_direction = new_signal.get("direction", "").lower()
    now = datetime.utcnow()
    resolved = False

    for s in active_signals:
        pair = s.get("pair")
        direction = s.get("direction", "").lower()
        status = s.get("status", "open")

        if status != "open" or pair != new_pair:
            updated_signals.append(s)
            continue

        if direction != new_direction:
            # Ngược hướng -> huỷ
            s["status"] = "canceled"
            msg = f"\ud83d\udeab <b>{pair}</b> tín hiệu ngược hướng mới, tự động huỷ."
            send_message(msg, reply_to_id=s.get("message_id"))
        else:
            # Cùng hướng -> đánh dấu là resignal, giữ lại
            new_signal["assessment"] = "Resignal - tín hiệu mở rộng"
        updated_signals.append(s)
        resolved = True

    if resolved:
        save_active_signals(updated_signals)
    return new_signal


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
                    if message_id:
                        send_message(f"\u26a0\ufe0f <b>{pair}</b> \u0111\u00e3 timeout sau 12 gi\u1edd kh\u00f4ng v\u00e0o l\u1ec7nh.", reply_to_id=message_id)
                    else:
                        send_message(f"\u26a0\ufe0f <b>{pair}</b> \u0111\u00e3 timeout sau 12 gi\u1edd kh\u00f4ng v\u00e0o l\u1ec7nh.")
                    updated_signals.append(signal)
                    continue

            if (direction == "long" and price <= sl) or (direction == "short" and price >= sl):
                signal["status"] = "stopped"
                if message_id:
                    send_message(f"\ud83d\udea9 <b>{pair}</b> \u0111\u00e3 hit Stop Loss \u1edf {price:,.2f}", reply_to_id=message_id)
                else:
                    send_message(f"\ud83d\udea9 <b>{pair}</b> \u0111\u00e3 hit Stop Loss \u1edf {price:,.2f}")
                updated_signals.append(signal)
                continue

            try:
                raw_candles = fetch_coin_data(pair, interval="4hour")
                enriched = compute_indicators(raw_candles)
                new_trend = classify_trend(enriched)
                if (direction == "long" and new_trend == "downtrend") or (direction == "short" and new_trend == "uptrend"):
                    signal["status"] = "reversed"
                    send_message(f"\u21a9\ufe0f <b>{pair}</b> \u0111\u00e3 \u0111\u1ea3o chi\u1ec1u xu h\u01b0\u1edbng. L\u1ec7nh {direction.title()} b\u1ecb hu\u1ef7.", reply_to_id=message_id)
                    updated_signals.append(signal)
                    continue
            except Exception as err:
                print(f"\u26a0\ufe0f Kh\u00f4ng th\u1ec3 ki\u1ec3m tra \u0111\u1ea3o chi\u1ec1u cho {pair}: {err}")

            tp_hit = False
            for i, tp in enumerate(tps):
                if i + 1 in hit_tp:
                    continue
                if (direction == "long" and price >= tp) or (direction == "short" and price <= tp):
                    hit_tp.append(i + 1)
                    if message_id:
                        send_message(f"\u2705 <b>{pair}</b> \u0111\u00e3 \u0111\u1ea1t TP{i + 1} \u1edf {price:,.2f}", reply_to_id=message_id)
                    else:
                        send_message(f"\u2705 <b>{pair}</b> \u0111\u00e3 \u0111\u1ea1t TP{i + 1} \u1edf {price:,.2f}")
                    tp_hit = True

            if tp_hit:
                signal["hit_tp"] = hit_tp
                if len(hit_tp) == len(tps):
                    signal["status"] = "closed"
                    if message_id:
                        send_message(f"\ud83c\udfaf <b>{pair}</b> \u0111\u00e3 ho\u00e0n th\u00e0nh t\u1ea5t c\u1ea3 m\u1ee5c ti\u00eau v\u00e0 \u0111\u00f3ng l\u1ec7nh.", reply_to_id=message_id)
                    else:
                        send_message(f"\ud83c\udfaf <b>{pair}</b> \u0111\u00e3 ho\u00e0n th\u00e0nh t\u1ea5t c\u1ea3 m\u1ee5c ti\u00eau v\u00e0 \u0111\u00f3ng l\u1ec7nh.")

            updated_signals.append(signal)

        except Exception as e:
            print(f"\u274c L\u1ed7i khi x\u1eed l\u00fd t\u00edn hi\u1ec7u {signal.get('pair')}: {e}")
            updated_signals.append(signal)

    save_active_signals(updated_signals)


if __name__ == "__main__":
    check_signals()
