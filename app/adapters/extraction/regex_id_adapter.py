import re
from app.ports.info_extractor_port import InfoExtractorPort


class RegexIdAdapter(InfoExtractorPort):
    """
    Extrae identidad (13 dígitos) y nombre completo de texto OCR.
    Pensado para DNI/Licencia de Honduras.
    """
    def extract(self, ocr_text: str) -> dict:
        raw_lines = (ocr_text or "").splitlines()
        lines = [re.sub(r"[|_;]+", " ", ln).strip() for ln in raw_lines if ln.strip()]
        text = "\n".join(lines)

        # Normaliza dígitos con correcciones típicas de OCR
        digit_fix = str.maketrans({
            "O": "0", "o": "0", "Q": "0",
            "I": "1", "l": "1", "|": "1",
            "S": "5", "s": "5",
            "B": "8",
            "G": "6", "g": "6",
        })
        fixed_text = text.translate(digit_fix)

        # Busca patrón 4-4-5 con separadores laxos (prioriza líneas que lo contengan)
        identity = ""
        pattern = re.compile(r"(\d{4})\D{0,2}(\d{4})\D{0,2}(\d{5})")
        for ln in lines:
            m = pattern.search(ln)
            if m:
                identity = "".join(m.groups())
                break
        if not identity:
            m = pattern.search(fixed_text)
            if m:
                identity = "".join(m.groups())
        if not identity:
            digits = re.sub(r"\D", "", fixed_text)
            if len(digits) >= 13:
                identity = digits[:13]
            elif len(digits) >= 11:
                identity = digits

        identity_fmt = identity
        if len(identity) == 13:
            year = identity[4:8]
            if year.startswith("4"):
                identity = identity[:4] + ("1" + year[1:]) + identity[8:]

        def strip_val(val: str) -> str:
            return re.sub(r"^[^A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+", "", val.strip(" -:_,.;"))

        # Heurísticas de nombre: usa etiquetas y el siguiente renglón
        first_name = ""
        last_name = ""
        for idx, ln in enumerate(lines):
            low = ln.lower()
            if any(k in low for k in ["nombre", "forename"]) and idx + 1 < len(lines):
                candidate = strip_val(lines[idx + 1])
                if candidate and len(candidate) > 3:
                    first_name = candidate
            if any(k in low for k in ["apellido", "surname"]) and idx + 1 < len(lines):
                candidate = strip_val(lines[idx + 1])
                if candidate and len(candidate) > 3:
                    last_name = candidate
            if first_name and last_name:
                break

        # Fallback: tomar líneas con muchas letras y pocas cifras, evitando etiquetas comunes
        if not first_name or not last_name:
            blacklist = ("nacionalidad", "fecha", "expir", "identific", "numero", "documento", "registro", "place", "birth", "nation", "hnd")
            scored = []
            for ln in lines:
                low = ln.lower()
                if any(b in low for b in blacklist):
                    continue
                letters = sum(ch.isalpha() for ch in ln)
                digits_ln = sum(ch.isdigit() for ch in ln)
                score = letters - digits_ln * 3
                scored.append((score, strip_val(ln)))
            scored.sort(reverse=True, key=lambda t: t[0])
            top = [t for t in scored if t[0] > 0][:3]
            if not first_name and top:
                first_name = top[0][1]
            if not last_name and len(top) > 1:
                last_name = top[1][1]

        full_name = " ".join(p for p in [first_name, last_name] if p).strip()
        # Limpia ruido y normaliza espacios/símbolos
        full_name = re.sub(r"[^A-Za-zÁÉÍÓÚÜÑáéíóúüñ ]", " ", full_name)
        full_name = re.sub(r"\s{2,}", " ", full_name).strip()


        return {
            "identity": identity,
            "identityFormatted": identity_fmt,
            "full_name": full_name,
            "lines": lines,
        }
