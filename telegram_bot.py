import os
import requests

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
USER_ID = os.getenv("USER_ID")

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
        "chat_id": USER_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    response = requests.post(url, json=data)
    
    if response.status_code != 200:
        print(f"❌ Failed to send message: {response.status_code} - {response.text}")
    else:
        print("✅ Message sent to Telegram.")

decimal_map = {
    "BTC": 2,
    "ETH": 2,
    "BNB": 2,
    "AVAX": 2,
    "LINK": 2,
    "INJ": 2,
    "NEAR": 3,
    "PENDLE": 3,
    "ARB": 4,
    "SUI": 4,
}
def format_price(val, symbol="BTC"):
    decimals = decimal_map.get(symbol.split("/")[0], 2)
    return f"{val:,.{decimals}f}"


def format_message(s):
    try:
        pair = s['pair']  # e.g. "BTC/USDT"
        base_symbol = pair.split("/")[0]  # "BTC"
        return f"""<b>{pair} | {s['direction'].upper()}</b>
🎯 <b>Entry:</b> {format_price(s['entry_1'], base_symbol)} / {format_price(s['entry_2'], base_symbol)}
📉 <b>SL:</b> {format_price(s['stop_loss'], base_symbol)}
💰 <b>TPs:</b> {', '.join(format_price(p, base_symbol) for p in s['tp'])}
🧭 <b>Strategy:</b> {s['strategy']}
🧠 <b>Assessment:</b> {s['assessment']}
⚖️ <b>Risk:</b> {s['risk_level']} | <b>Leverage:</b> {s.get('leverage', 'x5')}
🔍 <b>Key Watch:</b> {s['key_watch']}"""
    except Exception as e:
        return "⚠️ Định dạng tín hiệu lỗi: " + str(e)


