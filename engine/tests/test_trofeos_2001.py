"""Los doce trofeos de pretemporada de PCF2001.

PCF7 tenía siete mapeados (Bernabéu, Gamper, Carranza, Colombino, Ciutat de Palma, Naranja y
Teresa Herrera) y PCF2001 ninguno, aunque los trae todos y cinco más: Ciutat de Barcelona,
Ciudad de Vigo, La Línea, Villa de Gijón y Villa de Madrid. Esos cinco nombres **no existen** en
el MANAGER.EXE de PCF7, así que son propios de 2001.

Localizarlos tuvo una vuelta de tuerca sobre la regla del nombre: aquí la tabla no va pegada a
su identificador, sino unos 200-270 bytes antes, con las rutas de sus imágenes por medio. La
distancia se **midió en PCF7**, donde estas tablas ya estaban mapeadas de antes, y se buscó la
misma forma en 2001. Que el número de plazas coincida en los siete trofeos comunes es lo que
cierra el argumento.

No llevan `sigue_liga`: sus participantes son invitaciones (el Santos en el Bernabéu, el PSV en
el Gamper), no la composición de una división. El anfitrión no figura en la tabla.
"""
import os
import struct
import sys

import pytest

RAIZ = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, os.path.join(RAIZ, "engine"))

MANAGER = os.path.join(RAIZ, "gamedata", "PCF2001", "manager.exe")
EQUIPOS = os.path.join(RAIZ, "gamedata", "PCF2001", "DBDAT", "eq00022.fdi")
MANAGER7 = os.path.join(RAIZ, "gamedata", "FUTBOL7", "MANAGER.EXE")
BUILD_2001 = 7991296

# (clave, nombre en el ejecutable, nº de plazas)
TROFEOS = [
    ("trofeo_bernabeu", b"BERNABEU\x00", 1),
    ("trofeo_barcelona", b"BARCELON\x00", 1),
    ("trofeo_vigo", b"VIGO____\x00", 1),
    ("trofeo_gamper", b"GAMPER\x00", 1),
    ("trofeo_linea", b"LINEA___\x00", 2),
    ("trofeo_carranza", b"TCARRANZA\x00", 3),
    ("trofeo_colombino", b"TCOLOMBINO\x00", 3),
    ("trofeo_palma", b"TCPALMA\x00", 3),
    ("trofeo_naranja", b"TNARANJA\x00", 2),
    ("trofeo_herrera", b"TTHERRERA\x00", 3),
    ("trofeo_gijon", b"GIJON___\x00", 1),
    ("trofeo_villamadrid", b"VMADRID_\x00", 1),
]


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


def _trofeo(clave):
    from houdini_engine.formats import pcf2000_manager as PM
    return next(c for c in PM.FDI_EUROCUPS[BUILD_2001] if c["key"] == clave)


@pytest.mark.parametrize("clave,nombre,n", TROFEOS)
def test_cada_trofeo_tiene_su_tabla_y_su_nombre_detras(mundo, clave, nombre, n):
    from houdini_engine.formats import pcf2000_manager as PM
    raw, nom = mundo
    t = _trofeo(clave)
    assert len(t["slots"]) == n
    fin = max(t["slots"]) - PM._VB6 + 2
    assert nombre in raw[fin:fin + 400], f"{clave}: detrás no está su nombre"
    equipos = [nom.get(struct.unpack_from("<H", raw, o - PM._VB6)[0]) for o in t["slots"]]
    assert all(equipos), f"{clave}: alguna plaza no trae un equipo real"


@pytest.mark.parametrize("clave,_n,_c", [(k, n, c) for k, c, n in TROFEOS])
def test_la_tabla_esta_aislada(mundo, clave, _n, _c):
    """Delante y detrás de cada tabla hay ceros: es lo que fija dónde empieza y acaba."""
    from houdini_engine.formats import pcf2000_manager as PM
    raw, _nom = mundo
    ini = min(_trofeo(clave)["slots"]) - PM._VB6
    assert struct.unpack_from("<H", raw, ini - 2)[0] == 0, f"{clave}: la plaza 0 no es la primera"


