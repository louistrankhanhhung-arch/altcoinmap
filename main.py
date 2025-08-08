import sys
import json
import traceback
import asyncio
import time
from datetime import datetime, UTC
from gpt_signal_builder import get_gpt_signals, BLOCKS
from kucoin_api import fetch_coin_data
from telegram_bot import send_message, format_message
from signal_logger import save_signals
from indicators import compute_indicators, generate_suggested_tps, compute_short_term_momentum
from signal_tracker import resolve_duplicate_signal

ACTIVE_FILE = "active_signals.json"

TF_MAP = {"1H": "1hour", "4H": "4hour", "1D": "1day"}

TEST_MODE = True  # Set to False to enforce 4H candle closure

def safe_float(val):
    try:
        if isinstance(val, str):
            val = val.replace(',', '').replace('"', '').strip()
        return float(val)
    except:
        return None

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

def is_opposite_trend(a, b):
    return (a == "uptrend" and b == "downtrend") or (a == "downtrend" and b == "uptrend")

def strong_momentum_flag(m):
    """
    Quy tắc đơn giản: momentum mạnh khi một trong các điều kiện sau thỏa:
      - abs(pct_change_1h) >= 2.0
      - atr_spike_ratio >= 1.5
      - volume_spike_ratio >= 1.5
      - bb_width_ratio >= 1.4
    """
    if not isinstance(m, dict):
        return False
    pc = m.get("pct_change_1h")
    atr_r = m.get("atr_spike_ratio")
    vol_r = m.get("volume_spike_ratio")
    bb_r = m.get("bb_width_ratio")
    return any([
        (pc is not None and abs(pc) >= 2.0),
        (atr_r is not None and atr_r >= 1.5),
        (vol_r is not None and vol_r >= 1.5),
        (bb_r is not None and bb_r >= 1.4),
    ])

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

def run_block(block_name):
    if TEST_MODE:
        print(f"⏳ [TEST MODE] Bỏ qua kiểm tra giờ, luôn chạy block {block_name}")
    else:
        current_time = datetime.now(UTC)
        if current_time.hour % 4 != 0:
            print(f"⏸ Bỏ qua block {block_name} vì chưa đến thời điểm đóng nến 4H")
            return

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
# Gắn động lượng 1H
if "1H" in raw_data:
    try:
        candles_1h = compute_indicators(raw_data["1H"])
        momo = compute_short_term_momentum(candles_1h)
        if isinstance(momo, dict):
            enriched.setdefault("1H", {}).update({
                "pct_change_1h": momo.get("pct_change_1h"),
                "bb_width_ratio": momo.get("bb_width_ratio"),
                "atr_spike_ratio": momo.get("atr_spike_ratio"),
                "volume_spike_ratio": momo.get("volume_spike_ratio"),
            })
    except Exception as _e:
        print(f"⚠️ Không tính được momentum 1H cho {symbol}: {_e}")

# Siết đồng thuận khung giờ
t1h = enriched.get("1H", {}).get("trend", "unknown")
t4h = enriched.get("4H", {}).get("trend", "unknown")
t1d = enriched.get("1D", {}).get("trend", "unknown")
candle4h = enriched.get("4H", {}).get("candle_signal", "none")

accept = False
# Rule chính: 4H phải KHÔNG sideways và đồng hướng với 1D
if t4h in ("uptrend", "downtrend") and t1d == t4h:
    accept = True
# Rule phụ: 1D không sideways, 4H không ngược 1D (và 4H không sideways)
elif t1d in ("uptrend", "downtrend") and not is_opposite_trend(t4h, t1d) and t4h != "sideways":
    accept = True
else:
    # Ngoại lệ: 4H có nến tín hiệu mạnh + momentum 1H bùng nổ
    mmm = {
        "pct_change_1h": enriched.get("1H", {}).get("pct_change_1h"),
        "bb_width_ratio": enriched.get("1H", {}).get("bb_width_ratio"),
        "atr_spike_ratio": enriched.get("1H", {}).get("atr_spike_ratio"),
        "volume_spike_ratio": enriched.get("1H", {}).get("volume_spike_ratio"),
    }
    if candle4h in ("bullish engulfing", "bearish engulfing") and strong_momentum_flag(mmm):
        accept = True

if not accept:
    print(f"⛔ {symbol}: không đạt đồng thuận 4H/1D (t4h={t4h}, t1d={t1d}), bỏ qua.")
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
        signals_dict = asyncio.run(get_gpt_signals(data_by_symbol, suggested_tps_by_symbol, test_mode=TEST_MODE))
        signals = list(signals_dict.values())
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

            tps = sig.get("take_profits") or sig.get("take_profit") or sig.get("tp")
            if isinstance(tps, str):
                try:
                    tps = json.loads(tps)
                except:
                    try:
                        tps = [float(x.strip()) for x in tps.strip('[]').split(',') if x.strip()]
                    except:
                        print(f"⚠️ Không thể chuyển đổi TP cho {sym}, bỏ qua")
                        sig["tp"] = []
                        continue

            if isinstance(tps, list):
                tps_clean = [safe_float(tp) for tp in tps[:5]]
                for i, tp_val in enumerate(tps_clean):
                    sig[f"tp{i+1}"] = tp_val
                sig["tp"] = tps_clean
            else:
                sig["tp"] = []

            tp_list = sig.get("tp", [])
            tp1 = safe_float(tp_list[0]) if isinstance(tp_list, list) and len(tp_list) > 0 else None

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

            sig = resolve_duplicate_signal(sig)
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

def main():
    now = datetime.now(UTC)
    print(f"\n⏰ [UTC {now.strftime('%Y-%m-%d %H:%M:%S')}] Running scheduled scan...")

    if len(sys.argv) > 1:
        block_name = sys.argv[1]
        if block_name in BLOCKS:
            run_block(block_name)
        else:
            print(f"❌ Block không hợp lệ: {block_name}")
    else:
        for blk in BLOCKS:
            run_block(blk)
            print("⏳ Đợi 60 giây trước khi chạy block tiếp theo...")
            time.sleep(60)

if __name__ == "__main__":
    main()
