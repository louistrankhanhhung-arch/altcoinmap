# ============================
# 📁 File: gpt_signal_builder.py
# ============================

import openai
import os

openai.api_key = os.getenv("GPT_API")

COINS = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "LINK/USDT", "AVAX/USDT", "NEAR/USDT", "ARB/USDT", "SUI/USDT", "PENDLE/USDT"]

# Placeholder for historical data loader
def load_price_data():
    # Normally fetch from an API or DB, return simplified format here
    return {"BTC/USDT": [{"close": 59000, "volume": 300}, ...]}  # 100 candles per coin

def build_prompt(data):
    return f"""
You are a crypto trading assistant. Given 100 sessions of 4H OHLCV, MA20, MA50, Bollinger Bands, and RSI for each coin below:

{data}

Select ONLY strong signals, return JSON in this format:
{{
  "pair": "BTC/USDT",
  "direction": "long",
  "entry_1": 59000,
  "entry_2": 58600,
  "stop_loss": 57800,
  "tp": [60000, 61000, 62000, 63000, 64000],
  "strategy": "Breakout with confirmation from BTC context",
  "assessment": "Clear breakout supported by strong RSI and BTC trend.",
  "risk_level": "Medium",
  "key_watch": "Maintain above 58600 to confirm trend",
  "leverage": "x5"
}}
If no valid signal, return empty JSON.
"""

def build_trading_signal():
    market_data = load_price_data()
    prompt = build_prompt(market_data)
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        result = response.choices[0].message.content
        return result
    except Exception as e:
        print(f"GPT error: {e}")
        return None


