"""Round-trip and basic conversion tests for the converter registry."""

import base64
import io
import json

import pytest

from app.converters import (
    ConversionError,
    ConvertOptions,
    convert,
    detect_format,
    list_formats,
    pandoc_ext,
    read_as_document_html,
    render_document,
)

pandoc_only = pytest.mark.skipif(
    not pandoc_ext.PANDOC_AVAILABLE, reason="pandoc binary not available"
)


def _png_bytes() -> bytes:
    from PIL import Image

    img = Image.new("RGB", (8, 8), (0, 128, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_catalogue_has_expected_formats():
    names = {f["name"] for f in list_formats()}
    assert {"txt", "md", "html", "docx", "pdf"} <= names
    assert {"json", "yaml", "csv", "xml"} <= names


# --- Document family --------------------------------------------------------
def test_md_to_html():
    out = convert(b"# Title\n\nHello **world**", "md", "html").decode("utf-8")
    assert "<h1>Title</h1>" in out
    assert "<strong>world</strong>" in out


def test_html_to_md():
    out = convert(b"<h1>Title</h1><p>Hello</p>", "html", "md").decode("utf-8")
    assert "# Title" in out
    assert "Hello" in out


def test_md_to_txt():
    out = convert(b"# Title\n\nHello world", "md", "txt").decode("utf-8")
    assert "Title" in out
    assert "Hello world" in out


def test_md_to_docx_produces_zip():
    out = convert(b"# Heading\n\nBody text", "md", "docx")
    # DOCX files are zip archives -> start with the PK magic bytes.
    assert out[:2] == b"PK"


def test_md_to_pdf_produces_pdf():
    out = convert(b"# Heading\n\nBody text", "md", "pdf")
    assert out[:4] == b"%PDF"


# --- Data family ------------------------------------------------------------
def test_json_to_yaml_and_back():
    src = json.dumps({"name": "Kiro", "tags": ["a", "b"]}).encode("utf-8")
    yaml_bytes = convert(src, "json", "yaml")
    assert b"name: Kiro" in yaml_bytes
    back = convert(yaml_bytes, "yaml", "json")
    assert json.loads(back) == {"name": "Kiro", "tags": ["a", "b"]}


def test_csv_to_json():
    csv_bytes = b"name,age\nAlice,30\nBob,25\n"
    out = json.loads(convert(csv_bytes, "csv", "json"))
    assert out == [{"name": "Alice", "age": "30"}, {"name": "Bob", "age": "25"}]


def test_json_list_to_csv():
    src = json.dumps([{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]).encode()
    out = convert(src, "json", "csv").decode("utf-8")
    assert "name,age" in out
    assert "Alice,30" in out


def test_json_to_xml_and_back():
    src = json.dumps({"root": {"item": ["x", "y"]}}).encode("utf-8")
    xml_bytes = convert(src, "json", "xml")
    assert b"<root>" in xml_bytes
    back = json.loads(convert(xml_bytes, "xml", "json"))
    assert back == {"root": {"item": ["x", "y"]}}


# --- New formats ------------------------------------------------------------
def test_toml_roundtrip_with_json():
    src = b'title = "Demo"\n[owner]\nname = "Kiro"\n'
    obj = json.loads(convert(src, "toml", "json"))
    assert obj == {"title": "Demo", "owner": {"name": "Kiro"}}
    back = convert(json.dumps(obj).encode(), "json", "toml").decode("utf-8")
    assert 'title = "Demo"' in back


def test_html_to_latex():
    # Works with both the pure-Python writer and the Pandoc writer.
    out = convert(b"<h1>Title</h1><p>Body with 50% off</p>", "html", "latex").decode()
    assert "\\documentclass" in out
    assert "\\section" in out
    assert "Title" in out
    assert "50\\%" in out  # special char escaped


def test_html_to_rtf():
    out = convert(b"<p>Hello <strong>bold</strong></p>", "html", "rtf").decode()
    assert out.startswith("{\\rtf1")
    assert "bold" in out


def test_md_to_odt_and_back():
    odt_bytes = convert(b"# Title\n\nHello world", "md", "odt")
    assert odt_bytes[:2] == b"PK"  # ODT is a zip container
    html = convert(odt_bytes, "odt", "html").decode("utf-8")
    assert "Title" in html
    assert "Hello world" in html


def test_rtf_roundtrip_text():
    rtf_bytes = convert(b"<p>Just some text</p>", "html", "rtf")
    txt = convert(rtf_bytes, "rtf", "txt").decode("utf-8")
    assert "Just some text" in txt


# --- Cross-family bridging (data -> document) -------------------------------
def test_json_list_to_html_table():
    src = json.dumps([{"name": "Alice", "age": 30}]).encode()
    html = convert(src, "json", "html").decode("utf-8")
    assert "<table" in html
    assert "Alice" in html


def test_json_to_pdf_via_bridge():
    src = json.dumps({"key": "value"}).encode()
    out = convert(src, "json", "pdf")
    assert out[:4] == b"%PDF"


def test_csv_to_docx_via_bridge():
    out = convert(b"name,age\nAlice,30\n", "csv", "docx")
    assert out[:2] == b"PK"


# --- Auto-detect ------------------------------------------------------------
def test_detect_format_from_extension():
    assert detect_format("report.MD") == "md"
    assert detect_format("data.yml") == "yaml"
    assert detect_format("page.htm") == "html"
    assert detect_format("paper.tex") == "latex"


def test_detect_format_unknown():
    with pytest.raises(ConversionError):
        detect_format("mystery.xyz")
    with pytest.raises(ConversionError):
        detect_format("noext")


# --- Convert options --------------------------------------------------------
def test_toc_option_adds_table_of_contents():
    out = convert(
        b"# One\n\n## Two\n\ntext", "md", "html", ConvertOptions(toc=True)
    ).decode()
    assert 'class="toc"' in out
    assert 'href="#one"' in out
    assert 'id="one"' in out


def test_theme_option_changes_css():
    out = convert(b"# Hi", "md", "html", ConvertOptions(theme="dark")).decode()
    assert "#0d1117" in out  # dark background color


def test_paper_size_in_pdf_uses_page_rule():
    # PDF is binary; just ensure it still renders with a non-default size.
    out = convert(b"# Hi", "md", "pdf", ConvertOptions(paper_size="Letter"))
    assert out[:4] == b"%PDF"


# --- Merge helpers ----------------------------------------------------------
def test_merge_documents_into_one_pdf():
    a = read_as_document_html(b"# Doc A", "md")
    b = read_as_document_html(b"# Doc B", "md")
    combined = a + '<div style="page-break-before:always"></div>' + b
    out = render_document(combined, "pdf", ConvertOptions())
    assert out[:4] == b"%PDF"


def test_render_document_rejects_data_target():
    with pytest.raises(ConversionError):
        render_document("<p>hi</p>", "json", ConvertOptions())


# --- PDF image extraction ---------------------------------------------------
def test_pdf_image_round_trip():
    data_uri = "data:image/png;base64," + base64.b64encode(_png_bytes()).decode()
    html = f'<h1>Doc</h1><p>text</p><img src="{data_uri}">'
    pdf = convert(html.encode(), "html", "pdf")
    assert pdf[:4] == b"%PDF"
    back = convert(pdf, "pdf", "html").decode()
    assert "<img" in back  # embedded image was extracted


# --- Pandoc high-fidelity path (only when the binary is present) ------------
@pandoc_only
def test_latex_is_readable_with_pandoc():
    names = {f["name"]: f for f in list_formats()}
    assert names["latex"]["readable"] is True


@pandoc_only
def test_read_latex_to_markdown_keeps_structure():
    tex = rb"""\documentclass{article}
\begin{document}
\section{Intro}
Hello world.
\end{document}
"""
    md = convert(tex, "latex", "md").decode("utf-8")
    assert "Intro" in md
    assert "Hello world" in md


@pandoc_only
def test_html_table_to_latex_uses_tabular():
    out = convert(
        b"<table><tr><th>X</th><th>Y</th></tr><tr><td>1</td><td>2</td></tr></table>",
        "html",
        "latex",
    ).decode()
    assert "tabular" in out or "longtable" in out


# --- Spreadsheets (XLSX / ODS) ----------------------------------------------
def test_json_to_xlsx_and_back():
    src = json.dumps([{"name": "Al", "age": 30}, {"name": "Bo", "age": 25}]).encode()
    xlsx = convert(src, "json", "xlsx")
    assert xlsx[:2] == b"PK"
    back = json.loads(convert(xlsx, "xlsx", "json"))
    assert [r["name"] for r in back] == ["Al", "Bo"]


def test_csv_to_ods_and_back():
    ods = convert(b"name,age\nAl,30\nBo,25\n", "csv", "ods")
    assert ods[:2] == b"PK"
    back = json.loads(convert(ods, "ods", "json"))
    assert back[0]["name"] == "Al"


# --- Pandoc-only new document formats ---------------------------------------
@pandoc_only
def test_md_to_epub_and_back():
    epub = convert(b"# Chapter\n\nBody text", "md", "epub")
    assert epub[:2] == b"PK"  # epub is a zip container
    back = convert(epub, "epub", "md").decode()
    assert "Chapter" in back


@pandoc_only
def test_md_to_revealjs_slides():
    out = convert(b"# Slide 1\n\nHi\n\n# Slide 2\n\nBye", "md", "revealjs").decode()
    assert "reveal" in out.lower()


@pandoc_only
def test_md_to_pptx():
    out = convert(b"# Slide 1\n\nHi\n\n# Slide 2\n\nBye", "md", "pptx")
    assert out[:2] == b"PK"


# --- Corrupt input handling -------------------------------------------------
def test_corrupt_input_raises_conversion_error():
    with pytest.raises(ConversionError):
        convert(b"this is definitely not a valid xlsx file", "xlsx", "json")


# --- Error handling ---------------------------------------------------------
def test_document_to_data_rejected():
    # No bridge exists in the document -> data direction.
    with pytest.raises(ConversionError):
        convert(b"# hi", "md", "json")


def test_unknown_format_rejected():
    with pytest.raises(ConversionError):
        convert(b"hi", "txt", "nope")
