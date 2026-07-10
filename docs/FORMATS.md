# Định dạng & khả năng chuyển đổi

Mỗi định dạng thuộc một **nhóm** (family) và dùng một biểu diễn trung gian (hub):

- **Nhóm tài liệu** — hub là chuỗi HTML
- **Nhóm dữ liệu** — hub là object Python (dict/list/...)

## Nhóm tài liệu

| Định dạng | Đuôi | Đọc | Ghi | Ghi chú |
|-----------|------|-----|-----|---------|
| `txt` | .txt | ✓ | ✓ | thuần Python |
| `md` | .md | ✓ | ✓ | ghi dùng pandoc nếu có (bảng tốt hơn) |
| `html` | .html | ✓ | ✓ | thuần Python, có theme |
| `docx` | .docx | ✓ | ✓ | pandoc nếu có, không thì mammoth/python-docx |
| `pdf` | .pdf | ✓ | ✓ | đọc: trích text + ảnh; ghi: xhtml2pdf |
| `rtf` | .rtf | ✓ | ✓ | đọc: striprtf; ghi: pandoc nếu có |
| `odt` | .odt | ✓ | ✓ | pandoc nếu có, không thì odfpy |
| `latex` | .tex | pandoc | ✓ | **đọc cần pandoc** |
| `epub` | .epub | pandoc | pandoc | **cần pandoc** |
| `revealjs` | .html | — | pandoc | slide reveal.js, **cần pandoc** |
| `pptx` | .pptx | — | pandoc | slide PowerPoint, **cần pandoc** |
| `rst` | .rst | pandoc | pandoc | **cần pandoc** |
| `org` | .org | pandoc | pandoc | **cần pandoc** |
| `textile` | .textile | pandoc | pandoc | **cần pandoc** |
| `mediawiki` | .wiki | pandoc | pandoc | **cần pandoc** |
| `asciidoc` | .adoc | — | pandoc | **cần pandoc** (pandoc không đọc AsciiDoc) |

## Nhóm dữ liệu

| Định dạng | Đuôi | Đọc | Ghi | Ghi chú |
|-----------|------|-----|-----|---------|
| `json` | .json | ✓ | ✓ | |
| `yaml` | .yaml/.yml | ✓ | ✓ | |
| `csv` | .csv | ✓ | ✓ | dạng list-of-dicts |
| `xml` | .xml | ✓ | ✓ | ánh xạ phần tử ↔ dict |
| `toml` | .toml | ✓ | ✓ | không biểu diễn được `null` |
| `xlsx` | .xlsx | ✓ | ✓ | openpyxl, sheet đầu |
| `ods` | .ods | ✓ | ✓ | odfpy |

## Quy tắc chuyển đổi

1. **Cùng nhóm** → chuyển tự do giữa mọi cặp (nguồn đọc được × đích ghi được).
2. **Nhóm dữ liệu → nhóm tài liệu** (bridge): object được render thành bảng
   HTML rồi tiếp tục như tài liệu. Ví dụ `csv → pdf`, `json → docx`.
3. **Nhóm tài liệu → nhóm dữ liệu**: **không hỗ trợ** (không có ý nghĩa rõ ràng).

Ví dụ hợp lệ: `md → pdf`, `docx → md`, `latex → html`, `json → yaml`,
`csv → xlsx`, `yaml → docx` (bridge). Không hợp lệ: `md → json`.

## Vai trò của Pandoc

Khi có binary `pandoc` (và `USE_PANDOC != 0`), các reader/writer sau bị **ghi
đè** bằng pandoc để tăng độ trung thực (bảng, ảnh, công thức) và mở khóa các
định dạng cần pandoc:

- Đọc: `latex`, `docx`, `odt`, `epub`, `rst`, `org`, `textile`, `mediawiki`
- Ghi: `latex`, `docx`, `odt`, `rtf`, `md`, `epub`, `revealjs`, `pptx`, `rst`,
  `org`, `textile`, `mediawiki`, `asciidoc`

Không có pandoc, các định dạng "cần pandoc" sẽ **không xuất hiện** làm nguồn/đích
trong UI, và bộ chuyển đổi thuần Python được dùng cho phần còn lại. `pdf` luôn
dùng thuần Python (đọc trích text + ảnh, ghi qua xhtml2pdf).

Cách cài pandoc: xem [CONFIGURATION.md](CONFIGURATION.md#pandoc).
