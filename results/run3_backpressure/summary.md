# Kết quả load test /predict — backpressure (1 inference/lần, MAX_INFLIGHT=4, 503), liveness TCP, Nginx max_fails=0

Locust (client) đo end-to-end qua Nginx → K8s Service → pod; cột *server* lấy từ Prometheus.
Mỗi pod: 1 worker Gunicorn, limit 2 CPU, ORT_THREADS=2. Mỗi user gửi 1 ảnh mỗi 0.5–1.5 s.
Locust chạy 90 s mỗi mức; p50/p95/p99 tính trên mọi request kể cả request lỗi.

| Replicas | Users | RPS gửi | RPS thành công | Lỗi % | p50 (ms) | p95 (ms) | p99 (ms) | p95 server (ms) | p95 inference (ms) | CPU (core) | CPU throttled % |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 3 | 10 | 6.3 | 6.27 | 0.36 | 390 | 860 | 980 | 876.6 | 423.2 | 4.3 | 23.3 |
| 3 | 25 | 14.22 | 9.16 | 35.61 | 660 | 1300 | 1300 | 1426.6 | 485.7 | 5.6 | 53.5 |
| 3 | 50 | 34.29 | 9.08 | 73.51 | 9 | 1300 | 1400 | 1397.2 | 488.9 | 6.0 | 74.7 |
| 3 | 100 | 79.39 | 11.28 | 85.8 | 7 | 1100 | 1500 | 1064.5 | 456.6 | 6.0 | 85.6 |
| 5 | 10 | 7.5 | 7.5 | 0.0 | 190 | 390 | 500 | 397.7 | 274.1 | 4.1 | 10.7 |
| 5 | 25 | 16.58 | 15.21 | 8.25 | 360 | 810 | 910 | 847.6 | 294.3 | 7.6 | 26.9 |
| 5 | 50 | 30.8 | 18.35 | 40.43 | 550 | 1200 | 1300 | 1373.8 | 462.0 | 9.8 | 52.9 |
| 5 | 100 | 72.66 | 19.89 | 72.63 | 7 | 1000 | 1100 | 1210.4 | 299.3 | 10.1 | 75.6 |
