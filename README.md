# vn_traffic_deploy

Triển khai mô hình **YOLOv8s phát hiện phương tiện giao thông Việt Nam** (motorcycle, car, bus, truck) từ môi trường
nghiên cứu lên “production”: ONNX → Flask + Gunicorn + Nginx → Docker → Kubernetes → Prometheus/Grafana,
kèm PostgreSQL lưu lịch sử dự đoán và VS Code extension làm client.

![Kiến trúc](docs/report/architecture.png)

## Thành phần

| Thư mục | Nội dung |
|---|---|
| `scripts/export_onnx.py`, `verify_onnx.py` | Xuất ONNX (imgsz 640) và so sánh với `.pt` (lệch 0.05 px) |
| `app/` | Flask API: `POST /predict`, `GET /health`, `/metrics`, `/history`, `/stats`; inference bằng onnxruntime, tiền/hậu xử lý tự viết bằng NumPy/OpenCV |
| `gunicorn.conf.py`, `docker/` | Gunicorn (gthread, metrics multiprocess), Dockerfile, Nginx, Prometheus, schema PostgreSQL |
| `docker-compose.yml` | Môi trường local: api, nginx, postgres, prometheus, grafana |
| `k8s/` | Deployment (3 replica, backpressure, probe), Service NodePort, PostgreSQL, Prometheus + Grafana |
| `monitoring/` | Dashboard Grafana (RPS, latency p50/p95/p99, error rate, CPU theo pod, …) |
| `loadtest/` | Locust + script chạy nhiều mức tải |
| `vscode-extension/` | Extension VS Code gửi ảnh lên API, vẽ bbox, xem lịch sử |
| `results/` | Số liệu load test 4 lượt + ảnh dashboard |

## Chạy nhanh

```bash
# local
docker compose up -d --build
curl -F file=@anh.jpg localhost/predict

# Kubernetes
kubectl create configmap postgres-init --from-file=docker/postgres/init.sql
kubectl apply -f k8s/postgres.yaml -f k8s/deployment.yaml -f k8s/service.yaml
kubectl create configmap grafana-dashboards --from-file=monitoring/grafana/dashboards/
kubectl apply -f k8s/monitoring.yaml
kubectl scale deployment vn-traffic-api --replicas=5

# test
pip install -r requirements-dev.txt && pytest -q
```

Kết quả load test và phân tích: [`results/README.md`](results/README.md).
