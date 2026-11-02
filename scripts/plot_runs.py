"""Vẽ biểu đồ so sánh các lượt load test -> results/comparison.png

    python scripts/plot_runs.py

Đọc results/run*/summary.csv. Lưới 2x2: hàng = số replica, cột = RPS thành công | p95 client.
Cần matplotlib (môi trường dev, không nằm trong image API).
"""
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RESULTS = Path(__file__).resolve().parents[1] / "results"

# Thứ tự cố định, màu theo lượt (không theo thứ hạng). Bảng màu categorical đã kiểm CVD.
RUNS = [
    ("run1_sync", "1. sync, probe 1 s", "#2a78d6", "o"),
    ("run2_gthread", "2. gthread x4", "#eb6834", "s"),
    ("run3_backpressure", "3. backpressure, inflight 4", "#1baf7a", "^"),
    ("run4_inflight8", "4. backpressure, inflight 8", "#eda100", "D"),
]
TEXT, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"


def load(run):
    p = RESULTS / run / "summary.csv"
    if not p.exists():
        return []
    with open(p) as f:
        return [{k: float(v) if v not in ("", "None") else None for k, v in r.items()} for r in csv.DictReader(f)]


def main():
    data = {run: load(run) for run, *_ in RUNS}
    runs = [r for r in RUNS if data[r[0]]]

    plt.rcParams.update({"font.size": 11, "axes.edgecolor": MUTED, "axes.labelcolor": TEXT,
                         "xtick.color": MUTED, "ytick.color": MUTED, "text.color": TEXT})
    fig, axes = plt.subplots(2, 2, figsize=(13, 9), sharex=True)
    metrics = [("ok_rps", "Request thành công / giây", 1), ("p95_ms", "Latency p95 phía client (s)", 1 / 1000)]

    for row, rep in enumerate((3, 5)):
        for col, (key, label, scale) in enumerate(metrics):
            ax = axes[row][col]
            for run, name, color, marker in runs:
                pts = [(r["users"], r[key] * scale) for r in data[run] if r["replicas"] == rep and r[key] is not None]
                if not pts:
                    continue
                xs, ys = zip(*pts)
                ax.plot(xs, ys, color=color, lw=2, marker=marker, ms=8,
                        markeredgecolor="white", markeredgewidth=2, label=name)
            ax.set_title(f"{rep} replica — {label}", loc="left", fontsize=12, color=TEXT)
            ax.set_xscale("log")
            ax.set_xticks([10, 25, 50, 100], labels=["10", "25", "50", "100"])
            ax.minorticks_off()
            ax.set_ylim(bottom=0)
            ax.grid(axis="y", color=GRID, lw=1)
            ax.spines[["top", "right"]].set_visible(False)
            if row == 1:
                ax.set_xlabel("Số user đồng thời (locust)")

    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=len(labels), frameon=False, bbox_to_anchor=(0.5, 1.0))
    fig.text(0.5, 0.005, "p95 tính trên mọi request kể cả 503 trả nhanh; lượt 3–4 có trần latency nhờ backpressure.",
             ha="center", fontsize=9, color=MUTED)
    fig.tight_layout(rect=(0, 0.02, 1, 0.95))
    out = RESULTS / "comparison.png"
    fig.savefig(out, dpi=150, facecolor="white")
    print("->", out)


if __name__ == "__main__":
    main()
