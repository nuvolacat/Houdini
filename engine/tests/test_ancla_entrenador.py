"""El ancla del entrenador, y por qué un DBC de 6.0 original salía ilegible.

Un mod de **6.0 original** con solo España actualizada cerraba el juego al cargar la base de
datos. El culpable estaba en el **Cádiz**: el parser situaba a su entrenador 775 bytes más allá
de donde está, en mitad de otro texto, y al escribirle encima el entrenador nuevo que trae el
import (Albert Celades) su DBC quedaba ilegible a partir de ese punto. Y el DBC es justo lo que
el juego lee al crear liga.

Pasaba porque el ancla se elegía con un filtro que miraba si detrás del nombre largo caminaban
tres textos de **menos de 2.000 bytes**. El perfil del entrenador del Cádiz mide 4.368, así que
lo descartaba y se quedaba con el primer `02` casual que sí lo cumplía. Ahora manda un criterio
exacto, el de la gramática de PCx-Utils (`Staff.hs`): la cola del bloque es una lista de fichas
marcadas, así que saltando entrenadores desde el candidato hay que aterrizar JUSTO en el primer
jugador. El filtro viejo queda de reserva por si ningún candidato cuadra.

De propina aparecieron seis entrenadores que antes salían vacíos o con una letra suelta, y son
los reales de aquella temporada: Juande Ramos (Barcelona B), Maceda (Badajoz), Luis Ángel Duque
(Getafe), Bianchi (Boca), Rezza (Belgrano) y Aldridge (Tranmere).
"""
import os

import pytest

from houdini_engine.formats import dbc as DBC
from houdini_engine.formats import equipos_pkf as E

RAIZ = os.path.join(os.path.dirname(__file__), "..", "..")


def _base(edicion, fichero):
    p = os.path.join(RAIZ, "gamedata", edicion, fichero)
    if not os.path.exists(p):
        pytest.skip(f"sin {edicion} en gamedata")
    with open(p, "rb") as f:
        return E.parse(f.read())


def _equipo(pf, nombre):
    return next(t for t in pf.teams if (t.short_name or "") == nombre)


def test_el_cadiz_ancla_en_su_entrenador():
    """LA REGRESIÓN."""
    t = _equipo(_base("pcf6", "EQ022022.PKF"), "Cádiz")
    assert t.coach_short == "Ramón Blanco"
    assert t.coach_long.startswith("Ramon Blanco")


@pytest.mark.parametrize("edicion,fichero,equipo,entrenador", [
    ("pcf6", "EQ022022.PKF", "Cádiz", "Ramón Blanco"),
    ("pcf6oro", "EQ022022.PKF", "Barcelona B", "Juande Ramos"),
    ("pcf6oro", "EQ022022.PKF", "Badajoz", "Maceda"),
    ("pcf6oro", "EQ022022.PKF", "Getafe", "Luis Angel Duque"),
    ("apertura98", "EQ003003.PKF", "Boca", "Bianchi"),
    ("premier6", "EQ030022.PKF", "Tranmere Rov", "Aldridge"),
])
def test_los_que_estaban_mal_ya_salen(edicion, fichero, equipo, entrenador):
    """Los seis que salían vacíos o con basura. Son entrenadores REALES de esa temporada."""
    assert _equipo(_base(edicion, fichero), equipo).coach_short == entrenador


def test_ningun_equipo_se_queda_sin_entrenador():
    """El criterio nuevo no puede quitar ninguno de los que ya se localizaban. Medido: en las
    ocho bases cambian 14 equipos y los 14 son a mejor; ninguno pierde el suyo."""
    esperado = {"pcf6": 482, "pcf6oro": 962, "pcf5": 260, "pcf5oro": 481,
                "apertura97": 426, "apertura98": 471, "premier6": 480, "calcio6": 432}
    visto = 0
    for edicion, minimo in esperado.items():
        for fichero in ("EQ022022.PKF", "EQ003003.PKF", "EQ030022.PKF",
                        "EQ036022.PKF", "EQUIPOS.PKF"):
            p = os.path.join(RAIZ, "gamedata", edicion, fichero)
            if not os.path.exists(p):
                continue
            with open(p, "rb") as f:
                pf = E.parse(f.read())
            con = sum(1 for t in pf.teams if getattr(t, "coach_short", None))
            assert con >= minimo, f"{edicion}: {con} entrenadores, se esperaban {minimo}"
            visto += 1
            break
    if not visto:
        pytest.skip("sin bases de v5/6 en gamedata")


def test_no_se_escribe_donde_no_hay_entrenador():
    """El guardarraíl: aunque el ancla se equivocara, `rebuild_prefix_coach` no puede escribir
    en un sitio que no empiece por la marca `02`. Ante la duda, deja el bloque como estaba."""
    pf = _base("pcf6", "EQ022022.PKF")
    tid = next(i for i, t in enumerate(pf.teams) if (t.short_name or "") == "Cádiz")
    t = pf.teams[tid]
    blk = DBC.block_for_team(pf, tid)
    falso = type(t)(**{k: getattr(t, k) for k in t.__dataclass_fields__}) \
        if hasattr(t, "__dataclass_fields__") else None
    if falso is None:
        pytest.skip("el registro de equipo no es un dataclass")
    falso.coaches = [dict(t.coaches[0], short_off=t.coaches[0]["short_off"] + 40,
                          long_off=t.coaches[0]["long_off"] + 40)]
    assert E.rebuild_prefix_coach(blk.prefix, falso, "X", "Y") == blk.prefix
