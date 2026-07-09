"""Converter package: registry + format families."""

from .registry import convert, list_formats, ConversionError

# Importing the family modules registers their readers/writers as a side effect.
from . import documents  # noqa: F401
from . import data  # noqa: F401

__all__ = ["convert", "list_formats", "ConversionError"]
