import os
import openai
from datetime import datetime, UTC
import json
from utils import parse_signal_response

# Gửi từng coin một với prompt có định dạng từ PROMPT_TEMPLATE
async def get_gpt_signals(data_by_symbol, suggested_tps_by_symbol):
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

                current_price = tf_data.get("4H", {}).get("close", "N/A")
                trend_4h = tf_data.get("4H", {}).get("trend", "unknown")
                trend_1d = tf_data.get("1D", {}).get("trend", "unknown")
                suggested_tps = suggested_tps_by_symbol.get(symbol, [])

                json_tps = json.dumps(suggested_tps, ensure_ascii=False)

                prompt = f"""
Bạn là một trợ lý giao dịch crypto chuyên nghiệp.
Dưới đây là dữ liệu kỹ thuật của {symbol} theo từng khung thời gian:

{chr(10).join(summary_lines)}

Giá hiện tại: {current_price}
Các vùng Take Profit gợi ý theo kỹ thuật: {json_tps}
Xu hướng 4H: {trend_4h}, xu hướng 1D: {trend_1d}

Hãy đánh giá xem có cơ hội giao dịch không dựa trên xu hướng (Trend), lực nến, RSI, MA, Bollinger Bands. 
Các mức Entry, Stop Loss và Take Profit cần được xác định dựa trên các chỉ báo kỹ thuật như hỗ trợ/kháng cự, Bollinger Bands, MA và ATR. Tránh đặt Entry quá xa giá hiện tại. Stop Loss không nên quá gần. TP nên thực tế và có thể đạt được trong bối cảnh thị trường. Tỷ lệ R:R nên hợp lý, ví dụ 1:1.5 trở lên.
Nếu có, hãy đề xuất kế hoạch giao dịch chi tiết như sau, ưu tiên đúng kỹ thuật và thực tế thị trường:

Chỉ TRẢ VỀ nội dung JSON THUẦN TÚY đúng định dạng sau, KHÔNG thêm ```json hoặc bất kỳ mô tả, ký tự nào khác:
"""
                prompt += """
{
  "symbol": "...",
  "direction": "Long hoặc Short",
  "entry1": ..., 
  "entry2": ...,  
  "stop_loss": ..., 
  "take_profits": [...],
  "risk_level": "Low / Medium / High",
  "leverage": "3x / 5x",
  "confidence": "high / medium / low",
  "key_watch": "...",
  "nhan_dinh": "..."
}
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

                reply = response.choices[0].message.content.strip()
                print(f"📩 GPT raw reply for {symbol}:", reply)

                # Strip leading/trailing non-json characters for safety
                json_start = reply.find('{')
                json_end = reply.rfind('}') + 1
                cleaned = reply[json_start:json_end].strip()

                parsed = parse_signal_response(cleaned)

                if not parsed:
                    print(f"⚠️ GPT trả về định dạng không hợp lệ cho {symbol}.")
                    continue

                parsed["pair"] = symbol

                # Lấy các thông số kỹ thuật để tự động tính SL nếu cần
                direction = parsed.get("direction")
                tf_4h = tf_data.get("4H", {})
                entry_1 = parsed.get("entry_1")
                bb_lower = tf_4h.get("bb_lower")
                bb_upper = tf_4h.get("bb_upper")
                swing_low = tf_4h.get("low")
                swing_high = tf_4h.get("high")
                atr_val = tf_4h.get("atr")
                ma20 = tf_4h.get("ma20")
                rsi = tf_4h.get("rsi")
                sr_levels = tf_4h.get("sr_levels")

                results[symbol] = parsed

            except Exception as e:
                print(f"❌ GPT failed for {symbol}: {e}")

    return results

BLOCKS = {
    "block1": ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT"],
    "block2": ["LINK/USDT", "NEAR/USDT", "AVAX/USDT", "ARB/USDT"],
    "block3": ["SUI/USDT", "PENDLE/USDT"]
}
