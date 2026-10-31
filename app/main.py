import os
import threading
import time

import cv2
import numpy as np
from flask import Flask, jsonify, request
from prometheus_client import Counter, Histogram
from prometheus_flask_exporter import PrometheusMetrics
from prometheus_flask_exporter.multiprocess import GunicornInternalPrometheusMetrics

from app.inference import CLASS_NAMES, Detector

app = Flask(__name__)
# Bucket latency mịn hơn mặc định để p50/p95/p99 trên Grafana sát thực tế
LATENCY_BUCKETS = (0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.75, 1.0, 1.5, 2.0,
                   3.0, 5.0, 7.5, 10.0, 15.0, 30.0, 60.0)
# Gunicorn nhiều worker: mỗi worker ghi metrics ra PROMETHEUS_MULTIPROC_DIR,
# /metrics gộp lại từ mọi worker. Chạy `flask run`/pytest thì dùng bản thường.
if os.getenv("PROMETHEUS_MULTIPROC_DIR"):
    metrics = GunicornInternalPrometheusMetrics(app, buckets=LATENCY_BUCKETS)
else:
    metrics = PrometheusMetrics(app, buckets=LATENCY_BUCKETS)  # tự tạo /metrics + flask_http_request_*

INFER_SECONDS = Histogram(
    "model_inference_seconds", "Thời gian chạy onnxruntime cho 1 ảnh",
    buckets=(0.01, 0.025, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3, 0.5, 0.75, 1.0, 2.0, 5.0),
)
DETECTIONS = Counter("model_detections_total", "Số object phát hiện", ["class_name"])
REJECTED = Counter("predict_rejected_total", "Số request /predict bị từ chối (503) vì quá tải")

detector = Detector(os.getenv("MODEL_PATH", "models/best.onnx"))

# Backpressure (mỗi process):
# - INFER_CONCURRENCY: số inference chạy song song. Inference đã dùng ORT_THREADS core,
#   chạy song song nhiều hơn chỉ tranh CPU (load test: p50 x2, throughput giảm).
# - MAX_INFLIGHT: số /predict được nằm trong process (đang chạy + đang chờ). Vượt quá thì
#   trả 503 ngay thay vì xếp hàng vô hạn -> latency có trần, và luôn còn thread rảnh để
#   trả lời /health (tránh K8s probe fail rồi restart pod dây chuyền lúc quá tải).
#   Cần GUNICORN_THREADS > MAX_INFLIGHT.
MAX_INFLIGHT = int(os.getenv("MAX_INFLIGHT", "4"))
_inflight = threading.BoundedSemaphore(MAX_INFLIGHT)
_infer_slots = threading.BoundedSemaphore(int(os.getenv("INFER_CONCURRENCY", "1")))


@app.get("/health")
@metrics.do_not_track()
def health():
    return jsonify(status="ok", model=detector.model_path, classes=CLASS_NAMES)


@app.post("/predict")
def predict():
    f = request.files.get("file")
    if f is None:
        return jsonify(error="thiếu field 'file' (multipart/form-data)"), 400

    if not _inflight.acquire(blocking=False):
        REJECTED.inc()
        return jsonify(error="server đang quá tải, thử lại sau"), 503, {"Retry-After": "1"}
    try:
        return _predict(f)
    finally:
        _inflight.release()


def _predict(f):
    img = cv2.imdecode(np.frombuffer(f.read(), np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return jsonify(error="không decode được ảnh"), 400

    try:
        conf = float(request.args.get("conf", 0.25))
    except ValueError:
        return jsonify(error="conf phải là số trong khoảng [0, 1]"), 400
    if not 0 <= conf <= 1:
        return jsonify(error="conf phải là số trong khoảng [0, 1]"), 400

    with _infer_slots:
        t0 = time.perf_counter()
        dets = detector.predict(img, conf_thres=conf)
        dt = time.perf_counter() - t0

    INFER_SECONDS.observe(dt)
    for d in dets:
        DETECTIONS.labels(class_name=d["class"]).inc()

    h, w = img.shape[:2]
    return jsonify(
        detections=dets,
        count=len(dets),
        image_size=[w, h],
        inference_ms=round(dt * 1000, 2),
    )