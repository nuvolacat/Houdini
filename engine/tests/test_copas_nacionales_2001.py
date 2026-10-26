"""Las copas nacionales de PCF2001, identificadas por su NOMBRE dentro del ejecutable.

Hasta ahora las tablas del `manager.exe` se emparejaban por deducción: «esta lista de 18
equipos alemanes tiene que ser la Bundesliga». Así se coló el fallo de la Copa de Alemania,
que editaba la liga. El 22-sep-2026 se vio que **no hace falta deducir nada**: detrás de cada
tabla de equipos, el propio ejecutable escribe el identificador de su competición en texto
plano, junto a la plantilla de calendario `actliga\\XXXXX%03u.CPT`:

    …tabla de 44 + tabla de 68 equipos españoles…  «CREY»     → Copa del Rey
    …tabla de 124 equipos ingleses y galeses…      «FACUP»    → F.A. Cup
    …tabla de 92 equipos ingleses…                 «CCCUP»    → Copa de la Liga (Coca-Cola)
    …tabla de 48 equipos italianos…                «CITALIA»  → Copa de Italia
    …tabla de 18 alemanes… «BUNDES1»  ·  …tabla de 20… «BUNDES3A»  ·  …y «CBUNDES» tras la copa

Con esa regla se comprueba de paso que lo ya mapeado estaba bien, y aparecen dos divisiones
que faltaban: las Regionalligas alemanas.
"""
import os
import struct
import sys

import pytest

RAIZ = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, os.path.join(RAIZ, "engine"))

MANAGER = os.path.join(RAIZ, "gamedata", "PCF2001", "manager.exe")
EQUIPOS = os.path.join(RAIZ, "gamedata", "PCF2001", "DBDAT", "eq00022.fdi")
BUILD_2001 = 7991296

ESPAÑA, INGLATERRA, GALES, ITALIA, ALEMANIA = 22, 30, 45, 36, 2


@pytest.fixture(scope="module")
def mundo():
    if not (os.path.exists(MANAGER) and os.path.exists(EQUIPOS)):
        pytest.skip("sin el manager.exe / eq00022.fdi de PCF2001")
    from houdini_engine.formats import pcf2000 as FDI
    with open(MANAGER, "rb") as f:
        raw = f.read()
    with open(EQUIPOS, "rb") as f:
        eq = FDI.parse(f.read(), "eq00022.fdi", variant="2001")
    return raw, {t.code: (t.nombre_corto, t.pais) for t in eq.records}


def _copa(clave):
    from houdini_engine.formats import pcf2000_manager as PM
    return next(c for c in PM.FDI_EUROCUPS[BUILD_2001] if c["key"] == clave)


def _equipos(raw, nom, copa, campo="slots"):
    from houdini_engine.formats import pcf2000_manager as PM
    return [nom.get(struct.unpack_from("<H", raw, o - PM._VB6)[0], ("??", -1))
            for o in copa[campo]]


# ───────────────────── el nombre está en el binario, no se deduce ─────────────────────

@pytest.mark.parametrize("clave,etiqueta", [
    ("copa_rey_2", "CREY"), ("fa_cup", "FACUP"),
    ("copa_liga_ing", "CCCUP"), ("copa_ita", "CITALIA"),
])
def test_cada_copa_lleva_su_nombre_detras(mundo, clave, etiqueta):
    """La prueba que ata el offset: tras la última plaza de la tabla, y antes de que empiece
    otra tabla de equipos, el ejecutable escribe el identificador de la competición."""
    from houdini_engine.formats import pcf2000_manager as PM
    raw, _nom = mundo
    fin = max(_copa(clave)["slots"]) - PM._VB6 + 2
    ventana = raw[fin:fin + 800]
    assert etiqueta.encode() + b"\x00" in ventana, (
        f"«{etiqueta}» no aparece tras la tabla de {clave}: el offset no es el que creemos")


