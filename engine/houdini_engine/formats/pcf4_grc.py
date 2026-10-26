"""Textos de interfaz de PCF 4.0/4.5 — ficheros `.GRC` ("GFX Resource file").

Ingeniería inversa confirmada con FUTBOL_RELOAD. Estructura:
- Cabecera ASCII terminada en **0x1A**.
- Después, objetos de interfaz. Los que llevan texto van precedidos de un descriptor de
  **12 bytes** (6×u16 LE): `tipo, param1, param2, x, y, longitud`, y luego el texto CIFRADO.
- **Cifrado (simétrico):** `claro[i] = cif[i] XOR ((0xC0 + longitud + i) & 0xFF)`.

El parser ESCANEA buscando textos "plausibles" (ASCII en mayúsculas + dígitos + signos), que
es lo que separa las cadenas reales del ruido binario. Al editar, el texto se rellena con
espacios o se recorta a la longitud original → el fichero conserva su tamaño (offsets intactos).
"""
from __future__ import annotations

_SIGNOS = set(" .,:;-/()%'?!+*<>=&@#\"")


def _u16(d: bytes, o: int) -> int:
    return d[o] | (d[o + 1] << 8)


def _cipher(data: bytes) -> bytes:
    n = len(data)
    return bytes((data[i] ^ ((0xC0 + n + i) & 0xFF)) for i in range(n))


def _plausible(s: str) -> bool:
    if len(s) < 3:
        return False
    letras = 0
    for c in s:
        u = ord(c)
        if (ord("A") <= u <= ord("Z")) or (ord("0") <= u <= ord("9")) or u == 0xD1:  # Ñ
            letras += 1
        elif c not in _SIGNOS:
            return False
    return letras >= max(3, len(s) - 2)


def read_texts(data: bytes) -> list[dict]:
    """Lista de textos: [{offset, tipo, x, y, length, text}], en orden de aparición."""
    out: list[dict] = []
    cab = data.find(b"\x1a")
    if cab < 0:
        return out
    off = cab + 1 + 12
    n = len(data)
    while off < n - 1:
        length = _u16(data, off - 2)
        if 2 <= length <= 60 and off + length <= n:
            s = _cipher(data[off:off + length]).decode("latin-1")
            if _plausible(s):
                out.append({
                    "offset": off,
                    "tipo": _u16(data, off - 12),
                    "x": _u16(data, off - 6),
                    "y": _u16(data, off - 4),
                    "length": length,
                    "text": s.rstrip(),
                })
                off += length + 12
                continue
        off += 1
    return out


def write_text(data: bytearray, offset: int, length: int, new_text: str) -> None:
    """Reescribe (in-place) el texto en `offset`, respetando `length` (rellena/recorta)."""
    s = new_text.upper()[:length].ljust(length)
    cif = _cipher(s.encode("latin-1", "replace"))
    data[offset:offset + length] = cif


def apply_edits(data: bytes, edits: dict[int, str]) -> bytes:
    """Devuelve el `.GRC` con los textos editados (`{offset: nuevo_texto}`). Tamaño intacto."""
    buf = bytearray(data)
    texts = {t["offset"]: t for t in read_texts(data)}
    for off, new in edits.items():
        t = texts.get(int(off))
        if t:
            write_text(buf, t["offset"], t["length"], new)
    return bytes(buf)
