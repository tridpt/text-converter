"""Tests for the pure-Python document converters.

These call the functions in ``documents.py`` directly so they are exercised
even when Pandoc is installed and overrides the registry entries.
"""

from app.converters import documents as D


# --- Writers (HTML hub -> bytes) --------------------------------------------
def test_pure_write_html_wraps_fragment():
    out = D.write_html("<p>hi</p>").decode()
    assert "<!DOCTYPE html>" in out
    assert "<p>hi</p>" in out


def test_pure_write_html_theme():
    out = D.write_html("<p>hi</p>", D.ConvertOptions(theme="dark")).decode()
    assert "#0d1117" in out


def test_pure_write_md():
    out = D.write_md("<h1>Title</h1><p>Body</p>").decode()
    assert "# Title" in out
    assert "Body" in out


def test_pure_write_txt():
    out = D.write_txt("<h1>Title</h1><p>Hello world</p>").decode()
    assert "Title" in out
    assert "Hello world" in out


def test_pure_write_latex():
    out = D.write_latex("<h1>Hi</h1><p>50% off</p>").decode()
    assert "\\documentclass{article}" in out
    assert "\\section*{Hi}" in out
    assert "50\\%" in out


def test_pure_write_rtf():
    out = D.write_rtf("<p>Hello <strong>bold</strong></p>").decode()
    assert out.startswith("{\\rtf1")
    assert "\\b bold" in out


def test_pure_write_docx_with_table_and_list():
    html = (
        "<h1>Doc</h1><p>text</p>"
        "<ul><li>a</li><li>b</li></ul>"
        "<table><tr><th>X</th><th>Y</th></tr><tr><td>1</td><td>2</td></tr></table>"
    )
    out = D.write_docx(html)
    assert out[:2] == b"PK"


def test_pure_write_odt():
    out = D.write_odt("<h1>Title</h1><p>Body</p>")
    assert out[:2] == b"PK"


def test_pure_write_pdf():
    out = D.write_pdf("<h1>Hi</h1>", D.ConvertOptions(paper_size="Letter"))
    assert out[:4] == b"%PDF"


# --- Readers (bytes -> HTML hub) --------------------------------------------
def test_pure_read_txt():
    html = D.read_txt(b"Line one\n\nLine two")
    assert "<p>" in html
    assert "Line one" in html


def test_pure_read_md():
    html = D.read_md(b"# Title\n\n- a\n- b")
    assert "<h1>Title</h1>" in html
    assert "<li>a</li>" in html


def test_pure_read_docx_round_trip():
    docx = D.write_docx("<h1>Heading</h1><p>Body text</p>")
    html = D.read_docx(docx)
    assert "Heading" in html
    assert "Body text" in html


def test_pure_read_odt_round_trip():
    odt = D.write_odt("<h1>Heading</h1><p>Body</p>")
    html = D.read_odt(odt)
    assert "Heading" in html


def test_pure_read_rtf_round_trip():
    rtf = D.write_rtf("<p>Just some text</p>")
    html = D.read_rtf(rtf)
    assert "Just some text" in html


def test_pure_read_pdf_text():
    pdf = D.write_pdf("<p>Extractable text here</p>")
    html = D.read_pdf(pdf)
    assert "Extractable text here" in html


# --- Sanitizer --------------------------------------------------------------
def test_pure_sanitize_strips_script():
    out = D.sanitize_html("<h1>ok</h1><script>bad()</script>")
    assert "<script" not in out
    assert "ok" in out
