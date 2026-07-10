# Hướng dẫn sử dụng

## Chạy web app

```bash
pip install -r requirements.txt
python -m app
```

Mở http://127.0.0.1:8000. Muốn auto-reload khi dev: `uvicorn app.main:app --reload`.

### Giao diện web

**Tab "Từ file"**
1. Kéo & thả file (hoặc cả thư mục) vào vùng drop, hoặc bấm để chọn.
2. Chọn **định dạng nguồn** (hoặc để "Tự động" — nhận diện theo đuôi file) và
   **định dạng đích**.
3. (Tùy chọn) Tick **Gộp nhiều file thành 1** để nối tất cả input thành một
   tài liệu duy nhất.
4. Bấm **Xem trước** để kiểm tra, hoặc **Chuyển đổi & Tải về**.

**Tab "Từ URL"**
1. Dán link trang web công khai (http/https).
2. Chọn định dạng đích (chỉ nhóm tài liệu).
3. Bấm chuyển đổi — trang web được tải về, làm sạch, rồi chuyển đổi.

**Tùy chọn** (áp dụng cho cả hai tab)
- **Theme** (HTML/PDF): default, github, dark, minimal
- **Cỡ giấy** (PDF): A4, Letter, Legal, A3, A5
- **Tiêu đề / Tác giả** (metadata): nhúng vào epub/docx/...
- **Mục lục**: tự sinh từ các heading
- **Đánh số trang** (PDF)

**Xem trước theo định dạng đích**
- `pdf` → khung xem PDF; `html` → khung iframe (sandbox)
- `revealjs` → mở slide ở **tab mới**
- Định dạng text (md, json, csv, txt, yaml, xml, latex, rtf) → hiển thị văn bản
- `docx`, `odt`, `epub`, `pptx` → không xem trước, hãy tải về

**Nhiều file**
- Không gộp → tải về một file `.zip` chứa từng file đã chuyển.
- Có gộp → một file tài liệu duy nhất (mỗi input một trang khi xuất PDF).

**Song ngữ**: nút VI/EN ở góc phải, lựa chọn được ghi nhớ.

## Dòng lệnh (CLI)

CLI dùng chung engine với web app.

```bash
python -m app.cli INPUT [INPUT...] OUTPUT [options]
```

Định dạng nguồn suy ra từ đuôi file input, đích từ đuôi file output (có thể
ghi đè bằng `--from` / `--to`).

### Ví dụ

```bash
# Chuyển đơn giản (đoán định dạng theo đuôi)
python -m app.cli report.md report.pdf

# Dữ liệu
python -m app.cli data.json data.yaml
python -m app.cli table.csv table.xlsx

# Gộp nhiều file thành một ebook
python -m app.cli ch1.md ch2.md ch3.md book.epub --title "Sách của tôi" --author "Kiro"

# PDF có mục lục, đánh số trang, theme github
python -m app.cli paper.tex out.pdf --toc --page-numbers --theme github -p A4

# Ép định dạng khi đuôi file không chuẩn
python -m app.cli input.txt output.bin --to html
```

### Cờ dòng lệnh

| Cờ | Mô tả |
|----|-------|
| `-f`, `--from` | Định dạng nguồn (mặc định: theo đuôi input) |
| `-t`, `--to` | Định dạng đích (mặc định: theo đuôi output) |
| `--theme` | Theme CSS: default/github/dark/minimal |
| `-p`, `--paper-size` | Cỡ giấy PDF |
| `--toc` | Thêm mục lục |
| `--title` | Metadata tiêu đề |
| `--author` | Metadata tác giả |
| `--page-numbers` | Đánh số trang PDF |

Mã thoát: `0` thành công, `1` lỗi chuyển đổi/không tìm thấy file, `2` sai tham số.

## Ma trận định dạng

Trang `/matrix` (hoặc `GET /api/matrix`) hiển thị cặp nguồn → đích nào chuyển
được. Xem [FORMATS.md](FORMATS.md) để hiểu quy tắc.
