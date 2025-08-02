import os 
import json
from datetime import datetime
from kucoin_api import fetch_coin_data  # 🆕 Giả định bạn có file kucoin_api.py xử lý dữ liệu
from openai import OpenAI

from openai import OpenAI

client = OpenAI(api_key=os.getenv("GPT_API"))

def get_market_data():
    symbols = [
        "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "LINK/USDT",
        "NEAR/USDT", "AVAX/USDT", "ARB/USDT", "SUI/USDT", "PENDLE/USDT"
    ]
    coin_data = []

    for symbol in symbols:
        try:
            data = fetch_coin_data(symbol)
            coin_data.append({"symbol": symbol, "data": data})
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
            print(f"- {coin['symbol']}: {coin['data']}")

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
- Chỉ chọn tín hiệu đủ mạnh (ví dụ: breakout rõ ràng để vào lệnh Long hoặc breakdown mạnh để vào lệnh Short, volume vượt đỉnh, RSI quá mua/quá bán rõ).
- Tư vấn đòn bẩy (leverage) phù hợp với mức độ rủi ro của tín hiệu (ví dụ: x3 cho tín hiệu có rủi ro cao, x10 cho tín hiệu an toàn và rõ ràng).
- Chỉ phát tối đa 1 tín hiệu cho mỗi đồng coin.
- Trả về định dạng JSON gồm: pair, direction, entry_1, entry_2, stop_loss, tp [5 mục tiêu], risk_level, leverage, key_watch, assessment.
- Nếu không có tín hiệu mạnh, trả về null.

Trả lời bằng tiếng Việt.
'''

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )

        result = response.choices[0].message.content
        print("📤 GPT Output:")
        print(result)

        if "null" in result.lower():
            return [], all_symbols, raw_signals

        parsed = json.loads(result)
        return parsed, all_symbols, raw_signals

    except Exception as e:
        print(f"❌ GPT error: {e}")
        return [], [], []
