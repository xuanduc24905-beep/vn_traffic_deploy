"""Gọi API thật (qua Nginx -> K8s) với 1 ảnh test, vẽ bbox giống extension -> docs/report/prediction_example.jpg"""
import json
import sys
import urllib.request
import uuid
from pathlib import Path

import cv2

API = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8088"
IMG = sorted(Path("/home/xuand/vn_traffic_ai/data/merged_v5/images/test").glob("*.jpg"))[450]
COLORS = {"motorcycle": "#2a78d6", "car": "#eb6834", "bus": "#1baf7a", "truck": "#eda100"}

boundary = uuid.uuid4().hex
data = IMG.read_bytes()
body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{IMG.name}\"\r\n"
        f"Content-Type: image/jpeg\r\n\r\n").encode() + data + f"\r\n--{boundary}--\r\n".encode()
req = urllib.request.Request(f"{API}/predict", data=body, headers={
    "Content-Type": f"multipart/form-data; boundary={boundary}", "User-Agent": "report-figure"})
res = json.load(urllib.request.urlopen(req, timeout=30))

img = cv2.imread(str(IMG))
lw = max(2, img.shape[1] // 640)
for d in res["detections"]:
    x1, y1, x2, y2 = map(int, d["bbox"])
    h = COLORS[d["class"]].lstrip("#")
    bgr = tuple(int(h[i:i + 2], 16) for i in (4, 2, 0))
    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 0), lw + 2)
    cv2.rectangle(img, (x1, y1), (x2, y2), bgr, lw)
    label = f"{d['class']} {d['confidence']:.2f}"
    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
    cv2.rectangle(img, (x1, max(0, y1 - th - 6)), (x1 + tw + 6, y1), (20, 20, 20), -1)
    cv2.putText(img, label, (x1 + 3, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
out = Path(__file__).with_name("prediction_example.jpg")
cv2.imwrite(str(out), img)
json.dump({k: v for k, v in res.items() if k != "detections"} | {"image": IMG.name, "detections": res["detections"]},
          open(out.with_suffix(".json"), "w"), ensure_ascii=False, indent=1)
print(out, res["count"], "box", res["served_by"], res["inference_ms"], "ms, id", res["id"])
