"""PCF7: las copas inglesas, y las dos plazas que le faltaban a la Copa del Rey.

Misma regla que en 2000 y 2001 — el `MANAGER.EXE` escribe el nombre de cada competición justo
detrás de su tabla de equipos. Aplicada a PCF7:

* sus divisiones estaban TODAS bien («PREMIERLEAGUE», «SERIEA», «LIGA1», «BUNDES1»…), que es
  justo lo que se quería comprobar antes de tocar nada;
* aparece la **F.A. Cup** («FACUP», 124 plazas), que no estaba;
* y la Copa del Rey empezaba dos plazas tarde: delante de los clubes de 1ª y 2ª van los
  **finalistas de la Copa anterior** (Barcelona y Mallorca, la final del 97-98), y además la
  tabla tenía 41 plazas cuando son 42.

Dos tablas quedan localizadas pero SIN mapear a propósito —la Copa de la Liga inglesa («CCCUP»,
100 plazas para 90 clubes) y la Copa de Italia («CITALIA», con repetidos en su tercer bloque)—
porque no se entienden del todo. Mapear a medias es como se rompió la Copa de Alemania, y hay
un test por cada una que avisará si algún día dejan de tener repetidos.
"""
import os
import struct
import sys

import pytest

RAIZ = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, os.path.join(RAIZ, "engine"))

MANAGER = os.path.join(RAIZ, "gamedata", "FUTBOL7", "MANAGER.EXE")
EQUIPOS = os.path.join(RAIZ, "gamedata", "FUTBOL7", "DBDAT", "EQ99022.FDI")

ESPAÑA, INGLATERRA, GALES, ITALIA, FRANCIA, ALEMANIA = 22, 30, 45, 36, 24, 2


@pytest.fixture(scope="module")
def mundo():
    if not (os.path.exists(MANAGER) and os.path.exists(EQUIPOS)):
        pytest.skip("sin el MANAGER.EXE / EQ99022.FDI de PCF7")
    from houdini_engine.formats import pcf7 as FDI
    with open(MANAGER, "rb") as f:
        raw = f.read()
    with open(EQUIPOS, "rb") as f:
        eq = FDI.parse(f.read(), "EQ99022.FDI")
    return raw, {t.code: (t.nombre_corto, t.pais) for t in eq.records}


def _tabla(clave):
    from houdini_engine.formats import pcf7_manager as PM
    return next(t for t in PM.FDI_TABLES[4939776] if t["key"] == clave)


def _codes(raw, off, n):
    return [struct.unpack_from("<H", raw, off + 2 * i)[0] for i in range(n)]


# ───────────────────── la regla confirma lo que ya teníamos ─────────────────────

@pytest.mark.parametrize("pais,etiqueta,nombre", [
    (INGLATERRA, "Premier League", b"PREMIERLEAGUE\x00"),
    (INGLATERRA, "First Division", b"FIRSTDIVISION\x00"),
    (ITALIA, "Serie A", b"SERIEA\x00"),
    (ESPAÑA, "Primera División", b"LIGA1\x00"),
    (ESPAÑA, "Segunda División", b"LIGA2\x00"),
    (FRANCIA, "Ligue 1", b"FRANCE1\x00"),
    (ALEMANIA, "Bundesliga 1", b"BUNDES1\x00"),
])
def test_las_divisiones_de_pcf7_ya_estaban_bien(mundo, pais, etiqueta, nombre):
    """Lo primero que se hizo al traer la regla: comprobarla contra lo viejo. En PCF2000 así
    salió que la Primera apuntaba a la Copa del Rey; aquí todo estaba en su sitio."""
    from houdini_engine.formats import pcf7_manager as PM
    raw, _nom = mundo
    off, n = next((o, c) for p, e, o, c in PM.DIVISIONS if (p, e) == (pais, etiqueta))
    assert nombre in raw[off + n * 2:off + n * 2 + 900], f"{etiqueta}: el offset no es el suyo"


# ───────────────────── las copas inglesas que faltaban ─────────────────────

