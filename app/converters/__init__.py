"""Converter package: registry + format families."""

# Importing the family modules registers their readers/writers as a side effect.
# Pandoc overrides selected readers/writers when the binary is available.
# Imported last so its registrations take precedence over the pure-Python ones.
from . import (
    data,  # noqa: F401
    documents,  # noqa: F401
    pandoc_ext,  # noqa: F401,E402
)
from .registry import (
    ConversionError,
    ConvertOptions,
    convert,
    detect_format,
    list_formats,
    read_as_document_html,
    render_document,
)

__all__ = [
    "convert",
    "list_formats",
    "ConversionError",
    "ConvertOptions",
    "detect_format",
    "read_as_document_html",
    "render_document",
]
