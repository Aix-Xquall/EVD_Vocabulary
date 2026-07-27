import argparse
import csv
import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path, PureWindowsPath
from typing import Dict, Iterable

from config import DEFAULT_SETTINGS, Settings
from script_builder import audio_key_for_entry
from vocabulary_loader import load_vocabulary


TENSE_NAMES_ZH = [
    "現在簡單式",
    "現在進行式",
    "現在完成式",
    "現在完成進行式",
    "過去簡單式",
    "過去進行式",
    "過去完成式",
    "過去完成進行式",
    "未來簡單式",
    "未來進行式",
    "未來完成式",
    "未來完成進行式",
    "特殊句型/需確認",
]

TENSE_FORMULAS = {
    "現在簡單式": "S + V / V-s",
    "現在進行式": "S + am/is/are + V-ing",
    "現在完成式": "S + have/has + p.p.",
    "現在完成進行式": "S + have/has been + V-ing",
    "過去簡單式": "S + V-ed",
    "過去進行式": "S + was/were + V-ing",
    "過去完成式": "S + had + p.p.",
    "過去完成進行式": "S + had been + V-ing",
    "未來簡單式": "S + will + V",
    "未來進行式": "S + will be + V-ing",
    "未來完成式": "S + will have + p.p.",
    "未來完成進行式": "S + will have been + V-ing",
    "特殊句型/需確認": "依實際句型判斷",
}

TENSE_DISPLAY_NAMES = {
    name: name.removesuffix("式")
    for name in TENSE_NAMES_ZH
    if name != "特殊句型/需確認"
}

ANNOTATION_COLUMNS = [
    "sentence_key",
    "source_file",
    "source_id",
    "word",
    "example_number",
    "example_en",
    "tense_name_zh",
    "formula",
    "highlights_json",
    "confidence",
    "reviewed_at",
]

_MODAL_PATTERN = re.compile(
    r"\b(?:cannot|can't|couldn't|shouldn't|wouldn't|won't|mightn't|mustn't|shan't|"
    r"can|could|may|might|must|shall|should|will|would)\b",
    re.IGNORECASE,
)
_WORD_PATTERN = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
_MODAL_SUBJECT_PRONOUNS = {"i", "you", "he", "she", "it", "we", "they"}
_MODAL_SUBJECT_DETERMINERS = {
    "a",
    "an",
    "the",
    "my",
    "your",
    "his",
    "her",
    "its",
    "our",
    "their",
    "this",
    "that",
    "these",
    "those",
    "each",
    "every",
    "some",
    "any",
}
_MODAL_INTERVENING_ADVERBS = {
    "also",
    "always",
    "certainly",
    "definitely",
    "ever",
    "just",
    "never",
    "possibly",
    "probably",
    "rather",
    "really",
    "simply",
    "still",
}


@dataclass(frozen=True)
class AnnotationValidation:
    annotations: Dict[str, dict]
    errors: list[str]


def load_tense_annotations_for_entries(
    entries: Iterable[dict],
    settings: Settings,
) -> Dict[str, Dict[str, dict]]:
    """Map reviewed CSV annotations to the payload format used by the website."""
    entry_list = list(entries)
    validation = read_tense_annotations(settings.tense_annotations_path)
    if validation.errors:
        raise ValueError(_format_validation_errors(validation.errors))

    result: Dict[str, Dict[str, dict]] = {}
    missing_count = 0
    for entry in entry_list:
        entry_key = audio_key_for_entry(entry)
        for example_index in (1, 2):
            text = _example_text(entry, example_index)
            if not text:
                continue
            analysis = validation.annotations.get(sentence_key(text))
            if analysis is None:
                missing_count += 1
                continue
            public_analysis = dict(analysis)
            modal_structure = extract_modal_structure(text)
            if modal_structure:
                public_analysis["modal_structure"] = modal_structure
            public_analysis.update(_display_analysis(public_analysis))
            result.setdefault(entry_key, {})[f"example_{example_index}"] = public_analysis

    if missing_count:
        print(f"Tense annotations: {missing_count} example occurrences are not annotated.")
    else:
        print(f"Tense annotations: all {count_unique_examples(entry_list)} unique examples are covered.")
    return result


