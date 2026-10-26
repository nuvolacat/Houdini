"""Las 40 zonas de la táctica dibujada de FDI: qué son de verdad.

La táctica dibujada de PCF7/2000/2001 son 1.760 bytes = **11 jugadores × 40 zonas × (x, y)**.
Eso estaba claro y el round-trip es byte-perfecto desde el principio. Lo que no estaba bien era
qué significan las 40 zonas.

Nuestra especificación decía `z = fila*8 + columna*2 + estado`, o sea **5 filas × 4 columnas**
de posición del balón. Midiendo las 898 tácticas de la base de PCF7 resulta que eso es falso y
la estructura real es:

    z = situación_del_balón * 2 + estado          (20 situaciones × 2 estados)
    situaciones = 4 CARRILES con (4, 6, 6, 4) pasos de profundidad

O sea: el balón se divide en cuatro carriles de izquierda a derecha, y dentro de cada uno en
pasos de avance — más finos por el centro (6) que por fuera (4). 4+6+6+4 = 20.

Lo que lo demuestra, y está comprobado aquí abajo:

* la lectura de 5×4 exige que la x crezca por tramos de cuatro, y **no se cumple en ninguno**
  de los 898 equipos; la de carriles se cumple en 896;
* los carriles **0 y 3** (exteriores) dan cifras casi idénticas entre sí, y los **1 y 2**
  (interiores) también: es la simetría izquierda/derecha de un campo de fútbol;
* el bit bajo separa dos situaciones con 86 unidades de diferencia en avance, en **898 de
  898** — es tener el balón o no tenerlo.

Importa para el editor por zonas: si la rejilla está mal, el dibujo que se le enseña al usuario
no es el que interpreta el juego.
"""
import os
import statistics as st
import sys

import pytest

RAIZ = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, os.path.join(RAIZ, "engine"))

PCF7 = os.path.join(RAIZ, "gamedata", "FUTBOL7", "DBDAT", "EQ99022.FDI")
PCF2001 = os.path.join(RAIZ, "gamedata", "PCF2001", "DBDAT", "eq00022.fdi")


def _tacticas(ruta, variante=None):
    if not os.path.exists(ruta):
        pytest.skip(f"sin {os.path.basename(ruta)}")
    with open(ruta, "rb") as f:
        d = f.read()
    nombre = os.path.basename(ruta)
    if variante:
        from houdini_engine.formats import pcf2000 as M
        eq = M.parse(d, nombre, variant=variante)
    else:
        from houdini_engine.formats import pcf7 as M
        eq = M.parse(d, nombre)
    return [t.tactica for t in eq.records
            if getattr(t, "tactica", None) and len(t.tactica) >= 1760]


def _xy(b, j, z):
    o = (j * 40 + z) * 4
    return (int.from_bytes(b[o:o + 2], "little"),
            int.from_bytes(b[o + 2:o + 4], "little"))


def _x(b, s):
    """Avance MEDIO de los 11 jugadores en la situación `s` (0..19), con el balón."""
    return st.mean([_xy(b, j, s * 2)[0] for j in range(11)])


def _y(b, s):
    return st.mean([_xy(b, j, s * 2)[1] for j in range(11)])


def _carriles():
    from houdini_engine.formats import pcf7 as P
    fuera, out = 0, []
    for n in P.ZONAS_POR_CARRIL:
        out.append(range(fuera, fuera + n))
        fuera += n
    return out


@pytest.fixture(scope="module")
def tac7():
    return _tacticas(PCF7)


# ───────────────── el bit de estado: con balón o sin él ─────────────────

def test_el_bit_bajo_separa_tener_el_balon_de_no_tenerlo(tac7):
    """Con la pelota el equipo está MÁS ADELANTADO, y no es una tendencia: pasa en todos."""
    dif = []
    for b in tac7:
        con = st.mean([_xy(b, j, z)[0] for j in range(11) for z in range(0, 40, 2)])
        sin = st.mean([_xy(b, j, z)[0] for j in range(11) for z in range(1, 40, 2)])
        dif.append(con - sin)
    assert min(dif) > 0, f"hay equipos al revés (mínimo {min(dif):+.0f})"
    assert st.mean(dif) > 50, f"la diferencia media es de solo {st.mean(dif):.0f}"


# ───────────────── la rejilla: 4 carriles de 4·6·6·4 ─────────────────

