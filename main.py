from gpt_signal_builder import build_signals
from telegram_bot import send_signals
import os
import datetime

def main():
    now = datetime.datetime.utcnow()
    print(f"⏰ [UTC {now.strftime('%Y-%m-%d %H:%M:%S')}] Running scheduled scan...")

    signals = build_signals()
    print(f"📊 Raw signals: {signals}")  # Debug log

    if signals:
        print(f"✅ {len(signals)} signal(s) found. Sending to Telegram...")
        send_signals(signals)
    else:
        print("⚠️ No strong signals detected. Sending announcement...")
        send_signals([])  # Signal bot to send 'no signal' message

if __name__ == "__main__":
    print("🚀 Starting main.py")
    main()
    print("✅ Finished running main.py")
