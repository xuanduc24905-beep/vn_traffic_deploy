"""Lưu lịch sử dự đoán vào PostgreSQL (tuỳ chọn).

Bật bằng biến môi trường DATABASE_URL (vd postgresql://vntraffic:...@postgres:5432/vntraffic).
Không có DATABASE_URL thì API vẫn chạy bình thường, chỉ không lưu lịch sử.
DB lỗi cũng không làm hỏng /predict: ghi log + tăng metric db_errors_total.
Schema: docker/postgres/init.sql.
"""
import logging
import os

from prometheus_client import Counter
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

log = logging.getLogger(__name__)
DB_ERRORS = Counter("db_errors_total", "Số lần thao tác PostgreSQL bị lỗi", ["op"])

_pool = None


def init():
    """Mở connection pool (gọi trong mỗi worker, sau khi Gunicorn fork)."""
    global _pool
    url = os.getenv("DATABASE_URL")
    if not url:
        log.info("DATABASE_URL chưa đặt -> không lưu lịch sử dự đoán")
        return
    from psycopg_pool import ConnectionPool

    # open=False + open(wait=False): pod vẫn khởi động được khi Postgres chưa sẵn sàng
    _pool = ConnectionPool(url, min_size=1, max_size=int(os.getenv("DB_POOL_SIZE", "4")),
                           kwargs={"connect_timeout": 3}, open=False)
    _pool.open(wait=False)


def enabled():
    return _pool is not None


def save_prediction(*, filename, image_size, dets, inference_ms, conf, served_by, client):
    """Ghi 1 dòng, trả về id (hoặc None nếu tắt DB / lỗi)."""
    if _pool is None:
        return None
    counts = {}
    for d in dets:
        counts[d["class"]] = counts.get(d["class"], 0) + 1
    try:
        with _pool.connection(timeout=2) as conn:
            row = conn.execute(
                """INSERT INTO predictions (filename, image_width, image_height, n_detections, counts,
                                            detections, inference_ms, conf_threshold, served_by, client)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                (filename, image_size[0], image_size[1], len(dets), Jsonb(counts), Jsonb(dets),
                 inference_ms, conf, served_by, client),
            ).fetchone()
            return row[0]
    except Exception as e:  # DB lỗi không được làm hỏng /predict
        DB_ERRORS.labels(op="insert").inc()
        log.warning("Không lưu được prediction: %s", e)
        return None


def history(limit=20, full=False):
    cols = "id, created_at, filename, image_width, image_height, n_detections, counts, " \
           "inference_ms, conf_threshold, served_by, client" + (", detections" if full else "")
    with _pool.connection(timeout=2) as conn:
        cur = conn.cursor(row_factory=dict_row)
        rows = cur.execute(f"SELECT {cols} FROM predictions ORDER BY id DESC LIMIT %s", (limit,)).fetchall()
    for r in rows:
        r["created_at"] = r["created_at"].isoformat()
    return rows


def stats():
    with _pool.connection(timeout=2) as conn:
        cur = conn.cursor(row_factory=dict_row)
        total = cur.execute(
            """SELECT count(*) AS predictions, coalesce(sum(n_detections), 0) AS detections,
                      round(avg(inference_ms)::numeric, 1)::float AS avg_inference_ms,
                      min(created_at) AS first_at, max(created_at) AS last_at
               FROM predictions""").fetchone()
        by_class = cur.execute(
            """SELECT key AS class, sum(value::int) AS count
               FROM predictions, jsonb_each_text(counts) GROUP BY key ORDER BY count DESC""").fetchall()
        by_pod = cur.execute(
            """SELECT served_by, count(*) AS predictions FROM predictions
               GROUP BY served_by ORDER BY predictions DESC""").fetchall()
    for k in ("first_at", "last_at"):
        total[k] = total[k].isoformat() if total[k] else None
    total["by_class"] = {r["class"]: r["count"] for r in by_class}
    total["by_pod"] = {r["served_by"]: r["predictions"] for r in by_pod}
    return total
