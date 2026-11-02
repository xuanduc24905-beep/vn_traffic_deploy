"""Vẽ sơ đồ kiến trúc triển khai -> docs/report/architecture.png"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

TEXT, MUTED, LINE = "#0b0b0b", "#52514e", "#8a8984"
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"

fig, ax = plt.subplots(figsize=(14, 7.2))
ax.set_xlim(0, 140)
ax.set_ylim(0, 72)
ax.axis("off")


def box(x, y, w, h, title, sub="", edge=LINE, fill="#ffffff", lw=1.5, title_size=11, sub_size=8.5):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.2", fc=fill, ec=edge, lw=lw))
    ax.text(x + w / 2, y + h / 2 + (1.6 if sub else 0), title, ha="center", va="center", fontsize=title_size, color=TEXT, weight="bold")
    if sub:
        ax.text(x + w / 2, y + h / 2 - 2.2, sub, ha="center", va="center", fontsize=sub_size, color=MUTED)


def arrow(x1, y1, x2, y2, label="", both=False, dy=1.3):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="<|-|>" if both else "-|>", mutation_scale=13, color=LINE, lw=1.4))
    if label:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + dy, label, ha="center", va="bottom", fontsize=8.5, color=MUTED)


# Client
box(2, 40, 22, 12, "VS Code", "extension VN Traffic Detector", edge=BLUE)
box(2, 22, 22, 10, "Locust", "load test nhiều mức user")
# Local
box(30, 56, 28, 12, "ML Local Model", "docker-compose: nginx, api,\npostgres, prometheus, grafana", edge=MUTED)
# Proxy
box(36, 34, 18, 12, "Nginx proxy", "cổng 8088\nvnt-k8s-proxy", edge=ORANGE)
# K8s cluster
ax.add_patch(FancyBboxPatch((62, 6), 54, 60, boxstyle="round,pad=0.4,rounding_size=2", fc="#f6f6f4", ec=LINE, lw=1.2, ls="--"))
ax.text(64, 63, "Kubernetes cluster (Docker Desktop, kind)", fontsize=11, color=TEXT, weight="bold")
box(64, 50, 26, 8, "Service NodePort", "vn-traffic-api :30080")
for i, y in enumerate((38, 27, 16)):
    box(64, y, 26, 8, f"Pod API #{i + 1}" if i < 2 else "Pod API #3…#5", "Gunicorn → Flask → onnxruntime", edge=AQUA, title_size=10, sub_size=8)
ax.text(77, 12.6, "Deployment replicas 3 → scale 5", ha="center", fontsize=8.5, color=MUTED)
box(94, 46, 20, 12, "PostgreSQL", "INSERT mỗi /predict\nbảng predictions, PVC 1Gi", edge=YELLOW, sub_size=8)
box(94, 28, 20, 10, "Prometheus", "scrape /metrics từng pod\n+ cAdvisor (CPU)", sub_size=8)
box(94, 12, 20, 10, "Grafana", "dashboard, đọc Prometheus", sub_size=8)
# Arrows
arrow(24, 45, 36, 41)
ax.text(25, 47.6, "POST /predict, GET /history", fontsize=8.5, color=MUTED)
arrow(24, 27, 36, 37, "HTTP", dy=-3.5)
arrow(13, 52, 32, 59)
ax.text(3, 56, "chọn server local", fontsize=8.5, color=MUTED)
arrow(54, 40, 64, 52)
arrow(77, 50, 77, 46)
arrow(77, 38, 77, 35)
arrow(77, 27, 77, 24)
arrow(90, 42, 94, 49)
arrow(94, 33, 90, 31)
arrow(104, 22, 104, 28)

out = Path(__file__).with_name("architecture.png")
fig.savefig(out, dpi=170, bbox_inches="tight", facecolor="white")
print(out)
