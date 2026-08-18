"""Build, load, and validate source annotations for vocabulary examples."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import Counter
from datetime import date
from pathlib import Path, PureWindowsPath
from typing import Iterable

from config import DEFAULT_SETTINGS, Settings
from script_builder import audio_key_for_entry
from tense_analyzer import sentence_key
from vocabulary_loader import load_vocabulary


ANNOTATION_COLUMNS = [
    "sentence_key",
    "source_file",
    "source_id",
    "word",
    "example_number",
    "example_en",
    "reference_document",
    "reference_section",
    "reference_page",
    "attribution",
    "confidence",
    "reviewed_at",
]

NASA_4003 = "NASA-STD-4003A_w-Change 1 - Revalidated 03-13-2026.pdf"
NASA_6012 = "2022-01-11-NASA-STD-6012A-Approved.pdf"
MIL_464 = "MIL-STD-464C.pdf"
MSFC_3697 = "MSFC-HDBK-3697.pdf"
MEETING_REPORT = "Report_June 26.docx"
REFERENCE_ORDER = {
    "MSFC-HDBK-3697.csv": [MSFC_3697, NASA_4003, MIL_464, NASA_6012],
    "NASA-STD-4003A.csv": [NASA_4003, MSFC_3697, NASA_6012, MIL_464],
    "複合材質航電環.csv": [MEETING_REPORT, NASA_4003, NASA_6012, MSFC_3697, MIL_464],
    "EMC顧問回覆與系統整合詞彙.csv": [MEETING_REPORT, MIL_464, NASA_4003, MSFC_3697, NASA_6012],
    "EMC航電詞彙整合1.csv": [MIL_464, NASA_4003, MSFC_3697, MEETING_REPORT, NASA_6012],
    "EMC航電詞彙整合2.csv": [MIL_464, NASA_4003, MSFC_3697, MEETING_REPORT, NASA_6012],
}
SELF_AUTHORED_SECTION = "無對應工程參考文件章節"
CURATED_OVERRIDES = {
    "Bonding provides a low-impedance path between metal parts.": (
        MIL_464, "A.5.11 Electrical bonding", "138"
    ),
    "Each enclosure should have a defined bonding path.": (
        MIL_464, "A.5.11 Electrical bonding", "141"
    ),
    "Shielding reduces radiated emissions and susceptibility.": (
        MSFC_3697, "5.4.1 BONDING FOR ENCLOSURE SHIELDING INTEGRITY", "32"
    ),
    "The composite ring does not naturally provide shielding.": (
        MIL_464, "A.5.3 External RF EME", "81"
    ),
    "A bonding strap should be short and wide.": (
        MIL_464, "A.5.11 Electrical bonding", "141"
    ),
    "Long bonding straps are ineffective at high frequency.": (
        MSFC_3697, "4.3 RADIO FREQUENCY (RF) (CLASS R) BONDING", "13"
    ),
    "A direct RF bond may not be realistically obtained with shock mounts.": (
        MSFC_3697, "4.3 RADIO FREQUENCY (RF) (CLASS R) BONDING", "13"
    ),
    "The A1 ring is open-ended at the top and bottom.": (
        MEETING_REPORT, "Consultant recommendation", "12"
    ),
}
TOKEN_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)?", re.IGNORECASE)
NUMBERED_SECTION_PATTERN = re.compile(
    r"^(?:[A-Z]\.)?\d+(?:\.\d+){0,5}\s+[A-Z]",
)
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "before", "by", "can", "could",
    "each", "for", "from", "has", "have", "if", "in", "into", "is", "it", "may",
    "must", "of", "on", "or", "should", "that", "the", "their", "this", "to", "was",
    "were", "will", "with", "without",
}


def load_example_sources_for_entries(
    entries: Iterable[dict],
    settings: Settings,
) -> dict[str, dict[str, dict]]:
    annotations = read_annotations(settings.example_sources_path)
    result: dict[str, dict[str, dict]] = {}
    missing = 0
    for entry in entries:
        entry_key = audio_key_for_entry(entry)
        for example_number in (1, 2):
            example = str(entry.get(f"example_{example_number}_en") or "").strip()
            if not example:
                continue
            annotation = annotations.get(sentence_key(example))
            if annotation is None:
                missing += 1
                continue
            result.setdefault(entry_key, {})[f"example_{example_number}"] = annotation
    if missing:
        print(f"Example sources: {missing} example occurrences are not annotated.")
    else:
        print("Example sources: all example occurrences are covered.")
    return result


def read_annotations(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    annotations = {}
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        missing = [column for column in ANNOTATION_COLUMNS if column not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path} missing columns: {', '.join(missing)}")
        for row_number, row in enumerate(reader, start=2):
            key = str(row.get("sentence_key") or "").strip()
            example = str(row.get("example_en") or "").strip()
            if not key or key != sentence_key(example):
                raise ValueError(f"{path} row {row_number} has an invalid sentence_key")
            if key in annotations:
                raise ValueError(f"{path} row {row_number} duplicates sentence_key {key}")
            annotations[key] = {
                "document": str(row.get("reference_document") or "").strip(),
                "section": str(row.get("reference_section") or "").strip(),
                "page": str(row.get("reference_page") or "").strip(),
                "attribution": str(row.get("attribution") or "").strip(),
            }
    return annotations


def generate_annotations(entries: Iterable[dict], corpus_path: Path, output_path: Path) -> int:
    records = load_corpus(corpus_path)
    document_frequency = Counter()
    for record in records:
        document_frequency.update(set(record["tokens"]))
    record_count = max(len(records), 1)
    idf = {
        token: math.log((record_count + 1) / (count + 1)) + 1
        for token, count in document_frequency.items()
    }

    rows = []
    seen = set()
    for entry in entries:
        source_file = source_name(entry.get("_source_file", ""))
        matching_source_file = matching_chapter_name(entry, source_file)
        for example_number in (1, 2):
            example = str(entry.get(f"example_{example_number}_en") or "").strip()
            if not example:
                continue
            key = sentence_key(example)
            if key in seen:
                continue
            seen.add(key)
            match = match_source(entry, example, matching_source_file, records, idf)
            rows.append(
                {
                    "sentence_key": key,
                    "source_file": source_file,
                    "source_id": str(entry.get("id") or ""),
                    "word": str(entry.get("word") or ""),
                    "example_number": str(example_number),
                    "example_en": example,
                    "reference_document": match["document"],
                    "reference_section": match["section"],
                    "reference_page": match["page"],
                    "attribution": match["attribution"],
                    "confidence": f"{match['confidence']:.2f}",
                    "reviewed_at": date.today().isoformat(),
                }
            )
    write_rows(output_path, rows)
    return len(rows)


def load_corpus(path: Path) -> list[dict]:
    records = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            record = json.loads(line)
            section = str(record.get("section") or "").strip()
            document = str(record.get("document") or "").strip()
            if not is_usable_section(document, section):
                continue
            text = normalize(str(record.get("text") or ""))
            records.append(
                {
                    "document": document,
                    "section": section,
                    "page": str(record.get("page") or record.get("paragraph") or ""),
                    "text": text,
                    "tokens": content_tokens(text),
                }
            )
    return records


def is_usable_section(document: str, section: str) -> bool:
    if not section or section == "Front matter" or len(section) > 100 or "...." in section:
        return False
    if document == MEETING_REPORT:
        return section != "Document body"
    if "[EBR" in section or re.match(r"^\d+\s+of\s+\d+$", section, re.IGNORECASE):
        return False
    bare_number = re.match(r"^(\d+)\s", section)
    if bare_number and int(bare_number.group(1)) > 9:
        return False
    title = re.sub(r"^(?:[A-Z]\.)?\d+(?:\.\d+){0,5}\s+", "", section)
    if len(title.split()) > 12:
        return False
    if re.search(r"\b(?:V/m|A/m|Telephone|e-mail)\b", title, re.IGNORECASE):
        return False
    return bool(NUMBERED_SECTION_PATTERN.match(section) or section.upper().startswith("APPENDIX "))


def match_source(
    entry: dict,
    example: str,
    source_file: str,
    records: list[dict],
    idf: dict[str, float],
) -> dict:
    override = CURATED_OVERRIDES.get(example)
    if override:
        document, section, page = override
        return {
            "document": document,
            "section": section,
            "page": page,
            "attribution": "改寫自",
            "confidence": 1.0,
        }
    allowed_documents = REFERENCE_ORDER.get(source_file, [])
    if not allowed_documents:
        return self_authored_match()

    normalized_example = normalize(example)
    example_tokens = content_tokens(example)
    term = normalize(str(entry.get("word") or ""))
    term_tokens = content_tokens(term)
    candidates = [record for record in records if record["document"] in allowed_documents]
    exact = [record for record in candidates if normalized_example in record["text"]]
    if exact:
        record = exact[0]
        return source_match(record, "原文摘錄", 1.0)

    weighted_total = sum(idf.get(token, 1.0) for token in example_tokens) or 1.0
    ranked = []
    for record in candidates:
        shared = example_tokens & record["tokens"]
        lexical = sum(idf.get(token, 1.0) for token in shared) / weighted_total
        term_coverage = len(term_tokens & record["tokens"]) / max(len(term_tokens), 1)
        phrase_bonus = 0.18 if term and term in record["text"] else 0.0
        section_tokens = content_tokens(record["section"])
        section_bonus = 0.08 * (len(example_tokens & section_tokens) / max(len(section_tokens), 1))
        priority = allowed_documents.index(record["document"])
        priority_bonus = max(0.0, 0.06 - (priority * 0.012))
        score = (lexical * 0.62) + (term_coverage * 0.22) + phrase_bonus + section_bonus + priority_bonus
        ranked.append((score, record))

    score, record = max(ranked, key=lambda item: item[0])
    if score < 0.38:
        return self_authored_match()
    attribution = "改寫自" if score >= 0.55 else "主題參考"
    return source_match(record, attribution, min(score, 0.99))


def source_match(record: dict, attribution: str, confidence: float) -> dict:
    return {
        "document": record["document"],
        "section": record["section"],
        "page": record["page"],
        "attribution": attribution,
        "confidence": confidence,
    }


def self_authored_match() -> dict:
    return {
        "document": "自編例句",
        "section": SELF_AUTHORED_SECTION,
        "page": "",
        "attribution": "自編例句",
        "confidence": 1.0,
    }


def validate_coverage(entries: Iterable[dict], path: Path) -> list[str]:
    annotations = read_annotations(path)
    errors = []
    expected = set()
    for entry in entries:
        for example_number in (1, 2):
            example = str(entry.get(f"example_{example_number}_en") or "").strip()
            if example:
                expected.add(sentence_key(example))
    missing = expected - set(annotations)
    extra = set(annotations) - expected
    if missing:
        errors.append(f"missing {len(missing)} unique examples")
    if extra:
        errors.append(f"contains {len(extra)} stale examples")
    return errors


def normalize(value: str) -> str:
    return " ".join(TOKEN_PATTERN.findall(str(value or "").casefold()))


def content_tokens(value: str) -> set[str]:
    return {token for token in TOKEN_PATTERN.findall(str(value or "").casefold()) if token not in STOPWORDS}


def source_name(value: str) -> str:
    text = str(value or "")
    return PureWindowsPath(text).name if "\\" in text else Path(text).name


def matching_chapter_name(entry: dict, source_file: str) -> str:
    if source_file != "hard_words.csv":
        return source_file
    chapter = str(entry.get("_source_chapter") or "").strip()
    if not chapter:
        return source_file
    return chapter if chapter.lower().endswith(".csv") else f"{chapter}.csv"


def write_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=ANNOTATION_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    generate = subparsers.add_parser("generate")
    generate.add_argument("--corpus", required=True, type=Path)
    generate.add_argument("--output", type=Path, default=DEFAULT_SETTINGS.example_sources_path)
    validate = subparsers.add_parser("validate")
    validate.add_argument("--path", type=Path, default=DEFAULT_SETTINGS.example_sources_path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    entries = load_vocabulary(DEFAULT_SETTINGS.vocabulary_dir)
    if args.command == "generate":
        count = generate_annotations(entries, args.corpus, args.output)
        print(f"Generated {count} unique example source annotations: {args.output}")
        return
    errors = validate_coverage(entries, args.path)
    if errors:
        raise SystemExit("Example source validation failed: " + "; ".join(errors))
    print("Example source validation passed.")


if __name__ == "__main__":
    main()
