# Text Format Converter

[![CI](https://github.com/tridpt/text-converter/actions/workflows/ci.yml/badge.svg)](https://github.com/tridpt/text-converter/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/)
[![codecov](https://codecov.io/gh/tridpt/text-converter/branch/main/graph/badge.svg)](https://codecov.io/gh/tridpt/text-converter)
[![Formats](https://img.shields.io/badge/formats-23-brightgreen.svg)](/matrix)
[![Ruff](https://img.shields.io/badge/lint-ruff-orange.svg)](https://github.com/astral-sh/ruff)

Web app (Python + FastAPI) chuyển đổi qua lại giữa nhiều định dạng file văn bản.

## Ảnh chụp màn hình

<!-- Thêm ảnh/GIF demo vào thư mục docs/ rồi bỏ comment các dòng dưới:
![Giao diện chính](docs/screenshot-home.png)
![Ma trận định dạng](docs/screenshot-matrix.png)
-->

> Chưa có ảnh. Xem [docs/README.md](docs/README.md) để biết cách chụp và thêm.

## Tài liệu

| Tài liệu | Nội dung |
|----------|----------|
| [docs/USAGE.md](docs/USAGE.md) | Hướng dẫn sử dụng (web UI, CLI, ví dụ) |
| [docs/FORMATS.md](docs/FORMATS.md) | Định dạng, khả năng đọc/ghi, vai trò pandoc |
| [docs/API.md](docs/API.md) | Tham chiếu API HTTP + ví dụ `curl` |
| [docs/CONFIGURATION.md](docs/CONFIGURATION.md) | Biến môi trường, bảo mật, deploy |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Kiến trúc & luồng xử lý |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Hướng dẫn đóng góp |

## Định dạng hỗ trợ

| Nhóm | Định dạng | Hub trung gian |
|------|-----------|----------------|
| Tài liệu | `txt`, `md`, `html`, `docx`, `pdf`, `rtf`, `odt`, `latex`, `epub`*, `revealjs`*, `pptx`*, `rst`*, `org`*, `textile`*, `mediawiki`*, `asciidoc`* | HTML |
| Dữ liệu | `json`, `yaml`, `csv`, `xml`, `toml`, `xlsx`, `ods` | Python object |

`*` cần pandoc. `epub` đọc + ghi; `rst`/`org`/`textile`/`mediawiki` đọc + ghi;
`revealjs`/`pptx`/`asciidoc` chỉ ghi (`revealjs`/`pptx` tạo slide từ heading).

Chuyển đổi tự do **trong cùng một nhóm**. Ví dụ: `md → pdf`, `docx → md`,
`odt → html`, `json → yaml`, `csv → json`, `toml → json`...

**Cầu nối chéo nhóm (`data → document`):** dữ liệu có thể xuất sang tài liệu.
Object sẽ được render thành bảng HTML rồi chuyển tiếp. Ví dụ: `csv → docx`,
`json → pdf`, `yaml → md`.

Ghi chú:
- `latex`: **ghi** luôn được; **đọc** cần pandoc (xem mục dưới).
- `pdf` đọc được (trích text + ảnh), `pdf`/`docx`/`odt` là đầu ra nhị phân.
- Chiều `document → data` (ví dụ `md → json`) không có cầu nối vì không có
  ý nghĩa rõ ràng.

## Chất lượng cao với Pandoc (tùy chọn)

Nếu có sẵn **pandoc** trên máy, app tự động dùng nó cho các chuyển đổi chất
lượng cao (giữ bảng, ảnh, công thức tốt hơn nhiều) và **mở khóa đọc LaTeX**.
Không có pandoc thì app vẫn chạy bình thường bằng bộ chuyển đổi pure-Python.

Khi pandoc bật, nó thay thế:
- Đọc (`→ HTML`): `latex` (mới), `docx`, `odt` — kèm trích ảnh (nhúng base64)
  và công thức (MathML).
- Ghi (`HTML →`): `latex`, `docx`, `odt`, `rtf`, `md` — giữ bảng, danh sách,
  công thức (LaTeX/MathML → OMML của Word).

Cài pandoc:
- Docker: đã cài sẵn trong image.
- Windows/macOS/Linux: cài binary `pandoc`, hoặc `pip install pypandoc_binary`
  (đóng gói sẵn binary).
- Tắt cưỡng bức: đặt biến môi trường `USE_PANDOC=0`.

`pdf` vẫn dùng bộ pure-Python: đọc trích text + **trích ảnh nhúng** (pypdf),
ghi qua xhtml2pdf (giữ tùy chọn cỡ giấy/theme).

## Tính năng

- **Song ngữ**: giao diện tiếng Việt / English (nút chuyển ở góc phải, nhớ lựa chọn).
- **Kéo & thả file hoặc cả thư mục** (đệ quy) + danh sách file, nút xóa hết.
- **Xem trước slide** (reveal.js) mở ở tab mới; PDF/HTML render trong khung.
- **Chống nội dung độc hại**: tự loại `<script>`, iframe, thuộc tính `on*`,
  URL `javascript:`/`data:` không phải ảnh khỏi HTML xuất ra.
- **Xem trước** kết quả trước khi tải: text hiển thị trực tiếp, HTML/PDF
  render trong khung xem trước.
- **Thanh tiến trình** hiển thị % upload rồi trạng thái đang xử lý.
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
  - Metadata tiêu đề/tác giả (nhúng vào epub/docx/...)
  - Đánh số trang cho PDF
- **Ảnh**: `docx → html/pdf` giữ được ảnh (nhúng base64), `html → docx`
  chèn lại ảnh từ data URI.
- **Bảng**: bảng được giữ khi chuyển `docx ↔ html ↔ md` và `html → docx`.
- **Định dạng inline**: in đậm/nghiêng được giữ trong `html → docx/rtf`.
- **Nhiều file**: upload nhiều file cùng lúc → tải về một file `.zip`.

## API

| Endpoint | Mô tả |
|----------|-------|
| `GET /api/formats` | Danh mục định dạng |
| `GET /api/matrix` | Ma trận cặp nguồn → đích hỗ trợ |
| `POST /api/convert` | Convert file. Fields: `files`, `source` (hoặc `auto`), `target`, `paper_size`, `toc`, `theme`, `merge`, `title`, `author`, `page_numbers` |
| `POST /api/convert-url` | Convert từ URL. Fields: `url`, `target`, `paper_size`, `toc`, `theme`, `title`, `author`, `page_numbers` |

Nếu đặt `API_KEY`, hai endpoint convert cần header `X-API-Key`.

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
| `USE_PANDOC` | `1` | Dùng pandoc nếu có (`0` để tắt) |
| `API_KEY` | *(trống)* | Nếu đặt, endpoint convert yêu cầu header `X-API-Key` |
| `RATE_LIMIT_PER_MINUTE` | `0` | Giới hạn request/phút mỗi IP (`0` = tắt) |
| `SANITIZE_HTML` | `1` | Loại script/nội dung động khỏi HTML xuất ra (`0` để tắt) |
| `LOG_LEVEL` | `INFO` | Mức log (DEBUG/INFO/WARNING/ERROR) |
| `LOG_JSON` | `0` | Log dạng JSON có cấu trúc cho production (`1` để bật) |

> Rate limit lưu trong bộ nhớ tiến trình — reset khi restart và không chia sẻ
> giữa nhiều worker. Đủ dùng cho single-instance; nếu chạy nhiều instance nên
> dùng reverse proxy hoặc store dùng chung.

## CLI

Dùng chung engine với web app:

```bash
python -m app.cli report.md report.pdf          # tự đoán định dạng theo đuôi
python -m app.cli data.json data.yaml
python -m app.cli a.md b.md c.md book.epub       # nhiều input -> gộp 1 file
python -m app.cli page.tex out.docx --toc --theme github -p A4
```

Tùy chọn: `-f/--from`, `-t/--to` (ghi đè định dạng), `--toc`, `--theme`,
`-p/--paper-size`.

## Ma trận định dạng

Xem trang `/matrix` (hoặc API `GET /api/matrix`) để biết cặp nguồn → đích nào
chuyển được.

## Chạy bằng Docker

```bat
docker build -t text-converter .
docker run -p 8000:8000 text-converter
```

Mở http://127.0.0.1:8000 — healthcheck tại `/health`.

## Deploy

Cả hai nền tảng dưới đây deploy trực tiếp từ `Dockerfile` (đã có pandoc).
Config production mẫu bật sẵn `RATE_LIMIT_PER_MINUTE=60` và `HOST=0.0.0.0`.

### Fly.io (dùng `fly.toml`)

```bash
# Cài flyctl: https://fly.io/docs/hands-on/install-flyctl/
fly auth login
fly launch --copy-config --now      # dùng fly.toml sẵn có (đổi tên app nếu trùng)
# các lần sau:
fly deploy
```

### Render (dùng `render.yaml`)

1. Push repo lên GitHub (đã xong).
2. Trên Render: **New → Blueprint**, chọn repo này. Render tự đọc `render.yaml`.
3. Bấm **Apply**. Render build Docker và cấp URL công khai.

Sau khi deploy, đặt thêm `API_KEY` (nếu muốn giới hạn truy cập) và điều chỉnh
`MAX_UPLOAD_MB` tùy nhu cầu.

## Phát triển (test & lint)

```bat
pip install -r requirements-dev.txt
pytest -q                                   # chạy test (kèm pandoc)
pytest --cov=app --cov-report=term-missing  # kèm báo cáo coverage
ruff check app tests                        # lint
ruff format app tests                       # format code
```

CI trên GitHub Actions chạy lint (ruff) + test có đo coverage (ngưỡng tối
thiểu 90%, hiện ~93%) mỗi lần push/PR, và upload lên Codecov.

## Thêm định dạng mới

Trong `documents.py` hoặc `data.py`:

```python
register_format(FormatSpec("rst", "document", "reStructuredText", ".rst", "text/x-rst", False))

@reader("rst")
def read_rst(data: bytes) -> str: ...   # -> HTML

@writer("rst")
def write_rst(html: str) -> bytes: ...  # HTML -> bytes
```