def test_los_invitados_de_fabrica_son_creibles(mundo):
    """Unos cuantos, por su nombre: si los offsets estuvieran corridos saldría cualquier cosa."""
    from houdini_engine.formats import pcf2000_manager as PM
    raw, nom = mundo
    esperado = {
        "trofeo_bernabeu": ["Santos"],
        "trofeo_gamper": ["PSV"],
        "trofeo_carranza": ["R. Betis B.", "Villarreal C. F.", "R.C.D. Mallorca"],
        "trofeo_herrera": ["Lazio", "Athletic Club", "Borussia D."],
    }
    for clave, nombres in esperado.items():
        leidos = [nom[struct.unpack_from("<H", raw, o - PM._VB6)[0]][0]
                  for o in _trofeo(clave)["slots"]]
        assert leidos == nombres, clave


def test_los_siete_comunes_tienen_las_mismas_plazas_que_en_pcf7(mundo):
    """El argumento que cierra la localización: el número de participantes coincide con el de
    PCF7, donde estas tablas se mapearon por otro camino."""
    from houdini_engine.formats import pcf7_manager as P7
    comunes = {"trofeo_bernabeu", "trofeo_gamper", "trofeo_carranza", "trofeo_colombino",
               "trofeo_palma", "trofeo_naranja", "trofeo_herrera"}
    en7 = {t["key"]: t["n"] for t in P7.FDI_TABLES[4939776] if t["key"] in comunes}
    assert set(en7) == comunes, f"faltan en PCF7: {comunes - set(en7)}"
    for clave, n in en7.items():
        assert len(_trofeo(clave)["slots"]) == n, clave


def test_los_cinco_nuevos_no_estan_en_pcf7():
    """Y por eso no se buscaron allí: son competiciones que 2001 añadió."""
    if not os.path.exists(MANAGER7):
        pytest.skip("sin el MANAGER.EXE de PCF7")
    with open(MANAGER7, "rb") as f:
        raw7 = f.read()
    for nombre in (b"BARCELON\x00", b"VIGO____\x00", b"LINEA___\x00",
                   b"GIJON___\x00", b"VMADRID_\x00"):
        assert nombre not in raw7, f"{nombre!r} sí está en PCF7: revisar"


def test_los_trofeos_no_siguen_a_la_liga(mundo):
    """Sus participantes son invitaciones. Si se marcaran como copa de división, recolocar
    España les cambiaría los invitados."""
    from houdini_engine.formats import pcf2000_manager as PM, pcf7_manager as P7
    slots = set(P7.CUP_SLOTS.get(BUILD_2001, ()))
    for c in PM.FDI_EUROCUPS[BUILD_2001]:
        if c["key"].startswith("trofeo"):
            assert not c.get("sigue_liga"), c["key"]
            assert not (slots & {o - PM._VB6 for o in c["slots"]}), c["key"]


def test_se_editan_sin_tocar_a_los_demas(mundo):
    from houdini_engine.formats import pcf2000_manager as PM
    raw, _nom = mundo
    antes = {c["key"]: c["pointers"] for c in PM.eurocups_read(raw)}
    out = PM.eurocups_write(raw, {"trofeo_bernabeu": [4]})
    assert len(out) == len(raw)
    despues = {c["key"]: c["pointers"] for c in PM.eurocups_read(out)}
    assert despues["trofeo_bernabeu"] == [4]
    for k, v in antes.items():
        if k != "trofeo_bernabeu":
            assert despues[k] == v, k


def test_ninguna_tabla_nueva_pisa_a_otra(mundo):
    from houdini_engine.formats import pcf2000_manager as PM
    _raw, _nom = mundo
    duenyo = {}
    for _p, e, off, n in PM.DIVISIONS["2001"]:
        for i in range(n):
            duenyo[off + 2 * i] = e
    for c in PM.FDI_EUROCUPS[BUILD_2001]:
        for campo in ("slots", "mirror"):
            for o in (c.get(campo) or []):
                sitio = o - PM._VB6
                assert sitio not in duenyo, f"«{c['key']}» pisa «{duenyo[sitio]}»"
                duenyo[sitio] = c["key"]
