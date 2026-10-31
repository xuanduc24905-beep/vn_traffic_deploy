import cv2
import numpy as np
import onnxruntime as ort

CLASS_NAMES = ["motorcycle", "car", "bus", "truck"]


class Detector:
    def __init__(self, model_path, imgsz=640, iou_thres=0.7):
        self.model_path = model_path
        self.imgsz = imgsz
        self.iou_thres = iou_thres  # 0.7 = mặc định của ultralytics predict
        self.session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
        self.input_name = self.session.get_inputs()[0].name

    def _letterbox(self, img):
        """Resize giữ tỉ lệ + pad xám 114 về imgsz x imgsz (giống ultralytics)."""
        h, w = img.shape[:2]
        r = min(self.imgsz / h, self.imgsz / w)
        nw, nh = round(w * r), round(h * r)
        pad_x, pad_y = (self.imgsz - nw) / 2, (self.imgsz - nh) / 2
        img = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LINEAR)
        top, bottom = round(pad_y - 0.1), round(pad_y + 0.1)
        left, right = round(pad_x - 0.1), round(pad_x + 0.1)
        img = cv2.copyMakeBorder(img, top, bottom, left, right,
                                 cv2.BORDER_CONSTANT, value=(114, 114, 114))
        return img, r, left, top

    def predict(self, img_bgr, conf_thres=0.25):
        h0, w0 = img_bgr.shape[:2]
        lb, r, left, top = self._letterbox(img_bgr)

        # HWC BGR uint8 -> NCHW RGB float32 [0, 1]
        x = cv2.cvtColor(lb, cv2.COLOR_BGR2RGB).transpose(2, 0, 1)
        x = np.ascontiguousarray(x, dtype=np.float32)[None] / 255.0

        out = self.session.run(None, {self.input_name: x})[0]  # [1, 8, 8400]
        pred = out[0].T                                          # [8400, 8] = cx,cy,w,h + 4 class scores

        scores = pred[:, 4:]
        class_ids = scores.argmax(1)
        confs = scores.max(1)
        keep = confs >= conf_thres
        pred, class_ids, confs = pred[keep], class_ids[keep], confs[keep]
        if len(pred) == 0:
            return []

        # cxcywh (không gian 640 đã letterbox) -> xyxy trên ảnh gốc
        cx, cy, bw, bh = pred[:, 0], pred[:, 1], pred[:, 2], pred[:, 3]
        x1 = ((cx - bw / 2 - left) / r).clip(0, w0)
        y1 = ((cy - bh / 2 - top) / r).clip(0, h0)
        x2 = ((cx + bw / 2 - left) / r).clip(0, w0)
        y2 = ((cy + bh / 2 - top) / r).clip(0, h0)

        # NMS theo từng class (class-aware, giống ultralytics agnostic=False)
        xywh = np.stack([x1, y1, x2 - x1, y2 - y1], 1)
        idx = cv2.dnn.NMSBoxesBatched(xywh.tolist(), confs.tolist(), class_ids.tolist(),
                                      conf_thres, self.iou_thres)
        idx = np.array(idx, dtype=int).flatten()

        dets = [
            {
                "bbox": [round(float(x1[i]), 1), round(float(y1[i]), 1),
                         round(float(x2[i]), 1), round(float(y2[i]), 1)],
                "class_id": int(class_ids[i]),
                "class": CLASS_NAMES[class_ids[i]],
                "confidence": round(float(confs[i]), 4),
            }
            for i in idx
        ]
        return sorted(dets, key=lambda d: d["confidence"], reverse=True)