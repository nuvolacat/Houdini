"""Tablas de liga del `manager.exe` de PCF 2000/2001.

Como en v5/6/7: cada plaza de liga es un puntero de equipo **u16** en un offset fijo del
`manager.exe`. Leerlas da el MAPA DE DIVISIONES (qué equipo está en Primera/Segunda/2ªB),
que la web usa para desglosar España por divisiones en el grid.

Offsets por juego (2000 y 2001 tienen binarios DISTINTOS):
- **2001**: verificados contra el `manager.exe` real (coinciden con `spain.json` del editor
  Java de la comunidad). Primera=20, Segunda=22, 2ªB I-IV=20.
- **2000**: binario más pequeño (5,1 MB) con otro layout. Primera localizada y verificada
  por firma (contiene Barça=1 y Madrid=4). Segunda/2ªB PENDIENTES (layout distinto, requiere
  más ingeniería inversa) → esos equipos caen en "Otros" de momento.

Solo se modela la liga ESPAÑOLA (país 22): es la única jugable en estos juegos.
"""
from __future__ import annotations

import re as _re
import struct

from . import pcf7_manager as _PM7

from .pcf7_manager import _ENC, _cased, _find_cstring, _rename_in_prose  # C-strings (idéntico)

# países con liga jugable (solo España en 2000/2001; los foráneos son relleno)
PLAYABLE_COUNTRIES = (22,)

# (país, etiqueta, offset del manager.exe, nº de plazas) — offsets FIJOS verificados
# contra los manager.exe reales (2001 coincide con spain.json del editor Java).
# En PCF2000, Primera(20) y Segunda(22) van CONTIGUAS (0x4AC3C8 / +40); las 2ªB van
# dispersas con huecos → PENDIENTES (esos equipos caen en "Otros").
DIVISIONS: dict[str, list[tuple[int, str, int, int]]] = {
    "2001": [
        (22, "Primera División", 7555436, 20),
        (22, "Segunda División", 7555820, 22),
        (22, "Segunda B · Grupo I", 7555904, 20),
        (22, "Segunda B · Grupo II", 7555944, 20),
        (22, "Segunda B · Grupo III", 7555984, 20),
        (22, "Segunda B · Grupo IV", 7556024, 20),
    ],
    # PCF2000: Primera(20)+Segunda(22) contiguas; las 4 tablas de 2ªB van contiguas
    # cada 40 bytes desde 0x4AC944 (localizadas cruzando las capturas del juego; casan
    # 20/20/20/20 EXACTAS y en orden). Algunas plazas apuntan a equipos que NO están en
    # el eq00022.fdi (filiales/pequeños) → esos no se pintan. PCF2000 NO tiene Tercera.
    "2000": [
        # OJO — ESTO ESTABA MAL HASTA EL 22-sep-2026: apuntaba a 0x4AC3C8, que no es la Liga
        # sino el segundo bloque de la **Copa del Rey** (sus dos primeras plazas, 0x4AC3C4,
        # son los finalistas de la Copa anterior: Barcelona y Mallorca, que jugaron la final
        # del 97-98). Leerla «funcionaba» porque son los mismos 20 clubes, pero en OTRO ORDEN
        # —así que el puesto que dedujéramos podía no ser el suyo— y sobre todo **escribir**
        # recolocaba la Copa del Rey en vez de la Liga. Es el mismo fallo que tuvimos con la
        # Copa de Alemania, y aquí duele más porque España sí es jugable en 2000.
        # La LIGA1 de verdad está 736 bytes más allá y lo dice el propio ejecutable: detrás de
        # cada tabla escribe el nombre de su competición («CREY», «LIGA1», «LIGA2», «LIGA2B»).
        (22, "Primera División", 0x4AC6A4, 20),
        # Segunda: la tabla de DEFINICIÓN completa (22, con At.Madrid B) está en 0x4AC880;
        # la de 0x4AC3F0 es la de clasificación y tiene un hueco (le falta At.Madrid B).
        (22, "Segunda División", 0x4AC880, 22),
        (22, "Segunda B · Grupo I", 0x4AC944, 20),
        (22, "Segunda B · Grupo II", 0x4AC944 + 40, 20),
        (22, "Segunda B · Grupo III", 0x4AC944 + 80, 20),
        (22, "Segunda B · Grupo IV", 0x4AC944 + 120, 20),
    ],
}

# Tercera División de 2001: 17 grupos (3ª I…XVII), 22 plazas c/u, CONTIGUOS en el
# manager.exe (base 7556168, paso 44; offsets del spain.json del editor Java, verificados:
# 342/374 plazas con equipo español real). Se generan aquí para no listarlos a mano.
_ROMAN17 = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX",
            "X", "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII"]
DIVISIONS["2001"] += [(22, f"Tercera · Grupo {_ROMAN17[g]}", 7556168 + g * 44, 22)
                      for g in range(17)]

# LIGAS EXTRANJERAS de PCF2000. No estaban: sus equipos caían todos en «Otros». Localizadas
# con la misma regla del nombre que resolvió las copas de 2001 — cada tabla lleva detrás su
# identificador en texto («PREMIERLEAGUE», «SERIEA», «FRANCE1», «BUNDES1»…), así que no hay
# que deducir cuál es cuál ni arriesgarse a coger la copa gemela por la liga.
DIVISIONS["2000"] += [
    # Inglaterra (30). Cuentan también los galeses (Wrexham, Swansea), que juegan su liga.
    (30, "Premier League", 0x4AA344, 20),
    (30, "Division One", 0x4A9FC0, 24),
    (30, "Division Two", 0x4AA41C, 24),
    (30, "Division Three", 0x4AA4E4, 24),
    # Italia (36)
    (36, "Serie A", 0x4AACAC, 18),
    (36, "Serie B", 0x4AAECC, 20),
    (36, "Serie C1 - Grupo A", 0x4AAF88, 18),
    (36, "Serie C1 - Grupo B", 0x4AAFAC, 18),
    # Francia (24)
    (24, "Division 1", 0x4AE194, 18),
    (24, "Division 2", 0x4AE234, 20),
    # Alemania (2)
    (2, "1. Bundesliga", 0x4AE494, 18),
    (2, "2. Bundesliga", 0x4AE518, 18),
]

