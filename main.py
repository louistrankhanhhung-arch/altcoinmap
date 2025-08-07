import sys 
import json 
import traceback 
import asyncio 
from datetime import datetime, UTC 
from gpt_signal_builder import get_gpt_signals, BLOCKS 
from kucoin_api import fetch_coin_data 
from telegram_bot import send_message, format_message 
from signal_logger import save_signals 
from indicators import compute_indicators, generate_suggested_tps 
from signal_tracker import is_duplicate_signal

ACTIVE_FILE = "active_signals.json"

TF_MAP = {"1H": "1hour", "4H": "4hour", "1D": "1day"}

def safe_float(val): try: if isinstance(val, str): val = val.replace(',', '') return float(val) except: return None

def save_active_signals(signals): now = datetime.now(UTC).isoformat() for s in signals: s["sent_at"] = now s["status"] = "open"

try:
    with open(ACTIVE_FILE, "r") as f:
        existing = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    existing = []

new_data = signals + existing
with open(ACTIVE_FILE, "w") as f:
    json.dump(new_data[:50], f, indent=2)

def classify_trend(candles): if not candles or candles[-1].get("ma20") is None: return "unknown" price = candles[-1]["close"] ma20 = candles[-1]["ma20"] ma50 = candles[-1]["ma50"]

if ma20 and ma50:
    if price > ma20 > ma50:
        return "uptrend"
    elif price < ma20 < ma50:
        return "downtrend"
    else:
        return "sideways"
return "unknown"

def detect_candle_signal(candles): if len(candles) < 2: return "none" c1 = candles[-2] c2 = candles[-1] if c1["close"] < c1["open"] and c2["close"] > c2["open"] and c2["close"] > c1["open"]: return "bullish engulfing" elif c1["close"] > c1["open"] and c2["close"] < c2["open"] and c2["close"] < c1["open"]: return "bearish engulfing" elif abs(c2["close"] - c2["open"]) < (c2["high"] - c2["low"]) * 0.1: return "doji" return "none"

def run_block(block_name): symbols = BLOCKS.get(block_name) if not symbols: print(f"❌ Block không hợp lệ: {block_name}") return

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

        trends = [enriched[tf]["trend"] for tf in TF_MAP if tf in enriched]
        if all(t == "sideways" for t in trends):
            print(f"⚠️ {symbol} có cả 3 khung thời gian đều sideways -> BỎ QUA")
            continue

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
    print(f"✅ Số tín hiệu hợp lệ sau lọc: {len(signals)}")

    final_signals = []
    for sig in signals:
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

        entry_1 = safe_float(sig.get("entry_1") or sig.get("entry1"))
        if entry_1 is None:
            print(f"⚠️ Thiếu dữ liệu entry hoặc giá hiện tại -> BỎ QUA {sym}")
            continue

        sig["entry_1"] = entry_1

        if direction.lower() == "long" and entry_1 > current_price * 1.1:
            print(f"⚠️ Entry LONG quá xa: entry={entry_1}, price={current_price} -> BỎ QUA {sym}")
            continue
        elif direction.lower() == "short" and entry_1 < current_price * 0.9:
            print(f"⚠️ Entry SHORT quá xa: entry={entry_1}, price={current_price} -> BỎ QUA {sym}")
            continue
        elif direction.lower() not in ["long", "short"]:
            print(f"⚠️ Hướng giao dịch không rõ ràng: {direction} -> BỎ QUA {sym}")
            continue

        stop_loss = safe_float(sig.get("stop_loss") or sig.get("StopLoss") or sig.get("stoploss"))
        if stop_loss is None:
            print(f"⚠️ Không có Stop Loss hợp lệ từ GPT cho {sym} -> BỎ QUA")
            continue
        sig["stop_loss"] = stop_loss

        tps = sig.get("take_profits") or sig.get("take_profit")
        if isinstance(tps, list):
            for i, tp in enumerate(tps[:5]):
                safe_tp = safe_float(tp)
                if safe_tp is not None:
                    sig[f"tp{i+1}"] = safe_tp

        tp1 = safe_float(sig.get("tp1"))
        rr_ratio = abs(entry_1 - stop_loss)
        if rr_ratio == 0:
            print(f"⚠️ R:R không hợp lệ với {sym} -> BỎ QUA")
            continue
        if tp1:
            rr_reward = abs(tp1 - entry_1)
            rr = rr_reward / rr_ratio
            if rr < 1.2:
                print(f"⚠️ R:R quá thấp ({rr:.2f}) cho {sym} | entry: {entry_1}, sl: {stop_loss}, tp1: {tp1}")
                continue
            else:
                print(f"✅ R:R = {rr:.2f} cho {sym}")
        else:
            print(f"⚠️ Không có TP1 cho {sym} -> BỎ QUA")
            continue

        try:
            text = format_message(sig)
            message_id = send_message(text)
            sig["message_id"] = message_id
            final_signals.append(sig)
        except Exception as e:
            print(f"❌ Lỗi khi gửi {sym} tới Telegram: {e}")

    save_signals(final_signals, list(data_by_symbol.keys()), data_by_symbol)
    save_active_signals(final_signals)

except Exception as e:
    print(f"❌ Main error in {block_name}: {e}")
    traceback.print_exc()
    send_message(f"⚠️ Lỗi khi chạy hệ thống với {block_name}: {str(e)}")

def main(): now = datetime.now(UTC) print(f"\n⏰ [UTC {now.strftime('%Y-%m-%d %H:%M:%S')}] Running scheduled scan...")

if len(sys.argv) > 1:
    block_name = sys.argv[1]
    if block_name in BLOCKS:
        run_block(block_name)
    else:
        print(f"❌ Block không hợp lệ: {block_name}")
else:
    for blk in BLOCKS:
        run_block(blk)

if name == "main": main()

