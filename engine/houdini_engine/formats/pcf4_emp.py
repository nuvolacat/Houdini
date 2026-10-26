"""Escudo del SIMULADOR de PCF 4.0/4.5 — ficheros `ESCUDOS/EQ95NNNN.EMP`.

Es el escudo que se ve en el partido 2D (distinto del MINIESC de la ficha). Formato
(ingeniería inversa confirmada con FUTBOL_RELOAD, del creador de la comunidad):

    offset 0..23    : cabecera de 24 bytes (0x18) — se PRESERVA tal cual del original
    offset 24..    : PIXELS bytes = imagen W×H, índices de una paleta propia de 256
                      colores (`refdata/pcf4_palette_sim.json`), escritos en **4 pasadas
                      entrelazadas por columna**: pasada p recorre las columnas p, p+4, p+8…
    offset ..final : 4 bytes de cola — se PRESERVAN tal cual

Dos VARIANTES (se detectan por tamaño de fichero, como en FUTBOL_RELOAD):
  - ESPAÑOLA (PCF 4.0/4.5): 52×65 → 3380 px, total 3408 B (size ≥ 1500).
  - ITALIANA (PC Calcio 4.5): 32×45 → 1440 px, total 1468 B (size < 1500).

Para editar hace falta el `.EMP` original como base (cabecera+cola); solo se sustituye la
región de píxeles. El juego los lee sueltos de `ESCUDOS/`.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from PIL import Image

# variante ESPAÑOLA (por defecto). Las dims REALES se deciden por tamaño con _dims().
WIDTH = 52
HEIGHT = 65
HEADER = 24
PIXELS = WIDTH * HEIGHT              # 3380
TAIL = 4
TOTAL = HEADER + PIXELS + TAIL       # 3408

# (ancho, alto) por variante. El italiano (PC Calcio) es 32×45.
_DIMS_ES = (52, 65)
_DIMS_IT = (32, 45)

_PAL_PATH = Path(__file__).resolve().parent.parent / "refdata" / "pcf4_palette_sim.json"


@lru_cache(maxsize=1)
def palette() -> list[tuple[int, int, int]]:
    """256 colores (r,g,b) del simulador de PCF4."""
    raw = json.loads(_PAL_PATH.read_bytes())
    return [tuple(c) for c in raw]


def _dims(data: bytes) -> tuple[int, int]:
    """(ancho, alto) de un `.EMP` según su tamaño: <1500 = italiano 32×45, si no español 52×65."""
    return _DIMS_IT if len(data) < 1500 else _DIMS_ES


@lru_cache(maxsize=4)
def _interleave_positions(w: int, h: int) -> tuple[tuple[int, int], ...]:
    """Orden (fila, columna) en que se serializan los w×h píxeles (4 pasadas por columna)."""
    order: list[tuple[int, int]] = []
    for p in range(4):
        for row in range(h):
            for col in range(p, w, 4):
                order.append((row, col))
    return tuple(order)


_ORDER = _interleave_positions(WIDTH, HEIGHT)


def decode(data: bytes) -> Image.Image:
    """`.EMP` → imagen RGB (52×65 español o 32×45 italiano, según tamaño)."""
    w, h = _dims(data)
    pixels = w * h
    if len(data) < HEADER + pixels:
        raise ValueError(f"EMP demasiado corto: {len(data)}")
    pix = data[HEADER:HEADER + pixels]
    pal = palette()
    img = Image.new("RGB", (w, h))
    px = img.load()
    for i, (row, col) in enumerate(_interleave_positions(w, h)):
        px[col, row] = pal[pix[i]]
    return img


def _nearest(pal: list[tuple[int, int, int]], rgb: tuple[int, int, int]) -> int:
    r, g, b = rgb
    best, bi = 1 << 30, 0
    for i, (pr, pg, pb) in enumerate(pal):
        d = (pr - r) ** 2 + (pg - g) ** 2 + (pb - b) ** 2
        if d < best:
            best, bi = d, i
            if d == 0:
                break
    return bi


def encode(original_emp: bytes, source_png: bytes,
           bg_index: int = 0) -> bytes:
    """Genera un `.EMP` nuevo: conserva cabecera y cola del `original_emp` y sustituye la región de
    píxeles por `source_png` (escalado a las dims del original — 52×65 o 32×45 — y llevado a la paleta
    del simulador). Los píxeles transparentes van a `bg_index` (0 = negro/fondo)."""
    w, h = _dims(original_emp)
    pixels = w * h
    if len(original_emp) < HEADER + pixels:
        raise ValueError("EMP original inválido (base para cabecera/cola)")
    header = original_emp[:HEADER]
    tail = original_emp[HEADER + pixels:]            # normalmente 4 bytes
    pal = palette()

    src = Image.open(__import__("io").BytesIO(source_png)).convert("RGBA")
    src = src.resize((w, h), Image.LANCZOS)
    sp = src.load()

    idx = [[bg_index] * w for _ in range(h)]
    for row in range(h):
        for col in range(w):
            r, g, b, a = sp[col, row]
            idx[row][col] = bg_index if a < 128 else _nearest(pal, (r, g, b))

    out = bytearray(header)
    out += bytes(idx[row][col] for (row, col) in _interleave_positions(w, h))
    out += tail
    return bytes(out)


def reencode_indices(original_emp: bytes) -> bytes:
    """Round-trip de control: reescribe el `.EMP` con SUS MISMOS índices (debe ser idéntico)."""
    w, h = _dims(original_emp)
    pixels = w * h
    header = original_emp[:HEADER]
    pix = original_emp[HEADER:HEADER + pixels]
    tail = original_emp[HEADER + pixels:]
    return bytes(header) + bytes(pix) + bytes(tail)
