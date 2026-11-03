# models/

Trọng số model **không** nằm trong repo. Cần 2 file đặt tại đây trước khi chạy API hoặc build Docker image:

| File | Nguồn |
|---|---|
| `best.pt` | YOLOv8s đã huấn luyện (run `train_v8s_v5_honest`, 4 lớp motorcycle/car/bus/truck, imgsz 640) |
| `best.onnx` | Sinh từ `best.pt`: `python scripts/export_onnx.py` (cần `ultralytics` ở máy dev) |

API và Docker image chỉ cần `best.onnx`; `best.pt` chỉ dùng để export và kiểm tra (`scripts/verify_onnx.py`).
Đường dẫn khác thì đặt biến môi trường `MODEL_PATH`.
