"""Tablas de competición de PCF 3.0, leídas CON ESTRUCTURA.

Los seis `.DBC` de competición (LIGA, COPAREY, EUROPA, UEFA, ARBITROS, COMMENT) se venían
enseñando como una lista plana de textos anónimos —«Texto», «Texto», «Texto»…— porque el
escaneo solo busca cadenas. Pero no son textos sueltos: son SECUENCIAS DE REGISTROS, y entre
cadena y cadena van los NÚMEROS del registro (partidos, goles, puntos, años).

Regla común a todos (2026-08-30, ingeniería inversa contra la historia real):

    registro = [texto…] + números u16 + una MARCA u16

La marca vale 0 dentro de un grupo y, en el límite, lleva el AÑO DEL GRUPO SIGUIENTE
(9999 = se acabó). Es decir, el año va POR DELANTE del grupo que nombra, así que el primer
grupo de cada fichero no tiene año escrito y hay que saberlo (Liga 1928-29, Copa 1902).

Comprobado contra la realidad, no solo contra el fichero:
  · Liga 1928-29: Barcelona campeón con 25 puntos, 18 PJ, 11-3-4, 37-23.
  · El corte de la guerra: los años saltan de 1935 a 1939, y las plantillas de 10/12/14
    equipos por temporada cuadran con las de verdad. Eso es lo que demuestra que el año ABRE
    el grupo (si lo cerrara, la temporada 1935-36 quedaría etiquetada como 1939).
  · Palmarés al pie: Madrid 25 Ligas, Barcelona 14 · Athletic 23 Copas, Barcelona 22.
  · Copa 1902 Vizcaya 2-1 Barcelona · 1994 Zaragoza 0-0 Celta (la de los penaltis).
  · Copa de Europa 1956 Real Madrid 4-3 Stade de Reims.
  · Ranking europeo: los puntos son 2·PG + PE (Real Madrid 227 = 2·101 + 25).

Cada celda lleva su OFFSET para poder editarla: los textos por el mismo camino de siempre
(`Pcf3DB.set_field`) y los números escribiendo el u16 en su sitio (`set_num`), que no mueve
un byte del fichero.
"""

from __future__ import annotations

import struct

from . import pcf3 as _p3

# La marca de año que cierra la lista (no es una temporada).
FIN = 9999
# Marcador de "no hubo partido de vuelta" en las finales a doble partido de la UEFA.
SIN_VUELTA = 99

# Primer año de cada fichero: no está escrito porque el año abre el grupo SIGUIENTE.
PRIMER_ANO = {"LIGA.DBC": 1929, "COPAREY.DBC": 1902}

_APARTADOS = ("Novedades en el equipo", "Sistema de juego", "Objetivo en la Liga")


def _num(db, off: int) -> int:
    return struct.unpack_from("<H", db.raw, off)[0]


def set_num(db, off: int, valor: int) -> None:
    """Escribe un número u16 del registro. No cambia la longitud: el fichero no se mueve."""
    if not (0 <= off <= len(db.raw) - 2):
        raise ValueError("offset fuera del fichero")
    if not (0 <= valor <= 65535):
        raise ValueError("valor fuera de rango (0-65535)")
    struct.pack_into("<H", db.raw, off, valor)


def set_texto_hueco(db, off: int, texto: str) -> None:
    """Escribe un texto que no es un campo del índice sino que vive DENTRO del hueco del registro
    (la alineación del campeón). Conserva la longitud: se rellena con espacios y se rechaza lo que
    no quepa, así que el fichero no se mueve."""
    if off < 2 or off > len(db.raw):
        raise ValueError("offset fuera del fichero")
    ln = _num(db, off - 2)
    if off + ln > len(db.raw):
        raise ValueError("longitud incoherente")
    raw = texto.encode(db.cp, "replace")
    if len(raw) > ln:
        raise ValueError(f"máximo {ln} caracteres")
    raw = raw + b" " * (ln - len(raw))
    db.raw[off:off + ln] = bytes(b ^ ((0xC0 + ln + i) & 0xFF) for i, b in enumerate(raw))


