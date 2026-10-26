"""PCF 3.0: las tablas de competición, leídas con estructura (RE 2026-08-30).

Los seis `.DBC` de competición se enseñaban como una lista plana de textos anónimos, todos
etiquetados «Texto». No lo son: entre cadena y cadena van los NÚMEROS del registro. Este fichero
comprueba la lectura contra la HISTORIA REAL, que es la única manera de saber si el formato se ha
entendido o solo se ha inventado una estructura que cuadra consigo misma.
"""
import os

import pytest

from houdini_engine.formats.pcf3 import Pcf3DB
from houdini_engine.formats import pcf3_comp as CMP

_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "gamedata", "FUTBOL3")


def _db(fn: str) -> Pcf3DB:
    p = os.path.join(_DIR, fn)
    if not os.path.exists(p):
        pytest.skip("sin gamedata/FUTBOL3")
    with open(p, "rb") as f:
        return Pcf3DB(f.read(), name=fn)


def _secs(fn: str, equipos=None):
    db = _db(fn)
    return db, {s["clave"]: s for s in CMP.leer(db, fn, equipos)}


def _v(fila):
    return [c.get("v") for c in fila["celdas"]]


# --- LIGA.DBC: la clasificación de cada temporada -------------------------------------------
def test_liga_temporadas_y_tabla_del_28_29():
    _, s = _secs("LIGA.DBC")
    grupos = s["temporadas"]["grupos"]
    assert len(grupos) == 63                                  # 1928-29 .. 1993-94
    vieja = grupos[-1]
    assert vieja["titulo"] == "1928-29"
    assert len(vieja["filas"]) == 10                          # la primera Liga tuvo 10 equipos
    # Barcelona campeón: 18 PJ, 11-3-4, 37-23, 25 puntos. Tal cual pasó.
    assert _v(vieja["filas"][0]) == [1, "Barcelona", 18, 11, 3, 4, 37, 23, 25]


def test_liga_ultima_temporada_y_corte_de_la_guerra():
    _, s = _secs("LIGA.DBC")
    grupos = s["temporadas"]["grupos"]
    assert grupos[0]["titulo"] == "1993-94"
    # 93-94: Barcelona campeón por el golaverage particular, ambos con 56.
    assert _v(grupos[0]["filas"][0])[1:] == ["Barcelona", 38, 25, 6, 7, 91, 42, 56]
    assert _v(grupos[0]["filas"][1])[1] == "Deportivo"
    # No hubo Liga del 36 al 39: los años saltan. Esto es lo que demuestra que el año ABRE el
    # grupo — si lo cerrara, la temporada 1935-36 quedaría etiquetada como 1939-40.
    titulos = [g["titulo"] for g in reversed(grupos)]
    assert titulos[7] == "1935-36" and titulos[8] == "1939-40"


def test_liga_palmares():
    _, s = _secs("LIGA.DBC")
    filas = s["palmares"]["grupos"][0]["filas"]
    assert _v(filas[0]) == ["Real Madrid", 25]                # títulos de Liga en 1994
    assert _v(filas[1]) == ["Barcelona", 14]
    assert len(filas) == 8


# --- COPAREY.DBC: las finales, con el once del campeón --------------------------------------
def test_copa_primera_y_ultima_final():
    _, s = _secs("COPAREY.DBC")
    filas = s["finales"]["grupos"][0]["filas"]
    assert len(filas) == 91
    # 1994: Zaragoza 0-0 Celta (la que se decidió en los penaltis).
    assert _v(filas[0])[:6] == ["1994", "20-4", "Zaragoza", 0, "Celta", 0]
    # 1902, la Copa de la Coronación: Club Vizcaya 2-1 Barcelona.
    assert _v(filas[-1])[2:6] == ["Club Viz. de Bilbao", 2, "Barcelona", 1]
    assert "Larrañaga" in _v(filas[-1])[6]                     # el once del campeón


def test_copa_palmares():
    _, s = _secs("COPAREY.DBC")
    filas = s["palmares"]["grupos"][0]["filas"]
    assert _v(filas[0]) == ["Ath. Bilbao", 23]
    assert _v(filas[1]) == ["Barcelona", 22]


# --- EUROPA.DBC / UEFA.DBC: ranking histórico + finales --------------------------------------
def test_copa_de_europa():
    _, s = _secs("EUROPA.DBC")
    filas = s["finales"]["grupos"][0]["filas"]
    assert len(filas) == 39                                   # 1956 .. 1994
    assert _v(filas[-1])[:6] == ["1955-56", "París, 13 de Junio de 1956",
                                 "Real Madrid", 4, "Stade de Reims", 3]
    assert _v(filas[0])[2:6] == ["Milán", 4, "Barcelona", 0]  # Atenas 1994
    esp = s["espanoles"]["grupos"][0]["filas"]
    assert [_v(x)[0] for x in esp] == ["Real Madrid", "Barcelona", "Atl. de Madrid"]


