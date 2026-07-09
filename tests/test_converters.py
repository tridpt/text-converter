"""Round-trip and basic conversion tests for the converter registry."""

import json

import pytest

from app.converters import convert, list_formats, ConversionError


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
    out = convert(b"<h1>Title</h1><p>Body with 50% off</p>", "html", "latex").decode()
    assert "\\documentclass{article}" in out
    assert "\\section*{Title}" in out
    assert "50\\%" in out  # special char escaped


def test_html_to_rtf():
    out = convert(b"<p>Hello <strong>bold</strong></p>", "html", "rtf").decode()
    assert out.startswith("{\\rtf1")
    assert "\\b bold" in out


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


# --- Error handling ---------------------------------------------------------
def test_document_to_data_rejected():
    # No bridge exists in the document -> data direction.
    with pytest.raises(ConversionError):
        convert(b"# hi", "md", "json")


def test_unknown_format_rejected():
    with pytest.raises(ConversionError):
        convert(b"hi", "txt", "nope")
