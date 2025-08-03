import os
import json
from datetime import datetime
from kucoin_api import fetch_coin_data, fetch_realtime_price
from openai import OpenAI
from indicators import compute_indicators_for_all_timeframes

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

symbols = [
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT",
    "LINK/USDT", "NEAR/USDT", "AVAX/USDT", "ARB/USDT",
    "SUI/USDT", "PENDLE/USDT"
]

interval_map = {
    "1H": "1hour",
    "4H": "4hour",
    "1D": "1day"
}

def get_market_data(target_symbols):
    coins = []

    for symbol in target_symbols:
        try:
            coin = {"symbol": symbol, "realtime": fetch_realtime_price(symbol)}
            for tf, kucoin_tf in interval_map.items():
                coin[tf] = fetch_coin_data(symbol, interval=kucoin_tf, limit=100)
            compute_indicators_for_all_timeframes(coin)  # Add RSI, MA20, MA50, BB
            coins.append(coin)
        except Exception as e:
            print(f"❌ Lỗi khi fetch dữ liệu {symbol}: {e}")

    return coins

def build_prompt(context, coins):
    return f'''
Bạn là một chuyên gia phân tích kỹ thuật crypto có nhiều kinh nghiệm.

🎯 Nhiệm vụ: Phân tích kỹ dữ liệu của từng đồng coin (gồm các khung thời gian 1H, 4H, 1D) và chọn ra các tín hiệu giao dịch mạnh, đáng tin cậy để Long hoặc Short.

---

🧠 **Bối cảnh thị trường chung**:
{context}

---

📈 **Dữ liệu từng đồng coin** (theo từng khung thời gian, đã tính RSI, MA20, MA50, Bollinger Bands):

{json.dumps(coins, indent=2, ensure_ascii=False)}

---

📌 **Yêu cầu phân tích**:

1. Với mỗi đồng coin, đánh giá xu hướng ở từng khung thời gian:
   - <b>1H trend</b>: dựa vào hướng MA20, MA50 và vị trí giá so với MA.
   - <b>4H trend</b>: dùng để xác định cấu trúc sóng chính (ưu tiên xác nhận).
   - <b>1D trend</b>: dùng để lọc bối cảnh lớn, xác định lực thị trường chung.

2. Ưu tiên các tín hiệu có hội tụ từ nhiều khung:
   - Ví dụ: 1H breakout, 4H đang có mô hình hồi, 1D vẫn còn uptrend.

3. Lọc tín hiệu theo logic sau:
   - Ưu tiên breakout rõ (Long khi vượt kháng cự kèm volume, Short khi thủng hỗ trợ).
   - Chấp nhận pullback nếu có tín hiệu đảo chiều rõ (ví dụ bullish engulfing trên hỗ trợ).
   - Không nhận Long nếu RSI < 40 + nến xác nhận đỏ. Không nhận Short nếu RSI > 60 + nến xanh.
   - Bỏ qua nếu tín hiệu không khớp với xu hướng lớn (ví dụ short ở khung nhỏ nhưng khung lớn đang uptrend mạnh).
   - Volume phải xác nhận cho tín hiệu breakout/pullback.

4. Điều kiện tín hiệu hợp lệ:
   - Entry quanh vùng giá realtime.
   - TP1–TP5 phải hợp lý với cấu trúc giá và BB.
   - Stop Loss rõ ràng, không đặt quá gần Entry.
   - Nếu Entry nằm lệch hẳn MA20/MA50 hoặc phía sai so với BB – loại tín hiệu.

5. Thông tin mỗi tín hiệu cần gồm:
   - Nhận định đa khung gọn gàng, nêu rõ vì sao đây là tín hiệu tốt (ví dụ: 4H breakout xác nhận, 1D giữ uptrend).
   - Rủi ro (risk_level): high / medium / low.
   - Leverage khuyến nghị theo rủi ro.
   - Key watch: chỉ số/chỉ báo/nến cần theo dõi tiếp theo để xác nhận tín hiệu.

6. Với mỗi coin, chỉ trả tối đa 1 tín hiệu mạnh nhất.
7. Chỉ giữ lại các tín hiệu có strength là "strong" hoặc "moderate".

---

📤 **Kết quả trả về**: <b>Chỉ trả JSON thuần</b> dạng:

[
  {{
    "pair": "...",
    "direction": "Long" hoặc "Short",
    "entry_1": ..., 
    "entry_2": ..., 
    "stop_loss": ..., 
    "tp": [tp1, tp2, tp3, tp4, tp5],
    "risk_level": "...",
    "leverage": "...",
    "key_watch": "...",
    "assessment": "Nhận định kỹ thuật ngắn gọn, đúng bản chất, không phóng đại",
    "strength": "strong" hoặc "moderate"
  }}
]

⛔ Không đưa bất kỳ nhận xét, giải thích hay văn bản nào ngoài JSON.

⛔ Trả lời bằng tiếng Việt với ngôn ngữ tài chính – kỹ thuật dành cho trader chuyên nghiệp.
'''

def build_signals(target_symbols=symbols):
    try:
        context = "Tổng quan thị trường đang được đánh giá trung tính đến tích cực, BTC giữ trên MA50 khung ngày."
        coins = get_market_data(target_symbols)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M")
        debug_filename = f"debug_input_{timestamp}.json"
        with open(debug_filename, "w") as f:
            json.dump({"context": context, "coins": coins}, f, indent=2)

        prompt = build_prompt(context, coins)

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )

        result = response.choices[0].message.content.strip()
        json_start = result.find("[")
        json_end = result.rfind("]")

        if json_start == -1 or json_end == -1:
            print("⚠️ Không tìm thấy JSON hợp lệ trong GPT output.")
            return [], [coin["symbol"] for coin in coins], coins

        parsed = json.loads(result[json_start:json_end + 1])

        required_keys = {"pair", "direction", "entry_1", "entry_2", "stop_loss", "tp", "risk_level", "leverage", "key_watch", "assessment", "strength"}
        valid_signals = [s for s in parsed if required_keys.issubset(s.keys())]

        return valid_signals, [coin["symbol"] for coin in coins], coins

    except Exception as e:
        print(f"❌ GPT error: {e}")
        return [], [], []
