import openai
from datetime import datetime, UTC
from utils import format_prompt_for_gpt, parse_signal_response

# Gửi từng coin một với prompt tối giản
async def get_gpt_signals(data_by_symbol):
    results = {}

    for symbol, tf_data in data_by_symbol.items():
        try:
            # Rút gọn nội dung gửi đi bằng cách nén từng khung thời gian
            summary_lines = []
            for tf in ["1H", "4H", "1D"]:
                item = tf_data.get(tf, {})
                if item:
                    summary_lines.append(
                        f"[{tf}] Trend: {item.get('trend')}, RSI: {item.get('rsi')}, MA: {item.get('ma_cross')}, Candle: {item.get('candle_signal')}, Note: {item.get('comment', '')}"
                    )
            prompt = format_prompt_for_gpt(symbol, summary_lines)

            now = datetime.now(UTC)
            print(f"\n🤖 GPT analyzing {symbol} at {now.isoformat()}...")

            response = await openai.ChatCompletion.acreate(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an experienced crypto trading assistant. Based on multi-timeframe data, choose whether this coin has a strong signal and build a detailed trading plan."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
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
