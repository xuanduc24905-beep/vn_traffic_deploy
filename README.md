# 🚦 VN Traffic Deploy — Triển khai YOLOv8s phát hiện phương tiện giao thông Việt Nam

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![ONNX Runtime](https://img.shields.io/badge/ONNX%20Runtime-1.31-005CED?logo=onnx&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.1-000000?logo=flask&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-compose-2496ED?logo=docker&logoColor=white)
![Kubernetes](https://img.shields.io/badge/Kubernetes-1.34-326CE5?logo=kubernetes&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)
![Prometheus](https://img.shields.io/badge/Prometheus-3.5-E6522C?logo=prometheus&logoColor=white)
![Grafana](https://img.shields.io/badge/Grafana-12.1-F46800?logo=grafana&logoColor=white)

Đưa mô hình **YOLOv8s** (đã huấn luyện ở repo [VN_Traffic_AI](https://github.com/xuanduc24905-beep/VN_Traffic_AI))
từ môi trường nghiên cứu lên **production**: phát hiện 4 loại phương tiện — `motorcycle`, `car`, `bus`, `truck` — trong ảnh camera giao thông.

**ONNX → REST API (Flask + Gunicorn + Nginx) → Docker → Kubernetes → Prometheus/Grafana**,
kèm **PostgreSQL** lưu lịch sử dự đoán, **VS Code extension** làm client và **Locust** đo tải.

<p align="center">
  <img src="docs/report/prediction_example.jpg" width="760" alt="Kết quả /predict">
  <br><em>Kết quả thật từ <code>POST /predict</code> qua Nginx → Kubernetes: 19 phương tiện, inference 167 ms trên CPU</em>
</p>

---

## Mục lục

- [Kiến trúc](#kiến-trúc)
- [Điểm nổi bật](#điểm-nổi-bật)
- [Cấu trúc thư mục](#cấu-trúc-thư-mục)
- [Chạy nhanh](#chạy-nhanh) — [local](#1-chạy-local-không-docker) · [docker-compose](#2-docker-compose) · [Kubernetes](#3-kubernetes)
- [API](#api)
- [VS Code extension](#vs-code-extension)
- [Giám sát](#giám-sát-prometheus--grafana)
- [Load test & kết quả](#load-test--kết-quả)
- [Test](#test)
- [Xử lý sự cố](#xử-lý-sự-cố)

---

## Kiến trúc

![Kiến trúc](docs/report/architecture.png)

Một request đi qua: **client** (VS Code extension / Locust / curl) → **Nginx** → **Service** Kubernetes → một **pod API**
(Gunicorn → Flask → onnxruntime) → ghi một dòng vào **PostgreSQL** → trả JSON.
**Prometheus** tự tìm từng pod để lấy `/metrics` mỗi 5 s, **Grafana** vẽ dashboard.

| Thành phần | Công nghệ | Vai trò |
|---|---|---|
| Model | YOLOv8s → ONNX (opset 12, input `[1,3,640,640]`, FP32) | Phát hiện 4 lớp phương tiện |
| Inference | onnxruntime CPU + NumPy/OpenCV | Tiền xử lý (letterbox, BGR→RGB, NCHW) và hậu xử lý (decode `[1,8,8400]`, NMS) tự viết — **image không cần `torch`/`ultralytics`** |
| API | Flask, Gunicorn (`gthread`), Nginx | REST API, WSGI server, reverse proxy |
| Đóng gói | Docker, docker-compose | Môi trường local (“ML Local Model”) |
| Điều phối | Kubernetes (Docker Desktop) | Nhiều replica (“ML Production Model”), scale, probe, rolling update |
| Lưu trữ | PostgreSQL 16 | Lịch sử dự đoán (`/history`, `/stats`) |
| Giám sát | prometheus-flask-exporter, Prometheus, Grafana | RPS, latency p50/p95/p99, error rate, CPU theo pod |
| Client | VS Code extension, Locust | Gửi ảnh từ editor; bắn tải nhiều mức user |

---

## Điểm nổi bật

- **ONNX khớp `.pt` tuyệt đối:** cùng số box trên 10/10 ảnh test, bbox lệch tối đa **0.05 px** (`scripts/verify_onnx.py`).
- **Image API gọn:** `python:3.11-slim` + onnxruntime + OpenCV headless, không có PyTorch.
- **Metrics đúng khi nhiều worker:** dùng `GunicornInternalPrometheusMetrics` + `PROMETHEUS_MULTIPROC_DIR` để `/metrics` gộp mọi worker.
- **Backpressure chống sập dây chuyền:** mỗi pod chạy 1 inference/lần, tối đa 8 request đang xử lý; vượt quá trả ngay
  `503 + Retry-After` thay vì xếp hàng vô hạn. Liveness probe dạng TCP nên quá tải không làm pod bị kill.
- **Đo thật, 4 lượt load test** từ cấu hình ban đầu bị sụp đến cấu hình cuối — xem [Load test & kết quả](#load-test--kết-quả).
- **Database không làm hỏng dự đoán:** PostgreSQL lỗi thì `/predict` vẫn trả kết quả, chỉ tăng metric `db_errors_total`.

---

## Cấu trúc thư mục

```
vn_traffic_deploy/
├── models/                 best.pt (YOLOv8s), best.onnx
├── scripts/
│   ├── export_onnx.py      xuất ONNX (cần ultralytics, chỉ dùng ở máy dev)
│   ├── verify_onnx.py      so sánh .pt và ONNX
│   ├── gen_grafana_dashboard.py, summarize_loadtest.py, plot_runs.py
├── app/
│   ├── main.py             Flask: /predict /health /metrics /history /stats, backpressure
│   ├── inference.py        onnxruntime + tiền/hậu xử lý NumPy/OpenCV
│   └── db.py               PostgreSQL (connection pool)
├── gunicorn.conf.py        gthread, dọn thư mục metrics multiprocess
├── docker/                 Dockerfile, nginx.conf, nginx-k8s.conf, prometheus.yml, postgres/init.sql
├── docker-compose.yml      api, nginx, postgres, prometheus, grafana
├── k8s/                    deployment, service, postgres, monitoring (Prometheus + Grafana)
├── monitoring/grafana/     provisioning + dashboard JSON
├── loadtest/               locustfile.py, run_levels.sh
├── vscode-extension/       client VS Code (JavaScript, không dùng thư viện ngoài)
├── tests/                  pytest cho API
└── results/                CSV Locust, bảng tổng hợp, ảnh dashboard của 4 lượt đo
```

---

## Chạy nhanh

Yêu cầu: Python 3.11, Docker. Phần Kubernetes dùng Kubernetes tích hợp trong Docker Desktop (hoặc cluster bất kỳ có `kubectl`).

### 1. Chạy local (không Docker)

```bash
pip install -r requirements-dev.txt
flask --app app.main run -p 5000
curl -F file=@anh.jpg localhost:5000/predict
```

Chạy bằng Gunicorn như production:

```bash
PROMETHEUS_MULTIPROC_DIR=/tmp/prom gunicorn app.main:app   # đọc gunicorn.conf.py, cổng 8000
```

Không đặt `DATABASE_URL` thì API vẫn chạy, chỉ không lưu lịch sử.

### 2. docker-compose

```bash
docker compose up -d --build
```

| Dịch vụ | Địa chỉ |
|---|---|
| API (qua Nginx) | http://localhost/predict |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 (`admin` / `admin`), dashboard **VN Traffic API** tự nạp sẵn |

```bash
curl -F file=@anh.jpg localhost/predict
curl localhost/history?limit=5
```

### 3. Kubernetes

```bash
# 1. Build image và đưa vào cluster
docker build -f docker/Dockerfile -t vn-traffic-api:latest .
# Docker Desktop (kind) không thấy image local -> nạp vào node:
docker save vn-traffic-api:latest | docker exec -i desktop-control-plane \
  ctr --namespace=k8s.io images import --all-platforms --digests --snapshotter=overlayfs -

# 2. PostgreSQL
kubectl create configmap postgres-init --from-file=docker/postgres/init.sql
kubectl apply -f k8s/postgres.yaml

# 3. API: 3 replica + Service NodePort 30080
kubectl apply -f k8s/deployment.yaml -f k8s/service.yaml

# 4. Prometheus + Grafana trong cluster
kubectl create configmap grafana-dashboards --from-file=monitoring/grafana/dashboards/
kubectl apply -f k8s/monitoring.yaml

# 5. Demo scale
kubectl scale deployment vn-traffic-api --replicas=5
kubectl get pods -l app=vn-traffic-api
```

Docker Desktop (kind) không mở Service ra `localhost`, nên đặt một container Nginx cùng mạng `kind` làm proxy
(cấu hình ở [`docker/nginx-k8s.conf`](docker/nginx-k8s.conf)):

```bash
docker create --name vnt-k8s-proxy --network kind --restart unless-stopped \
  -p 8088:80 -p 3300:3000 -p 9091:9090 nginx:1.27-alpine
docker cp docker/nginx-k8s.conf vnt-k8s-proxy:/etc/nginx/conf.d/default.conf
docker start vnt-k8s-proxy
```

| Dịch vụ | Địa chỉ |
|---|---|
| API | http://localhost:8088 |
| Grafana | http://localhost:3300 (`admin` / `admin`) |
| Prometheus | http://localhost:9091 |

> Mật khẩu PostgreSQL trong `k8s/postgres.yaml` và `docker-compose.yml` chỉ dùng cho demo local.

---

## API

| Method | Endpoint | Mô tả |
|---|---|---|
| `POST` | `/predict` | Ảnh (multipart, field `file`), tuỳ chọn `?conf=0.25`. Trả danh sách phương tiện |
| `GET` | `/health` | Trạng thái, tên pod xử lý, có database hay không (dùng cho probe) |
| `GET` | `/metrics` | Số liệu Prometheus |
| `GET` | `/history?limit=20&full=1` | Các lần dự đoán gần nhất (từ PostgreSQL) |
| `GET` | `/stats` | Tổng số lần dự đoán, số phương tiện theo lớp, theo pod |

**Ví dụ**

```bash
curl -F file=@anh.jpg "localhost:8088/predict?conf=0.3"
```

```json
{
  "count": 19,
  "detections": [
    {"bbox": [269.4, 393.8, 413.0, 478.8], "class": "car", "class_id": 1, "confidence": 0.8452},
    {"bbox": [806.5, 263.9, 856.1, 317.4], "class": "car", "class_id": 1, "confidence": 0.7938}
  ],
  "image_size": [1280, 720],
  "inference_ms": 167.13,
  "served_by": "vn-traffic-api-fc5499845-6678r",
  "id": 12
}
```

`bbox` là `[x1, y1, x2, y2]` theo pixel ảnh gốc. `id` là số bản ghi trong PostgreSQL (`null` nếu không có database).

| Mã lỗi | Khi nào |
|---|---|
| `400` | Thiếu `file`, file không phải ảnh, `conf` không nằm trong `[0, 1]` |
| `503` + `Retry-After: 1` | Pod đang quá tải (đã đủ `MAX_INFLIGHT` request) — client nên thử lại |

**Metrics riêng của model:** `model_inference_seconds` (histogram), `model_detections_total{class_name}`,
`predict_rejected_total`, `db_errors_total` — cùng với `flask_http_request_duration_seconds` của prometheus-flask-exporter.

**Biến môi trường**

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `MODEL_PATH` | `models/best.onnx` | Đường dẫn model |
| `ORT_THREADS` | `0` (tự chọn) | Số thread onnxruntime — đặt bằng CPU limit của pod |
| `CV_THREADS` | `1` | Số thread OpenCV |
| `INFER_CONCURRENCY` | `1` | Số inference chạy song song trong một process |
| `MAX_INFLIGHT` | `4` (K8s đặt `8`) | Số `/predict` tối đa trong một process, vượt quá trả 503 |
| `GUNICORN_WORKERS` / `GUNICORN_THREADS` | `2` / `8` | Phải có `GUNICORN_THREADS > MAX_INFLIGHT` |
| `DATABASE_URL` | — | `postgresql://user:pass@host:5432/db`; bỏ trống = không lưu lịch sử |

---

## VS Code extension

Thư mục [`vscode-extension/`](vscode-extension) — client đúng như khối “Visual Studio Code → Extension” trong sơ đồ.

- Chuột phải vào ảnh trong Explorer → **Phát hiện phương tiện trong ảnh** (hoặc nút 🔍 khi đang xem ảnh).
- Kết quả mở bên cạnh: ảnh vẽ bbox theo màu từng lớp, rê chuột xem lớp/confidence, thanh lọc confidence, pod xử lý, id bản ghi.
- **VN Traffic: Lịch sử dự đoán** — thống kê và 30 lần gần nhất từ PostgreSQL.
- Thanh trạng thái: chuyển giữa **production** (cụm K8s, `:8088`) và **local** (docker-compose, `:80`).
- Server trả 503 thì tự chờ theo `Retry-After` rồi gửi lại.

```bash
cd vscode-extension
npm test                                   # 4 unit test; VN_TRAFFIC_URL=http://localhost:8088 npm test để gọi API thật
npm run package                            # -> vn-traffic-detector-0.1.0.vsix
code --install-extension vn-traffic-detector-0.1.0.vsix
```

---

## Giám sát (Prometheus + Grafana)

Prometheus dùng `kubernetes_sd_configs` để tìm các pod có annotation `prometheus.io/scrape: "true"` và lấy số liệu
**riêng từng pod**, cộng CPU từng container qua cAdvisor. Dashboard
([`monitoring/grafana/dashboards/vn-traffic-api.json`](monitoring/grafana/dashboards/vn-traffic-api.json),
sinh bằng `scripts/gen_grafana_dashboard.py`) gồm 11 panel:

- Ô số: throughput, latency p95, error rate, số pod đang UP
- Requests/s theo pod · latency p50/p95/p99 · thời gian inference p50/p95/p99
- Số pod trả lời scrape theo thời gian · CPU theo pod (limit 2 core)
- Error rate (503 khi quá tải) · số phương tiện phát hiện mỗi giây theo lớp

![Grafana dashboard](results/grafana/run4_inflight8_dashboard.png)

---

## Load test & kết quả

Locust giả lập mỗi user là một camera gửi 1 ảnh thật mỗi 0.5–1.5 s; 4 mức **10 / 25 / 50 / 100 user** × 90 s,
với **3** và **5** replica. Số liệu server lấy từ Prometheus đúng khung thời gian từng mức.

```bash
OUT=results/run5 bash loadtest/run_levels.sh
python scripts/summarize_loadtest.py results/run5
python scripts/plot_runs.py
```

| Lượt | Cấu hình | Điều quan sát được |
|---|---|---|
| 1 | Gunicorn `sync`, probe timeout 1 s | Quá tải → probe fail → **pod bị restart dây chuyền**; Nginx `max_fails=1` khuếch đại 964 lỗi kết nối thành **8 687** lỗi 502 |
| 2 | `gthread` 4 thread | Hết 502 ở 50 user nhưng 4 inference tranh 2 CPU (throttle ~100%), throughput giảm |
| 3 | Backpressure, tối đa 4 request/pod, liveness TCP, Nginx `max_fails=0` | Không còn restart, latency có trần; 3 replica bị 503 sớm do chia tải ngẫu nhiên |
| 4 | Tối đa 8 request/pod, OpenCV 1 thread | **Cấu hình hiện tại** — tốt nhất |

**Lượt 1 so với lượt 4** (request `/predict` thành công mỗi giây · latency p95 phía client):

| Replica | User | Lượt 1 | Lượt 4 |
|---:|---:|---|---|
| 3 | 10 | 7.5 req/s · 0.39 s | 7.6 req/s · **0.30 s** |
| 3 | 50 | 12.4 req/s · 5.3 s | **17.5 req/s · 1.4 s** |
| 5 | 50 | 15.8 req/s · 3.1 s | **18.3 req/s · 2.3 s** |
| 5 | 100 | 14.8 req/s · 5.5 s (p99 12 s) | **19.5 req/s · 2.1 s (p99 2.3 s)** |

![So sánh 4 lượt](results/comparison.png)

Ở mức quá tải, tỉ lệ lỗi của lượt 3–4 vẫn cao vì đó là **503 từ chối có chủ đích** (trả về trong vài ms), không phải sự cố.
Với 5 replica, throughput dừng quanh 18–20 req/s vì hết CPU của cả máy (16 core, Locust chạy chung).
Chi tiết từng lượt: [`results/README.md`](results/README.md).

---

## Test

```bash
pytest -q                                   # 11 test API + 1 test tích hợp PostgreSQL (bỏ qua nếu không có DB)
TEST_DATABASE_URL=postgresql://vntraffic:pass@localhost:5432/vntraffic pytest -q   # chạy cả test DB
```

Kiểm tra ONNX so với `.pt` (cần `ultralytics` ở máy dev):

```bash
python scripts/export_onnx.py
python scripts/verify_onnx.py
```

---

## Xử lý sự cố

| Triệu chứng | Nguyên nhân · cách xử lý |
|---|---|
| Pod `ErrImageNeverPull` | Cluster kind không thấy image local → nạp lại bằng `docker save … \| docker exec -i desktop-control-plane ctr … import -` rồi `kubectl rollout restart deployment/vn-traffic-api` |
| Không gọi được `localhost` qua Service | Docker Desktop (kind) không mở LoadBalancer/NodePort ra máy → dùng container `vnt-k8s-proxy` ở trên |
| `vnt-k8s-proxy` không chạy sau khi khởi động lại máy, lỗi `not a directory` | Bind-mount file của Docker Desktop + WSL bị mất sau reboot → tạo lại bằng `docker cp` như hướng dẫn, không dùng `-v` |
| 502 hàng loạt khi tải cao | Nginx coi upstream chết sau 1 lỗi → đặt `max_fails=0` (đã có trong cấu hình) |
| `.pt` và ONNX lệch số box | Ultralytics letterbox “rect” khi chạy `.pt`, ONNX luôn pad vuông 640 → so sánh trên ảnh đã pad vuông |
| Số liệu Prometheus mất sau khi tắt máy | Prometheus trong K8s không có volume → xuất CSV/ảnh dashboard ngay sau mỗi lần đo |

---

Tác giả: [xuanduc24905-beep](https://github.com/xuanduc24905-beep)
