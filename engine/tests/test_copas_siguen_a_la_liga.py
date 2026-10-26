"""Al recolocar divisiones, las copas nacionales tienen que ir detrás.

La Copa del Rey la juegan los clubes de 1ª y 2ª; la F.A. Cup, los de las cuatro divisiones
inglesas. Si el import sube a un equipo de 2ªB a Segunda y baja a otro, esas copas se quedaban
con los equipos VIEJOS: el que bajó seguía jugando la Copa del Rey y el que subió no aparecía.

Las copas de Alemania y Francia sí se arrastraban, pero por casualidad: son copia **byte a
byte** de su liga, y `escribe_divisiones` las encuentra buscando esos mismos bytes. La Copa del
Rey (42 clubes de dos divisiones, en otro orden) y la F.A. Cup (124, con las inferiores) no se
encuentran así.

Ahora se compara **quién entra y quién sale de la división**, una sola vez y al terminar de
escribirla. Eso es justo lo contrario de hacerlo plaza a plaza mientras se escribe, que fue el
primer intento y destrozaba la copa: el orden de la liga cambia cada temporada, y con una simple
rotación los cambios se encadenaban (la plaza 1 pasa de A a B, así que toda A se vuelve B; luego
la plaza 2 pasa de B a C y arrastra también lo recién escrito) hasta dejar la Copa del Rey con
cuatro equipos. Yendo por membresía, reordenar la liga no toca la copa — que es lo correcto.

La sustitución es por EQUIPO, no por posición, así que respeta el orden propio de la copa (las
rondas) y los clubes que figuran en más de una plaza.
"""
import os
import struct
import sys

import pytest

RAIZ = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, os.path.join(RAIZ, "engine"))

ESPAÑA, INGLATERRA = 22, 30

BASES = {
    "2001": (os.path.join(RAIZ, "gamedata", "PCF2001", "manager.exe"), 7991296),
    "7": (os.path.join(RAIZ, "gamedata", "FUTBOL7", "MANAGER.EXE"), 4939776),
}


def _raw(edicion):
    ruta, tam = BASES[edicion]
    if not os.path.exists(ruta):
        pytest.skip(f"sin el manager.exe de {edicion}")
    with open(ruta, "rb") as f:
        raw = f.read()
    assert len(raw) == tam
    return raw


def _divs(edicion):
    from houdini_engine.formats import pcf2000_manager as PM, pcf7_manager as P7
    return P7.DIVISIONS if edicion == "7" else PM.DIVISIONS["2001"]


def _off(edicion, pais, etiqueta):
    return next((o, n) for p, e, o, n in _divs(edicion) if (p, e) == (pais, etiqueta))


def _cup_slots(edicion):
    from houdini_engine.formats import pcf2000_manager as _PM  # registra las de 2000/2001
    from houdini_engine.formats import pcf7_manager as P7
    assert _PM
    return P7.CUP_SLOTS[BASES[edicion][1]]


def _en_copas(raw, edicion, code):
    return [o for o in _cup_slots(edicion)
            if struct.unpack_from("<H", raw, o)[0] == code]


# ───────────────────────── el comportamiento nuevo ─────────────────────────

def _recoloca(edicion, pais, etiqueta, codes):
    """Reescribe una división por el camino de verdad (el que usa el import)."""
    from houdini_engine.formats import pcf2000_manager as PM, pcf7_manager as P7
    raw = _raw(edicion)
    off, n = _off(edicion, pais, etiqueta)
    if edicion == "7":
        out = P7.set_divisions(raw, [(pais, etiqueta, codes)])
    else:
        out = PM.set_divisions(raw, "2001", [(pais, etiqueta, codes)])
    return raw, out, off, n


@pytest.mark.parametrize("edicion", ["2001", "7"])
def test_el_que_sube_entra_en_la_copa_y_el_que_baja_sale(edicion):
    raw = _raw(edicion)
    off, n = _off(edicion, ESPAÑA, "Primera División")
    actual = [struct.unpack_from("<H", raw, off + 2 * i)[0] for i in range(n)]
    sale = actual[0]
    entra = next(c for c in range(9000, 9500) if not _en_copas(raw, edicion, c))

    antes = _en_copas(raw, edicion, sale)
    assert antes, "el club de la plaza 1 no jugaba ninguna copa: mal elegido el caso"

    _r, out, _o, _n = _recoloca(edicion, ESPAÑA, "Primera División", [entra] + actual[1:])

    assert struct.unpack_from("<H", out, off)[0] == entra
    assert sorted(_en_copas(out, edicion, entra)) == sorted(antes), "la copa no ha seguido"
    assert not _en_copas(out, edicion, sale), "el que se fue sigue jugando la copa"


