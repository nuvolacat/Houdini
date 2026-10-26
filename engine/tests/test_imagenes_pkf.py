"""Tests del lector de contenedores de imágenes (NANOESC/MINIESC/MINIFOTO).

Usan los contenedores de gamedata/ (no versionados); se saltan si no están.
"""
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from houdini_engine import match
from houdini_engine.codec import image as I
from houdini_engine.formats import equipos_pkf as E
from houdini_engine.formats import imagenes_pkf as IP

_GAMEDATA = Path(__file__).resolve().parents[2] / "gamedata"
_PCF5 = _GAMEDATA / "pcf5"
skip_no_files = pytest.mark.skipif(
    not (_PCF5 / "MINIESC.PKF").exists(), reason="contenedores no disponibles")


@skip_no_files
def test_miniesc_index_and_decode():
    cont = IP.parse((_PCF5 / "MINIESC.PKF").read_bytes())
    assert len(cont.index) == 260
    # Barcelona=1, Real Madrid=4, At. Madrid=12 (verificado visualmente)
    for ptr in (1, 4, 12):
        blob = cont.blob(ptr)
        assert blob and blob[:2] == b"DM"
        png = I.dm_blob_to_png(blob)
        img = Image.open(BytesIO(png))
        assert img.size == (48 * 4, 64 * 4)  # mini 48x64 escalado x4


@skip_no_files
def test_minifoto_pointers_match_players():
    cont = IP.parse((_PCF5 / "MINIFOTO.PKF").read_bytes())
    pf = E.parse((_PCF5 / "EQUIPOS.PKF").read_bytes(), "EQUIPOS.PKF")
    pptrs = {p.pointer for p in pf.players}
    hits = sum(1 for n in cont.pointers if n in pptrs)
    assert len(cont.index) == 978
    assert hits >= 960  # 970/978 en el fichero original


@skip_no_files
def test_match_team_pointers_known():
    pf = E.parse((_PCF5 / "EQUIPOS.PKF").read_bytes(), "EQUIPOS.PKF")
    nano = IP.parse((_PCF5 / "NANOESC.PKF").read_bytes())
    ptrs = match.match_team_pointers(pf.teams, nano.pointers)
    by_name = {pf.teams[i].short_name: p for i, p in ptrs.items()}
    assert by_name["Barcelona"] == 1
    assert by_name["Real Madrid"] == 4
    assert by_name["At. Madrid"] == 12
    assert by_name["Sevilla"] == 6
    assert by_name["Zaragoza"] == 3
    # cobertura amplia: casi todos los equipos con puntero
    assert len(ptrs) >= 240