def _celdas(db):
    """Para cada campo: (campo, offset donde empiezan sus números, cuántos bytes hay hasta el
    siguiente texto). Ese hueco es el registro, no relleno."""
    out, n = [], len(db.fields)
    for i, f in enumerate(db.fields):
        ini = f.data_off + f.length
        fin = db.fields[i + 1].off if i + 1 < n else len(db.raw)
        out.append((f, ini, max(0, fin - ini)))
    return out


def _txt(f, tope: int | None = None) -> dict:
    return {"t": "texto", "off": f.off, "v": f.text, "max": tope if tope is not None else f.length}


def _n(db, off: int, etq: str = "") -> dict:
    # sin la etiqueta cuando no la hay: son ~1.000 celdas por fichero y la respuesta abulta
    d = {"t": "num", "off": off, "v": _num(db, off)}
    if etq:
        d["etq"] = etq
    return d


# --------------------------------------------------------------------------------------------
#  LIGA.DBC — la clasificación final de CADA temporada, y al pie el palmarés
# --------------------------------------------------------------------------------------------
COLS_TABLA = ["Pos", "Equipo", "PJ", "PG", "PE", "PP", "GF", "GC", "Pts"]


def _liga(db) -> list[dict]:
    grupos, filas, palmares = [], [], []
    ano, ano_off = PRIMER_ANO["LIGA.DBC"] - 1, None
    for f, ini, hueco in _celdas(db):
        if hueco < 16:                                   # se acabaron las estadísticas: palmarés
            palmares.append({"celdas": [_txt(f)] + ([_n(db, ini, "Ligas")] if hueco >= 2 else [])})
            continue
        est = [_n(db, ini + 2 * k) for k in range(7)]
        filas.append({"celdas": [{"t": "pos", "v": len(filas) + 1}, _txt(f)] + est})
        marca = _num(db, ini + 14)
        if marca:                                        # la marca cierra el grupo y ABRE el siguiente
            grupos.append({"titulo": f"{ano}-{(ano + 1) % 100:02d}", "ano": ano,
                           "ano_off": ano_off, "filas": filas})
            filas, ano, ano_off = [], marca, ini + 14
    if filas:
        grupos.append({"titulo": f"{ano}-{(ano + 1) % 100:02d}", "ano": ano,
                       "ano_off": ano_off, "filas": filas})
    return [
        {"clave": "temporadas", "titulo": "Clasificación por temporada",
         "columnas": COLS_TABLA, "grupos": list(reversed(grupos))},
        {"clave": "palmares", "titulo": "Palmarés de Liga",
         "columnas": ["Equipo", "Ligas"], "grupos": [{"titulo": "", "filas": palmares}]},
    ]


# --------------------------------------------------------------------------------------------
#  COPAREY.DBC — la final de cada año, con el once del campeón
# --------------------------------------------------------------------------------------------
def _alineacion(db, ini: int, hueco: int):
    """En el hueco del subcampeón: [u16 goles][u16 longitud][once del campeón][u16 marca]."""
    if hueco < 6:
        return None, None, None, None
    goles = _num(db, ini)
    ln = _num(db, ini + 2)
    if not (0 < ln <= hueco - 6):
        return goles, None, None, (_num(db, ini + 2) if hueco >= 4 else None)
    once = _p3.decode_text(bytes(db.raw[ini + 4:ini + 4 + ln]), db.cp)
    return goles, once, ini + 4, _num(db, ini + 4 + ln)


