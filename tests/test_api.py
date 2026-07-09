"""Integration tests for the FastAPI endpoints."""

import io
import zipfile

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

client = TestClient(app)


def test_index_served():
    r = client.get("/")
    assert r.status_code == 200
    assert "Text Format Converter" in r.text


def test_formats_endpoint():
    r = client.get("/api/formats")
    assert r.status_code == 200
    names = {f["name"] for f in r.json()["formats"]}
    assert {"md", "html", "json", "csv", "xlsx"} <= names


def test_convert_single_file():
    r = client.post(
        "/api/convert",
        files={"files": ("a.md", b"# Title\n\nHello")},
        data={"source": "md", "target": "html"},
    )
    assert r.status_code == 200
    assert "<h1>Title</h1>" in r.text
    assert r.headers["content-disposition"].endswith('filename="a.html"')


def test_convert_auto_detect_source():
    r = client.post(
        "/api/convert",
        files={"files": ("note.md", b"# Auto")},
        data={"source": "auto", "target": "html"},
    )
    assert r.status_code == 200
    assert "Auto" in r.text


def test_convert_multiple_returns_zip():
    r = client.post(
        "/api/convert",
        files=[("files", ("a.md", b"# A")), ("files", ("b.md", b"# B"))],
        data={"source": "auto", "target": "html"},
    )
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/zip"
    names = zipfile.ZipFile(io.BytesIO(r.content)).namelist()
    assert set(names) == {"a.html", "b.html"}


def test_convert_merge_single_output():
    r = client.post(
        "/api/convert",
        files=[("files", ("a.md", b"# A")), ("files", ("b.md", b"# B"))],
        data={"source": "auto", "target": "html", "merge": "true"},
    )
    assert r.status_code == 200
    assert r.headers["content-disposition"].endswith('filename="merged.html"')
    assert "A" in r.text and "B" in r.text


def test_convert_with_options_toc():
    r = client.post(
        "/api/convert",
        files={"files": ("a.md", b"# One\n\n## Two")},
        data={"source": "md", "target": "html", "toc": "true"},
    )
    assert r.status_code == 200
    assert 'class="toc"' in r.text


def test_convert_empty_file_rejected():
    r = client.post(
        "/api/convert",
        files={"files": ("a.md", b"")},
        data={"source": "md", "target": "html"},
    )
    assert r.status_code == 400


def test_convert_corrupt_file_returns_400():
    r = client.post(
        "/api/convert",
        files={"files": ("a.xlsx", b"not a real xlsx")},
        data={"source": "xlsx", "target": "json"},
    )
    assert r.status_code == 400


def test_upload_size_limit(monkeypatch):
    monkeypatch.setattr(settings, "max_upload_mb", 0)
    r = client.post(
        "/api/convert",
        files={"files": ("a.md", b"# hi")},
        data={"source": "md", "target": "html"},
    )
    assert r.status_code == 413


# --- URL endpoint SSRF guard ------------------------------------------------
def test_convert_url_rejects_loopback():
    r = client.post(
        "/api/convert-url",
        data={"url": "http://127.0.0.1:8000/secret", "target": "md"},
    )
    assert r.status_code == 400


def test_convert_url_rejects_non_http_scheme():
    r = client.post(
        "/api/convert-url",
        data={"url": "file:///etc/passwd", "target": "md"},
    )
    assert r.status_code == 400
