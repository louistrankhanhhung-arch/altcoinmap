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


