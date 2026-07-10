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


# --- Structured logging -----------------------------------------------------
def test_json_formatter_outputs_valid_json():
    import json
    import logging

    from app.logging_config import JsonFormatter

    rec = logging.LogRecord("t", logging.INFO, __file__, 1, "hello", None, None)
    rec.extra_fields = {"path": "/x", "status": 200}
    payload = json.loads(JsonFormatter().format(rec))
    assert payload["message"] == "hello"
    assert payload["path"] == "/x"
    assert payload["status"] == 200
    assert payload["level"] == "INFO"


def test_json_formatter_includes_exception():
    import json
    import logging

    from app.logging_config import JsonFormatter

    try:
        raise ValueError("boom")
    except ValueError:
        import sys

        rec = logging.LogRecord(
            "t", logging.ERROR, __file__, 1, "failed", None, sys.exc_info()
        )
    payload = json.loads(JsonFormatter().format(rec))
    assert "boom" in payload["exc"]


def test_configure_logging_and_log_helper():
    import logging

    from app.logging_config import configure_logging, log

    logger = configure_logging()
    log(logger, logging.INFO, "test-event", key="value")  # should not raise
    assert logger.name == "text_converter"
