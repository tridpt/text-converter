"""Converter package: registry + format families."""

from .registry import (
    ConversionError,
    ConvertOptions,
    convert,
    detect_format,
    list_formats,
    read_as_document_html,
    render_document,
)

# Importing the family modules registers their readers/writers as a side effect.
from . import documents  # noqa: F401
from . import data  # noqa: F401

__all__ = [
    "convert",
    "list_formats",
    "ConversionError",
    "ConvertOptions",
    "detect_format",
    "read_as_document_html",
    "render_document",
]