def test_la_lectura_vieja_de_cinco_filas_por_cuatro_es_falsa(tac7):
    """El test que destapó el fallo. Si las zonas fueran 5 filas de 4 columnas, la x media de
    cada fila tendría que crecer de la 0 a la 4, y no lo hace en NI UN equipo."""
    cumplen = 0
    for b in tac7:
        filas = [st.mean([_x(b, s) for s in range(f * 4, f * 4 + 4)]) for f in range(5)]
        cumplen += all(filas[i] <= filas[i + 1] for i in range(4))
    assert cumplen == 0, f"{cumplen} equipos la cumplen: revisar esta conclusión"


def test_dentro_de_cada_carril_el_equipo_avanza_con_el_balon(tac7):
    """Lo que sí se cumple: dentro de un carril, cuanto más adelantada es la situación, más
    arriba juega el equipo."""
    ok = 0
    for b in tac7:
        ok += all(all(_x(b, s) <= _x(b, s + 1) + 2 for s in list(g)[:-1]) for g in _carriles())
    assert ok >= len(tac7) * 0.99, f"solo {ok}/{len(tac7)}"


def test_el_equipo_se_desplaza_hacia_la_banda_del_balon(tac7):
    """Y de un carril al siguiente el equipo se corre hacia esa banda: la y crece del 0 al 3."""
    ok = 0
    for b in tac7:
        ys = [st.mean([_y(b, s) for s in g]) for g in _carriles()]
        ok += ys[0] <= ys[1] <= ys[2] <= ys[3]
    assert ok >= len(tac7) * 0.95, f"solo {ok}/{len(tac7)}"


def test_los_carriles_son_simetricos_como_un_campo(tac7):
    """Lo que remata la lectura: el carril 0 se parece al 3 (los exteriores, 4 pasos) y el 1 al
    2 (los interiores, 6). Si la división fuera otra, no habría por qué."""
    g = _carriles()
    avance = [st.mean([_x(b, s) for b in tac7 for s in c]) for c in g]
    assert abs(avance[0] - avance[3]) < 15, f"exteriores {avance[0]:.0f} vs {avance[3]:.0f}"
    assert abs(avance[1] - avance[2]) < 15, f"interiores {avance[1]:.0f} vs {avance[2]:.0f}"
    # y los interiores, con más pasos, no son un calco de los exteriores
    assert abs(avance[1] - avance[0]) > 3


def test_en_2001_la_rejilla_es_la_misma():
    """La familia FDI comparte pizarra: si 2001 no cuadrara, la lectura sería casualidad."""
    tac = _tacticas(PCF2001, "2001")
    ok = 0
    for b in tac:
        ys = [st.mean([_y(b, s) for s in g]) for g in _carriles()]
        ok += ys[0] <= ys[1] <= ys[2] <= ys[3]
    assert ok == len(tac), f"solo {ok}/{len(tac)}"


# ───────────────── los ayudantes que traducen la rejilla ─────────────────

def test_las_cuarenta_zonas_se_cubren_una_sola_vez():
    from houdini_engine.formats import pcf7 as P
    vistas = {}
    for c, n in enumerate(P.ZONAS_POR_CARRIL):
        for p in range(n):
            for con in (True, False):
                z = P.zona_de(c, p, con)
                assert z not in vistas, f"la zona {z} sale dos veces"
                vistas[z] = (c, p, con)
    assert sorted(vistas) == list(range(40))


def test_ida_y_vuelta_de_la_rejilla():
    from houdini_engine.formats import pcf7 as P
    for z in range(40):
        c, p, con = P.carril_y_paso(z)
        assert P.zona_de(c, p, con) == z


def test_no_se_admiten_zonas_que_no_existen():
    from houdini_engine.formats import pcf7 as P
    with pytest.raises(ValueError):
        P.zona_de(4, 0)                    # solo hay 4 carriles (0-3)
    with pytest.raises(ValueError):
        P.zona_de(0, 4)                    # el carril exterior solo tiene 4 pasos
    with pytest.raises(ValueError):
        P.zona_de(1, 6)                    # y el interior, 6
    assert P.zona_de(1, 5) == (4 + 5) * 2  # pero el 5 del interior sí existe
    for malo in (-1, 40, 99):
        with pytest.raises(ValueError):
            P.carril_y_paso(malo)
