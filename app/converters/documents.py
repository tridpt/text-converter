"""Document family converters. Hub representation: an HTML string.

Supported formats: txt, md, html, docx, pdf.
"""

from __future__ import annotations

import base64
import html as html_lib
import io

import markdown as md_lib
import mammoth
import pdfplumber
from bs4 import BeautifulSoup, NavigableString, Tag
from docx import Document
from docx.shared import Inches
from markdownify import markdownify
from striprtf.striprtf import rtf_to_text
from xhtml2pdf import pisa

from odf.opendocument import OpenDocumentText, load as odf_load
from odf import text as odf_text
from odf.teletype import extractText

from .registry import FormatSpec, ConversionError, reader, register_format, writer

# --- Format catalogue -------------------------------------------------------
register_format(FormatSpec("txt", "document", "Plain text", ".txt", "text/plain", False))
register_format(FormatSpec("md", "document", "Markdown", ".md", "text/markdown", False))
register_format(FormatSpec("html", "document", "HTML", ".html", "text/html", False))
register_format(
    FormatSpec(
        "docx",
        "document",
        "Word (DOCX)",
        ".docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        True,
    )
)
register_format(FormatSpec("pdf", "document", "PDF", ".pdf", "application/pdf", True))
register_format(FormatSpec("rtf", "document", "Rich Text (RTF)", ".rtf", "application/rtf", False))
register_format(
    FormatSpec(
        "odt",
        "document",
        "OpenDocument (ODT)",
        ".odt",
        "application/vnd.oasis.opendocument.text",
        True,
    )
)
register_format(FormatSpec("latex", "document", "LaTeX", ".tex", "application/x-tex", False))


# --- Helpers ----------------------------------------------------------------
_BLOCK_TAGS = {"p", "div", "section", "article", "br", "li", "tr", "pre", "blockquote"}
_HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}


