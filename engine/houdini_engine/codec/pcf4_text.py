"""Códec de texto de PCF 4.0 / 4.5.

Distinto de v5/v6 (que usa XOR 0x61 + longitudes u16 LE). En la 4.x:
- Cada carácter: `XOR 0x61`; si el resultado tiene el bit 0x80, es un índice a la
  tabla `CARACTERES` (acentos/ñ/ç…). Ref: `bbdd_futbol.cpp` de FUTBOL_RELOAD.
- Cadenas: prefijo de longitud de **1 byte (u8)** + bytes codificados.
- Textos largos de BBDD (comentario del jugador, info/declaraciones del entrenador):
  formato TROCEADO → `[num_chunks u8]` + `num_chunks+1` trozos `[len u8][bytes]`.

Verificado byte a byte contra los DBC reales de la 4.0.
"""
from __future__ import annotations

# Tabla de caracteres especiales (índice 0..47 → byte latin-1). Los dos 0x00 son huecos sin
# usar. Es la zona alta del Code Page 437 de IBM (Ç, ü, é, â… = CP437 0x80+), estándar público
# de facto desde 1981. Verificada además contra los DBC reales.
CARACTERES = [
    0xC7, 0xFC, 0xE9, 0xE2, 0xE4, 0xE0, 0xE5, 0xE7, 0xEA, 0xEB,
    0xE8, 0xEF, 0xEE, 0xEC, 0xC4, 0xC5, 0xC9, 0xE6, 0xC6, 0xF4,
    0xF6, 0xF2, 0xFB, 0xF9, 0xFF, 0xD6, 0xDC, 0xA2, 0xA3, 0xA5,
    0x00, 0x00, 0xE1, 0xED, 0xF3, 0xFA, 0xF1, 0xD1, 0xAA, 0xBA,
    0xBF, 0x81, 0xAC, 0xBD, 0xBC, 0xA1, 0xAB, 0xBB,
]
# Mapa inverso latin-1 → índice (para codificar). El primero gana en caso de repes.
_LATIN_TO_IDX: dict[int, int] = {}
for _i, _b in enumerate(CARACTERES):
    if _b and _b not in _LATIN_TO_IDX:
        _LATIN_TO_IDX[_b] = _i


# Área de uso privado Unicode para bytes "basura" que no mapean a ningún carácter:
# los guardamos como chr(0xE000|byte) para poder re-codificarlos EXACTOS (lossless).
_PUA = 0xE000


def decode_char(val: int) -> str:
    """Descodifica 1 byte a carácter. Lossless: los bytes desconocidos se guardan
    en el área de uso privado para poder re-codificarlos exactos."""
    raw = val
    val ^= 0x61
    if val & 0x80:
        idx = val & ~0x80
        if idx < 48 and CARACTERES[idx]:
            return chr(CARACTERES[idx])
        return chr(_PUA | raw)          # byte sin mapa → sentinela lossless
    return chr(val)


def encode_char(ch: str) -> int:
    """Codifica 1 carácter a byte. Inversa EXACTA de decode_char."""
    o = ord(ch)
    if _PUA <= o <= _PUA | 0xFF:         # sentinela → byte original
        return o & 0xFF
    b = o & 0xFF
    idx = _LATIN_TO_IDX.get(b)
    if idx is not None:
        return (idx | 0x80) ^ 0x61
    return b ^ 0x61


def decode_str(data: bytes, off: int) -> tuple[str, int]:
    """Cadena con prefijo u8. Devuelve (texto, offset_siguiente)."""
    ln = data[off]
    s = "".join(decode_char(data[off + 1 + i]) for i in range(ln))
    return s, off + 1 + ln


def encode_str(s: str) -> bytes:
    """Cadena a bytes: [len u8][codificado]. Máx 255 caracteres."""
    s = s[:255]
    out = bytearray([len(s)])
    for ch in s:
        out.append(encode_char(ch))
    return bytes(out)


import unicodedata  # noqa: E402

# Letras especiales sin descomposición NFKD (Ø, Ł, ß…) → equivalente representable.
_TRANSLIT = {
    "Ø": "O", "ø": "o", "Ł": "L", "ł": "l", "Đ": "D", "đ": "d", "Ð": "D", "ð": "d",
    "Þ": "Th", "þ": "th", "ß": "ss", "Œ": "OE", "œ": "oe", "ı": "i", "İ": "I",
    "Ħ": "H", "ħ": "h", "Ŋ": "N", "ŋ": "n", "'": "'", "’": "'", "‘": "'", "–": "-",
    # puntuación tipográfica de las fuentes web (2026-08-16): sin esto las comillas
    # curvas de los apodos y el bullet se PERDÍAN (Vini “Vini” → Vini Vini).
    "“": '"', "”": '"', "„": '"', "‟": '"', "«": '"', "»": '"', "″": '"',
    "‚": "'", "‛": "'", "′": "'", "—": "-", "‑": "-", "‒": "-", "―": "-",
    "•": "-", "€": "E", "™": "", " ": " ", "​": "",
}


def _representable(ch: str) -> bool:
    """¿El carácter sobrevive un round-trip por el códec de PCF4?"""
    return decode_char(encode_char(ch)) == ch and (0x20 <= ord(ch) < 0x7F
                                                    or 0xA0 <= ord(ch) < 0x100)


def sanitize(s: str) -> str:
    """Adapta un texto (importado de fuera) al charset de PCF 4.x: conserva
    los caracteres representables (incluidos á é í ó ú ü ñ ç…) y translitera el
    resto a su equivalente ASCII (Ø→O, ć→c, Ø…). Evita que un carácter no
    soportado corrompa el bloque al re-parsear."""
    out = []
    for ch in s:
        if _representable(ch):
            out.append(ch)
            continue
        if ch in _TRANSLIT:
            out.append(_TRANSLIT[ch])
            continue
        # quitar diacríticos no soportados (ć→c, ž→z, ș→s…)
        base = "".join(c for c in unicodedata.normalize("NFKD", ch)
                       if not unicodedata.combining(c))
        out.append("".join(c for c in base if _representable(c)))
    return "".join(out)


def decode_chunked(data: bytes, off: int) -> tuple[str, int]:
    """Texto BBDD troceado: [num_chunks u8] + (num_chunks+1) trozos [len u8][bytes].
    Devuelve (texto_completo, offset_siguiente)."""
    num = data[off]
    off += 1
    parts: list[str] = []
    for _ in range(num + 1):
        ln = data[off]
        off += 1
        parts.append("".join(decode_char(data[off + i]) for i in range(ln)))
        off += ln
    return "".join(parts), off


def encode_chunked(s: str) -> bytes:
    """Texto largo a formato troceado (trozos de 16, como FUTBOL_RELOAD)."""
    chunk = 16
    while len(s) // chunk > 254:
        chunk += 1
    num = len(s) // chunk
    out = bytearray([num])
    for k in range(num + 1):
        sub = s[k * chunk:(k + 1) * chunk]
        out.append(len(sub))
        for ch in sub:
            out.append(encode_char(ch))
    return bytes(out)
