# Kết quả load test /predict — backpressure MAX_INFLIGHT=8, OpenCV 1 thread

Locust (client) đo end-to-end qua Nginx → K8s Service → pod; cột *server* lấy từ Prometheus.
Mỗi pod: 1 worker Gunicorn, limit 2 CPU, ORT_THREADS=2. Mỗi user gửi 1 ảnh mỗi 0.5–1.5 s.
Locust chạy 90 s mỗi mức; p50/p95/p99 tính trên mọi request kể cả request lỗi.

| Replicas | Users | RPS gửi | RPS thành công | Lỗi % | p50 (ms) | p95 (ms) | p99 (ms) | p95 server (ms) | p95 inference (ms) | CPU (core) | CPU throttled % |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 3 | 10 | 7.62 | 7.62 | 0.0 | 150 | 300 | 390 | 299.9 | 153.2 | 3.4 | 16.1 |
| 3 | 25 | 15.73 | 14.78 | 6.0 | 390 | 1200 | 1200 | 1317.7 | 197.2 | 5.2 | 49.5 |
| 3 | 50 | 26.35 | 17.48 | 33.66 | 1000 | 1400 | 1500 | 1459.2 | 199.4 | 6.0 | 86.0 |
| 3 | 100 | 67.89 | 16.37 | 75.89 | 5 | 1500 | 1700 | 1619.0 | 272.1 | 6.0 | 94.4 |
| 5 | 10 | 7.78 | 7.78 | 0.0 | 150 | 250 | 290 | 261.6 | 188.6 | 3.9 | 5.6 |
| 5 | 25 | 16.02 | 16.02 | 0.0 | 340 | 960 | 1200 | 977.5 | 298.2 | 8.0 | 33.8 |
| 5 | 50 | 20.91 | 18.29 | 12.55 | 1300 | 2300 | 2700 | 2678.3 | 462.0 | 9.4 | 51.2 |
| 5 | 100 | 54.51 | 19.46 | 64.3 | 8 | 2100 | 2300 | 2532.1 | 374.7 | 9.8 | 86.9 |
