"""Nombre del entrenador en v5/6: reparto del hueco y ampliación por DBC.

El fichero guarda cada cadena con su hueco `u16` y la edición in-place lo respeta, así que
el tope del míster era el largo del nombre que le puso Dinamic —de 4 a 23 caracteres según
el equipo—. Los dos nombres van PEGADOS, de modo que lo único que el bloque obliga a
respetar es la SUMA; y lo que ni así cabe se guarda entero en el DBC, que no arrastra esa
restricción (es lo que hacen también los editores de la comunidad).
"""
import glob
import os

import pytest

from houdini_engine.formats import dbc as DBC
from houdini_engine.formats import equipos_pkf as E

_GD = os.path.join(os.path.dirname(__file__), "..", "..", "gamedata")


def _pkf(ed):
    fs = [x for x in glob.glob(os.path.join(_GD, ed, "**", "*"), recursive=True)
          if x.lower().endswith(".pkf") and os.path.basename(x).lower().startswith("eq")]
    if not fs:
        pytest.skip(f"sin gamedata de {ed}")
    return open(fs[0], "rb").read()


def _equipo_con_mister(pf):
    for i, t in enumerate(pf.teams):
        if (getattr(t, "coaches", None) or []) and E.coach_names_pool(pf, t, 0) >= 12:
            return i, t
    pytest.skip("ningún equipo con entrenador editable")


def test_el_hueco_es_de_la_pareja():
    """El hueco repartible es la suma de los dos nombres, que van contiguos."""
    pf = E.parse(bytearray(_pkf("pcf6oro")))
    _i, t = _equipo_con_mister(pf)
    lim = E.coach_text_limits(pf, t, 0)
    assert E.coach_names_pool(pf, t, 0) == lim["short_name"] + lim["long_name"]


def test_el_corto_puede_crecer_a_costa_del_largo():
    """Lo que arregla el bug: un nombre corto ya no está encadenado a SU tramo."""
    pf = E.parse(bytearray(_pkf("pcf6oro")))
    i, t = _equipo_con_mister(pf)
    n = len(pf.raw)
    pool = E.coach_names_pool(pf, t, 0)
    corto_original = len(t.coach_short)
    nuevo = "A" * (pool - 2)
    assert len(nuevo) > corto_original          # imposible antes de repartir
    E.set_coach_names(pf, t, 0, nuevo, "Bo")
    assert len(pf.raw) == n                     # el bloque NO cambia de tamaño
    releido = E.parse(bytearray(pf.raw))
    assert releido.teams[i].coach_short == nuevo


def test_los_textos_de_bbdd_del_mister_no_se_mueven():
    """El perfil y el palmarés van justo detrás de los nombres: si el reparto descuadrara
    la zona, se los llevaría por delante."""
    pf = E.parse(bytearray(_pkf("pcf6oro")))
    i, t = _equipo_con_mister(pf)
    antes = E.coach_texts_at(pf, t, 0)
    pool = E.coach_names_pool(pf, t, 0)
    E.set_coach_names(pf, t, 0, "X" * (pool - 4), "Yes")
    assert E.coach_texts_at(E.parse(bytearray(pf.raw)), E.parse(bytearray(pf.raw)).teams[i], 0) == antes


def test_pasarse_de_la_suma_se_rechaza():
    pf = E.parse(bytearray(_pkf("pcf6oro")))
    _i, t = _equipo_con_mister(pf)
    pool = E.coach_names_pool(pf, t, 0)
    with pytest.raises(E.TextTooLong):
        E.set_coach_names(pf, t, 0, "A" * pool, "B" * pool)


def test_el_recorte_nunca_deja_un_nombre_vacio():
    """Al míster se le localiza por gramática dentro del bloque; un nombre vacío lo dejaría
    imposible de reencontrar y el equipo se quedaría sin entrenador."""
    for pool in range(4, 40):
        corto, largo = E.fit_coach_names(pool, "A" * 80, "B" * 80)
        assert len(corto) >= 2 and len(largo) >= 2
        assert len(corto) + len(largo) <= pool
    assert E.fit_coach_names(3, "AAA", "BBB") is None


def test_el_recorte_respeta_el_campo_editado():
    assert E.fit_coach_names(10, "12345678", "abcdefgh") == ("12345678", "ab")
    assert E.fit_coach_names(10, "12345678", "abcdefgh", "long_name") == ("12", "abcdefgh")
    assert E.fit_coach_names(30, "corto", "largo") == ("corto", "largo")   # cabe: no toca


def test_el_dbc_no_tiene_tope():
    """En un DBC la longitud de cada cadena se calcula de la propia cadena. Comprobado
    también en mods de la comunidad: uno distribuido pasa un 'Kisel' (hueco de 5) a
    'Giovanni Trapattoni'."""
    pf = E.parse(bytearray(_pkf("pcf6oro")))
    i, t = _equipo_con_mister(pf)
    blk = DBC.block_for_team(pf, i)
    jugadores = len(blk.players)
    largo = "Sir Robert William Robson Caballero del Imperio Britanico"
    blk.prefix = E.rebuild_prefix_coach(blk.prefix, t, largo, "Bobby Robson")
    leido = E.parse(bytearray(DBC.write_dbc(blk)), "EQ960001.DBC")
    assert leido.teams[0].coach_short == largo
    assert leido.teams[0].coach_long == "Bobby Robson"
    assert len(leido.teams[0].players) == jugadores      # la plantilla, intacta


def test_valdano_no_se_pierde_por_el_tope_del_anclaje():
    """De fábrica hay un nombre de 43 caracteres —'Jorge Alberto Francisco Valdano
    Castellanos'— y con el tope viejo (40) su registro se descartaba entero: el Valencia
    salía entrenado por Ranieri."""
    pf = E.parse(bytearray(_pkf("pcf6oro")))
    assert any("Valdano" in (t.coach_long or "") for t in pf.teams)


def test_una_zona_de_entrenador_degenerada_sigue_sin_tocarse():
    """Los bloques con el míster degenerado de fábrica crashean el juego si se escriben en
    ellos (validado con el Levante de 6.0 Oro): ahí el hueco repartible es 0."""
    pf = E.parse(bytearray(_pkf("pcf6oro")))
    malos = [t for t in pf.teams
             if (getattr(t, "coaches", None) or []) and not E.coach_area_sane(pf.raw, t)]
    for t in malos:
        assert E.coach_names_pool(pf, t, 0) == 0
        with pytest.raises(KeyError):
            E.set_coach_names(pf, t, 0, "Pep", "Pep Guardiola")