def _copa(db) -> list[dict]:
    cel = _celdas(db)
    filas, palmares, ano, fin_finales = [], [], PRIMER_ANO["COPAREY.DBC"], 0
    i, n = 0, len(cel)
    while i < n - 1:
        f, ini, hueco = cel[i]
        if hueco != 2 or cel[i + 1][2] <= 6:
            i += 1
            continue
        sub, sub_ini, sub_hueco = cel[i + 1]
        goles_s, once, once_off, marca = _alineacion(db, sub_ini, sub_hueco)
        if once is None:
            i += 1
            continue
        fecha = cel[i - 1][0] if i and cel[i - 1][2] == 0 else None
        filas.append({"celdas": [
            {"t": "etq", "v": str(ano)},
            _txt(fecha) if fecha is not None else {"t": "etq", "v": ""},
            _txt(f), _n(db, ini, "Goles"),
            _txt(sub), _n(db, sub_ini, "Goles"),
            {"t": "hueco", "off": once_off, "v": once, "max": len(once), "largo": True},
        ]})
        if marca and marca != FIN:
            ano = marca
        i, fin_finales = i + 2, i + 2
    for f, ini, hueco in cel[fin_finales:]:
        if hueco >= 2:
            palmares.append({"celdas": [_txt(f), _n(db, ini, "Copas")]})
    return [
        {"clave": "finales", "titulo": "Finales de Copa",
         "columnas": ["Año", "Fecha", "Campeón", "", "Subcampeón", "", "Once del campeón"],
         "grupos": [{"titulo": "", "filas": list(reversed(filas))}]},
        {"clave": "palmares", "titulo": "Palmarés de Copa",
         "columnas": ["Equipo", "Copas"], "grupos": [{"titulo": "", "filas": palmares}]},
    ]


# --------------------------------------------------------------------------------------------
#  EUROPA.DBC / UEFA.DBC — ranking histórico de clubes + las finales
# --------------------------------------------------------------------------------------------
COLS_RANK = ["Club", "Pts", "Part.", "PJ", "PG", "PE", "PP", "GF", "GC"]


def _europeas(db, con_sede: bool) -> list[dict]:
    cel = _celdas(db)
    rank, finales, esp = [], [], []
    i, n, ano = 0, len(cel), 0
    while i < n:                                          # ranking: 8 números + marca
        f, ini, hueco = cel[i]
        if hueco < 18:
            break
        rank.append({"celdas": [_txt(f)] + [_n(db, ini + 2 * k) for k in range(8)]})
        ano = _num(db, ini + 16) or ano
        i += 1
    while i < n:
        f, ini, hueco = cel[i]
        if hueco < 2:
            break
        if con_sede:
            # sede+fecha [flag] · campeón [goles,0] · subcampeón [goles,len,once,marca]
            if i + 2 >= n or cel[i + 2][2] <= 6:
                break
            camp, camp_ini, _ = cel[i + 1]
            sub, sub_ini, sub_hueco = cel[i + 2]
            goles_s, once, once_off, marca = _alineacion(db, sub_ini, sub_hueco)
            if once is None:
                break
            finales.append({"celdas": [
                {"t": "etq", "v": f"{ano}-{(ano + 1) % 100:02d}"}, _txt(f),
                _txt(camp), _n(db, camp_ini, "Goles"),
                _txt(sub), _n(db, sub_ini, "Goles"),
                {"t": "hueco", "off": once_off, "v": once, "max": len(once), "largo": True},
            ]})
            i += 3
            if marca == FIN:
                break
            ano = marca or ano
        else:
            # equipo A [flag] · equipo B [ida, vuelta…, marca, flag]. El flag dice quién ganó:
            # 1 = el campeón es B, 0 = es A.
            if i + 1 >= n or hueco != 2:
                break
            b, b_ini, b_hueco = cel[i + 1]
            if b_hueco < 8:
                break
            campeon_es_b = bool(_num(db, ini))
            a1, b1 = _n(db, b_ini), _n(db, b_ini + 2)
            tercero = _num(db, b_ini + 4)
            if tercero == SIN_VUELTA:                     # partido único
                vuelta, marca_off = None, b_ini + 6
            else:
                vuelta = (_n(db, b_ini + 4), _n(db, b_ini + 6))
                marca_off = b_ini + 8
            marca = _num(db, marca_off) if marca_off + 2 <= b_ini + b_hueco else 0
            camp, sub = (b, f) if campeon_es_b else (f, b)
            ida = f"{a1['v']}-{b1['v']}" if not campeon_es_b else f"{b1['v']}-{a1['v']}"
            vue = ""
            if vuelta:
                vue = (f"{vuelta[1]['v']}-{vuelta[0]['v']}" if campeon_es_b
                       else f"{vuelta[0]['v']}-{vuelta[1]['v']}")
            finales.append({"celdas": [
                {"t": "etq", "v": str(ano)}, _txt(camp), _txt(sub),
                {"t": "etq", "v": ida}, {"t": "etq", "v": vue or "—"},
            ]})
            i += 2
            if marca == FIN:
                break
            ano = marca or ano
    for f, ini, hueco in cel[i:]:
        if hueco >= 2:
            esp.append({"celdas": [_txt(f), _n(db, ini, "Pts")]})
    cols_fin = (["Año", "Sede y fecha", "Campeón", "", "Subcampeón", "", "Once del campeón"]
                if con_sede else ["Año", "Campeón", "Subcampeón", "Ida", "Vuelta"])
    return [
        {"clave": "finales", "titulo": "Finales",
         "columnas": cols_fin, "grupos": [{"titulo": "", "filas": list(reversed(finales))}]},
        {"clave": "ranking", "titulo": "Ranking histórico de clubes",
         "columnas": COLS_RANK, "grupos": [{"titulo": "", "filas": rank}]},
        {"clave": "espanoles", "titulo": "Equipos españoles",
         "columnas": ["Club", "Pts"], "grupos": [{"titulo": "", "filas": esp}]},
    ]


