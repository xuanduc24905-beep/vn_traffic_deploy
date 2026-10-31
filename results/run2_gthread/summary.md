# Kết quả load test /predict — worker gthread x4, probe timeout 3-5s

Locust (client) đo end-to-end qua Nginx → K8s Service → pod; cột *server* lấy từ Prometheus.
Mỗi pod: 1 worker Gunicorn, limit 2 CPU, ORT_THREADS=2. Mỗi user gửi 1 ảnh mỗi 0.5–1.5 s.
Locust chạy 90 s mỗi mức; p50/p95/p99 tính trên mọi request kể cả request lỗi.

| Replicas | Users | RPS gửi | RPS thành công | Lỗi % | p50 (ms) | p95 (ms) | p99 (ms) | p95 server (ms) | p95 inference (ms) | CPU (core) | CPU throttled % |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 3 | 10 | 6.3 | 6.3 | 0.0 | 410 | 1000 | 1200 | 1128.1 | 1000.0 | 4.4 | 39.1 |
| 3 | 25 | 8.95 | 8.95 | 0.0 | 1400 | 3300 | 3800 | 1472.4 | 1000.0 | 5.8 | 88.1 |
| 3 | 50 | 9.04 | 9.04 | 0.0 | 4100 | 5800 | 6500 | 1489.7 | 1000.0 | 6.0 | 100.0 |
| 3 | 100 | 25.06 | 9.08 | 63.78 | 4 | 10000 | 13000 | 1476.0 | 1000.0 | 5.8 | 99.7 |
| 5 | 10 | 6.4 | 6.4 | 0.0 | 350 | 980 | 1200 | 907.2 | 936.6 | 4.6 | 21.9 |
| 5 | 25 | 10.94 | 10.94 | 0.0 | 1100 | 2200 | 2700 | 1822.7 | 1000.0 | 8.6 | 75.5 |
| 5 | 50 | 12.42 | 12.42 | 0.0 | 2700 | 4500 | 5100 | 1966.9 | 1000.0 | 10.1 | 98.8 |
| 5 | 100 | 20.5 | 12.48 | 39.11 | 3600 | 7900 | 8900 | 1965.7 | 1000.0 | 10.1 | 98.5 |
