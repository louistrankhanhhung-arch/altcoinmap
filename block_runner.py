import os
import subprocess
import time

# Config (env overrides)
ENFORCE_4H_CLOSE = os.getenv("ENFORCE_4H_CLOSE", "0")  # "1" = chờ nến 4H đóng; "0" = quét mỗi giờ
BLOCK_SLEEP = int(os.getenv("BLOCK_SLEEP", "60"))      # giây nghỉ giữa các block (mặc định 60s)

blocks = ["block1", "block2", "block3"]

print(f"⚙️ ENFORCE_4H_CLOSE={ENFORCE_4H_CLOSE} | BLOCK_SLEEP={BLOCK_SLEEP}s")

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
    time.sleep(BLOCK_SLEEP)
