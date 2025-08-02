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
