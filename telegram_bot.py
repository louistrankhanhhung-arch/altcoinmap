import os
import requests
import time

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
                message_id = send_message_with_retry(text)
                s["message_id"] = message_id
    elif isinstance(signals, str):
        send_message(signals)

def send_message(text, reply_to_id=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": USER_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_to_id:
        data["reply_to_message_id"] = reply_to_id

    # Basic send once (kept for backward compatibility); returns message_id or None
    print(f"[SEND] {text[:80]}..." if len(text) > 80 else f"[SEND] {text}")
    try:
        response = requests.post(url, json=data, timeout=10)
        if response.status_code != 200:
            print(f"❌ Failed to send message: {response.status_code} - {response.text}")
            return None
        res = response.json()
        msg = res.get("result")
        if isinstance(msg, dict):
            mid = msg.get("message_id")
            if mid is None:
                print(f"⚠️ Telegram returned no message_id. Payload: {res}")
            else:
                print(f"✅ Message sent. message_id={mid}")
            return mid
        print(f"⚠️ Unexpected Telegram response format: {res}")
    except Exception as e:
        print(f"❌ Telegram send failed: {e}")
    return None

def send_message_with_retry(text, reply_to_id=None, retries=3):
    backoff = 1.0
    for attempt in range(1, retries+1):
        mid = send_message(text, reply_to_id=reply_to_id)
        if mid is not None:
            return mid
        time.sleep(backoff)
        backoff = min(backoff * 2, 8)
    return None

decimal_map = {
    # MAJORS
    "BTC": 2, "ETH": 2, "BNB": 2, "SOL": 2, "ADA": 4, "TRX": 5,
    # LARGE CAP ALTS
    "LINK": 2, "AVAX": 2, "NEAR": 3, "INJ": 2, "ATOM": 2, "AAVE": 2, "UNI": 2, "FIL": 2,
    # MID CAP ALTS
    "ARB": 4, "SUI": 4, "PENDLE": 3, "APT": 3, "OP": 3, "STRK": 3, "DYDX": 3, "GMX": 2, "TIA": 3, "ENS": 2, "FET": 3, "RPL": 3,
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

        # Lấy danh sách TP từ các key khác nhau
        tp_raw = s.get("tp") or s.get("take_profits") or [s.get(k) for k in ["tp1", "tp2", "tp3", "tp4", "tp5"]]
        tp_list = [p for p in tp_raw if p is not None]

        
        entry2_line = ""
        if s.get("entry_2") is not None:
            entry2_line = f"<b>Entry 2:</b> {format_price(s.get('entry_2'), base_symbol)}\n"

        return (
            f"<b>{pair} | {s.get('direction', '?').upper()}</b>\n"
            f"<b>Entry 1:</b> {format_price(s.get('entry_1'), base_symbol)}\n"
            f"{entry2_line}"
            f"<b>SL:</b> {format_price(s.get('stop_loss'), base_symbol)}\n"
            f"<b>TPs:</b> {', '.join(format_price(p, base_symbol) for p in tp_list)}\n"
            f"<b>Assessment:</b> {s.get('assessment', 'Không có đánh giá')}\n"
            f"<b>Risk:</b> {s.get('risk_level', '?')} | <b>Leverage:</b> {s.get('leverage', 'x5')}\n"
            f"{f'<b>Strategy:</b> {s.get('strategy_type')}\n' if s.get('strategy_type') else ''}"
            f"<b>Confidence:</b> {s.get('confidence', '?')}\n"
            f"<b>Key Watch:</b> {s.get('key_watch', '...')}"
        )
    except Exception as e:
        return "⚠️ Định dạng tín hiệu lỗi: " + str(e)

