"""PCF2000: la Primera División apuntaba a la Copa del Rey, y faltaban las ligas extranjeras.

Aplicando a PCF2000 la regla que destapó las copas de 2001 —el ejecutable escribe el nombre de
cada competición justo detrás de su tabla de equipos— sale que la tabla que llamábamos «Primera
División» (0x4AC3C8) está dentro del bloque de **«CREY»**, la Copa del Rey. La LIGA1 de verdad
está en 0x4AC6A4.

Por qué no se había visto: son **los mismos 20 clubes**, así que leer la división funcionaba.
Pero van en otro orden —el de la copa, no el de la clasificación— y, sobre todo, **escribir**
recolocaba la Copa del Rey en lugar de la Liga. Es el mismo fallo que tuvimos con la Copa de
Alemania, y aquí duele más: España sí es jugable en PCF2000.

De paso entran las ligas de Inglaterra, Italia, Francia y Alemania, que no estaban mapeadas en
2000 y dejaban a 240 equipos en «Otros».
"""
import os
import struct
import sys

import pytest

RAIZ = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, os.path.join(RAIZ, "engine"))

MANAGER = os.path.join(RAIZ, "gamedata", "PCF2000", "manager.exe")
EQUIPOS = os.path.join(RAIZ, "gamedata", "PCF2000", "DBDAT", "eq00022.fdi")

ESPAÑA, INGLATERRA, GALES, ITALIA, FRANCIA, ALEMANIA = 22, 30, 45, 36, 24, 2


@pytest.fixture(scope="module")
def mundo():
    if not (os.path.exists(MANAGER) and os.path.exists(EQUIPOS)):
        pytest.skip("sin el manager.exe / eq00022.fdi de PCF2000")
    from houdini_engine.formats import pcf2000 as FDI
    with open(MANAGER, "rb") as f:
        raw = f.read()
    with open(EQUIPOS, "rb") as f:
        eq = FDI.parse(f.read(), "eq00022.fdi", variant="2000")
    return raw, {t.code: (t.nombre_corto, t.pais) for t in eq.records}


def _tabla(raw, off, n):
    return [struct.unpack_from("<H", raw, off + 2 * i)[0] for i in range(n)]


def _liga(clave):
    from houdini_engine.formats import pcf2000_manager as PM
    return next((off, n) for p, e, off, n in PM.DIVISIONS["2000"] if (p, e) == clave)


# ───────────────────────── el fallo que se arregla ─────────────────────────

def test_la_primera_ya_no_apunta_a_la_copa_del_rey(mundo):
    from houdini_engine.formats import pcf2000_manager as PM
    raw, _nom = mundo
    off, n = _liga((ESPAÑA, "Primera División"))
    assert (off, n) == (0x4AC6A4, 20)
    assert b"LIGA1\x00" in raw[off + n * 2:off + n * 2 + 900], "detrás no pone LIGA1"
    assert not (0x4AC3C4 <= off < 0x4AC500), "vuelve a caer en el bloque de la Copa del Rey"


def test_la_tabla_vieja_es_la_copa_del_rey_y_empieza_por_los_finalistas(mundo):
    """La prueba de que no es una manía: en 0x4AC3C4 van dos equipos ANTES de los 20 de
    Primera, y son los finalistas de la Copa anterior (Barcelona y Mallorca jugaron la final
    del 97-98). Detrás de todo el bloque, el ejecutable pone «CREY»."""
    raw, nom = mundo
    cab = _tabla(raw, 0x4AC3C4, 2)
    assert [nom[c][0] for c in cab] == ["F.C. Barcelona", "R.C.D. Mallorca"]
    assert b"CREY\x00" in raw[0x4AC4F2:0x4AC4F2 + 900]


def test_los_mismos_clubes_pero_en_otro_orden(mundo):
    """Por esto pasaba desapercibido: el conjunto coincide, la secuencia no."""
    raw, _nom = mundo
    off, n = _liga((ESPAÑA, "Primera División"))
    liga = _tabla(raw, off, n)
    copa = _tabla(raw, 0x4AC3C8, 20)
    assert set(liga) == set(copa)
    assert liga != copa, "si fueran idénticas, daría igual cuál se escribe"


def test_escribir_la_liga_no_toca_la_copa(mundo):
    """Lo que de verdad estaba roto: recolocar la Liga escribía en la Copa del Rey."""
    from houdini_engine.formats import pcf2000_manager as PM
    raw, _nom = mundo
    duenyo = {}
    for _p, e, off, n in PM.DIVISIONS["2000"]:
        for i in range(n):
            assert off + 2 * i not in duenyo, f"«{e}» pisa «{duenyo[off + 2 * i]}»"
            duenyo[off + 2 * i] = e
    copa = set(range(0x4AC3C4, 0x4AC4F2, 2))
    assert not (copa & set(duenyo)), "una división sigue escribiendo dentro de la Copa del Rey"


# ───────────────────────── las ligas que faltaban ─────────────────────────

@pytest.mark.parametrize("pais,etiqueta,nombre,n", [
    (INGLATERRA, "Premier League", b"PREMIERLEAGUE\x00", 20),
    (INGLATERRA, "Division One", b"FIRSTDIVISION\x00", 24),
    (INGLATERRA, "Division Two", b"SECONDDIVISION\x00", 24),
    (INGLATERRA, "Division Three", b"THIRDDIVISION\x00", 24),
    (ITALIA, "Serie A", b"SERIEA\x00", 18),
    (ITALIA, "Serie B", b"SERIEB\x00", 20),
    (FRANCIA, "Division 1", b"FRANCE1\x00", 18),
    (FRANCIA, "Division 2", b"FRANCE2\x00", 20),
    (ALEMANIA, "1. Bundesliga", b"BUNDES1\x00", 18),
    (ALEMANIA, "2. Bundesliga", b"BUNDES2\x00", 18),
])
def test_cada_liga_extranjera_lleva_su_nombre_detras(mundo, pais, etiqueta, nombre, n):
    raw, nom = mundo
    off, cuantas = _liga((pais, etiqueta))
    assert cuantas == n
    assert nombre in raw[off + n * 2:off + n * 2 + 900], f"{etiqueta}: el offset no es el suyo"
    equipos = [nom.get(c, ("??", -1)) for c in _tabla(raw, off, n)]
    de_otro = [e for e in equipos if e[1] not in (pais, GALES)]
    assert not de_otro, f"{etiqueta} trae equipos de otro país: {de_otro[:3]}"
    assert len({c for c in _tabla(raw, off, n)}) == n, f"{etiqueta}: plazas repetidas"


def test_los_dos_grupos_de_la_serie_c1_son_distintos(mundo):
    """Van pegados (18 + 18) y es fácil coger dos veces el mismo."""
    raw, _nom = mundo
    a = _tabla(raw, *_liga((ITALIA, "Serie C1 - Grupo A")))
    b = _tabla(raw, *_liga((ITALIA, "Serie C1 - Grupo B")))
    assert len(a) == len(b) == 18
    assert not (set(a) & set(b)), "un club italiano está en los dos grupos"


def test_ahora_2000_coloca_muchos_mas_equipos(mundo):
    """El efecto visible: antes solo se ubicaban los españoles y el resto caía en «Otros»."""
    from houdini_engine.formats import pcf2000_manager as PM
    raw, _nom = mundo
    mapa = PM.division_map(raw, "2000")
    assert len(mapa) > 340, f"solo {len(mapa)} equipos ubicados"
    paises = {p for p, _e in mapa.values()}
    assert {ESPAÑA, INGLATERRA, ITALIA, FRANCIA, ALEMANIA} <= paises
