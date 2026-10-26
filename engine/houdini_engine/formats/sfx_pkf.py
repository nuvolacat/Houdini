"""Contenedores de VOZ/COMENTARIOS de PCF 7 (`SFX/*.PKF`).

Mismo contenedor PKF que `MUSICAS.PKF` (cabecera + índice de offset/tamaño), pero con **clips
WAV estándar** (mono 11025 Hz 8-bit) en vez de módulos S3M. Cada clip empieza por `RIFF....WAVE`.

Contenido (`gamedata/FUTBOL7/SFX/`):
- `COMPCF7/*.PKF` — comentarios del SIMULADOR por evento (GOL, PENALTY, FALTA…).
- `AMBIENTE.PKF` — público/ambiente. `NGI022/*.PKF` — narración.

Lectura robusta por firma `RIFF...WAVE` + tamaño del chunk (RIFF size + 8). Los WAV se
reproducen directos en el navegador (no hace falta ffmpeg).

EDICIÓN (reemplazar un clip): **in-place** — se sobrescribe el hueco del clip con el WAV nuevo
(que debe caber: ≤ tamaño original) rellenando con ceros. Así NO cambian offsets ni el índice
(el juego lee el tamaño real del propio WAV en su cabecera; el relleno se ignora). Evita tener
que reversear el índice completo para recolocar clips de otro tamaño.
"""
from __future__ import annotations

import struct

_RIFF = b"RIFF"
_WAVE = b"WAVE"


_INDEX_START = 232        # el índice PKF empieza aquí (igual que imagenes_pkf)


def index_ranges(data: bytes) -> list[tuple[int, int]]:
    """[(offset, tamaño)] leyendo el ÍNDICE PKF paginado (tag 02 = entrada con offset u32 en
    +26 y tamaño en +30 ; tag 04 = salto al u32 en +1). AGNÓSTICO al contenido → sirve tanto
    para clips WAV (PCF7/6.0) como RAW (COMENT.PKF de 5.0). [] si no hay índice válido."""
    out: list[tuple[int, int]] = []
    pos, seen = _INDEX_START, set()
    while 0 <= pos < len(data) - 38 and pos not in seen:
        seen.add(pos)
        tag = data[pos]
        if tag == 0x02:
            off, size = struct.unpack_from("<II", data, pos + 26)
            if 0 <= off < len(data) and 0 < size <= len(data) - off:
                out.append((off, size))
            pos += 38
        elif tag == 0x04:
            pos = struct.unpack_from("<I", data, pos + 1)[0]
        else:
            break
    return out


def _riff_ranges(data: bytes) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    i = -1
    while True:
        i = data.find(_RIFF, i + 1)
        if i < 0:
            break
        if data[i + 8:i + 12] != _WAVE:
            continue
        size = struct.unpack_from("<I", data, i + 4)[0] + 8    # RIFF chunk size + 8
        if 0 < size <= len(data) - i:
            out.append((i, size))
    return out


def clip_ranges(data: bytes) -> list[tuple[int, int]]:
    """[(offset, tamaño)] de cada clip. Usa el ÍNDICE PKF (robusto, sirve RAW y WAV); si el
    índice no aparece, cae a buscar por firma RIFF."""
    idx = index_ranges(data)
    return idx if idx else _riff_ranges(data)


def is_wav(blob: bytes) -> bool:
    return len(blob) > 12 and blob[:4] == _RIFF and blob[8:12] == _WAVE


def count(data: bytes) -> int:
    return len(clip_ranges(data))


def extract(data: bytes, idx: int) -> bytes | None:
    """WAV del clip `idx` (0-based)."""
    r = clip_ranges(data)
    if not (0 <= idx < len(r)):
        return None
    off, size = r[idx]
    return data[off:off + size]


def _layout(data: bytes):
    """Descompone el PKF en su estructura paginada: bloques de ÍNDICE (gaps) y RUNS de clips
    contiguos, alternados `[idx][clips][idx][clips]…` + cola. Devuelve (gaps, runs, tail):
    gaps=[(ini,fin)] bytes de cada bloque de índice; runs=[[(off,size)…]] clips de cada run;
    tail=(ini,fin) bytes tras el último clip."""
    clips = clip_ranges(data)
    if not clips:
        return [(0, len(data))], [], (len(data), len(data))
    runs: list[list[tuple[int, int]]] = []
    cur = [clips[0]]
    for off, size in clips[1:]:
        if off == cur[-1][0] + cur[-1][1]:          # pegado al anterior → mismo run
            cur.append((off, size))
        else:
            runs.append(cur)
            cur = [(off, size)]
    runs.append(cur)
    gaps, prev_end = [], 0
    for run in runs:
        gaps.append((prev_end, run[0][0]))
        prev_end = run[-1][0] + run[-1][1]
    return gaps, runs, (prev_end, len(data))


def repack(data: bytes, replacements: dict[int, bytes]) -> bytes:
    """DESEMPAQUETA y REEMPAQUETA el PKF sustituyendo los clips indicados (`{idx: wav}`) por
    otros de CUALQUIER tamaño, recolocando todo y parcheando el índice paginado (offsets,
    tamaños y saltos entre bloques). Sin cambios → idéntico al original (round-trip)."""
    gaps, runs, tail = _layout(data)
    if not runs:
        return data
    orig_gap_start = [g[0] for g in gaps]
    gap_bytes = [bytearray(data[a:b]) for a, b in gaps]
    # 1ª pasada: nuevas posiciones (los bloques de índice conservan su tamaño; los clips no)
    new_gap_start, new_clip_off, new_clip_bytes, pos, gci = [], [], [], 0, 0
    for i, run in enumerate(runs):
        new_gap_start.append(pos)
        pos += len(gap_bytes[i])
        for off, size in run:
            nb = replacements.get(gci, data[off:off + size])
            new_clip_off.append(pos)
            new_clip_bytes.append(nb)
            pos += len(nb)
            gci += 1
    # 2ª pasada: parchear cada bloque de índice (offset+tamaño de sus clips; saltos a otros bloques)
    gci = 0
    for i, run in enumerate(runs):
        gb = gap_bytes[i]
        for off, _size in run:
            p = gb.find(struct.pack("<I", off))            # campo offset de este clip
            if p >= 0:
                struct.pack_into("<I", gb, p, new_clip_off[gci])
                struct.pack_into("<I", gb, p + 4, len(new_clip_bytes[gci]))  # tamaño (a +4)
            gci += 1
        for j in range(i + 1, len(gaps)):                  # saltos a bloques posteriores
            p = gb.find(struct.pack("<I", orig_gap_start[j]))
            if p >= 0:
                struct.pack_into("<I", gb, p, new_gap_start[j])
    out = bytearray()
    gci = 0
    for i, run in enumerate(runs):
        out += gap_bytes[i]
        for _ in run:
            out += new_clip_bytes[gci]
            gci += 1
    out += data[tail[0]:tail[1]]
    return bytes(out)
