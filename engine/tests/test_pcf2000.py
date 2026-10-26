"""PC Fútbol 2000 / 2001 — round-trip byte-perfecto de los 4 FDI (equipo/jugador/
entrenador/ESTADIO), en las temporadas 99 (base) y 00 (Extensión).

Ficheros reales en `gamedata/PCF2000/DBDAT/` (gitignored). Se saltan si no están.
"""
from pathlib import Path

import pytest

from houdini_engine.formats import pcf2000

_GAMEDATA = Path(__file__).resolve().parents[2] / "gamedata"
_DBDAT = _GAMEDATA / "PCF2000" / "DBDAT"
_FILES = {
    "EQ": ["eq99022.fdi", "eq00022.fdi"],
    "JUG": ["jug99022.fdi", "jug00022.fdi"],
    "ENT": ["ent99022.fdi", "ent00022.fdi"],
    "EST": ["est99022.fdi", "est00022.fdi"],
}
_ALL = [(k, f) for k, fs in _FILES.items() for f in fs
        if (_DBDAT / f).exists()]
skip_no_files = pytest.mark.skipif(not _ALL, reason="FDI de PCF2000 no disponibles")

# round-trip por juego+variante (2000 y 2001 comparten motor; solo difiere el equipo)
_VARIANTS = [("PCF2000", "2000"), ("PCF2001", "2001")]
_ALL_V = [(g, v, k, f) for g, v in _VARIANTS for k, fs in _FILES.items() for f in fs
          if (_GAMEDATA / g / "DBDAT" / f).exists()]


@pytest.mark.skipif(not _ALL_V, reason="FDI de PCF2000/2001 no disponibles")
@pytest.mark.parametrize("game,variant,kind,fname", _ALL_V)
def test_roundtrip_byte_perfect(game, variant, kind, fname):
    data = (_GAMEDATA / game / "DBDAT" / fname).read_bytes()
    f = pcf2000.parse(data, kind, variant)
    out = pcf2000.serialize(f)
    assert out == data, f"{game}/{fname}: round-trip no byte-perfecto (len {len(out)} vs {len(data)})"


@skip_no_files
def test_barcelona_stadium_ref():
    """El equipo 1 (Barça) referencia un estadio por id (NUEVO en 2000)."""
    if not (_DBDAT / "eq00022.fdi").exists():
        pytest.skip("eq00022 no disponible")
    f = pcf2000.parse((_DBDAT / "eq00022.fdi").read_bytes(), "EQ")
    barsa = next(t for t in f.records if t.code == 1)
    assert "Barcelona" in barsa.nombre
    assert barsa.pais == 22
    assert barsa.tipo == 0
    assert barsa.estadio_id > 0
    assert barsa.version == pcf2000.VERSION_800


@skip_no_files
def test_player_3_new_bytes():
    """Jugador de liga jugable: 16 medias, 7 textos y los 3 bytes nuevos presentes."""
    if not (_DBDAT / "jug00022.fdi").exists():
        pytest.skip("jug00022 no disponible")
    f = pcf2000.parse((_DBDAT / "jug00022.fdi").read_bytes(), "JUG")
    jugables = [p for p in f.records if p.tipo == 0]
    assert jugables
    p = jugables[0]
    assert len(p.medias) == 16
    assert len(p.bbdd) == 7
    assert p.version == pcf2000.VERSION_800
    # los 3 campos nuevos existen (aunque valgan 0)
    for attr in ("pelo_tipo", "bello", "nacionalizado"):
        assert hasattr(p, attr)


@pytest.mark.skipif(
    not (_GAMEDATA / "PCF2001" / "manager.exe").exists(),
    reason="manager.exe de PCF2001 no disponible")
def test_division_map_2001():
    """Las tablas de liga del manager.exe dan las divisiones españolas correctas."""
    from houdini_engine.formats import pcf2000_manager as PM
    mb = (_GAMEDATA / "PCF2001" / "manager.exe").read_bytes()
    dmap = PM.division_map(mb, "2001")
    labels = {v[1] for v in dmap.values()}
    assert "Primera División" in labels
    assert "Segunda División" in labels
    assert dmap.get(1) == (22, "Primera División")     # Barça en Primera
    assert dmap.get(4) == (22, "Primera División")     # Real Madrid en Primera
    assert "Tercera · Grupo I" in labels               # las 17 de Tercera también mapeadas
    assert "Tercera · Grupo XVII" in labels
    # Primera(20)+Segunda(22)+2ªB(4×20)+Tercera(17×22, con huecos) → varios cientos
    assert len(dmap) > 400


@pytest.mark.skipif(
    not (_GAMEDATA / "PCF2001" / "manager.exe").exists(),
    reason="manager.exe de PCF2001 no disponible")
def test_set_divisions_and_competitions():
    """Escribir tablas de división y renombrar competiciones es in-place (tamaño intacto)."""
    from houdini_engine.formats import pcf2000_manager as PM
    mb = (_GAMEDATA / "PCF2001" / "manager.exe").read_bytes()
    # set_divisions: reescribe Primera al revés y se relee igual (como conjunto)
    dm = PM.division_map(mb, "2001")
    # "Primera División" existe para España (22) Y Argentina (3) → filtrar por país
    prim = [c for c, (p, lab) in dm.items() if p == 22 and lab == "Primera División"]
    mb2 = PM.set_divisions(mb, "2001", [(22, "Primera División", list(reversed(prim)))])
    assert len(mb2) == len(mb)
    dm2 = PM.division_map(mb2, "2001")
    prim2 = [c for c, (p, lab) in dm2.items() if p == 22 and lab == "Primera División"]
    assert set(prim) == set(prim2)
    # competiciones: renombrar Primera División in-place
    fields = PM.competition_fields(mb)
    assert any(f["key"] == "primera" and f["field"] == "name" for f in fields)
    mb3 = PM.apply_competitions(mb, {"primera/name": "La Liga"})
    assert len(mb3) == len(mb)
    assert b"La Liga\x00" in mb3


@skip_no_files
def test_stadium_entity():
    """El FDI de estadios se parsea como entidad propia con aforo."""
    if not (_DBDAT / "est00022.fdi").exists():
        pytest.skip("est00022 no disponible")
    f = pcf2000.parse((_DBDAT / "est00022.fdi").read_bytes(), "EST")
    assert f.records
    con_aforo = [s for s in f.records if s.sentados + s.de_pie > 10000]
    assert con_aforo, "ningún estadio con aforo > 10000"
    assert con_aforo[0].nombre
