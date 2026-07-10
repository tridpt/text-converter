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


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "pandoc" in body


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


def test_convert_url_rejects_missing_host():
    r = client.post("/api/convert-url", data={"url": "http://", "target": "md"})
    assert r.status_code == 400


def test_convert_url_rejects_unresolvable_host():
    # .invalid is reserved and never resolves (RFC 2606).
    r = client.post(
        "/api/convert-url",
        data={"url": "http://nope.invalid/", "target": "md"},
    )
    assert r.status_code == 400


# --- URL fetch with a mocked HTTP client ------------------------------------
class _FakeResp:
    def __init__(self, content: bytes, url: str, ctype: str = "text/html"):
        self.content = content
        self.url = url
        self.headers = {"content-type": ctype}

    def raise_for_status(self):
        return None


class _FakeClient:
    def __init__(self, resp):
        self._resp = resp

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, url, headers=None):
        return self._resp


def _patch_client(monkeypatch, resp):
    import app.main as main_mod

    monkeypatch.setattr(main_mod.httpx, "AsyncClient", lambda *a, **k: _FakeClient(resp))


def test_convert_url_success(monkeypatch):
    _patch_client(
        monkeypatch, _FakeResp(b"<h1>Web Page</h1><p>Body</p>", "http://example.com")
    )
    r = client.post(
        "/api/convert-url", data={"url": "http://example.com", "target": "md"}
    )
    assert r.status_code == 200
    assert "Web Page" in r.text
    assert r.headers["content-disposition"].endswith('filename="example_com.md"')


def test_convert_url_rejects_binary_content_type(monkeypatch):
    _patch_client(
        monkeypatch,
        _FakeResp(
            b"\x00\x01binary", "http://example.com", ctype="application/octet-stream"
        ),
    )
    r = client.post(
        "/api/convert-url", data={"url": "http://example.com", "target": "md"}
    )
    assert r.status_code == 400


def test_convert_url_rejects_oversized_fetch(monkeypatch):
    monkeypatch.setattr(settings, "max_upload_mb", 1)
    big = b"<p>" + b"x" * (2 * 1024 * 1024) + b"</p>"
    _patch_client(monkeypatch, _FakeResp(big, "http://example.com"))
    r = client.post(
        "/api/convert-url", data={"url": "http://example.com", "target": "md"}
    )
    assert r.status_code == 413


# --- File endpoint edge cases -----------------------------------------------
def test_convert_auto_detect_unknown_extension_rejected():
    r = client.post(
        "/api/convert",
        files={"files": ("mystery.zzz", b"data")},
        data={"source": "auto", "target": "html"},
    )
    assert r.status_code == 400


def test_convert_no_valid_files_rejected():
    # An empty filename is rejected as a client error (FastAPI validation or
    # the endpoint's own "no files" guard).
    r = client.post(
        "/api/convert",
        files=[("files", ("", b"ignored"))],
        data={"source": "md", "target": "html"},
    )
    assert r.status_code in (400, 422)


def test_convert_merge_skips_empty_file():
    r = client.post(
        "/api/convert",
        files=[("files", ("a.md", b"# A")), ("files", ("b.md", b""))],
        data={"source": "auto", "target": "html", "merge": "true"},
    )
    assert r.status_code == 200
    assert "A" in r.text


def test_convert_zip_deduplicates_names():
    r = client.post(
        "/api/convert",
        files=[("files", ("a.md", b"# A")), ("files", ("a.md", b"# B"))],
        data={"source": "auto", "target": "html"},
    )
    assert r.status_code == 200
    names = zipfile.ZipFile(io.BytesIO(r.content)).namelist()
    assert "a.html" in names
    assert "a_1.html" in names


# --- Format matrix ----------------------------------------------------------
def test_matrix_endpoint():
    m = client.get("/api/matrix").json()
    assert "sources" in m and "targets" in m and "pairs" in m
    # Same-family conversion is supported.
    assert m["pairs"]["md"]["html"] is True
    # Cross-family data -> document is supported (bridge).
    assert m["pairs"]["json"]["pdf"] is True
    # Document -> data is not.
    assert m["pairs"]["md"].get("json", False) is False


def test_matrix_page_served():
    r = client.get("/matrix")
    assert r.status_code == 200
    assert "Ma trận" in r.text


# --- API key & rate limiting ------------------------------------------------
def test_api_key_required_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "api_key", "secret123")
    # Missing key -> 401
    r = client.post(
        "/api/convert",
        files={"files": ("a.md", b"# Hi")},
        data={"source": "md", "target": "html"},
    )
    assert r.status_code == 401
    # Correct key -> 200
    r2 = client.post(
        "/api/convert",
        files={"files": ("a.md", b"# Hi")},
        data={"source": "md", "target": "html"},
        headers={"X-API-Key": "secret123"},
    )
    assert r2.status_code == 200


def test_rate_limit(monkeypatch):
    import app.main as main_mod

    monkeypatch.setattr(settings, "rate_limit_per_minute", 2)
    main_mod._rate_state.clear()
    ok = 0
    limited = 0
    for _ in range(4):
        r = client.post(
            "/api/convert",
            files={"files": ("a.md", b"# Hi")},
            data={"source": "md", "target": "html"},
        )
        if r.status_code == 200:
            ok += 1
        elif r.status_code == 429:
            limited += 1
    assert ok == 2
    assert limited == 2
