import os
import openai
import json
from datetime import datetime

openai.api_key = os.getenv("GPT_API")


def get_market_data():
    # Dummy data, sẽ thay bằng fetch thật sau
    return {
        "context": "BTC/USDT volume tăng, RSI giảm sâu, MA20 cắt xuống MA50.",
        "coins": [
            {"symbol": "BNB/USDT", "data": "..."},
            {"symbol": "PENDLE/USDT", "data": "..."},
        ]
    }


def build_signals():
    try:
        market_data = get_market_data()
        context = market_data["context"]
        coin_data = market_data["coins"]
        all_symbols = [coin["symbol"] for coin in coin_data]
        raw_signals = coin_data

        # Log dữ liệu input
        print("📘 Bối cảnh thị trường:")
        print(context)
        print("📈 Dữ liệu các coin:")
        for coin in coin_data:
            print(f"- {coin['symbol']}: {coin['data']}")

        # (Tùy chọn) lưu ra file để debug
        with open("debug_input.json", "w") as f:
            json.dump({"context": context, "coins": coin_data}, f, indent=2)

        prompt = f'''
Bạn là một chuyên gia giao dịch crypto. Hãy phân tích và chọn ra các tín hiệu mạnh từ dữ liệu sau:

Bối cảnh thị trường chung:
{context}

Dữ liệu các đồng coin:
{coin_data}

Yêu cầu:
- Chỉ chọn tín hiệu đủ mạnh (breakout rõ ràng, volume vượt đỉnh, RSI quá mua/quá bán rõ).
- Chỉ phát tối đa 1 tín hiệu cho mỗi đồng coin.
- Trả về định dạng JSON gồm: pair, direction, entry_1, entry_2, stop_loss, tp [5 mục tiêu], risk_level, key_watch, assessment.
- Nếu không có tín hiệu mạnh, trả về null.

Trả lời bằng tiếng Việt.
'''

        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )

        result = response.choices[0].message["content"]
        print("📤 GPT Output:")
        print(result)

        if "null" in result.lower():
            return [], all_symbols, raw_signals

        # Parse output từ GPT
        parsed = json.loads(result)
        return parsed, all_symbols, raw_signals

    except Exception as e:
        print(f"❌ GPT error: {e}")
        return [], [], []
