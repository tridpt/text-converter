# Đóng góp cho Text Format Converter

Cảm ơn bạn đã quan tâm! Tài liệu này mô tả kiến trúc và cách thêm tính năng.

## Cài đặt môi trường

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

`requirements-dev.txt` kèm `pypandoc-binary` (đóng gói sẵn pandoc), `ruff`,
`pytest`, `httpx` — đủ để chạy toàn bộ test kể cả nhánh pandoc.

## Chạy

```bash
python -m app                  # web app tại http://127.0.0.1:8000
python -m app.cli in.md out.pdf  # CLI
pytest -q                      # test
ruff check app tests           # lint
ruff format app tests          # format
```

## Kiến trúc

Lõi là **registry hub-and-spoke** (`app/converters/registry.py`). Mỗi định
dạng thuộc một *nhóm* (family), mỗi nhóm dùng một biểu diễn trung gian (hub):

| Nhóm | Hub | Định dạng |
|------|-----|-----------|
| `document` | chuỗi HTML | txt, md, html, docx, pdf, rtf, odt, latex, epub, revealjs, pptx |
| `data` | object Python | json, yaml, csv, xml, toml, xlsx, ods |

Mỗi định dạng chỉ cần một **reader** (`bytes → hub`) và một **writer**
(`hub → bytes`). Nhờ đó mọi cặp trong cùng nhóm chuyển được cho nhau mà không
phải viết N×N converter.

```
app/
├── main.py                  # FastAPI: endpoints + middleware (size/API key/rate limit)
├── cli.py                   # CLI dùng chung engine
├── config.py                # cấu hình qua biến môi trường
├── templates/               # index.html, matrix.html
└── converters/
    ├── registry.py          # registry, convert(), bridge, ma trận hỗ trợ
    ├── documents.py         # nhóm tài liệu (hub = HTML) + theme/TOC
    ├── data.py              # nhóm dữ liệu (hub = object) + bridge data→document
    └── pandoc_ext.py        # ghi đè reader/writer bằng pandoc khi có sẵn
```

**Bridge**: nhóm dữ liệu có thể xuất sang tài liệu (`_obj_to_html` render object
thành bảng HTML), nên `csv → pdf`, `json → docx`... đều chạy.

**Pandoc**: khi có binary pandoc, `pandoc_ext.py` ghi đè các reader/writer chọn
lọc để tăng độ trung thực (bảng, ảnh, công thức) và mở khóa đọc LaTeX. Không có
pandoc thì fallback về bộ pure-Python.

## Thêm một định dạng mới

Ví dụ thêm `.rst` (reStructuredText) vào nhóm tài liệu:

```python
# trong documents.py
register_format(
    FormatSpec("rst", "document", "reStructuredText", ".rst", "text/x-rst", False)
)

@reader("rst")
def read_rst(data: bytes) -> str:
    ...   # trả về chuỗi HTML (hub)

@writer("rst")
def write_rst(html: str, options: ConvertOptions | None = None) -> bytes:
    ...   # nhận HTML hub, trả về bytes
```

Định dạng mới tự động chuyển được với mọi định dạng cùng nhóm. Nếu chỉ có
reader hoặc chỉ có writer, nó sẽ hiển thị tương ứng trong UI (nguồn/đích).

Nếu định dạng chỉ pandoc xử lý được: đăng ký `FormatSpec` ở `documents.py`
(không kèm reader/writer pure-Python) rồi thêm cấu hình vào `_READ_CONFIG` /
`_WRITE_CONFIG` trong `pandoc_ext.py`.

## Quy ước

- Code theo `ruff` (lint + format). Chạy `ruff check` và `ruff format` trước khi mở PR.
- Thêm test cho mọi tính năng/định dạng mới (`tests/`). Test cần pandoc dùng
  marker `@pandoc_only` để tự bỏ qua khi máy không có pandoc.
- Viết commit message rõ ràng, mô tả "cái gì" và "tại sao".

## Mở Pull Request

1. Fork và tạo nhánh từ `main`.
2. Đảm bảo `ruff check`, `ruff format --check` và `pytest` đều xanh.
3. Mô tả thay đổi, cách test, và tính năng bị ảnh hưởng (nếu có).