def test_la_misma_regla_confirma_lo_que_ya_teniamos(mundo):
    """Si la regla vale para las copas nuevas, tiene que valer para las tablas viejas. Aquí es
    donde habría saltado el fallo de la Copa de Alemania: tras las tablas que llamábamos copa
    va «CBUNDES», y tras las de liga «BUNDES1»/«BUNDES2»."""
    from houdini_engine.formats import pcf2000_manager as PM
    raw, _nom = mundo
    ligas = {e: (off, n) for _p, e, off, n in PM.DIVISIONS["2001"]}
    for etiqueta, nombre in (("1. Bundesliga", b"BUNDES1\x00"), ("2. Bundesliga", b"BUNDES2\x00"),
                             ("Regionalliga Nord", b"BUNDES3A\x00"),
                             ("Regionalliga Süd", b"BUNDES3B\x00")):
        off, n = ligas[etiqueta]
        assert nombre in raw[off + n * 2:off + n * 2 + 80], etiqueta
    fin = max(_copa("copa_de_2")["slots"]) - PM._VB6 + 2
    assert b"CBUNDES\x00" in raw[fin:fin + 80], "la Copa de Alemania ya no cae donde decía"


# ───────────────────── y lo que hay dentro es lo que tiene que haber ─────────────────────

def test_la_copa_del_rey_son_112_plazas_espanolas(mundo):
    """La composición real, que hasta hoy era un «no lo sabemos» apuntado en el revisor."""
    raw, nom = mundo
    a = _equipos(raw, nom, _copa("copa_rey_1"))
    b = _equipos(raw, nom, _copa("copa_rey_2"))
    assert len(a) == 44 and len(b) == 68
    assert all(p == ESPAÑA for _n, p in a + b)
    assert "Real Madrid C.F." in {n for n, _p in a} and "F.C. Barcelona" in {n for n, _p in a}


def test_las_dos_primeras_plazas_son_los_finalistas_del_ano_anterior(mundo):
    """Lo que explica los dos «repetidos» del bloque: las plazas 1 y 2 no son de división,
    son los dos finalistas de la Copa anterior — y de fábrica son el Espanyol y el Atlético,
    que es justo quiénes jugaron la final de 2000. Las 42 restantes son exactamente los
    mismos clubes que Primera (20) y Segunda (22)."""
    from houdini_engine.formats import pcf2000_manager as PM
    raw, nom = mundo
    copa = _copa("copa_rey_1")
    cods = [struct.unpack_from("<H", raw, o - PM._VB6)[0] for o in copa["slots"]]
    assert [nom[c][0] for c in cods[:2]] == ["R.C.D. Espanyol", "C. At. Madrid"]
    assert copa["slot_labels"][0].startswith("Finalista")

    L = {(p, e): (off, n) for p, e, off, n in PM.DIVISIONS["2001"]}
    liga = []
    for clave in ((ESPAÑA, "Primera División"), (ESPAÑA, "Segunda División")):
        off, n = L[clave]
        liga += [struct.unpack_from("<H", raw, off + 2 * i)[0] for i in range(n)]
    assert len(liga) == 42
    assert set(cods[2:]) == set(liga), "las 42 plazas ya no son las de 1ª y 2ª"
    assert cods[2:] != liga, "van en otro orden: no es una copia de la tabla de liga"


def test_la_fa_cup_lleva_a_los_tres_galeses(mundo):
    """124 plazas: 121 clubes ingleses y los 3 de Gales que juegan la copa inglesa."""
    raw, nom = mundo
    eq = _equipos(raw, nom, _copa("fa_cup"))
    assert len(eq) == 124
    galeses = {n for n, p in eq if p == GALES}
    assert galeses == {"Cardiff", "Swansea", "Wrexham"}, galeses
    assert sum(1 for _n, p in eq if p == INGLATERRA) == 121


def test_la_copa_de_la_liga_inglesa_son_los_92_de_la_liga(mundo):
    """El campo exacto de la Worthington: los 92 clubes de la Football League y la Premier.
    Las plazas NO son correlativas — van en tres bloques (61 + 7 + 24) con unos bytes por
    medio, que es la entrada escalonada por rondas."""
    from houdini_engine.formats import pcf2000_manager as PM
    raw, nom = mundo
    copa = _copa("copa_liga_ing")
    eq = _equipos(raw, nom, copa)
    assert len(eq) == 92
    assert all(p in (INGLATERRA, GALES) for _n, p in eq)
    assert len({n for n, _p in eq}) == 92, "hay clubes repetidos"
    saltos = [i for i in range(len(copa["slots"]) - 1)
              if copa["slots"][i + 1] - copa["slots"][i] != 2]
    assert len(saltos) == 2, "los tres bloques de rondas ya no están donde creíamos"
    # los 7 del bloque de en medio son los que jugaban en Europa ese año
    medio = {n for n, _p in eq[saltos[0] + 1:saltos[1] + 1]}
    assert {"Liverpool", "Manchester Utd.", "Arsenal", "Leeds Utd."} <= medio, medio


