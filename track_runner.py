import time
from signal_tracker import check_signals

INTERVAL_MINUTES = 30

if __name__ == "__main__":
    print("🚦 Bắt đầu theo dõi tín hiệu (mỗi 30 phút)...")
    while True:
        try:
            check_signals()
            print("✅ Đã kiểm tra tín hiệu.")
        except Exception as e:
            print(f"❌ Lỗi khi chạy check_signals: {e}")
        time.sleep(INTERVAL_MINUTES * 60)
