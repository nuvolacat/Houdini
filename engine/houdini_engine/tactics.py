"""Táctica DIBUJADA de PCF 5/6: decodificación del bloque de 176 bytes.

Estructura reverseada (2026-08-16, contrastando las 15 formaciones del `pcf.mdb` con
las de los dos editores comunitarios — idénticas byte a byte):

    176 bytes = 11 jugadores × 8 u16 LE (16 bytes por jugador)

    +0 xMin   +1 yMin   +2 ancho  +3 alto     ← ZONA de movimiento (rectángulo)
    +4 xDef   +5 yDef                          ← posición DEFENDIENDO (sin balón)
    +6 xAtk   +7 yAtk                          ← posición ATACANDO (con balón)

Ejes: `x` = eje LARGO (0 = línea de gol propia, ~320 = la rival), `y` = eje ANCHO
(0 = banda izquierda, 88 = centro, ~176 = banda derecha). El registro 1 es el
portero y es idéntico en las 15 tácticas: zona x[0,42] y[66,132], posición (0,88).

Verificado: en las 15 tácticas × 11 jugadores × 2 posiciones (330 casos) se cumple
`xMin ≤ x ≤ xMin+ancho` y `yMin ≤ y ≤ yMin+alto`, lo que descarta leer los campos
+2/+3 como xMax/yMax.
"""
from __future__ import annotations

import struct

BLOCK_LEN = 176          # el campo del bloque de equipo
PLAYERS = 11
X_MAX = 320.0            # eje largo (para normalizar a 0..1)
Y_MAX = 176.0            # eje ancho (centro = 88)


def decode_shape(blob: bytes, x_max: float = X_MAX, y_max: float = Y_MAX,
                 cell: bool = False) -> list[dict]:
    """Las 11 posiciones de una táctica. Devuelve, por jugador:
    `zone` (x, y, w, h), `def_` (x, y) y `atk` (x, y) en unidades del juego, más
    `nx/ny` (defensa) y `ax/ay` (ataque) NORMALIZADOS a 0..1 para pintarlos."""
    if not blob or len(blob) < BLOCK_LEN:
        return []
    out = []
    for i in range(PLAYERS):
        w = struct.unpack_from("<8H", blob, i * 16)
        # contrato COMÚN con FDI (pcf7.tactic_shape): d* = repliegue, n* = natural
        # (punto medio, la alineación que se muestra por defecto), a* = ataque.
        # PCF4 guarda CASILLAS de una rejilla (16×9), no píxeles: se pinta el CENTRO
        # de la casilla, así el portero (casilla y=4 de 9) queda centrado exacto.
        h = 0.5 if cell else 0.0
        dx, dy = (w[4] + h) / x_max, (w[5] + h) / y_max
        ax, ay = (w[6] + h) / x_max, (w[7] + h) / y_max
        out.append({
            "n": i + 1,
            "zone": {"x": w[0], "y": w[1], "w": w[2], "h": w[3]},
            "def_": {"x": w[4], "y": w[5]},
            "atk": {"x": w[6], "y": w[7]},
            "dx": round(dx, 4), "dy": round(dy, 4),
            "nx": round((dx + ax) / 2, 4), "ny": round((dy + ay) / 2, 4),
            "ax": round(ax, 4), "ay": round(ay, 4),
        })
    return out


def shift_player(blob: bytes, j: int, x: float, y: float,
                 x_max: float = X_MAX, y_max: float = Y_MAX,
                 keep_x0: bool = True, which: str = "nat") -> bytes:
    """Mueve al jugador `j` al punto (x, y) —en unidades del juego— y devuelve los 176 B.

    `which` dice QUÉ posición se coloca, que es justo lo que enseña el selector del campo:

      · `nat` — las dos a la vez, conservando la distancia entre ellas: el jugador se
        traslada entero y mantiene su carácter (un lateral que sube mucho lo sigue haciendo
        desde su nueva casilla). El objetivo es el punto medio, el que pinta la web.
      · `def` / `atk` — solo la de repliegue o solo la de ataque. Es la única forma de
        llevar a un delantero al córner: con las dos atadas, su punto medio no puede
        acercarse a la línea de gol sin sacar del campo la posición de ataque.

    La zona de movimiento acompaña siempre y se garantiza que sigue conteniendo al jugador.

    `keep_x0`: en v5/6 el primer u16 del bloque (zona xMin del portero) va SIEMPRE a 0 y en
    el fichero solo se guardan los otros 174 B, así que ese campo no puede salir de 0 sin
    perderse al escribir. Con la bandera puesta el portero solo se mueve a lo ancho — que es
    lo único que tiene sentido, porque su x es 0 en las 15 tácticas del juego.
    """
    if not blob or len(blob) < BLOCK_LEN or not 0 <= j < PLAYERS:
        return bytes(blob)
    out = bytearray(blob[:BLOCK_LEN])
    o = j * 16
    w = list(struct.unpack_from("<8H", out, o))
    mueve = {"def": (4, 5), "atk": (6, 7)}.get(which)          # None = las dos
    ref_x = w[mueve[0]] if mueve else (w[4] + w[6]) / 2.0
    ref_y = w[mueve[1]] if mueve else (w[5] + w[7]) / 2.0
    dx = int(round(max(0.0, min(x_max, x)) - ref_x))
    dy = int(round(max(0.0, min(y_max, y)) - ref_y))
    if keep_x0 and j == 0:
        dx = 0
    ejes = ((dx, 0, (4, 6), x_max), (dy, 1, (5, 7), y_max))
    for d, zona, par, tope in ejes:
        lim = int(tope)
        pos = tuple(k for k in par if mueve is None or k in mueve)   # lo que se mueve
        # mandan las POSICIONES: se recorta solo lo justo para que no se salgan del campo.
        # (Recortar por la zona dejaba a los jugadores de zona ancha sin poder llegar a la
        # banda: un rectángulo de 214 sobre un campo de 320 topa muchísimo antes.)
        d = max(-min(w[k] for k in pos), min(lim - max(w[k] for k in pos), d))
        for k in pos:
            w[k] += d
        # la zona le sigue conservando el tamaño; si se sale del campo, se desliza dentro
        z0, ancho = w[zona] + d, w[zona + 2]
        z0 = max(0, min(lim - ancho, z0)) if ancho <= lim else 0
        z1 = min(lim, z0 + ancho)
        # y se garantiza que sigue conteniendo las DOS posiciones (`xMin ≤ x ≤ xMin+ancho`
        # se cumple en los 330 casos reales, así que no se rompe): solo puede hacer falta
        # cuando la zona ya era casi todo el campo
        z0 = min(z0, *(w[k] for k in par))
        z1 = max(z1, *(w[k] for k in par))
        w[zona], w[zona + 2] = z0, z1 - z0
    struct.pack_into("<8H", out, o, *w)
    return bytes(out)