# LIGAS EXTRANJERAS de PCF2001 (descubiertas 2026-07-23 escaneando el manager.exe:
# runs de códigos de equipo válidos en 0x732000-0x738000). Cada liga tiene DOS copias
# (temporada 1999-00 y 2000-01); estos offsets son las tablas de la TEMPORADA EN CURSO
# (composición casada con la 2000-01 real: Serie A=18 con Brescia/Vicenza/Atalanta,
# Premier=20 con Ipswich/Charlton/Bradford…). LECTURA verificada; escritura PENDIENTE
# DE VALIDAR EN JUEGO (por eso PLAYABLE_COUNTRIES sigue siendo solo España).
DIVISIONS["2001"] += [
    # Inglaterra (30)
    (30, "Premier League", 7547384, 20),
    (30, "Division One", 7546708, 24),
    (30, "Division Two", 7547472, 24),
    (30, "Division Three", 7547568, 24),
    # Italia (36)
    (36, "Serie A", 7549196, 18),
    (36, "Serie B", 7549660, 20),
    (36, "Serie C1 - Grupo A", 7549760, 18),
    (36, "Serie C1 - Grupo B", 7549796, 18),
    # Francia (24)
    (24, "Division 1", 7565464, 18),
    (24, "Division 2", 7565540, 20),
    # Alemania (2). OJO: 7566240/7566280 NO son la liga, son la COPA de Alemania —que de
    # fábrica es su espejo exacto, por eso escribir ahí «funcionaba» por rebote del replicador
    # de secuencias. La liga de verdad está 216 bytes antes (verificado contra el mapa del
    # editor de pcfutbolmania y leyendo las cuatro tablas del binario, 21-sep-2026).
    (2, "1. Bundesliga", 7566024, 18),
    (2, "2. Bundesliga", 7566072, 18),
    # Y hay DOS categorías más que no estaban: las Regionalligas. No hay que deducir cuál es
    # cuál — el ejecutable pone el nombre detrás de cada tabla, «BUNDES3A» tras la de 20
    # equipos y «BUNDES3B» tras la de 18 (misma regla que da «BUNDES1», «BUNDES2» y
    # «CBUNDES» para la liga y la copa).
    (2, "Regionalliga Nord", 7566120, 19),
    (2, "Regionalliga Süd", 7566176, 18),
    # Argentina (3). La segunda categoría son DOS tablas seguidas y NO una de 20: Primera B
    # Interior (16) acaba justo donde empieza Primera B Metropolitana (7567880 + 16*2 =
    # 7567912). Con la entrada de 20 que había aquí se escribían cuatro códigos DENTRO del
    # Metropolitano, que es el patrón exacto del cuelgue por equipo en dos divisiones — y
    # Argentina es jugable en 2001, así que el import la recoloca de verdad.
    (3, "Primera División", 7567252, 20),
    (3, "Primera B Interior", 7567880, 16),
    (3, "Primera B Metropolitana", 7567912, 18),
    # Portugal (47)
    (47, "1ª División", 7567972, 18),
    (47, "2ª División", 7568020, 18),
    # Escocia (19)
    (19, "Premier League", 7568088, 12),
    (19, "First Division", 7568124, 10),
    # Holanda (27)
    (27, "Eredivisie", 7568176, 18),
    (27, "Eerste Divisie", 7568224, 18),
    # Bélgica (12)
    (12, "1ª División", 7568284, 18),
    (12, "2ª División", 7568332, 18),
]


def _divisions(variant: str) -> list[tuple[int, str, int, int]]:
    return DIVISIONS.get(variant, [])


def division_map(manager: bytes, variant: str) -> dict[int, tuple[int, str]]:
    """{código de equipo → (país, etiqueta de división)} leyendo las tablas de liga.
    Ignora plazas con puntero 0/0xFFFF (vacías) o fuera del fichero."""
    out: dict[int, tuple[int, str]] = {}
    n = len(manager)
    for pais, label, base, count in _divisions(variant):
        if base + count * 2 > n:
            continue
        for i in range(count):
            ptr = struct.unpack_from("<H", manager, base + i * 2)[0]
            if ptr and ptr != 0xFFFF:
                out.setdefault(ptr, (pais, label))
    return out


def divisions_of_country(variant: str, pais: int) -> list[str]:
    """Etiquetas de división de un país, en orden (para la navegación del grid)."""
    return [label for p, label, _o, _n in _divisions(variant) if p == pais]


# Países con LIGA JUGABLE = los del menú de PAÍS del juego (confirmado contra el
# juego real). NO derivado de los offsets que tenemos: en 2000 solo están reverseadas las tablas
# de España, pero el juego SÍ deja jugar en 5 países → hay que protegerlos igual del "Ampliar".
#   2000 = 5 (España, Inglaterra, Italia, Francia, Alemania)
#   2001 = 10 (+ Argentina, Portugal, Escocia, Holanda, Bélgica)
# Códigos: España 22 · Inglaterra 30 · Italia 36 · Francia 24 · Alemania 2 · Argentina 3 ·
#          Portugal 47 · Escocia 19 · Holanda 27 · Bélgica 12
_PLAYABLE: dict[str, frozenset] = {
    # ARGENTINA (3) ES JUGABLE EN PCF2000 (16-sep-2026, con el juego delante: su menú de
    # país la ofrece junto a Alemania, Italia, España, Inglaterra y Francia, y tiene TRES
    # divisiones — Primera A, 1ªB Metropolitana y 1ªB Interior). Lo confirma la base: sus 62
    # equipos son de ficha COMPLETA (tipo 0), como los de los países jugables, y no reducida.
    # Sus tablas de división todavía NO están localizadas —sus códigos (9001-9061) no aparecen
    # agrupados ni en el manager.exe ni en ningún otro fichero del juego, y los rótulos de la
    # pantalla no son texto del ejecutable—, así que no se recoloca; pero al ser jugable queda
    # protegida de que le cambiemos el número de equipos, que es lo que cuelga el juego.
    "2000": frozenset({22, 30, 36, 24, 2, 3}),
    "2001": frozenset({22, 30, 36, 24, 2, 3, 47, 19, 27, 12}),
}


def playable_countries(variant: str) -> frozenset:
    """Países con LIGA JUGABLE (menú de PAÍS del juego). NO se amplían con relleno. La
    RECOLOCACIÓN a la temporada actual requiere ADEMÁS tener los offsets de sus divisiones
    (`divisions_of_country`); los que no —las ligas extranjeras de PCF2000— quedan protegidos
    del 'Ampliar' pero solo se actualizan sus plantillas in situ (pendiente reversear offsets)."""
    return _PLAYABLE.get(variant, frozenset({22}))


def read_divisions(manager: bytes, variant: str) -> list[tuple[int, str, list[int]]]:
    """Tablas de división ORDENADAS tal como están en el manager.exe:
    [(país, etiqueta, [códigos])] — para sembrar sess.divisions al mover equipos."""
    out = []
    n = len(manager)
    for pais, label, base, count in _divisions(variant):
        if base + count * 2 > n:
            continue
        codes = [struct.unpack_from("<H", manager, base + i * 2)[0] for i in range(count)]
        out.append((pais, label, [c for c in codes if c and c != 0xFFFF]))
    return out


def set_divisions(manager: bytes, variant: str,
                  tables: list[tuple[int, str, list[int]]]) -> bytes:
    """Reescribe las tablas de división del manager.exe IN-PLACE. `tables` = lista de
    (país, etiqueta, [códigos en orden de clasificación]). Rellena hasta el nº de plazas
    y pone 0 en las que sobren. NO cambia el tamaño del binario. VALIDAR EN JUEGO."""
    off_of = {(p, label): (off, n) for p, label, off, n in _divisions(variant)}
    b = bytearray(manager)
    total = len(b)
    escribir = []
    for pais, label, codes in tables:
        oi = off_of.get((pais, label))
        if oi is None:
            continue
        off, n = oi
        if off + n * 2 > total:          # binario inesperado → no reventar la descarga
            continue
        escribir.append((off, n, codes))
    # mismo relleno que PCF7 (una sola implementación) y con TODAS las tablas a la vez: la plaza
    # que el plan no llena conserva su equipo de fábrica solo si no juega ya en otra división, y
    # nunca se escribe en los huecos que Dinamic dejó a 0. Y 2001 guarda 11 de sus divisiones
    # por DUPLICADO (las copas nacionales; las inglesas hasta por triplicado): hay que tocar
    # todas las copias. Ver `pcf7_manager.escribe_divisiones`.
    _PM7.escribe_divisiones(b, escribir)
    return bytes(b)


