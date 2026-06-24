import re


DISPLAY_ABBREVIATIONS = [
    (re.compile(r"(?<!\()MIL-STD-461\b"), "Military Standard 461 (MIL-STD-461)"),
    (re.compile(r"(?<!\()\bEMC\b"), "Electromagnetic Compatibility (EMC)"),
    (re.compile(r"(?<!\()\bEMS\b"), "Electromagnetic Susceptibility (EMS)"),
    (re.compile(r"(?<!\()\bE3\b"), "Electromagnetic Environmental Effects (E3)"),
    (re.compile(r"(?<!\()\bEPDS\b"), "Electronic Power Distribution System (EPDS)"),
]

SPEECH_ABBREVIATIONS = [
    (re.compile(r"\bMilitary Standard 461 \(MIL-STD-461\)|\bMIL-STD-461\b"), "Military Standard 461"),
    (re.compile(r"\bElectromagnetic Compatibility \(EMC\)|\bEMC\b"), "Electromagnetic Compatibility"),
    (re.compile(r"\bElectromagnetic Susceptibility \(EMS\)|\bEMS\b"), "Electromagnetic Susceptibility"),
    (re.compile(r"\bElectromagnetic Environmental Effects \(E3\)|\bE3\b"), "Electromagnetic Environmental Effects"),
    (re.compile(r"\bElectronic Power Distribution System \(EPDS\)|\bEPDS\b"), "Electronic Power Distribution System"),
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
