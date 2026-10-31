"""Load test POST /predict.

Chạy headless 1 mức tải:
    locust -f loadtest/locustfile.py --host http://localhost:8088 \
        --headless -u 50 -r 10 -t 90s --csv results/locust_u50

Ảnh lấy ngẫu nhiên từ tập test (nhiều camera) để tải giống thực tế;
đổi thư mục bằng biến LOCUST_IMG_DIR.
"""
import os
import random
from pathlib import Path

from locust import HttpUser, between, task

IMG_DIR = Path(os.getenv("LOCUST_IMG_DIR", "/home/xuand/vn_traffic_ai/data/merged_v5/images/test"))
N_IMAGES = int(os.getenv("LOCUST_N_IMAGES", "50"))

# Đọc sẵn vào RAM để client không bị nghẽn ở đĩa
_all = sorted(IMG_DIR.glob("*.jpg"))
IMAGES = [(p.name, p.read_bytes()) for p in _all[:: max(1, len(_all) // N_IMAGES)][:N_IMAGES]]
if not IMAGES:
    raise SystemExit(f"Không có ảnh .jpg trong {IMG_DIR}")


class PredictUser(HttpUser):
    # Mỗi user (≈ 1 camera/ứng dụng) gửi 1 ảnh mỗi 0.5–1.5 s
    wait_time = between(0.5, 1.5)

    @task(10)
    def predict(self):
        name, data = random.choice(IMAGES)
        with self.client.post("/predict", files={"file": (name, data, "image/jpeg")},
                              name="/predict", catch_response=True) as r:
            if r.status_code != 200:
                r.failure(f"HTTP {r.status_code}")
            elif "detections" not in r.json():
                r.failure("thiếu detections trong response")

    @task(1)
    def health(self):
        self.client.get("/health", name="/health")