# --------------------------------------------------------------------------------
# NOMBRES DE COMPETICIÓN (texto plano NUL-terminado en el manager.exe de 2000/2001)
# Mismo enfoque que PCF7: búsqueda de contenido + reescritura in-place en el hueco.
# Solo se listan formas verificadas como C-string en los binarios reales. EXPERIMENTAL.
# --------------------------------------------------------------------------------
COMPETITIONS: list[dict] = [
    {"key": "primera", "label": "Primera División (España)",
     "fields": {"name": ["PRIMERA DIVISIÓN", "Primera División"], "abbr": ["Primera"]}},
    {"key": "segunda", "label": "Segunda División (España)",
     "fields": {"name": ["SEGUNDA DIVISIÓN", "Segunda División"], "abbr": ["Segunda"]}},
    {"key": "copadelrey", "label": "Copa del Rey",
     "fields": {"name": ["COPA DEL REY", "Copa del Rey"]}},
    {"key": "supercopa_esp", "label": "Supercopa de España",
     "fields": {"name": ["SUPERCOPA DE ESPAÑA", "Supercopa de España"]}},
    {"key": "champions", "label": "Liga de Campeones / Champions",
     "fields": {"name": ["Champions", "LIGA DE CAMPEONES", "Liga de Campeones"]}},
    {"key": "uefa", "label": "Copa de la UEFA",
     "fields": {"name": ["Copa de la UEFA"]}},
    {"key": "supercopa_eur", "label": "Supercopa de Europa",
     "fields": {"name": ["SUPERCOPA DE EUROPA"]}},
    {"key": "recopa", "label": "Recopa", "fields": {"name": ["RECOPA", "Recopa"]}},
    {"key": "intercontinental", "label": "Copa Intercontinental",
     "fields": {"name": ["Copa Intercontinental"]}},
]


def competition_fields(manager: bytes, overrides: dict | None = None) -> list[dict]:
    """Campos de nombre de competición editables (los que existen NUL-terminados)."""
    overrides = overrides or {}
    out = []
    for comp in COMPETITIONS:
        for fld, needles in comp["fields"].items():
            occ = [(off, room, nd) for nd in needles for off, room in _find_cstring(manager, nd)]
            if not occ:
                continue
            rep = next((nd for _o, _r, nd in occ if not nd.isupper()), occ[0][2])
            max_len = min(r for _o, r, _nd in occ)
            kf = f"{comp['key']}/{fld}"
            out.append({"key": comp["key"], "field": fld, "label": comp["label"],
                        "field_label": "Rótulo" if fld == "name" else "Sigla",
                        "original": rep, "value": overrides.get(kf, rep),
                        "max_len": max_len, "custom": kf in overrides})
    return out


def apply_competitions(manager: bytes, overrides: dict) -> bytes:
    """Aplica los overrides {key/field: valor} al binario (in-place, en el hueco).
    Cubre el rótulo standalone Y las menciones dentro de textos corridos (mismo
    alcance que los mods de la comunidad; ver pcf7_manager._rename_in_prose)."""
    data = bytearray(manager)
    for comp in COMPETITIONS:
        for fld, needles in comp["fields"].items():
            val = overrides.get(f"{comp['key']}/{fld}")
            if not val:
                continue
            for needle in needles:
                for off, room in list(_find_cstring(bytes(data), needle)):
                    enc = _cased(val.strip(), needle).encode(_ENC, "replace")
                    if len(enc) > room:
                        continue
                    data[off:off + room + 1] = enc + b"\x00" * (room + 1 - len(enc))
                if fld == "name" and len(needle) >= 8:
                    _rename_in_prose(data, needle, val)
    return bytes(data)


# --------------------------------------------------------------------------------
# EXTRAS DEL MANAGER (economía). Struct IDÉNTICO en 2000 y 2001 (mismo motor, mismos
# valores por defecto); solo cambia la BASE en el binario. Offsets 2001 del material VB6
# de la comunidad (PCF2001-main; VB6 1-based → aquí 0-based). Offsets 2000 localizados
# buscando el patrón de valores por defecto (mismo struct, base distinta). Verificados
# contra ambos binarios reales. Cada valor es un i32 LE contiguo.
# --------------------------------------------------------------------------------
_MERCH_PRODUCTS = ["Llaveros", "Guantes", "Gorras", "Chándals", "Camisetas", "CDs",
                   "Bufandas", "Tazas", "Banderas", "Balones", "Pósters", "Fotos"]
# (clave, etiqueta, offset RELATIVO a la base de merchandising, nº productos)
_MERCH_LAYOUT = [
    ("precio_min", "Precio mínimo", 0, 12),
    ("precio_max", "Precio máximo", 48, 12),
    ("maximo_fabrica", "Máx. fábrica", 96, 6),   # solo 6 productos en el fichero
    ("salto_precio", "Salto de precio", 120, 12),
    ("nivel_ventas", "Nivel de ventas", 168, 12),
    ("auto_fabricacion", "Auto-fabricación", 228, 12),
]
# 16 valores i32 seguidos: 8 de ENTRADA y 8 de ABONO. Los ocho de abono faltaban hasta el
# 2026-08-20 (se leían y escribían solo los primeros 8). Verificado leyendo la tabla en los
# dos binarios: entrada 2.500/3.500/5.000/8.000 máx y 1.000/2.500/3.500/5.000 mín; abono
# 50.000/70.000/100.000/140.000 máx y 20.000/35.000/50.000/80.000 mín. Pesetas.
_PRICE_LABELS = ["Entrada · Grada (máx)", "Entrada · Tribuna (máx)",
                 "Entrada · Palco (máx)", "Entrada · VIP (máx)",
                 "Entrada · Grada (mín)", "Entrada · Tribuna (mín)",
                 "Entrada · Palco (mín)", "Entrada · VIP (mín)",
                 "Abono · Grada (máx)", "Abono · Tribuna (máx)",
                 "Abono · Palco (máx)", "Abono · VIP (máx)",
                 "Abono · Grada (mín)", "Abono · Tribuna (mín)",
                 "Abono · Palco (mín)", "Abono · VIP (mín)"]
_N_PRICES = len(_PRICE_LABELS)
_EXTRAS = {
    "2001": {"merch_base": 6762548, "prices_off": 6765388, "scout": True},
    "2000": {"merch_base": 4406444, "prices_off": 4452432, "scout": True},
}


def _merch_fields(variant: str):
    """[(clave, etiqueta, offset absoluto, count)] para la variante."""
    base = _EXTRAS[variant]["merch_base"]
    return [(k, lab, base + rel, cnt) for k, lab, rel, cnt in _MERCH_LAYOUT]


# FECHAS GRABADAS EN EL MANAGER. El juego lleva algunas fechas a fuego en el código, con
# esta forma:  `mov cl, MES` · `mov eax, AÑO` · `mov byte [..], DÍA`.
#
# Se localizan por ESTRUCTURA, no por offsets fijos: así valen para cualquier build (los que
# publicó la comunidad son de la v3.6 y no cuadran en el nuestro). El patrón exige que el DÍA
# sea un inmediato — hay más sitios que fijan mes y año pero toman el día de un registro, y
# esos no se pueden editar así.
#
# En PCF2001 salen CINCO y son los cinco PARTIDOS DE PRETEMPORADA: 10/07, 05/08, 13/08,
# 13/08 y 19/08 del 2000, justo antes de que arranque la liga. Coinciden exactamente con los
# offsets que documentó la comunidad, redescubiertos por su forma.
# En PCF2000 salen SIETE y son una mezcla (dos de agosto del 99, cuatro de enero del 2000 y
# una de septiembre), así que ahí NO se afirma qué es cada una: se enseñan con su fecha.
_RX_FECHA = _re.compile(rb"\xb1([\x01-\x0c])\xb8([\xc0-\xe0])\x07\x00\x00"
                        rb"(\xc6\x05....|\xc6\x44\x24.)", _re.S)


def hardcoded_dates(manager: bytes) -> list[dict]:
    """Fechas grabadas en el manager, en orden de aparición."""
    out = []
    for m in _RX_FECHA.finditer(manager):
        o = m.start()
        cola = m.group(3)
        off_dia = o + 7 + (6 if cola[:2] == b"\xc6\x05" else 4)
        if off_dia >= len(manager):
            continue
        out.append({"index": len(out), "off_month": o + 1, "off_year": o + 3,
                    "off_day": off_dia, "day": manager[off_dia],
                    "month": m.group(1)[0],
                    "year": struct.unpack_from("<H", manager, o + 3)[0]})
    return out