def test_la_copa_de_italia_se_escribe_en_las_dos_copias(mundo):
    """En el ejecutable hay DOS tablas idénticas de la Copa de Italia. Como no se puede
    demostrar cuál lee el juego, la ficha escribe las dos: dejar una sin tocar es exactamente
    el fallo que tuvimos con la Copa de Alemania."""
    from houdini_engine.formats import pcf2000_manager as PM
    raw, nom = mundo
    copa = _copa("copa_ita")
    a = _equipos(raw, nom, copa)
    b = _equipos(raw, nom, copa, "mirror")
    assert len(a) == 48 and a == b, "las dos copias ya no son iguales de fábrica"
    assert all(p == ITALIA for _n, p in a)
    assert {"Milan", "Juventus", "Lazio"} <= {n for n, _p in a}

    nuevo = list(range(1, 49))
    out = PM.eurocups_write(raw, {"copa_ita": nuevo})
    for campo in ("slots", "mirror"):
        leidos = [struct.unpack_from("<H", out, o - PM._VB6)[0] for o in copa[campo]]
        assert leidos == nuevo, f"la copia «{campo}» se ha quedado sin escribir"
    assert len(out) == len(raw)


def test_las_regionalligas_son_alemanas_y_no_repiten_bundesliga(mundo):
    raw, nom = mundo
    from houdini_engine.formats import pcf2000_manager as PM
    ligas = {e: (off, n) for _p, e, off, n in PM.DIVISIONS["2001"]}
    por_liga = {}
    for e in ("1. Bundesliga", "2. Bundesliga", "Regionalliga Nord", "Regionalliga Süd"):
        off, n = ligas[e]
        cods = [struct.unpack_from("<H", raw, off + 2 * i)[0] for i in range(n)]
        assert all(nom.get(c, ("", -1))[1] == ALEMANIA for c in cods), e
        por_liga[e] = set(cods)
    assert len(por_liga) == 4
    todos = [c for s in por_liga.values() for c in s]
    assert len(todos) == len(set(todos)), "un club alemán está en dos divisiones a la vez"


# ───────────────────── guardarraíles generales ─────────────────────

def test_ninguna_tabla_pisa_a_otra(mundo):
    """El guardarraíl que nació del fallo alemán, ahora también sobre las plazas espejo."""
    from houdini_engine.formats import pcf2000_manager as PM
    _raw, _nom = mundo
    duenyo = {}
    for _p, e, off, n in PM.DIVISIONS["2001"]:
        for i in range(n):
            assert off + 2 * i not in duenyo, f"«{e}» pisa «{duenyo[off + 2 * i]}»"
            duenyo[off + 2 * i] = e
    for c in PM.FDI_EUROCUPS[BUILD_2001]:
        for campo in ("slots", "mirror"):
            for o in (c.get(campo) or []):
                sitio = o - PM._VB6
                assert sitio not in duenyo, f"«{c['key']}» pisa «{duenyo[sitio]}»"
                duenyo[sitio] = c["key"]


def test_las_copas_nuevas_se_leen_por_la_api_del_motor(mundo):
    from houdini_engine.formats import pcf2000_manager as PM
    raw, nom = mundo
    leido = {c["key"]: c for c in PM.eurocups_read(raw)}
    for clave, n in (("copa_rey_1", 44), ("copa_rey_2", 68), ("fa_cup", 124),
                     ("copa_liga_ing", 92), ("copa_ita", 48)):
        assert len(leido[clave]["pointers"]) == n
        assert all(p in nom for p in leido[clave]["pointers"]), clave
        assert leido[clave]["label"]


def test_escribir_una_copa_no_toca_las_demas(mundo):
    from houdini_engine.formats import pcf2000_manager as PM
    raw, _nom = mundo
    antes = PM.eurocups_read(raw)
    out = PM.eurocups_write(raw, {"fa_cup": [7] * 124})
    despues = {c["key"]: c["pointers"] for c in PM.eurocups_read(out)}
    for c in antes:
        if c["key"] != "fa_cup":
            assert despues[c["key"]] == c["pointers"], c["key"]
    assert despues["fa_cup"] == [7] * 124
