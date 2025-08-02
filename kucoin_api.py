import requests
import pandas as pd
import numpy as np

def fetch_coin_data(symbol: str, interval="4hour", limit=100):
    """
    Fetch historical OHLCV data from Kucoin and calculate indicators.
    """
    base_url = "https://api.kucoin.com"
    symbol_formatted = symbol.replace("/", "-")
    url = f"{base_url}/api/v1/market/candles?type={interval}&symbol={symbol_formatted}&limit={limit}"

    try:
        response = requests.get(url)
        response.raise_for_status()
        raw = response.json()["data"]
    except Exception as e:
        raise RuntimeError(f"Lỗi khi gọi API Kucoin: {e}")

    # Format data to DataFrame
    df = pd.DataFrame(raw, columns=["timestamp", "open", "close", "high", "low", "volume", "turnover"])
    df = df.iloc[::-1].reset_index(drop=True)
    df[["open", "close", "high", "low", "volume"]] = df[["open", "close", "high", "low", "volume"]].astype(float)

    # Tính chỉ báo
    df["MA20"] = df["close"].rolling(window=20).mean()
    df["MA50"] = df["close"].rolling(window=50).mean()
    df["stddev"] = df["close"].rolling(window=20).std()
    df["UpperBB"] = df["MA20"] + 2 * df["stddev"]
    df["LowerBB"] = df["MA20"] - 2 * df["stddev"]

    # RSI
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df["RSI"] = 100 - (100 / (1 + rs))

    # Chỉ lấy 1 dòng mới nhất
    last = df.iloc[-1]
    return {
        "close": last["close"],
        "volume": last["volume"],
        "MA20": round(last["MA20"], 4),
        "MA50": round(last["MA50"], 4),
        "UpperBB": round(last["UpperBB"], 4),
        "LowerBB": round(last["LowerBB"], 4),
        "RSI": round(last["RSI"], 2),
        "price_above_ma20": last["close"] > last["MA20"],
        "price_above_ma50": last["close"] > last["MA50"],
        "bb_breakout": last["close"] > last["UpperBB"],
        "bb_breakdown": last["close"] < last["LowerBB"],
    }
