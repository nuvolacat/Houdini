"""Contenedor de audio `EF CD AB 00` de PCF 2000/2001 (`SFX/*`).

Estructura: **magic `EF CD AB 00` (4 B) + entradas auto-delimitadas concatenadas, SIN índice**.
Cada entrada es un fichero completo que se delimita solo por su propio formato:
- **WAV** (`RIFF....WAVE`): tamaño en la cabecera RIFF (chunk size + 8). Voces/ambiente/cánticos.
- **MIDI** (`MThd`): cabecera + chunks `MTrk` con su tamaño; el siguiente `MThd` marca el corte.
  Música de PCF2000 (`SFX/Musicas` = 3 MIDI).
- **MP3**: no se auto-delimita bien; se trocea por etiquetas `ID3` (cada una inicia una pista)
  además del inicio del stream. Música de PCF2001 (`SFX/Musicas` = MP3).

REEMPAQUETADO trivial: no hay índice ni offsets → `magic + concat(entradas)`. Por eso reemplazar
una entrada por otra de CUALQUIER tamaño es directo (a diferencia del PKF paginado de PCF7).
"""
from __future__ import annotations

import struct

MAGIC = b"\xef\xcd\xab\x00"


def _body(data: bytes) -> int:
    return 4 if data[:4] == MAGIC else 0


def _midi_ranges(data: bytes, start: int) -> list[tuple[int, int]]:
    offs = []
    i = start - 1
    while True:
        i = data.find(b"MThd", i + 1)
        if i < 0:
            break
        offs.append(i)
    bounds = offs + [len(data)]
    return [(offs[k], bounds[k + 1] - offs[k]) for k in range(len(offs))]


def _wav_ranges(data: bytes, start: int) -> list[tuple[int, int]]:
    out = []
    i = start - 1
    while True:
        i = data.find(b"RIFF", i + 1)
        if i < 0:
            break
        if data[i + 8:i + 12] != b"WAVE":
            continue
        size = struct.unpack_from("<I", data, i + 4)[0] + 8
        if 0 < size <= len(data) - i:
            out.append((i, size))
    return out


def _is_id3v2(data: bytes, i: int) -> bool:
    """¿Hay una cabecera ID3v2 REAL en `i`? 'ID3' + versión (2.x/3.x/4.x) + flags +
    tamaño synchsafe (4 bytes, todos <0x80). Descarta los 'ID3' que aparecen DENTRO
    del audio MP3 (bytes de datos que casan por azar)."""
    if i + 10 > len(data) or data[i:i + 3] != b"ID3":
        return False
    return data[i + 3] in (2, 3, 4) and data[i + 4] == 0 \
        and all(b < 0x80 for b in data[i + 6:i + 10])


def _mp3_ranges(data: bytes, start: int) -> list[tuple[int, int]]:
    """Troceo por cabeceras ID3v2 REALES (cada pista arranca con una) + el inicio del
    stream. ANTES cortaba en cualquier 'ID3' → un 'ID3' falso dentro del audio partía
    una canción en dos (la 1ª se cortaba y la 2ª empezaba con el resto de la 1ª). Un
    MP3 continuo sin ID3v2 real queda como UNA sola pista (correcto)."""
    cuts = [start]
    i = start
    while True:
        i = data.find(b"ID3", i + 1)
        if i < 0:
            break
        if i > cuts[-1] + 1000 and _is_id3v2(data, i):
            cuts.append(i)
    cuts.append(len(data))
    return [(cuts[k], cuts[k + 1] - cuts[k]) for k in range(len(cuts) - 1)]


def _ds1_entry_len(data: bytes, off: int) -> int:
    """Longitud EXACTA de una entrada DS1: global 14 B + chunks (complen u16 + declen u16 +
    complen bytes) hasta sumar `total_declen`. Así NO se corta por falsos "DS1" en el audio."""
    total = struct.unpack_from("<I", data, off + 8)[0]
    pos, got = off + 14, 0
    n = len(data)
    while got < total and pos + 4 <= n:
        complen, declen = struct.unpack_from("<HH", data, pos)
        pos += 4 + complen
        got += declen
        if declen == 0:
            break
    return pos - off


def _ds1_ranges(data: bytes, start: int) -> list[tuple[int, int]]:
    """Recorre las entradas DS1 por su LONGITUD (no por firma) → evita los falsos "DS1" que
    aparecen dentro del audio comprimido (PCF2001 tenía 15 clips corruptos por eso)."""
    out = []
    pos = start
    n = len(data)
    while pos + 14 <= n and data[pos:pos + 3] == b"DS1":
        ln = _ds1_entry_len(data, pos)
        if ln <= 14 or pos + ln > n:
            break
        out.append((pos, ln))
        pos += ln
    return out


