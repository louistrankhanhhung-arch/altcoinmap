import requests
import time

def fetch_coin_data(symbol, interval="4hour", limit=100):
    base_url = "https://api.kucoin.com/api/v1/market/candles"
    symbol_kucoin = symbol.replace("/", "-")

    params = {
        "symbol": symbol_kucoin,
        "type": interval,
        "limit": limit
    }

    response = requests.get(base_url, params=params)
    if response.status_code != 200:
        raise Exception(f"Lỗi API Kucoin: {response.text}")

    data = response.json()
    if data.get("code") != "200000":
        raise Exception(f"Kucoin trả về lỗi: {data}")

    candles = data["data"]

    result = []
    for c in reversed(candles):  # đảo ngược về thời gian gần nhất
        result.append({
            "time": c[0],
            "open": float(c[1]),
            "close": float(c[2]),
            "high": float(c[3]),
            "low": float(c[4]),
            "volume": float(c[5])
        })

    return result

def fetch_realtime_price(symbol):
    base_url = "https://api.kucoin.com/api/v1/market/orderbook/level1"
    symbol_kucoin = symbol.replace("/", "-")
    params = {"symbol": symbol_kucoin}
    response = requests.get(base_url, params=params)
    if response.status_code != 200:
        raise Exception(f"Lỗi realtime price Kucoin: {response.text}")
    data = response.json()
    return float(data["data"]["price"])