def set_hardcoded_date(manager: bytes, index: int, day: int, month: int) -> bytes:
    """Cambia el día y el mes de una de esas fechas. El AÑO no se toca aquí: lo mueve el
    parche del año de temporada, que ya reconoce este `mov eax, AÑO` como constante."""
    fechas = hardcoded_dates(manager)
    if not 0 <= index < len(fechas):
        return manager
    f = fechas[index]
    b = bytearray(manager)
    b[f["off_day"]] = max(1, min(31, int(day))) & 0xFF
    b[f["off_month"]] = max(1, min(12, int(month))) & 0xFF
    return bytes(b)


def has_extras(variant: str) -> bool:
    return variant in _EXTRAS


def read_extras(manager: bytes, variant: str) -> dict:
    """Estado actual de los extras económicos del manager. {} si el juego no está mapeado."""
    cfg = _EXTRAS.get(variant)
    if not cfg:
        return {}
    n = len(manager)
    out: dict = {"products": list(_MERCH_PRODUCTS), "merch": {}, "prices": []}
    for key, label, off, cnt in _merch_fields(variant):
        if off + cnt * 4 > n:
            continue
        out["merch"][key] = {"label": label,
                             "values": [struct.unpack_from("<i", manager, off + i * 4)[0]
                                        for i in range(cnt)]}
    po = cfg["prices_off"]
    if po + _N_PRICES * 4 <= n:
        out["prices"] = [{"label": _PRICE_LABELS[i],
                          "value": struct.unpack_from("<i", manager, po + i * 4)[0]}
                         for i in range(_N_PRICES)]
    out["scout_available"] = bool(cfg.get("scout"))
    # fechas grabadas: en 2001 son los cinco partidos de pretemporada; en 2000 son siete y
    # de distinto tipo, así que se enseñan sin etiquetarlas
    fechas = hardcoded_dates(manager)
    out["dates_label"] = ("Partidos de pretemporada" if variant == "2001"
                          else "Fechas grabadas en el manager")
    out["dates"] = [{"index": f["index"], "day": f["day"], "month": f["month"],
                     "year": f["year"]} for f in fechas]
    return out


def apply_extras(manager: bytes, variant: str, changes: dict) -> bytes:
    """Aplica cambios a los extras (in-place). `changes` = {'merch': {campo: {idx: valor}},
    'prices': {idx: valor}, 'scout': bool}. Devuelve el manager parcheado."""
    cfg = _EXTRAS.get(variant)
    if not cfg:
        return manager
    b = bytearray(manager)
    n = len(b)
    merch_off = {key: (off, cnt) for key, _l, off, cnt in _merch_fields(variant)}
    for key, idxvals in (changes.get("merch") or {}).items():
        oc = merch_off.get(key)
        if not oc:
            continue
        off, cnt = oc
        for idx, val in idxvals.items():
            i = int(idx)
            if 0 <= i < cnt and off + i * 4 + 4 <= n:
                struct.pack_into("<i", b, off + i * 4, max(0, int(val)) & 0x7FFFFFFF)
    po = cfg["prices_off"]
    for idx, val in (changes.get("prices") or {}).items():
        i = int(idx)
        if 0 <= i < _N_PRICES and po + i * 4 + 4 <= n:
            struct.pack_into("<i", b, po + i * 4, max(0, int(val)) & 0x7FFFFFFF)
    for idx, dm in (changes.get("dates") or {}).items():
        try:
            b = bytearray(set_hardcoded_date(bytes(b), int(idx),
                                             int(dm.get("day", 1)), int(dm.get("month", 1))))
        except Exception:  # noqa: BLE001
            pass
    if changes.get("scout") and cfg.get("scout"):
        # Arreglo del ojeador (para que busque fuera del filial), según la utilidad
        # Java de Jordi Gironés. Es un reemplazo de `E3 26` → `00 00`, así que hay que
        # ceñirse EXACTAMENTE a lo que hace la suya: recorre el fichero DE DOS EN DOS y solo
        # sustituye en offsets PARES. Nosotros lo hacíamos en cualquier offset, que toca casi
        # el doble de sitios (26 contra 13 en 2000) — más agresivo que el original y sin
        # motivo. Sigue pendiente de localizar el sitio bueno por estructura, como se hizo
        # con los extracomunitarios de v5/6.
        for i in range(0, n - 1, 2):
            if b[i] == 0xE3 and b[i + 1] == 0x26:
                b[i] = b[i + 1] = 0x00
    return bytes(b)


