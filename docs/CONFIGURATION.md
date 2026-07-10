# Cấu hình & vận hành

Mọi cấu hình đọc từ biến môi trường (xem `app/config.py`). Sao chép
`.env.example` để tham khảo.

## Biến môi trường

| Biến | Mặc định | Mô tả |
|------|----------|-------|
| `HOST` | `127.0.0.1` | Interface bind (`0.0.0.0` để mở ra mạng/Docker) |
| `PORT` | `8000` | Cổng web server |
| `MAX_UPLOAD_MB` | `25` | Giới hạn dung lượng mỗi request (MB) |
| `USE_PANDOC` | `1` | Dùng pandoc nếu có (`0` để tắt cưỡng bức) |
| `API_KEY` | *(trống)* | Nếu đặt, endpoint convert yêu cầu header `X-API-Key` |
| `RATE_LIMIT_PER_MINUTE` | `0` | Giới hạn request/phút mỗi IP (`0` = tắt) |
| `SANITIZE_HTML` | `1` | Loại script/nội dung động khỏi HTML xuất ra |
| `LOG_LEVEL` | `INFO` | DEBUG/INFO/WARNING/ERROR |
| `LOG_JSON` | `0` | Log JSON có cấu trúc (`1` để bật) |

`python -m app` tôn trọng `HOST`/`PORT`. Entry point `app/__main__.py`.

## Bảo mật

- **Giới hạn upload**: middleware từ chối sớm request vượt `MAX_UPLOAD_MB`
  (HTTP 413) dựa trên `Content-Length`.
- **API key**: khi `API_KEY` được đặt, `/api/convert` và `/api/convert-url`
  cần header `X-API-Key` khớp, nếu không → 401.
- **Rate limit**: giới hạn theo IP mỗi phút (429 kèm `Retry-After`). *Lưu ý:
  trạng thái nằm trong bộ nhớ tiến trình — reset khi restart và không chia sẻ
  giữa nhiều worker.* Với nhiều instance, dùng rate limit ở reverse proxy.
- **SSRF guard** (`/api/convert-url`): chỉ http/https, chặn địa chỉ
  private/loopback/link-local/reserved/multicast, kiểm tra lại sau redirect,
  tối đa 5 redirect, chỉ nhận content-type văn bản/HTML.
- **Sanitize HTML**: loại `<script>`, `<iframe>`, `object/embed`, thuộc tính
  `on*`, URL `javascript:`/`vbscript:` và `data:` không phải ảnh khỏi HTML xuất.

Khi deploy công khai, khuyến nghị: `HOST=0.0.0.0`, đặt `MAX_UPLOAD_MB` hợp lý,
bật `RATE_LIMIT_PER_MINUTE`, cân nhắc `API_KEY`, và `LOG_JSON=1`.

## Pandoc

Bật đọc LaTeX và tăng độ trung thực bảng/ảnh/công thức + mở khóa
epub/revealjs/pptx/rst/org/textile/mediawiki/asciidoc.

- **Docker**: image đã cài sẵn pandoc (qua `apt`).
- **Local**: cài binary `pandoc` (https://pandoc.org/installing.html), hoặc
  `pip install pypandoc_binary` (đóng gói sẵn binary).
- Tắt: `USE_PANDOC=0`.

Kiểm tra: `GET /health` trả `"pandoc": true/false`.

## Docker

```bash
docker build -t text-converter .
docker run -p 8000:8000 -e RATE_LIMIT_PER_MINUTE=60 text-converter
```

## Deploy

- **Fly.io**: dùng `fly.toml` sẵn có — `fly launch --copy-config --now`.
- **Render**: dùng `render.yaml` (New → Blueprint → chọn repo).

Cả hai deploy trực tiếp từ `Dockerfile`, healthcheck tại `/health`.