def test_ranking_europeo_los_puntos_son_2pg_mas_pe():
    """Si la lectura de columnas fuese otra, esta cuenta no saldría en casi ninguna fila.

    No sale en TODAS porque la tabla del juego trae erratas suyas: al Real Madrid de la UEFA le
    pone 0 empates en 58 partidos, y a media docena más les bailan dos o tres unidades. Son
    fallos de Dinamic, no de la lectura — si las columnas estuvieran corridas fallarían todas.
    """
    _, s = _secs("EUROPA.DBC")
    filas = s["ranking"]["grupos"][0]["filas"]
    assert _v(filas[0])[:2] == ["Real Madrid", 227]
    cuadran = sum(1 for f in filas
                  if (lambda x: x[1] == 2 * x[4] + x[5])(_v(f)))
    assert cuadran >= len(filas) * 0.8


def test_uefa_finales_y_espanoles():
    _, s = _secs("UEFA.DBC")
    filas = s["finales"]["grupos"][0]["filas"]
    assert len(filas) == 36
    # 1994: Inter 1-0 y 1-0 al Salzburgo.
    assert _v(filas[0]) == ["1994", "Inter", "Salzburgo", "1-0", "1-0"]
    # 1958, la primera Copa de Ferias: Barcelona 2-2 y 6-0 a la selección de Londres.
    assert _v(filas[-1]) == ["1958", "Barcelona", "Sel. London", "2-2", "6-0"]
    esp = s["espanoles"]["grupos"][0]["filas"]
    assert _v(esp[0]) == ["Barcelona", 147]


# --- ARBITROS.DBC ----------------------------------------------------------------------------
def test_arbitros_cuatro_campos_cada_uno():
    _, s = _secs("ARBITROS.DBC")
    filas = s["arbitros"]["grupos"][0]["filas"]
    assert len(filas) == 44
    assert all(len(f["celdas"]) == 4 for f in filas)


# --- COMMENT.DBC -----------------------------------------------------------------------------
def test_comentarios_recuperan_las_lineas_largas():
    """El escaneo corta en 64 caracteres y estas líneas miden ~75: se veían 2 de cada 9."""
    db, s = _secs("COMMENT.DBC", ["Barcelona", "Deportivo"])
    grupos = s["comentarios"]["grupos"]
    assert len(grupos) == 58
    assert grupos[0]["titulo"] == "Barcelona · Novedades en el equipo"
    assert len(grupos[0]["filas"]) == 9
    texto = " ".join(_v(f)[0] for f in grupos[0]["filas"])
    assert "Cruyff" in texto and "Hagi" in texto
    assert grupos[3]["titulo"].startswith("Deportivo")


# --- edición: los números y el once se escriben SIN mover el fichero --------------------------
def test_editar_numero_no_mueve_el_fichero():
    db, s = _secs("LIGA.DBC")
    antes = len(db.raw)
    celda = s["temporadas"]["grupos"][-1]["filas"][0]["celdas"][8]   # puntos del Barcelona del 28-29
    CMP.set_num(db, celda["off"], 99)
    assert len(db.raw) == antes
    s2 = {x["clave"]: x for x in CMP.leer(db, "LIGA.DBC")}
    assert _v(s2["temporadas"]["grupos"][-1]["filas"][0])[8] == 99


def test_editar_el_once_del_campeon_conserva_la_longitud():
    db, s = _secs("COPAREY.DBC")
    antes = len(db.raw)
    celda = s["finales"]["grupos"][0]["filas"][0]["celdas"][6]
    CMP.set_texto_hueco(db, celda["off"], "Cedrún y los demás")
    assert len(db.raw) == antes
    s2 = {x["clave"]: x for x in CMP.leer(db, "COPAREY.DBC")}
    assert _v(s2["finales"]["grupos"][0]["filas"][0])[6].strip() == "Cedrún y los demás"
    with pytest.raises(ValueError):
        CMP.set_texto_hueco(db, celda["off"], "x" * 400)


def test_round_trip_byte_perfecto():
    """La prueba obligatoria: leer y volver a escribir no puede cambiar un solo byte."""
    for fn in ("LIGA.DBC", "COPAREY.DBC", "EUROPA.DBC", "UEFA.DBC",
               "ARBITROS.DBC", "COMMENT.DBC"):
        p = os.path.join(_DIR, fn)
        if not os.path.exists(p):
            pytest.skip("sin gamedata/FUTBOL3")
        with open(p, "rb") as f:
            orig = f.read()
        db = Pcf3DB(orig, name=fn)
        CMP.leer(db, fn)
        assert db.to_bytes() == orig, fn
