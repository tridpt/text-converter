# Text Format Converter

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

- **Ảnh**: `docx → html/pdf` giữ được ảnh (nhúng base64), `html → docx`
  chèn lại ảnh từ data URI.
- **Bảng**: bảng được giữ khi chuyển `docx ↔ html ↔ md` và `html → docx`.
- **Định dạng inline**: in đậm/nghiêng được giữ trong `html → docx/rtf`.
- **Nhiều file**: upload nhiều file cùng lúc → tải về một file `.zip`.

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
uvicorn app.main:app --reload
```

Mở http://127.0.0.1:8000 — API docs tại http://127.0.0.1:8000/docs

## Thêm định dạng mới

Trong `documents.py` hoặc `data.py`:

```python
register_format(FormatSpec("rst", "document", "reStructuredText", ".rst", "text/x-rst", False))

@reader("rst")
def read_rst(data: bytes) -> str: ...   # -> HTML

@writer("rst")
def write_rst(html: str) -> bytes: ...  # HTML -> bytes
```
