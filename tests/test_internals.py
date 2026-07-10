"""Unit tests for internal helpers (pandoc availability, media inlining)."""

import base64
import io

from PIL import Image

from app.config import settings
from app.converters import pandoc_ext


def _png() -> bytes:
    img = Image.new("RGB", (4, 4), (10, 20, 30))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_pandoc_available_respects_use_pandoc_flag(monkeypatch):
    monkeypatch.setattr(settings, "use_pandoc", False)
    assert pandoc_ext._pandoc_available() is False


def test_pandoc_available_handles_missing_binary(monkeypatch):
    monkeypatch.setattr(settings, "use_pandoc", True)
    import pypandoc

    def boom():
        raise OSError("pandoc not found")

    monkeypatch.setattr(pypandoc, "get_pandoc_path", boom)
    assert pandoc_ext._pandoc_available() is False


def test_inline_media_inlines_local_and_skips_others(tmp_path):
    media = tmp_path / "media"
    media.mkdir()
    (media / "pic.png").write_bytes(_png())

    existing_uri = "data:image/png;base64," + base64.b64encode(_png()).decode()
    html = (
        '<img src="media/pic.png">'  # local file -> should be inlined
        f'<img src="{existing_uri}">'  # already a data URI -> untouched
        '<img src="missing.png">'  # not found -> left as-is
    )
    out = pandoc_ext._inline_media(html, str(tmp_path), str(media))
    assert out.count("data:image/png;base64,") == 2  # one inlined + one kept
    assert 'src="missing.png"' in out