def extract_modal_structure(sentence: str) -> dict | None:
    """Return the concrete modal and following base verb used in a sentence."""
    words = [match.group(0) for match in _WORD_PATTERN.finditer(sentence)]
    modal_index = next(
        (index for index, word in enumerate(words) if _MODAL_PATTERN.fullmatch(word)),
        None,
    )
    if modal_index is None:
        return None

    modal_verb = words[modal_index].lower()
    next_index = modal_index + 1
    is_question = "?" in sentence

    if is_question and next_index < len(words):
        subject_start = words[next_index].lower()
        if subject_start in _MODAL_SUBJECT_PRONOUNS:
            next_index += 1
        elif subject_start in _MODAL_SUBJECT_DETERMINERS:
            # Current vocabulary questions use a determiner plus one subject noun,
            # such as "Can my child try...?" and "Could a porter help...?".
            next_index += 2

    if next_index < len(words) and words[next_index].lower() == "not":
        modal_verb = f"{modal_verb} not"
        next_index += 1

    while next_index < len(words):
        candidate = words[next_index].lower()
        if candidate in _MODAL_INTERVENING_ADVERBS or candidate.endswith("ly"):
            next_index += 1
            continue
        return {
            "modal_verb": modal_verb,
            "base_verb": candidate,
        }
    return None


def validate_annotations_three_passes(
    entries: Iterable[dict],
    annotations_path: Path,
) -> list[dict]:
    """Validate stored annotations, display rules, and explicit grammar markers."""
    entry_list = list(entries)
    records = _unique_example_records(entry_list)
    validation, missing = validate_annotation_coverage(entry_list, annotations_path)
    reports = [
        {
            "pass": 1,
            "name": "資料完整性",
            "checked": len(validation.annotations),
            "errors": list(validation.errors)
            + ([f"missing {len(missing)} unique examples"] if missing else []),
        }
    ]

    display_errors = []
    for key, analysis in validation.annotations.items():
        sentence = str(records.get(key, {}).get("example_en") or "")
        if not sentence:
            continue
        modal_structure = extract_modal_structure(sentence)
        display = _display_analysis(
            {
                **analysis,
                "modal_structure": modal_structure,
            }
        )
        if not display.get("display_name_zh") or not display.get("display_formula"):
            display_errors.append(f"{sentence!r}: display label or formula is empty")
        elif (
            analysis["name_zh"] == "特殊句型/需確認"
            and _MODAL_PATTERN.search(sentence)
            and display["display_name_zh"] != "情態動詞"
        ):
            display_errors.append(f"{sentence!r}: modal structure was not converted")
        elif analysis["name_zh"] in TENSE_DISPLAY_NAMES and (
            display["display_name_zh"] != TENSE_DISPLAY_NAMES[analysis["name_zh"]]
            or display["display_formula"] != TENSE_FORMULAS[analysis["name_zh"]]
        ):
            display_errors.append(f"{sentence!r}: tense display is not canonical")
    reports.append(
        {
            "pass": 2,
            "name": "顯示規則",
            "checked": len(validation.annotations),
            "errors": display_errors,
        }
    )

    grammar_errors = []
    for key, analysis in validation.annotations.items():
        sentence = str(records.get(key, {}).get("example_en") or "")
        if not sentence or analysis["name_zh"] == "特殊句型/需確認":
            continue
        highlighted_structure = " ".join(analysis.get("highlights") or [])
        inferred_name = _infer_explicit_tense(highlighted_structure)
        if inferred_name and inferred_name != analysis["name_zh"]:
            grammar_errors.append(
                f"{sentence!r}: annotated {analysis['name_zh']}, "
                f"explicit markers indicate {inferred_name}"
            )
    reports.append(
        {
            "pass": 3,
            "name": "文法標記交叉檢查",
            "checked": len(validation.annotations),
            "errors": grammar_errors,
        }
    )
    return reports


