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
from signal_tracker import is_duplicate_signal

ACTIVE_FILE = "active_signals.json"

TF_MAP = {"1H": "1hour", "4H": "4hour", "1D": "1day"}

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

def classify_trend(candles):
    if not candles or candles[-1].get("ma20") is None:
        return "unknown"
    price = candles[-1]["close"]
    ma20 = candles[-1]["ma20"]
    ma50 = candles[-1]["ma50"]

    if ma20 and ma50:
        if price > ma20 > ma50:
            return "uptrend"
        elif price < ma20 < ma50:
            return "downtrend"
        else:
            return "sideways"
    return "unknown"

def detect_candle_signal(candles):
    if len(candles) < 2:
        return "none"
    c1 = candles[-2]
    c2 = candles[-1]
    if c1["close"] < c1["open"] and c2["close"] > c2["open"] and c2["close"] > c1["open"]:
        return "bullish engulfing"
    elif c1["close"] > c1["open"] and c2["close"] < c2["open"] and c2["close"] < c1["open"]:
        return "bearish engulfing"
    elif abs(c2["close"] - c2["open"]) < (c2["high"] - c2["low"]) * 0.1:
        return "doji"
    return "none"

def label_strategy_type(signal):
    try:
        e1 = signal.get("entry_1")
        e2 = signal.get("entry_2")
        direction = signal.get("direction", "").lower()
        if direction == "long" and e1 and e2:
            return "dca" if e1 > e2 else "scale_in"
        elif direction == "short" and e1 and e2:
            return "dca" if e1 < e2 else "scale_in"
    except:
        pass
    return "unknown"

def run_block(block_name):
    symbols = BLOCKS.get(block_name)
    if not symbols:
        print(f"❌ Block không hợp lệ: {block_name}")
        return

    print(f"\n📦 Đang xử lý block: {block_name} với {len(symbols)} mã: {symbols}")

    try:
        print("📥 Fetching market data...")
        data_by_symbol = {}
        for symbol in symbols:
            raw_data = {
                tf: fetch_coin_data(symbol, interval=TF_MAP[tf]) for tf in TF_MAP
            }
            enriched = {}
            for tf in raw_data:
                candles = compute_indicators(raw_data[tf])
                trend = classify_trend(candles)
                signal = detect_candle_signal(candles)
                enriched[tf] = {
                    "trend": trend,
                    "candle_signal": signal,
                    **candles[-1]
                }
            data_by_symbol[symbol] = enriched

        print("📊 Sending to GPT...")
        signals_dict = asyncio.run(get_gpt_signals(data_by_symbol))
        signals = list(signals_dict.values())
        signals = [s for s in signals if not is_duplicate_signal(s)]
        all_symbols = list(data_by_symbol.keys())

        for sig in signals:
            sig["strategy_type"] = label_strategy_type(sig)

        save_signals(signals, all_symbols, data_by_symbol)
        save_active_signals(signals)

        if signals:
            print(f"✅ {len(signals)} signal(s) found in {block_name}. Sending to Telegram...")
            send_signals(signals)
        else:
            print(f"⚠️ No strong signals detected in {block_name}. Sending announcement...")
            send_signals([])

    except Exception as e:
        print(f"❌ Main error in {block_name}: {e}")
        traceback.print_exc()
        send_signals([f"⚠️ Lỗi khi chạy hệ thống với {block_name}: {str(e)}"])

def main():
    now = datetime.now(UTC)
    print(f"\n⏰ [UTC {now.strftime('%Y-%m-%d %H:%M:%S')}] Running scheduled scan...")

    for blk in BLOCKS:
        run_block(blk)

if __name__ == "__main__":
    main()
