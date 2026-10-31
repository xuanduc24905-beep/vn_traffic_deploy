"""Gộp kết quả locust + số liệu Prometheus cho từng lần chạy -> <run>/summary.{csv,md}.

    python scripts/summarize_loadtest.py results/run2 [--prom http://localhost:9091] [--title "..."]

Đọc <run>/timeline.csv (do loadtest/run_levels.sh ghi) và <run>/locust/r{rep}_u{users}_stats.csv.
Số liệu phía server lấy bằng increase()/rate() đúng trong khung thời gian của từng lần chạy.
"""
import argparse
import csv
import json
import urllib.parse
import urllib.request
from pathlib import Path

WARMUP = 10  # bỏ vài giây đầu lúc locust đang spawn user

P = 'path="/predict"'
QUERIES = {
    "server_p50_ms": 'histogram_quantile(0.50, sum by (le) (increase(flask_http_request_duration_seconds_bucket{%s}[{w}])))' % P,
    "server_p95_ms": 'histogram_quantile(0.95, sum by (le) (increase(flask_http_request_duration_seconds_bucket{%s}[{w}])))' % P,
    "server_p99_ms": 'histogram_quantile(0.99, sum by (le) (increase(flask_http_request_duration_seconds_bucket{%s}[{w}])))' % P,
    "infer_p95_ms": "histogram_quantile(0.95, sum by (le) (increase(model_inference_seconds_bucket[{w}])))",
    "cpu_cores": 'sum(rate(container_cpu_usage_seconds_total{container="api"}[{w}]))',
    "cpu_throttled_pct": 'sum(increase(container_cpu_cfs_throttled_periods_total{container="api"}[{w}]))'
                         ' / sum(increase(container_cpu_cfs_periods_total{container="api"}[{w}]))',
}
SCALE = {"server_p50_ms": 1000, "server_p95_ms": 1000, "server_p99_ms": 1000, "infer_p95_ms": 1000,
         "cpu_cores": 1, "cpu_throttled_pct": 100}


def prom(base, expr, t):
    url = f"{base}/api/v1/query?" + urllib.parse.urlencode({"query": expr, "time": t})
    res = json.load(urllib.request.urlopen(url, timeout=10))["data"]["result"]
    if not res:
        return None
    v = float(res[0]["value"][1])
    return None if v != v else v  # NaN -> None


def locust_row(run, rep, users):
    with open(run / "locust" / f"r{rep}_u{users}_stats.csv") as f:
        rows = {r["Name"]: r for r in csv.DictReader(f)}
    r = rows["/predict"]
    n, fails = int(r["Request Count"]), int(r["Failure Count"])
    return {
        "requests": n,
        "rps": round(float(r["Requests/s"]), 2),
        "ok_rps": round(float(r["Requests/s"]) * (n - fails) / n, 2) if n else 0.0,
        "fail_pct": round(100 * fails / n, 2) if n else 0.0,
        "p50_ms": int(r["50%"]), "p95_ms": int(r["95%"]), "p99_ms": int(r["99%"]),
        "avg_ms": round(float(r["Average Response Time"])), "max_ms": round(float(r["Max Response Time"])),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run", type=Path)
    ap.add_argument("--prom", default="http://localhost:9091")
    ap.add_argument("--title", default="")
    args = ap.parse_args()
    run = args.run

    out = []
    with open(run / "timeline.csv") as f:
        for t in csv.DictReader(f):
            rep, users = int(t["replicas"]), int(t["users"])
            start, end = int(t["start_unix"]) + WARMUP, int(t["end_unix"])
            w = f"{end - start}s"
            row = {"replicas": rep, "users": users, **locust_row(run, rep, users)}
            for k, q in QUERIES.items():
                v = prom(args.prom, q.replace("{w}", w), end)
                row[k] = None if v is None else round(v * SCALE[k], 1)
            out.append(row)

    with open(run / "summary.csv", "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(out[0]))
        wr.writeheader()
        wr.writerows(out)

    cols = [("replicas", "Replicas"), ("users", "Users"), ("rps", "RPS gửi"), ("ok_rps", "RPS thành công"), ("fail_pct", "Lỗi %"),
            ("p50_ms", "p50 (ms)"), ("p95_ms", "p95 (ms)"), ("p99_ms", "p99 (ms)"),
            ("server_p95_ms", "p95 server (ms)"), ("infer_p95_ms", "p95 inference (ms)"),
            ("cpu_cores", "CPU (core)"), ("cpu_throttled_pct", "CPU throttled %")]
    lines = ["| " + " | ".join(h for _, h in cols) + " |", "|" + "---:|" * len(cols)]
    lines += ["| " + " | ".join("–" if r[k] is None else str(r[k]) for k, _ in cols) + " |" for r in out]
    md = (f"# Kết quả load test /predict{' — ' + args.title if args.title else ''}\n\n"
          "Locust (client) đo end-to-end qua Nginx → K8s Service → pod; cột *server* lấy từ Prometheus.\n"
          "Mỗi pod: 1 worker Gunicorn, limit 2 CPU, ORT_THREADS=2. Mỗi user gửi 1 ảnh mỗi 0.5–1.5 s.\n"
          "Locust chạy 90 s mỗi mức; p50/p95/p99 tính trên mọi request kể cả request lỗi.\n\n"
          + "\n".join(lines) + "\n")
    (run / "summary.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
