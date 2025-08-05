import os
import openai
from datetime import datetime, UTC
from utils import parse_signal_response
from indicators import generate_take_profits, generate_stop_loss

# Gửi từng coin một với prompt có định dạng từ PROMPT_TEMPLATE
async def get_gpt_signals(data_by_symbol):
    results = {}

    openai.api_key = os.getenv("OPENAI_API_KEY")

    async with openai.AsyncOpenAI() as client:
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

Hãy đánh giá xem có cơ hội giao dịch không dựa trên xu hướng (Trend), lực nến, RSI, MA, Bollinger Bands.
Nếu có, hãy đề xuất kế hoạch giao dịch chi tiết như sau, ưu tiên đúng kỹ thuật và thực tế thị trường:

- Symbol: {symbol} 
- Direction: Long hoặc Short
- Entry 1:
- Entry 2: (nếu áp dụng chiến lược scale-in hoặc DCA)
- Stop Loss: theo hỗ trợ/kháng cự hoặc BB/SwingLow-SwingHigh, tránh đặt quá gần Entry
- TP1 đến TP5: chia đều theo vùng kháng cự/hỗ trợ hoặc Fibonacci, tối thiểu 2 TP, tối đa 5 TP (có thể bỏ TP4–TP5 nếu không có vùng mạnh)
- Risk Level: Low / Medium / High
- Leverage: 3x / 5x tuỳ mức độ tín hiệu
- Strategy: dca hoặc scale-in (nêu rõ khi nào dùng)
- Confidence: high / medium / low (tùy theo đồng thuận nhiều khung thời gian và mô hình nến)
- Key watch: mô tả điều kiện cần theo dõi thêm (ví dụ: kháng cự gần, RSI breakout, BB chạm biên,...)
- Nhận định ngắn gọn về tín hiệu này bằng tiếng Việt (gợi ý hành động cụ thể và rủi ro nếu có).

Chỉ trả về dữ liệu JSON.
"""

                now = datetime.now(UTC)
                print(f"\n🤖 GPT analyzing {symbol} at {now.isoformat()}...")

                response = await client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt.strip()}],
                    temperature=0.4,
                    max_tokens=1200,
                    timeout=30
                )

                reply = response.choices[0].message.content
                print(f"📩 GPT raw reply for {symbol}:", reply)
                parsed = parse_signal_response(reply)

                if not parsed:
                    print(f"⚠️ GPT trả về định dạng không hợp lệ cho {symbol}.")
                    continue

                parsed["pair"] = symbol
                results[symbol] = parsed

            except Exception as e:
                print(f"❌ GPT failed for {symbol}: {e}")

    return results

BLOCKS = {
    "block1": ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT"],
    "block2": ["LINK/USDT", "NEAR/USDT", "AVAX/USDT", "ARB/USDT"],
    "block3": ["SUI/USDT", "PENDLE/USDT"]
}
