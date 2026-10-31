"""Sinh monitoring/grafana/dashboards/vn-traffic-api.json (chạy lại sau khi sửa panel)."""
import json
from pathlib import Path
DS = {"type": "prometheus", "uid": "prometheus"}
P = 'path="/predict"'
R = "$__rate_interval"
pid = iter(range(1, 100))

def ts(title, targets, unit, x, y, w=12, h=9, stack=False, legend_calcs=("mean", "max"), soft_max=None, decimals=None):
    return {
        "id": next(pid), "type": "timeseries", "title": title, "datasource": DS,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "targets": [{"refId": chr(65 + i), "expr": e, "legendFormat": l, "datasource": DS}
                    for i, (e, l) in enumerate(targets)],
        "fieldConfig": {"defaults": {"unit": unit, "min": 0, **({"decimals": decimals} if decimals is not None else {}),
                                     "custom": {**({"axisSoftMax": soft_max} if soft_max is not None else {}), "lineWidth": 2, "fillOpacity": 10 if not stack else 60,
                                                "showPoints": "never",
                                                "stacking": {"mode": "normal" if stack else "none"}}},
                        "overrides": []},
        "options": {"legend": {"displayMode": "table", "placement": "bottom", "calcs": list(legend_calcs)},
                    "tooltip": {"mode": "multi", "sort": "desc"}},
    }

def stat(title, expr, unit, x, decimals=2, thresholds=None):
    return {
        "id": next(pid), "type": "stat", "title": title, "datasource": DS,
        "gridPos": {"x": x, "y": 0, "w": 6, "h": 4},
        "targets": [{"refId": "A", "expr": expr, "datasource": DS}],
        "fieldConfig": {"defaults": {"unit": unit, "decimals": decimals,
                                     "thresholds": {"mode": "absolute", "steps": thresholds or [{"color": "text", "value": None}]},
                                     "color": {"mode": "thresholds"}}, "overrides": []},
        "options": {"reduceOptions": {"calcs": ["mean"]}, "colorMode": "value", "graphMode": "area",
                    "textMode": "value"},
    }

q = lambda p: f'histogram_quantile({p}, sum by (le) (rate(flask_http_request_duration_seconds_bucket{{{P}}}[{R}])))'
qi = lambda p: f'histogram_quantile({p}, sum by (le) (rate(model_inference_seconds_bucket[{R}])))'
err = (f'(sum(rate(flask_http_request_duration_seconds_count{{{P},status!~"2.."}}[{R}])) or vector(0))'
       f' / sum(rate(flask_http_request_duration_seconds_count{{{P}}}[{R}]))')

panels = [
    stat("Throughput /predict (TB khung giờ)", f'sum(rate(flask_http_request_duration_seconds_count{{{P}}}[{R}]))', "reqps", 0),
    stat("Latency p95 (TB khung giờ)", q(0.95), "s", 6, 3),
    stat("Error rate phía Flask (TB)", err, "percentunit", 12, 2,
         [{"color": "green", "value": None}, {"color": "orange", "value": 0.01}, {"color": "red", "value": 0.05}]),
    stat("Pod API đang UP (TB)", 'sum(up{job="vn-traffic-api"})', "none", 18, 1),
    ts("Requests/s theo pod (stacked = tổng RPS)",
       [(f'sum by (pod) (rate(flask_http_request_duration_seconds_count{{{P}}}[{R}]))', "{{pod}}")],
       "reqps", 0, 4, h=11, stack=True),
    ts("Latency /predict (end-to-end trong Flask)",
       [(q(0.50), "p50"), (q(0.95), "p95"), (q(0.99), "p99")], "s", 12, 4, h=11),
    ts("Số pod API trả lời scrape (up) — rớt = pod quá tải/bị restart",
       [('sum(up{job="vn-traffic-api"})', "pod up"),
        ('count(up{job="vn-traffic-api"})', "pod được discover")], "none", 0, 15, decimals=0),
    ts("Thời gian inference onnxruntime",
       [(qi(0.50), "p50"), (qi(0.95), "p95"), (qi(0.99), "p99")], "s", 12, 15),
    ts("CPU theo pod (core, limit = 2)",
       [('sum by (pod) (rate(container_cpu_usage_seconds_total{container="api"}[1m]))', "{{pod}}")],
       "none", 0, 24, h=11),
    ts("Error rate phía Flask (503 = từ chối do quá tải; 502 từ Nginx không tính)",
       [(err, "error rate")], "percentunit", 12, 24, h=11, soft_max=0.05),
    ts("Số object phát hiện / giây theo class",
       [(f'sum by (class_name) (rate(model_detections_total[{R}]))', "{{class_name}}")], "none", 0, 35, w=24, h=8),
]

dash = {
    "uid": "vn-traffic-api", "title": "VN Traffic API — YOLOv8s ONNX", "tags": ["vn-traffic", "mlops"],
    "timezone": "browser", "schemaVersion": 41, "version": 2, "refresh": "5s",
    "time": {"from": "now-15m", "to": "now"}, "panels": panels,
}
json.dump(dash, open(Path(__file__).resolve().parents[1] / "monitoring/grafana/dashboards/vn-traffic-api.json", "w"),
          ensure_ascii=False, indent=2)
print(len(panels), "panels")
