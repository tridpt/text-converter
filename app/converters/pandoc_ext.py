"""Optional Pandoc-powered converters for higher-fidelity conversions.

When the ``pandoc`` binary is available (and not disabled via ``USE_PANDOC=0``),
this module overrides selected document readers/writers with Pandoc-based
implementations that preserve tables, images and math far better than the
pure-Python fallbacks. It also unlocks *reading* LaTeX.

If Pandoc is not present, this module registers nothing and the pure-Python
converters remain in effect.
"""

from __future__ import annotations

import base64
import mimetypes
import os
import shutil
import tempfile

from bs4 import BeautifulSoup

from ..config import settings
from .registry import ConvertOptions, reader, writer

_REVEALJS_URL = "https://cdn.jsdelivr.net/npm/reveal.js@4"

# Readers: our format id -> (pandoc input format, temp file extension).
_READ_CONFIG = {
    "latex": ("latex", ".tex"),
    "docx": ("docx", ".docx"),
    "odt": ("odt", ".odt"),
    "epub": ("epub", ".epub"),
}

# Writers: our format id -> (pandoc output format, is_binary, extra pandoc args).
_WRITE_CONFIG = {
    "latex": ("latex", False, ["--standalone"]),
    "docx": ("docx", True, []),
    "odt": ("odt", True, []),
    "rtf": ("rtf", False, ["--standalone"]),
    "md": ("gfm", False, []),  # GitHub-flavoured markdown keeps tables
    "epub": ("epub3", True, ["--standalone"]),
    "revealjs": (
        "revealjs",
        False,
        ["--standalone", "-V", f"revealjs-url={_REVEALJS_URL}"],
    ),
    "pptx": ("pptx", True, []),
}


def _pandoc_available() -> bool:
    if not settings.use_pandoc:
        return False
    try:
        import pypandoc

        pypandoc.get_pandoc_path()
        return True
    except Exception:  # noqa: BLE001 - binary missing or import failure
        return False


PANDOC_AVAILABLE = _pandoc_available()


def _inline_media(html: str, base_dir: str, media_dir: str) -> str:
    """Replace <img> file references produced by --extract-media with data URIs."""
    soup = BeautifulSoup(html, "html.parser")
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if not src or src.startswith("data:"):
            continue
        candidates = [
            src,
            os.path.join(base_dir, src),
            os.path.join(media_dir, os.path.basename(src)),
        ]
        path = next((p for p in candidates if os.path.isfile(p)), None)
        if path is None:
            continue
        try:
            with open(path, "rb") as fh:
                raw = fh.read()
        except OSError:
            continue
        mime = mimetypes.guess_type(path)[0] or "image/png"
        encoded = base64.b64encode(raw).decode("ascii")
        img["src"] = f"data:{mime};base64,{encoded}"
    return str(soup)


def _read_with_pandoc(data: bytes, fmt: str, ext: str) -> str:
    import pypandoc

    tmpdir = tempfile.mkdtemp(prefix="tc_pandoc_")
    media_dir = os.path.join(tmpdir, "media")
    in_path = os.path.join(tmpdir, f"input{ext}")
    try:
        with open(in_path, "wb") as fh:
            fh.write(data)
        html = pypandoc.convert_file(
            in_path,
            "html",
            format=fmt,
            extra_args=["--extract-media", media_dir, "--mathml"],
        )
        return _inline_media(html, tmpdir, media_dir)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def _write_with_pandoc(html: str, fmt: str, binary: bool, extra_args: list[str]) -> bytes:
    import pypandoc

    if binary:
        fd, out_path = tempfile.mkstemp(suffix=f".{fmt}", prefix="tc_pandoc_")
        os.close(fd)
        try:
            pypandoc.convert_text(
                html, fmt, format="html", outputfile=out_path, extra_args=extra_args
            )
            with open(out_path, "rb") as fh:
                return fh.read()
        finally:
            try:
                os.remove(out_path)
            except OSError:
                pass
    text = pypandoc.convert_text(html, fmt, format="html", extra_args=extra_args)
    return text.encode("utf-8")


# --- Registration (only when Pandoc is usable) ------------------------------
def _make_reader(fmt: str, pandoc_fmt: str, ext: str):
    @reader(fmt)
    def _r(data: bytes) -> str:
        return _read_with_pandoc(data, pandoc_fmt, ext)

    return _r


def _make_writer(fmt: str, pandoc_fmt: str, binary: bool, extra_args: list[str]):
    @writer(fmt)
    def _w(html: str, options: ConvertOptions | None = None) -> bytes:
        return _write_with_pandoc(html, pandoc_fmt, binary, extra_args)

    return _w


if PANDOC_AVAILABLE:
    for _name, (_pfmt, _ext) in _READ_CONFIG.items():
        _make_reader(_name, _pfmt, _ext)
    for _name, (_pfmt, _binary, _args) in _WRITE_CONFIG.items():
        _make_writer(_name, _pfmt, _binary, _args)
