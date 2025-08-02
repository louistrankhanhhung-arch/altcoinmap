from gpt_signal_builder import build_signals
from telegram_bot import send_signals
import os

def main():
    print("⏰ Running scheduled scan...")

    signals = build_signals()
    if signals:
        print(f"✅ {len(signals)} signal(s) found. Sending to Telegram...")
        send_signals(signals)
    else:
        print("⚠️ No strong signals detected. Sending announcement...")
        send_signals([])  # Signal bot to send 'no signal' message

if __name__ == "__main__":
    main()
