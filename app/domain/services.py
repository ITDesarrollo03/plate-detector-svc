import re

# =========================
# DOMAIN LOGIC (Pure Python)
# =========================

HN_PLATE_RE = re.compile(r'([A-Z]{3})\s*([0-9]{4})')

LETTER_FIX = str.maketrans({
    "0": "O",
    "1": "I",
    "2": "Z",
    "5": "S",
    "6": "G",
    "8": "B",
})

DIGIT_FIX = str.maketrans({
    "O": "0",
    "Q": "0",
    "D": "0",
    "I": "1",
    "L": "1",
    "Z": "2",
    "S": "5",
    "G": "6",
    "B": "8",
})


def clean_alnum_upper(s: str) -> str:
    return "".join(ch for ch in (s or "").upper() if ch.isalnum())


def normalize_hn_plate(raw_text: str) -> str:
    """
    Extrae/normaliza placa Honduras: AAA####  -> 'AAA 1234'
    Aplica correcciones de confusiones letras/números según posición.
    """
    cleaned = clean_alnum_upper(raw_text)
    if not cleaned:
        return ""

    # 1) Intenta encontrar patrón directamente dentro del texto
    m = HN_PLATE_RE.search(cleaned)
    if m:
        letters = m.group(1)
        digits = m.group(2)
        return f"{letters} {digits}"

    # 2) Si no match, intenta rescatar: toma los primeros 7 alfanum si hay
    # (útil cuando tesseract mete basura antes/después)
    if len(cleaned) < 7:
        return ""

    # Busca cualquier ventana de 7 chars que pueda convertirse
    for i in range(0, len(cleaned) - 6):
        chunk = cleaned[i:i+7]  # 3 + 4
        lpart = chunk[:3]
        dpart = chunk[3:]

        # Corrige por posición:
        # primeras 3 deben ser letras
        lpart = lpart.translate(LETTER_FIX)
        # últimas 4 deben ser dígitos
        dpart = dpart.translate(DIGIT_FIX)

        if re.fullmatch(r"[A-Z]{3}", lpart) and re.fullmatch(r"\d{4}", dpart):
            return f"{lpart} {dpart}"

    return ""
