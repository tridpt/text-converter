"""FastAPI application exposing the text format converter."""

from __future__ import annotations

import io
import ipaddress
import socket
import time
import zipfile
from pathlib import Path
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from .config import settings
from .converters import (
    ConversionError,
    ConvertOptions,
    convert,
    detect_format,
    list_formats,
    read_as_document_html,
    render_document,
)
from .converters.registry import get_spec, support_matrix

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE = BASE_DIR / "templates" / "index.html"
MATRIX_TEMPLATE = BASE_DIR / "templates" / "matrix.html"

app = FastAPI(title="Text Format Converter", version="0.3.0")

# Endpoints that perform (potentially expensive) conversions.
_PROTECTED_PATHS = {"/api/convert", "/api/convert-url"}
# In-memory per-IP rate-limit state: ip -> (minute_window, count).
# Note: not shared across processes and resets on restart.
_rate_state: dict[str, tuple[int, int]] = {}


@app.middleware("http")
async def gatekeeper(request: Request, call_next):
    """Enforce upload size limit, optional API key, and per-IP rate limiting."""
    if request.method == "POST":
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > settings.max_upload_bytes:
            return JSONResponse(
                status_code=413,
                content={
                    "detail": f"Upload too large. Maximum is {settings.max_upload_mb} MB."
                },
            )

        if request.url.path in _PROTECTED_PATHS:
            if settings.api_key and request.headers.get("x-api-key") != settings.api_key:
                return JSONResponse(
                    status_code=401, content={"detail": "Invalid or missing API key."}
                )

            limit = settings.rate_limit_per_minute
            if limit > 0:
                ip = request.client.host if request.client else "unknown"
                window = int(time.time() // 60)
                prev = _rate_state.get(ip)
                count = prev[1] + 1 if prev and prev[0] == window else 1
                _rate_state[ip] = (window, count)
                if count > limit:
                    return JSONResponse(
                        status_code=429,
                        content={"detail": "Rate limit exceeded. Try again later."},
                        headers={"Retry-After": "60"},
                    )

    return await call_next(request)


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


@app.get("/health")
def health() -> dict:
    """Lightweight health check for load balancers / platform probes."""
    from .converters import pandoc_ext

    return {"status": "ok", "pandoc": pandoc_ext.PANDOC_AVAILABLE}


@app.get("/api/formats")
def formats() -> dict:
    return {"formats": list_formats()}


@app.get("/api/matrix")
def matrix() -> dict:
    return support_matrix()


@app.get("/matrix", response_class=HTMLResponse)
def matrix_page() -> str:
    return MATRIX_TEMPLATE.read_text(encoding="utf-8")


# --- Helpers ----------------------------------------------------------------
def _build_options(paper_size: str, toc: bool, theme: str) -> ConvertOptions:
    return ConvertOptions(paper_size=paper_size, toc=toc, theme=theme)


def _resolve_source(source: str, filename: str) -> str:
    """Return the source format, auto-detecting from the filename if requested."""
    if source and source != "auto":
        return source
    try:
        return detect_format(filename)
    except ConversionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _guard(func, *args):
    try:
        return func(*args)
    except ConversionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - surface converter errors cleanly
        raise HTTPException(status_code=500, detail=f"Conversion failed: {exc}") from exc


def _stream(result: bytes, filename: str, mime: str) -> StreamingResponse:
    return StreamingResponse(
        io.BytesIO(result),
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# --- File conversion --------------------------------------------------------
@app.post("/api/convert")
async def api_convert(
    files: list[UploadFile] = File(...),
    source: str = Form("auto"),
    target: str = Form(...),
    paper_size: str = Form("A4"),
    toc: bool = Form(False),
    theme: str = Form("default"),
    merge: bool = Form(False),
) -> StreamingResponse:
    files = [f for f in files if f.filename]
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    spec = get_spec(target)
    options = _build_options(paper_size, toc, theme)

    # Merge: combine every input into a single document output.
    if merge and len(files) > 1:
        fragments = []
        for upload in files:
            data = await upload.read()
            if not data:
                continue
            src = _resolve_source(source, upload.filename)
            fragments.append(_guard(read_as_document_html, data, src))
        combined = '\n<div style="page-break-before:always"></div>\n'.join(fragments)
        result = _guard(render_document, combined, target, options)
        return _stream(result, f"merged{spec.extension}", spec.mime)

    # Single file -> stream directly.
    if len(files) == 1:
        data = await files[0].read()
        if not data:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        src = _resolve_source(source, files[0].filename)
        result = _guard(convert, data, src, target, options)
        stem = Path(files[0].filename or "converted").stem or "converted"
        return _stream(result, f"{stem}{spec.extension}", spec.mime)

    # Multiple files (no merge) -> zip archive.
    buf = io.BytesIO()
    used: dict[str, int] = {}
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
        for upload in files:
            data = await upload.read()
            if not data:
                continue
            src = _resolve_source(source, upload.filename)
            result = _guard(convert, data, src, target, options)
            stem = Path(upload.filename or "converted").stem or "converted"
            name = f"{stem}{spec.extension}"
            if name in used:
                used[name] += 1
                name = f"{stem}_{used[name]}{spec.extension}"
            else:
                used[name] = 0
            archive.writestr(name, result)

    buf.seek(0)
    return _stream(buf.getvalue(), "converted.zip", "application/zip")


# --- URL conversion ---------------------------------------------------------
def _validate_public_url(raw_url: str) -> None:
    """Block non-http(s) schemes and private/internal addresses (SSRF guard)."""
    parsed = urlparse(raw_url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Only http/https URLs are allowed.")
    host = parsed.hostname
    if not host:
        raise HTTPException(status_code=400, detail="Invalid URL.")
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise HTTPException(status_code=400, detail="Could not resolve host.") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise HTTPException(
                status_code=400,
                detail="Refusing to fetch a private or internal address.",
            )


@app.post("/api/convert-url")
async def api_convert_url(
    url: str = Form(...),
    target: str = Form(...),
    paper_size: str = Form("A4"),
    toc: bool = Form(False),
    theme: str = Form("default"),
) -> StreamingResponse:
    _validate_public_url(url)
    spec = get_spec(target)
    options = _build_options(paper_size, toc, theme)

    try:
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=15.0, max_redirects=5
        ) as client:
            resp = await client.get(url, headers={"User-Agent": "text-converter/0.3"})
        _validate_public_url(str(resp.url))  # re-check after redirects
        resp.raise_for_status()
    except HTTPException:
        raise
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=400, detail=f"Failed to fetch URL: {exc}"
        ) from exc

    # Only accept textual/HTML documents — reject binaries, downloads, etc.
    content_type = resp.headers.get("content-type", "").split(";")[0].strip().lower()
    allowed = {
        "text/html",
        "application/xhtml+xml",
        "text/plain",
        "text/markdown",
        "application/xml",
        "text/xml",
    }
    if content_type and content_type not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"URL returned unsupported content type: {content_type}.",
        )

    if len(resp.content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Fetched page exceeds {settings.max_upload_mb} MB.",
        )

    result = _guard(convert, resp.content, "html", target, options)

    host = urlparse(url).hostname or "webpage"
    name = f"{host.replace('.', '_')}{spec.extension}"
    return _stream(result, name, spec.mime)
