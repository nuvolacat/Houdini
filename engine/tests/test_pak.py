"""Contenedor de imágenes `.pak` de PC Fútbol 2000/2001.

Cubre los DOS modos de cifrado de ruta: XOR incremental (PCF2000) y texto plano
(PCF2001). Se salta si no está el gamedata (gitignored).
"""
from pathlib import Path

import pytest

from houdini_engine.codec import pak

_GAMEDATA = Path(__file__).resolve().parents[2] / "gamedata"
_CASES = [
    ("PCF2000", "MINIESC.PAK", "eq98", 0x94),   # XOR incremental
    ("PCF2001", "MINIESC.PAK", "eq98", None),   # ruta en plano
]
_AVAIL = [(g, f, p, k) for g, f, p, k in _CASES
          if (_GAMEDATA / g / "DBDAT" / f).exists()]
skip_no_files = pytest.mark.skipif(not _AVAIL, reason="paks de PCF2000/2001 no disponibles")


@skip_no_files
@pytest.mark.parametrize("game,fname,prefix,expected_key", _AVAIL)
def test_index_and_key(game, fname, prefix, expected_key):
    data = (_GAMEDATA / game / "DBDAT" / fname).read_bytes()
    assert pak.detect_key(data) == expected_key
    idx = pak.by_pointer(data, prefix)
    assert len(idx) > 100
    assert 1 in idx                     # el escudo del equipo 1 (Barça) existe


@skip_no_files
@pytest.mark.parametrize("game,fname,prefix,expected_key", _AVAIL)
def test_decode_all_escudos(game, fname, prefix, expected_key):
    """Todos los escudos decodifican (incluye BMP con compresión RLE8)."""
    data = (_GAMEDATA / game / "DBDAT" / fname).read_bytes()
    idx = pak.by_pointer(data, prefix)
    ok = 0
    for init, length in idx.values():
        pak.decode_bmp(data[init:init + length]).convert("RGBA")
        ok += 1
    assert ok == len(idx)


@skip_no_files
def test_barsa_png_is_png():
    data = (_GAMEDATA / "PCF2000" / "DBDAT" / "MINIESC.PAK").read_bytes()
    idx = pak.by_pointer(data, "eq98")
    init, length = idx[1]
    png = pak.entry_png(data, init, length)
    assert png[:4] == b"\x89PNG"
