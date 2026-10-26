"""Generador de archivos LHA/LZH (método `-lh0-`, almacenado sin comprimir).

PCF 4.0 empaqueta sus ficheros en archivos LZH que se extraen con `LHA.EXE`.

Se usa `-lh0-` (stored): no comprime, pero produce un archivo LHA
100% válido que `LHA.EXE` extrae igual. Cabecera de nivel 0 (la que usa el juego).
"""
from __future__ import annotations

import struct

# CRC-16 (IBM/ARC, polinomio reflejado 0xA001) — el que usa LHA
_CRC16 = []
for _b in range(256):
    _c = _b
    for _ in range(8):
        _c = (_c >> 1) ^ 0xA001 if _c & 1 else _c >> 1
    _CRC16.append(_c)


def crc16(data: bytes) -> int:
    c = 0
    for byte in data:
        c = (c >> 8) ^ _CRC16[(c ^ byte) & 0xFF]
    return c & 0xFFFF


def _dos_time(t: tuple = (2026, 1, 1, 0, 0, 0)) -> int:
    """Fecha/hora empaquetada MS-DOS (u32 LE). Fija por defecto (determinista)."""
    y, mo, d, h, mi, s = t
    date = ((y - 1980) << 9) | (mo << 5) | d
    time = (h << 11) | (mi << 5) | (s // 2)
    return (date << 16) | time


def make_lh0(files: list[tuple[str, bytes]]) -> bytes:
    """`files` = lista de (ruta_relativa, datos) → archivo LHA `-lh0-` (nivel 0). Las rutas
    usan '\\' (DOS). Termina con un byte 0 (fin de archivo)."""
    dt = _dos_time()
    out = bytearray()
    for path, data in files:
        name = path.replace("/", "\\").encode("latin-1", "replace")
        body = bytearray()
        body += b"-lh0-"                          # método (stored)
        body += struct.pack("<I", len(data))      # tamaño comprimido (= original en lh0)
        body += struct.pack("<I", len(data))      # tamaño original
        body += struct.pack("<I", dt)             # fecha/hora MS-DOS
        body += bytes([0x20])                     # atributo (archive)
        body += bytes([0x00])                     # nivel de cabecera = 0
        body += bytes([len(name) & 0xFF])         # longitud del nombre
        body += name
        body += struct.pack("<H", crc16(data))    # CRC-16 de los datos
        hsize = len(body) & 0xFF                   # tamaño de cabecera (sin los 2 primeros bytes)
        checksum = sum(body) & 0xFF
        out += bytes([hsize, checksum]) + body + data
    out += b"\x00"                                 # marcador de fin
    return bytes(out)
