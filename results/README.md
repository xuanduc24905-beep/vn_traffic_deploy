# Kết quả load test

Locust bắn `POST /predict` qua Nginx → K8s Service → pod, mỗi user gửi 1 ảnh test mỗi 0.5–1.5 s,
4 mức 10/25/50/100 user × 90 s, với 3 và 5 replica (`loadtest/run_levels.sh`).
Số liệu server (latency Flask, inference, CPU, throttle) lấy từ Prometheus đúng khung thời gian từng mức
(`scripts/summarize_loadtest.py`).

| Thư mục | Cấu hình |
|---|---|
| `run1_sync/` | Gunicorn worker sync, probe timeout 1 s (ban đầu) → probe fail, pod restart dây chuyền, Nginx `max_fails=1` khuếch đại thành 502 hàng loạt |
| `run2_gthread/` | gthread 4 thread/pod → hết 502 ở 50 user nhưng tranh CPU (throttle ~100%), throughput giảm |
| `run3_backpressure/` | 1 inference/lần, tối đa 4 request/pod (503 + Retry-After), liveness TCP, Nginx `max_fails=0` |
| `run4_inflight8/` | Như run3, tối đa 8 request/pod, OpenCV 1 thread — cấu hình hiện tại |

Mỗi thư mục: `summary.md` / `summary.csv` (bảng tổng hợp), `timeline.csv` (mốc thời gian), `locust/` (CSV gốc).
`comparison.png`: so sánh 4 lượt (`scripts/plot_runs.py`). `grafana/`: ảnh dashboard từng lượt (Grafana Image Renderer).
