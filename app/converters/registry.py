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

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


class ConversionError(Exception):
    """Raised when a conversion cannot be performed."""


@dataclass(frozen=True)
class FormatSpec:
    name: str  # canonical format id, e.g. "md"
    family: str  # "document" or "data"
    label: str  # human friendly name
    extension: str  # default file extension (with dot)
    mime: str  # mime type for downloads
    binary: bool  # True if the output is binary (e.g. pdf, docx)


@dataclass
class ConvertOptions:
    """User-selectable options that influence how output is rendered."""

    paper_size: str = "A4"  # A4, Letter, Legal, A3, A5 (PDF only)
    toc: bool = False  # prepend a table of contents (documents)
    theme: str = "default"  # CSS theme for HTML/PDF output


# Extra file-extension aliases mapped to canonical format names.
_EXTENSION_ALIASES: dict[str, str] = {
    ".yml": "yaml",
    ".htm": "html",
    ".markdown": "md",
    ".mdown": "md",
    ".tex": "latex",
    ".text": "txt",
    ".asciidoc": "asciidoc",
    ".adoc": "asciidoc",
}


# Registries -----------------------------------------------------------------
_FORMATS: dict[str, FormatSpec] = {}
_READERS: dict[str, Callable[[bytes], object]] = {}
_WRITERS: dict[str, Callable[[object], bytes]] = {}
# Bridge functions convert a source family's hub into a target family's hub,
# keyed by (source_family, target_family).
_BRIDGES: dict[tuple[str, str], Callable[[object], object]] = {}
# Optional transform applied to a document (HTML) hub, e.g. table of contents.
_TOC_TRANSFORMER: Callable[[str], str] | None = None
# Optional HTML sanitizer applied to every document-family output.
_HTML_SANITIZER: Callable[[str], str] | None = None


def register_format(spec: FormatSpec) -> None:
    _FORMATS[spec.name] = spec


def set_toc_transformer(func: Callable[[str], str]) -> None:
    """Register the function that injects a table of contents into HTML."""
    global _TOC_TRANSFORMER
    _TOC_TRANSFORMER = func


def set_html_sanitizer(func: Callable[[str], str]) -> None:
    """Register the function that strips active content from HTML output."""
    global _HTML_SANITIZER
    _HTML_SANITIZER = func


def detect_format(filename: str) -> str:
    """Guess the canonical format from a file name's extension."""
    ext = Path(filename or "").suffix.lower()
    if not ext:
        raise ConversionError(f"Cannot detect format: {filename!r} has no extension.")
    if ext in _EXTENSION_ALIASES:
        return _EXTENSION_ALIASES[ext]
    for spec in _FORMATS.values():
        if spec.extension.lower() == ext:
            return spec.name
    raise ConversionError(f"Unsupported file extension: {ext!r}")


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


def can_convert(source: str, target: str) -> bool:
    """Whether a conversion from ``source`` to ``target`` is supported."""
    if source not in _READERS or target not in _WRITERS:
        return False
    src, tgt = _FORMATS[source], _FORMATS[target]
    if src.family == tgt.family:
        return True
    return (src.family, tgt.family) in _BRIDGES


def support_matrix() -> dict:
    """Return the full source x target support matrix for display."""
    sources = sorted(
        (s for s in _FORMATS.values() if s.name in _READERS),
        key=lambda s: (s.family, s.name),
    )
    targets = sorted(
        (t for t in _FORMATS.values() if t.name in _WRITERS),
        key=lambda t: (t.family, t.name),
    )
    return {
        "sources": [
            {"name": s.name, "label": s.label, "family": s.family} for s in sources
        ],
        "targets": [
            {"name": t.name, "label": t.label, "family": t.family} for t in targets
        ],
        "pairs": {
            s.name: {t.name: can_convert(s.name, t.name) for t in targets}
            for s in sources
        },
    }


def _apply_document_transforms(html: str, options: ConvertOptions) -> str:
    if _HTML_SANITIZER is not None:
        html = _HTML_SANITIZER(html)
    if options.toc and _TOC_TRANSFORMER is not None:
        html = _TOC_TRANSFORMER(html)
    return html


def _read(source: str, data: bytes) -> object:
    """Run a reader, turning unexpected parse failures into ConversionError."""
    try:
        return _READERS[source](data)
    except ConversionError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise ConversionError(
            f"Could not read the {source} file — it may be corrupt or in an "
            f"unexpected format ({exc})."
        ) from exc


def convert(
    data: bytes, source: str, target: str, options: ConvertOptions | None = None
) -> bytes:
    """Convert ``data`` from ``source`` format to ``target`` format."""
    options = options or ConvertOptions()
    src = get_spec(source)
    tgt = get_spec(target)

    if source not in _READERS:
        raise ConversionError(f"Cannot read from format: {source!r}")
    if target not in _WRITERS:
        raise ConversionError(f"Cannot write to format: {target!r}")

    hub = _read(source, data)

    if src.family != tgt.family:
        bridge = _BRIDGES.get((src.family, tgt.family))
        if bridge is None:
            raise ConversionError(
                f"Cannot convert from {src.family!r} ({source}) to "
                f"{tgt.family!r} ({target}). No bridge is available for this "
                "direction."
            )
        hub = bridge(hub)

    if tgt.family == "document":
        hub = _apply_document_transforms(hub, options)

    return _WRITERS[target](hub, options)


def read_as_document_html(data: bytes, source: str) -> str:
    """Read a source file and return its document-family HTML hub.

    Bridges data formats into HTML when needed. Used for merging and URL flows.
    """
    spec = get_spec(source)
    if source not in _READERS:
        raise ConversionError(f"Cannot read from format: {source!r}")
    hub = _read(source, data)
    if spec.family == "document":
        return hub
    bridge = _BRIDGES.get((spec.family, "document"))
    if bridge is None:
        raise ConversionError(f"Cannot treat {source!r} as a document.")
    return bridge(hub)


def render_document(
    html: str, target: str, options: ConvertOptions | None = None
) -> bytes:
    """Write an HTML document hub to ``target`` (must be a document format)."""
    options = options or ConvertOptions()
    tgt = get_spec(target)
    if tgt.family != "document":
        raise ConversionError(
            f"Merging/URL output is only supported for document formats, not {target!r}."
        )
    if target not in _WRITERS:
        raise ConversionError(f"Cannot write to format: {target!r}")
    html = _apply_document_transforms(html, options)
    return _WRITERS[target](html, options)
