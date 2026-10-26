"""Las divisiones españolas de las ediciones ORIGINALES de 5.0 y 6.0.

Un usuario montó un mod de **6.0 original**, le dio a «Actualizar España» y las divisiones
quedaron hechas un destrozo. La causa: las tablas de división viven en el `manager.exe` y el
mapa que las localiza va por TAMAÑO del ejecutable, así que solo conocía las dos ediciones de
Oro. Sin tablas, `leagues.plan_country` devuelve None —no se recoloca— y `repair_divisions` no
puede arreglar nada; el import cambiaba las plantillas dejando los equipos del 97-98 donde
estaban.

Los offsets NO se copiaron de ningún sitio: se buscaron en el binario por ESTRUCTURA. La zona de
divisiones es una sucesión de tramos de u16 que son TODOS punteros canónicos de clubes españoles
de esa misma base, y 6.0 original tiene la misma forma que 6.0 Oro tramo a tramo y a las mismas
distancias (+0 de 40 valores, +160 de 64, +712 Primera, +1160 Segunda, +1534 la 2ªB), de donde
sale el desplazamiento. En 5.0 original las tres tablas van SEGUIDAS en vez de separadas.

La comprobación de verdad no son los offsets: es que lo que se lee ahí sean las divisiones
REALES de la temporada de cada edición.
"""
import os

import pytest

from houdini_engine.formats import equipos_pkf as E
from houdini_engine.formats import manager as MGR

RAIZ = os.path.join(os.path.dirname(__file__), "..", "..")


def _slots(edicion):
    p = os.path.join(RAIZ, "gamedata", edicion, "manager.exe")
    if not os.path.exists(p):
        pytest.skip(f"sin el manager.exe de {edicion}")
    with open(p, "rb") as f:
        sl = MGR.division_slots(f.read())
    assert sl, f"{edicion}: el manager.exe no está soportado"
    return sl


@pytest.mark.parametrize("edicion,primera,segunda", [
    ("pcf5", 22, 20),        # 95-96: la Primera tuvo 22 equipos
    ("pcf5oro", 22, 20),
    ("pcf6", 20, 22),        # 97-98: la Primera bajó a 20 y la Segunda subió a 22
    ("pcf6oro", 20, 22),
])
def test_las_cuatro_ediciones_dan_sus_plazas(edicion, primera, segunda):
    """LA REGRESIÓN: las dos originales no daban ninguna."""
    sl = _slots(edicion)
    assert len(sl["primera"]) == primera
    assert len(sl["segunda"]) == segunda
    assert [len(g) for g in sl["grupos2b"]] == [20, 20, 20, 20]


@pytest.mark.parametrize("edicion", ["pcf5", "pcf5oro", "pcf6", "pcf6oro"])
def test_ninguna_plaza_repetida(edicion):
    """Un offset medio corrido se nota en cuanto sale un puntero dos veces."""
    sl = _slots(edicion)
    for nombre, tabla in [("primera", sl["primera"]), ("segunda", sl["segunda"])] + \
            [(f"2ªB G{i+1}", g) for i, g in enumerate(sl["grupos2b"])]:
        assert len(set(tabla)) == len(tabla), f"{edicion}/{nombre} repite plazas"


def test_la_primera_de_6_0_original_son_sus_equipos():
    """Que los offsets caigan donde deben no se comprueba con el número, sino MIRANDO LO QUE
    PONE. En 6.0 original la tabla da la Primera del 97-98: Madrid, Barcelona, Deportivo,
    Betis, At. Madrid, Athletic, Valladolid, Real Sociedad, Tenerife, Valencia, Compostela,
    Espanyol, Racing, Zaragoza, Sporting, Celta, Oviedo, Mérida, Salamanca y Mallorca."""
    p = os.path.join(RAIZ, "gamedata", "pcf6", "EQ022022.PKF")
    cont = os.path.join(RAIZ, "gamedata", "pcf6", "NANOESC.PKF")
    if not (os.path.exists(p) and os.path.exists(cont)):
        pytest.skip("sin la base de 6.0 original")
    from houdini_engine.formats import imagenes_pkf as IM
    with open(p, "rb") as f:
        pf = E.parse(f.read())
    with open(cont, "rb") as f:
        punteros = [int(n[4:8]) for n in IM.entries(f.read())
                    if len(n) >= 8 and n[4:8].isdigit()]
    nombre = {punteros[i]: t.short_name for i, t in enumerate(pf.teams) if i < len(punteros)}
    sl = _slots("pcf6")
    assert [nombre.get(x, "?") for x in sl["primera"][:3]] == \
        ["Real Madrid C.F.", "F.C. Barcelona", "R.C. Deportivo"]


def test_en_5_0_original_las_tres_tablas_van_seguidas():
    """La diferencia de formato entre las dos originales: en 5.0 no hay huecos entre Primera,
    Segunda y los cuatro grupos, y las plazas van en orden ascendente porque Dinamic repartió
    los punteros por divisiones. (Los nombres se verificaron aparte con la sesión real: la
    Primera del 95-96 empieza por Barcelona, Deportivo y Zaragoza.)"""
    sl = _slots("pcf5")
    assert sl["primera"][:3] == [1, 2, 3]
    seguidas = sl["primera"] + sl["segunda"] + [x for g in sl["grupos2b"] for x in g]
    assert seguidas == sorted(seguidas), "las plazas de 5.0 original van en orden"
    assert len(set(seguidas)) == len(seguidas) == 122


def test_una_edicion_desconocida_no_inventa_nada():
    """Ante un manager.exe que no conocemos, se devuelve None y NO se recoloca: es mejor
    dejar las divisiones como están que colocarlas a ciegas, que es justo lo que se vio."""
    assert MGR.division_slots(b"\x00" * 1000) is None
