"""Los países que el juego OFRECE viven en el `manager.exe`, no en la base.

Pregunta del foro y comprobada el 2-sep-2026: **Andorra** existe en la base de 6.0
Oro —con su club, sus jugadores, y hasta salen en la selección de Europa del Desafío— pero el
juego no la ofrece en ninguna pantalla, y añadirle equipos no cambia nada. La lista está en dos
tablas de códigos de país de un byte dentro del ejecutable:

    Sudamérica (10)   Argentina, Brasil, Uruguay, Chile, Colombia, Paraguay,
                      Venezuela, Ecuador, Bolivia, Perú
    (38 bytes a cero)
    Europa (47)       incluidos Israel, Georgia, Armenia y Azerbaiyán, que son UEFA

La prueba de que son LAS tablas: de los países que aparecen, **ni uno carece de equipos** en la
base. Y los que tienen equipos y no están son exactamente los diez sudamericanos —que van en su
propia lista—, USA, Islas Feroe y Andorra: las micro-federaciones que Dinamic dejó fuera.

Las plazas son FIJAS: la tabla europea está pegada a datos de punteros —el `00` que la cierra es
ya el primer byte del siguiente—, así que alargarla obligaría a moverla y repuntar quien la
referencia. Por eso lo que se ofrece es un INTERCAMBIO.
"""
import json
import os

import pytest

from houdini_engine import refdata
from houdini_engine.formats import equipos_pkf as E
from houdini_engine.formats import manager as MGR

RAIZ = os.path.join(os.path.dirname(__file__), "..", "..")
_P = json.load(open(os.path.join(os.path.dirname(refdata.__file__), "countries.json")))
NOMBRE = {c["pointer"]: c["name"] for c in _P}


def _exe(edicion):
    p = os.path.join(RAIZ, "gamedata", edicion, "manager.exe")
    if not os.path.exists(p):
        pytest.skip(f"sin el manager.exe de {edicion}")
    with open(p, "rb") as f:
        return f.read()


@pytest.mark.parametrize("edicion,grupos", [
    ("pcf5", {"europa": 34}),
    ("pcf5oro", {"europa": 36}),
    ("pcf6", {"sudamerica": 10, "europa": 47}),
    ("pcf6oro", {"sudamerica": 10, "europa": 47}),
])
def test_las_cuatro_ediciones_tienen_sus_listas(edicion, grupos):
    sl = MGR.country_slots(_exe(edicion))
    assert sl and {k: len(v) for k, v in sl.items()} == grupos


@pytest.mark.parametrize("edicion,fichero", [
    ("pcf6oro", "EQ022022.PKF"), ("pcf6", "EQ022022.PKF"),
    ("pcf5oro", "EQ022022.PKF"), ("pcf5", "EQUIPOS.PKF"),
])
def test_todos_los_paises_de_la_lista_tienen_equipos(edicion, fichero):
    """La comprobación que dice que los offsets son los buenos: si estuvieran corridos,
    saldrían códigos de países sin un solo equipo."""
    p = os.path.join(RAIZ, "gamedata", edicion, fichero)
    if not os.path.exists(p):
        pytest.skip(f"sin la base de {edicion}")
    with open(p, "rb") as f:
        pf = E.parse(f.read())
    con_equipos = {t.country for t in pf.teams if t.country}
    for grupo, codigos in MGR.country_slots(_exe(edicion)).items():
        sin = [NOMBRE.get(c, c) for c in codigos if c not in con_equipos]
        assert not sin, f"{edicion}/{grupo}: países sin equipos en la lista → {sin}"
        assert len(set(codigos)) == len(codigos), f"{edicion}/{grupo}: países repetidos"


def test_andorra_no_esta_ofrecida_en_6_0_oro():
    """El caso concreto del foro."""
    sl = MGR.country_slots(_exe("pcf6oro"))
    todos = {c for v in sl.values() for c in v}
    assert 75 not in todos, "Andorra no debería estar en las listas de fábrica"
    assert 34 not in todos and 61 not in todos, "Islas Feroe y USA tampoco"


def test_se_puede_cambiar_un_pais_por_otro():
    """LA FUNCIÓN: intercambiar. Macedonia (39) sale, Andorra (75) entra."""
    d = bytearray(_exe("pcf6oro"))
    eur = MGR.country_slots(bytes(d))["europa"]
    assert 39 in eur
    nuevo = [75 if c == 39 else c for c in eur]
    assert MGR.countries_write(d, {"europa": nuevo}) is True
    despues = MGR.country_slots(bytes(d))["europa"]
    assert 75 in despues and 39 not in despues
    assert len(despues) == len(eur), "el número de plazas no cambia"


def test_no_se_puede_alargar_ni_repetir():
    """La tabla no se puede alargar en su sitio, y un país repetido rompería el recorrido:
    en los dos casos NO se escribe nada."""
    original = _exe("pcf6oro")
    eur = MGR.country_slots(original)["europa"]
    for intento in (eur + [75], eur[:-1], [eur[0]] * len(eur)):
        d = bytearray(original)
        MGR.countries_write(d, {"europa": intento})
        assert MGR.country_slots(bytes(d))["europa"] == eur, "no debía tocarse"


def test_un_manager_desconocido_no_se_toca():
    assert MGR.country_slots(b"\x00" * 5000) is None
    d = bytearray(b"\x00" * 5000)
    assert MGR.countries_write(d, {"europa": [1, 2, 3]}) is False