def test_la_fa_cup(mundo):
    """124 plazas contiguas, todas de clubes ingleses o galeses y sin repetir, y entre ellas
    están los 92 de la Liga. Es la única copa inglesa de PCF7 que se entiende entera."""
    raw, nom = mundo
    t = _tabla("fa_cup")
    assert (t["off"], t["n"]) == (0x49D560, 124)
    assert b"FACUP\x00" in raw[t["off"] + 124 * 2:t["off"] + 124 * 2 + 900]
    cods = _codes(raw, t["off"], 124)
    eq = [nom.get(c, ("??", -1)) for c in cods]
    assert all(p in (INGLATERRA, GALES) for _x, p in eq), "hay equipos de otro país"
    assert len(set(cods)) == 124, "plazas repetidas"
    galeses = {x for x, p in eq if p == GALES}
    assert any(x.startswith("Cardiff") for x in galeses) and "Wrexham" in galeses, galeses


def test_la_copa_de_la_liga_inglesa_sigue_sin_mapear(mundo):
    """Localizada («CCCUP» en 0x49D2D4) pero no editable: son 100 plazas para 90 clubes
    —Southampton y West Ham entre los que salen dos veces— y le faltan dos de los 92 de la
    Liga. En PCF2001 la misma copa son 92 sin repetir. Hasta entender la diferencia no se
    toca; este test recuerda por qué."""
    from houdini_engine.formats import pcf7_manager as PM
    raw, _nom = mundo
    assert not [t for t in PM.FDI_TABLES[4939776] if t["key"] == "copa_liga_ing"]
    assert b"CCCUP\x00" in raw[0x49D2D4 + 200:0x49D2D4 + 1100]
    cods = _codes(raw, 0x49D2D4, 100)
    assert len(set(cods)) == 90, "ya no hay repetidos: quizá ahora sí se puede mapear"


# ───────────────────── la Copa del Rey, entera ─────────────────────

def test_los_finalistas_del_ano_anterior(mundo):
    """Las dos plazas que iban delante y no se leían. De fábrica, quienes jugaron la final
    del 97-98 — el mismo patrón que en PCF2000 y PCF2001."""
    raw, nom = mundo
    t = _tabla("copa_rey_final")
    assert (t["off"], t["n"]) == (0x49EDFC, 2)
    assert [nom[c][0] for c in _codes(raw, t["off"], 2)] == ["F.C. Barcelona", "R.C.D. Mallorca"]


def test_la_segunda_ronda_son_42_y_no_41(mundo):
    """Le faltaba la última plaza, y las 42 son exactamente los clubes de 1ª y 2ª."""
    from houdini_engine.formats import pcf7_manager as PM
    raw, nom = mundo
    t = _tabla("copa_rey_2")
    assert (t["off"], t["n"]) == (0x49EE00, 42)
    liga = []
    for clave in ((ESPAÑA, "Primera División"), (ESPAÑA, "Segunda División")):
        off, n = next((o, c) for p, e, o, c in PM.DIVISIONS if (p, e) == clave)
        liga += _codes(raw, off, n)
    assert len(liga) == 42
    copa = _codes(raw, t["off"], t["n"])
    # una plaza lleva un club que no está en el EQ (el filial del Atlético): se compara el resto
    assert len(set(copa) & set(liga)) >= 41, "la 2ª ronda ya no son los clubes de 1ª y 2ª"


def test_no_se_ha_movido_lo_que_ya_estaba_guardado(mundo):
    """`copa_rey_2` se deja donde estaba y solo se ALARGA. Correrlo dos plazas atrás habría
    desplazado la copa entera en los mods que ya la tienen guardada."""
    t = _tabla("copa_rey_2")
    assert t["off"] == 0x49EE00, "se ha movido: los mods viejos escribirían corridos"


