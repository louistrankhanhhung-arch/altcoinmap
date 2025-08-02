import os
import openai
from datetime import datetime

openai.api_key = os.getenv("GPT_API")

# Dummy function to simulate data scanning
def get_market_data():
    return {
        "context": "BTC/USDT volume tăng, RSI giảm sâu, MA20 cắt xuống MA50.",
        "coins": [
            {"symbol": "BNB/USDT", "data": "..."},
            {"symbol": "PENDLE/USDT", "data": "..."},
        ]
    }

def build_signals():
    market_data = get_market_data()
    context = market_data["context"]
    coin_data = market_data["coins"]

    prompt = f'''
Bạn là một chuyên gia giao dịch crypto. Hãy phân tích và chọn ra các tín hiệu mạnh từ dữ liệu sau:

Bối cảnh thị trường chung:
{context}

Dữ liệu các đồng coin:
{coin_data}

Yêu cầu:
- Chỉ chọn tín hiệu đủ mạnh (breakout rõ ràng, volume vượt đỉnh, RSI quá mua/quá bán rõ).
- Chỉ phát tối đa 1 tín hiệu cho mỗi đồng coin.
- Trả về định dạng JSON gồm: pair, direction, entry_1, entry_2, stop_loss, tp [5 mục tiêu], risk_level, key_watch, analysis.
- Nếu không có tín hiệu mạnh, trả về null.

Trả lời bằng tiếng Việt.
'''

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        result = response.choices[0].message["content"]
        if "null" in result.lower():
            return []
        return [result]  # Should parse JSON here
    except Exception as e:
        print(f"GPT error: {e}")
        return []
