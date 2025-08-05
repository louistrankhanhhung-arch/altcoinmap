import os
import requests

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
USER_ID = os.getenv("USER_ID")

def send_signals(signals):
    if not BOT_TOKEN or not USER_ID:
        print("⚠️ Chưa thiết lập TELEGRAM_TOKEN hoặc USER_ID.")
        return

    if not signals:
        return  # Không gửi thông báo nếu không có tín hiệu mạnh

    if isinstance(signals, list):
        for s in signals:
            if isinstance(s, str):
                send_message(s)
            else:
                if 'pair' not in s:
                    s['pair'] = s.get('symbol', 'UNKNOWN')
                text = format_message(s)
                send_message(text)
    elif isinstance(signals, str):
        send_message(signals)

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": USER_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    print(f"🔔 [SEND] {text[:80]}..." if len(text) > 80 else f"🔔 [SEND] {text}")
    try:
        response = requests.post(url, json=data, timeout=10)
        if response.status_code != 200:
            print(f"❌ Failed to send message: {response.status_code} - {response.text}")
        else:
            print("✅ Message sent to Telegram.")
    except Exception as e:
        print(f"❌ Telegram send failed: {e}")

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
    try:
        if val is None:
            return "?"
        decimals = decimal_map.get(symbol.split("/")[0], 2)
        return f"{val:,.{decimals}f}"
    except Exception as e:
        print(f"⚠️ Giá trị không hợp lệ: {val}, lỗi: {e}")
        return "?"

def format_message(s):
    try:
        pair = s['pair']
        base_symbol = pair.split("/")[0]
        return f"""<b>{pair} | {s.get('direction', '?').upper()}</b>
🎯 <b>Entry 1:</b> {format_price(s['entry_1'], base_symbol)}
🎯 <b>Entry 2:</b> {format_price(s['entry_2'], base_symbol)}
📉 <b>SL:</b> {format_price(s['stop_loss'], base_symbol)}
💰 <b>TPs:</b> {', '.join(format_price(p, base_symbol) for p in s['tp'])}
🧠 <b>Assessment:</b> {s.get('assessment', 'Không có đánh giá')}
⚖️ <b>Risk:</b> {s.get('risk_level', '?')} | <b>Leverage:</b> {s.get('leverage', 'x5')}
📐 <b>Strategy:</b> {s.get('strategy_type', '...')}
🔎 <b>Confidence:</b> {s.get('confidence', '?')}
🔍 <b>Key Watch:</b> {s.get('key_watch', '...')}"""
    except Exception as e:
        return "⚠️ Định dạng tín hiệu lỗi: " + str(e)
