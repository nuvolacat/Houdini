"""PCF 3.0 — la marca NF / AS / BJ del jugador (RE 2026-08-30).

Salió preguntando por los FILIALES. En PCF 4.0 «filial» son los equipos que no pueden ascender, y
eso ahí vive cableado en el ejecutable del manager. **En PCF 3.0 eso no existe**: el juego no
simula ascensos ni descensos —entre sus 143 rótulos no hay ASCENSO, DESCENSO ni PROMOCIÓN, y la
temporada acaba en el CUADRO DE HONOR—, así que no hay nada que marcar a nivel de equipo.

Lo que sí tiene, y estaba sin identificar, es una marca **por JUGADOR**. La cadena está en claro
dentro de `PCFUTBOL.DAT`:

    NF=Nuevo Fichaje   AS=Ascendido del filial   BJ=Baja

Es el **byte 9** del bloque de 13 que va tras el nombre completo, el único de los tres que
quedaba sin descifrar: 0 = nada · 1 = NF · 2 = AS · 3 = BJ.

La identificación se apoya en la historia real del 94-95, que es lo que la hace fiable.
"""
import os

import pytest

from houdini_engine.formats.pcf3 import Pcf3DB

_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "gamedata", "FUTBOL3")


@pytest.fixture(scope="module")
def db():
    p = os.path.join(_DIR, "LIG94951.DBC")
    if not os.path.exists(p):
        pytest.skip("sin gamedata/FUTBOL3")
    with open(p, "rb") as f:
        return Pcf3DB(f.read(), name="LIG94951.DBC")


def _estado(db, equipo, apodo):
    ti = next(i for i, t in enumerate(db.teams) if t.name == equipo)
    k = next(j for j, pl in enumerate(db.teams[ti].players) if pl[0].text == apodo)
    return db.player_info(ti, k)["estado"]


def test_los_fichajes_del_madrid_del_94_estan_marcados(db):
    """Sus cinco altas de aquel verano, y ninguna más."""
    for apodo in ("Cañizares", "Quique", "Redondo", "Laudrup", "Amavisca"):
        assert _estado(db, "Real Madrid", apodo) == 1, apodo


def test_raul_figura_como_ascendido_del_filial(db):
    """El caso canónico: subió del Castilla en 1994."""
    assert _estado(db, "Real Madrid", "Raúl") == 2


def test_jordi_cruyff_tambien_subio_del_filial(db):
    assert _estado(db, "Barcelona", "Jordi") == 2


def test_romario_figura_como_baja(db):
    """Se marchó al Flamengo en enero del 95."""
    assert _estado(db, "Barcelona", "Romário") == 3


def test_los_fichajes_del_barca_del_94(db):
    for apodo in ("Lopetegi", "Abelardo", "Hagi"):
        assert _estado(db, "Barcelona", apodo) == 1, apodo


def test_los_de_toda_la_vida_no_llevan_marca(db):
    """Si el byte se leyera mal, o saldrían todos marcados o ninguno."""
    for apodo in ("Guardiola", "Bakero", "Amor", "Stoitchkov"):
        assert _estado(db, "Barcelona", apodo) == 0, apodo


def test_el_reparto_es_creible(db):
    """Un tercio de la base marcada: ni todos ni nadie."""
    from collections import Counter
    c = Counter(db.player_info(ti, k)["estado"]
                for ti, t in enumerate(db.teams) for k in range(len(t.players)))
    assert c[0] > c[1] > c[2] > c[3] > 0
    assert sum(c.values()) == 527


def test_todos_los_valores_estan_en_rango(db):
    for ti, t in enumerate(db.teams):
        for k in range(len(t.players)):
            assert db.player_info(ti, k)["estado"] in (0, 1, 2, 3)


def test_cambiar_la_marca_no_mueve_nada(db):
    """Es un byte de sitio fijo: se escribe donde está."""
    tam = len(db.raw)
    plantillas = [len(t.players) for t in db.teams]
    mad = next(i for i, t in enumerate(db.teams) if t.name == "Real Madrid")
    k = next(j for j, pl in enumerate(db.teams[mad].players) if pl[0].text == "Raúl")
    db.set_player_estado(mad, k, 1)
    assert db.player_info(mad, k)["estado"] == 1
    assert len(db.to_bytes()) == tam
    assert [len(t.players) for t in db.teams] == plantillas
    db.set_player_estado(mad, k, 2)                     # se deja como estaba
    assert db.player_info(mad, k)["estado"] == 2


def test_una_marca_inventada_se_rechaza(db):
    with pytest.raises(ValueError, match="0-3"):
        db.set_player_estado(0, 0, 9)


def test_pcf3_no_tiene_ascensos_ni_descensos():
    """La razón de que el mecanismo de filiales de PCF4 no aplique aquí. Si algún día apareciera
    un rótulo de ascenso, habría que replantearlo."""
    p = os.path.join(_DIR, "PCFRES00.GRC")
    if not os.path.exists(p):
        pytest.skip("sin PCFRES00.GRC")
    from houdini_engine.formats import pcf4_grc as GRC
    with open(p, "rb") as f:
        textos = [t["text"].upper() for t in GRC.read_texts(f.read())]
    for palabra in ("ASCENSO", "DESCENSO", "PROMOCION", "FILIAL"):
        assert not any(palabra in t for t in textos), palabra
    assert any("CUADRO DE HONOR" in t for t in textos)
