import re


DISPLAY_ABBREVIATIONS = [
    (re.compile(r"(?<!\()MIL-STD-461\b"), "Military Standard 461 (MIL-STD-461)"),
    (re.compile(r"(?<!\()\bEMC\b"), "Electromagnetic Compatibility (EMC)"),
    (re.compile(r"(?<!\()\bEMS\b"), "Electromagnetic Susceptibility (EMS)"),
    (re.compile(r"(?<!\()\bE3\b"), "Electromagnetic Environmental Effects (E3)"),
    (re.compile(r"(?<!\()\bEPDS\b"), "Electronic Power Distribution System (EPDS)"),
    (re.compile(r"(?<!\()\bDAQ\b"), "Data Acquisition (DAQ)"),
]

SPEECH_ABBREVIATIONS = [
    (re.compile(r"\bMilitary Standard 461 \(MIL-STD-461\)|\bMIL-STD-461\b"), "Military Standard 461"),
    (re.compile(r"\bElectromagnetic Compatibility \(EMC\)|\bEMC\b"), "Electromagnetic Compatibility"),
    (re.compile(r"\bElectromagnetic Susceptibility \(EMS\)|\bEMS\b"), "Electromagnetic Susceptibility"),
    (re.compile(r"\bElectromagnetic Environmental Effects \(E3\)|\bE3\b"), "Electromagnetic Environmental Effects"),
    (re.compile(r"\bElectronic Power Distribution System \(EPDS\)|\bEPDS\b"), "Electronic Power Distribution System"),
    (re.compile(r"\bData Acquisition \(DAQ\)|\bDAQ\b"), "Data Acquisition"),
]

CHINESE_FIELD_ABBREVIATIONS = [
    (
        re.compile(r"\bMilitary Standard 461(?:\s*[\(（]MIL-STD-461[\)）])?", re.IGNORECASE),
        "MIL-STD-461",
    ),
    (
        re.compile(r"\bElectromagnetic Compatibility(?:\s*[\(（]EMC[\)）])?", re.IGNORECASE),
        "EMC",
    ),
    (
        re.compile(r"\bElectromagnetic Susceptibility(?:\s*[\(（]EMS[\)）])?", re.IGNORECASE),
        "EMS",
    ),
    (
        re.compile(r"\bElectromagnetic Environmental Effects(?:\s*[\(（]E3[\)）])?", re.IGNORECASE),
        "E3",
    ),
    (
        re.compile(r"\bElectronic Power Distribution System(?:\s*[\(（]EPDS[\)）])?", re.IGNORECASE),
        "EPDS",
    ),
    (
        re.compile(r"\bData Acquisition(?:\s*[\(（]DAQ[\)）])?", re.IGNORECASE),
        "DAQ",
    ),
    (
        re.compile(r"\bRadio Frequency(?:\s*[\(（]RF[\)）])?", re.IGNORECASE),
        "RF",
    ),
]


def expand_abbreviations_for_display(text: str) -> str:
    value = str(text or "").strip()
    for pattern, replacement in DISPLAY_ABBREVIATIONS:
        value = pattern.sub(replacement, value)
    return value


def expand_abbreviations_for_speech(text: str) -> str:
    value = str(text or "").strip()
    for pattern, replacement in SPEECH_ABBREVIATIONS:
        value = pattern.sub(replacement, value)
    return value


def abbreviate_english_terms_in_chinese(text: str) -> str:
    """Keep English technical names compact inside Chinese display and speech."""
    value = str(text or "").strip()
    for pattern, replacement in CHINESE_FIELD_ABBREVIATIONS:
        value = pattern.sub(replacement, value)
    return value
