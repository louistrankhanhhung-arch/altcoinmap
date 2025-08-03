import sys
import json
import traceback
import asyncio
from datetime import datetime, UTC
from gpt_signal_builder import get_gpt_signals, BLOCKS
from kucoin_api import fetch_coin_data
from telegram_bot import send_signals
from signal_logger import save_signals
from indicators import compute_indicators

ACTIVE_FILE = "active_signals.json"

def save_active_signals(signals):
    now = datetime.now(UTC).isoformat()
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
        json.dump(new_data[:50], f, indent=2)

def main():
    now = datetime.now(UTC)
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
        print("📥 Fetching market data...")
        data_by_symbol = {}
        for symbol in symbols:
            raw_data = {
                tf: fetch_coin_data(symbol, interval=tf.lower()) for tf in ["1H", "4H", "1D"]
            }
            enriched = {
                tf: compute_indicators(raw_data[tf]) for tf in raw_data
            }
            data_by_symbol[symbol] = enriched

        print("📊 Sending to GPT...")
        signals_dict = asyncio.run(get_gpt_signals(data_by_symbol))
        signals = list(signals_dict.values())
        all_symbols = list(data_by_symbol.keys())
        save_signals(signals, all_symbols, data_by_symbol)

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
