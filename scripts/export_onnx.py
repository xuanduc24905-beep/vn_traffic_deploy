from ultralytics import YOLO

model = YOLO("models/best.pt")
model.export(
    format="onnx",
    imgsz=640,       # phải trùng imgsz lúc train
    opset=12,
    dynamic=False,   # input cố định [1, 3, 640, 640]
    simplify=True,
    half=False,      # FP32, chạy trên CPU
)