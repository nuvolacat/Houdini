"""PCF 3.0 — nombres MÁS LARGOS de lo que traía el jugador (2026-08-30).

Pregunta del foro: unos nombres tienen 8 letras y otros 5, ¿se puede alargar? Hasta ahora el
editor conservaba la longitud, porque alargar un texto desplaza todo lo que va detrás.

**Sí se puede, y el formato no impone ningún límite:** cada texto va `[u8 longitud][texto]` —caben
255— y dentro del `.DBC` no hay ni tabla de offsets ni punteros absolutos (los del escudo y las
fotos apuntan a los `.DGF`, no aquí). El juego RECORRE el fichero, así que desplazar bytes no le
molesta. Se comprobó buscando los 41 inicios de equipo como u16 y como u32 en la cabecera: ni uno.

**El límite lo pone el JUEGO**, no el fichero: cuánto le cabe en su buffer y en pantalla. Como no
se le puede preguntar, el tope es **lo que él mismo trae de fábrica**, que es la única prueba de
lo que digiere: apodo 17 (`Txomin Larrainzar`), nombre 30 (`José Francisco BELMAN González`).

Lo que vigilan estas pruebas es que recomponer el fichero no se lleve nada por delante.
"""
import os
import sys

import pytest

from houdini_engine.formats.pcf3 import Pcf3DB

_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "gamedata", "FUTBOL3")
_PLANTILLAS = [26, 22, 24, 26, 22, 23, 25, 24, 24, 22, 23, 24, 27, 30, 24, 34, 35, 23, 23, 26, 20]


def _db():
    p = os.path.join(_DIR, "LIG94951.DBC")
    if not os.path.exists(p):
        pytest.skip("sin gamedata/FUTBOL3")
    with open(p, "rb") as f:
        return Pcf3DB(f.read(), name="LIG94951.DBC")


@pytest.fixture()
def db():
    return _db()


def _barsa(db):
    return next(i for i, t in enumerate(db.teams) if t.name == "Barcelona")


# --- el tope ---

def test_el_tope_sale_de_lo_que_trae_el_propio_juego(db):
    bar = _barsa(db)
    apodo, nombre = db.teams[bar].players[0]
    assert db.tope_de(apodo) == 17          # 'Txomin Larrainzar'
    assert db.tope_de(nombre) == 30         # 'José Francisco BELMAN González'


def test_nunca_se_recorta_por_debajo_de_lo_que_ya_hay(db):
    """Si un campo del juego fuera más largo que el tope de su clase, manda el campo."""
    for t in db.teams:
        for f in list(t.fields) + list(t.coach) + [x for pl in t.players for x in pl]:
            assert db.tope_de(f) >= f.length, f.text


def test_pasarse_del_tope_se_rechaza(db):
    bar = _barsa(db)
    with pytest.raises(ValueError, match="máximo 17"):
        db.set_field(db.teams[bar].players[0][0].off, "X" * 40)


# --- alargar sin romper nada ---

def test_alargar_un_apodo_no_descuadra_la_base(db):
    bar = _barsa(db)
    antes = len(db.raw)
    db.set_field(db.teams[bar].players[0][0].off, "Lopetegui")
    assert len(db.raw) == antes + 1
    assert db.teams[bar].players[0][0].text == "Lopetegui"
    assert len(db.teams) == 21 and db.declared_teams() == 20
    assert [len(t.players) for t in db.teams] == _PLANTILLAS


def test_el_jugador_conserva_todo_lo_suyo(db):
    """Medias, dorsal, demarcación y fecha van en bytes que se desplazan con él."""
    bar = _barsa(db)
    medias = db.player_ratings(bar, 0)["medias"]
    info = db.player_info(bar, 0)
    db.set_field(db.teams[bar].players[0][0].off, "Julen Lopetegui")
    assert db.player_ratings(bar, 0)["medias"] == medias
    assert db.player_info(bar, 0) == info


def test_los_demas_jugadores_no_se_mueven(db):
    bar = _barsa(db)
    otros = {k: (db.teams[bar].players[k][0].text, db.player_ratings(bar, k)["medias"])
             for k in range(1, 8)}
    db.set_field(db.teams[bar].players[0][0].off, "Julen Lopetegui")
    for k, (nombre, medias) in otros.items():
        assert db.teams[bar].players[k][0].text == nombre
        assert db.player_ratings(bar, k)["medias"] == medias


