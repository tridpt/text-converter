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

# Map our canonical format ids to Pandoc format names.
_PANDOC_IN = {"latex": "latex", "docx": "docx", "odt": "odt"}
_PANDOC_OUT = {
    "latex": "latex",
    "docx": "docx",
    "odt": "odt",
    "rtf": "rtf",
    "md": "gfm",  # GitHub-flavoured markdown keeps tables
}
_BINARY_OUT = {"docx", "odt"}
# Text formats that need a complete standalone document (header/preamble),
# otherwise Pandoc emits only a body fragment.
_STANDALONE_OUT = {"latex", "rtf"}


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


def _write_with_pandoc(html: str, fmt: str, binary: bool, standalone: bool) -> bytes:
    import pypandoc

    extra_args = ["--standalone"] if standalone else []

    if binary:
        suffix = "." + fmt
        fd, out_path = tempfile.mkstemp(suffix=suffix, prefix="tc_pandoc_")
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
if PANDOC_AVAILABLE:

    @reader("latex")
    def read_latex(data: bytes) -> str:
        return _read_with_pandoc(data, "latex", ".tex")

    @reader("docx")
    def read_docx_pandoc(data: bytes) -> str:
        return _read_with_pandoc(data, "docx", ".docx")

    @reader("odt")
    def read_odt_pandoc(data: bytes) -> str:
        return _read_with_pandoc(data, "odt", ".odt")

    def _make_writer(fmt: str, pandoc_fmt: str, binary: bool, standalone: bool):
        @writer(fmt)
        def _w(html: str, options: ConvertOptions | None = None) -> bytes:
            return _write_with_pandoc(html, pandoc_fmt, binary, standalone)

        return _w

    for _name, _pfmt in _PANDOC_OUT.items():
        _make_writer(
            _name, _pfmt, _name in _BINARY_OUT, _name in _STANDALONE_OUT
        )
