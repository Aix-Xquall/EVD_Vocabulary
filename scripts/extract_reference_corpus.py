"""Extract searchable page and section text from reference PDFs and DOCX files."""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree


SECTION_PATTERN = re.compile(
    r"^(?P<number>(?:[A-Z]\.)?\d+(?:\.\d+){0,5}\.?|APPENDIX\s+[A-Z]|[A-Z]\.\d+(?:\.\d+)*)"
    r"(?:\s+|\s*[-:]\s*)(?P<title>[A-Z][^\n]{1,120})$",
)
PAGE_COUNT_PATTERN = re.compile(r"^\d+\s+of\s+\d+$", re.IGNORECASE)
WORD_NAMESPACE = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", action="append", default=[], type=Path)
    parser.add_argument("--docx", action="append", default=[], type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def heading_from_line(raw_line: str) -> str:
    line = normalize_text(raw_line)
    if not line or PAGE_COUNT_PATTERN.match(line) or "...." in line:
        return ""
    match = SECTION_PATTERN.match(line)
    if not match:
        return ""
    number = match.group("number").rstrip(".")
    title = match.group("title").rstrip(".")
    # Reject body text that begins with a value, requirement number, or list item.
    if number.isdigit() and int(number) > 9:
        return ""
    if len(title.split()) > 12:
        return ""
    if re.search(r"\b(?:V/m|A/m|Telephone|e-mail)\b", title, re.IGNORECASE):
        return ""
    return f"{number} {title}"


def page_records(path: Path, page_number: int, raw_text: str, current_section: str) -> tuple[list[dict], str]:
    records = []
    chunk = []
    section = current_section

    def flush() -> None:
        text = normalize_text(" ".join(chunk))
        if text:
            records.append(
                {
                    "document": path.name,
                    "page": page_number,
                    "section": section,
                    "text": text,
                }
            )
        chunk.clear()

    for raw_line in raw_text.splitlines():
        line = normalize_text(raw_line)
        if not line:
            continue
        heading = heading_from_line(line)
        if heading:
            flush()
            section = heading
        chunk.append(line)
    flush()
    return records, section


def extract_pdf(path: Path) -> list[dict]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("pypdf is required to extract reference PDFs") from exc

    reader = PdfReader(path)
    records = []
    current_section = "Front matter"
    for page_number, page in enumerate(reader.pages, start=1):
        raw_text = page.extract_text() or ""
        page_chunks, current_section = page_records(path, page_number, raw_text, current_section)
        records.extend(page_chunks)
    return records


def extract_docx(path: Path) -> list[dict]:
    with zipfile.ZipFile(path) as archive:
        document_xml = archive.read("word/document.xml")
    root = ElementTree.fromstring(document_xml)
    paragraphs = []
    for paragraph in root.iter(f"{WORD_NAMESPACE}p"):
        text = normalize_text("".join(node.text or "" for node in paragraph.iter(f"{WORD_NAMESPACE}t")))
        if text:
            paragraphs.append(text)

    records = []
    current_section = "Document body"
    for index, paragraph in enumerate(paragraphs, start=1):
        heading = heading_from_line(paragraph)
        if heading:
            current_section = heading
        elif paragraph.endswith(":") and len(paragraph) <= 100:
            current_section = paragraph.rstrip(":")
        records.append(
            {
                "document": path.name,
                "page": "",
                "paragraph": index,
                "section": current_section,
                "text": paragraph,
            }
        )
    return records


def main() -> None:
    args = parse_args()
    records = []
    for path in args.pdf:
        records.extend(extract_pdf(path))
    for path in args.docx:
        records.extend(extract_docx(path))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as output:
        for record in records:
            output.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"Extracted {len(records)} records to {args.output}")


if __name__ == "__main__":
    main()
