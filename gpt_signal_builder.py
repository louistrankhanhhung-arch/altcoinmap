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

            if parsed:
                results[symbol] = parsed
            else:
                print(f"⚠️ GPT trả về không hợp lệ cho {symbol}.\n{reply}")

        except Exception as e:
            print(f"❌ GPT failed for {symbol}: {e}")

    return results

BLOCKS = {
    "block1": ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT"],
    "block2": ["LINK/USDT", "NEAR/USDT", "AVAX/USDT", "ARB/USDT"],
    "block3": ["SUI/USDT", "PENDLE/USDT"]
}
