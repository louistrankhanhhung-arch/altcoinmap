import subprocess
import time

blocks = ["block1", "block2", "block3"]

for block in blocks:
    print(f"\n🚀 Running {block}...")
    try:
        subprocess.run(["python", "main.py", block], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Lỗi khi chạy {block}: {e}")
    time.sleep(60)  # nghỉ 1 phút giữa các block
