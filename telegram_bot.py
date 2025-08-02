import os
import requests

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("BOT_CHANNEL_ID")

def send_signals(signals):
    if not signals:
        send_message("⚠️ Không có tín hiệu đủ mạnh ở thời điểm này.")
        return

    for s in signals:
        text = format_message(s)
        send_message(text)

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHANNEL_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    requests.post(url, json=data)

def format_message(s):
    try:
        return f"""<b>{s['pair']} | {s['direction'].upper()}</b>
🎯 <b>Entry:</b> {s['entry_1']} / {s['entry_2']}
📉 <b>SL:</b> {s['stop_loss']}
💰 <b>TPs:</b> {', '.join(map(str, s['tp']))}
🧭 <b>Strategy:</b> {s['strategy']}
🧠 <b>Assessment:</b> {s['assessment']}
⚖️ <b>Risk:</b> {s['risk_level']} | <b>Leverage:</b> {s.get('leverage', 'x5')}
🔍 <b>Key Watch:</b> {s['key_watch']}"""
    except Exception as e:
        return "⚠️ Định dạng tín hiệu lỗi: " + str(e)
