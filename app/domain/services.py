import re

# =========================
# DOMAIN LOGIC (Pure Python)
# =========================

HN_PLATE_RE = re.compile(r"([A-Z]{3})\s*([0-9]{4})")

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

LETTER_FIRST_FIX = {
    "I": "T",
    "L": "T",
    "1": "T",
}

def _fix_first_letter(s: str) -> str:
    if s and s[0] in LETTER_FIRST_FIX:
        return LETTER_FIRST_FIX[s[0]] + s[1:]
    return s


def normalize_hn_plate(raw_text: str) -> str:
    """
    Extracts Honduras plate: AAA#### -> 'AAA 1234'.
    Applies position-aware letter/digit corrections.
    """
    cleaned = clean_alnum_upper(raw_text)
    if not cleaned:
        return ""

    # Try fixing first letter confusion (I/L -> T) for trucks
    cleaned_first_fixed = _fix_first_letter(cleaned)

    # Direct match
    m = HN_PLATE_RE.search(cleaned)
    if not m:
        m = HN_PLATE_RE.search(cleaned_first_fixed)
    if m:
        letters = m.group(1)
        digits = m.group(2)
        return f"{letters} {digits}"

    # Try to salvage a 7-char window
    if len(cleaned) < 7:
        cleaned = cleaned_first_fixed
        if len(cleaned) < 7:
            return ""

    for i in range(0, len(cleaned) - 6):
        chunk = cleaned[i:i + 7]  # 3 letters + 4 digits
        # Apply first-letter correction on the window
        chunk = _fix_first_letter(chunk)
        lpart = chunk[:3].translate(LETTER_FIX)
        dpart = chunk[3:].translate(DIGIT_FIX)

        if re.fullmatch(r"[A-Z]{3}", lpart) and re.fullmatch(r"\d{4}", dpart):
            return f"{lpart} {dpart}"

    return ""


def parse_dispatch_info(raw_text: str) -> dict:
    """
    Extracts key fields from OCR'd driver dispatch text.
    Returns a dict with cleaned values (empty strings if missing).
    """
    lines = [ln.strip() for ln in (raw_text or "").splitlines() if ln.strip()]

    def match_field(pattern: str):
        for ln in lines:
            m = re.search(pattern, ln, re.IGNORECASE)
            if m:
                groups = [g for g in m.groups() if g]
                value = groups[-1] if groups else m.group(1)
                return value.strip(" -:_,.;")
        return ""

    def normalize_phone(raw: str) -> str:
        digits = re.sub(r"\D+", "", raw or "")
        if len(digits) == 8:
            return f"{digits[:4]}-{digits[4:]}"
        if len(digits) == 9:  # sometimes leading digit for country
            return f"{digits[1:5]}-{digits[5:]}"
        return raw.strip()

    dispatch_time = ""
    for ln in lines:
        m = re.search(r"(\d{1,2}:\d{2})", ln)
        if "despacho" in ln.lower() and m:
            dispatch_time = m.group(1)
            break

    year_raw = match_field(r"a(?:n|\u00f1)o[:\s]+([0-9]{4})")
    year_int = int(year_raw) if year_raw.isdigit() else None

    phone_raw = match_field(r"tel(?:e|\u00e9)fono[:\s-]+(.+)")

    motorista_val = match_field(r"motorista[:\s]+(.+)")
    # Evita capturar la frase de la cabecera "para despacho..."
    if "despacho" in motorista_val.lower():
        motorista_val = ""
    if not motorista_val:
        for ln in lines:
            if ln.lower().startswith("motorista"):
                parts = ln.split(maxsplit=1)
                if len(parts) == 2:
                    motorista_val = parts[1].strip(" -:_,.;")
                break

    licencia_val = match_field(r"licen[cs]ia[:\s]+(.+)")
    licencia_val = re.sub(r"[^0-9-]", "", licencia_val)

    placa_val = match_field(r"placa[:\s]+(.+)")
    placa_val = placa_val.replace(",", "").strip()

    rtn_val = match_field(r"(?:rtn|rin)[:\s]+(.+)")
    rtn_val = re.sub(r"[^\d]", "", rtn_val)

    # Build payload with Spanish keys as requested
    return {
        "horaDespacho": dispatch_time,
        "motorista": motorista_val,
        "licencia": licencia_val,
        "placa": placa_val,
        "telefono": normalize_phone(phone_raw),
        "color": match_field(r"color[:\s]+(.+)"),
        "marca": match_field(r"marca[:\s]+(.+)"),
        "anio": year_int or year_raw,
        "motor": match_field(r"motor[:\s]+(.+)"),
        "vin": match_field(r"(?:chasis\s*/?\s*vin|chasis|vin)[:\s]+(.+)"),
        "codigo": match_field(r"c(?:o|\u00f3)digo[:\s]+(.+)"),
        "transporte": match_field(r"transporte[:\s]+(.+)"),
        "rtn": rtn_val,
        "lineas": lines,
    }
