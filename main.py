from gpt_signal_builder import build_signals
from telegram_bot import send_signals
from signal_logger import save_signals
import datetime

def main():
    now = datetime.datetime.utcnow()
    print(f"⏰ [UTC {now.strftime('%Y-%m-%d %H:%M:%S')}] Running scheduled scan...")

    signals, all_symbols, raw_signals = build_signals()
    print(f"📊 Raw signals: {signals}")

    save_signals(signals, all_symbols, raw_signals)

    if signals:
        print(f"✅ {len(signals)} signal(s) found. Sending to Telegram...")
        send_signals(signals)
    else:
        print("⚠️ No strong signals detected. Sending announcement...")
        send_signals([])


if __name__ == "__main__":
    print("🚀 Starting main.py")
    main()
    print("✅ Finished running main.py")
