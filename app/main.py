import os
import time

import cv2
import numpy as np
from flask import Flask, jsonify, request
from prometheus_client import Counter, Histogram
from prometheus_flask_exporter import PrometheusMetrics
from prometheus_flask_exporter.multiprocess import GunicornInternalPrometheusMetrics

from app.inference import CLASS_NAMES, Detector

app = Flask(__name__)
# Gunicorn nhiều worker: mỗi worker ghi metrics ra PROMETHEUS_MULTIPROC_DIR,
# /metrics gộp lại từ mọi worker. Chạy `flask run`/pytest thì dùng bản thường.
if os.getenv("PROMETHEUS_MULTIPROC_DIR"):
    metrics = GunicornInternalPrometheusMetrics(app)
else:
    metrics = PrometheusMetrics(app)  # tự tạo /metrics + flask_http_request_*

INFER_SECONDS = Histogram(
    "model_inference_seconds", "Thời gian chạy onnxruntime cho 1 ảnh",
    buckets=(0.01, 0.025, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3, 0.5, 1.0),
)
DETECTIONS = Counter("model_detections_total", "Số object phát hiện", ["class_name"])

detector = Detector(os.getenv("MODEL_PATH", "models/best.onnx"))


@app.get("/health")
@metrics.do_not_track()
def health():
    return jsonify(status="ok", model=detector.model_path, classes=CLASS_NAMES)


@app.post("/predict")
def predict():
    f = request.files.get("file")
    if f is None:
        return jsonify(error="thiếu field 'file' (multipart/form-data)"), 400

    img = cv2.imdecode(np.frombuffer(f.read(), np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return jsonify(error="không decode được ảnh"), 400

    try:
        conf = float(request.args.get("conf", 0.25))
    except ValueError:
        return jsonify(error="conf phải là số trong khoảng [0, 1]"), 400
    if not 0 <= conf <= 1:
        return jsonify(error="conf phải là số trong khoảng [0, 1]"), 400

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