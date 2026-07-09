# Text Format Converter

[![CI](https://github.com/tridpt/text-converter/actions/workflows/ci.yml/badge.svg)](https://github.com/tridpt/text-converter/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/)

Web app (Python + FastAPI) chuyển đổi qua lại giữa nhiều định dạng file văn bản.

## Định dạng hỗ trợ

| Nhóm | Định dạng | Hub trung gian |
|------|-----------|----------------|
| Tài liệu | `txt`, `md`, `html`, `docx`, `pdf`, `rtf`, `odt`, `latex` | HTML |
| Dữ liệu | `json`, `yaml`, `csv`, `xml`, `toml` | Python object |

Chuyển đổi tự do **trong cùng một nhóm**. Ví dụ: `md → pdf`, `docx → md`,
`odt → html`, `json → yaml`, `csv → json`, `toml → json`...

**Cầu nối chéo nhóm (`data → document`):** dữ liệu có thể xuất sang tài liệu.
Object sẽ được render thành bảng HTML rồi chuyển tiếp. Ví dụ: `csv → docx`,
`json → pdf`, `yaml → md`.

Ghi chú:
- `latex` hiện chỉ **ghi** (HTML → LaTeX), chưa đọc.
- `pdf` đọc được (trích xuất text), `pdf`/`docx`/`odt` là đầu ra nhị phân.
- Chiều `document → data` (ví dụ `md → json`) không có cầu nối vì không có
  ý nghĩa rõ ràng.

## Tính năng

- **Tự phát hiện định dạng nguồn** từ đuôi file (chọn "Tự động", hỗ trợ cả
  `.yml`, `.htm`, `.markdown`, `.tex`...).
- **Chuyển đổi từ URL**: dán link trang web → md/pdf/docx... (có chặn SSRF,
  chỉ nhận http/https công khai).
- **Gộp nhiều file thành 1**: nhiều `.md`/`.docx`... → một file tài liệu duy
  nhất (mỗi file một trang khi xuất PDF).
- **Tùy chọn khi convert**:
  - Cỡ giấy PDF: A4, Letter, Legal, A3, A5
  - Mục lục (Table of Contents) tự sinh từ các heading
  - Theme CSS cho HTML/PDF: default, github, dark, minimal
- **Ảnh**: `docx → html/pdf` giữ được ảnh (nhúng base64), `html → docx`
  chèn lại ảnh từ data URI.
- **Bảng**: bảng được giữ khi chuyển `docx ↔ html ↔ md` và `html → docx`.
- **Định dạng inline**: in đậm/nghiêng được giữ trong `html → docx/rtf`.
- **Nhiều file**: upload nhiều file cùng lúc → tải về một file `.zip`.

## API

| Endpoint | Mô tả |
|----------|-------|
| `GET /api/formats` | Danh mục định dạng |
| `POST /api/convert` | Convert file. Fields: `files`, `source` (hoặc `auto`), `target`, `paper_size`, `toc`, `theme`, `merge` |
| `POST /api/convert-url` | Convert từ URL. Fields: `url`, `target`, `paper_size`, `toc`, `theme` |

## Kiến trúc

Dùng mô hình **hub-and-spoke**: mỗi định dạng chỉ cần 1 *reader*
(`bytes → hub`) và 1 *writer* (`hub → bytes`). Nhờ đó thêm định dạng mới
không phải viết N×N cặp chuyển đổi.

```
app/
├── main.py                 # FastAPI: /  /api/formats  /api/convert
├── templates/index.html    # Giao diện web
└── converters/
    ├── registry.py         # Registry + logic convert
    ├── documents.py        # Nhóm tài liệu (hub = HTML)
    └── data.py             # Nhóm dữ liệu (hub = Python object) + bridge data→document
```

Endpoint `/api/convert` nhận 1 hoặc nhiều file (field `files`), `source`,
`target`. Một file trả về trực tiếp, nhiều file trả về `.zip`.

## Cài đặt & chạy

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m app
```

Mở http://127.0.0.1:8000 — API docs tại http://127.0.0.1:8000/docs

Để dev có auto-reload: `uvicorn app.main:app --reload`

## Cấu hình (biến môi trường)

Sao chép `.env.example` và chỉnh nếu cần:

| Biến | Mặc định | Mô tả |
|------|----------|-------|
| `HOST` | `127.0.0.1` | Interface bind (dùng `0.0.0.0` để mở ra mạng/Docker) |
| `PORT` | `8000` | Cổng web server |
| `MAX_UPLOAD_MB` | `25` | Giới hạn dung lượng mỗi request (MB) |

## Chạy bằng Docker

```bat
docker build -t text-converter .
docker run -p 8000:8000 text-converter
```

Mở http://127.0.0.1:8000

## Chạy test

```bat
pip install pytest
pytest -q
```

## Thêm định dạng mới

Trong `documents.py` hoặc `data.py`:

```python
register_format(FormatSpec("rst", "document", "reStructuredText", ".rst", "text/x-rst", False))

@reader("rst")
def read_rst(data: bytes) -> str: ...   # -> HTML

@writer("rst")
def write_rst(html: str) -> bytes: ...  # HTML -> bytes
```
