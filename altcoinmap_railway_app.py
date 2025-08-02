# Project: Altcoin Map Pro - Railway Deployment Version
# Structure: GPT-powered signal generator with Telegram integration and scheduling

# ============================
# 📁 File: main.py
# ============================

from gpt_signal_builder import build_trading_signal
from telegram_bot import send_signal
import os

if __name__ == '__main__':
    signal = build_trading_signal()
    if signal:
        send_signal(signal)
    else:
        send_signal({"message": "⚠️ No strong signals found in this scan."})


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


# ============================
# 📁 File: telegram_bot.py
# ============================

import os
import requests
import json

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("BOT_CHANNEL_ID")

def send_signal(signal):
    if isinstance(signal, str):
        text = signal
    elif isinstance(signal, dict) and "message" in signal:
        text = signal["message"]
    else:
        text = format_signal(signal)

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHANNEL_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    response = requests.post(url, json=data)
    print(response.status_code, response.text)


def format_signal(s):
    return f"""
<b>{s['pair']} | {s['direction'].upper()}</b>
🎯 <b>Entry:</b> {s['entry_1']} / {s['entry_2']}
📉 <b>SL:</b> {s['stop_loss']}
💰 <b>TPs:</b> {', '.join(map(str, s['tp']))}
🧭 <b>Strategy:</b> {s['strategy']}
🧠 <b>Assessment:</b> {s['assessment']}
⚖️ <b>Risk:</b> {s['risk_level']} | <b>Leverage:</b> {s['leverage']}
🔍 <b>Key Watch:</b> {s['key_watch']}
"""


# ============================
# 📁 File: requirements.txt
# ============================
openai
requests
python-dotenv


# ============================
# 📁 File: .env (example only - don't expose in production)
# ============================
GPT_API=your_openai_api_key_here
TELEGRAM_TOKEN=your_bot_token_here
BOT_CHANNEL_ID=@your_channel_id_here
