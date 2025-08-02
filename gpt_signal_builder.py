import os  
import json
import re
from datetime import datetime
from kucoin_api import fetch_coin_data, fetch_realtime_price
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_market_data():
    symbols = [
        "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "LINK/USDT",
        "NEAR/USDT", "AVAX/USDT", "ARB/USDT", "SUI/USDT", "PENDLE/USDT"
    ]
    coin_data = []

    for symbol in symbols:
        try:
            data = fetch_coin_data(symbol)
            realtime = fetch_realtime_price(symbol)
            coin_data.append({"symbol": symbol, "data": data, "realtime": realtime})
        except Exception as e:
            print(f"❌ Lỗi khi fetch {symbol}: {e}")

    context = "Phân tích kỹ thuật tổng thể dựa trên BTC/USDT hoặc market cap... (placeholder)"

    return {
        "context": context,
        "coins": coin_data
    }

def build_signals():
    try:
        market_data = get_market_data()
        context = market_data["context"]
        coin_data = market_data["coins"]
        all_symbols = [coin["symbol"] for coin in coin_data]
        raw_signals = coin_data

        print("📘 Bối cảnh thị trường:")
        print(context)
        print("📈 Dữ liệu các coin:")
        for coin in coin_data:
            print(f"- {coin['symbol']}: {coin['data'][-1]} | Realtime: {coin['realtime']}")

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M")
        debug_filename = f"debug_input_{timestamp}.json"
        with open(debug_filename, "w") as f:
            json.dump({"context": context, "coins": coin_data}, f, indent=2)

        prompt = f'''
Bạn là một chuyên gia giao dịch crypto. Hãy phân tích và chọn ra các tín hiệu mạnh từ dữ liệu sau:

Bối cảnh thị trường chung:
{context}

Dữ liệu các đồng coin:
{coin_data}

Yêu cầu:
- Ưu tiên các tín hiệu có xác suất cao: breakout rõ ràng (cho Long), breakdown mạnh (cho Short), volume vượt đỉnh, RSI quá mua/quá bán rõ.
- Ngoài ra, chấp nhận các tín hiệu pullback (về MA, vùng hỗ trợ/kháng cự) hoặc sideways range có biến động tăng dần nếu có tín hiệu hồi phục hoặc đảo chiều rõ ràng.
- Với mỗi tín hiệu, đánh giá mức độ: "strong", "moderate", hoặc "weak" và chỉ giữ tín hiệu "strong" hoặc "moderate".
- Nếu có tín hiệu Long và Short đồng thời trên cùng một đồng coin, chỉ giữ tín hiệu có xác suất cao hơn.
- Tư vấn đòn bẩy (leverage) phù hợp với mức độ rủi ro của tín hiệu (ví dụ: x3 cho tín hiệu có rủi ro cao, x10 cho tín hiệu an toàn và rõ ràng).
- Entry 1 và Entry 2 nên nằm quanh giá real-time (giá realtime đã được cung cấp cho từng coin).
- Chỉ phát tối đa 1 tín hiệu cho mỗi đồng coin.
- Nếu không có tín hiệu mạnh, loại bỏ coin đó khỏi kết quả.
- Trả về **chỉ JSON thuần túy** theo định dạng:
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
    "assessment": "Viết nhận định ngắn gọn, đúng bản chất tín hiệu kỹ thuật, không phóng đại",
    "strength": "strong" hoặc "moderate"
  }}
]

Trả lời bằng tiếng Việt, dùng từ ngữ tài chính – kỹ thuật phù hợp với trader Việt. Không thêm giải thích ngoài JSON.
'''

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )

        result = response.choices[0].message.content.strip()

        json_start = result.find("[")
        json_end = result.rfind("]")
        if json_start == -1 or json_end == -1:
            print("⚠️ Không tìm thấy JSON hợp lệ trong GPT output.")
            return [], all_symbols, raw_signals

        result = result[json_start:json_end + 1]

        print("📤 GPT Output:")
        print(result)

        if "null" in result.lower():
            return [], all_symbols, raw_signals

        try:
            parsed = json.loads(result)
        except json.JSONDecodeError as e:
            print(f"❌ JSON decode error: {e}")
            print("🔍 Raw GPT result:")
            print(result)
            return [], all_symbols, raw_signals

        required_keys = {"pair", "direction", "entry_1", "entry_2", "stop_loss", "tp", "risk_level", "leverage", "key_watch", "assessment", "strength"}
        valid_signals = []

        for s in parsed:
            if all(k in s for k in required_keys):
                valid_signals.append(s)
            else:
                print(f"⚠️ Thiếu trường trong tín hiệu: {s}")

        return valid_signals, all_symbols, raw_signals

    except Exception as e:
        print(f"❌ GPT error: {e}")
        return [], [], []
