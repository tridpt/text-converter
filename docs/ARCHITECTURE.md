# Kiến trúc

## Tổng quan

Text Format Converter là web app FastAPI + CLI, chia sẻ một lõi chuyển đổi
duy nhất trong `app/converters/`.

```
app/
├── main.py            # FastAPI: endpoints + middleware (log, size, API key, rate limit)
├── cli.py             # CLI dùng chung engine
├── __main__.py        # entry point: python -m app
├── config.py          # cấu hình qua biến môi trường
├── logging_config.py  # logging plain/JSON + helper
├── templates/         # index.html (UI song ngữ), matrix.html
└── converters/
    ├── registry.py    # registry, convert(), bridge, ma trận, options, sanitize/toc hooks
    ├── documents.py   # nhóm tài liệu (hub = HTML): reader/writer thuần Python, theme, TOC, sanitize
    ├── data.py        # nhóm dữ liệu (hub = object): reader/writer + bridge data→document
    └── pandoc_ext.py  # ghi đè reader/writer bằng pandoc khi có sẵn
```

## Hub-and-spoke

Mỗi định dạng thuộc một **nhóm** (family); mỗi nhóm dùng một biểu diễn trung
gian (**hub**):

- Nhóm `document` → hub là chuỗi **HTML**
- Nhóm `data` → hub là **object Python**

Mỗi định dạng chỉ cần một **reader** (`bytes → hub`) và một **writer**
(`hub → bytes`). Nhờ đó mọi cặp trong cùng nhóm chuyển được cho nhau mà không
phải viết N×N converter — chỉ cần N reader + N writer.

```
        reader                         writer
bytes  ────────►   hub (HTML / object)  ────────►  bytes
(nguồn)          ▲ transforms: sanitize, TOC ▲     (đích)
                 └──── bridge (data→document) ────┘
```

## Luồng `convert()`

`registry.convert(data, source, target, options)`:

1. Tra `FormatSpec` của nguồn/đích; kiểm tra reader/writer tồn tại.
2. `_read(source, data)` → hub. Lỗi parse bất ngờ được gói thành
   `ConversionError` (→ HTTP 400) để báo "file có thể hỏng".
3. Nếu **khác nhóm**: tra bridge `(src.family, tgt.family)`. Chỉ có bridge
   `data → document` (render object thành bảng HTML). Không có → lỗi.
4. Nếu đích là nhóm tài liệu: áp dụng **transforms** trên hub HTML:
   - sanitize HTML (bỏ script/nội dung động) — nếu `SANITIZE_HTML`
   - chèn mục lục — nếu `options.toc`
5. `writer(hub, options)` → bytes.

Các hàm phụ trợ: `read_as_document_html()` (đọc + bridge sang HTML, dùng cho
gộp file và URL), `render_document()` (ghi HTML hub ra định dạng tài liệu).

## Options

`ConvertOptions(paper_size, toc, theme, title, author, page_numbers)` được
truyền xuyên suốt tới writer. Ví dụ:
- `theme`/`paper_size`/`page_numbers` → dùng khi bọc tài liệu HTML/PDF.
- `title`/`author` → truyền thành metadata pandoc (`-M title=...`).
- `toc` → transform trên hub trước khi ghi (áp dụng cho mọi writer tài liệu).

## Lớp Pandoc

`pandoc_ext.py` phát hiện binary pandoc lúc import. Nếu có (và
`USE_PANDOC != 0`), nó **ghi đè** các reader/writer chọn lọc bằng bản pandoc
(chất lượng cao hơn: bảng, ảnh, công thức) và đăng ký thêm định dạng chỉ
pandoc mới làm được. Vì chỉ thay reader/writer *trong* kiến trúc hub, toàn bộ
hệ thống options (theme/TOC/sanitize/metadata) vẫn hoạt động không đổi.

Import theo thứ tự trong `converters/__init__.py`: `documents` → `data` →
`pandoc_ext` (cuối cùng, để ghi đè có hiệu lực).

## Mở rộng

Thêm định dạng mới: chỉ cần một `FormatSpec` + `@reader`/`@writer`. Chi tiết
và ví dụ trong [../CONTRIBUTING.md](../CONTRIBUTING.md).

## Web layer

- Middleware `request_logger`: log method/path/status/duration.
- Middleware `gatekeeper`: giới hạn dung lượng, API key, rate limit.
- SSRF guard cho `/api/convert-url`.
- UI (`index.html`) là trang tĩnh + JS thuần, i18n VI/EN, gọi `/api/*`.

Xem thêm: [API.md](API.md), [CONFIGURATION.md](CONFIGURATION.md),
[FORMATS.md](FORMATS.md).
