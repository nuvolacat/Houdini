"""Tests del formato de PC Fútbol 4.0/4.5 contra los DBC reales.

Los DBC del juego no se versionan; los tests se saltan si no están en
`gamedata/pcf4/DBDAT/`.
"""
from pathlib import Path

import pytest

from houdini_engine.codec import pcf4_text as T
from houdini_engine.formats import pcf4

_DBDAT = Path(__file__).resolve().parents[2] / "gamedata" / "pcf4" / "DBDAT"
_FILES = sorted(_DBDAT.glob("EQ95*.DBC")) if _DBDAT.exists() else []
skip_no_files = pytest.mark.skipif(not _FILES, reason="DBC de PCF4 no disponibles")


def test_codec_roundtrip():
    # solo caracteres del juego de PCF4 (las MAYÚSCULAS acentuadas no existen: en
    # el juego los nombres en mayúsculas van sin tilde, p.ej. "FUTBOL CLUB")
    for s in ["Ronaldo", "RONALDO Luiz Nazario", "Josep Lluis Núñez Clemente",
              "Camp Nou", "peña ñoño çava", "Müller", ""]:
        assert T.decode_str(T.encode_str(s), 0)[0] == s


@skip_no_files
def test_all_dbc_roundtrip_byte_perfect():
    bad = []
    for p in _FILES:
        data = p.read_bytes()
        if pcf4.serialize(pcf4.parse(data)) != data:
            bad.append(p.name)
    assert not bad, f"round-trip no idéntico en {len(bad)} ficheros: {bad[:5]}"


@skip_no_files
def test_coaches_and_players_parsed():
    # Barcelona (EQ950001): Cruyff + plantilla con nombres legibles
    t = pcf4.parse((_DBDAT / "EQ950001.DBC").read_bytes())
    assert t.name_short == "Barcelona"
    assert t.coaches and t.coaches[0].short_name == "Cruyff"
    assert len(t.players) >= 15
    assert all(pcf4._plausible(pl.short_name) for pl in t.players)


@skip_no_files
def test_edit_roundtrips():
    data = (_DBDAT / "EQ950001.DBC").read_bytes()
    t = pcf4.parse(data)
    t.players[0].short_name = "Prueba"
    t.players[0].speed = 99
    t2 = pcf4.parse(pcf4.serialize(t))
    assert t2.players[0].short_name == "Prueba"
    assert t2.players[0].speed == 99


def test_mapa_de_camisas_sin_ambiguedades():
    """La tabla que devuelve a cada club su camiseta: 44 huecos (los de Primera y Segunda
    del 95-96, los únicos con fichero en DBDAT/CAMISAS) y ningún nombre repetido — un
    nombre en dos huecos daría una camiseta distinta según el orden de lectura."""
    from houdini_engine import refdata
    mapa = refdata.pcf4_camisas()
    assert len(mapa) == 44
    vistas: dict[str, str] = {}
    for tid, info in mapa.items():
        assert info["claves"], f"{tid} sin ningún nombre"
        for k in info["claves"]:
            assert k not in vistas, f"'{k}' está en {vistas[k]} y en {tid}"
            vistas[k] = tid
