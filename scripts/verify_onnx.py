import sys
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort
from ultralytics import YOLO

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.inference import Detector  # noqa: E402

IMG_DIR = Path("/home/xuand/vn_traffic_ai/data/merged_v5/images/test")
imgs = sorted(IMG_DIR.glob("*.jpg"))[::150][:10]  # rải đều nhiều camera

sess = ort.InferenceSession("models/best.onnx", providers=["CPUExecutionProvider"])
print("input :", sess.get_inputs()[0].name, sess.get_inputs()[0].shape)
print("output:", sess.get_outputs()[0].name, sess.get_outputs()[0].shape)

pt = YOLO("models/best.pt")
det = Detector("models/best.onnx")  # pipeline numpy/onnxruntime dùng trong API


def max_diff(a, b):
    """Box của a lệch xa nhất bao nhiêu px so với box gần nhất của b."""
    if not len(a) or not len(b):
        return 0.0
    return np.abs(a[:, None, :] - b[None, :, :]).max(-1).min(1).max()


# Lưu ý: với .pt, ultralytics letterbox kiểu "rect" (pad tới bội số 32, vd 640x384),
# còn ONNX static luôn pad vuông 640x640 -> input khác nhau, số box có thể lệch 1-3.
# Để so công bằng, letterbox sẵn ảnh về 640x640 rồi mới đưa cho cả hai.
for p in imgs:
    sq = det._letterbox(cv2.imread(str(p)))[0]
    a = pt.predict(sq, imgsz=640, conf=0.25, device="cpu", verbose=False)[0].boxes.xyxy.numpy()
    b = np.array([d["bbox"] for d in det.predict(sq)]).reshape(-1, 4)
    print(f"{p.name[:40]:40s}  pt={len(a):3d}  onnx={len(b):3d}  max_bbox_diff={max_diff(a, b):.2f}px")