def test_la_copa_de_italia_sigue_sin_mapear(mundo):
    """A propósito: su tercer bloque trae clubes repetidos y no se entiende. Si algún día se
    mapea, que sea a sabiendas — este test lo recuerda."""
    from houdini_engine.formats import pcf7_manager as PM
    raw, nom = mundo
    assert not [t for t in PM.FDI_TABLES[4939776] if "ita" in t["key"] and "supercopa" not in t["key"]]
    assert b"CITALIA\x00" in raw[0x49E170:0x49E400], "la tabla ya ni siquiera está donde decíamos"
    tercero = [nom.get(c, ("?", 0))[0] for c in _codes(raw, 0x49E1B4, 48)]
    assert len(set(tercero)) < 48, "ya no hay repetidos: quizá ahora sí se puede mapear"


# ───────────────────── guardarraíl ─────────────────────

def test_ninguna_copa_pisa_una_division(mundo):
    from houdini_engine.formats import pcf7_manager as PM
    _raw, _nom = mundo
    duenyo = {}
    for _p, e, off, n in PM.DIVISIONS:
        for i in range(n):
            duenyo[off + 2 * i] = e
    for t in PM.FDI_TABLES[4939776]:
        for o in PM.table_offsets(t):
            assert o not in duenyo, f"«{t['key']}» escribe dentro de «{duenyo[o]}»"


def test_las_copas_nuevas_se_leen_y_se_escriben(mundo):
    from houdini_engine.formats import pcf7_manager as PM
    raw, _nom = mundo
    leido = {t["key"]: t for t in PM.tables_read(raw)}
    assert len(leido["fa_cup"]["pointers"]) == 124
    out = PM.tables_write(raw, {"fa_cup": [9] * 124})
    assert len(out) == len(raw)
    despues = {t["key"]: t["pointers"] for t in PM.tables_read(out)}
    assert despues["fa_cup"] == [9] * 124
    for k, v in leido.items():
        if k != "fa_cup":
            assert despues[k] == v["pointers"], k


def test_los_participantes_europeos_van_en_instrucciones(mundo):
    """La lista VIVA de los europeos no es una tabla contigua: son 34 `mov word [..], <código>`
    (patrón `66 C7 44 … FE`) repartidos en 0x1C48DB-0x1C4E96. Se edita por `slots`. Las tablas
    `euro_pool`/`champions` (0x453690/0x453780) NO valen: son fijas, idénticas en 7/2000/2001 y
    editarlas no cambia nada (el mod comunitario 25-26 reescribe estas 34 y ninguna de aquellas)."""
    from houdini_engine.formats import pcf7_manager as PM
    raw, _nom = mundo
    t = _tabla("euro7")
    assert "slots" in t and len(t["slots"]) == 34
    # cada plaza es el inmediato de una instrucción `66 C7 44 xx FE <code>`
    for o in t["slots"]:
        assert (raw[o - 5], raw[o - 4], raw[o - 1]) == (0x66, 0xC7, 0xFE), hex(o)
    leido = {x["key"]: x for x in PM.tables_read(raw)}
    assert leido["euro7"]["pointers"] == [
        1459, 401, 312, 1003, 215, 1201, 25, 506, 902, 205, 606, 1302, 7, 421, 804, 751, 1153,
        1108, 201, 601, 802, 1, 1452, 520, 406, 1303, 303, 1351, 204, 415, 4, 508, 812, 309]
    # escribir cambia SOLO los 2 bytes de cada plaza y no mueve el tamaño
    out = PM.tables_write(raw, {"euro7": [30] * 34})
    assert len(out) == len(raw)
    fuera = {i for i in range(len(raw)) if raw[i] != out[i]}
    assert fuera <= {o + k for o in t["slots"] for k in (0, 1)}, "toca bytes fuera de las plazas"
    # y restaurar deja el fichero de fábrica
    vuelta = PM.tables_write(out, {k: v["pointers"] for k, v in leido.items()})
    assert vuelta == raw
    # el señuelo ya no se ofrece como editable
    assert not [x for x in PM.FDI_TABLES[4939776] if x["key"] in ("euro_pool", "champions")]