def _decode(data: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _wrap_html_document(body_html: str) -> str:
    """Wrap fragment HTML in a minimal, well-formed HTML document."""
    return (
        "<!DOCTYPE html>\n<html>\n<head>\n"
        '<meta charset="utf-8">\n'
        "<style>body{font-family:sans-serif;line-height:1.5;"
        "max-width:800px;margin:2rem auto;padding:0 1rem;}"
        "pre{background:#f4f4f4;padding:1rem;overflow:auto;}"
        "</style>\n</head>\n<body>\n" + body_html + "\n</body>\n</html>\n"
    )


# --- Readers (bytes -> HTML string) -----------------------------------------
@reader("txt")
def read_txt(data: bytes) -> str:
    text = _decode(data)
    paragraphs = text.split("\n\n")
    parts = []
    for para in paragraphs:
        para = para.strip("\n")
        if not para:
            continue
        escaped = html_lib.escape(para).replace("\n", "<br>\n")
        parts.append(f"<p>{escaped}</p>")
    return "\n".join(parts)


@reader("md")
def read_md(data: bytes) -> str:
    text = _decode(data)
    return md_lib.markdown(text, extensions=["extra", "sane_lists", "tables"])


@reader("html")
def read_html(data: bytes) -> str:
    return _decode(data)


@reader("docx")
def read_docx(data: bytes) -> str:
    # Embed images inline as base64 data URIs so they survive later conversions.
    result = mammoth.convert_to_html(
        io.BytesIO(data), convert_image=mammoth.images.data_uri
    )
    return result.value


@reader("pdf")
def read_pdf(data: bytes) -> str:
    parts = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for para in text.split("\n"):
                para = para.strip()
                if para:
                    parts.append(f"<p>{html_lib.escape(para)}</p>")
    return "\n".join(parts)


# --- Writers (HTML string -> bytes) -----------------------------------------
@writer("html")
def write_html(html: str) -> bytes:
    # Only wrap if it is a bare fragment.
    lowered = html.lower()
    if "<html" not in lowered:
        html = _wrap_html_document(html)
    return html.encode("utf-8")


@writer("md")
def write_md(html: str) -> bytes:
    md_text = markdownify(html, heading_style="ATX")
    # Collapse excessive blank lines.
    lines = [ln.rstrip() for ln in md_text.splitlines()]
    cleaned = "\n".join(lines).strip() + "\n"
    return cleaned.encode("utf-8")


@writer("txt")
def write_txt(html: str) -> bytes:
    soup = BeautifulSoup(html, "html.parser")
    for br in soup.find_all("br"):
        br.replace_with("\n")
    blocks = soup.find_all(_BLOCK_TAGS | _HEADING_TAGS)
    if blocks:
        text = "\n\n".join(b.get_text(strip=True) for b in blocks if b.get_text(strip=True))
    else:
        text = soup.get_text("\n")
    return (text.strip() + "\n").encode("utf-8")


def _data_uri_to_stream(src: str) -> io.BytesIO | None:
    """Decode a ``data:`` image URI into a byte stream, else return None."""
    if not src or not src.startswith("data:"):
        return None
    try:
        _, encoded = src.split(",", 1)
        return io.BytesIO(base64.b64decode(encoded))
    except (ValueError, base64.binascii.Error):
        return None


def _add_runs(paragraph, element: Tag) -> None:
    """Add text runs from ``element`` to a docx paragraph, keeping bold/italic."""
    for node in element.children:
        if isinstance(node, NavigableString):
            text = str(node)
            if text:
                paragraph.add_run(text)
        elif isinstance(node, Tag):
            if node.name == "br":
                paragraph.add_run().add_break()
                continue
            run = paragraph.add_run(node.get_text())
            if node.name in ("strong", "b"):
                run.bold = True
            elif node.name in ("em", "i"):
                run.italic = True
            elif node.name == "code":
                run.font.name = "Consolas"


def _add_table(doc, table_el: Tag) -> None:
    rows = table_el.find_all("tr")
    if not rows:
        return
    ncols = max(len(r.find_all(["td", "th"])) for r in rows)
    if ncols == 0:
        return
    table = doc.add_table(rows=0, cols=ncols)
    table.style = "Table Grid"
    for tr in rows:
        cells = tr.find_all(["td", "th"])
        row = table.add_row().cells
        for i, cell in enumerate(cells):
            if i < ncols:
                row[i].text = cell.get_text(strip=True)


def _walk_docx(doc, element: Tag) -> None:
    """Recursively emit docx content from block-level HTML elements."""
    for child in element.children:
        if isinstance(child, NavigableString):
            continue
        if not isinstance(child, Tag):
            continue
        name = child.name
        if name in _HEADING_TAGS:
            doc.add_heading(child.get_text(strip=True), level=int(name[1]))
        elif name == "p":
            para = doc.add_paragraph()
            _add_runs(para, child)
            img = child.find("img")
            if img:
                _emit_image(doc, img)
        elif name in ("ul", "ol"):
            style = "List Bullet" if name == "ul" else "List Number"
            for li in child.find_all("li", recursive=False):
                doc.add_paragraph(li.get_text(strip=True), style=style)
        elif name == "table":
            _add_table(doc, child)
        elif name == "pre":
            doc.add_paragraph(child.get_text()).style = "No Spacing"
        elif name == "blockquote":
            doc.add_paragraph(child.get_text(strip=True), style="Intense Quote")
        elif name == "img":
            _emit_image(doc, child)
        elif name in ("div", "section", "article", "body", "main", "header", "footer"):
            _walk_docx(doc, child)
        else:
            text = child.get_text(strip=True)
            if text:
                doc.add_paragraph(text)


def _emit_image(doc, img: Tag) -> None:
    stream = _data_uri_to_stream(img.get("src", ""))
    if stream is None:
        return
    try:
        doc.add_picture(stream, width=Inches(5))
    except Exception:  # noqa: BLE001 - unsupported/broken image, skip gracefully
        pass


@writer("docx")
def write_docx(html: str) -> bytes:
    soup = BeautifulSoup(html, "html.parser")
    doc = Document()
    root = soup.body or soup

    _walk_docx(doc, root)

    # Fallback: nothing block-level was found, dump raw text.
    if not doc.paragraphs and not doc.tables:
        for line in soup.get_text("\n").splitlines():
            if line.strip():
                doc.add_paragraph(line.strip())

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


@writer("pdf")
def write_pdf(html: str) -> bytes:
    lowered = html.lower()
    if "<html" not in lowered:
        html = _wrap_html_document(html)
    buf = io.BytesIO()
    result = pisa.CreatePDF(src=html, dest=buf, encoding="utf-8")
    if result.err:
        raise ConversionError("Failed to render PDF from HTML.")
    return buf.getvalue()


# --- RTF ---------------------------------------------------------------------
def _rtf_escape(text: str) -> str:
    out = []
    for ch in text:
        code = ord(ch)
        if ch in "\\{}":
            out.append("\\" + ch)
        elif ch == "\n":
            out.append("\\line ")
        elif code > 127:
            out.append(f"\\u{code}?")
        else:
            out.append(ch)
    return "".join(out)


def _rtf_inline(element: Tag) -> str:
    parts = []
    for node in element.children:
        if isinstance(node, NavigableString):
            parts.append(_rtf_escape(str(node)))
        elif isinstance(node, Tag):
            if node.name == "br":
                parts.append("\\line ")
            elif node.name in ("strong", "b"):
                parts.append("{\\b " + _rtf_escape(node.get_text()) + "}")
            elif node.name in ("em", "i"):
                parts.append("{\\i " + _rtf_escape(node.get_text()) + "}")
            else:
                parts.append(_rtf_escape(node.get_text()))
    return "".join(parts)


@reader("rtf")
def read_rtf(data: bytes) -> str:
    text = rtf_to_text(_decode(data))
    parts = []
    for para in text.split("\n\n"):
        para = para.strip()
        if para:
            escaped = html_lib.escape(para).replace("\n", "<br>\n")
            parts.append(f"<p>{escaped}</p>")
    return "\n".join(parts)


@writer("rtf")
def write_rtf(html: str) -> bytes:
    soup = BeautifulSoup(html, "html.parser")
    root = soup.body or soup
    body_parts = []
    for el in root.find_all(_HEADING_TAGS | {"p", "li", "pre", "blockquote"}):
        text = el.get_text(strip=True)
        if not text:
            continue
        name = el.name
        if name in _HEADING_TAGS:
            size = {1: 36, 2: 32, 3: 28, 4: 26, 5: 24, 6: 22}.get(int(name[1]), 24)
            body_parts.append(f"{{\\b\\fs{size} {_rtf_escape(text)}}}\\par")
        elif name == "li":
            body_parts.append("\\bullet\\tab " + _rtf_inline(el) + "\\par")
        elif name == "pre":
            body_parts.append("{\\f1 " + _rtf_escape(text) + "}\\par")
        elif name == "blockquote":
            body_parts.append("{\\i " + _rtf_escape(text) + "}\\par")
        else:
            body_parts.append(_rtf_inline(el) + "\\par")
    body = "\n".join(body_parts)
    doc = (
        "{\\rtf1\\ansi\\ansicpg1252\\deff0"
        "{\\fonttbl{\\f0 Calibri;}{\\f1 Consolas;}}\n" + body + "\n}"
    )
    return doc.encode("utf-8")


# --- ODT ---------------------------------------------------------------------
@reader("odt")
def read_odt(data: bytes) -> str:
    doc = odf_load(io.BytesIO(data))
    parts = []
    for el in doc.text.childNodes:
        name = getattr(el, "qname", (None, None))[1]
        if name == "h":
            try:
                level = int(el.getAttribute("outlinelevel") or 1)
            except (TypeError, ValueError):
                level = 1
            level = min(max(level, 1), 6)
            txt = extractText(el)
            if txt.strip():
                parts.append(f"<h{level}>{html_lib.escape(txt)}</h{level}>")
        elif name == "p":
            txt = extractText(el)
            if txt.strip():
                parts.append(f"<p>{html_lib.escape(txt)}</p>")
    return "\n".join(parts)


@writer("odt")
def write_odt(html: str) -> bytes:
    soup = BeautifulSoup(html, "html.parser")
    root = soup.body or soup
    doc = OpenDocumentText()
    for el in root.find_all(_HEADING_TAGS | {"p", "li", "pre", "blockquote"}):
        text = el.get_text(strip=True)
        if not text:
            continue
        if el.name in _HEADING_TAGS:
            doc.text.addElement(odf_text.H(outlinelevel=int(el.name[1]), text=text))
        elif el.name == "li":
            doc.text.addElement(odf_text.P(text="\u2022 " + text))
        else:
            doc.text.addElement(odf_text.P(text=text))
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# --- LaTeX (writer only) -----------------------------------------------------
_LATEX_SPECIAL = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def _latex_escape(text: str) -> str:
    return "".join(_LATEX_SPECIAL.get(ch, ch) for ch in text)


@writer("latex")
def write_latex(html: str) -> bytes:
    soup = BeautifulSoup(html, "html.parser")
    root = soup.body or soup
    body_parts = []
    section_cmds = {1: "section", 2: "subsection", 3: "subsubsection"}

    for el in root.find_all(_HEADING_TAGS | {"p", "ul", "ol", "pre", "blockquote"}):
        name = el.name
        if name in _HEADING_TAGS:
            level = int(name[1])
            cmd = section_cmds.get(level, "paragraph")
            body_parts.append(f"\\{cmd}*{{{_latex_escape(el.get_text(strip=True))}}}")
        elif name in ("ul", "ol"):
            env = "itemize" if name == "ul" else "enumerate"
            items = [
                f"  \\item {_latex_escape(li.get_text(strip=True))}"
                for li in el.find_all("li", recursive=False)
                if li.get_text(strip=True)
            ]
            if items:
                body_parts.append(
                    f"\\begin{{{env}}}\n" + "\n".join(items) + f"\n\\end{{{env}}}"
                )
        elif name == "pre":
            body_parts.append(
                "\\begin{verbatim}\n" + el.get_text() + "\n\\end{verbatim}"
            )
        elif name == "blockquote":
            body_parts.append(
                "\\begin{quote}\n" + _latex_escape(el.get_text(strip=True)) + "\n\\end{quote}"
            )
        else:  # paragraph
            text = el.get_text(strip=True)
            if text:
                body_parts.append(_latex_escape(text))

    body = "\n\n".join(body_parts)
    document = (
        "\\documentclass{article}\n"
        "\\usepackage[utf8]{inputenc}\n"
        "\\usepackage[T1]{fontenc}\n"
        "\\usepackage{graphicx}\n"
        "\\usepackage{hyperref}\n"
        "\\begin{document}\n\n" + body + "\n\n\\end{document}\n"
    )
    return document.encode("utf-8")