# --- COPAS EUROPEAS (2026-08-16) ------------------------------------------------------
# Qué equipos juegan la Copa de Europa, la UEFA y cada Supercopa. Son punteros u16 en
# offsets sueltos del manager.exe. Offsets del editor comunitario J-Competiciones.
#
# GOTCHA: ese editor es VB6 y VB6 numera los ficheros DESDE 1 → el offset real es
# `constante - 1`. Con el ajuste, 30 de sus 32 constantes resuelven a equipos reales de
# nuestro manager (las 2 restantes venían ya a 0, sin mapear tampoco en el original) y
# el contenido casa con la temporada 2000/01: Copa de Europa España = Real Madrid,
# Barcelona, Deportivo y Valencia; UEFA España = Rayo, Zaragoza, Alavés y Espanyol;
# Italia = Juventus, Lazio, Milan e Inter. Clave del mapa = tamaño del manager.exe.
FDI_EUROCUPS: dict[int, list[dict]] = {
    7991296: [                                   # PC Fútbol 2001
        {"key": "champions_es", "label": "Copa de Europa — España",
         "slots": [2200424, 2200140, 2199956, 2200327]},
        {"key": "champions_ing", "label": "Copa de Europa — Inglaterra",
         "slots": [2200396, 2200258, 2199979, 2199884]},
        {"key": "champions_ita", "label": "Copa de Europa — Italia",
         "slots": [2200281, 2200071, 2199907, 2199651]},
        {"key": "uefa_es", "label": "Copa de la UEFA — España",
         "slots": [2254676, 2254760, 2254772, 2254784]},
        {"key": "uefa_ing", "label": "Copa de la UEFA — Inglaterra",
         "slots": [2254904, 2254916, 2254928]},
        {"key": "uefa_ita", "label": "Copa de la UEFA — Italia",
         "slots": [2254736, 2254748, 2254724]},
        {"key": "supercopas", "label": "Supercopas (campeón de Copa)",
         "slots": [7557021, 7545997, 7549873],
         "slot_labels": ["España", "Inglaterra", "Italia"]},
        # TABLAS GRANDES (2026-08-18): las mismas que en PCF7, localizadas barriendo el
        # ejecutable. Son BYTE A BYTE IDÉNTICAS en los tres juegos (PCF7, 2000 y 2001), o sea
        # datos fijos que Dinamic arrastró de versión en versión — por eso NO son los
        # participantes de la Copa de Europa de una temporada, como se creyó al principio.
        {"key": "euro_pool", "label": "Equipos europeos por país (lista fija)",
         "slots": [6840201, 6840203, 6840205, 6840207, 6840209, 6840211, 6840213, 6840215, 6840217, 6840219, 6840221, 6840223, 6840225, 6840227, 6840229, 6840231, 6840233, 6840235, 6840237, 6840239, 6840241, 6840243, 6840245, 6840247, 6840249, 6840251, 6840253, 6840255, 6840257, 6840259, 6840261, 6840263, 6840265, 6840267, 6840269, 6840271, 6840273, 6840275, 6840277, 6840279, 6840281, 6840283, 6840285, 6840287, 6840289, 6840291, 6840293, 6840295, 6840297, 6840299, 6840301, 6840303, 6840305, 6840307, 6840309, 6840311, 6840313, 6840315, 6840317, 6840319, 6840321, 6840323, 6840325, 6840327, 6840329, 6840331, 6840333, 6840335, 6840337, 6840339, 6840341, 6840343, 6840345, 6840347, 6840349, 6840351, 6840353, 6840355, 6840357, 6840359, 6840361, 6840363, 6840365, 6840367, 6840369, 6840371, 6840373, 6840375, 6840377, 6840379, 6840381, 6840383, 6840385, 6840387, 6840389, 6840391, 6840393, 6840395, 6840397, 6840399, 6840401, 6840403, 6840405, 6840407, 6840409, 6840411, 6840413, 6840415, 6840417, 6840419, 6840421, 6840423, 6840425, 6840427, 6840429, 6840431, 6840433, 6840435, 6840437, 6840439]},
        {"key": "champions", "label": "Equipos europeos — bloque de 16 (lista fija)",
         "slots": [6840441, 6840443, 6840445, 6840447, 6840449, 6840451, 6840453, 6840455, 6840457, 6840459, 6840461, 6840463, 6840465, 6840467, 6840469, 6840471]},
        {"key": "mundo", "label": "Grandes del mundo",
         "slots": [6785173, 6785175, 6785177, 6785179, 6785181, 6785183, 6785185, 6785187, 6785189, 6785191, 6785193, 6785195, 6785197, 6785199, 6785201, 6785203, 6785205, 6785207, 6785209, 6785211, 6785213, 6785215, 6785217, 6785219, 6785221, 6785223, 6785225, 6785227, 6785229, 6785231, 6785233, 6785235, 6785237]},
        {"key": "copa_liga_de", "label": "Copa de la Liga alemana",
         "slots": [6845217, 6845219, 6845221, 6845223, 6845225, 6845227]},
        # COPAS NACIONALES: no son deducción. Cada una es la COPIA EXACTA de una liga que ya
        # tenemos mapeada (mismos equipos, mismo orden), y en PCF7 el trabajo de josewolf22
        # demuestra que esa copia es la copa del país — coincide porque la juegan todos los
        # clubes de la división.
        {"key": "copa_fr_1", "sigue_liga": True, "label": "Copa de Francia — clubes de 1ª",
         "slots": [7565373, 7565375, 7565377, 7565379, 7565381, 7565383, 7565385, 7565387, 7565389, 7565391, 7565393, 7565395, 7565397, 7565399, 7565401, 7565403, 7565405, 7565407]},
        {"key": "copa_fr_2", "sigue_liga": True, "label": "Copa de Francia — clubes de 2ª",
         "slots": [7565413, 7565415, 7565417, 7565419, 7565421, 7565423, 7565425, 7565427, 7565429, 7565431, 7565433, 7565435, 7565437, 7565439, 7565441, 7565443, 7565445, 7565447, 7565449, 7565451]},
        # OJO: estos dos apuntaban a 7566024/7566072, que NO son la copa sino **las dos
        # Bundesligas** — la ficha «Copa de Alemania» editaba la liga por segunda vez y la copa
        # de verdad no se tocaba nunca. La copa está 216 bytes más allá (0x7373A0 / 0x7373C8),
        # y de fábrica es el espejo exacto de la liga, que es lo que despistó. Corregido el
        # 22-sep-2026 leyendo las cuatro tablas del binario y el mapa del editor comunitario.
        {"key": "copa_de_1", "sigue_liga": True, "label": "Copa de Alemania — clubes de 1ª",
         "slots": [7566241, 7566243, 7566245, 7566247, 7566249, 7566251, 7566253, 7566255, 7566257, 7566259, 7566261, 7566263, 7566265, 7566267, 7566269, 7566271, 7566273, 7566275]},
        {"key": "copa_de_2", "sigue_liga": True, "label": "Copa de Alemania — clubes de 2ª",
         "slots": [7566281, 7566283, 7566285, 7566287, 7566289, 7566291, 7566293, 7566295, 7566297, 7566299, 7566301, 7566303, 7566305, 7566307, 7566309, 7566311, 7566313, 7566315]},
        # ── COPAS NACIONALES DE PCF2001, identificadas por su NOMBRE en el propio
        # ejecutable (22-sep-2026). No es deducción: cada tabla de equipos lleva detrás el
        # identificador de su competición en texto plano —«CREY», «FACUP», «CCCUP»,
        # «CITALIA»— junto a su plantilla de calendario `actliga\XXXXX%03u.CPT`. Con esa
        # regla se comprueba además que lo ya mapeado estaba bien: la tabla que llamamos
        # Copa de Alemania va seguida de «CBUNDES», y las ligas de «BUNDES1»/«BUNDES2».
        {"key": "copa_rey_1", "sigue_liga": True, "label": "Copa del Rey — finalistas y clubes de 1ª y 2ª",
         "slot_labels": ["Finalista 1 (campeón del año anterior)", "Finalista 2"]
                       + [""] * 42,
         "slots": [
         7554729, 7554731, 7554733, 7554735, 7554737, 7554739, 7554741, 7554743, 7554745,
          7554747, 7554749, 7554751, 7554753, 7554755, 7554757, 7554759, 7554761, 7554763,
          7554765, 7554767, 7554769, 7554771, 7554773, 7554775, 7554777, 7554779, 7554781,
          7554783, 7554785, 7554787, 7554789, 7554791, 7554793, 7554795, 7554797, 7554799,
          7554801, 7554803, 7554805, 7554807, 7554809, 7554811, 7554813, 7554815]},
        {"key": "copa_rey_2", "sigue_liga": True, "label": "Copa del Rey — 2ªB y Tercera",
         "slots": [
         7554901, 7554903, 7554905, 7554907, 7554909, 7554911, 7554913, 7554915, 7554917,
          7554919, 7554921, 7554923, 7554925, 7554927, 7554929, 7554931, 7554933, 7554935,
          7554937, 7554939, 7554941, 7554943, 7554945, 7554947, 7554949, 7554951, 7554953,
          7554955, 7554957, 7554959, 7554961, 7554963, 7554965, 7554967, 7554969, 7554971,
          7554973, 7554975, 7554977, 7554979, 7554981, 7554983, 7554985, 7554987, 7554989,
          7554991, 7554993, 7554995, 7554997, 7554999, 7555001, 7555003, 7555005, 7555007,
          7555009, 7555011, 7555013, 7555015, 7555017, 7555019, 7555021, 7555023, 7555025,
          7555027, 7555029, 7555031, 7555033, 7555035]},
        # La composición real de la Copa del Rey, que hasta hoy era un «no lo sabemos»
        # apuntado en el revisor: 112 plazas en dos tablas. Y la primera NO son 44 clubes a
        # secas — las dos PRIMERAS plazas son los finalistas de la Copa del año anterior, que
        # por eso salen repetidos (de fábrica, Espanyol y Atlético: la final de 2000 la ganó
        # el Espanyol al Atlético). Las 42 restantes son exactamente el mismo conjunto que
        # Primera (20) + Segunda (22), comprobado contra las tablas de liga.
        {"key": "fa_cup", "sigue_liga": True, "label": "F.A. Cup",
         "slots": [
         7546425, 7546427, 7546429, 7546431, 7546433, 7546435, 7546437, 7546439, 7546441,
          7546443, 7546445, 7546447, 7546449, 7546451, 7546453, 7546455, 7546457, 7546459,
          7546461, 7546463, 7546465, 7546467, 7546469, 7546471, 7546473, 7546475, 7546477,
          7546479, 7546481, 7546483, 7546485, 7546487, 7546489, 7546491, 7546493, 7546495,
          7546497, 7546499, 7546501, 7546503, 7546505, 7546507, 7546509, 7546511, 7546513,
          7546515, 7546517, 7546519, 7546521, 7546523, 7546525, 7546527, 7546529, 7546531,
          7546533, 7546535, 7546537, 7546539, 7546541, 7546543, 7546545, 7546547, 7546549,
          7546551, 7546553, 7546555, 7546557, 7546559, 7546561, 7546563, 7546565, 7546567,
          7546569, 7546571, 7546573, 7546575, 7546577, 7546579, 7546581, 7546583, 7546585,
          7546587, 7546589, 7546591, 7546593, 7546595, 7546597, 7546599, 7546601, 7546603,
          7546605, 7546607, 7546609, 7546611, 7546613, 7546615, 7546617, 7546619, 7546621,
          7546623, 7546625, 7546627, 7546629, 7546631, 7546633, 7546635, 7546637, 7546639,
          7546641, 7546643, 7546645, 7546647, 7546649, 7546651, 7546653, 7546655, 7546657,
          7546659, 7546661, 7546663, 7546665, 7546667, 7546669, 7546671]},
        # 124 plazas: 121 clubes ingleses y 3 galeses (Cardiff, Swansea y Wrexham), que es
        # como la juega el juego.
        {"key": "copa_liga_ing", "sigue_liga": True, "label": "Copa de la Liga inglesa (Worthington)",
         "slots": [
         7545757, 7545759, 7545761, 7545763, 7545765, 7545767, 7545769, 7545771, 7545773,
          7545775, 7545777, 7545779, 7545781, 7545783, 7545785, 7545787, 7545789, 7545791,
          7545793, 7545795, 7545797, 7545799, 7545801, 7545803, 7545805, 7545807, 7545809,
          7545811, 7545813, 7545815, 7545817, 7545819, 7545821, 7545823, 7545825, 7545827,
          7545829, 7545831, 7545833, 7545835, 7545837, 7545839, 7545841, 7545843, 7545845,
          7545847, 7545849, 7545851, 7545853, 7545855, 7545857, 7545859, 7545861, 7545863,
          7545865, 7545867, 7545869, 7545871, 7545873, 7545875, 7545877, 7545885, 7545887,
          7545889, 7545891, 7545893, 7545895, 7545897, 7545901, 7545903, 7545905, 7545907,
          7545909, 7545911, 7545913, 7545915, 7545917, 7545919, 7545921, 7545923, 7545925,
          7545927, 7545929, 7545931, 7545933, 7545935, 7545937, 7545939, 7545941, 7545943,
          7545945, 7545947]},
        # 92 plazas = los 92 clubes de la Liga inglesa, en TRES bloques (61 + 7 + 24) con
        # unos bytes de separación entre ellos: es la entrada escalonada por rondas, y los 7
        # del bloque de en medio son los que jugaban en Europa. Por eso las plazas no son
        # correlativas. El identificador es «CCCUP» (Coca-Cola Cup, el nombre viejo del
        # patrocinio; las imágenes del juego dicen «cocacola» y «worthington»).
        {"key": "copa_ita", "sigue_liga": True, "label": "Copa de Italia",
         "slots": [
         7549061, 7549063, 7549065, 7549067, 7549069, 7549071, 7549073, 7549075, 7549077,
          7549079, 7549081, 7549083, 7549085, 7549087, 7549089, 7549091, 7549093, 7549095,
          7549097, 7549099, 7549101, 7549103, 7549105, 7549107, 7549109, 7549111, 7549113,
          7549117, 7549119, 7549121, 7549123, 7549125, 7549129, 7549131, 7549133, 7549135,
          7549137, 7549139, 7549141, 7549143, 7549145, 7549147, 7549149, 7549151, 7549153,
          7549155, 7549157, 7549159],
         "mirror": [
         7545657, 7545659, 7545661, 7545663, 7545665, 7545667, 7545669, 7545671, 7545673,
          7545675, 7545677, 7545679, 7545681, 7545683, 7545685, 7545687, 7545689, 7545691,
          7545693, 7545695, 7545697, 7545699, 7545701, 7545703, 7545705, 7545707, 7545709,
          7545713, 7545715, 7545717, 7545719, 7545721, 7545725, 7545727, 7545729, 7545731,
          7545733, 7545735, 7545737, 7545739, 7545741, 7545743, 7545745, 7545747, 7545749,
          7545751, 7545753, 7545755]},
        # 48 plazas en tres bloques (27 + 5 + 16), otra vez la entrada por rondas. OJO: en el
        # ejecutable hay DOS copias idénticas de esta tabla —la de «CITALIA» y otra igual 8 KB
        # antes, sin nombre propio—. Como no se puede demostrar cuál lee el juego, se escriben
        # LAS DOS (`mirror`): es exactamente el fallo de la Copa de Alemania, donde una ficha
        # editaba una tabla y el juego leía la otra.
        # ── TROFEOS DE PRETEMPORADA de PCF2001 (22-sep-2026). Los doce que trae el juego:
        # los siete que PCF7 ya tenía mapeados y cinco más que aparecieron en 2001 (Ciutat de
        # Barcelona, Ciudad de Vigo, La Línea, Villa de Gijón y Villa de Madrid; esos cinco
        # nombres no existen en el MANAGER.EXE de PCF7).
        #
        # Localizados con la misma regla del nombre, con una vuelta de tuerca: aquí la tabla no
        # va pegada al nombre, sino unos 200-270 bytes antes, con las rutas de sus imágenes por
        # medio. La distancia se MIDIÓ en PCF7, donde estas tablas ya estaban mapeadas, y se
        # buscó la misma forma en 2001 — y el número de plazas coincide en los siete trofeos
        # comunes (Bernabéu y Gamper 1, Naranja 2, Carranza, Colombino, Palma y Teresa Herrera
        # 3). Cada tabla lleva ceros delante y detrás.
        #
        # NO llevan `sigue_liga`: sus participantes son INVITACIONES (el Santos en el Bernabéu,
        # el PSV en el Gamper), no la composición de una división, y el anfitrión no figura.
        {"key": "trofeo_bernabeu", "label": "Trofeo Santiago Bernabéu",
         "slots": [7550285]},
        {"key": "trofeo_barcelona", "label": "Trofeo Ciutat de Barcelona",
         "slots": [7550653]},
        {"key": "trofeo_vigo", "label": "Trofeo Ciudad de Vigo",
         "slots": [7551021]},
        {"key": "trofeo_gamper", "label": "Trofeo Joan Gamper",
         "slots": [7551357]},
        {"key": "trofeo_linea", "label": "Trofeo de La Línea",
         "slots": [7551677, 7551679]},
        {"key": "trofeo_carranza", "label": "Trofeo Carranza",
         "slots": [7552081, 7552083, 7552085]},
        {"key": "trofeo_colombino", "label": "Trofeo Colombino",
         "slots": [7552453, 7552455, 7552457]},
        {"key": "trofeo_palma", "label": "Trofeo Ciutat de Palma",
         "slots": [7552833, 7552835, 7552837]},
        {"key": "trofeo_naranja", "label": "Trofeo Naranja",
         "slots": [7553265, 7553267]},
        {"key": "trofeo_herrera", "label": "Trofeo Teresa Herrera",
         "slots": [7553633, 7553635, 7553637]},
        {"key": "trofeo_gijon", "label": "Trofeo Villa de Gijón",
         "slots": [7554013]},
        {"key": "trofeo_villamadrid", "label": "Trofeo Villa de Madrid",
         "slots": [7554365]},
    ],
    5115904: [                                   # PC Fútbol 2000
        # Mismas cuatro tablas globales, verificadas igual. Las copas de Francia y Alemania
        # NO se mapean aquí: en 2000 esas ligas no están mapeadas, así que no puedo demostrar
        # cuál de las dos tablas gemelas es la liga y cuál la copa. Localizadas, sin etiquetar.
        {"key": "euro_pool", "label": "Equipos europeos por país (lista fija)",
         "slots": [4502517, 4502519, 4502521, 4502523, 4502525, 4502527, 4502529, 4502531, 4502533, 4502535, 4502537, 4502539, 4502541, 4502543, 4502545, 4502547, 4502549, 4502551, 4502553, 4502555, 4502557, 4502559, 4502561, 4502563, 4502565, 4502567, 4502569, 4502571, 4502573, 4502575, 4502577, 4502579, 4502581, 4502583, 4502585, 4502587, 4502589, 4502591, 4502593, 4502595, 4502597, 4502599, 4502601, 4502603, 4502605, 4502607, 4502609, 4502611, 4502613, 4502615, 4502617, 4502619, 4502621, 4502623, 4502625, 4502627, 4502629, 4502631, 4502633, 4502635, 4502637, 4502639, 4502641, 4502643, 4502645, 4502647, 4502649, 4502651, 4502653, 4502655, 4502657, 4502659, 4502661, 4502663, 4502665, 4502667, 4502669, 4502671, 4502673, 4502675, 4502677, 4502679, 4502681, 4502683, 4502685, 4502687, 4502689, 4502691, 4502693, 4502695, 4502697, 4502699, 4502701, 4502703, 4502705, 4502707, 4502709, 4502711, 4502713, 4502715, 4502717, 4502719, 4502721, 4502723, 4502725, 4502727, 4502729, 4502731, 4502733, 4502735, 4502737, 4502739, 4502741, 4502743, 4502745, 4502747, 4502749, 4502751, 4502753, 4502755]},
        {"key": "champions", "label": "Equipos europeos — bloque de 16 (lista fija)",
         "slots": [4502757, 4502759, 4502761, 4502763, 4502765, 4502767, 4502769, 4502771, 4502773, 4502775, 4502777, 4502779, 4502781, 4502783, 4502785, 4502787]},
        {"key": "mundo", "label": "Grandes del mundo",
         "slots": [4470913, 4470915, 4470917, 4470919, 4470921, 4470923, 4470925, 4470927, 4470929, 4470931, 4470933, 4470935, 4470937, 4470939, 4470941, 4470943, 4470945, 4470947, 4470949, 4470951, 4470953, 4470955, 4470957, 4470959, 4470961, 4470963, 4470965, 4470967, 4470969, 4470971, 4470973, 4470975, 4470977]},
        {"key": "copa_liga_de", "label": "Copa de la Liga alemana",
         "slots": [4506801, 4506803, 4506805, 4506807, 4506809, 4506811]},
    ],
}
_VB6 = 1        # las constantes del editor VB6 son 1-based


