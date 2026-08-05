import re


DISPLAY_ABBREVIATIONS = [
    (re.compile(r"(?<!\()MIL-STD-461\b"), "Military Standard 461 (MIL-STD-461)"),
    (re.compile(r"(?<!\()\bEMC\b"), "Electromagnetic Compatibility (EMC)"),
    (re.compile(r"(?<!\()\bEMS\b"), "Electromagnetic Susceptibility (EMS)"),
    (re.compile(r"(?<!\()\bE3\b"), "Electromagnetic Environmental Effects (E3)"),
    (re.compile(r"(?<!\()\bEPDS\b"), "Electronic Power Distribution System (EPDS)"),
    (re.compile(r"(?<!\()\bDAQ\b"), "Data Acquisition (DAQ)"),
    (re.compile(r"(?<!\()\bHERO\b"), "Hazards of Electromagnetic Radiation to Ordnance (HERO)"),
    (re.compile(r"(?<!\()\bEEDs\b"), "Electro-Explosive Devices (EEDs)"),
    (re.compile(r"(?<!\()\bEED\b"), "Electro-Explosive Device (EED)"),
    (re.compile(r"(?<!\()\bFTS\b"), "Flight Termination System (FTS)"),
    (re.compile(r"(?<!\()\bGNSS\b"), "Global Navigation Satellite System (GNSS)"),
    (re.compile(r"(?<!\()\bEME\b"), "Electromagnetic Environment (EME)"),
    (re.compile(r"(?<!\()\bEMI\b"), "Electromagnetic Interference (EMI)"),
    (re.compile(r"(?<!\()\bP-static\b", re.IGNORECASE), "Precipitation Static (P-static)"),
]

SPEECH_ABBREVIATIONS = [
    (re.compile(r"\bMilitary Standard 461 \(MIL-STD-461\)|\bMIL-STD-461\b"), "Military Standard 461"),
    (re.compile(r"\bElectromagnetic Compatibility \(EMC\)|\bEMC\b"), "Electromagnetic Compatibility"),
    (re.compile(r"\bElectromagnetic Susceptibility \(EMS\)|\bEMS\b"), "Electromagnetic Susceptibility"),
    (re.compile(r"\bElectromagnetic Environmental Effects \(E3\)|\bE3\b"), "Electromagnetic Environmental Effects"),
    (re.compile(r"\bElectronic Power Distribution System \(EPDS\)|\bEPDS\b"), "Electronic Power Distribution System"),
    (re.compile(r"\bData Acquisition \(DAQ\)|\bDAQ\b"), "Data Acquisition"),
    (
        re.compile(r"\bHazards of Electromagnetic Radiation to Ordnance \(HERO\)|\bHERO\b"),
        "Hazards of Electromagnetic Radiation to Ordnance",
    ),
    (re.compile(r"\bElectro-Explosive Devices \(EEDs\)|\bEEDs\b"), "Electro-Explosive Devices"),
    (re.compile(r"\bElectro-Explosive Device \(EED\)|\bEED\b"), "Electro-Explosive Device"),
    (re.compile(r"\bFlight Termination System \(FTS\)|\bFTS\b"), "Flight Termination System"),
    (
        re.compile(r"\bGlobal Navigation Satellite System \(GNSS\)|\bGNSS\b"),
        "Global Navigation Satellite System",
    ),
    (re.compile(r"\bElectromagnetic Effects \(EME\)"), "Electromagnetic Effects"),
    (
        re.compile(r"\bElectromagnetic Environment \(EME\)|\bEME\b"),
        "Electromagnetic Environment",
    ),
    (
        re.compile(r"\bElectromagnetic Interference \(EMI\)|\bEMI\b"),
        "Electromagnetic Interference",
    ),
    (
        re.compile(r"\bPrecipitation Static \(P-static\)|\bP-static\b", re.IGNORECASE),
        "Precipitation Static",
    ),
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
        re.compile(
            r"\bHazards of Electromagnetic Radiation to Ordnance(?:\s*[\(（]HERO[\)）])?",
            re.IGNORECASE,
        ),
        "HERO",
    ),
    (
        re.compile(r"\bElectro-Explosive Devices(?:\s*[\(（]EEDs[\)）])?", re.IGNORECASE),
        "EEDs",
    ),
    (
        re.compile(r"\bElectro-Explosive Device(?:\s*[\(（]EED[\)）])?", re.IGNORECASE),
        "EED",
    ),
    (
        re.compile(r"\bFlight Termination System(?:\s*[\(（]FTS[\)）])?", re.IGNORECASE),
        "FTS",
    ),
    (
        re.compile(
            r"\bGlobal Navigation Satellite System(?:\s*[\(（]GNSS[\)）])?",
            re.IGNORECASE,
        ),
        "GNSS",
    ),
    (
        re.compile(r"\bElectromagnetic Environment(?:\s*[\(（]EME[\)）])?", re.IGNORECASE),
        "EME",
    ),
    (
        re.compile(r"\bElectromagnetic Effects(?:\s*[\(（]EME[\)）])?", re.IGNORECASE),
        "EME",
    ),
    (
        re.compile(r"\bElectromagnetic Interference(?:\s*[\(（]EMI[\)）])?", re.IGNORECASE),
        "EMI",
    ),
    (
        re.compile(r"\bPrecipitation Static(?:\s*[\(（]P-static[\)）])?", re.IGNORECASE),
        "P-static",
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
