"""PCF 7 / PC Calcio 7+ — contenedor FDI y registros (equipo/jugador/entrenador).

 PCF7 es la familia v5/v6 reorganizada:
mismo cifrado de texto (**XOR 0x61**, u16 LE de longitud), misma firma Dinamic y
mismos punteros canónicos, pero con **contenedor FDI con índice** en vez del PKF
único, y jugadores/entrenadores en **tablas propias** (no en la cola del equipo).

Ficheros (modo espejo, 2 temporadas 98/99): `EQ{98,99}022.FDI` (equipos),
`JUG{98,99}022.FDI` (jugadores), `ENT{98,99}022.FDI` (entrenadores).

Round-trip **byte-perfecto** verificado en los 6 FDI (41.341 registros). Los blobs
opacos (palmarés/historial 82B, táctica dibujada 1760B) se guardan crudos y se
editan por accessors tipados; el resto es campo a campo.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field

from ..codec import text as T

MAGIC = b"DMFIv1.0"
INDEX_ENTRY = 13          # u32 code + 1 pad + u32 inicio + u32 largo
HEADER_LEN = 20           # magic(8) + zero(8) + u32 count(4)
VERSION_700 = 700         # versión de registro (el juego la ignora; se preserva)

# TOPE DE PLANTILLA de PCF7: el nº de jugadores del equipo va en **u8** (`_ser_team`), así que
# el techo real es 255. El motor no impone tope (conserva todos los punteros); esto es para la
# UI, que devolvía 35 a fuego y deshabilitaba «Añadir jugador» con equipos de fábrica de 49-50.
# PCF2000/2001 usan `pcf2000.max_players(variant)` (255 / 65535 por el u16 de la versión 800).
MAX_PLAYERS = 255

# nombres de los 7 textos BBDD del jugador (esquema italiano)
PLAYER_BBDD = ("perfil", "caracteristicas", "palmares", "nacional",
               "anecdotas", "ultima_temporada", "trayectoria")

# las 16 medias, en orden
# ---- CÓDIGOS DE EQUIPO: van POR PAÍS, en bloques ----------------------------------------
# El código canónico de un equipo no es un número cualquiera: la familia FDI los reparte en
# BLOQUES DE 50 y cada bloque es de un país. En PCF7: España 1-182, Italia 201-292,
# Inglaterra 301-393, Alemania 401-465, Francia 501-571, Portugal 601-623, Yugoslavia 701…
# De los 200 bloques de 50 que caben, el juego usa 87 y solo 7 mezclan dos países (Gales
# dentro de Inglaterra y algún vecino pequeño), así que la regla es firme.
#
# **POR QUÉ IMPORTA (22-sep-2026).** Al ampliar la base metíamos cada equipo nuevo en el
# PRIMER código libre, que es el 32, el 46, el 49… o sea DENTRO DEL BLOQUE DE ESPAÑA. En el
# fichero no se nota —cada equipo lleva su país— pero el juego usa el rango de códigos para
# saber de quién es cada club, y un mod con clubes albaneses y argentinos en el hueco español
# enseñaba equipos franceses al entrar en la Segunda División y se caía. Un mod real con 541
# equipos nuevos lo destapó.
BLOQUE_CODIGOS = 50
CODIGO_MAX = 9999         # el juego solo referencia equipos de 4 dígitos (escudos `eq98NNNN`)


def bloques_de_pais(codigos: dict) -> dict:
    """`{país: {bloques de 50 donde tiene equipos}}` a partir de `{código: país}`."""
    out: dict = {}
    for code, pais in codigos.items():
        if code and 0 < code <= CODIGO_MAX:
            out.setdefault(pais, set()).add((code - 1) // BLOQUE_CODIGOS)
    return out


def codigo_para_pais(pais: int, bloques: dict, usados, tope: int = CODIGO_MAX) -> int:
    """Un código libre para un equipo NUEVO de `pais`, respetando el reparto por bloques.

    Primero, un hueco del propio bloque del país (España acaba en 182 y su bloque llega al
    200: ahí caben 18 equipos españoles más). Si el país no tiene bloque —porque el juego no
    traía ni un club suyo— o lo tiene lleno, se le reserva uno **entero libre**, de los 113
    que quedan sin usar. Lo que NO se hace nunca es colarlo en el bloque de otro país.
    """
    usados = set(usados)
    ocupados = {b for bs in bloques.values() for b in bs}
    propios = sorted(bloques.get(pais, ()))
    for b in propios:                                  # 1) hueco en su propio bloque
        for c in range(b * BLOQUE_CODIGOS + 1, min((b + 1) * BLOQUE_CODIGOS, tope) + 1):
            if c not in usados:
                return c
    for b in range(tope // BLOQUE_CODIGOS + 1):        # 2) un bloque entero libre para él
        if b in ocupados:
            continue
        for c in range(b * BLOQUE_CODIGOS + 1, min((b + 1) * BLOQUE_CODIGOS, tope) + 1):
            if c not in usados:
                bloques.setdefault(pais, set()).add(b)   # queda reservado para este país
                return c
    raise ValueError("no quedan códigos de equipo libres sin invadir el bloque de otro país")


MEDIA_NAMES = ("velocidad", "resistencia", "agresividad", "calidad", "remate",
               "regate", "pase", "tiro", "entradas", "portero", "pie",
               "penaltis", "corner_izq", "corner_der", "falta_izq", "falta_der")


# ------------------------------------------------------------------ helpers
class _R:
    """Lector secuencial."""
    __slots__ = ("d", "p")

    def __init__(self, d: bytes, p: int = 0):
        self.d, self.p = d, p

    def u8(self) -> int:
        v = self.d[self.p]; self.p += 1; return v

    def u16(self) -> int:
        v = struct.unpack_from("<H", self.d, self.p)[0]; self.p += 2; return v

    def u32(self) -> int:
        v = struct.unpack_from("<I", self.d, self.p)[0]; self.p += 4; return v

    def raw(self, n: int) -> bytes:
        v = self.d[self.p:self.p + n]; self.p += n; return v

    def st(self) -> str:
        n = self.u16()
        return T.decode(self.raw(n))


class _W:
    """Escritor secuencial."""
    __slots__ = ("b",)

    def __init__(self):
        self.b = bytearray()

    def u8(self, v: int):
        self.b.append(v & 0xFF)

    def u16(self, v: int):
        self.b += struct.pack("<H", v & 0xFFFF)

    def u32(self, v: int):
        self.b += struct.pack("<I", v & 0xFFFFFFFF)

    def raw(self, v: bytes):
        self.b += v

    def st(self, s: str):
        enc = T.encode(s)
        self.u16(len(enc))
        self.b += enc


def _sumalargos(*strings: str) -> int:
    """sumaLargos = Σ(len(cadena) + 1) de las cadenas con nombre propio."""
    return sum(len(T.encode(s)) + 1 for s in strings)


# ------------------------------------------------------------------ modelos
@dataclass
class Player:
    code: int                       # puntero canónico (= idFoto)
    tipo: int                       # 0 liga jugable (ficha completa) / 1 no jugable
    id_foto: int                    # SIEMPRE == code
    dorsal: int
    apodo: str
    nombre: str
    slot: int                       # posicionAlineacion (1..N; 99 = filial; 1-11 = once)
    estado: int                     # 0 continúa · 1 fichaje · 2 ascendido · 3 no aparece · 4 fichaje
    roles: bytes                    # 6 bytes
    nacionalidad: int
    piel: int
    pelo: int
    demarcacion: int                # 0 portero · 1 def · 2 medio · 3 delantero
    dia: int
    mes: int
    anyo: int
    altura: int
    peso: int
    version: int = VERSION_700
    # solo si tipo == 0
    pais_natal: int = 0
    ciudad: str = ""
    procedencia: str = ""
    internacional: str = ""         # es texto (p.ej. "22" o "Portugal")
    bbdd: list = field(default_factory=list)   # 7 textos (ver PLAYER_BBDD)
    medias: bytes = b"\x00" * 16    # 16 medias (ver MEDIA_NAMES)
    raw: bytes = b""                # ver Team.raw (registro no reconocido)
    opaque: bool = False

    def media(self, name: str) -> int:
        return self.medias[MEDIA_NAMES.index(name)]

    def set_media(self, name: str, value: int):
        m = bytearray(self.medias)
        m[MEDIA_NAMES.index(name)] = value & 0xFF
        self.medias = bytes(m)


@dataclass
class Coach:
    code: int                       # idEntrenador
    tipo: int                       # 0 ficha completa / 1 relleno (solo apodo)
    apodo: str
    version: int = VERSION_700      # el "pad" u16 = 700
    nombre: str = ""
    bbdd: list = field(default_factory=list)   # 6 textos
    flag: int = 0                   # 0 = no fue jugador / 3 = fue jugador
    extra: list = field(default_factory=list)  # 1 texto (flag 0) o 2 (flag 3)
    raw: bytes = b""                # ver Team.raw (registro no reconocido)
    opaque: bool = False


@dataclass
class Team:
    code: int                       # puntero canónico
    firma: bytes                    # 36 bytes "Copyright (c)1998 Dinamic Multimedia"
    tipo: int                       # 0 liga jugable / 1 foráneo
    pad: int                        # 1 byte (=0)
    nombre_corto: str
    estadio: str
    pais: int
    latitud: int                    # int8 con signo (grados de la ciudad)
    nombre: str
    sentados: int
    de_pie: int
    ancho_campo: int
    largo_campo: int
    fundacion: int
    version: int = VERSION_700
    # solo si tipo == 0
    anyo_estadio: int = 0
    socios: int = 0
    presidente: str = ""
    presupuesto: int = 0            # cassa gioco
    presupuesto_gen: int = 0        # cassa reale
    patrocinador: str = ""
    proveedor: str = ""
    filial: int = 0xFFFF            # 0xFFFF = sin filial
    palmares: bytes = b""           # 82 bytes: historial de liga (blob, accessors aparte)
    competiciones: list = field(default_factory=list)  # [(id, participaciones, titulos)]
    # presentes en TODOS los equipos:
    tactica: bytes = b"\x00" * 1760          # táctica dibujada (blob)
    tactica_equipo: bytes = b"\x00" * 7      # estilo: toque, contragolpe, ataque…
    entrenadores: list = field(default_factory=list)   # punteros u32 a ENT
    jugadores: list = field(default_factory=list)      # [(en_plantilla, puntero_u32)]
    # registro que NO cuadra con el layout conocido (mods de terceros): se guarda tal
    # cual y se re-emite byte a byte. Ver `_opaque_record`.
    raw: bytes = b""
    opaque: bool = False


@dataclass
class FdiFile:
    kind: str                       # "EQ" | "JUG" | "ENT"
    records: list = field(default_factory=list)   # Team | Player | Coach en orden de índice


# ---- HISTORIAL de liga (bloque `palmares`) y TÁCTICA de equipo (7 B) ----
# El bloque mide 82 B en PCF7/PCF2000 y 83 B en PCF2001: en 2001 hay un byte EXTRA (Girone3) en el
# índice 1, justo tras grupo2b, que DESPLAZA +1 todo lo que va detrás. Verificado empíricamente sobre
# los FDI reales: con el desplazamiento, pj/puntos/temporadas son plausibles en 987/987 equipos de
# 2001; sin él, solo en 659/987 (la interpretación de 82 B leía los campos 1 byte corridos). PCF7 y
# PCF2000 (82 B, sin Girone3) no se desplazan. Los offsets de abajo son los del bloque de 82 B; en
# 2001 se les suma `_hist_shift`. grupo2b va SIEMPRE en el índice 0 (no se desplaza).
_HIST_U8 = {"temporadas1a": 21, "campeon": 34, "subcampeon": 35}
_HIST_U16 = {"pj": 22, "pg": 24, "pe": 26, "gf": 28, "gc": 30, "puntos": 32}
TACTIC_FIELDS = ["toque", "contragolpe", "ataque", "entradas", "marcaje", "despejes", "presion"]


def _hist_shift(p) -> int:
    """+1 si el bloque de historial es el de PCF2001 (83 B, con el byte Girone3 extra en el índice 1);
    0 en PCF7/PCF2000 (82 B)."""
    return 1 if len(p) >= 83 else 0


# Los 17 grupos de TERCERA, que en 2001 son el byte `girone3` del historial. No es «en qué grupo
# juega este club»: lo llevan TODOS los clubes españoles, también los de Primera, porque es el
# grupo que le toca por REGIÓN —y por tanto a dónde caería si bajara—. Leído de la propia base:
# el Deportivo y el Celta llevan 1, el Oviedo y el Sporting 2, el Athletic y la Real 4, el Barça
# y el Espanyol 5, el Madrid y el Atlético 7, el Mallorca 11, el Tenerife y Las Palmas 12…
# Coinciden uno a uno con los grupos reales de la Tercera de entonces. 255 = sin grupo.
TERCERA_GRUPOS = {
    1: "I · Galicia", 2: "II · Asturias", 3: "III · Cantabria", 4: "IV · País Vasco",
    5: "V · Cataluña", 6: "VI · Comunidad Valenciana", 7: "VII · Madrid",
    8: "VIII · Castilla y León", 9: "IX · Andalucía oriental",
    10: "X · Andalucía occidental", 11: "XI · Baleares", 12: "XII · Canarias",
    13: "XIII · Murcia", 14: "XIV · Extremadura", 15: "XV · Navarra y La Rioja",
    16: "XVI · Aragón", 17: "XVII · Castilla-La Mancha", 255: "sin grupo",
}


def team_historial(t: "Team") -> dict | None:
    """Historial del club: grupo 2ªB (+ Girone3 en 2001), últimas 10 ligas como PARES
    (puesto, división), temporadas en 1ª, PJ/PG/PE/GF/GC/puntos, campeón/subcampeón y 46
    posiciones por jornada. Devuelve None si el equipo es foráneo (sin historial)."""
    p = t.palmares
    if len(p) < 82:
        return None
    s = _hist_shift(p)
    out: dict = {"grupo2b": p[0]}
    if s:
        out["girone3"] = p[1]                       # byte extra propio de 2001
    lb = 1 + s                                       # base de las 10 ligas (2 bytes/liga: puesto, div)
    out["ligas"] = [{"pos": p[lb + i * 2], "div": p[lb + i * 2 + 1]} for i in range(10)]
    for k, o in _HIST_U8.items():
        out[k] = p[o + s]
    for k, o in _HIST_U16.items():
        out[k] = struct.unpack_from("<H", p, o + s)[0]
    out["jornadas"] = list(p[36 + s:82 + s])
    return out


def set_historial_field(t: "Team", field: str, value: int) -> bool:
    p = bytearray(t.palmares)
    if len(p) < 82:
        return False
    s = _hist_shift(p)
    if field == "grupo2b":
        p[0] = value & 0xFF
    elif field == "girone3" and s:
        p[1] = value & 0xFF
    elif field in _HIST_U8:
        p[_HIST_U8[field] + s] = value & 0xFF
    elif field in _HIST_U16:
        struct.pack_into("<H", p, _HIST_U16[field] + s, value & 0xFFFF)
    elif field.startswith("liga_pos_"):
        i = int(field.rsplit("_", 1)[1])
        if not 0 <= i < 10:
            return False
        p[(1 + s) + i * 2] = value & 0xFF            # puesto (u8, byte bajo)
    elif field.startswith("liga_div_"):
        i = int(field.rsplit("_", 1)[1])
        if not 0 <= i < 10:
            return False
        p[(1 + s) + i * 2 + 1] = value & 0xFF        # división (u8, byte alto)
    elif field.startswith("jornada_"):
        i = int(field.rsplit("_", 1)[1])
        if not 0 <= i < 46:
            return False
        p[(36 + s) + i] = value & 0xFF
    else:
        return False
    t.palmares = bytes(p)
    return True


# ---- PALMARÉS DE COPAS (lista `competiciones`, aparte del historial de liga) ----
# En FDI el palmarés NO es un bloque fijo como en 5.0/6.0 (14 bytes, 7 competiciones): es una
# LISTA de longitud variable —`u8 nº` + n×(id, participaciones, títulos)— así que cada club
# lleva solo las competiciones que ha jugado, y un club puede tener 0. Por eso añadir o quitar
# una CAMBIA el tamaño del registro; el índice del FDI se recalcula solo al reemitir.
#
# Los 21 identificadores están descifrados contra la propia base de PCF2001, comprobando los
# títulos con la realidad (22-sep-2026). Los siete primeros son los mismos que ya etiquetamos en
# 5.0/6.0 — Madrid 8 Copas de Europa, Athletic 23 Copas del Rey, Barcelona 24 —, y del 7 en
# adelante hay competiciones que v5/6 no tenía:
#
#   7  Man Utd 10 · Tottenham 8 · Aston Villa 7        → F.A. Cup
#   8  Liverpool 5 · Aston Villa 5 · Forest 4          → Copa de la Liga inglesa
#   9  Man Utd 12 · Liverpool 12 · Arsenal 10          → Charity Shield
#   10 Man Utd 6 · Arsenal 1 · Blackburn 1 (4 clubes)  → Premier League (desde 1992)
#   11 Liverpool 18 · Arsenal 10 · Everton 9           → Football League (1ª antigua)
#   15 Juventus 9 · Roma 7 · Fiorentina 5              → Copa de Italia
#   16 Milan 4 · Juventus 2 · Lazio 2                  → Supercopa de Italia
#   17 Independiente 7 · Estudiantes 3 · Boca 2        → Copa Libertadores
#   18 Rosario Central 1 · Lanús 1 · Talleres 1        → Copa CONMEBOL
#   19 Independiente 2 · Estudiantes 1 · Vélez 1       → Copa Interamericana
#   20 siete clubes con 10 participaciones y 1 título  → Supercopa Sudamericana
#      (las 10 ediciones exactas, y solo invitaba a ex campeones de la Libertadores)
#
# El 5 (Intercontinental) es COMPARTIDO entre continentes, no hay uno por país: Independiente
# 7/2, Milan 6/3, Madrid 4/2, Boca 2/1. Los títulos de LIGA no están aquí — viven en el
# historial (`campeon`, `temporadas1a`).
COMPETICIONES = {
    0: "Copa de la UEFA / Ferias", 1: "Copa del Rey", 2: "Copa de Europa",
    3: "Recopa de Europa", 4: "Supercopa de España", 5: "Copa Intercontinental",
    6: "Supercopa de Europa", 7: "F.A. Cup", 8: "Copa de la Liga inglesa",
    9: "Charity Shield", 10: "Premier League", 11: "Football League (1ª antigua)",
    12: "2ª división inglesa", 13: "3ª división inglesa", 14: "4ª división inglesa",
    15: "Copa de Italia", 16: "Supercopa de Italia", 17: "Copa Libertadores",
    18: "Copa CONMEBOL", 19: "Copa Interamericana", 20: "Supercopa Sudamericana",
}


def team_palmares(t: "Team") -> list:
    """Palmarés de copas del club: [{id, name, played, won}] en el orden del fichero."""
    return [{"id": cid, "name": COMPETICIONES.get(cid, f"Competición {cid}"),
             "played": part, "won": tit}
            for cid, part, tit in (getattr(t, "competiciones", None) or [])]


def set_palmares(t: "Team", cid: int, played: int, won: int) -> bool:
    """Pone participaciones y títulos de una competición. La añade si no estaba y la QUITA si
    las dos cifras quedan a cero (que es como lo trae el juego: un club sin palmarés no lleva
    la entrada).

    OJO: los títulos **pueden** superar a las participaciones y no es un error. En PCF2000 hay
    257 fichas así, y la razón se ve al mirarlas: al Athletic le pone 0 participaciones y 23
    Copas del Rey, y al Zaragoza 1 y 4. En la Copa del Rey juegan todos los años todos, así que
    Dinamic no llevaba la cuenta de participaciones — solo la de títulos. Si aquí se recortara
    el título al número de participaciones (que fue el primer impulso), tocar la casilla del
    Athletic le borraría 23 Copas."""
    if not 0 <= cid <= 0xFF:
        return False
    played = max(0, min(0xFF, played))
    won = max(0, min(0xFF, won))
    lista = [list(x) for x in (getattr(t, "competiciones", None) or [])]
    i = next((k for k, x in enumerate(lista) if x[0] == cid), None)
    if played == 0 and won == 0:
        if i is None:
            return True
        lista.pop(i)
    elif i is None:
        lista.append([cid, played, won])
        lista.sort(key=lambda x: x[0])
    else:
        lista[i][1], lista[i][2] = played, won
    t.competiciones = [tuple(x) for x in lista]
    return True


def set_palmares_field(t: "Team", field: str, value: int) -> bool:
    """`copa_<id>_part` / `copa_<id>_tit`, para editar una cifra suelta desde la ficha."""
    if not field.startswith("copa_"):
        return False
    try:
        _, sid, que = field.split("_", 2)
        cid = int(sid)
    except ValueError:
        return False
    if que not in ("part", "tit"):
        return False
    actual = next((x for x in (getattr(t, "competiciones", None) or []) if x[0] == cid),
                  (cid, 0, 0))
    part, tit = (value, actual[2]) if que == "part" else (actual[1], value)
    return set_palmares(t, cid, part, tit)


def team_tactic(t: "Team") -> dict:
    """Táctica de equipo (7 B): toque%, contragolpe%, ataque, entradas, marcaje,
    despejes, presión."""
    if len(t.tactica_equipo) < 7:
        return {}
    return dict(zip(TACTIC_FIELDS, t.tactica_equipo[:7]))


def set_tactic_field(t: "Team", field: str, value: int) -> bool:
    if field not in TACTIC_FIELDS:
        return False
    b = bytearray(t.tactica_equipo)
    while len(b) < 7:
        b.append(0)
    b[TACTIC_FIELDS.index(field)] = value & 0xFF
    t.tactica_equipo = bytes(b)
    return True


# ---- TÁCTICA DIBUJADA (1760 B) = 11 jugadores × 40 zonas × (x u16, y u16) ----
# offset(j,z) = (j*40 + z)*4 ; j 0..10 (0 = portero) ; z 0..39.
# Coordenadas confirmadas:
#   x = avance (0 portería propia … ~417 rival) ; y = banda (0 izq … ~244 der).
#
# z = situación_del_balón*2 + estado, con estado 0 = CON posesión y 1 = sin ella (con el balón
# el equipo está 86 unidades más adelantado, y se cumple en las 898 tácticas de la base).
#
# Y las 20 SITUACIONES son **4 carriles × (4, 6, 6, 4) pasos de profundidad** — ver
# `ZONAS_POR_CARRIL`. Aquí decía antes «5 filas × 4 columnas», y los datos lo desmienten: esa
# lectura exige que la x crezca por tramos de 4 y no lo hace en NINGUNO de los 898 equipos,
# mientras que la de carriles se cumple en 896. Lo que la remata es la simetría del campo: los
# carriles 0 y 3 (exteriores, 4 pasos) dan cifras casi idénticas entre sí, y los 1 y 2
# (interiores, 6 pasos) también. En PCF2001 el orden de carriles sale en 1.451 de 1.451.
TACTIC_PLAYERS = 11
TACTIC_ZONES = 40
TACTIC_XMAX = 470          # avance máx observado en datos reales (portería rival)
TACTIC_YMAX = 290          # banda máx observada (banda derecha)
ZONAS_POR_CARRIL = (4, 6, 6, 4)     # el balón se divide más fino por el centro que por fuera


def zona_de(carril: int, paso: int, con_balon: bool = True) -> int:
    """Índice `z` (0..39) de una zona de la pizarra: carril 0..3 (izq→der), `paso` = avance del
    balón dentro de ese carril (0..3 en los exteriores, 0..5 en los interiores)."""
    if not 0 <= carril < len(ZONAS_POR_CARRIL):
        raise ValueError("carril fuera de rango (0-3)")
    if not 0 <= paso < ZONAS_POR_CARRIL[carril]:
        raise ValueError(f"el carril {carril} tiene {ZONAS_POR_CARRIL[carril]} pasos")
    return (sum(ZONAS_POR_CARRIL[:carril]) + paso) * 2 + (0 if con_balon else 1)


def carril_y_paso(z: int) -> tuple[int, int, bool]:
    """Lo contrario de `zona_de`: (carril, paso, con_balón) de un índice 0..39."""
    if not 0 <= z < TACTIC_ZONES:
        raise ValueError("zona fuera de rango (0-39)")
    situacion, estado = divmod(z, 2)
    for carril, n in enumerate(ZONAS_POR_CARRIL):
        if situacion < n:
            return carril, situacion, estado == 0
        situacion -= n
    raise ValueError("zona fuera de rango (0-39)")


# El bit bajo de `z` es el ESTADO: tener el balón (0) o no tenerlo (1). Con el balón el equipo
# está ~86 unidades más adelantado en 898 de 898 tácticas, así que «con balón» es la posición de
# ATAQUE y «sin balón» la de REPLIEGUE. El campo de la ficha enseña tres disposiciones y cada
# una mueve lo suyo: `nat` las 40 (el jugador entero = formación), `def` las 20 sin balón, `atk`
# las 20 con balón. Así «mover solo defensa» o «solo ataque» tiene sentido (foro).
ZONAS_CON = tuple(range(0, TACTIC_ZONES, 2))    # con posesión (ataque)
ZONAS_SIN = tuple(range(1, TACTIC_ZONES, 2))    # sin posesión (repliegue)
_ZONAS_TODAS = tuple(range(TACTIC_ZONES))


def zonas_de(which: str = "nat") -> tuple[int, ...]:
    """Las zonas que toca cada disposición del campo: `def` = sin balón, `atk` = con balón,
    `nat` = las 40 (el jugador entero). Cualquier otro valor cae en `nat`."""
    return ZONAS_SIN if which == "def" else ZONAS_CON if which == "atk" else _ZONAS_TODAS


def _media_zonas(blob: bytes, j: int, zonas) -> tuple[float, float]:
    """Centro (x, y) del jugador j promediando SOLO las zonas indicadas."""
    sx = sy = 0
    for z in zonas:
        o = (j * TACTIC_ZONES + z) * 4
        sx += int.from_bytes(blob[o:o + 2], "little")
        sy += int.from_bytes(blob[o + 2:o + 4], "little")
    n = len(zonas)
    return sx / n, sy / n


def tactic_positions(t: "Team") -> list[list[dict]]:
    """Devuelve [jugador 0..10][zona 0..39] = {"x", "y"}. Jugador 0 = portero."""
    blob = t.tactica
    if len(blob) < 1760:
        blob = blob + b"\x00" * (1760 - len(blob))
    out = []
    for j in range(TACTIC_PLAYERS):
        zs = []
        for z in range(TACTIC_ZONES):
            o = (j * TACTIC_ZONES + z) * 4
            zs.append({"x": int.from_bytes(blob[o:o + 2], "little"),
                       "y": int.from_bytes(blob[o + 2:o + 4], "little")})
        out.append(zs)
    return out


def set_tactic_position(t: "Team", j: int, z: int, x: int, y: int) -> bool:
    """Fija (x,y) del jugador j (0..10) en la zona z (0..39). Round-trip byte-perfecto."""
    if not (0 <= j < TACTIC_PLAYERS and 0 <= z < TACTIC_ZONES):
        return False
    b = bytearray(t.tactica)
    while len(b) < 1760:
        b.append(0)
    o = (j * TACTIC_ZONES + z) * 4
    b[o:o + 2] = max(0, min(0xFFFF, int(x))).to_bytes(2, "little")
    b[o + 2:o + 4] = max(0, min(0xFFFF, int(y))).to_bytes(2, "little")
    t.tactica = bytes(b)
    return True


_FDI_PRESETS: dict[str, list] = {}

# Cada edición trae LAS SUYAS y no se mezclan. Las de PCF7 son sus `Tactics/predef.001..010`;
# las de 2000/2001 no se incluyen en este repositorio: si existe
# `refdata/pcf2000_fdi_tactics.json` se usa, y si no la lista sale vacía.
_FICHERO_PRESETS = {"pcf7": "pcf_fdi_tactics.json", "pcf2000": "pcf2000_fdi_tactics.json"}


def fdi_tactic_presets(variante: str = "pcf7") -> list:
    """Las tácticas PREDEFINIDAS de esa edición, bundleadas en refdata (no dependen de
    gamedata). Cada una = {"name", "hex"(1760B)}. `variante` ∈ {"pcf7", "pcf2000"}."""
    clave = "pcf2000" if str(variante).startswith(("pcf2000", "pcf2001", "2000", "2001")) else "pcf7"
    if clave not in _FDI_PRESETS:
        import json
        import pathlib
        p = pathlib.Path(__file__).parent.parent / "refdata" / _FICHERO_PRESETS[clave]
        try:
            _FDI_PRESETS[clave] = json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            _FDI_PRESETS[clave] = []
    return _FDI_PRESETS[clave]


def apply_tactic_preset(t: "Team", idx: int, variante: str = "pcf7") -> bool:
    """Aplica la táctica predefinida `idx`: copia su blob de 1760 B a t.tactica."""
    presets = fdi_tactic_presets(variante)
    if not (0 <= idx < len(presets)):
        return False
    blob = bytes.fromhex(presets[idx]["hex"])
    if len(blob) != 1760:
        return False
    t.tactica = blob
    return True


def tactic_base(t: "Team") -> list[dict]:
    """Posición 'de casa' (formación) de cada jugador = MEDIA de sus 40 zonas. Es lo
    que se dibuja como formación estática. [{"x","y"}] × 11 (jugador 0 = portero)."""
    blob = t.tactica
    if len(blob) < 1760:
        blob = blob + b"\x00" * (1760 - len(blob))
    out = []
    for j in range(TACTIC_PLAYERS):
        cx, cy = _media_zonas(blob, j, _ZONAS_TODAS)
        out.append({"x": round(cx), "y": round(cy)})
    return out


# Dimensiones del terreno en unidades de táctica FDI, deducidas de los datos (2026-08-16):
# el barrido de las 898 tácticas de PCF7 da x∈[7,417] e y∈[8,244], con la y centrada en
# ~126 (los porteros están ahí). 420×252 = ratio 1,667, la proporción de un campo real.
PITCH_W = 420.0
PITCH_H = 252.0
# PCF2001 usa un terreno MAYOR con la misma proporción (medido: x hasta 469, y hasta 288).
PITCH_2001 = (480.0, 288.0)


def field_dims(variante: str = "pcf7") -> tuple[float, float]:
    """Terreno de la familia FDI en unidades de táctica (avance × banda), para normalizar el
    dibujo. PCF7 y PCF2000 comparten 420×252; PCF2001 usa 480×288 (misma proporción).

    Es la MISMA escala que usa el campo al PINTAR y la que hay que usar al ARRASTRAR: si no
    coinciden, la ficha se coloca donde no la sueltas (el descuadre que reportó el foro)."""
    return PITCH_2001 if str(variante).startswith(("pcf2001", "2001")) else (PITCH_W, PITCH_H)


def tactic_shape(t: "Team", x_max: float = PITCH_W,
                 y_max: float = PITCH_H) -> list[dict]:
    """Las 11 posiciones de la táctica, NORMALIZADAS a 0..1 y en tres situaciones.

    A diferencia de v5/6 (que guarda dos posiciones fijas), en FDI cada jugador tiene
    40 zonas = dónde se coloca según dónde esté el balón. `nx/ny` = posición natural (media
    de las 40), `dx/dy` = repliegue (media de las 20 SIN balón), `ax/ay` = ataque (media de
    las 20 CON balón) — que es lo que mueve cada disposición al arrastrar (`zonas_de`)."""
    blob = t.tactica or b""
    if len(blob) < TACTIC_PLAYERS * TACTIC_ZONES * 4:
        return []

    out = []
    for j in range(TACTIC_PLAYERS):
        todas = _media_zonas(blob, j, _ZONAS_TODAS)
        d = _media_zonas(blob, j, ZONAS_SIN)
        a = _media_zonas(blob, j, ZONAS_CON)
        out.append({
            "n": j + 1,
            "nx": round(todas[0] / x_max, 4), "ny": round(todas[1] / y_max, 4),
            "dx": round(d[0] / x_max, 4), "dy": round(d[1] / y_max, 4),
            "ax": round(a[0] / x_max, 4), "ay": round(a[1] / y_max, 4),
        })
    return out


def shift_tactic_player(t: "Team", j: int, x: int, y: int, which: str = "nat") -> bool:
    """Mueve al jugador j (0..10) a (x,y) en el campo. `which` decide QUÉ se mueve, igual que
    las disposiciones de la ficha: `nat` = las 40 zonas (el jugador entero), `def` = solo las
    20 sin balón (repliegue), `atk` = solo las 20 con balón (ataque). El delta se aplica a las
    zonas elegidas respecto a SU propia media, así la ficha queda donde se suelta (y las otras
    dos vistas no se mueven). Round-trip byte-perfecto."""
    if not (0 <= j < TACTIC_PLAYERS):
        return False
    zonas = zonas_de(which)
    blob = t.tactica
    if len(blob) < 1760:
        blob = blob + b"\x00" * (1760 - len(blob))
    cx, cy = _media_zonas(blob, j, zonas)
    dx, dy = int(x) - round(cx), int(y) - round(cy)
    if dx == 0 and dy == 0:
        return True
    b = bytearray(blob)
    for z in zonas:
        o = (j * TACTIC_ZONES + z) * 4
        nx = max(0, min(0xFFFF, int.from_bytes(b[o:o + 2], "little") + dx))
        ny = max(0, min(0xFFFF, int.from_bytes(b[o + 2:o + 4], "little") + dy))
        b[o:o + 2] = nx.to_bytes(2, "little")
        b[o + 2:o + 4] = ny.to_bytes(2, "little")
    t.tactica = bytes(b)
    return True


# ------------------------------------------------------------------ parse jugador
def _parse_player(d: bytes, ini: int, largo: int, code: int) -> Player:
    r = _R(d, ini)
    r.u16()                                     # sumaLargos (derivado; se recomputa)
    version = r.u16()
    tipo = r.u8()
    id_foto = r.u16()
    dorsal = r.u8()
    apodo = r.st()
    nombre = r.st()
    slot = r.u8()
    estado = r.u8()
    roles = r.raw(6)
    nac = r.u8(); piel = r.u8(); pelo = r.u8(); dem = r.u8()
    dia = r.u8(); mes = r.u8(); anyo = r.u16()
    altura = r.u8(); peso = r.u8()
    p = Player(code=code, tipo=tipo, id_foto=id_foto, dorsal=dorsal, apodo=apodo,
               nombre=nombre, slot=slot, estado=estado, roles=roles, nacionalidad=nac,
               piel=piel, pelo=pelo, demarcacion=dem, dia=dia, mes=mes, anyo=anyo,
               altura=altura, peso=peso, version=version)
    if tipo == 0:
        p.pais_natal = r.u8()
        p.ciudad = r.st()
        p.procedencia = r.st()
        p.internacional = r.st()
        fin = ini + largo - 16
        while r.p < fin:
            p.bbdd.append(r.st())
    p.medias = r.raw(16)
    if r.p != ini + largo:
        raise ValueError(f"jugador {code}: {r.p - ini} != {largo}")
    return p


def _ser_player(p: Player) -> bytes:
    if p.opaque and p.raw:
        return p.raw          # registro no reconocido: se re-emite tal cual
    w = _W()
    if p.tipo == 0:
        w.u16(_sumalargos(p.apodo, p.nombre, p.ciudad, p.procedencia, p.internacional))
    else:
        w.u16(_sumalargos(p.apodo, p.nombre))
    w.u16(p.version)
    w.u8(p.tipo)
    w.u16(p.id_foto)
    w.u8(p.dorsal)
    w.st(p.apodo); w.st(p.nombre)
    w.u8(p.slot); w.u8(p.estado)
    w.raw(p.roles)
    w.u8(p.nacionalidad); w.u8(p.piel); w.u8(p.pelo); w.u8(p.demarcacion)
    w.u8(p.dia); w.u8(p.mes); w.u16(p.anyo)
    w.u8(p.altura); w.u8(p.peso)
    if p.tipo == 0:
        w.u8(p.pais_natal)
        w.st(p.ciudad); w.st(p.procedencia); w.st(p.internacional)
        for t in p.bbdd:
            w.st(t)
    w.raw(p.medias)
    return bytes(w.b)


# ------------------------------------------------------------------ parse equipo
def _parse_team(d: bytes, ini: int, largo: int, code: int) -> Team:
    r = _R(d, ini)
    firma = r.raw(36)
    r.u16()                                     # sumaLargos (derivado)
    version = r.u16()
    pad = r.u8()
    tipo = r.u8()
    corto = r.st()
    estadio = r.st()
    pais = r.u8()
    latitud = struct.unpack("<b", bytes([r.u8()]))[0]
    nombre = r.st()
    sentados = r.u32(); de_pie = r.u32()
    ancho = r.u16(); largo_c = r.u16(); fundacion = r.u16()
    t = Team(code=code, firma=firma, tipo=tipo, pad=pad, nombre_corto=corto,
             estadio=estadio, pais=pais, latitud=latitud, nombre=nombre,
             sentados=sentados, de_pie=de_pie, ancho_campo=ancho,
             largo_campo=largo_c, fundacion=fundacion, version=version)
    if tipo == 0:
        t.anyo_estadio = r.u16()
        t.socios = r.u32()
        t.presidente = r.st()
        t.presupuesto = r.u32(); t.presupuesto_gen = r.u32()
        t.patrocinador = r.st(); t.proveedor = r.st()
        t.filial = r.u16()
        t.palmares = r.raw(82)
        n_comp = r.u8()
        t.competiciones = [(r.u8(), r.u8(), r.u8()) for _ in range(n_comp)]
    t.tactica = r.raw(1760)
    t.tactica_equipo = r.raw(7)
    n_ent = r.u8()
    t.entrenadores = [r.u32() for _ in range(n_ent)]
    n_jug = r.u8()
    t.jugadores = [(r.u8(), r.u32()) for _ in range(n_jug)]
    if r.p != ini + largo:
        raise ValueError(f"equipo {code}: {r.p - ini} != {largo}")
    return t


def _ser_team(t: Team) -> bytes:
    if t.opaque and t.raw:
        return t.raw          # registro no reconocido: se re-emite tal cual
    w = _W()
    w.raw(t.firma)
    if t.tipo == 0:
        w.u16(_sumalargos(t.nombre_corto, t.estadio, t.nombre,
                          t.presidente, t.patrocinador, t.proveedor))
    else:
        w.u16(_sumalargos(t.nombre_corto, t.estadio, t.nombre))
    w.u16(t.version)
    w.u8(t.pad); w.u8(t.tipo)
    w.st(t.nombre_corto); w.st(t.estadio)
    w.u8(t.pais)
    w.raw(struct.pack("<b", t.latitud))
    w.st(t.nombre)
    w.u32(t.sentados); w.u32(t.de_pie)
    w.u16(t.ancho_campo); w.u16(t.largo_campo); w.u16(t.fundacion)
    if t.tipo == 0:
        w.u16(t.anyo_estadio); w.u32(t.socios)
        w.st(t.presidente)
        w.u32(t.presupuesto); w.u32(t.presupuesto_gen)
        w.st(t.patrocinador); w.st(t.proveedor)
        w.u16(t.filial)
        w.raw(t.palmares)
        w.u8(len(t.competiciones))
        for cid, part, tit in t.competiciones:
            w.u8(cid); w.u8(part); w.u8(tit)
    w.raw(t.tactica); w.raw(t.tactica_equipo)
    w.u8(len(t.entrenadores))
    for ptr in t.entrenadores:
        w.u32(ptr)
    w.u8(len(t.jugadores))
    for en_plantilla, ptr in t.jugadores:
        w.u8(en_plantilla); w.u32(ptr)
    return bytes(w.b)


# ------------------------------------------------------------------ parse entrenador
def _parse_coach(d: bytes, ini: int, largo: int, code: int) -> Coach:
    r = _R(d, ini)
    r.u16()                                     # sumaLargos (derivado)
    version = r.u16()                           # "pad" = 700
    tipo = r.u8()
    cid = r.u16()
    apodo = r.st()
    c = Coach(code=cid, tipo=tipo, apodo=apodo, version=version)
    if tipo == 0:
        c.nombre = r.st()
        c.bbdd = [r.st() for _ in range(6)]
        c.flag = r.u8()
        while r.p < ini + largo:
            c.extra.append(r.st())
    if r.p != ini + largo:
        raise ValueError(f"entrenador {code}: {r.p - ini} != {largo}")
    return c


def _ser_coach(c: Coach) -> bytes:
    if c.opaque and c.raw:
        return c.raw          # registro no reconocido: se re-emite tal cual
    w = _W()
    if c.tipo == 0:
        w.u16(_sumalargos(c.apodo, c.nombre))
    else:
        w.u16(_sumalargos(c.apodo))
    w.u16(c.version)
    w.u8(c.tipo)
    w.u16(c.code)
    w.st(c.apodo)
    if c.tipo == 0:
        w.st(c.nombre)
        for t in c.bbdd:
            w.st(t)
        w.u8(c.flag)
        for t in c.extra:
            w.st(t)
    return bytes(w.b)


# --------------------------------------------------- registros no reconocidos (mods)
# Un mod hecho a mano con otro editor puede traer algún registro que no cuadra con el
# layout documentado. Antes eso tiraba TODO el fichero (y con él el mod entero del
# usuario); ahora ese registro se guarda EN CRUDO y se re-emite byte a byte: el resto
# de la base se edita con normalidad y el equipo raro viaja intacto a la descarga.
def _hdr_names(d: bytes, ini: int, saltar) -> tuple[str, str]:
    """(nombre corto, nombre) a la brava: la cabecera casi siempre está bien — el
    desajuste aparece más adelante (táctica, plantilla). `saltar` lee lo que hay entre
    ambos nombres, que es lo único que cambia entre PCF7 y PCF2000."""
    try:
        r = _R(d, ini)
        r.raw(36); r.u16(); r.u16(); r.u8(); r.u8()
        corto = r.st()
        saltar(r)
        return corto, r.st()
    except Exception:  # noqa: BLE001
        return "", ""


def _skip_pcf7(r) -> None:
    r.st(); r.u8(); r.u8()                      # estadio (texto), país, latitud


def opaque_team(d: bytes, ini: int, largo: int, code: int, saltar=_skip_pcf7) -> Team:
    blob = d[ini:ini + largo]
    corto, nombre = _hdr_names(d, ini, saltar)
    return Team(code=code, firma=blob[:36], tipo=1, pad=0, nombre_corto=corto,
                estadio="", pais=0, latitud=0, nombre=nombre or corto or f"Equipo {code}",
                sentados=0, de_pie=0, ancho_campo=0, largo_campo=0, fundacion=0,
                raw=blob, opaque=True)


def opaque_player(d: bytes, ini: int, largo: int, code: int, cls=None):
    """Cabecera de jugador: idéntica en PCF7 y PCF2000 hasta el nombre."""
    blob = d[ini:ini + largo]
    apodo = nombre = ""
    try:
        r = _R(d, ini)
        r.u16(); r.u16(); r.u8(); r.u16(); r.u8()
        apodo = r.st(); nombre = r.st()
    except Exception:  # noqa: BLE001
        pass
    return (cls or Player)(
        code=code, tipo=1, id_foto=code, dorsal=0, apodo=apodo or f"Jugador {code}",
        nombre=nombre, slot=0, estado=0, roles=b"\x00" * 6, nacionalidad=0, piel=0,
        pelo=0, demarcacion=0, dia=1, mes=1, anyo=1970, altura=0, peso=0,
        raw=blob, opaque=True,
        # 2000/2001: pelo_tipo=3 y vello=1 son los de fábrica; con 0 el pelo sale verde
        **({"pelo_tipo": 3, "bello": 1, "nacionalizado": 0} if cls is not None else {}))


def opaque_coach(d: bytes, ini: int, largo: int, code: int) -> Coach:
    blob = d[ini:ini + largo]
    apodo = ""
    try:
        r = _R(d, ini)
        r.u16(); r.u16(); r.u8()
        apodo = r.st()
    except Exception:  # noqa: BLE001
        pass
    return Coach(code=code, tipo=1, apodo=apodo or f"Entrenador {code}",
                 raw=blob, opaque=True)


# ------------------------------------------------------------------ contenedor FDI
_KIND_PARSE = {"EQ": _parse_team, "JUG": _parse_player, "ENT": _parse_coach}
_KIND_SER = {"EQ": _ser_team, "JUG": _ser_player, "ENT": _ser_coach}
_KIND_OPAQUE = {"EQ": opaque_team, "JUG": opaque_player, "ENT": opaque_coach}


def _detect_kind(name: str) -> str:
    u = name.upper()
    if u.startswith("EQ"):
        return "EQ"
    if u.startswith("JUG"):
        return "JUG"
    if u.startswith("ENT"):
        return "ENT"
    raise ValueError(f"no sé qué FDI es: {name}")


def parse(data: bytes, kind: str) -> FdiFile:
    """Parsea un FDI. `kind` ∈ {'EQ','JUG','ENT'} (o el nombre de fichero)."""
    if kind not in _KIND_PARSE:
        kind = _detect_kind(kind)
    if data[:8] != MAGIC:
        raise ValueError("no es un FDI (falta DMFIv1.0)")
    n = struct.unpack_from("<I", data, 16)[0]
    parse_fn = _KIND_PARSE[kind]
    op_fn = _KIND_OPAQUE[kind]
    records = []
    for i in range(n):
        code, ini, largo = struct.unpack_from("<IxII", data, HEADER_LEN + i * INDEX_ENTRY)
        try:
            records.append(parse_fn(data, ini, largo, code))
        except Exception:  # noqa: BLE001 — registro raro: se conserva en crudo
            records.append(op_fn(data, ini, largo, code))
    return FdiFile(kind=kind, records=records)


def serialize(f: FdiFile) -> bytes:
    """Reconstruye el FDI: reindexa (offsets contiguos en orden de la lista)."""
    ser_fn = _KIND_SER[f.kind]
    blocks = [ser_fn(rec) for rec in f.records]
    n = len(blocks)
    out = bytearray()
    out += MAGIC
    out += b"\x00" * 8
    out += struct.pack("<I", n)
    # índice: code(u32) + pad(1) + inicio(u32) + largo(u32)
    inicio = HEADER_LEN + n * INDEX_ENTRY
    index = bytearray()
    for rec, blk in zip(f.records, blocks):
        index += struct.pack("<IxII", rec.code, inicio, len(blk))
        inicio += len(blk)
    out += index
    for blk in blocks:
        out += blk
    return bytes(out)
