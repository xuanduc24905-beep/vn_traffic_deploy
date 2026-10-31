# Gunicorn tự đọc file này khi chạy từ thư mục gốc repo:
#   PROMETHEUS_MULTIPROC_DIR=/tmp/prom gunicorn app.main:app
import os
import shutil

from prometheus_flask_exporter.multiprocess import GunicornInternalPrometheusMetrics

bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8000")
workers = int(os.getenv("GUNICORN_WORKERS", "2"))
# gthread: mỗi worker nhiều thread -> /health vẫn trả lời khi các thread khác đang
# chạy inference. Với worker "sync", probe K8s bị kẹt sau hàng đợi /predict lúc quá tải
# -> liveness fail -> pod bị restart dây chuyền (đã gặp khi load test).
worker_class = os.getenv("GUNICORN_WORKER_CLASS", "gthread")
threads = int(os.getenv("GUNICORN_THREADS", "8"))  # > MAX_INFLIGHT (app/main.py)
timeout = 60
accesslog = "-"
forwarded_allow_ips = "*"  # tin X-Forwarded-* từ Nginx


def on_starting(server):
    # Xoá file metrics cũ của lần chạy trước, nếu không số liệu sẽ cộng dồn
    d = os.environ["PROMETHEUS_MULTIPROC_DIR"]
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)


def child_exit(server, worker):
    GunicornInternalPrometheusMetrics.mark_process_dead_on_child_exit(worker.pid)