@pytest.mark.parametrize("edicion", ["2001", "7"])
def test_reordenar_la_liga_no_toca_la_copa(edicion):
    """El caso que hay que no romper, y el que destapó el fallo: el orden de la liga cambia
    cada temporada y eso NO cambia quién juega la copa. Sustituyendo plaza a plaza, una simple
    rotación encadenaba los cambios y dejaba la Copa del Rey con cuatro equipos."""
    raw = _raw(edicion)
    off, n = _off(edicion, ESPAÑA, "Primera División")
    actual = [struct.unpack_from("<H", raw, off + 2 * i)[0] for i in range(n)]
    _r, out, _o, _n = _recoloca(edicion, ESPAÑA, "Primera División", actual[1:] + [actual[0]])

    slots = _cup_slots(edicion)
    assert ([struct.unpack_from("<H", out, o)[0] for o in slots]
            == [struct.unpack_from("<H", raw, o)[0] for o in slots]), "la copa se ha movido"


def test_no_se_toca_nada_si_la_liga_no_cambia():
    raw = _raw("2001")
    off, n = _off("2001", ESPAÑA, "Primera División")
    actual = [struct.unpack_from("<H", raw, off + 2 * i)[0] for i in range(n)]
    _r, out, _o, _n = _recoloca("2001", ESPAÑA, "Primera División", actual)
    assert out == raw, "reescribir lo mismo ha modificado el binario"


def test_solo_se_escribe_donde_estaba_ese_equipo():
    """La sustitución se comprueba plaza a plaza: si una copa ya se retocó a mano y ahí no está
    el equipo que sale, no se pisa."""
    from houdini_engine.formats import pcf2000_manager as PM
    raw = _raw("2001")
    off, n = _off("2001", ESPAÑA, "Primera División")
    actual = [struct.unpack_from("<H", raw, off + 2 * i)[0] for i in range(n)]
    tocada = _en_copas(raw, "2001", actual[0])[0]
    b = bytearray(raw)
    struct.pack_into("<H", b, tocada, 8888)        # alguien cambió esa plaza a mano
    out = PM.set_divisions(bytes(b), "2001",
                           [(ESPAÑA, "Primera División", [9999] + actual[1:])])
    assert struct.unpack_from("<H", out, tocada)[0] == 8888, "se ha pisado una copa retocada"


def test_el_tamano_del_ejecutable_no_cambia():
    raw = _raw("2001")
    off, n = _off("2001", ESPAÑA, "Segunda División")
    actual = [struct.unpack_from("<H", raw, off + 2 * i)[0] for i in range(n)]
    _r, out, _o, _n = _recoloca("2001", ESPAÑA, "Segunda División", [9999] + actual[1:])
    assert len(out) == len(raw)


# ───────────────────────── de punta a punta ─────────────────────────

def test_las_copas_registradas_son_las_que_dependen_de_la_liga():
    """Guardarraíl: que no se cuele aquí una Supercopa o un trofeo de pretemporada, cuyos
    participantes se eligen a mano y no tienen por qué seguir a la división."""
    from houdini_engine.formats import pcf2000_manager as PM, pcf7_manager as P7
    marcadas = {c["key"] for c in PM.FDI_EUROCUPS[7991296] if c.get("sigue_liga")}
    marcadas |= {t["key"] for t in P7.FDI_TABLES[4939776] if t.get("sigue_liga")}
    assert marcadas
    for k in marcadas:
        assert "supercopa" not in k and "trofeo" not in k and "mundo" not in k, k
    # y las que NO se marcan siguen sin estar
    for c in PM.FDI_EUROCUPS[7991296]:
        if c["key"] in ("euro_pool", "mundo", "champions", "supercopas"):
            assert not c.get("sigue_liga"), c["key"]


def test_pcf2000_todavia_no_tiene_copas_registradas():
    """A propósito: en PCF2000 las copas nacionales están localizadas pero sin mapear (sus
    plazas traen códigos que ni siquiera están en su base). Cuando se mapeen, este test cambia."""
    from houdini_engine.formats import pcf2000_manager as _PM
    from houdini_engine.formats import pcf7_manager as P7
    assert _PM
    assert not P7.CUP_SLOTS.get(5115904)
