"""FastAPI application exposing the text format converter."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse

from .converters import ConversionError, convert, list_formats
from .converters.registry import get_spec

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE = BASE_DIR / "templates" / "index.html"

app = FastAPI(title="Text Format Converter", version="0.1.0")


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


@app.get("/api/formats")
def formats() -> dict:
    return {"formats": list_formats()}


def _convert_one(data: bytes, source: str, target: str) -> bytes:
    try:
        return convert(data, source, target)
    except ConversionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - surface converter errors cleanly
        raise HTTPException(status_code=500, detail=f"Conversion failed: {exc}") from exc


@app.post("/api/convert")
async def api_convert(
    files: list[UploadFile] = File(...),
    source: str = Form(...),
    target: str = Form(...),
) -> StreamingResponse:
    files = [f for f in files if f.filename]
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    spec = get_spec(target)

    # Single file -> stream the converted file directly.
    if len(files) == 1:
        data = await files[0].read()
        if not data:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        result = _convert_one(data, source, target)
        stem = Path(files[0].filename or "converted").stem or "converted"
        filename = f"{stem}{spec.extension}"
        return StreamingResponse(
            io.BytesIO(result),
            media_type=spec.mime,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    # Multiple files -> bundle the results into a zip archive.
    buf = io.BytesIO()
    used: dict[str, int] = {}
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
        for upload in files:
            data = await upload.read()
            if not data:
                continue
            result = _convert_one(data, source, target)
            stem = Path(upload.filename or "converted").stem or "converted"
            name = f"{stem}{spec.extension}"
            # Avoid clobbering duplicate output names.
            if name in used:
                used[name] += 1
                name = f"{stem}_{used[name]}{spec.extension}"
            else:
                used[name] = 0
            archive.writestr(name, result)

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="converted.zip"'},
    )
