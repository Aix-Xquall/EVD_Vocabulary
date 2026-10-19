"""Replace handbook-glossary templates with chapter-context examples.

Run without arguments to preview; pass --apply to update vocabulary and annotations.
No speech synthesis is performed by this migration.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "vocabulary"
ANNOTATION_DIR = ROOT / "annotations"
TEMPLATE_PREFIXES = (
    'The handbook uses "',
    'The handbook discusses "',
    'The handbook discusses the term "',
    'The term "',
    "The handbook helps ",
)
SENTENCES = {
    "_01_": (
        ("The design team considers the {word} during requirements development.",
         "設計團隊在需求開發期間會考量{meaning}。", "considers"),
        ("The requirements review records the {word} before design approval.",
         "設計核准前，需求審查會記錄{meaning}。", "records"),
    ),
    "_04_": (
        ("The electrical engineer evaluates the {word} while designing the bond path.",
         "電氣工程師在設計接合路徑時會評估{meaning}。", "evaluates"),
        ("The design review checks the {word} against the bonding requirement.",
         "設計審查會依接合要求檢查{meaning}。", "checks"),
    ),
    "_05-1_": (
        ("The installer checks the {word} before completing the bond joint.",
         "安裝人員在完成接合處前會檢查{meaning}。", "checks"),
        ("The assembly record identifies the {word} used at the joint.",
         "組裝紀錄會註明接合處使用的{meaning}。", "identifies"),
    ),
    "_05-2_": (
        ("The technician evaluates the {word} before preparing the bond surface.",
         "技術人員在處理接合表面前會評估{meaning}。", "evaluates"),
        ("The surface inspection checks the {word} before sealing the joint.",
         "密封接合處前，表面檢查會確認{meaning}。", "checks"),
    ),
    "_05-3_": (
        ("The enclosure design accounts for the {word}.",
         "機箱設計會考量{meaning}。", "accounts"),
        ("The integration team checks the {word} during assembly.",
         "整合團隊在組裝期間會檢查{meaning}。", "checks"),
    ),
    "_05-4_": (
        ("The verification plan includes the {word}.",
         "驗證計畫會納入{meaning}。", "includes"),
        ("The inspector checks the {word} before accepting the assembly.",
         "驗收組件前，檢驗人員會檢查{meaning}。", "checks"),
    ),
    "_06_": (
        ("The reviewer checks the {word} before releasing the drawing.",
         "圖面發行前，審查人員會檢查{meaning}。", "checks"),
        ("The drawing identifies the {word} needed for bonding.",
         "圖面會標明接合作業所需的{meaning}。", "identifies"),
    ),
    "_07_": (
        ("The inspector checks the {word} during the bonding inspection.",
         "檢驗人員在接合檢查時會確認{meaning}。", "checks"),
        ("The checklist records the {word} for final acceptance.",
         "檢查表會記錄{meaning}供最終驗收。", "records"),
    ),
    "_08_": (
        ("The engineer uses the {word} when describing the electrical bond.",
         "工程師描述電氣接合時會使用{meaning}。", "uses"),
        ("The design review defines the {word} before testing.",
         "測試前，設計審查會定義{meaning}。", "defines"),
    ),
    "_09_": (
        ("The technician evaluates {word} before cleaning the bond surface.",
         "技術人員在清潔接合表面前會評估{meaning}。", "evaluates"),
        ("The cleaning procedure specifies the {word} for this material.",
         "清潔程序會針對此材料指定{meaning}。", "specifies"),
    ),
}
CUSTOM = {
    "specific": (
        ("Specific bonding requirements apply to each hardware item.",
         "每項硬體都適用特定的接合要求。", "apply"),
        ("The program document defines specific project requirements.",
         "計畫文件會定義特定專案的要求。", "defines"),
    ),
    "to fay": (
        ("The two metal surfaces need to fay closely before the fasteners are tightened.",
         "在緊固件鎖緊前，兩個金屬表面須緊密貼合。", "need"),
        ("The installer prepares the mating surfaces to fay without a visible gap.",
         "安裝人員會準備配合面，使其接合時沒有可見間隙。", "prepares"),
    ),
    "phase angle": (
        ("The phase angle changes as the bond impedance changes with frequency.",
         "接合阻抗隨頻率變化時，相位角也會改變。", "changes"),
        ("The engineer records the phase angle with the impedance measurement.",
         "工程師會將相位角與阻抗量測結果一起記錄。", "records"),
    ),
    "complex quantity": (
        ("Impedance is a complex quantity with magnitude and phase.",
         "阻抗是具有大小與相位的複數量。", "is"),
        ("The engineer records the complex quantity in the test report.",
         "工程師會在測試報告中記錄複數量。", "records"),
    ),
    "imaginary part": (
        ("The imaginary part of impedance changes with frequency.",
         "阻抗的虛部會隨頻率改變。", "changes"),
        ("The engineer plots the imaginary part beside the real part.",
         "工程師會將虛部與實部一起繪圖。", "plots"),
    ),
    "zero reference potential": (
        ("The circuit model defines a zero reference potential.",
         "電路模型會定義零參考電位。", "defines"),
        ("The engineer measures voltage relative to the zero reference potential.",
         "工程師會相對於零參考電位量測電壓。", "measures"),
    ),
    "primary structure": (
        ("The primary structure carries the main vehicle loads.",
         "主結構承受載具的主要載荷。", "carries"),
        ("The bonding path connects the equipment to the primary structure.",
         "接合路徑會將設備連接至主結構。", "connects"),
    ),
    "secondary structure": (
        ("The secondary structure supports the equipment panel.",
         "次結構支撐設備面板。", "supports"),
        ("The engineer checks the bond to the secondary structure.",
         "工程師會檢查與次結構的接合。", "checks"),
    ),
    "tertiary structure": (
        ("The tertiary structure supports local hardware.",
         "第三級結構支撐局部硬體。", "supports"),
        ("The drawing identifies the bond to the tertiary structure.",
         "圖面會標示與第三級結構的接合。", "identifies"),
    ),
    "drawing release": (
        ("The drawing release follows approval of the bonding details.",
         "圖面發行會在接合細節獲核准後進行。", "follows"),
        ("The reviewer confirms every bond callout before drawing release.",
         "圖面發行前，審查人員會確認每項接合標註。", "confirms"),
    ),
}


def sentence_key(sentence: str) -> str:
    return hashlib.sha256(" ".join(sentence.strip().split()).encode("utf-8")).hexdigest()


def csv_lines(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return file.readlines()


def parse_line(line: str) -> list[str]:
    return next(csv.reader([line]))


def render_line(values: list[str], original: str) -> str:
    ending = "\r\n" if original.endswith("\r\n") else "\n"
    buffer = io.StringIO(newline="")
    csv.writer(buffer, lineterminator=ending).writerow(values)
    return buffer.getvalue()


def replacement(source_name: str, row: dict[str, str], number: int) -> tuple[str, str, str]:
    word = row["word"]
    if word in CUSTOM:
        return CUSTOM[word][number - 1]
    chapter = next((key for key in SENTENCES if key in source_name), None)
    if chapter is None:
        raise ValueError(f"No chapter template for {source_name}")
    english, chinese, verb = SENTENCES[chapter][number - 1]
    meaning = row["chinese_meaning"].split("；", 1)[0].split("／", 1)[0]
    return english.format(word=word), chinese.format(meaning=meaning), verb


def migration() -> tuple[dict[Path, list[str]], dict[str, tuple[str, str]]]:
    updated: dict[Path, list[str]] = {}
    replacements: dict[str, tuple[str, str]] = {}
    for path in sorted(SOURCE_DIR.glob("MSFC-HDBK-3697*.csv")):
        lines = csv_lines(path)
        headers = parse_line(lines[0])
        result = [lines[0]]
        for line in lines[1:]:
            fields = parse_line(line)
            row = dict(zip(headers, fields, strict=True))
            changed = False
            for number in (1, 2):
                field = f"example_{number}_en"
                old = row[field]
                glossary_example = "_08_" in path.name and row["word"] in CUSTOM and (
                    old.startswith('The technician reviews "')
                    or old.startswith("The engineer uses the ")
                )
                cleaning_example = "_09_" in path.name and number == 1 and old.startswith(
                    "The technician evaluates the "
                )
                if not (old.startswith(TEMPLATE_PREFIXES) or glossary_example or cleaning_example):
                    continue
                english, chinese, verb = replacement(path.name, row, number)
                if row["word"].lower() not in english.lower():
                    raise ValueError(f"Target missing from example: {row['word']}")
                if old in replacements and replacements[old][0] != english:
                    raise ValueError(f"Conflicting replacement for {old}")
                replacements[old] = (english, verb)
                row[field] = english
                row[f"example_{number}_zh"] = chinese
                changed = True
            result.append(render_line([row[column] for column in headers], line) if changed else line)
        updated[path] = result
    return updated, replacements


def update_annotations(replacements: dict[str, tuple[str, str]]) -> dict[Path, list[str]]:
    updated = {}
    for filename in ("example_sources.csv", "tense_annotations.csv"):
        path = ANNOTATION_DIR / filename
        lines = csv_lines(path)
        headers = parse_line(lines[0])
        result = [lines[0]]
        seen = set()
        for line in lines[1:]:
            fields = parse_line(line)
            row = dict(zip(headers, fields, strict=True))
            old = row["example_en"]
            if old not in replacements:
                result.append(line)
                continue
            english, verb = replacements[old]
            row["example_en"] = english
            row["sentence_key"] = sentence_key(english)
            seen.add(old)
            if filename == "example_sources.csv":
                row["attribution"] = "主題參考"
                row["confidence"] = "0.50"
            else:
                row["tense_name_zh"] = "現在簡單式"
                row["formula"] = "S + V / V-s"
                row["highlights_json"] = json.dumps([verb], ensure_ascii=False)
                row["confidence"] = "0.90"
            result.append(render_line([row[column] for column in headers], line))
        missing = set(replacements) - seen
        if missing:
            raise ValueError(f"{filename} missing {len(missing)} source annotations")
        updated[path] = result
    return updated


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="write the migration")
    args = parser.parse_args()
    changes, replacements = migration()
    changes.update(update_annotations(replacements))
    print(f"{len(replacements)} examples in {len(changes)} files")
    if args.apply:
        for path, lines in changes.items():
            with path.open("w", encoding="utf-8-sig", newline="") as file:
                file.writelines(lines)


if __name__ == "__main__":
    main()
