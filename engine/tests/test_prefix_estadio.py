"""Cambiar el ESTADIO por la vía DBC no puede descuadrar el bloque.

Entre el campo del estadio y el nombre largo hay **2 bytes** que no modelamos (están en
todos los equipos, medidos en 6.0 Oro). `rebuild_prefix_names` los conservaba sin querer
mientras no se tocaba el estadio —copiaba el tramo entero— pero al escribir un estadio nuevo
escribía solo su campo y esos 2 bytes se perdían. El bloque quedaba descuadrado y su DBC ya
no se podía releer; al juego le impedía arrancar («la aplicación no puede continuar») sin
decir por qué.

Solo saltaba cuando el estadio NO cabía en su hueco y venía por override: 3 equipos de 127
en el mod que lo destapó, reportado en el foro el 2026-08-21.
"""
import glob
import os

import pytest

from houdini_engine.formats import block as B
from houdini_engine.formats import dbc as DBC
from houdini_engine.formats import equipos_pkf as E

_GD = os.path.join(os.path.dirname(__file__), "..", "..", "gamedata")


def _pkf(ed="pcf6oro"):
    fs = [x for x in glob.glob(os.path.join(_GD, ed, "**", "*"), recursive=True)
          if x.lower().endswith(".pkf") and os.path.basename(x).lower().startswith("eq")]
    if not fs:
        pytest.skip(f"sin gamedata de {ed}")
    return E.parse(bytearray(open(fs[0], "rb").read()))


def _equipo(pf):
    """Un nacional con estadio y bloque exportable."""
    for i, t in enumerate(pf.teams):
        if not (t.complete and not t.foreign and t.players):
            continue
        o = t._off
        if all(k in o for k in ("short", "stadium", "long", "capacity")):
            return i, t
    pytest.skip("ningún equipo con la cabecera completa")


def _relee(prefix, players, foreign=False):
    d = DBC.write_dbc(B.Block(prefix=prefix, players=players, foreign=foreign))
    try:
        return bool(E.parse(bytearray(d), "x.DBC").teams)
    except Exception:  # noqa: BLE001
        return False


def test_el_estadio_nuevo_no_rompe_el_bloque():
    """La prueba del caso real: un estadio MÁS LARGO que el hueco original."""
    pf = _pkf()
    i, t = _equipo(pf)
    blk = DBC.block_for_team(pf, i)
    assert _relee(blk.prefix, blk.players), "el bloque original ya no se relee"
    p = E.rebuild_prefix_names(blk.prefix, t, t.short_name, t.long_name,
                               stadium="Estadio Municipal de Nombre Larguísimo")
    assert _relee(p, blk.players)


def test_da_igual_que_el_estadio_sea_mas_corto():
    pf = _pkf()
    i, t = _equipo(pf)
    blk = DBC.block_for_team(pf, i)
    p = E.rebuild_prefix_names(blk.prefix, t, t.short_name, t.long_name, stadium="A")
    assert _relee(p, blk.players)


def test_conserva_los_2_bytes_que_hay_entre_el_estadio_y_el_nombre_largo():
    """Lo que se perdía. Se comprueba por TAMAÑO: el bloque nuevo tiene que crecer o menguar
    exactamente lo que cambia el texto, ni un byte más."""
    pf = _pkf()
    i, t = _equipo(pf)
    blk = DBC.block_for_team(pf, i)
    base, o = t.sig_off, t._off
    rst, rl = o["stadium"] - base, o["long"] - base
    viejo = int.from_bytes(bytes(blk.prefix[rst:rst + 2]), "little")
    nuevo = "Un estadio cualquiera"
    p = E.rebuild_prefix_names(blk.prefix, t, t.short_name, t.long_name, stadium=nuevo)
    assert len(p) - len(blk.prefix) == len(nuevo) - viejo
    # y ese hueco intermedio sigue ahí, byte a byte
    entre = bytes(blk.prefix[rst + 2 + viejo:rl])
    assert entre and entre in p


def test_sin_estadio_nuevo_se_respeta_lo_que_habia():
    """El camino que ya funcionaba: no tocar el estadio deja su tramo intacto byte a byte."""
    pf = _pkf()
    i, t = _equipo(pf)
    blk = DBC.block_for_team(pf, i)
    base, o = t.sig_off, t._off
    tramo = bytes(blk.prefix[o["stadium"] - base:o["long"] - base])
    p = E.rebuild_prefix_names(blk.prefix, t, t.short_name, t.long_name)
    assert _relee(p, blk.players)
    assert tramo in p
