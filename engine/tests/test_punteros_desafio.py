"""Los punteros reservados a las selecciones del Desafío no se reparten a jugadores nuevos.

En 5.0 y 6.0 hay **33 punteros de jugador** que el juego usa para armar las selecciones de
**Europa y América del Desafío**. El dato no está en la base —por eso no se podía deducir
mirando el fichero—, viene de la lista de punteros especiales que circula en la comunidad.

Comprobado contra la base de 6.0 Oro: los 33 existen y son justo quienes uno esperaría —Hierro,
Redondo y Raúl, Figo, Guardiola, Mijatovic, Kluivert, Köhler, Zanetti, Ronaldo—. Y la prueba que
lo cierra: **31 de los 33 cuadran con la nacionalidad** que marca la lista. Los dos que no,
Redondo y Aldair, son naturalizados, así que el Desafío los cuenta por su país de NACIMIENTO
(Aldair tiene dos fichas y la suya dice Brasil).

Por qué importa: al crear un jugador se le da el primer puntero libre. Si un «Actualizar todo»
se lleva por delante a Raúl o a Figo —y se lo lleva, porque son plantillas de 1999—, su puntero
queda libre y el siguiente jugador nuevo se lo queda, con lo que acaba en la selección
continental sin que nadie lo haya pedido.
"""
import os
import sys

import pytest

RAIZ = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, os.path.join(RAIZ, "engine"))

EUROPA = {
    "Albania", "Alemania", "Andorra", "Armenia", "Austria", "Azerbaiyán", "Bielorusia",
    "Bosnia", "Bulgaria", "Bélgica", "Cataluña", "Chipre", "Croacia", "Dinamarca", "Escocia",
    "Eslovaquia", "Eslovenia", "España", "Estonia", "Finlandia", "Francia", "Georgia",
    "Grecia", "Holanda", "Hungría", "Inglaterra", "Irlanda", "Irlanda del Norte", "Islandia",
    "Islas Feroe", "Israel", "Italia", "Letonia", "Lituania", "Luxemburgo", "Macedonia",
    "Malta", "Moldavia", "Noruega", "País de Gales", "Polonia", "Portugal",
    "República Checa", "Rumania", "Rusia", "San Marino", "Serbia", "Suecia", "Suiza",
    "Turquía", "Ucrania", "Yugoslavia",
}
# lado que le asigna la lista de punteros especiales
LADO = {10: "E", 12: "A", 20: "E", 31: "E", 34: "E", 144: "E", 1802: "E", 1870: "E",
        1872: "E", 1995: "E", 2004: "E", 2685: "E", 2814: "E", 3149: "A", 3371: "E",
        3385: "E", 3411: "A", 3612: "A", 4067: "A", 4150: "A", 4302: "A", 4327: "A",
        4331: "A", 7278: "A", 8452: "E", 8492: "E", 8577: "A", 8837: "A", 8857: "A",
        9911: "A", 14626: "A", 16856: "A", 16875: "A"}


def test_son_los_33_de_la_lista():
    from houdini_engine.formats.block import PUNTEROS_DESAFIO
    assert set(PUNTEROS_DESAFIO) == set(LADO)


def test_no_se_reparte_uno_libre_habiendo_otro():
    """Lo que de verdad se arregla: con el 10 libre (Hierro borrado por un import) y el 55
    también, el jugador nuevo se lleva el 55."""
    from houdini_engine.formats.block import free_pointer
    usados = set(range(1, 60)) - {10, 55}
    assert free_pointer(usados) == 55


def test_tampoco_dentro_del_rango_del_equipo():
    """El primer intento es el bloque de 50 del club, y ahí también hay que esquivarlos: el
    puntero 10 cae en el bloque del Barcelona (1-50)."""
    from houdini_engine.formats.block import free_pointer
    usados = set(range(1, 51)) - {10, 34}      # los dos libres son del Desafío
    # el bloque del Barça (ptr 1) está lleno salvo esos dos → se va fuera del bloque
    assert free_pointer(usados, team_pointer=1) == 51