def infer_demarcations(shape: list[dict], u1: float = 0.22,
                       u2: float = 0.38) -> list[int]:
    """Demarcación aproximada de los 10 huecos de campo DEDUCIDA del propio dibujo.

    Hace falta porque los equipos de fábrica casi nunca usan una formación estándar:
    en 5.0/6.0 Oro solo "Por defecto" aparece como preset y el resto son dibujos
    ÚNICOS hechos por Dinamic (42 y 86 distintos). Sin esto, el once solo se podía
    armar por formación en los equipos con preset reconocido.

    Línea por `x` (largo del campo) y carril por `y` (ancho; y ALTO = banda derecha,
    y BAJO = izquierda, como en las tácticas estándar: lateral derecho y=154,
    lateral izquierdo y=16). Los centrales/medios centrados se reparten por
    profundidad (el más retrasado = líbero / medio centro defensivo)."""
    campo = [p for p in shape[1:]]                     # sin el portero
    if len(campo) != 10:
        return []
    # LÍNEAS: umbrales de profundidad (los que mejor reproducen las 15 formaciones
    # conocidas) y, SI alguna línea queda vacía —pasa con los dibujos atípicos de
    # Dinamic, muy retrasados, que daban formaciones imposibles tipo "6-4-0"—, se
    # reparte por los DOS saltos mayores, que garantiza 3 líneas no vacías.
    # se usa la posición de REPLIEGUE (`dx`), sobre la que están calibrados los
    # umbrales; `nx` es el punto medio y desplazaría todas las líneas.
    # `u1`/`u2` = fronteras defensa|medio y medio|delantero. Los valores por defecto
    # están calibrados para v5/6 (98% sobre las 15 formaciones conocidas); PCF4 usa su
    # propia escala de casillas y pasa 0.25/0.44 (ver PITCH_CELLS).
    _linea = {i: (1 if p["dx"] < u1 else 2 if p["dx"] < u2 else 3)
              for i, p in enumerate(campo)}
    if len(set(_linea.values())) < 3:
        orden = sorted(range(10), key=lambda i: campo[i]["dx"])
        cortes = sorted(k for _, k in sorted(
            ((campo[orden[k + 1]]["dx"] - campo[orden[k]]["dx"], k) for k in range(9)),
            reverse=True)[:2])
        _linea = {i: (1 if pos <= cortes[0] else 2 if pos <= cortes[1] else 3)
                  for pos, i in enumerate(orden)}

    def linea(p):
        return _linea[campo.index(p)]
    def carril(p):
        return "izq" if p["dy"] < 0.34 else ("der" if p["dy"] > 0.66 else "centro")
    out: list[int] = []
    for p in campo:
        ln, ca = linea(p), carril(p)
        if ln == 1:                                    # defensa
            out.append(3 if ca == "izq" else 2 if ca == "der" else 0)
        elif ln == 2:                                  # medio
            out.append(11 if ca == "izq" else 7 if ca == "der" else 0)
        else:                                          # delantero
            out.append(14 if ca == "izq" else 12 if ca == "der" else 9)
    # los centrados (0) se resuelven por profundidad dentro de su línea
    for ln, opciones in ((1, [4, 5, 6]), (2, [15, 10, 13])):
        idx = [i for i, p in enumerate(campo)
               if linea(p) == ln and carril(p) == "centro"]
        idx.sort(key=lambda i: campo[i]["dx"])         # del más retrasado al más adelantado
        for k, i in enumerate(idx):
            out[i] = opciones[min(k, len(opciones) - 1)]
    return out


def preset_shape(name: str) -> list[dict] | None:
    """Forma de una táctica ESTÁNDAR del juego, con la demarcación de cada hueco
    (Dem2..Dem11 del propio mdb; el hueco 1 es siempre el portero)."""
    from . import refdata
    for t in refdata.tactics():
        if t.get("Nom") != name:
            continue
        blob = bytes.fromhex(t.get("Hex") or "")
        if len(blob) == BLOCK_LEN - 2:      # el mdb guarda los 174 sin la cabecera
            blob = b"\x00\x00" + blob
        shape = decode_shape(blob)
        for i, p in enumerate(shape):
            p["dem"] = 1 if i == 0 else (t.get(f"Dem{i + 1}") or 0)
        return shape
    return None