def _display_analysis(analysis: dict) -> dict:
    modal = analysis.get("modal_structure") or {}
    modal_verb = str(modal.get("modal_verb") or "").strip()
    base_verb = str(modal.get("base_verb") or "").strip()
    if (
        analysis.get("name_zh") == "特殊句型/需確認"
        and modal_verb
        and base_verb
    ):
        return {
            "display_name_zh": "情態動詞",
            "display_formula": f"{modal_verb} + 原形動詞：{base_verb}",
        }

    name = str(analysis.get("name_zh") or "").strip()
    return {
        "display_name_zh": TENSE_DISPLAY_NAMES.get(name, name),
        "display_formula": TENSE_FORMULAS.get(
            name,
            str(analysis.get("formula") or "").strip(),
        ),
    }


def _infer_explicit_tense(sentence: str) -> str | None:
    """Infer only tenses with unambiguous auxiliary markers."""
    normalized = " ".join(word.lower() for word in _WORD_PATTERN.findall(sentence))
    adverbs = r"(?:[a-z]+ly\s+){0,2}"
    past_participle = r"(?:been|[a-z]+(?:ed|en))"
    patterns = [
        ("未來完成進行式", r"\bwill have been [a-z]+ing\b"),
        ("未來完成式", rf"\bwill have {adverbs}{past_participle}\b"),
        ("未來進行式", r"\bwill be [a-z]+ing\b"),
        ("現在完成進行式", r"\b(?:have|has) been [a-z]+ing\b"),
        ("過去完成進行式", r"\bhad been [a-z]+ing\b"),
        ("現在進行式", r"\b(?:am|is|are) [a-z]+ing\b"),
        ("過去進行式", r"\b(?:was|were) [a-z]+ing\b"),
        ("現在完成式", rf"\b(?:have|has) {adverbs}{past_participle}\b"),
        ("過去完成式", rf"\bhad {adverbs}{past_participle}\b"),
        ("未來簡單式", r"\bwill\b"),
    ]
    for name, pattern in patterns:
        if re.search(pattern, normalized):
            return name
    return None


def export_pending_annotations(
    entries: Iterable[dict],
    annotations_path: Path,
    output_path: Path,
) -> int:
    """Write only examples that are missing from the reviewed annotation CSV."""
    validation = read_tense_annotations(annotations_path)
    if validation.errors:
        raise ValueError(_format_validation_errors(validation.errors))

    records = _unique_example_records(entries)
    pending = [
        _pending_row(record)
        for key, record in records.items()
        if key not in validation.annotations
    ]
    _write_rows(output_path, pending)
    return len(pending)


def import_completed_annotations(
    completed_path: Path,
    annotations_path: Path,
    entries: Iterable[dict],
) -> int:
    """Validate ChatGPT output and merge it into the reviewed annotation CSV."""
    known_examples = _unique_example_records(entries)
    existing = read_tense_annotations(annotations_path)
    if existing.errors:
        raise ValueError(_format_validation_errors(existing.errors))

    imported = read_tense_annotations(completed_path)
    errors = list(imported.errors)
    completed_rows = _read_csv_rows(completed_path)
    imported_keys = set(imported.annotations)

    for row_number, row in completed_rows:
        key = str(row.get("sentence_key") or "").strip()
        if key and key not in known_examples:
            errors.append(f"row {row_number}: sentence_key is not present in the current vocabulary")

    if not imported_keys:
        errors.append("completed file does not contain any valid annotations")
    if errors:
        raise ValueError(_format_validation_errors(errors))

    rows = []
    if annotations_path.exists():
        for _, row in _read_csv_rows(annotations_path):
            key = str(row.get("sentence_key") or "").strip()
            if key in known_examples and key not in imported_keys:
                rows.append(
                    {column: str(row.get(column) or "") for column in ANNOTATION_COLUMNS}
                )

    for key, record in known_examples.items():
        if key in imported_keys:
            rows.append(_annotation_row(record, imported.annotations[key]))

    _write_rows(annotations_path, rows)
    return len(imported_keys)


def validate_annotation_coverage(
    entries: Iterable[dict],
    annotations_path: Path,
) -> tuple[AnnotationValidation, list[dict]]:
    validation = read_tense_annotations(annotations_path)
    records = _unique_example_records(entries)
    missing = [record for key, record in records.items() if key not in validation.annotations]
    return validation, missing


