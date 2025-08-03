import requests
import time
from datetime import datetime, timezone

def fetch_coin_data(symbol, interval="4hour", limit=100):
    base_url = "https://api.kucoin.com/api/v1/market/candles"
    symbol_kucoin = symbol.replace("/", "-")

    params = {
        "symbol": symbol_kucoin,
        "type": interval,
        "limit": limit
    }

    for attempt in range(3):
        try:
            response = requests.get(base_url, params=params, timeout=10)
            if response.status_code != 200:
                raise Exception(f"Lỗi API Kucoin: {response.text}")

            data = response.json()
            if data.get("code") != "200000":
                raise Exception(f"Kucoin trả về lỗi: {data}")

            candles = data["data"]

            result = []
            for c in reversed(candles):  # đảo ngược về thời gian gần nhất
                result.append({
                    "time": datetime.fromtimestamp(c[0] / 1000, tz=timezone.utc).isoformat(),
                    "open": float(c[1]),
                    "close": float(c[2]),
                    "high": float(c[3]),
                    "low": float(c[4]),
                    "volume": float(c[5])
                })

            return result
        except Exception as e:
            print(f"⛔️ Lỗi khi fetch {symbol} (thử {attempt+1}/3): {e}")
            time.sleep(1)

    raise Exception(f"❌ Không thể fetch dữ liệu cho {symbol} sau 3 lần thử.")


def fetch_realtime_price(symbol):
    base_url = "https://api.kucoin.com/api/v1/market/orderbook/level1"
    symbol_kucoin = symbol.replace("/", "-")
    params = {"symbol": symbol_kucoin}

    response = requests.get(base_url, params=params, timeout=10)
    if response.status_code != 200:
        raise Exception(f"Lỗi realtime price Kucoin: {response.text}")

    data = response.json()
    return float(data["data"]["price"])


def get_market_data(symbols: list[str], interval="4hour", limit=100):
    """Hàm gộp để dùng trong main.py"""
    result = {}
    for symbol in symbols:
        result[symbol] = fetch_coin_data(symbol, interval, limit)
    return result
