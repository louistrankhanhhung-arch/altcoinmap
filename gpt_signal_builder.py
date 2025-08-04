import os
import openai
from datetime import datetime, UTC
from utils import parse_signal_response

# Gửi từng coin một với prompt có định dạng từ PROMPT_TEMPLATE
async def get_gpt_signals(data_by_symbol):
    results = {}

    openai.api_key = os.getenv("OPENAI_API_KEY")
    client = openai.AsyncOpenAI()

    for symbol, tf_data in data_by_symbol.items():
        try:
            summary_lines = []
            for tf in ["1H", "4H", "1D"]:
                item = tf_data.get(tf, {})
                if item:
                    summary_lines.append(
                        f"[{tf}] Trend: {item.get('trend')}, RSI: {item.get('rsi')}, MA20: {item.get('ma20')}, MA50: {item.get('ma50')}, Candle: {item.get('candle_signal')}, BB: ({item.get('bb_lower')}, {item.get('bb_upper')})"
                    )

            prompt = f"""
Bạn là một trợ lý giao dịch crypto chuyên nghiệp.
Dưới đây là dữ liệu kỹ thuật của {symbol} theo từng khung thời gian:

{chr(10).join(summary_lines)}

Dựa trên xu hướng, lực nến, RSI, MA, và vùng BB, hãy đánh giá xem có cơ hội giao dịch không.
Nếu có, hãy đề xuất kế hoạch giao dịch chi tiết như sau:

- Symbol: {symbol} 
- Direction: Long hoặc Short
- Entry 1:
- Stop Loss:
- TP1 đến TP5:
- Risk Level:
- Leverage:
- Key watch:
- Nhận định ngắn gọn về tín hiệu này bằng tiếng Việt.

Chỉ trả về dữ liệu JSON.
"""

            now = datetime.now(UTC)
            print(f"\n🤖 GPT analyzing {symbol} at {now.isoformat()}...")

            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt.strip()}],
                temperature=0.4,
                max_tokens=1000,
                timeout=30
            )

            reply = response.choices[0].message.content
            print(f"📩 GPT raw reply for {symbol}:", reply)
            parsed = parse_signal_response(reply)
            parsed["pair"] = symbol

            if not parsed:
                print(f"⚠️ GPT trả về định dạng không hợp lệ cho {symbol}.")
                continue

            def validate_signal(p, tf_data):
                try:
                    entry_1 = float(p["entry_1"])
                    sl = float(p["stop_loss"])
                    direction = p["direction"].lower()

                    trend_1h = tf_data.get("1H", {}).get("trend", "unknown")
                    trend_4h = tf_data.get("4H", {}).get("trend", "unknown")
                    trend_1d = tf_data.get("1D", {}).get("trend", "unknown")

                    rsi_1h = tf_data.get("1H", {}).get("rsi")
                    rsi_4h = tf_data.get("4H", {}).get("rsi")
                    candle_1h = tf_data.get("1H", {}).get("candle_signal", "none")
                    candle_4h = tf_data.get("4H", {}).get("candle_signal", "none")

                    strategy_type = ""
                    if direction == "long":
                        if trend_1h == trend_4h == trend_1d == "uptrend" and rsi_1h and rsi_1h > 55:
                            strategy_type = "scale-in"
                        elif trend_1d != trend_4h or trend_4h != trend_1h:
                            strategy_type = "DCA"
                    elif direction == "short":
                        if trend_1h == trend_4h == trend_1d == "downtrend" and rsi_1h and rsi_1h < 45:
                            strategy_type = "scale-in"
                        elif trend_1d != trend_4h or trend_4h != trend_1h:
                            strategy_type = "DCA"
                    if not strategy_type:
                        print(f"⚠️ Không thể xác định chiến lược cho {symbol}. Bỏ qua.")
                        return False
                    p["strategy_type"] = strategy_type

                    spread_pct = 0.005
                    if strategy_type == "scale-in":
                        p["entry_2"] = round(entry_1 * (1 + spread_pct), 2) if direction == "long" else round(entry_1 * (1 - spread_pct), 2)
                    elif strategy_type == "DCA":
                        p["entry_2"] = round(entry_1 * (1 - spread_pct), 2) if direction == "long" else round(entry_1 * (1 + spread_pct), 2)

                    # Sử dụng SR levels để tính TP chia theo cấp độ
                    sr_4h = tf_data.get("4H", {}).get("sr_levels", [])
                    sr_1d = tf_data.get("1D", {}).get("sr_levels", [])

                    if direction == "long":
                        r4h = sorted([price for _, price, typ in sr_4h if typ == "resistance" and price > entry_1])
                        r1d = sorted([price for _, price, typ in sr_1d if typ == "resistance" and price > entry_1])
                        tps = r4h[:2] + r1d[:3]
                        while len(tps) < 5:
                            tps.append(round(entry_1 * (1 + 0.01 * (len(tps) + 1)), 2))
                        p["tp"] = tps[:5]
                    elif direction == "short":
                        s4h = sorted([price for _, price, typ in sr_4h if typ == "support" and price < entry_1], reverse=True)
                        s1d = sorted([price for _, price, typ in sr_1d if typ == "support" and price < entry_1], reverse=True)
                        tps = s4h[:2] + s1d[:3]
                        while len(tps) < 5:
                            tps.append(round(entry_1 * (1 - 0.01 * (len(tps) + 1)), 2))
                        p["tp"] = tps[:5]

                    tp = p["tp"]
                    tp_range_ok = abs(float(tp[-1]) - entry_1) / entry_1 >= 0.01
                    sl_range_ok = abs(entry_1 - sl) / entry_1 >= 0.005

                    score = 0
                    if strategy_type == "scale-in":
                        if trend_1h == trend_4h == trend_1d:
                            score += 1
                        if candle_1h in ["bullish engulfing"] and direction == "long":
                            score += 1
                        if candle_1h in ["bearish engulfing"] and direction == "short":
                            score += 1
                        if direction == "long" and rsi_1h and rsi_1h > 60:
                            score += 1
                        if direction == "short" and rsi_1h and rsi_1h < 40:
                            score += 1
                    else:
                        if trend_1h != trend_4h or trend_4h != trend_1d:
                            score += 1
                        if candle_4h in ["bullish engulfing"] and direction == "long":
                            score += 1
                        if candle_4h in ["bearish engulfing"] and direction == "short":
                            score += 1
                        if direction == "long" and rsi_4h and rsi_4h < 40:
                            score += 1
                        if direction == "short" and rsi_4h and rsi_4h > 60:
                            score += 1

                    p["confidence"] = "high" if score >= 3 else "medium" if score == 2 else "low"

                    return tp_range_ok and sl_range_ok and p["confidence"] in ["high", "medium"]

                except Exception as err:
                    print(f"❌ Lỗi khi validate {symbol}: {err}")
                    return False

            is_valid = validate_signal(parsed, tf_data)
            if is_valid:
                results[symbol] = parsed
            else:
                print(f"✅ GPT trả về JSON hợp lệ nhưng bị loại do lọc logic cho {symbol}.")

        except Exception as e:
            print(f"❌ GPT failed for {symbol}: {e}")

    return results

BLOCKS = {
    "block1": ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT"],
    "block2": ["LINK/USDT", "NEAR/USDT", "AVAX/USDT", "ARB/USDT"],
    "block3": ["SUI/USDT", "PENDLE/USDT"]
}
