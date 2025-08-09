import os
import subprocess
import time

# Config (env overrides)
ENFORCE_4H_CLOSE = os.getenv("ENFORCE_4H_CLOSE", "0")  # "1" = chờ nến 4H đóng; "0" = quét mỗi giờ
BLOCK_SLEEP = int(os.getenv("BLOCK_SLEEP", "60"))      # giây nghỉ giữa các block (mặc định 60s)

blocks = ["block1", "block2", "block3"]

print(f"⚙️ ENFORCE_4H_CLOSE={ENFORCE_4H_CLOSE} | BLOCK_SLEEP={BLOCK_SLEEP}s")

def _run_daily_report():
    """Gọi signal_tracker.py; script sẽ tự gửi báo cáo lúc 12:00–12:05 UTC nếu chưa gửi."""
    try:
        subprocess.run(["python", "signal_tracker.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Lỗi khi chạy báo cáo ngày: {e}")

for block in blocks:
    print(f"\n🚀 Running {block}...")
    try:
        # Truyền ENFORCE_4H_CLOSE xuống process con (main.py / gpt_signal_builder.py sẽ đọc)
        env = dict(os.environ)
        env["ENFORCE_4H_CLOSE"] = ENFORCE_4H_CLOSE
        subprocess.run(["python", "main.py", block], check=True, env=env)
    except subprocess.CalledProcessError as e:
        print(f"❌ Lỗi khi chạy {block}: {e}")
    except KeyboardInterrupt:
        print("⏹️ Dừng theo yêu cầu người dùng.")
        break

    # Mỗi vòng lặp, thử gửi báo cáo ngày (chỉ gửi khi đến 12:00 UTC và chưa gửi hôm nay)
    _run_daily_report()

    time.sleep(BLOCK_SLEEP)

# Sau khi chạy xong các block, gọi lại báo cáo để chắc chắn nếu sát 12:00 UTC
_run_daily_report()
