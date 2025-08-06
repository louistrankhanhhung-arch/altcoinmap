import sys
import json
import traceback
import asyncio
from datetime import datetime, UTC
from gpt_signal_builder import get_gpt_signals, BLOCKS
from kucoin_api import fetch_coin_data
from telegram_bot import send_message
from signal_logger import save_signals
from indicators import compute_indicators, generate_suggested_tps
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
        raw_data_by_symbol = {}
        for symbol in symbols:
            raw_data = {
                tf: fetch_coin_data(symbol, interval=TF_MAP[tf]) for tf in TF_MAP
            }
            raw_data_by_symbol[symbol] = raw_data
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

        suggested_tps_by_symbol = {}
        for symbol in data_by_symbol:
            tf_data = data_by_symbol[symbol].get("4H", {})
            direction = tf_data.get("trend", "sideways")
            price = tf_data.get("close")
            sr_levels = tf_data.get("sr_levels", [])
            if price and direction and sr_levels:
                suggested = generate_suggested_tps(price, direction, sr_levels)
                suggested_tps_by_symbol[symbol] = suggested

        print("📊 Sending to GPT...")
        signals_dict = asyncio.run(get_gpt_signals(data_by_symbol, suggested_tps_by_symbol))
        signals = list(signals_dict.values())
        signals = [s for s in signals if not is_duplicate_signal(s)]
        all_symbols = list(data_by_symbol.keys())

        for sig in signals:
            for k in ["Entry 1", "Entry_1"]:
                if k in sig: sig["entry_1"] = float(sig[k])
            for k in ["Entry 2", "Entry_2"]:
                if k in sig: sig["entry_2"] = float(sig[k])
            for k in ["Stop Loss", "Stop_Loss"]:
                if k in sig: sig["stop_loss"] = float(sig[k])

            sym = sig.get("pair") or sig.get("symbol")
            tf_data = data_by_symbol.get(sym, {}).get("4H", {})
            raw_4h = raw_data_by_symbol.get(sym, {}).get("4H", [])

            direction = sig.get("direction")
            current_price = tf_data.get("close")
            atr_val = tf_data.get("atr")
            sr_levels = tf_data.get("sr_levels", [])

            if not all([direction, current_price, atr_val]):
                print(f"⚠️ Thiếu dữ liệu cho {sym} -> BỎ QUA")
                continue

            entry_1 = sig.get("entry_1")
            entry_2 = sig.get("entry_2")

            # Kiểm tra entry lệch quá 10% tùy theo hướng giao dịch -> loại bỏ
            if direction.lower() == "long" and entry_1 > current_price * 1.1:
                print(f"⚠️ Entry LONG quá xa giá hiện tại ({current_price}) -> BỎ QUA {sym}")
                continue
            elif direction.lower() == "short" and entry_1 < current_price * 0.9:
                print(f"⚠️ Entry SHORT quá xa giá hiện tại ({current_price}) -> BỎ QUA {sym}")
                continue

            if abs(entry_1 - current_price) / current_price > 0.1:
                print(f"⚠️ Entry 1 lệch quá xa giá hiện tại ({current_price}) -> BỎ QUA {sym}")
                continue

            if not entry_1 or not entry_2:
                print(f"⚠️ Không có entry từ GPT cho {sym} -> BỎ QUA")
                continue

            bb_lower = tf_data.get("bb_lower")
            bb_upper = tf_data.get("bb_upper")
            swing_low = min([c["low"] for c in raw_4h[-5:]]) if raw_4h else None
            swing_high = max([c["high"] for c in raw_4h[-5:]]) if raw_4h else None

            stop_loss = sig.get("stop_loss")
            if not stop_loss:
                print(f"⚠️ Không có Stop Loss từ GPT cho {sym} -> BỎ QUA")
                continue
            sig["stop_loss"] = float(stop_loss)

            rr_ratio = abs(entry_1 - stop_loss)
            if rr_ratio == 0:
                print(f"⚠️ R:R không hợp lệ với {sym} -> BỎ QUA")
                continue

            tp1 = sig.get("tp1")
            if tp1:
                rr_reward = abs(tp1 - entry_1)
                rr = rr_reward / rr_ratio if rr_ratio != 0 else 0
                if rr < 1.2:
                    print(f"⚠️ R:R quá thấp ({rr:.2f}) -> BỎ QUA {sym}")
                    continue
                else:
                    print(f"✅ R:R = {rr:.2f} cho {sym}")


            supports = [lvl for _, lvl, t in sr_levels if t == "support"]
            resistances = [lvl for _, lvl, t in sr_levels if t == "resistance"]
            trend_strength = tf_data.get("trend", "moderate")
            confidence = sig.get("confidence", "medium")
                        sig["strategy_type"] = label_strategy_type(sig)

            from telegram_bot import format_message
            text = format_message(sig)
            message_id = send_message(text)
            sig["message_id"] = message_id

        save_signals(signals, all_symbols, data_by_symbol)
        save_active_signals(signals)

    except Exception as e:
        print(f"❌ Main error in {block_name}: {e}")
        traceback.print_exc()
        send_message(f"⚠️ Lỗi khi chạy hệ thống với {block_name}: {str(e)}")

def main():
    now = datetime.now(UTC)
    print(f"\n⏰ [UTC {now.strftime('%Y-%m-%d %H:%M:%S')}] Running scheduled scan...")

    for blk in BLOCKS:
        run_block(blk)

if __name__ == "__main__":
    main()