# Y las de 2000/2001, al mismo registro compartido (`pcf7_manager.CUP_SLOTS`). Las plazas se
# guardan aquí con el offset REAL, ya sin el +1 de las constantes del editor VB6.
_PM7.CUP_SLOTS.update({
    tam: [o - _VB6 for c in lista if c.get("sigue_liga")
          for o in (c.get("slots") or []) + (c.get("mirror") or [])]
    for tam, lista in FDI_EUROCUPS.items()
})


# ─────────────────────────── PROMEDIOS ARGENTINOS ───────────────────────────
# En Argentina el descenso no lo decide la clasificación del año sino el PROMEDIO: los puntos
# por partido de las últimas temporadas. El juego se guarda las dos anteriores de cada club en
# una tabla del `manager.exe`, y sin ellas un mod recolocado arranca con los promedios del
# 99-00 — el equipo que acabas de subir hereda los números del que estaba antes.
#
# 54 registros de 10 bytes seguidos (los 20 de Primera A + 16 de Primera B Interior + 18 de
# Metropolitana), cada uno: código de equipo u16, partidos y puntos de la ÚLTIMA temporada, y
# partidos y puntos de la PENÚLTIMA. Leído contra el binario real: River 38/59, Boca 38/89,
# Lanús 38/50 — cifras de la temporada que trae el juego.
PROMEDIOS: dict[int, tuple[int, int]] = {
    7991296: (7567292, 54),          # PC Fútbol 2001
}
_PROM_FMT = "<5H"
_PROM_LEN = 10


