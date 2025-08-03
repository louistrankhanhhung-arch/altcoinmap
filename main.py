import sys 
import datetime
import traceback
import json
from gpt_signal_builder import get_gpt_signals, BLOCKS
from telegram_bot import send_signals
from signal_logger import save_signals
from kucoin_api import get_market_data
from indicators import compute_indicators

ACTIVE_FILE = "active_signals.json"


def save_active_signals(signals):
    now = datetime.datetime.now(datetime.UTC).isoformat()
    for s in signals:
        s["sent_at"] = now
        s["status"] = "open"

    try:
        with open(ACTIVE_FILE, "r") as f:
            existing = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        existing = []

    new_data = signals + existing
    with open(ACTIVE_FILE, "w") as f:
        json.dump(new_data[:50], f, indent=2)  # giữ lại 50 tín hiệu gần nhất


def main():
    now = datetime.datetime.now(datetime.UTC)
    print(f"\n⏰ [UTC {now.strftime('%Y-%m-%d %H:%M:%S')}] Running scheduled scan...")

    if len(sys.argv) < 2:
        print("❌ Thiếu tham số block. Vui lòng dùng: python main.py block1/block2/block3")
        return

    block_name = sys.argv[1]
    symbols = BLOCKS.get(block_name)

    if not symbols:
        print(f"❌ Block không hợp lệ: {block_name}")
        return

    try:
        # 1. Fetch raw market data
        raw_data = get_market_data(symbols)

        # 2. Tính indicators
        data_with_indicators = {
            symbol: compute_indicators(ohlcv) for symbol, ohlcv in raw_data.items()
        }

        # 3. Gửi qua GPT để đánh giá
        import asyncio
        signals = asyncio.run(get_gpt_signals(data_with_indicators))

        all_symbols = list(data_with_indicators.keys())
        raw_signals = data_with_indicators
        save_signals(signals, all_symbols, raw_signals)

        if signals:
            print(f"\n✅ {len(signals)} signal(s) found. Sending to Telegram...")
            send_signals(signals)
            save_active_signals(signals)
        else:
            print("\n⚠️ No strong signals detected. Sending announcement...")
            send_signals([])

    except Exception as e:
        print(f"\n❌ Main error: {e}")
        traceback.print_exc()
        send_signals(["⚠️ Lỗi khi chạy hệ thống: " + str(e)])


if __name__ == "__main__":
    main()
