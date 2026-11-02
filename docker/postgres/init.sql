-- Chạy 1 lần khi Postgres khởi tạo volume rỗng (/docker-entrypoint-initdb.d)
CREATE TABLE IF NOT EXISTS predictions (
    id             BIGSERIAL PRIMARY KEY,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    filename       TEXT,
    image_width    INT,
    image_height   INT,
    n_detections   INT   NOT NULL,
    counts         JSONB NOT NULL,   -- {"motorcycle": 12, "car": 5, ...}
    detections     JSONB NOT NULL,   -- [{bbox, class, class_id, confidence}, ...]
    inference_ms   REAL,
    conf_threshold REAL,
    served_by      TEXT,             -- hostname = tên pod/container xử lý request
    client         TEXT              -- User-Agent (vd vscode-vn-traffic/0.1.0)
);

CREATE INDEX IF NOT EXISTS predictions_created_at_idx ON predictions (created_at DESC);
