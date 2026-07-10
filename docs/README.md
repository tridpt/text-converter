# Tài liệu — Text Format Converter

Bộ tài liệu chi tiết cho dự án. Xem [README chính](../README.md) để có cái
nhìn tổng quan nhanh.

## Mục lục

| Tài liệu | Nội dung |
|----------|----------|
| [USAGE.md](USAGE.md) | Hướng dẫn sử dụng: web UI, CLI, ví dụ |
| [FORMATS.md](FORMATS.md) | Danh sách định dạng, khả năng đọc/ghi, yêu cầu pandoc |
| [API.md](API.md) | Tham chiếu API HTTP đầy đủ + ví dụ `curl` |
| [CONFIGURATION.md](CONFIGURATION.md) | Biến môi trường, bảo mật, deploy |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Kiến trúc hub-and-spoke, luồng xử lý, mở rộng |
| [../CONTRIBUTING.md](../CONTRIBUTING.md) | Hướng dẫn đóng góp |

## Ảnh chụp màn hình / GIF demo

Thư mục này cũng chứa ảnh minh họa cho README.

1. Chạy app: `python -m app` rồi mở http://127.0.0.1:8000
2. Chụp các màn hình gợi ý:
   - `screenshot-home.png` — giao diện chính
   - `screenshot-matrix.png` — trang `/matrix`
   - `demo.gif` — một lượt: kéo file → chọn đích → xem trước → tải về
3. Lưu vào thư mục `docs/` này rồi bỏ comment các dòng ảnh trong `README.md`.

Gợi ý công cụ (Windows): Snipping Tool (ảnh tĩnh), ScreenToGif (GIF).
Nén ảnh trước khi commit để repo gọn nhẹ.
