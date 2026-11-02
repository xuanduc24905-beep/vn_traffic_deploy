# VN Traffic Detector (VS Code extension)

Client của hệ thống: gửi ảnh camera giao thông từ VS Code tới API YOLOv8s (ONNX)
và hiển thị phương tiện phát hiện được (motorcycle, car, bus, truck) ngay trong editor.

## Dùng

- Chuột phải vào ảnh `.jpg/.png` trong Explorer → **Phát hiện phương tiện trong ảnh**,
  hoặc mở ảnh rồi bấm biểu tượng 🔍 trên thanh tiêu đề, hoặc `Ctrl+Shift+P` → `VN Traffic: …`.
- Kết quả: ảnh vẽ bbox (rê chuột xem class/confidence), số lượng theo class, thanh lọc confidence,
  pod nào xử lý, thời gian inference, id bản ghi trong PostgreSQL.
- `VN Traffic: Lịch sử dự đoán`: thống kê + các lần gần nhất (đọc từ `/history`, `/stats`).
- Thanh trạng thái góc phải: server đang dùng và trạng thái `/health`; bấm để đổi server.

## Server

| `vnTraffic.target` | URL mặc định | Tương ứng sơ đồ |
|---|---|---|
| `production` | `http://localhost:8088` | Nginx proxy → cụm Kubernetes |
| `local` | `http://localhost:80` | docker-compose (ML Local Model) |

Server trả `503 + Retry-After` khi quá tải → extension tự chờ và thử lại (`vnTraffic.maxRetries`).

## Build / cài

```bash
npm test                      # unit test; VN_TRAFFIC_URL=http://localhost:8088 npm test để gọi API thật
npm run package               # -> vn-traffic-detector-0.1.0.vsix
code --install-extension vn-traffic-detector-0.1.0.vsix
```
