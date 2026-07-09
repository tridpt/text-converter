"""Converter registry.

Uses a hub-and-spoke design. Each format belongs to a *family*, and every
family shares a single intermediate representation (a "hub"):

- ``document`` family  -> hub is an HTML string
- ``data`` family      -> hub is a native Python object (dict/list/...)

For each format we only need a *reader* (raw bytes -> hub) and a *writer*
(hub -> raw bytes). Any source format can then convert to any target format
within the same family without writing an N x N matrix of converters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict


class ConversionError(Exception):
    """Raised when a conversion cannot be performed."""


@dataclass(frozen=True)
class FormatSpec:
    name: str          # canonical format id, e.g. "md"
    family: str        # "document" or "data"
    label: str         # human friendly name
    extension: str     # default file extension (with dot)
    mime: str          # mime type for downloads
    binary: bool       # True if the output is binary (e.g. pdf, docx)


# Registries -----------------------------------------------------------------
_FORMATS: Dict[str, FormatSpec] = {}
_READERS: Dict[str, Callable[[bytes], object]] = {}
_WRITERS: Dict[str, Callable[[object], bytes]] = {}
# Bridge functions convert a source family's hub into a target family's hub,
# keyed by (source_family, target_family).
_BRIDGES: Dict[tuple[str, str], Callable[[object], object]] = {}


def register_format(spec: FormatSpec) -> None:
    _FORMATS[spec.name] = spec


def register_bridge(
    source_family: str, target_family: str, func: Callable[[object], object]
) -> None:
    """Register a converter between two family hubs (e.g. data -> document)."""
    _BRIDGES[(source_family, target_family)] = func


def reader(fmt: str) -> Callable:
    """Decorator to register a reader for ``fmt`` (bytes -> hub)."""

    def deco(func: Callable[[bytes], object]) -> Callable:
        _READERS[fmt] = func
        return func

    return deco


def writer(fmt: str) -> Callable:
    """Decorator to register a writer for ``fmt`` (hub -> bytes)."""

    def deco(func: Callable[[object], bytes]) -> Callable:
        _WRITERS[fmt] = func
        return func

    return deco


# Public API -----------------------------------------------------------------
def list_formats() -> list[dict]:
    """Return the catalogue of supported formats for the UI/API."""
    out = []
    for spec in sorted(_FORMATS.values(), key=lambda s: (s.family, s.name)):
        out.append(
            {
                "name": spec.name,
                "family": spec.family,
                "label": spec.label,
                "extension": spec.extension,
                "readable": spec.name in _READERS,
                "writable": spec.name in _WRITERS,
            }
        )
    return out


def get_spec(fmt: str) -> FormatSpec:
    spec = _FORMATS.get(fmt)
    if spec is None:
        raise ConversionError(f"Unknown format: {fmt!r}")
    return spec


def convert(data: bytes, source: str, target: str) -> bytes:
    """Convert ``data`` from ``source`` format to ``target`` format."""
    src = get_spec(source)
    tgt = get_spec(target)

    if source not in _READERS:
        raise ConversionError(f"Cannot read from format: {source!r}")
    if target not in _WRITERS:
        raise ConversionError(f"Cannot write to format: {target!r}")

    hub = _READERS[source](data)

    if src.family != tgt.family:
        bridge = _BRIDGES.get((src.family, tgt.family))
        if bridge is None:
            raise ConversionError(
                f"Cannot convert from {src.family!r} ({source}) to "
                f"{tgt.family!r} ({target}). No bridge is available for this "
                "direction."
            )
        hub = bridge(hub)

    return _WRITERS[target](hub)
