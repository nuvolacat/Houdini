"""Contenedor `MUSICAS.PKF` de PCF 7 — las canciones de fondo del juego.

Ingeniería inversa (2026-07-15): es un contenedor PKF (cabecera con índice) que guarda
**N módulos ScreamTracker 3 (`.S3M`)** concatenados — la música que suena en bucle mientras
juegas (7 canciones en PCF7). Cada módulo lleva la firma `SCRM` en su offset 44.

Estructura:
    - Cabecera (hasta el primer módulo, típicamente 1458 B en PCF7) con un ÍNDICE: por cada
      canción, un `offset u32` (absoluto en el fichero) y a +4 su `tamaño u32`.
    - A continuación, los módulos S3M pegados (sin relleno: el fin de uno = inicio del siguiente).

Lectura robusta: se localizan los módulos por la firma `SCRM` (offset del módulo = pos-44) y sus
límites son consecutivos. Para REEMPAQUETAR con una canción de otro tamaño, se parchean los
campos offset/tamaño del índice (localizados por el valor original) y se recolocan los módulos.
"""
from __future__ import annotations

import struct

_SCRM = b"SCRM"


def song_ranges(data: bytes) -> list[tuple[int, int]]:
    """[(offset, tamaño)] de cada módulo S3M, en orden. Por firma `SCRM` (offset 44)."""
    starts: list[int] = []
    i = 0
    while True:
        i = data.find(_SCRM, i + 1)
        if i < 0:
            break
        start = i - 44
        if start >= 0:
            starts.append(start)
    starts.sort()
    bounds = starts + [len(data)]
    return [(starts[k], bounds[k + 1] - starts[k]) for k in range(len(starts))]


def extract(data: bytes, idx: int) -> bytes | None:
    """Bytes del módulo `.S3M` número `idx` (0-based)."""
    rng = song_ranges(data)
    if not (0 <= idx < len(rng)):
        return None
    off, size = rng[idx]
    return data[off:off + size]


def is_s3m(blob: bytes) -> bool:
    return len(blob) > 48 and blob[44:48] == _SCRM


def repack(data: bytes, replacements: dict[int, bytes]) -> bytes:
    """Reconstruye el `MUSICAS.PKF` sustituyendo los módulos indicados (`{idx: bytes_s3m}`),
    parcheando el índice de la cabecera. Sin cambios → devuelve `data` igual (round-trip)."""
    ranges = song_ranges(data)
    if not ranges:
        return data
    header = bytearray(data[:ranges[0][0]])      # cabecera hasta el 1er módulo
    mods = [replacements.get(i, data[off:off + size]) for i, (off, size) in enumerate(ranges)]
    cur = len(header)
    for i, (old_off, _old_size) in enumerate(ranges):
        m = mods[i]
        pos = header.find(struct.pack("<I", old_off))    # localizar su offset en el índice
        if pos >= 0:
            struct.pack_into("<I", header, pos, cur)       # nuevo offset absoluto
            struct.pack_into("<I", header, pos + 4, len(m))  # nuevo tamaño
        cur += len(m)
    return bytes(header) + b"".join(mods)
