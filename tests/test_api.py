import io
import os
from pathlib import Path

import cv2
import numpy as np
import pytest

from app.main import app

SAMPLE_DIR = Path("/home/xuand/vn_traffic_ai/data/merged_v5/images/test")


@pytest.fixture
def client():
    app.config["TESTING"] = True
    return app.test_client()


def _jpg(img):
    return io.BytesIO(cv2.imencode(".jpg", img)[1].tobytes())


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json["classes"] == ["motorcycle", "car", "bus", "truck"]


def test_predict_blank_image(client):
    img = np.full((480, 640, 3), 114, np.uint8)
    r = client.post("/predict", data={"file": (_jpg(img), "blank.jpg")})
    assert r.status_code == 200
    assert r.json["image_size"] == [640, 480]
    assert r.json["count"] == len(r.json["detections"])


@pytest.mark.skipif(not SAMPLE_DIR.exists(), reason="không có ảnh test của repo train")
def test_predict_real_image(client):
    p = sorted(SAMPLE_DIR.glob("*.jpg"))[0]
    with open(p, "rb") as f:
        r = client.post("/predict", data={"file": (f, p.name)})
    assert r.status_code == 200
    dets = r.json["detections"]
    assert len(dets) > 0
    w, h = r.json["image_size"]
    for d in dets:
        x1, y1, x2, y2 = d["bbox"]
        assert 0 <= x1 < x2 <= w and 0 <= y1 < y2 <= h
        assert d["class"] in ("motorcycle", "car", "bus", "truck")
        assert 0.25 <= d["confidence"] <= 1


def test_predict_missing_file(client):
    assert client.post("/predict").status_code == 400


def test_predict_not_an_image(client):
    r = client.post("/predict", data={"file": (io.BytesIO(b"hello"), "x.jpg")})
    assert r.status_code == 400


@pytest.mark.parametrize("conf", ["abc", "1.5", "-0.1"])
def test_predict_bad_conf(client, conf):
    img = np.zeros((64, 64, 3), np.uint8)
    r = client.post(f"/predict?conf={conf}", data={"file": (_jpg(img), "a.jpg")})
    assert r.status_code == 400


def test_metrics(client):
    client.get("/health")
    body = client.get("/metrics").data.decode()
    assert "flask_http_request_duration_seconds" in body
    assert "model_inference_seconds" in body


def test_predict_overloaded_returns_503(client, monkeypatch):
    import threading

    import app.main as main

    full = threading.BoundedSemaphore(1)
    full.acquire()  # giả lập đã đủ MAX_INFLIGHT request đang xử lý
    monkeypatch.setattr(main, "_inflight", full)
    img = np.zeros((64, 64, 3), np.uint8)
    r = client.post("/predict", data={"file": (_jpg(img), "a.jpg")})
    assert r.status_code == 503
    assert r.headers["Retry-After"] == "1"
    assert client.get("/health").status_code == 200


def test_history_without_database(client):
    # Không đặt DATABASE_URL -> API vẫn chạy, chỉ báo không có lịch sử
    assert client.get("/history").status_code == 503
    assert client.get("/stats").status_code == 503
    assert client.get("/health").json["database"] is False


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="cần TEST_DATABASE_URL (Postgres đã chạy init.sql)")
def test_predict_saves_history(monkeypatch):
    import app.db as db

    monkeypatch.setenv("DATABASE_URL", os.environ["TEST_DATABASE_URL"])
    db.init()
    db._pool.wait(timeout=10)
    try:
        c = app.test_client()
        img = np.full((480, 640, 3), 114, np.uint8)
        r = c.post("/predict", data={"file": (_jpg(img), "blank.jpg")}, headers={"User-Agent": "pytest"})
        rid = r.json["id"]
        assert rid is not None
        items = c.get("/history?limit=5").json["items"]
        assert items[0]["id"] == rid and items[0]["filename"] == "blank.jpg" and items[0]["client"] == "pytest"
        assert c.get("/stats").json["predictions"] >= 1
    finally:
        db._pool.close()
        db._pool = None
