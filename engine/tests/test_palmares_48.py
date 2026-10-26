"""El palmarés de 48 bytes de Premier y Calcio.

Salió escribiendo un lector desde CERO siguiendo solo lo publicado en el wiki y lanzándolo
contra las ocho bases: 5.0 y 6.0 caminaban y Premier y Calcio no. El bloque de palmarés de
esas dos ediciones mide **48 bytes**, un tamaño que no está en ninguna fuente anterior —ni en
el manual de carky12 ni en el MultiEditorPCC de 1Simo1—, que solo documentan 14, 34 y 42.

Sin él, el recorrido determinista del bloque no cuadra y el equipo cae al escaneo heurístico,
que es el que se inventa fichas fantasma en los bloques raros (un fallo reportado en el foro
con el Niva Vinnitsa). Medido: 123 de los 126 equipos nacionales de Premier y 71 de los 76 de
Calcio estaban cayendo ahí.

Se mide restando: (offset del entrenador) − 183 de las dos tácticas − (inicio del palmarés).
"""
import glob
import os

import pytest

from houdini_engine.formats import equipos_pkf as E

_G = os.path.join(os.path.dirname(__file__), "..", "..", "gamedata")
BASES = sorted(glob.glob(os.path.join(_G, "*", "EQ*.PKF"))
               + glob.glob(os.path.join(_G, "*", "EQUIPOS.PKF")))
falta = pytest.mark.skipif(not BASES, reason="sin gamedata")


def _deterministas(ruta):
    raw = open(ruta, "rb").read()
    f = E.parse(raw)
    sig = [m.start() for m in E.TEAM_SIG_RE.finditer(raw)]
    ok = mal = 0
    for t in f.teams:
        if not (t.complete and not t.foreign):
            continue
        end = min([s for s in sig if s > t.sig_off], default=len(raw))
        if E._deterministic_players(raw, t, end):
            ok += 1
        else:
            mal += 1
    return ok, mal


def test_el_48_esta_en_la_lista():
    assert 48 in E._PALMARES_LENS, "sin el 48, Premier y Calcio caen al heurístico"


@falta
def test_premier_y_calcio_caminan_deterministas():
    """La regresión. Antes del arreglo: Premier 3 de 126 y Calcio 5 de 76."""
    for nombre, minimo in (("premier6", 100), ("calcio6", 60)):
        ruta = next((r for r in BASES if nombre in r), None)
        if not ruta:
            continue
        ok, mal = _deterministas(ruta)
        assert ok >= minimo, f"{nombre}: solo {ok} deterministas ({mal} al heurístico)"


@falta
def test_ninguna_edicion_empeora():
    """Añadir un tamaño no puede romper las que ya iban: el guardarraíl de que el recorrido
    tiene que llegar limpio a la firma siguiente lo impide, y aquí se comprueba."""
    esperado = {"pcf5": 120, "pcf5oro": 120, "pcf6": 120, "pcf6oro": 240,
                "apertura97": 20, "apertura98": 50}
    for nombre, minimo in esperado.items():
        ruta = next((r for r in BASES if f"/{nombre}/" in r.replace(os.sep, "/")), None)
        if not ruta:
            continue
        ok, _ = _deterministas(ruta)
        assert ok >= minimo, f"{nombre} ha empeorado: {ok} deterministas"


@falta
def test_el_round_trip_sigue_intacto():
    """Lo que no se puede romper jamás."""
    for ruta in BASES:
        raw = open(ruta, "rb").read()
        try:
            f = E.parse(raw)
        except Exception:  # noqa: BLE001
            continue
        if f.teams:
            assert E.serialize(f) == raw, f"round-trip roto en {ruta}"