def read_tense_annotations(path: Path) -> AnnotationValidation:
    if not path.exists():
        return AnnotationValidation({}, [])

    annotations: Dict[str, dict] = {}
    errors: list[str] = []
    for row_number, row in _read_csv_rows(path):
        if not any(str(value or "").strip() for value in row.values()):
            continue
        key = str(row.get("sentence_key") or "").strip()
        sentence = str(row.get("example_en") or "").strip()
        if not sentence:
            errors.append(f"row {row_number}: example_en is required")
            continue
        expected_key = sentence_key(sentence)
        if key != expected_key:
            errors.append(f"row {row_number}: sentence_key does not match example_en")
            continue

        analysis, row_errors = _analysis_from_row(row, sentence, row_number)
        errors.extend(row_errors)
        if row_errors:
            continue
        previous = annotations.get(key)
        if previous is not None and previous != analysis:
            errors.append(f"row {row_number}: duplicate sentence_key has conflicting analysis")
            continue
        annotations[key] = analysis
    return AnnotationValidation(annotations, errors)


def count_unique_examples(entries: Iterable[dict]) -> int:
    return len(_unique_example_records(entries))


def sentence_key(text: str) -> str:
    normalized = " ".join(text.strip().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _read_csv_rows(path: Path) -> list[tuple[int, dict]]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            fieldnames = reader.fieldnames or []
            missing = [column for column in ANNOTATION_COLUMNS if column not in fieldnames]
            if missing:
                raise ValueError(f"{path} missing required columns: {', '.join(missing)}")
            return [(row_number, row) for row_number, row in enumerate(reader, start=2)]
    except OSError as exc:
        raise ValueError(f"Unable to read {path}: {exc}") from exc


def _analysis_from_row(row: dict, sentence: str, row_number: int) -> tuple[dict, list[str]]:
    errors = []
    name = str(row.get("tense_name_zh") or "").strip()
    if name not in TENSE_NAMES_ZH:
        errors.append(f"row {row_number}: invalid tense_name_zh {name!r}")

    formula = str(row.get("formula") or "").strip()
    if not formula:
        errors.append(f"row {row_number}: formula is required")

    highlights = []
    raw_highlights = str(row.get("highlights_json") or "").strip()
    try:
        parsed_highlights = json.loads(raw_highlights)
    except json.JSONDecodeError:
        parsed_highlights = None
        errors.append(f"row {row_number}: highlights_json must be a JSON array")
    if isinstance(parsed_highlights, list):
        for highlight in parsed_highlights:
            value = str(highlight).strip()
            if not value:
                errors.append(f"row {row_number}: highlights_json contains an empty value")
            elif not _contains_whole_highlight(sentence, value):
                errors.append(
                    f"row {row_number}: highlight {value!r} is not a complete word or phrase"
                )
            elif value not in highlights:
                highlights.append(value)
    elif parsed_highlights is not None:
        errors.append(f"row {row_number}: highlights_json must be a JSON array")

    try:
        confidence = float(str(row.get("confidence") or "").strip())
    except ValueError:
        confidence = -1.0
    if not 0.0 <= confidence <= 1.0:
        errors.append(f"row {row_number}: confidence must be between 0 and 1")

    analysis = {
        "name_zh": name,
        "formula": formula,
        "highlights": highlights,
        "confidence": confidence,
    }
    return analysis, errors


def _contains_whole_highlight(sentence: str, highlight: str) -> bool:
    start = 0
    while True:
        start = sentence.find(highlight, start)
        if start < 0:
            return False
        end = start + len(highlight)
        starts_inside_word = (
            bool(highlight)
            and _is_word_character(highlight[0])
            and start > 0
            and _is_word_character(sentence[start - 1])
        )
        ends_inside_word = (
            bool(highlight)
            and _is_word_character(highlight[-1])
            and end < len(sentence)
            and _is_word_character(sentence[end])
        )
        if not starts_inside_word and not ends_inside_word:
            return True
        start = end or start + 1


def _is_word_character(value: str) -> bool:
    return value.isalnum() or value in {"'", "’"}


def _unique_example_records(entries: Iterable[dict]) -> Dict[str, dict]:
    entry_list = list(entries)
    formal_entries = [entry for entry in entry_list if not _is_hard_words_entry(entry)]
    hard_word_entries = [entry for entry in entry_list if _is_hard_words_entry(entry)]
    records: Dict[str, dict] = {}

    for entry in formal_entries + hard_word_entries:
        for example_index in (1, 2):
            sentence = _example_text(entry, example_index)
            if not sentence:
                continue
            key = sentence_key(sentence)
            records.setdefault(
                key,
                {
                    "sentence_key": key,
                    "source_file": _source_name(entry),
                    "source_id": str(entry.get("id") or "").strip(),
                    "word": str(entry.get("word") or "").strip(),
                    "example_number": str(example_index),
                    "example_en": sentence,
                },
            )
    return records


def _pending_row(record: dict) -> dict:
    row = dict(record)
    row.update(
        {
            "tense_name_zh": "",
            "formula": "",
            "highlights_json": "",
            "confidence": "",
            "reviewed_at": "",
        }
    )
    return row


def _annotation_row(record: dict, analysis: dict) -> dict:
    row = dict(record)
    row.update(
        {
            "tense_name_zh": analysis["name_zh"],
            "formula": analysis["formula"],
            "highlights_json": json.dumps(analysis["highlights"], ensure_ascii=False),
            "confidence": f"{analysis['confidence']:.2f}",
            "reviewed_at": date.today().isoformat(),
        }
    )
    return row


def _write_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    with temporary_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=ANNOTATION_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary_path, path)


