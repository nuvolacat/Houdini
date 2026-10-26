"""Dos tablas de división no pueden solaparse en el manager.exe.

Cada plaza de liga es un u16 en un offset fijo. Si una tabla declara más plazas de las que
tiene, al escribirla se meten códigos DENTRO de la tabla siguiente: el equipo acaba en dos
divisiones a la vez y el juego se cuelga al entrar en esa competición. Es el fallo que ya
documenta `pcf7_manager.rellena_divisiones`.

Pasaba de verdad: «Nacional B» de Argentina estaba mapeada con **20 plazas** cuando la tabla es
de **16** (Primera B Interior), y las cuatro que sobraban caían sobre Primera B Metropolitana,
que empieza justo donde acaba la otra. Y Argentina es jugable en PCF2001, así que el import la
recoloca de verdad. Encontrado el 21-sep-2026 comparando con el mapa del editor de
pcfutbolmania y leyendo el binario.

Este test no mira Argentina: mira TODAS las tablas de TODAS las ediciones, que es lo que hace
falta para que no vuelva a colarse ninguna.
"""
import os
import struct
import sys

import pytest

RAIZ = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, os.path.join(RAIZ, "engine"))


def _tablas():
    try:
        from houdini_engine.formats import pcf2000_manager as PM
        from houdini_engine.formats import pcf7_manager as P7
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"sin el motor ({e})")
    out = {}
    for variante, filas in PM.DIVISIONS.items():
        out[f"pcf{variante}"] = list(filas)
    tablas7 = getattr(P7, "DIVISIONS", None)
    if isinstance(tablas7, (list, tuple)):
        out["pcf7"] = list(tablas7)
    elif isinstance(tablas7, dict):
        for k, v in tablas7.items():
            out[f"pcf7:{k}"] = list(v)
    return out


@pytest.mark.parametrize("edicion", list(_tablas()))
def test_ninguna_tabla_pisa_a_la_siguiente(edicion):
    filas = sorted((f for f in _tablas()[edicion] if len(f) >= 4), key=lambda f: f[2])
    assert filas, edicion
    for (p1, e1, o1, n1), (p2, e2, o2, n2) in zip(filas, filas[1:]):
        fin = o1 + n1 * 2
        assert fin <= o2, (
            f"{edicion}: «{e1}» (offset {o1}, {n1} plazas) acaba en {fin} y «{e2}» empieza "
            f"en {o2}: se pisan {(fin - o2) // 2} plaza(s)")


@pytest.mark.parametrize("edicion,fichero", [
    ("2001", os.path.join(RAIZ, "gamedata", "PCF2001", "manager.exe")),
    ("2000", os.path.join(RAIZ, "gamedata", "PCF2000", "manager.exe")),
])
def test_todas_las_plazas_llevan_un_equipo_de_verdad(edicion, fichero):
    """Una tabla mal acotada se nota en el contenido: donde no hay tabla, los u16 no son
    códigos de equipo. Se exige que la inmensa mayoría de las plazas lo sean."""
    from houdini_engine.formats import pcf2000_manager as PM
    if not os.path.exists(fichero):
        pytest.skip(f"sin el manager.exe de {edicion}")
    with open(fichero, "rb") as f:
        raw = f.read()
    # Se valida contra los equipos de LA PROPIA BASE, no contra el catálogo comunitario: ese
    # no cubre los clubes pequeños (2ªB, Tercera) y daría por malas plazas que son correctas.
    from houdini_engine.formats import pcf2000 as FDI
    base = os.path.join(os.path.dirname(fichero), "DBDAT")
    eq = next((os.path.join(base, n) for n in ("eq00022.fdi", "EQ00022.FDI")
               if os.path.exists(os.path.join(base, n))), None)
    if eq is None:
        pytest.skip(f"sin el fichero de equipos de {edicion}")
    with open(eq, "rb") as f:
        validos = {r.code for r in FDI.parse(f.read(), "eq00022.fdi", variant=edicion).records}
    for pais, etiqueta, off, n in PM.DIVISIONS[edicion]:
        if off + n * 2 > len(raw):
            continue
        vals = [struct.unpack_from("<H", raw, off + i * 2)[0] for i in range(n)]
        # 0 = plaza vacía, legítima. Lo que no vale es un número que no es de nadie.
        raros = [v for v in vals if v and v not in validos]
        assert len(raros) <= max(2, n // 3), (
            f"{edicion} «{etiqueta}» (offset {off}, {n} plazas): {len(raros)} valores que no "
            f"son ningún equipo — la tabla probablemente no mide lo que decimos")