def test_se_usan_como_ultimo_recurso():
    """Mejor un jugador en la selección de Europa que un import que revienta por falta de
    sitio. Si no queda NADA más, se reparten."""
    from houdini_engine.formats.block import MAX_PLAYER_POINTER, free_pointer
    usados = set(range(1, MAX_PLAYER_POINTER + 1)) - {20}
    assert free_pointer(usados) == 20


def test_sigue_fallando_cuando_no_queda_ni_uno():
    from houdini_engine.formats.block import MAX_PLAYER_POINTER, SinPunteros, free_pointer
    with pytest.raises(SinPunteros):
        free_pointer(set(range(1, MAX_PLAYER_POINTER + 1)))


def test_los_33_existen_en_la_base_del_juego():
    """El dato que respalda todo: si fueran punteros inventados, no estarían en el fichero."""
    from houdini_engine.formats import equipos_pkf as E
    ruta = os.path.join(RAIZ, "gamedata", "pcf6oro", "EQ022022.PKF")
    if not os.path.exists(ruta):
        pytest.skip("sin la base de 6.0 Oro")
    with open(ruta, "rb") as f:
        pf = E.parse(f.read(), "EQ022022.PKF")
    usados = {j.pointer for t in pf.teams for j in t.players if j.pointer}
    faltan = [p for p in LADO if p not in usados]
    assert not faltan, f"{len(faltan)} punteros especiales no están en la base: {faltan[:6]}"


def test_y_son_los_jugadores_que_uno_esperaria():
    from houdini_engine.formats import equipos_pkf as E
    ruta = os.path.join(RAIZ, "gamedata", "pcf6oro", "EQ022022.PKF")
    if not os.path.exists(ruta):
        pytest.skip("sin la base de 6.0 Oro")
    with open(ruta, "rb") as f:
        pf = E.parse(f.read(), "EQ022022.PKF")
    nombre = {}
    for t in pf.teams:
        for j in t.players:
            if j.pointer in LADO:
                nombre.setdefault(j.pointer, (j.short_name or "").strip())
    for ptr, quien in ((10, "Hierro"), (20, "Raúl"), (31, "Figo"),
                       (34, "Guardiola"), (9911, "Ronaldo")):
        assert nombre.get(ptr) == quien, f"{ptr}: sale «{nombre.get(ptr)}» y no {quien}"


def test_el_lado_cuadra_con_la_nacionalidad():
    """La prueba que convierte la lista en un hecho: los marcados EUROPA son europeos y los
    marcados AMERICA, americanos. Solo fallan Redondo y Aldair, que son naturalizados — el
    Desafío los cuenta por su país de nacimiento."""
    from houdini_engine import refdata
    from houdini_engine.formats import equipos_pkf as E
    ruta = os.path.join(RAIZ, "gamedata", "pcf6oro", "EQ022022.PKF")
    if not os.path.exists(ruta):
        pytest.skip("sin la base de 6.0 Oro")
    pn = {c["pointer"]: c["name"] for c in refdata.countries()}
    with open(ruta, "rb") as f:
        pf = E.parse(f.read(), "EQ022022.PKF")
    paises = {}
    for t in pf.teams:
        for j in t.players:
            if j.pointer in LADO:
                paises.setdefault(j.pointer, set()).add(pn.get(getattr(j, "country", None), "?"))
    cuadran = []
    for ptr, lado in LADO.items():
        if ptr not in paises:
            continue
        # una ficha compartida puede traer dos países: basta con que UNO cuadre
        cuadran.append(any((p in EUROPA) == (lado == "E") for p in paises[ptr]))
    assert len(cuadran) > 30
    assert sum(cuadran) >= len(cuadran) - 1, (
        f"solo cuadran {sum(cuadran)} de {len(cuadran)}: revisar la lista")
