"""Prepare books locally; keep exact source offsets and non-overlapping work packets.

No LLM API calls or automatic uploads are performed.
"""
from __future__ import annotations

import hashlib
import json
import posixpath
import re
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote
from xml.etree import ElementTree

MAX_SOURCE = 50 * 1024 * 1024
MAX_EPUB_UNCOMPRESSED = 100 * 1024 * 1024
HEADINGS = re.compile(r"(?m)^(#{1,6})[ \t]+(.+?)[ \t]*$")
CHAPTERS = re.compile(r"(?im)^((?:chapter|part)[ \t]+[0-9ivxlcdm]+[^\n]*|第[零一二三四五六七八九十百千0-9]+[章节篇][^\n]*)$")


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class XHTMLText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip: list[str] = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "head", "svg"}:
            self.skip.append(tag)
        if self.skip:
            return
        if re.fullmatch(r"h[1-6]", tag):
            self.parts.append("\n\n" + "#" * tag[1] + " ")
        elif tag in {"p", "div", "section", "article", "li", "blockquote", "br", "tr"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self.skip:
            if tag == self.skip[-1]:
                self.skip.pop()
            return
        if tag in {"p", "div", "section", "article", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self.parts.append("\n")

    def handle_data(self, text: str) -> None:
        if not self.skip:
            self.parts.append(text)

    def result(self) -> str:
        return re.sub(r"\n{3,}", "\n\n", "".join(self.parts)).strip()


def epub_path(base: str, href: str) -> str:
    relative = unquote(href.split("#", 1)[0])
    path = posixpath.normpath(posixpath.join(base, relative))
    if not path or path == ".." or path.startswith("../") or path.startswith("/"):
        raise ValueError("EPUB contains an unsafe file reference")
    return path


def load_epub(source: Path) -> str:
    with zipfile.ZipFile(source) as archive:
        members = archive.infolist()
        if len(members) > 2000 or sum(m.file_size for m in members) > MAX_EPUB_UNCOMPRESSED:
            raise ValueError("EPUB exceeds extraction limits")
        if any(m.file_size > MAX_SOURCE for m in members):
            raise ValueError("EPUB has an oversized member")
        root = ElementTree.fromstring(archive.read("META-INF/container.xml"))
        rootfile = root.find(".//{*}rootfile")
        if rootfile is None or not rootfile.get("full-path"):
            raise ValueError("EPUB package location is missing")
        package_path = epub_path("", rootfile.attrib["full-path"])
        package = ElementTree.fromstring(archive.read(package_path))
        manifest = {
            item.attrib["id"]: (item.attrib["href"], item.get("media-type"))
            for item in package.findall(".//{*}manifest/{*}item")
            if "id" in item.attrib and "href" in item.attrib
        }
        spine = package.find(".//{*}spine")
        if spine is None:
            raise ValueError("EPUB spine is missing")
        parts = []
        for itemref in spine.findall("{*}itemref"):
            ref = itemref.get("idref")
            if ref not in manifest:
                raise ValueError("EPUB spine has an unresolved item")
            href, media_type = manifest[ref]
            if media_type not in ("application/xhtml+xml", "text/html"):
                continue
            item_path = epub_path(posixpath.dirname(package_path), href)
            parser = XHTMLText()
            parser.feed(archive.read(item_path).decode("utf-8-sig", errors="replace"))
            content = parser.result()
            if content:
                parts.append(content)
        if not parts:
            raise ValueError("EPUB contains no readable spine text")
        return "\n\n".join(parts)


def load_pdf(source: Path, backend: str) -> tuple[str, str, list[dict], list[str]]:
    warnings: list[str] = []
    if backend in {"auto", "docling"}:
        try:
            from docling.document_converter import DocumentConverter
            converted = DocumentConverter().convert(str(source)).document.export_to_markdown()
            if not converted.strip():
                raise ValueError("Empty Docling output")
            return converted, "docling", [], [
                "Docling Markdown has no verified original page mapping; only source offsets are auditable.",
                "Review tables, figures, OCR, and equations against the book.",
            ]
        except Exception as exc:
            if backend == "docling":
                raise RuntimeError(f"Docling could not parse PDF: {exc}") from exc
            warnings.append(f"Docling not used ({type(exc).__name__}); attempting PyMuPDF.")
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("PDF requires an optional dependency: pip install '.[pdf]' or '.[docling]'") from exc
    parts: list[str] = []
    pages: list[dict] = []
    offset = 0
    with fitz.open(str(source)) as pdf:
        for number, page in enumerate(pdf, 1):
            if number > 1:
                parts.append("\n\n")
                offset += 2
            text = page.get_text(sort=True).strip()
            start = offset
            parts.append(text)
            offset += len(text)
            pages.append({"page": number, "start": start, "end": offset})
    text = "".join(parts)
    if not text.strip():
        raise ValueError("PDF has no extracted text; an OCR workflow and manual verification are required")
    warnings.append("Figures, equations, tables, and layout have not been independently verified.")
    return text, "pymupdf", pages, warnings


def read_book(source: Path, backend: str) -> tuple[str, str, list[dict], list[str]]:
    if not source.is_file():
        raise FileNotFoundError(source)
    if source.stat().st_size > MAX_SOURCE:
        raise ValueError("Source exceeds 50 MiB")
    if source.suffix.lower() in {".txt", ".md", ".markdown"}:
        return source.read_text(encoding="utf-8-sig"), "text", [], []
    if source.suffix.lower() == ".epub":
        return load_epub(source), "epub-spine", [], [
            "EPUB images, notes, and multimedia are not verified by this reader."
        ]
    if source.suffix.lower() == ".pdf":
        return load_pdf(source, backend)
    raise ValueError("Supported inputs: .txt, .md, .markdown, .epub, .pdf")


def sections_from_text(text: str) -> tuple[list[dict], list[str]]:
    hits = [(m.start(), len(m.group(1)), m.group(2).strip()) for m in HEADINGS.finditer(text)]
    if not hits:
        hits = [(m.start(), 1, m.group(1).strip()) for m in CHAPTERS.finditer(text)]
    warnings: list[str] = []
    if not hits:
        hits = [(0, 1, "Unclassified full text")]
        warnings.append("No reliable headings found; synthetic section requires TOC review.")
    elif hits[0][0] and text[:hits[0][0]].strip():
        hits.insert(0, (0, 0, "Front matter"))
    sections = []
    for index, (start, level, title) in enumerate(hits):
        end = hits[index + 1][0] if index + 1 < len(hits) else len(text)
        sections.append({
            "id": f"S{index + 1:03d}", "title": title, "level": level,
            "start": start, "end": end,
            "non_whitespace_chars": len(re.sub(r"\s", "", text[start:end])),
        })
    return sections, warnings


def packets_from_text(text: str, sections: list[dict], max_chars: int) -> list[dict]:
    if max_chars < 200:
        raise ValueError("max_chars must be at least 200")
    packets = []
    for section in sections:
        start, number = section["start"], 0
        while start < section["end"]:
            end = min(start + max_chars, section["end"])
            if end < section["end"]:
                break_at = text.rfind("\n\n", start + max_chars // 2, end)
                if break_at > start:
                    end = break_at + 2
            number += 1
            packets.append({
                "id": f"{section['id']}-P{number:03d}",
                "section_id": section["id"], "start": start, "end": end, "text": text[start:end],
            })
            start = end
    if "".join(p["text"] for p in packets) != text:
        raise AssertionError("Packet generation lost or duplicated source text")
    return packets


def prepare(source: Path, output: Path, profile: str = "auto",
            max_chars: int = 2800, pdf_backend: str = "auto") -> dict:
    if (output / "manifest.json").exists() or (output / "units.json").exists():
        raise FileExistsError("Project exists; use a fresh --output directory")
    text, reader, pages, warnings = read_book(source, pdf_backend)
    if not text.strip():
        raise ValueError("No readable text in source")
    sections, structure_warnings = sections_from_text(text)
    packets = packets_from_text(text, sections, max_chars)
    manifest = {
        "schema_version": "0.1", "source_name": source.name,
        "source_sha256": digest(text), "source_length": len(text),
        "reader": reader, "profile": profile, "sections": sections,
        "page_spans": pages, "chunk_count": len(packets),
        "warnings": warnings + structure_warnings, "status": "awaiting_agent_analysis",
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "source.txt").write_text(text, encoding="utf-8")
    write_json(output / "manifest.json", manifest)
    with (output / "work_packets.jsonl").open("w", encoding="utf-8") as stream:
        for packet in packets:
            stream.write(json.dumps(packet, ensure_ascii=False) + "\n")
    write_json(output / "units.json", [])
    return manifest
