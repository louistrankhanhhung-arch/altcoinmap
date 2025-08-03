import os
import openai
from datetime import datetime, UTC
from utils import parse_signal_response

# Gửi từng coin một với prompt có định dạng từ PROMPT_TEMPLATE
async def get_gpt_signals(data_by_symbol):
    results = {}

    openai.api_key = os.getenv("OPENAI_API_KEY")
    client = openai.AsyncOpenAI()  # ✅ SDK mới

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
- Direction: Long hoặc Short
- Entry 1:
- Entry 2:
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
                messages=[
                    {"role": "user", "content": prompt.strip()}
                ],
                temperature=0.4,
                max_tokens=1000,
                timeout=30
            )

            reply = response.choices[0].message.content
            parsed = parse_signal_response(reply)

            def validate_signal(p):
                try:
                    tp = p["tp"]
                    entry_1 = float(p["entry_1"])
                    entry_2 = float(p["entry_2"])
                    sl = float(p["stop_loss"])
                    direction = p["direction"].lower()

                    tp_range_ok = abs(float(tp[-1]) - entry_1) / entry_1 >= 0.01
                    sl_range_ok = abs(entry_1 - sl) / entry_1 >= 0.005

                    # Chiến lược và confidence dựa trên entry (đã sửa đúng logic)
                    if direction == "long":
                        if entry_1 > entry_2:
                            p["strategy_type"] = "DCA"
                        elif entry_1 < entry_2:
                            p["strategy_type"] = "scale-in"
                        else:
                            p["strategy_type"] = "⚠️ check entry logic"
                    elif direction == "short":
                        if entry_1 > entry_2:
                            p["strategy_type"] = "scale-in"
                        elif entry_1 < entry_2:
                            p["strategy_type"] = "DCA"
                        else:
                            p["strategy_type"] = "⚠️ check entry logic"
                    else:
                        p["strategy_type"] = "unknown"

                    # Đánh giá confidence nâng cao
                    trend_1h = tf_data.get("1H", {}).get("trend", "unknown")
                    trend_4h = tf_data.get("4H", {}).get("trend", "unknown")
                    trend_1d = tf_data.get("1D", {}).get("trend", "unknown")

                    rsi_1h = tf_data.get("1H", {}).get("rsi")
                    rsi_4h = tf_data.get("4H", {}).get("rsi")
                    candle_1h = tf_data.get("1H", {}).get("candle_signal", "none")
                    candle_4h = tf_data.get("4H", {}).get("candle_signal", "none")

                    signal_strength = 0

                    # Scale-in: xu hướng đồng pha + tín hiệu nến thuận hướng + RSI hỗ trợ
                    if p["strategy_type"] == "scale-in":
                        if trend_1h == trend_4h == trend_1d and trend_1h in ["uptrend", "downtrend"]:
                            signal_strength += 1
                        if candle_1h == "bullish engulfing" and direction == "long":
                            signal_strength += 1
                        if candle_1h == "bearish engulfing" and direction == "short":
                            signal_strength += 1
                        if direction == "long" and rsi_1h and rsi_1h > 55:
                            signal_strength += 1
                        if direction == "short" and rsi_1h and rsi_1h < 45:
                            signal_strength += 1

                    # DCA: phân kỳ trend + nến đảo chiều + RSI quá bán/mua
                    elif p["strategy_type"] == "DCA":
                        if trend_1d != trend_4h or trend_1d != trend_1h:
                            signal_strength += 1
                        if candle_4h == "bullish engulfing" and direction == "long":
                            signal_strength += 1
                        if candle_4h == "bearish engulfing" and direction == "short":
                            signal_strength += 1
                        if direction == "long" and rsi_4h and rsi_4h < 40:
                            signal_strength += 1
                        if direction == "short" and rsi_4h and rsi_4h > 60:
                            signal_strength += 1

                    # Đánh giá tổng thể
                    if signal_strength >= 3:
                        p["confidence"] = "high"
                    elif signal_strength == 2:
                        p["confidence"] = "medium"
                    else:
                        p["confidence"] = "low"

                    entry_order_ok = p["strategy_type"] in ["scale-in", "DCA"]
                    return tp_range_ok and sl_range_ok and entry_order_ok and p["confidence"] in ["high", "medium"]
                except:
                    return False

            if parsed and isinstance(parsed, dict) and 'entry_1' in parsed and 'tp' in parsed and validate_signal(parsed):
                results[symbol] = parsed
            else:
                print(f"⚠️ GPT trả về không hợp lệ hoặc không đủ điều kiện lọc cho {symbol}.\n{reply}")

        except Exception as e:
            print(f"❌ GPT failed for {symbol}: {e}")

    return results

BLOCKS = {
    "block1": ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT"],
    "block2": ["LINK/USDT", "NEAR/USDT", "AVAX/USDT", "ARB/USDT"],
    "block3": ["SUI/USDT", "PENDLE/USDT"]
}
