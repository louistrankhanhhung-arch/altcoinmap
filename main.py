from gpt_signal_builder import build_signals
from telegram_bot import send_signals
from signal_logger import save_signals
import datetime
import traceback
import json

def main():
    now = datetime.datetime.utcnow()
    print(f"\n⏰ [UTC {now.strftime('%Y-%m-%d %H:%M:%S')}] Running scheduled scan...")

    try:
        signals, all_symbols, raw_signals = build_signals()
        print(f"\n📊 Raw signals ({len(signals)}): {json.dumps(signals, indent=2)}")

        save_signals(signals, all_symbols, raw_signals)

        if signals:
            print(f"\n✅ {len(signals)} signal(s) found. Sending to Telegram...")
            send_signals(signals)
        else:
            print("\n⚠️ No strong signals detected. Sending announcement...")
            send_signals([])

    except Exception as e:
        print(f"\n❌ Main error: {e}")
        traceback.print_exc()
        send_signals(["⚠️ Lỗi khi chạy hệ thống: " + str(e)])

if __name__ == "__main__":
    print("🚀 Starting main.py")
    main()
    print("✅ Finished running main.py")
