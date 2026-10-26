"""PC Fútbol 7 — round-trip byte-perfecto del contenedor FDI y los 3 registros.

Ficheros reales en `gamedata/FUTBOL7/DBDAT/` (gitignored). Los tests se saltan si
no están.
"""
from pathlib import Path

import pytest

from houdini_engine.formats import pcf7

_DBDAT = Path(__file__).resolve().parents[2] / "gamedata" / "FUTBOL7" / "DBDAT"
_FILES = {
    "EQ": ["EQ98022.FDI", "EQ99022.FDI"],
    "JUG": ["JUG98022.FDI", "JUG99022.FDI"],
    "ENT": ["ENT98022.FDI", "ENT99022.FDI"],
}
_ALL = [(k, f) for k, fs in _FILES.items() for f in fs
        if (_DBDAT / f).exists()]
skip_no_files = pytest.mark.skipif(not _ALL, reason="FDI de PCF7 no disponibles")


@skip_no_files
@pytest.mark.parametrize("kind,fname", _ALL)
def test_roundtrip_byte_perfect(kind, fname):
    data = (_DBDAT / fname).read_bytes()
    f = pcf7.parse(data, kind)
    out = pcf7.serialize(f)
    assert out == data, f"{fname}: round-trip no byte-perfecto (len {len(out)} vs {len(data)})"


@skip_no_files
def test_barcelona_readable():
    """El equipo puntero 1 es el Barça, en el Camp Nou."""
    if not (_DBDAT / "EQ98022.FDI").exists():
        pytest.skip("EQ98022 no disponible")
    f = pcf7.parse((_DBDAT / "EQ98022.FDI").read_bytes(), "EQ")
    barsa = next(t for t in f.records if t.code == 1)
    assert "Barcelona" in barsa.nombre
    assert barsa.pais == 22            # España
    assert barsa.tipo == 0             # liga jugable
    assert barsa.sentados + barsa.de_pie > 50000


@skip_no_files
def test_player_16_medias():
    """Los jugadores de liga jugable tienen 16 medias."""
    if not (_DBDAT / "JUG99022.FDI").exists():
        pytest.skip("JUG99022 no disponible")
    f = pcf7.parse((_DBDAT / "JUG99022.FDI").read_bytes(), "JUG")
    jugables = [p for p in f.records if p.tipo == 0]
    assert jugables, "sin jugadores de liga jugable"
    p = jugables[0]
    assert len(p.medias) == 16
    assert len(p.bbdd) == 7            # 7 textos de BBDD


@skip_no_files
def test_edit_reindex():
    """Editar un nombre largo recomputa sumaLargos y reindexa sin romper el resto."""
    if not (_DBDAT / "EQ99022.FDI").exists():
        pytest.skip("EQ99022 no disponible")
    data = (_DBDAT / "EQ99022.FDI").read_bytes()
    f = pcf7.parse(data, "EQ")
    f.records[0].nombre = "Un Nombre Larguísimo Que No Cabía En El Hueco Original"
    out = pcf7.serialize(f)
    f2 = pcf7.parse(out, "EQ")
    assert f2.records[0].nombre == f.records[0].nombre
    # los demás equipos intactos
    assert f2.records[1].nombre == f.records[1].nombre
    assert len(f2.records) == len(f.records)
