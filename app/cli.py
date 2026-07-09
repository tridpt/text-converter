"""Command-line interface for the text converter.

Reuses the same conversion engine as the web app.

Examples:
    python -m app.cli report.md report.pdf
    python -m app.cli data.json data.yaml
    python -m app.cli a.md b.md c.md book.epub          # merge into one
    python -m app.cli page.tex out.docx --toc --theme github
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .converters import (
    ConversionError,
    ConvertOptions,
    convert,
    detect_format,
    read_as_document_html,
    render_document,
)

_PAGE_BREAK = '\n<div style="page-break-before:always"></div>\n'


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="text-convert",
        description="Convert between many document and data formats.",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        metavar="PATH",
        help="one or more INPUT files followed by a single OUTPUT file",
    )
    parser.add_argument(
        "-f",
        "--from",
        dest="source",
        help="source format (default: from input extension)",
    )
    parser.add_argument(
        "-t", "--to", dest="target", help="target format (default: from output extension)"
    )
    parser.add_argument("--theme", default="default", help="CSS theme for HTML/PDF")
    parser.add_argument("-p", "--paper-size", default="A4", help="PDF paper size")
    parser.add_argument("--toc", action="store_true", help="add a table of contents")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if len(args.paths) < 2:
        print("error: need at least one INPUT and one OUTPUT path.", file=sys.stderr)
        return 2

    *inputs, output = args.paths
    options = ConvertOptions(paper_size=args.paper_size, toc=args.toc, theme=args.theme)

    try:
        target = args.target or detect_format(output)
        if len(inputs) > 1:
            fragments = []
            for path in inputs:
                data = Path(path).read_bytes()
                source = args.source or detect_format(path)
                fragments.append(read_as_document_html(data, source))
            result = render_document(_PAGE_BREAK.join(fragments), target, options)
        else:
            data = Path(inputs[0]).read_bytes()
            source = args.source or detect_format(inputs[0])
            result = convert(data, source, target, options)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except ConversionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    Path(output).write_bytes(result)
    print(f"Wrote {output} ({len(result)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