def promedios_read(manager: bytes) -> list[dict] | None:
    """`[{code, pj, pts, pj_ant, pts_ant}]` en el orden del fichero. None si no está mapeado."""
    sitio = PROMEDIOS.get(len(manager))
    if sitio is None:
        return None
    off, n = sitio
    if off + n * _PROM_LEN > len(manager):
        return None
    out = []
    for i in range(n):
        code, pj, pts, pj2, pts2 = struct.unpack_from(_PROM_FMT, manager, off + i * _PROM_LEN)
        out.append({"idx": i, "code": code, "pj": pj, "pts": pts,
                    "pj_ant": pj2, "pts_ant": pts2})
    return out


def promedios_write(manager: bytes, filas: list[dict]) -> bytes:
    """Escribe las filas indicadas por su `idx`. Tamaño intacto; lo que no venga se deja.

    Los puntos no pueden pasar de 3 por partido, que es lo máximo que se puede sacar: un
    promedio imposible descuadra la tabla de descensos del juego."""
    sitio = PROMEDIOS.get(len(manager))
    if sitio is None or not filas:
        return manager
    off, n = sitio
    b = bytearray(manager)
    for f in filas:
        i = int(f.get("idx", -1))
        if not 0 <= i < n:
            continue
        pos = off + i * _PROM_LEN
        code, pj, pts, pj2, pts2 = struct.unpack_from(_PROM_FMT, b, pos)
        nuevo = []
        for clave, actual in (("code", code), ("pj", pj), ("pts", pts),
                              ("pj_ant", pj2), ("pts_ant", pts2)):
            v = f.get(clave)
            nuevo.append(max(0, min(0xFFFF, int(v))) if v is not None else actual)
        nuevo[2] = min(nuevo[2], nuevo[1] * 3)
        nuevo[4] = min(nuevo[4], nuevo[3] * 3)
        struct.pack_into(_PROM_FMT, b, pos, *nuevo)
    return bytes(b)


def has_eurocups(manager: bytes) -> bool:
    return len(manager) in FDI_EUROCUPS


def eurocups_read(manager: bytes) -> list[dict] | None:
    """Competiciones del build con el puntero de cada plaza. None si no está mapeado."""
    lista = FDI_EUROCUPS.get(len(manager))
    if lista is None:
        return None
    out = []
    for c in lista:
        vals = []
        for i, off in enumerate(c["slots"]):
            o = off - _VB6
            vals.append(struct.unpack_from("<H", manager, o)[0]
                        if 0 <= o <= len(manager) - 2 else 0)
        out.append({"key": c["key"], "label": c["label"], "pointers": vals,
                    "slot_labels": c.get("slot_labels")})
    return out