def _example_text(entry: dict, example_index: int) -> str:
    return str(entry.get(f"example_{example_index}_en") or "").strip()


def _source_name(entry: dict) -> str:
    source = str(entry.get("_source_file") or "")
    if "\\" in source:
        return PureWindowsPath(source).name
    return Path(source).name


def _is_hard_words_entry(entry: dict) -> bool:
    return _source_name(entry).casefold() == "hard_words.csv"


def _format_validation_errors(errors: list[str]) -> str:
    preview = "\n".join(f"- {error}" for error in errors[:20])
    remainder = len(errors) - 20
    if remainder > 0:
        preview += f"\n- ... and {remainder} more errors"
    return f"Invalid tense annotations:\n{preview}"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage manually reviewed tense annotations.")
    parser.add_argument(
        "--vocabulary-dir",
        type=Path,
        default=DEFAULT_SETTINGS.vocabulary_dir,
        help="Folder containing chapter vocabulary CSV files.",
    )
    parser.add_argument(
        "--annotations",
        type=Path,
        default=DEFAULT_SETTINGS.tense_annotations_path,
        help="Reviewed tense annotation CSV.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    export_parser = subparsers.add_parser("export-pending", help="Export examples missing annotations.")
    export_parser.add_argument(
        "--output",
        type=Path,
        default=Path("tense_review") / "pending_tense_examples.csv",
    )

    import_parser = subparsers.add_parser("import", help="Validate and merge completed ChatGPT CSV.")
    import_parser.add_argument("completed_csv", type=Path)

    validate_parser = subparsers.add_parser("validate", help="Validate annotation rows and coverage.")
    validate_parser.add_argument("--require-complete", action="store_true")
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    # Annotation coverage includes every source row, even when the website
    # intentionally hides a repeated word from a later chapter.
    entries = load_vocabulary(args.vocabulary_dir, deduplicate_words=False)

    if args.command == "export-pending":
        count = export_pending_annotations(entries, args.annotations, args.output)
        print(f"Exported {count} pending examples to {args.output}")
        return

    if args.command == "import":
        count = import_completed_annotations(args.completed_csv, args.annotations, entries)
        print(f"Imported {count} reviewed examples into {args.annotations}")
        return

    validation, missing = validate_annotation_coverage(entries, args.annotations)
    reports = validate_annotations_three_passes(entries, args.annotations)
    for report in reports:
        print(
            f"Pass {report['pass']} ({report['name']}): "
            f"checked {report['checked']}, errors {len(report['errors'])}."
        )
        for error in report["errors"][:20]:
            print(f"- {error}")
    errors = [error for report in reports for error in report["errors"]]
    if validation.errors:
        raise SystemExit(_format_validation_errors(validation.errors))
    print(f"Validated {len(validation.annotations)} tense annotations.")
    print(f"Missing {len(missing)} of {count_unique_examples(entries)} unique examples.")
    if args.require_complete and errors:
        raise SystemExit("Tense annotation three-pass validation failed.")


if __name__ == "__main__":
    main()
