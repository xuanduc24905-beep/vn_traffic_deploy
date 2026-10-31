# Kết quả load test /predict — worker sync, probe timeout 1s

Locust (client) đo end-to-end qua Nginx → K8s Service → pod; cột *server* lấy từ Prometheus.
Mỗi pod: 1 worker Gunicorn, limit 2 CPU, ORT_THREADS=2. Mỗi user gửi 1 ảnh mỗi 0.5–1.5 s.
Locust chạy 90 s mỗi mức; p50/p95/p99 tính trên mọi request kể cả request lỗi.

| Replicas | Users | RPS gửi | RPS thành công | Lỗi % | p50 (ms) | p95 (ms) | p99 (ms) | p95 server (ms) | p95 inference (ms) | CPU (core) | CPU throttled % |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 3 | 10 | 7.48 | 7.48 | 0.0 | 180 | 390 | 510 | 202.4 | 199.2 | 3.8 | 6.4 |
| 3 | 25 | 13.81 | 13.81 | 0.0 | 580 | 1300 | 1700 | 284.4 | 280.9 | 5.7 | 24.6 |
| 3 | 50 | 17.36 | 12.35 | 28.87 | 1000 | 5300 | 6100 | 287.7 | 285.5 | 5.4 | 27.6 |
| 3 | 100 | 43.84 | 12.0 | 72.64 | 2 | 5700 | 7900 | 290.2 | 288.9 | 4.6 | 16.2 |
| 5 | 10 | 7.48 | 7.48 | 0.0 | 190 | 380 | 510 | 279.7 | 274.7 | 4.8 | 4.5 |
| 5 | 25 | 15.16 | 15.16 | 0.0 | 410 | 1100 | 1500 | 333.9 | 333.6 | 8.2 | 18.2 |
| 5 | 50 | 21.36 | 15.75 | 26.27 | 900 | 3100 | 3700 | 303.3 | 298.5 | 7.6 | 18.0 |
| 5 | 100 | 38.83 | 14.83 | 61.81 | 3 | 5500 | 12000 | 376.2 | 439.7 | 7.2 | 16.7 |
