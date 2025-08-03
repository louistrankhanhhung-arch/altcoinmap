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
Bạn là chuyên gia phân tích kỹ thuật crypto.

Bối cảnh thị trường:
{context}

Dữ liệu từng coin (multi-timeframe + chỉ báo kỹ thuật):
{json.dumps(coins, indent=2, ensure_ascii=False)}

Yêu cầu:
- Ưu tiên breakout, breakdown rõ (volume xác nhận).
- Cho phép tín hiệu pullback hoặc hồi trong range nếu có tín hiệu rõ.
- Loại Long nếu RSI thấp và nến đỏ xác nhận. Ngược lại với Short.
- Bỏ qua tín hiệu nếu Entry nằm lệch so với vùng hỗ trợ/kháng cự chính (MA20/MA50).
- Không dùng nếu không có xác nhận volume.
- Đánh giá strength, tư vấn leverage phù hợp.
- Entry gần với giá realtime.
- Tối đa 1 tín hiệu/coin, chỉ giữ "strong" hoặc "moderate".

Trả về JSON:
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
    "assessment": "Nhận định ngắn gọn, không phóng đại",
    "strength": "strong" hoặc "moderate"
  }}
]

Chỉ trả JSON thuần bằng tiếng Việt.
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
