import os
import openai
from datetime import datetime, UTC
import json
from utils import parse_signal_response

# Gửi từng coin một với prompt có định dạng từ PROMPT_TEMPLATE
async def get_gpt_signals(data_by_symbol, suggested_tps_by_symbol, test_mode=False):
    results = {}

    openai.api_key = os.getenv("OPENAI_API_KEY")

    async with openai.AsyncOpenAI() as client:
        for symbol, tf_data in data_by_symbol.items():
            try:
                if not test_mode:
                    current_time = datetime.now(UTC)
                    if current_time.hour % 4 != 0:
                        print(f"⏳ Bỏ qua {symbol} vì nến 4H chưa đóng.")
                        continue
                else:
                    print(f"🧪 [TEST MODE] Luôn xử lý {symbol} bất kể giờ.")
                summary_lines = []
                for tf in ["1H", "4H", "1D"]:
                    item = tf_data.get(tf, {})
                    if item:
                        base = f"[{tf}] Trend: {item.get('trend')}, RSI: {item.get('rsi')}, MA20: {item.get('ma20')}, MA50: {item.get('ma50')}, Candle: {item.get('candle_signal')}, BB: ({item.get('bb_lower')}, {item.get('bb_upper')})"
                        slopes = f", SLOPE: ma20={item.get('slope_ma20')}, ma50={item.get('slope_ma50')}, rsi={item.get('slope_rsi')}, bbw={item.get('slope_bb_width')}, atr={item.get('slope_atr')}"
                        if tf == "1H":
                            momo = f", MOMO: pct={item.get('pct_change_1h')}, bbw={item.get('bb_width_ratio')}, atr={item.get('atr_spike_ratio')}, vol={item.get('volume_spike_ratio')}"
                            summary_lines.append(base + slopes + momo)
                        else:
                            summary_lines.append(base + slopes)
                current_price = tf_data.get("4H", {}).get("close", "N/A")
                trend_1h = tf_data.get("1H", {}).get("trend", "unknown")
                trend_4h = tf_data.get("4H", {}).get("trend", "unknown")
                trend_1d = tf_data.get("1D", {}).get("trend", "unknown")
                rsi_4h = tf_data.get("4H", {}).get("rsi")
                bb_width_4h = tf_data.get("4H", {}).get("bb_upper", 0) - tf_data.get("4H", {}).get("bb_lower", 0)
                suggested_tps = suggested_tps_by_symbol.get(symbol, [])

                json_tps = json.dumps(suggested_tps, ensure_ascii=False)

                prompt = f"""
Bạn là một trợ lý giao dịch crypto chuyên nghiệp.
Dưới đây là dữ liệu kỹ thuật của {symbol} theo từng khung thời gian:

{chr(10).join(summary_lines)}

Giá hiện tại: {current_price}
Các vùng Take Profit gợi ý theo kỹ thuật: {json_tps}

Xu hướng 1H: {trend_1h}, xu hướng 4H: {trend_4h}, xu hướng 1D: {trend_1d}, RSI 4H: {rsi_4h}\nMomentum 1H (pct, bb_width_ratio, atr_spike_ratio, volume_spike_ratio): {tf_data.get('1H', {}).get('pct_change_1h')}, {tf_data.get('1H', {}).get('bb_width_ratio')}, {tf_data.get('1H', {}).get('atr_spike_ratio')}, {tf_data.get('1H', {}).get('volume_spike_ratio')}

Hãy đánh giá xem có cơ hội giao dịch không dựa trên sự đồng thuận giữa các khung thời gian, RSI, Bollinger Bands và lực nến.

- Nếu không rõ xu hướng hoặc khung 4H chưa thực sự break, KHÔNG đề xuất giao dịch.
- Nếu có tín hiệu, hãy phân loại: "trend-follow", "technical bounce", "trap setup" hoặc "breakout anticipation".
- Xem trọng động lượng 1H: nếu momentum bùng nổ nhưng 4H/1D chưa chuyển hẳn, chỉ cho phép "breakout anticipation" với SL chặt và R:R ≥ 1.5.

Chỉ TRẢ VỀ nội dung JSON THUẦN TÚY, KHÔNG bao gồm ```json, ``` hoặc bất kỳ chú thích, văn bản mô tả nào bên ngoài JSON. Định dạng bắt buộc:
{{
  "symbol": "BTC/USDT",
  "direction": "Long hoặc Short",
  "entry_1": 12345.67,
  "entry_2": 12200.0,
  "stop_loss": 11950.0,
  "tp": [12450.0, 12600.0, 12800.0],
  "risk_level": "Low / Medium / High",
  "leverage": "3x / 5x / 10x",
  "confidence": "high / medium / low",
  "strategy_type": "trend-follow / technical bounce / trap setup / breakout anticipation",
  "key_watch": "Kháng cự gần 12500, chờ xác nhận breakout",
  "nhan_dinh": "Tín hiệu Long theo xu hướng, lực nến mạnh, nên chờ retest entry"
}}

⚠️ Lưu ý kỹ:
- Chỉ trả về JSON đúng chuẩn như trên, KHÔNG thêm bất kỳ ký tự lạ, mô tả hay định dạng markdown nào.
- Không sử dụng emoji hoặc ký tự đặc biệt trong output.
- Dùng dấu chấm cho số thập phân, KHÔNG dùng dấu phẩy tách hàng nghìn.

- Chỉ sử dụng ký tự ASCII chuẩn hoặc ký tự chữ/số thông thường. Không sử dụng ký tự Unicode ngoài tiếng Việt và tiếng Anh.
- Các trường `entry_1`, `entry_2`, `stop_loss`, `tp` PHẢI là số (float), KHÔNG để trong ngoặc kép.
- `tp` phải là một danh sách các số (mảng số thực).
- Không được thiếu bất kỳ trường nào trong JSON trên.
"""

                now = datetime.now(UTC)
                print(f"\n🤖 GPT analyzing {symbol} at {now.isoformat()}...")

                response = await client.chat.completions.create(
                    model="gpt-4o",
                    response_format={"type": "json_object"},
                    messages=[{"role": "user", "content": prompt.strip()}],
                    temperature=0.2,
                    max_tokens=1200,
                    timeout=30
                )

                reply = response.choices[0].message.content.strip()
                print(f"📩 GPT raw reply for {symbol}:", reply)

                # Strip leading/trailing non-json characters for safety
                json_start = reply.find('{')
                json_end = reply.rfind('}') + 1
                if json_start == -1 or json_end <= 0:
                    print(f"⚠️ Không tìm thấy JSON trong reply cho {symbol}")
                    continue
                cleaned = reply[json_start:json_end].strip()

                parsed = parse_signal_response(cleaned)

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