def ds1_pcm(entry: bytes) -> bytes | None:
    """Decodifica una entrada `DS1` → PCM 8-bit SIN SIGNO 11025 Hz mono (silencio=128).
    El audio es **DPCM (deltas)**: se descomprimen los bloques zlib (~4096 muestras) → bytes de
    DELTA con signo, y se INTEGRAN (acumulador con clamp, arranca en 128) para reconstruir la
    señal. Sin integrar suena "seco/agudo" (es la señal diferenciada)."""
    import struct
    import zlib
    declen = struct.unpack_from("<I", entry, 8)[0] if len(entry) >= 12 else 0
    raw = bytearray()
    pos = entry.find(b"\x78\xda")
    if pos < 0:
        pos = entry.find(b"\x78\x9c")
    if pos < 0:
        return None
    while 0 <= pos < len(entry):
        obj = zlib.decompressobj()
        try:
            raw += obj.decompress(entry[pos:])
        except Exception:  # noqa: BLE001
            break
        consumed = len(entry[pos:]) - len(obj.unused_data)
        if consumed <= 0:
            break
        if declen and len(raw) >= declen:
            break
        pos = entry.find(b"\x78\xda", pos + consumed)
    if declen:
        raw = raw[:declen]
    out = bytearray(len(raw))                          # integrar deltas (DPCM) → 8-bit unsigned
    acc = 128
    for i, b in enumerate(raw):
        acc += b if b < 128 else b - 256               # delta con signo
        acc = 0 if acc < 0 else 255 if acc > 255 else acc
        out[i] = acc
    return bytes(out)


def build_ds1(pcm: bytes, rate: int = 11025, blocksize: int = 4096) -> bytes:
    """Construye una entrada `DS1` desde PCM 8-bit SIN SIGNO mono (inverso de `ds1_pcm`).
    DPCM-encode: delta[i] = clamp(muestra[i] - prev, -128..127); prev sigue al decodificador
    (clamp 0..255). Estructura: `DS1\\n` + rate u16 + canales u8 + bits u8 + total_declen u32 +
    blocksize u16, y por bloque: complen u16 + declen u16 + zlib(bloque de deltas)."""
    import struct
    import zlib
    deltas = bytearray(len(pcm))                       # DPCM: unsigned PCM → deltas con signo
    prev = 128
    for i, s in enumerate(pcm):
        d = s - prev
        d = -128 if d < -128 else 127 if d > 127 else d
        prev += d
        prev = 0 if prev < 0 else 255 if prev > 255 else prev
        deltas[i] = d & 0xFF
    out = bytearray(b"DS1\n")
    out += struct.pack("<HBB", rate, 1, 8)
    out += struct.pack("<I", len(deltas))
    out += struct.pack("<H", blocksize)
    for i in range(0, len(deltas), blocksize):
        chunk = deltas[i:i + blocksize]
        comp = zlib.compress(bytes(chunk), 9)
        out += struct.pack("<HH", len(comp), len(chunk))
        out += comp
    return bytes(out)


def kind(data: bytes) -> str:
    """Tipo de contenido: 'midi' | 'mp3' | 'wav' | 'ds1' | 'unknown'."""
    s = _body(data)
    head = data[s:s + 4]
    if head == b"MThd":
        return "midi"
    if head[:3] == b"DS1":
        return "ds1"
    if head[:3] == b"ID3" or head[:2] == b"\xff\xfb" or head[:2] == b"\xff\xf3":
        return "mp3"
    if head == b"RIFF":
        return "wav"
    return "unknown"


def ranges(data: bytes) -> list[tuple[int, int]]:
    """[(offset, tamaño)] de cada entrada, según el tipo del contenedor."""
    s = _body(data)
    k = kind(data)
    if k == "midi":
        return _midi_ranges(data, s)
    if k == "wav":
        return _wav_ranges(data, s)
    if k == "mp3":
        return _mp3_ranges(data, s)
    if k == "ds1":
        return _ds1_ranges(data, s)
    return []


def ext(data: bytes) -> str:
    return {"midi": "mid", "mp3": "mp3", "wav": "wav", "ds1": "raw"}.get(kind(data), "bin")


def extract(data: bytes, idx: int) -> bytes | None:
    r = ranges(data)
    if not (0 <= idx < len(r)):
        return None
    off, size = r[idx]
    return data[off:off + size]


def repack(data: bytes, replacements: dict[int, bytes]) -> bytes:
    """Reconstruye el contenedor sustituyendo entradas (`{idx: bytes}`) por otras de cualquier
    tamaño. `magic + concat`. Sin cambios → idéntico (round-trip)."""
    r = ranges(data)
    if not r:
        return data
    out = bytearray(MAGIC if data[:4] == MAGIC else b"")
    for i, (off, size) in enumerate(r):
        out += replacements.get(i, data[off:off + size])
    return bytes(out)