def test_los_demas_equipos_tampoco(db):
    bar = _barsa(db)
    antes = [(t.name, len(t.players)) for t in db.teams]
    db.set_field(db.teams[bar].players[0][0].off, "Julen Lopetegui")
    assert [(t.name, len(t.players)) for t in db.teams] == antes


def test_los_escudos_siguen_apuntando_a_su_sitio(db):
    """Los punteros de escudo van al `.DGF`, no al `.DBC`, así que desplazar bytes aquí no los
    toca — pero conviene comprobarlo, porque si se rompiera, cada equipo saldría con el de otro."""
    from houdini_engine.formats import pcf3_dgf as DGF
    with open(os.path.join(_DIR, "LIG94951.DGF"), "rb") as f:
        data = f.read()
    escs = frozenset(im["off"] for im in DGF.images(data) if (im["w"], im["h"]) == (48, 64))
    bar = _barsa(db)
    antes = {i: db.team_escudo_offset(i, escs) for i in range(20)}
    db.set_field(db.teams[bar].players[0][0].off, "Julen Lopetegui")
    assert {i: db.team_escudo_offset(i, escs) for i in range(20)} == antes


def test_varios_cambios_seguidos(db):
    """Cada cambio recompone el fichero; encadenarlos no puede degradarlo."""
    bar = _barsa(db)
    for nuevo in ("Lopetegui", "Julen Lopetegui", "J. Lopetegui", "Lopetegi"):
        db.set_field(db.teams[bar].players[0][0].off, nuevo)
        assert db.teams[bar].players[0][0].text == nuevo
        assert [len(t.players) for t in db.teams] == _PLANTILLAS


def test_acortar_tambien_vale(db):
    bar = _barsa(db)
    antes = len(db.raw)
    db.set_field(db.teams[bar].players[0][0].off, "Lope")
    assert len(db.raw) == antes - 4
    assert db.teams[bar].players[0][0].text == "Lope"
    assert [len(t.players) for t in db.teams] == _PLANTILLAS


def test_tambien_los_nombres_de_club_y_entrenador(db):
    bar = _barsa(db)
    est = next(f for f in db.teams[bar].fields if f.kind == "estadio")
    db.set_field(est.off, "Camp Nou de Barcelona")
    assert next(f.text for f in db.teams[bar].fields if f.kind == "estadio") == "Camp Nou de Barcelona"
    assert [len(t.players) for t in db.teams] == _PLANTILLAS


def test_los_ficheros_de_competicion_siguen_conservando_la_longitud(db):
    """Usan prefijo de DOS bytes y no se ha comprobado que no tengan tablas de offsets: ahí no se
    alarga nada hasta saberlo."""
    p = os.path.join(_DIR, "LIGA.DBC")
    if not os.path.exists(p):
        pytest.skip("sin LIGA.DBC")
    with open(p, "rb") as f:
        liga = Pcf3DB(f.read(), name="LIGA.DBC")
    if liga.lenw == 1:
        pytest.skip("este fichero usa prefijo de 1 byte")
    campo = liga.fields[0]
    antes = len(liga.raw)
    with pytest.raises(ValueError):
        liga.set_field(campo.off, "X" * (campo.length + 5))
    assert len(liga.raw) == antes


def test_el_entrenador_tambien_admite_mas_letras(db):
    """Se le fue la etiqueta la primera vez: sus dos campos se marcaban «entrenador» a secas, no
    casaban con la tabla de topes y se quedaban con el largo que traían."""
    bar = _barsa(db)
    corto, largo = db.teams[bar].coach
    assert (corto.kind, largo.kind) == ("entrenador_corto", "entrenador_largo")
    assert db.tope_de(corto) == 15 and db.tope_de(largo) == 30
    db.set_field(corto.off, "Johan Cruyff")               # de 6 a 12 letras
    assert db.teams[bar].coach[0].text == "Johan Cruyff"
    assert [len(t.players) for t in db.teams] == _PLANTILLAS


def test_etiquetar_al_entrenador_no_se_lleva_los_campos_del_club(db):
    """El filtro de campos de club los excluía por nombre exacto; al separarlos en dos había que
    cambiarlo o el club se quedaba con campos de más."""
    bar = _barsa(db)
    clases = [f.kind for f in db.teams[bar].fields]
    assert not any(c.startswith("entrenador") for c in clases)
    for esperado in ("corto", "largo", "estadio", "presidente"):
        assert esperado in clases