def eurocups_write(manager: bytes, values: dict[str, list[int]]) -> bytes:
    """Escribe las plazas indicadas. Tamaño intacto; lo que no venga se deja igual."""
    lista = FDI_EUROCUPS.get(len(manager))
    if lista is None or not values:
        return manager
    b = bytearray(manager)
    por_clave = {c["key"]: c for c in lista}
    for key, ptrs in values.items():
        c = por_clave.get(key)
        if c is None:
            continue
        for i, v in enumerate(ptrs[:len(c["slots"])]):
            o = c["slots"][i] - _VB6
            if v is None or not (0 < int(v) <= 0xFFFF) or not (0 <= o <= len(b) - 2):
                continue
            struct.pack_into("<H", b, o, int(v))
            # tabla gemela: hay competiciones con DOS copias idénticas en el ejecutable y no
            # se puede demostrar cuál lee el juego, así que se escriben las dos. Dejar una
            # sin tocar es el fallo que tuvimos con la Copa de Alemania.
            esp = c.get("mirror") or []
            if i < len(esp):
                om = esp[i] - _VB6
                if 0 <= om <= len(b) - 2:
                    struct.pack_into("<H", b, om, int(v))
    return bytes(b)


# --- TOPES DEL MOTOR (2026-08-16) -----------------------------------------------------
# Localizados por el MENSAJE, no por offsets prestados: cada regla lleva su aviso al lado
# y los textos sí son comunes a todos los builds. `sites` = [(offset, ancho)] porque el
# número aparece a la vez en la comprobación y en el texto del aviso.
# PCF 2001 queda fuera: ahí no hay un tope único sino una cascada de comparaciones
# (1,2,3,4,5,6,7), o sea un `switch`, y habría que entenderlo antes de tocarlo.
FDI_LIMITS: dict[int, list[dict]] = {
    4939776: [                                   # PCF 7
        {"key": "ofertas", "label": "Ofertas por semana",
         "help": "«La directiva sólo te deja hacer N ofertas.» Se cambian a la vez la "
                 "comprobación y el número que sale en el aviso.",
         "sites": [(0x4C140, 1), (0x4C161, 1)], "factory": 5, "min": 1, "max": 99},
    ],
    5115904: [                                   # PCF 2000
        {"key": "ofertas", "label": "Ofertas por semana",
         "help": "«La directiva sólo te deja hacer N ofertas.» Dos comprobaciones más el "
                 "número del aviso.",
         "sites": [(0xE7881, 1), (0xE7B6F, 1), (0xEB512, 1), (0xEB532, 1)],
         "factory": 4, "min": 1, "max": 99},
        {"key": "cedidos", "label": "Jugadores cedidos",
         "help": "Cuántos puedes tener cedidos a la vez.",
         "sites": [(0xE78BE, 1)], "factory": 4, "min": 0, "max": 99},
        # EXTRACOMUNITARIOS: mismo mecanismo que en PCF7 (ver la nota larga en
        # `pcf7_manager.FDI_LIMITS`). El tope es una función `mov eax, N; ret` en la tabla de
        # métodos de cada competición, pegada a la que devuelve el texto del aviso, y vale a
        # la vez para fichar y para alinear. Dos cupos, 4 y 3, cada uno por su lado.
        {"key": "extracom", "label": "Extracomunitarios (cupo general)",
         "help": "Cuántos jugadores de fuera de la UE puedes fichar Y alinear. El juego "
                 "avisa: «No se permite contratar más de 4 jugadores extracomunitarios.» "
                 "Súbelo si al actualizar a una temporada reciente no te caben las "
                 "plantillas de hoy.",
         "vtable": 0x2249C0, "factory": 4, "min": 0, "max": 99},
        {"key": "extracom_bajo", "label": "Extracomunitarios (cupo reducido)",
         "help": "El mismo tope, para las competiciones donde el juego solo admite 3. Si "
                 "subes el general y este no, seguirás topado en esas.",
         "vtable": 0x16DA70, "factory": 3, "min": 0, "max": 99},
    ],
}


def limits_read(manager: bytes) -> list[dict] | None:
    lista = FDI_LIMITS.get(len(manager))
    if lista is None:
        return None
    out = []
    from .pcf7_manager import vtable_limit_read     # cupo por función propia (ver allí)
    for lim in lista:
        if "vtable" in lim:
            v = vtable_limit_read(manager, lim["vtable"])
            if v is not None:
                out.append({**{k: lim[k] for k in ("key", "label", "help", "factory", "min", "max")},
                            "value": v})
            continue
        o, ancho = lim["sites"][0]
        if o + ancho > len(manager):
            continue
        v = manager[o] if ancho == 1 else struct.unpack_from("<I", manager, o)[0]
        out.append({**{k: lim[k] for k in ("key", "label", "help", "factory", "min", "max")},
                    "value": v})
    return out


def limits_write(manager: bytes, values: dict) -> bytes:
    """Escribe los topes. Tamaño intacto; si un sitio no es plausible, no se toca ese tope."""
    lista = FDI_LIMITS.get(len(manager))
    if lista is None or not values:
        return manager
    b = bytearray(manager)
    por_clave = {x["key"]: x for x in lista}
    for key, v in values.items():
        lim = por_clave.get(key)
        if lim is None or v is None:
            continue
        val = max(lim["min"], min(int(v), lim["max"]))
        if "vtable" in lim:
            from .pcf7_manager import vtable_limit_write
            vtable_limit_write(b, lim["vtable"], val, lim["factory"])
            continue
        sitios = []
        for o, ancho in lim["sites"]:
            if o + ancho > len(b):
                sitios = []
                break
            actual = b[o] if ancho == 1 else struct.unpack_from("<I", b, o)[0]
            if not (0 <= actual <= 999) or (ancho == 1 and val > 255):
                sitios = []
                break
            sitios.append((o, ancho))
        for o, ancho in sitios:
            if ancho == 1:
                b[o] = val & 0xFF
            else:
                struct.pack_into("<I", b, o, val)
    return bytes(b)


# --- COMPOSICIÓN DE CONTINENTES (MANAGER.EXE de 2000/2001) --------------------------------------
# Mismo esquema que PCF7 pero base distinta por build; se localiza por FIRMA (inicio de Europa
# Occidental: Alemania..Inglaterra). Layout idéntico en 2000 y 2001 (verificado); slots = capacidad
# del bloque − 1 (se deja ≥1 byte separador, como en PCF7). 1 código de país por slot; 0 = vacío.
_CONT_SIG = bytes([2, 75, 5, 12, 18, 19, 22, 24, 27, 30])
_CONT_LAYOUT = [
    (1, "Europa Occidental", 0, 23),
    (2, "Europa Oriental", 24, 27),
    (3, "Norteamérica", 52, 3),
    (4, "Sudamérica", 56, 11),
    (5, "Asia Occidental", 68, 7),
    (6, "Asia Oriental", 76, 3),
    (7, "Oceanía", 80, 3),
    (8, "África", 84, 7),
]


def _continents_base(manager: bytes):
    i = manager.find(_CONT_SIG)
    return i if i >= 0 else None


def continents_layout(manager: bytes) -> list[tuple[int, str, int, int]]:
    """[(id, etiqueta, offset_absoluto, nº_slots)] de la tabla de continentes, o [] si no se halla."""
    base = _continents_base(manager)
    if base is None:
        return []
    return [(cid, lab, base + rel, n) for cid, lab, rel, n in _CONT_LAYOUT]


def read_continents(manager: bytes) -> dict[int, list[int]]:
    """{id_continente: [código_país, …]} (los 0 son slots vacíos)."""
    return {cid: list(manager[off:off + n]) for cid, _l, off, n in continents_layout(manager)}


def set_continents(manager: bytes, comp: dict[int, list[int]]) -> bytes:
    """Reescribe los bloques indicados en `comp` (recorta/rellena con 0 a su nº de slots)."""
    lay = continents_layout(manager)
    if not lay:
        return manager
    out = bytearray(manager)
    for cid, _l, off, n in lay:
        if cid in comp:
            codes = [c & 0xFF for c in comp[cid][:n] if c > 0]
            codes += [0] * (n - len(codes))
            out[off:off + n] = bytes(codes)
    return bytes(out)
