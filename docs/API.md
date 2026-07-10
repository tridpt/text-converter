# Tham chiếu API HTTP

Base URL mặc định: `http://127.0.0.1:8000`. Tài liệu OpenAPI tương tác tại
`/docs` (Swagger UI).

Nếu đặt `API_KEY`, các endpoint `/api/convert` và `/api/convert-url` yêu cầu
header `X-API-Key`. Xem [CONFIGURATION.md](CONFIGURATION.md).

---

## GET /health

Health check nhẹ cho load balancer / nền tảng.

```json
{ "status": "ok", "pandoc": true }
```

## GET /api/formats

Danh mục định dạng và khả năng đọc/ghi hiện tại.

```json
{
  "formats": [
    { "name": "md", "family": "document", "label": "Markdown",
      "extension": ".md", "readable": true, "writable": true }
  ]
}
```

## GET /api/matrix

Ma trận cặp nguồn → đích được hỗ trợ.

```json
{
  "sources": [ { "name": "md", "label": "Markdown", "family": "document" } ],
  "targets":  [ { "name": "pdf", "label": "PDF", "family": "document" } ],
  "pairs":    { "md": { "pdf": true, "json": false } }
}
```

## GET /matrix

Trang HTML hiển thị ma trận định dạng (dành cho người dùng).

---

## POST /api/convert

Chuyển đổi một hoặc nhiều file (multipart/form-data).

| Field | Kiểu | Mặc định | Mô tả |
|-------|------|----------|-------|
| `files` | file[] | — | Một hoặc nhiều file (bắt buộc) |
| `source` | string | `auto` | Định dạng nguồn, hoặc `auto` (theo đuôi file) |
| `target` | string | — | Định dạng đích (bắt buộc) |
| `paper_size` | string | `A4` | A4/Letter/Legal/A3/A5 (PDF) |
| `toc` | bool | `false` | Thêm mục lục |
| `theme` | string | `default` | default/github/dark/minimal |
| `merge` | bool | `false` | Gộp nhiều file thành một tài liệu |
| `title` | string | `""` | Metadata tiêu đề |
| `author` | string | `""` | Metadata tác giả |
| `page_numbers` | bool | `false` | Đánh số trang PDF |

**Phản hồi**
- 1 file → file kết quả (attachment) với đúng MIME.
- Nhiều file, không gộp → `application/zip`.
- Nhiều file, có gộp → một file tài liệu (`merged.<ext>`).

**Mã lỗi**: `400` (input sai/hỏng, định dạng không hợp lệ, đuôi không nhận
diện được), `401` (thiếu/sai API key), `413` (quá dung lượng), `429` (quá
giới hạn tần suất), `500` (lỗi không lường trước).

### Ví dụ

```bash
# md -> pdf, có mục lục
curl -X POST http://127.0.0.1:8000/api/convert \
  -F "files=@report.md" -F "source=md" -F "target=pdf" -F "toc=true" \
  -o report.pdf

# tự đoán nguồn, nhiều file -> zip
curl -X POST http://127.0.0.1:8000/api/convert \
  -F "files=@a.md" -F "files=@b.docx" -F "source=auto" -F "target=html" \
  -o out.zip

# gộp thành epub kèm metadata
curl -X POST http://127.0.0.1:8000/api/convert \
  -F "files=@c1.md" -F "files=@c2.md" -F "source=auto" -F "target=epub" \
  -F "merge=true" -F "title=My Book" -F "author=Kiro" -o book.epub
```

## POST /api/convert-url

Tải một trang web rồi chuyển đổi (đích phải là **nhóm tài liệu**).

| Field | Kiểu | Mặc định | Mô tả |
|-------|------|----------|-------|
| `url` | string | — | URL http/https công khai (bắt buộc) |
| `target` | string | — | Định dạng tài liệu đích (bắt buộc) |
| `paper_size`, `toc`, `theme`, `title`, `author`, `page_numbers` | | | như trên |

**Bảo mật**: chặn scheme khác http/https, chặn địa chỉ nội bộ/loopback (SSRF),
tối đa 5 redirect, chỉ nhận content-type văn bản/HTML, giới hạn dung lượng.

### Ví dụ

```bash
curl -X POST http://127.0.0.1:8000/api/convert-url \
  -F "url=https://example.com" -F "target=md" -o example.md
```

Nếu bật API key, thêm `-H "X-API-Key: <key>"` vào mọi request convert.