# --------------------------------------------------------------------------------------------
#  ARBITROS.DBC — cuatro campos por árbitro
# --------------------------------------------------------------------------------------------
def _arbitros(db) -> list[dict]:
    filas = []
    for k in range(0, len(db.fields) - 3, 4):
        filas.append({"celdas": [_txt(x) for x in db.fields[k:k + 4]]})
    return [{"clave": "arbitros", "titulo": "Colegiados",
             "columnas": ["Nombre", "Nacimiento", "Profesión", "Comité autonómico"],
             "grupos": [{"titulo": "", "filas": filas}]}]


# --------------------------------------------------------------------------------------------
#  COMMENT.DBC — por equipo, tres apartados de texto (las líneas van sueltas, ya partidas)
# --------------------------------------------------------------------------------------------
def _comentarios(db, equipos: list[str] | None = None) -> list[dict]:
    grupos, actual, eq = [], None, 0
    for f in db.fields:
        cab = next((a for a in _APARTADOS if f.text.startswith(a)), None)
        if cab:
            if cab == _APARTADOS[0]:
                eq += 1
            nombre = (equipos[eq - 1] if equipos and 0 < eq <= len(equipos) else f"Equipo {eq}")
            actual = {"titulo": f"{nombre} · {cab}", "filas": []}
            grupos.append(actual)
            continue
        if actual is not None:
            actual["filas"].append({"celdas": [_txt(f)]})
    return [{"clave": "comentarios", "titulo": "Comentarios de pretemporada",
             "columnas": ["Texto"], "grupos": grupos}]


_LECTORES = {
    "LIGA.DBC": lambda db, eq: _liga(db),
    "COPAREY.DBC": lambda db, eq: _copa(db),
    "EUROPA.DBC": lambda db, eq: _europeas(db, con_sede=True),
    "UEFA.DBC": lambda db, eq: _europeas(db, con_sede=False),
    "ARBITROS.DBC": lambda db, eq: _arbitros(db),
    "COMMENT.DBC": lambda db, eq: _comentarios(db, eq),
}


def leer(db, fname: str, equipos: list[str] | None = None) -> list[dict]:
    """Secciones estructuradas del fichero, o `[]` si no se sabe leer (se cae a la lista plana)."""
    lector = _LECTORES.get(fname.upper())
    if not lector:
        return []
    try:
        return lector(db, equipos)
    except Exception:                                    # nunca peor que la lista plana de antes
        return []
