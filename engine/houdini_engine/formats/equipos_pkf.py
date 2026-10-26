"""Parser/writer de EQUIPOS.PKF / EQ*.PKF (carpeta DBDat).

Modelo **patch-in-place**: se conserva el buffer original completo y cada jugador
guarda los offsets de sus campos. `serialize()` parte del buffer original y aplica
solo los cambios → **round-trip byte-perfecto por construcción** (sin cambios,
salida idéntica a la entrada).

Estructura del registro de jugador (validada contra ficheros reales v5/v6):

    puntero   u16 LE
    dorsal    u8
    nombre corto   [len u8][00][bytes cifrados XOR 0x61]
    nombre largo   [len u8][00][bytes]
    --- bloque fijo de 18 bytes ---
    posicion_alineacion u8
    procedencia         u8
    demarcaciones       6 x u8
    pais                u8
    piel                u8
    pelo                u8
    tipo                u8
    dia u8, mes u8, anyo u16 LE
    altura u8, peso u8
    --- comentarios (variable) + medias (10 x u8 en crudo, antes del siguiente jugador) ---

La enumeración es por **escaneo de la gramática** (par de cadenas + bloque de 18
bytes válido), robusta frente a la estructura del contenedor de cabecera.
"""
from __future__ import annotations

import re
import struct
from dataclasses import dataclass, field
from functools import lru_cache

from ..codec import text
from ..models import GameVersion

BLOCK_LEN = 18  # bloque fijo tras el nombre largo del jugador
# Presupuesto EN EL JUEGO (millones): máximo del juego. En la base nunca pasa de 1000 (Real
# Madrid/Barça); un valor mayor CRASHEA el juego al cargar el equipo. Se acota al editar.
# PRESUPUESTO EN EL JUEGO: SIN TOPE ARTIFICIAL (2026-08-16).
#
# Llegamos a acotarlo a 1000 porque es el máximo de la base española (Real Madrid y Barça
# están clavados ahí), pero 1000 NO es el tope del motor: el campo es u32 y el MISMO
# formato trae 1500 de fábrica en Premier y Calcio y hasta 25.000 en Apertura 97/98. Dónde
# está el techo real de cada edición lo decide su manager.exe y solo se sabe probando en el
# juego, así que ahora se deja elegir y que cada uno encuentre el suyo. La UI avisa de que
# pasando de 1000 el juego puede negarse a cargar el equipo.
BUDGET_GAME_MAX = 0xFFFFFFFF          # el ancho real del campo


def budget_game_max(game_id: str | None = None) -> int:
    return BUDGET_GAME_MAX
# delimitador de bloque de equipo (el año varía: 1996 en v5, 1996/1997 en v6)
TEAM_SIG_RE = re.compile(rb"Copyright \(c\)\d{4} Dinamic Multimedia")
TEAM_SIG_LEN = 36


@dataclass
class PlayerRecord:
    """Jugador con offsets al buffer original (edición in-place)."""
    offset: int              # offset del puntero (inicio del registro)
    pointer: int
    number: int
    short_name: str
    long_name: str
    short_off: int           # offset del byte de longitud del nombre corto
    long_off: int
    block_off: int           # offset del bloque fijo de 18 bytes
    lineup_position: int
    origin: int
    demarcations: list[int]
    country: int
    skin: int
    hair: int
    ptype: int
    birth_day: int
    birth_month: int
    birth_year: int
    height: int
    weight: int
    ratings: list[int] = field(default_factory=list)  # VE RE AG CA RG RM PA TI EN PO (orden en disco)
    ratings_off: int = 0                               # offset de las 10 medias (0 si no localizadas)


@dataclass
class TeamRecord:
    """Equipo con offsets al buffer original (edición in-place)."""
    sig_off: int             # offset de la firma "Copyright..." (inicio del bloque)
    pointer: int
    short_name: str
    stadium: str
    long_name: str
    country: int
    capacity: int            # aforo
    field_width: int         # ancho del terreno (m)
    field_length: int        # largo del terreno (m)
    founded: int             # año de fundación
    members: int             # socios
    president: str
    budget_db: int           # presupuesto base de datos
    budget_game: int         # presupuesto en el juego (millones)
    sponsor: str             # patrocinador
    supplier: str            # proveedor
    filial: int              # puntero del filial (0xFFFF = sin filial)
    filial2: int = 0xFFFF    # puntero del 2º filial
    complete: bool = True     # True = cabecera nacional completa (con datos financieros)
    foreign: bool = False     # True = liga extranjera (sin info de BBDD: solo aforo, entrenador y táctica)
    coach_short: str = ""
    coach_long: str = ""
    # Un equipo puede llevar VARIOS entrenadores: son los que pasaron por el club esa
    # temporada (el Sevilla del 97/98 trae Camacho, Antonio Álvarez, Bilardo y Julián
    # Rubio, que es lo que ocurrió). En 6.0 Oro hay 45 equipos con más de uno. Los campos
    # `coach_*` de arriba son los del PRIMERO; aquí van todos con sus offsets.
    coaches: list = field(default_factory=list)
    version: GameVersion | None = None  # versión del BLOQUE (6.0 Oro mezcla v5+v6)
    tactics: list = field(default_factory=list)   # 7 bytes: toque%, contragolpe%, ataque, entradas, marcaje, despejes, presión
    # offsets de campos fijos para edición in-place
    _off: dict = field(default_factory=dict)
    players: list = field(default_factory=list)


@dataclass
class EquiposFile:
    raw: bytearray
    version: GameVersion
    teams: list[TeamRecord] = field(default_factory=list)
    players: list[PlayerRecord] = field(default_factory=list)


def detect_version(data: bytes, filename: str = "") -> GameVersion:
    """Detecta la versión por CONTENIDO (más fiable que el nombre de fichero):
    busca un equipo nacional (liga byte 00) y prueba parsearlo como v5 y v6; la
    que encaje determina la versión. Nota: hay ficheros con nombre estilo v6
    (Eq0…) pero formato v5 (5.0 Oro, Premier/Calcio del pack Oro).
    """
    sigs = [m.start() for m in TEAM_SIG_RE.finditer(bytes(data))]
    checked = 0
    for s in sigs:
        if s + 41 >= len(data) or data[s + 41] != 0:  # solo equipos nacionales
            continue
        t5 = _parse_team(data, s, GameVersion.PCF5)
        t6 = _parse_team(data, s, GameVersion.PCF6)
        if t5 and not t6:
            return GameVersion.PCF5
        if t6 and not t5:
            return GameVersion.PCF6
        checked += 1
        if checked >= 20:
            break
    # respaldo por nombre de fichero
    name = filename.upper()
    if name.startswith("EQ0") or (name.startswith("EQ") and name != "EQUIPOS.PKF"):
        return GameVersion.PCF6
    return GameVersion.PCF5


def _read_str(data, off):
    """Lee [len][00][texto]. Devuelve (texto, len_bytes, off_siguiente) o None."""
    if off + 2 > len(data):
        return None
    n = data[off]
    if n == 0 or n > 40 or data[off + 1] != 0x00:
        return None
    body = data[off + 2:off + 2 + n]
    if len(body) < n:
        return None
    s = text.decode(body)
    for c in s:
        o = ord(c)
        if not (32 <= o < 127 or 0xA0 <= o <= 0xFF):
            return None
    return s, n, off + 2 + n


def _valid_block(data, off):
    """¿Los 18 bytes en `off` son un bloque de jugador plausible?"""
    if off + BLOCK_LEN > len(data):
        return False
    b = data[off:off + BLOCK_LEN]
    dem1 = b[2]
    country = b[8]
    skin = b[9]
    hair = b[10]
    ptype = b[11]
    year = struct.unpack_from("<H", b, 14)[0]
    month = b[13]
    return (
        1 <= dem1 <= 0x12 and 0 <= country <= 210 and 1 <= skin <= 3
        and 0 <= hair <= 6 and 0 <= ptype <= 3 and month <= 12
        and 1900 <= year <= 1995
    )


def _parse_player(data, off, lenient=False):
    """Intenta parsear un jugador cuyo puntero está en `off`. None si no encaja. `lenient` se
    salta la validación heurística del bloque fijo (`_valid_block`): en el recorrido DETERMINISTA
    del flujo ya se sabe que es un jugador, y algunos reales (p.ej. 'Dany Olsson' del Elche) tienen
    un bloque que la heurística rechaza → así el editor los muestra igual que el juego."""
    if off + 3 > len(data):
        return None
    pointer = struct.unpack_from("<H", data, off)[0]
    number = data[off + 2]
    short_off = off + 3
    r1 = _read_str(data, short_off)
    if not r1:
        return None
    short_name, _, long_off = r1
    r2 = _read_str(data, long_off)
    if not r2:
        return None
    long_name, _, block_off = r2
    if not lenient and not _valid_block(data, block_off):
        return None
    b = data[block_off:block_off + BLOCK_LEN]
    return PlayerRecord(
        offset=off, pointer=pointer, number=number,
        short_name=short_name, long_name=long_name,
        short_off=short_off, long_off=long_off, block_off=block_off,
        lineup_position=b[0], origin=b[1], demarcations=list(b[2:8]),
        country=b[8], skin=b[9], hair=b[10], ptype=b[11],
        birth_day=b[12], birth_month=b[13],
        birth_year=struct.unpack_from("<H", b, 14)[0],
        height=b[16], weight=b[17],
    )


def _parse_team(data, sig_off, version):
    """Parsea el encabezamiento de equipo tras la firma. None si no encaja.

    v5 y v6 comparten firma y primeros campos, pero v6 usa enteros de 32 bits
    (aforo/socios), un byte extra tras el país y 2 bytes extra (año del estadio).
    """
    is6 = version == GameVersion.PCF6
    o = sig_off + TEAM_SIG_LEN
    off = {}
    try:
        pointer = struct.unpack_from("<H", data, o)[0]
        off["pointer"] = o
        o += 2 + 4                      # puntero + 4 bytes reservados
        off["short"] = o
        short, _, o = _read_lp(data, o)
        off["stadium"] = o
        stadium, _, o = _read_lp(data, o)
        off["country"] = o
        country = data[o]
        o += 2 if is6 else 1            # v6: país + 1 byte extra
        off["long"] = o
        long_name, _, o = _read_lp(data, o)
        off["capacity"] = o
        if is6:
            capacity = struct.unpack_from("<I", data, o)[0]; o += 4
            off["standing"] = o
            o += 4                      # plazas de pie u32
        else:
            capacity = data[o] | data[o + 1] << 8 | data[o + 2] << 16
            o += 3 + 1                  # aforo(3) + separador(1)
            if not _dims_ok(data, o):
                if _dims_ok(data, o + 3):
                    off["standing"] = o     # plazas de pie (3 bytes, sin separador)
                    o += 3
                elif _dims_ok(data, o + 4):
                    off["standing"] = o     # plazas de pie (3 bytes + separador; Apertura)
                    o += 4
        off["width"] = o
        width = data[o]; o += 2         # ancho + 00
        off["length"] = o
        length = data[o]; o += 2        # largo + 00
        off["founded"] = o
        founded = struct.unpack_from("<H", data, o)[0]; o += 2
        if is6:
            o += 2                      # año del estadio (reservado)
        off["members"] = o
        if is6:
            members = struct.unpack_from("<I", data, o)[0]; o += 4
        else:
            members = data[o] | data[o + 1] << 8 | data[o + 2] << 16
            o += 3 + 1                  # socios(3) + separador(1)
        off["president"] = o
        president, _, o = _read_lp(data, o)
        off["budget_db"] = o
        budget_db = struct.unpack_from("<I", data, o)[0]; o += 4
        off["budget_game"] = o
        budget_game = struct.unpack_from("<I", data, o)[0]; o += 4
        off["sponsor"] = o
        sponsor, _, o = _read_lp(data, o)
        off["supplier"] = o
        supplier, _, o = _read_lp(data, o)
        # filial 1 (u16) + filial 2 (u16); off["filial"] apunta al 2º (ancla del
        # historial). En RM: filial=26 (R. Madrid B) y filial2=98 (R. Madrid C).
        filial = struct.unpack_from("<H", data, o)[0]
        o += 2
        off["filial"] = o
        filial2 = struct.unpack_from("<H", data, o)[0]
    except (IndexError, struct.error, TypeError):
        return None
    # validaciones de coherencia
    if not (0 <= country <= 210 and 1800 <= founded <= 1998 and capacity < 500000):
        return None
    return TeamRecord(
        sig_off=sig_off, pointer=pointer, short_name=short, stadium=stadium,
        long_name=long_name, country=country, capacity=capacity,
        field_width=width, field_length=length, founded=founded, members=members,
        president=president, budget_db=budget_db, budget_game=budget_game,
        sponsor=sponsor, supplier=supplier, filial=filial, filial2=filial2, _off=off,
    )


def _parse_team_foreign(data, sig_off, version):
    """Equipo de liga extranjera: sin info de BBDD (presupuesto, socios, presidente…).
    Sí tiene nombre, estadio, país, nombre largo, aforo, entrenador y táctica.
    """
    is6 = version == GameVersion.PCF6
    o = sig_off + TEAM_SIG_LEN
    off = {}
    try:
        pointer = struct.unpack_from("<H", data, o)[0]
        off["pointer"] = o
        o += 2 + 4
        off["short"] = o
        short, _, o = _read_lp(data, o)
        off["stadium"] = o
        stadium, _, o = _read_lp(data, o)
        off["country"] = o
        country = data[o]
        o += 2 if is6 else 1
        off["long"] = o
        long_name, _, o = _read_lp(data, o)
        off["capacity"] = o
        if is6:
            capacity = struct.unpack_from("<I", data, o)[0]
        else:
            capacity = data[o] | data[o + 1] << 8 | data[o + 2] << 16
    except (IndexError, struct.error, TypeError):
        return None
    if not (0 <= country <= 210 and capacity < 500000 and short
            and _printable(short) and _printable(stadium)):
        return None
    return TeamRecord(
        sig_off=sig_off, pointer=pointer, short_name=short, stadium=stadium,
        long_name=long_name, country=country, capacity=capacity, field_width=0,
        field_length=0, founded=0, members=0, president="", budget_db=0,
        budget_game=0, sponsor="", supplier="", filial=0xFFFF,
        complete=False, foreign=True, _off=off,
    )


def _printable(s):
    return all(32 <= ord(c) < 127 or 0xA0 <= ord(c) <= 0xFF for c in s)


TACTIC_FIELDS = ["toque", "contragolpe", "ataque", "entradas", "marcaje", "despejes", "presion"]


def _coach_chain_ok(raw, o, end) -> bool:
    """Valida que tras el nombre largo del míster camina la cadena DOCUMENTADA
    del manual (sec. 18): perfil, sistemas, palmarés, anécdotas, última
    temporada y trayectoria, todos [u16 len][texto]. Distingue el ancla REAL
    de falsos '02' en la zona de posiciones por jornada (Deportivo, Valencia y
    Levante anclaban en uno y editar el míster CORROMPÍA el bloque → crash del
    juego, cazado por bisección). Se exigen los 3 primeros textos
    (perfil/sistemas/palmarés): los siguientes pueden superar el tope de tamaño
    del caminante (las anécdotas de Capello miden 2.325) y romperían anclas
    REALES si se exigieran."""
    for _ in range(3):
        if o + 2 > end:
            return False
        n = struct.unpack_from("<H", raw, o)[0]
        if n == 0 or n > 2000 or o + 2 + n > end:
            return False
        o += 2 + n
    return True


def _cola_camina(raw, o, end) -> bool:
    """¿Es `o` el principio de verdad de la cola del bloque?

    La cola es lo que hay tras la táctica: uno o varios entrenadores (marca `02`) y luego los
    jugadores. Como a esta función le llega en `end` el offset del PRIMER JUGADOR, la prueba
    es exacta: saltando entrenadores desde el candidato hay que aterrizar justo ahí, ni un
    byte antes ni uno después. Un `02` casual caído dentro de un texto no lo consigue.

    Es el criterio de la gramática de PCx-Utils (`Staff.hs`: la cola es una lista de fichas
    marcadas) y sustituye al de mirar solo si detrás caminan tres textos, que se equivocaba en
    los dos sentidos: aceptaba falsos y rechazaba místeres de perfil largo. En 6.0 original, al
    Cádiz lo anclaba 775 bytes más allá, dentro de otro texto —su entrenador tiene un perfil de
    4.368 bytes y el filtro cortaba en 2.000—, y al escribirle ahí el nombre nuevo su DBC
    quedaba ilegible a partir de ese punto. El DBC es justo lo que el juego lee al crear liga.
    """
    from . import block as _B
    # OJO: `end` es el primer jugador SIN su marca (el `01` ya consumido), así que el punto al
    # que hay que aterrizar es el byte anterior.
    objetivo = end - 1 if end >= 1 and raw[end - 1] == 0x01 else end
    try:
        for _ in range(8):                       # un club puede traer varios entrenadores
            if o == objetivo:
                return True
            if o > objetivo or raw[o] != 0x02:
                return False
            o = _B._skip_coach(raw, o, False)
    except Exception:  # noqa: BLE001  (cualquier descuadre es un «no»)
        return False
    return o == objetivo


def _locate_coach(raw, team, end):
    """Localiza entrenador (marcador 02 + puntero + nombres) y la táctica de equipo
    (7 bytes previos al 02), entre la cabecera y el primer jugador. El candidato
    solo se acepta si la cadena de textos posterior camina completa (manual
    sec. 18) — sin eso, un 02 casual del historial se disfrazaba de míster."""
    start = team._off.get("filial") or team._off.get("capacity") or team._off.get("long", 0)
    _reserva: list = [None]
    for o in range(start, end):
        if raw[o] != 0x02:
            continue
        try:
            p = o + 1 + 2                      # 02 + puntero
            n1 = raw[p]
            if raw[p + 1] != 0 or not (0 < n1 < COACH_SHORT_MAX + 1):
                continue
            s1 = text.decode(raw[p + 2:p + 2 + n1]); p2 = p + 2 + n1
            n2 = raw[p2]
            if raw[p2 + 1] != 0 or not (0 < n2 < COACH_LONG_MAX + 1):
                continue
            s2 = text.decode(raw[p2 + 2:p2 + 2 + n2])
        except IndexError:
            continue
        if not (_printable(s1) and _printable(s2) and any(c.isalpha() for c in s1)):
            continue
        # DOS CRITERIOS, en este orden. El bueno es recorrer la cola ENTERA: si desde aquí el
        # bloque se lee ficha a ficha hasta el final, este es el míster y no hay más que
        # hablar. El viejo —que tras el nombre largo caminen tres textos de menos de 2.000
        # bytes— se queda de RESERVA para cuando ninguno cuadre, porque además se le escapan
        # los místeres de perfil largo: el del Cádiz en 6.0 original mide 4.368 bytes, así que
        # lo descartaba y se enganchaba a un `02` casual 775 bytes más allá, dentro de otro
        # texto. Escribirle ahí el entrenador nuevo dejaba su DBC ilegible.
        if _cola_camina(raw, o, end):
            pass
        elif _coach_chain_ok(raw, p2 + 2 + n2, end):
            if _reserva[0] is None:
                _reserva[0] = (o, p, n1, s1, p2, n2, s2)
            continue
        else:
            continue
        team._off["coach_ptr"] = o + 1
        team._off["coach_short"] = o + 3
        team._off["coach_long"] = p2
        team._off["tactics"] = o - 7
        team.coach_short = s1
        team.coach_long = s2
        team.tactics = list(raw[o - 7:o])
        _locate_coach_texts(raw, team, end)
        _locate_all_coaches(raw, team, end)
        return
    if _reserva[0] is None:
        return
    o, _p, _n1, s1, p2, _n2, s2 = _reserva[0]      # ninguno caminaba: el de siempre
    team._off["coach_ptr"] = o + 1
    team._off["coach_short"] = o + 3
    team._off["coach_long"] = p2
    team._off["tactics"] = o - 7
    team.coach_short = s1
    team.coach_long = s2
    team.tactics = list(raw[o - 7:o])
    _locate_coach_texts(raw, team, end)
    _locate_all_coaches(raw, team, end)


# textos del entrenador tras su nombre largo (manual sec. 18.1), en orden
COACH_TEXT_FIELDS = ["coach_perfil", "coach_sistemas", "coach_palmares",
                     "coach_anecdotas", "coach_ultima", "coach_trayectoria"]


def _coach_text_offsets(raw, long_off, end) -> dict:
    """Offsets de las cadenas de BBDD del entrenador tras su nombre largo:
    perfil, sistemas, palmarés, anécdotas, última temporada, trayectoria,
    [03 + trayectoria como jugador], declaraciones. Longitudes u16 LE.
    Defensivo: si algo no encaja, devuelve lo localizado hasta ahí."""
    out: dict = {}
    o = long_off
    o += 2 + struct.unpack_from("<H", raw, o)[0]  # saltar nombre largo
    for key in COACH_TEXT_FIELDS:
        if o + 2 > end:
            return out
        n = struct.unpack_from("<H", raw, o)[0]
        # los textos VACÍOS (n == 0) son normales y hay que seguir contándolos: antes se
        # cortaba aquí y a esos entrenadores les faltaban los textos siguientes. La regla
        # buena es la de `block._skip_coach`, que es como lee el juego.
        # sin tope artificial de longitud: el entrenador ya está validado por el anclaje,
        # y hay textos de más de 2.000 bytes (las anécdotas de Capello miden 2.325). El
        # único límite real es el fin del bloque.
        if o + 2 + n > end:
            return out
        out[key] = o
        o += 2 + n
    # separador antes de "trayectoria como jugador": se consume SIEMPRE (vale 0x03 cuando
    # el entrenador fue jugador; si no, es otro byte y también ocupa su sitio)
    if o >= end:
        return out
    hubo_jugador = raw[o] == 0x03
    o += 1
    if hubo_jugador and o + 2 <= end:
        n = struct.unpack_from("<H", raw, o)[0]
        if o + 2 + n <= end:
            out["coach_tray_jugador"] = o
            o += 2 + n
    if o + 2 <= end:
        n = struct.unpack_from("<H", raw, o)[0]
        if o + 2 + n <= end:
            out["coach_declaraciones"] = o
    return out


def _locate_coach_texts(raw, team, end):
    team._off.update(_coach_text_offsets(raw, team._off["coach_long"], end))


def _read_coach_at(raw, o, end):
    """Lee el registro de entrenador que empieza en `o` (marca 0x02). Devuelve un dict con
    sus offsets y textos, o None si ahí no hay un entrenador válido.

    Mismas comprobaciones que `_locate_coach`; se usa para recorrer los que van DESPUÉS del
    primero (un equipo puede traer varios: los que pasaron por el club esa temporada)."""
    if o >= end or raw[o] != 0x02:
        return None
    try:
        p = o + 3                                   # 02 + puntero u16
        n1 = raw[p]
        if raw[p + 1] != 0 or not (0 < n1 < COACH_SHORT_MAX + 1):
            return None
        s1 = text.decode(raw[p + 2:p + 2 + n1])
        p2 = p + 2 + n1
        n2 = raw[p2]
        if raw[p2 + 1] != 0 or not (0 < n2 < COACH_LONG_MAX + 1):
            return None
        s2 = text.decode(raw[p2 + 2:p2 + 2 + n2])
    except IndexError:
        return None
    if not (_printable(s1) and _printable(s2) and any(c.isalpha() for c in s1)):
        return None
    return {"mark": o, "ptr_off": o + 1,
            "pointer": struct.unpack_from("<H", raw, o + 1)[0],
            "short_off": o + 3, "long_off": p2,
            "short_name": s1, "long_name": s2,
            "texts": _coach_text_offsets(raw, p2, end)}


def team_coaches(pf: EquiposFile, team: TeamRecord) -> list:
    """Todos los entrenadores del bloque, en orden. El primero es el que ya exponíamos."""
    return list(getattr(team, "coaches", None) or [])


def _locate_all_coaches(raw, team, end):
    """Recorre la cola del equipo (0x02 entrenador / 0x01 jugador) y guarda TODOS los
    entrenadores en `team.coaches`. El primero es el que ya localizaba `_locate_coach`."""
    from . import block as _B
    inicio = team._off.get("coach_ptr")
    if inicio is None:
        return
    o, out = inicio - 1, []
    try:
        while o < end and raw[o] in (0x01, 0x02):
            if raw[o] == 0x02:
                c = _read_coach_at(raw, o, end)
                if c is not None:
                    out.append(c)
                o = _B._skip_coach(raw, o, False)
                continue
            _fp, o = _B.parse_player(raw, o, False)
    except Exception:  # noqa: BLE001  (bloque raro: nos quedamos con lo recorrido)
        pass
    team.coaches = out


def _looks_name(s):
    return (len(s) >= 3 and any(c.isalpha() for c in s)
            and all(c.isalpha() or c in " .'-áéíóúñÁÉÍÓÚÑüÜçÇ" for c in s))


def _locate_coach_foreign(raw, team, end):
    """En equipos foráneos el entrenador es la última cadena de nombre (una sola)
    justo antes del primer jugador."""
    start = team._off.get("capacity", team._off.get("long", 0))
    best = None
    i = start
    while i < end - 2:
        n = raw[i]
        if 0 < n < 30 and raw[i + 1] == 0 and i + 2 + n <= end:
            s = text.decode(raw[i + 2:i + 2 + n])
            if _looks_name(s):
                best = (i, s)
                i += 2 + n
                continue
        i += 1
    if best:
        team._off["coach_short"] = best[0]
        team.coach_short = best[1]


def _dims_ok(data, o):
    """¿En `o` hay ancho(1)00 largo(1)00 año(u16) plausibles?"""
    try:
        width, length = data[o], data[o + 2]
        year = struct.unpack_from("<H", data, o + 4)[0]
        return 30 <= width <= 90 and 80 <= length <= 130 and 1800 <= year <= 1998
    except (IndexError, struct.error):
        return False


def _read_lp(data, off):
    """Lee [len][00][texto] sin validar imprimibilidad. (texto, len, off_sig)."""
    n = data[off]
    if data[off + 1] != 0x00:
        raise TypeError("no es cadena len-prefijada")
    body = data[off + 2:off + 2 + n]
    return text.decode(body), n, off + 2 + n


def is_foreign_block(data, sig_off, version) -> bool:
    """Clasificador nacional/foráneo. El byte de liga en sig+41 (0=nacional) es
    fiable en los juegos españoles, pero en PC Apertura los clubes argentinos
    llevan 1 pese a tener cabecera COMPLETA. Con byte=1 se intenta el parseo
    completo con validaciones estrictas: si encaja de verdad, es nacional."""
    if sig_off + 41 >= len(data) or data[sig_off + 41] == 0:
        return False
    t = _parse_team(data, sig_off, version)
    if t is None:
        return True
    if not (_printable(t.president) and _printable(t.sponsor)
            and _printable(t.supplier) and t.president.strip()):
        return True
    if not (30 <= t.field_width <= 90 and 80 <= t.field_length <= 130):
        return True
    if t.members > 2_000_000 or t.budget_game > 1_000_000:
        return True
    return False


def parse(data: bytes, filename: str = "") -> EquiposFile:
    raw = bytearray(data)
    version = detect_version(data, filename)

    # 1) equipos por la firma "Copyright..." — cada bloque se parsea con SU
    # versión: 6.0 Oro mezcla en un mismo PKF la temporada 96/97 (layout v5)
    # y la 97/98 (layout v6), así que si un bloque no encaja con la versión
    # global se reintenta con la otra y el equipo recuerda la suya.
    alt = GameVersion.PCF6 if version == GameVersion.PCF5 else GameVersion.PCF5
    # cotas anti-OOM: un EQUIPOS.PKF real tiene ~1.400 equipos y ~15.000 jugadores;
    # un fichero trucado podría generar millones de registros (~1 KB c/u) → varios GB.
    _MAX_TEAMS, _MAX_PLAYERS = 6000, 150000
    teams: list[TeamRecord] = []
    sig_offsets = [m.start() for m in TEAM_SIG_RE.finditer(bytes(raw))]
    for s in sig_offsets:
        if len(teams) >= _MAX_TEAMS:
            raise ValueError("demasiados equipos: fichero corrupto o no es un EQUIPOS.PKF")
        # la VERSIÓN DE FICHERO del bloque (sig+38) manda cuando es inequívoca:
        # 0x20D = layout v6; 0x1F4/0x203 = layout v5. Los foráneos (0x19F) no
        # distinguen, ahí se prueba la global y después la alternativa.
        fver = struct.unpack_from("<H", raw, s + 38)[0] if s + 40 <= len(raw) else 0
        if fver == 0x20D:
            order = (GameVersion.PCF6,)
        elif fver in (0x1F4, 0x203):
            order = (GameVersion.PCF5,)
        else:
            order = (version, alt)
        t = None
        for ver in order:
            if is_foreign_block(raw, s, ver):
                t = _parse_team_foreign(raw, s, ver)
            else:
                t = _parse_team(raw, s, ver) or _parse_team_foreign(raw, s, ver)
            if t is not None:
                t.version = ver
                break
        if t is not None:
            teams.append(t)

    # 2) jugadores por gramática. Pre-filtro BARATO: un jugador en `i` exige que
    # su nombre corto empiece en i+3 (_read_str: longitud 1..40 y byte alto 0),
    # así que se salta el ~90% de offsets sin entrar en _parse_player. Es
    # equivalente exacto: esos offsets devolverían None igualmente.
    players: list[PlayerRecord] = []
    i, n = 0, len(raw)
    while i < n - 24:
        if raw[i + 4] != 0 or not (1 <= raw[i + 3] <= 40):
            i += 1
            continue
        p = _parse_player(raw, i)
        if p is not None:
            players.append(p)
            if len(players) > _MAX_PLAYERS:
                raise ValueError("demasiados jugadores: fichero corrupto o no es un EQUIPOS.PKF")
            i = p.block_off + BLOCK_LEN
        else:
            i += 1

    # 3) asignar jugadores a equipos por rango de offsets. OJO: la cola de un
    # equipo termina en la SIGUIENTE FIRMA CRUDA, aunque ese bloque no haya
    # parseado como equipo (6.0 Oro mezcla dos temporadas — set EQ96 layout v5
    # y set EQ97 layout v6 — y sin este corte el último equipo del set 96 se
    # tragaba los ~9.600 jugadores de la temporada 97/98).
    parsed_sigs = {t.sig_off for t in teams}
    next_cut: dict[int, int] = {}
    for idx, s in enumerate(sig_offsets):
        if s in parsed_sigs:
            next_cut[s] = sig_offsets[idx + 1] if idx + 1 < len(sig_offsets) else n
    bounds = [t.sig_off for t in teams] + [n]
    ti = 0
    for p in players:
        while ti + 1 < len(teams) and p.offset >= bounds[ti + 1]:
            ti += 1
        if teams and bounds[ti] <= p.offset < bounds[ti + 1] \
                and p.offset < next_cut.get(teams[ti].sig_off, n):
            teams[ti].players.append(p)

    # 3b) entrenador y táctica de equipo (equipos con cabecera completa)
    team_bounds = [t.sig_off for t in teams] + [n]
    for ti, t in enumerate(teams):
        first_pl = min((p.offset for p in t.players), default=team_bounds[ti + 1])
        if t.complete:
            _locate_coach(raw, t, first_pl)
        elif t.foreign:
            _locate_coach_foreign(raw, t, first_pl)

    # 4) medias: 10 bytes justo antes del siguiente elemento (jugador o firma de
    #    equipo) menos el byte separador (0x01). Orden en disco: VE RE AG CA RG RM PA TI EN PO.
    boundaries = sorted({p.offset for p in players} | {t.sig_off for t in teams} | {n})
    import bisect
    starts = boundaries
    for p in players:
        j = bisect.bisect_right(starts, p.block_off + BLOCK_LEN)
        if j < len(starts):
            nb = starts[j]
            med = raw[nb - 11:nb - 1]
            if len(med) == 10 and all(v <= 99 for v in med):
                p.ratings = list(med)
                p.ratings_off = nb - 11

    # 4-bis) MEDIAS DEL ÚLTIMO JUGADOR DE CADA BLOQUE. El paso anterior las saca de los 10
    #    bytes que hay justo antes del SIGUIENTE elemento, y para el último de un bloque ese
    #    siguiente elemento es la firma del equipo, no otro jugador: la cuenta no cuadra, la
    #    validación falla y la ficha se quedaba SIN medias. En la web eso salía como media 0,
    #    sin casilla de portero y con "undefined" en la ficha (foro, 30-ago-2026).
    #
    #    Solo se nota cuando el recorrido determinista del paso 5 no ha podido reemplazar al
    #    heurístico —en 6.0 Oro son 27 equipos, y en los cuatro ficheros de fábrica 57 fichas,
    #    entre ellas George Weah—. Aquí no se ADIVINA nada: se vuelve a leer ESA ficha con el
    #    parser de registro, que sabe dónde acaba cada campo, y solo se acepta si el puntero
    #    que devuelve coincide con el que ya teníamos.
    from . import block as _B
    for _t in teams:
        for _p in _t.players:
            if len(_p.ratings) >= 10 or _p.offset < 1 or raw[_p.offset - 1] != 0x01:
                continue
            try:
                _fp, _nxt = _B.parse_player(raw, _p.offset - 1, _t.foreign)
            except Exception:  # noqa: BLE001
                continue
            _med = list(_fp.medias)
            if (_fp.pointer == _p.pointer and len(_med) == 10
                    and all(v <= 99 for v in _med) and _nxt - 10 >= 0):
                _p.ratings = _med
                _p.ratings_off = _nxt - 10

    # 5) PLANTILLA DETERMINISTA para nacionales completos (como 1Simo1): reemplaza el escaneo
    #    heurístico —que puede crear un jugador FANTASMA en las declaraciones del entrenador (Getafe)
    #    o perder alguno— por el recorrido determinista del flujo → el editor muestra lo MISMO que
    #    el juego. Solo si camina limpio hasta la firma; si no, se conserva el heurístico.
    replaced_old: set = set()   # id() de los jugadores heurísticos que se reemplazan por deterministas
    new_det: list = []          # jugadores deterministas nuevos (hay que meterlos en la lista global)
    for _t in teams:
        if not _t.players:
            continue
        nacional = _t.complete and not _t.foreign
        if not (nacional or _t.foreign):
            continue
        # límite = la SIGUIENTE FIRMA cualquiera (parseada o no), igual que dbc.block_for_team
        _end = min([s for s in sig_offsets if s > _t.sig_off], default=n)
        det = (_deterministic_players(raw, _t, _end) if nacional
               else _deterministic_players_foreign(raw, _t, _end))
        if det:
            replaced_old |= {id(p) for p in _t.players}
            _t.players = det
            new_det.extend(det)
            # El entrenador se localiza CONTANDO HACIA ATRÁS desde el primer jugador, y ese
            # primer jugador acaba de cambiar: hay que rehacerlo o se queda apuntando a donde
            # empezaba la ficha fantasma.
            _first = min(p.offset for p in det)
            if nacional:
                _locate_coach(raw, _t, _first)
            else:
                _locate_coach_foreign(raw, _t, _first)
    # La lista global `players` DEBE contener los MISMOS objetos que `t.players`: el paso 5 sustituyó
    # los jugadores heurísticos de algunos equipos por objetos deterministas NUEVOS. Sin esto,
    # `team_detail`/edición fallan con KeyError al mapear `id(p)` (jugadores "huérfanos"). Se quitan
    # los heurísticos reemplazados y se añaden los deterministas; los NO asignados a equipo se conservan.
    if replaced_old:
        players = [p for p in players if id(p) not in replaced_old] + new_det

    return EquiposFile(raw=raw, version=version, teams=teams, players=players)


# etiquetas de medias según versión (v6 intercambia RG y RM)
_RATING_ORDER_V5 = ["VE", "RE", "AG", "CA", "RG", "RM", "PA", "TI", "EN", "PO"]
_RATING_ORDER_V6 = ["VE", "RE", "AG", "CA", "RM", "RG", "PA", "TI", "EN", "PO"]


def rating_labels(version: GameVersion) -> list[str]:
    return _RATING_ORDER_V6 if version == GameVersion.PCF6 else _RATING_ORDER_V5


def get_ratings(pf: EquiposFile, player: PlayerRecord) -> dict:
    """Devuelve {etiqueta: valor} con el orden correcto de la versión."""
    labels = rating_labels(pf.version)
    return {labels[i]: player.ratings[i] for i in range(len(player.ratings))}


def set_rating(pf: EquiposFile, player: PlayerRecord, label: str, value: int) -> None:
    """Edita una media por etiqueta (VE, RE, ...). Respeta el swap RG/RM de v6."""
    if not player.ratings_off:
        raise ValueError("medias no localizadas para este jugador")
    labels = rating_labels(pf.version)
    idx = labels.index(label)
    value = max(0, min(99, value))
    pf.raw[player.ratings_off + idx] = value
    player.ratings[idx] = value


# ---- historial/estadísticas del club (zona tras el filial; layout verificado
# contra las trayectorias reales de Real Madrid y Barcelona en v5 y v6) ----

STATS_FIELDS = ["pj", "pg", "pe", "gf", "gc", "puntos"]

# 14 bytes de palmarés tras las posiciones por jornada: SIETE competiciones, cada una
# (participaciones, títulos).
#
# CORREGIDO 2026-08-20. La lectura anterior tenía mal 5 de los 14: llamaba a los dos
# primeros "finales de Copa perdidas" y "Supercopa de España", dejaba el tercero como
# "(reservado)" sin identificar, y ponía la UEFA donde va la Supercopa. Se descubrió
# contrastando con la documentación de PCx-Utils y se
# CONFIRMÓ con los datos reales, que es lo que manda:
#
#   · bytes 1-2 = UEFA/Copa de Ferias. Los títulos casan EXACTO con la historia en los
#     únicos clubes que la ganaron: Valencia 2 (Ferias 62 y 63), Zaragoza 1 (64),
#     Real Madrid 2 (UEFA 85 y 86), Barça 3 (58, 60, 66); cero en Athletic, Sevilla,
#     Espanyol, Betis, Depor y Real Sociedad. 12 aciertos de 13 en tres ediciones.
#   · bytes 3-4 = Copa del Rey. El byte 4 ya lo teníamos (23 Barça, 23 Athletic, 17 Madrid,
#     9 Atlético…); el 3 son las PARTICIPACIONES —el Barça lleva 92, y entre las dos copias
#     del club que trae el fichero (una es la temporada siguiente) sube a la vez que el
#     título cuando gana la Copa del 97—. Ahí acaba el "(reservado)".
#   · bytes 9-10 = Supercopa de España. Solo la tienen 14 clubes, TODOS españoles y
#     justamente los que la han jugado (campeones de Liga y de Copa): Barça 5, Madrid 3,
#     Atlético 1, Depor 1, Real Sociedad 1. No puede ser la UEFA: Valencia, Sevilla y
#     Espanyol la jugaron y aquí llevan 0.
PALMARES_FIELDS = [
    "uefa_participaciones", "uefa_titulos",
    "copa_participaciones", "copa_titulos",
    "ce_participaciones", "ce_titulos",
    "recopa_participaciones", "recopa_titulos",
    "supercopa_esp_participaciones", "supercopa_esp_titulos",
    "intercontinental_part", "intercontinental_titulos",
    "supercopa_eur_part", "supercopa_eur_titulos",
]


def _stats_offsets(pf: EquiposFile, team: TeamRecord) -> dict | None:
    """Offsets absolutos de la zona de historial. Solo equipos nacionales completos.

    El layout depende de la VERSIÓN DE FICHERO del bloque (u16 en sig+38), no del
    juego: <0x0200 (p.ej. 0x1F4, v5 español) → ligas 10×u8 y 42 jornadas;
    >=0x0200 (0x203 Apertura, 0x20D v6) → ligas 10×pares (puesto,liga) y 46 jornadas.
    """
    f = team._off.get("filial")
    if f is None or team.foreign or not team.complete:
        return None
    verfile = struct.unpack_from("<H", pf.raw, team.sig_off + 38)[0]
    pairs = verfile >= 0x0200
    ligas = f + 3
    temporadas = ligas + (20 if pairs else 10)
    stats = temporadas + 1
    campeon = stats + 12
    jornadas = campeon + 2
    n_jorn = 46 if pairs else 42
    return {"grupo2b": f + 2, "ligas": ligas, "temporadas1a": temporadas,
            "stats": stats, "campeon": campeon, "subcampeon": campeon + 1,
            "jornadas": jornadas, "n_jornadas": n_jorn,
            "palmares": jornadas + n_jorn, "pairs": pairs}


# Longitud del bloque de PALMARÉS según la versión de fichero (u16 en sig+38), igual que
# `LeggiSquadra` de 1Simo1 (Versione 525 → 42; 505-524 → 34) + PCF5 Oro español (500/0x1F4 → 14).
# Se PRUEBAN en orden: el correcto es el único que hace caminar el flujo limpio hasta la firma.
# 48 SALIÓ del wiki (2026-08-31): al escribir un lector siguiendo solo la documentación
# publicada y lanzarlo contra las OCHO bases, Premier y Calcio no caminaban. Su palmarés mide
# **48 bytes**, un tamaño que no estaba en ninguna fuente —ni en el manual de carky ni en
# MultiEditorPCC—, y sin él 123 de los 126 equipos nacionales de Premier y 71 de los 76 de
# Calcio caían al escaneo heurístico, que es el que se inventa fichas fantasma en los bloques
# raros. Medido restando: entrenador − 183 (táctica) − inicio del palmarés.
_PALMARES_LENS = (14, 34, 42, 48)


def _walk_squad(raw, o0, end, foreign: bool = False):
    """Camina el flujo desde `o0` (entrenador 0x02 + jugadores 0x01) como 1Simo1 y devuelve la lista
    de PlayerRecord, o None si no consume LIMPIO hasta la firma (cola ≤4). Construye el registro
    in-place directamente desde el parser de block.py (EXACTAMENTE como lee el juego) — sin los
    gates heurísticos que descartaban jugadores reales de bloque/nombre raros (p.ej. Dany Olsson).

    `foreign`: en los bloques de liga extranjera la ficha no lleva país de nacimiento ni los
    textos de BBDD, y el entrenador acaba tras su nombre corto."""
    from . import block as _B
    players: list = []
    o = o0
    try:
        while o < end and raw[o] in (0x01, 0x02):
            if raw[o] == 0x02:
                o = _B._skip_coach(raw, o, foreign)
                continue
            fp, next_o = _B.parse_player(raw, o, foreign)
            poff = o + 1
            short_off = poff + 3
            long_off = short_off + 2 + len(fp.short_raw)
            block_off = long_off + 2 + len(fp.long_raw)
            b = fp.fixed
            players.append(PlayerRecord(
                offset=poff, pointer=fp.pointer, number=fp.number,
                short_name=fp.short_name, long_name=fp.long_name,
                short_off=short_off, long_off=long_off, block_off=block_off,
                lineup_position=b[0], origin=b[1], demarcations=list(b[2:8]),
                country=b[8], skin=b[9], hair=b[10], ptype=b[11],
                birth_day=b[12], birth_month=b[13],
                birth_year=b[14] | (b[15] << 8), height=b[16], weight=b[17],
                ratings=list(fp.medias), ratings_off=next_o - 10))
            o = next_o
    except Exception:  # noqa: BLE001
        return None
    if not players or end - o > 4:
        return None
    return players


def foreign_stream_start(raw, sig_off, verfile) -> int | None:
    """Offset del inicio del FLUJO (entrenador+jugadores) de un bloque FORÁNEO.

    Es la misma cuenta que hace `LeggiSquadra` de MultiEditorPCC (1Simo1): en un equipo NO
    jugable se salta todo el bloque de datos de club (socios, presidente, caja, palmarés…) y
    se va directo de la cabecera a la táctica. Vive aquí —y no en `dbc`— porque lo usan los
    dos: el parser in-place y la reconstrucción del bloque."""
    try:
        lnc = struct.unpack_from("<H", raw, sig_off + 42)[0]
        lnst = raw[sig_off + 44 + lnc]
        off = sig_off + 47 + lnc + lnst
        if verfile == 0x20D:            # 525: latitud (v6)
            off += 1
        lnl = struct.unpack_from("<H", raw, off)[0]
        off += lnl + 10
        if verfile in (0x20D, 0x1FE):   # 525/510: año del estadio
            off += 4
        off += 2                        # año de fundación
        return off + 176 + 7            # táctica dibujada (176) + táctica de equipo (7)
    except Exception:  # noqa: BLE001
        return None


def _deterministic_players_foreign(raw, team, end) -> list | None:
    """Plantilla de un bloque FORÁNEO re-derivada de forma determinista.

    El gemelo de `_deterministic_players` para los equipos de liga extranjera. Hacía falta
    porque el escaneo heurístico se inventa fichas FANTASMA en algunos de ellos: una cuyo
    "nombre corto" es en realidad el final del nombre anterior + la cabecera de la ficha
    siguiente. Se veía en la parrilla, salía como jugador duplicado y —lo grave— al renombrarla
    se escribía encima de esa cabecera y el equipo se quedaba SIN PLANTILLA (Niva Vinnitsa de
    5.0 Oro, bug del foro 28-ago-2026). None si no camina limpio → se conserva el heurístico."""
    try:
        verfile = struct.unpack_from("<H", raw, team.sig_off + 38)[0]
    except Exception:  # noqa: BLE001
        return None
    o0 = foreign_stream_start(raw, team.sig_off, verfile)
    if o0 is None or not (team.sig_off < o0 < end) or raw[o0] not in (0x01, 0x02):
        return None
    return _walk_squad(raw, o0, end, foreign=True)


def _deterministic_players(raw, team, end) -> list | None:
    """Plantilla de un bloque NACIONAL completo re-derivada de forma DETERMINISTA, como `LeggiSquadra`
    de 1Simo1 (MultiEditorPCC): calcula el inicio del flujo (tras historial + PALMARÉS + táctica
    dibujada(176) + táctica equipo(7)) y camina entrenador(es)+jugadores. El palmarés cambia de
    tamaño por versión (v5=14, v5.5=34, v6=42), así que se prueban los 3 y se usa el que camina
    limpio hasta la firma → el editor muestra lo MISMO que el juego, sin el jugador FANTASMA del
    escaneo heurístico. None si ninguno camina limpio (→ se conserva el escaneo heurístico)."""
    f = team._off.get("filial")
    if f is None:
        return None
    try:
        verfile = struct.unpack_from("<H", raw, team.sig_off + 38)[0]
        pairs = verfile >= 0x0200
        ligas = f + 3
        temporadas = ligas + (20 if pairs else 10)
        jornadas = temporadas + 1 + 12 + 2
        pstart = jornadas + (46 if pairs else 42)         # inicio del bloque de palmarés
        for plen in _PALMARES_LENS:
            o0 = pstart + plen + 176 + 7                   # palmarés + táctica dibujada + táctica equipo
            if not (team.sig_off < o0 < end) or raw[o0] not in (0x01, 0x02):
                continue
            res = _walk_squad(raw, o0, end)
            if res is not None:
                return res
        return None
    except Exception:  # noqa: BLE001
        return None


def team_extra(pf: EquiposFile, team: TeamRecord) -> dict:
    """Campos sueltos presentes según versión: aforo de pie, latitud, año estadio."""
    out = {}
    off = team._off
    if "standing" in off:
        if pf.version == GameVersion.PCF6:
            out["standing"] = struct.unpack_from("<I", pf.raw, off["standing"])[0]
        else:
            o = off["standing"]
            out["standing"] = pf.raw[o] | pf.raw[o + 1] << 8 | pf.raw[o + 2] << 16
    if pf.version == GameVersion.PCF6 and "country" in off:
        out["latitude"] = pf.raw[off["country"] + 1]
    if pf.version == GameVersion.PCF6 and "founded" in off and team.complete:
        out["stadium_year"] = struct.unpack_from("<H", pf.raw, off["founded"] + 2)[0]
    return out


def team_stats(pf: EquiposFile, team: TeamRecord) -> dict | None:
    """Historial del club: grupo 2ªB, últimas 10 ligas, temporadas en 1ª,
    PJ/PG/PE/GF/GC/puntos y títulos de liga."""
    so = _stats_offsets(pf, team)
    if so is None:
        return None
    raw = pf.raw
    if so["subcampeon"] + 1 > len(raw):
        return None
    if so["pairs"]:
        ligas = [{"pos": raw[so["ligas"] + i * 2], "div": raw[so["ligas"] + i * 2 + 1]}
                 for i in range(10)]
    else:
        ligas = [{"pos": raw[so["ligas"] + i], "div": None} for i in range(10)]
    vals = struct.unpack_from("<6H", raw, so["stats"])
    out = {"grupo2b": raw[so["grupo2b"]], "temporadas1a": raw[so["temporadas1a"]],
           "campeon": raw[so["campeon"]], "subcampeon": raw[so["subcampeon"]],
           "ligas": ligas}
    out.update(dict(zip(STATS_FIELDS, vals)))
    if so["palmares"] + len(PALMARES_FIELDS) <= len(raw):
        out["jornadas"] = list(raw[so["jornadas"]:so["jornadas"] + so["n_jornadas"]])
        pal = raw[so["palmares"]:so["palmares"] + len(PALMARES_FIELDS)]
        out["palmares"] = dict(zip(PALMARES_FIELDS, pal))
    return out


# ---- táctica base (bloque de 176 bytes: 2 bytes + 174 de la táctica) ----

@lru_cache(maxsize=1)
def _tactic_presets() -> dict:
    from houdini_engine import refdata
    return {t["Nom"]: bytes.fromhex(t["Hex"]) for t in refdata.tactics() if t.get("Hex")}


def tactic_preset_names() -> list[str]:
    return list(_tactic_presets())


def get_tactic_name(pf: EquiposFile, team: TeamRecord) -> str | None:
    """Nombre de la táctica estándar si el bloque coincide; None = personalizada."""
    to = team._off.get("tactics")
    if not to:
        return None
    blk = bytes(pf.raw[to - 174:to])
    for name, b in _tactic_presets().items():
        if blk == b:
            return name
    return None


def get_tactic_shape(pf: EquiposFile, team: TeamRecord) -> list:
    """Las 11 posiciones de la táctica DIBUJADA del equipo (también si es
    personalizada). [] si el bloque no tiene táctica. Ver houdini_engine.tactics."""
    to = team._off.get("tactics")
    if not to:
        return []
    from houdini_engine import tactics as _T
    return _T.decode_shape(b"\x00\x00" + bytes(pf.raw[to - 174:to]))


def set_tactic_position(pf: EquiposFile, team: TeamRecord, j: int,
                        x: float, y: float, which: str = "nat") -> None:
    """Mueve al jugador `j` (0-10) de la táctica DIBUJADA al punto (x, y) del campo.

    Los 174 B del campo se reescriben enteros y en el sitio: misma longitud, sin
    descuadrar el bloque. El portero solo se mueve a lo ancho (ver `tactics.shift_player`)."""
    to = team._off.get("tactics")
    if not to:
        raise KeyError("este equipo no tiene táctica dibujada")
    from houdini_engine import tactics as _T
    blob = b"\x00\x00" + bytes(pf.raw[to - 174:to])
    pf.raw[to - 174:to] = _T.shift_player(blob, j, x, y, which=which)[2:]


def set_tactic_preset(pf: EquiposFile, team: TeamRecord, name: str) -> None:
    """Reemplaza la táctica dibujada por una estándar (los 174 bytes del mdb)."""
    to = team._off.get("tactics")
    b = _tactic_presets().get(name)
    if not to or b is None:
        raise KeyError(name)
    pf.raw[to - 174:to] = b


def clamp_budgets(pf: EquiposFile, cap: int | None = None) -> int:
    """Acota el `budget_game` de todos los equipos a `cap`. YA NO SE LLAMA en la descarga
    (ver BUDGET_GAME_MAX): se conserva por si hace falta sanear un mod concreto. (arregla mods
    ya guardados con un presupuesto que CRASHEA el juego al cargar). Devuelve cuántos corrigió.
    Se llama en la descarga → cualquier mod viejo sale ya válido sin tocar nada más."""
    fixed = 0
    for t in pf.teams:
        o = getattr(t, "_off", {}).get("budget_game")
        if o is None:
            continue
        tope = BUDGET_GAME_MAX if cap is None else int(cap)
        if struct.unpack_from("<I", pf.raw, o)[0] > tope:
            struct.pack_into("<I", pf.raw, o, tope)
            fixed += 1
    return fixed


def set_team_field(pf: EquiposFile, team: TeamRecord, field_name: str, value: int,
                   budget_max: int | None = None) -> None:
    """Edita un campo numérico de equipo (misma longitud → seguro).

    `budget_max`: tope del presupuesto EN EL JUEGO de esta edición (ver
    `budget_game_max`); por defecto, el de la base española."""
    off = team._off
    if field_name == "country":
        pf.raw[off["country"]] = value & 0xFF
    elif field_name in ("field_width", "field_length"):
        pf.raw[off["width" if field_name == "field_width" else "length"]] = value & 0xFF
    elif field_name == "founded":
        struct.pack_into("<H", pf.raw, off["founded"], value & 0xFFFF)
    elif field_name == "filial":
        struct.pack_into("<H", pf.raw, off["filial"] - 2, value & 0xFFFF)
    elif field_name == "filial2":
        struct.pack_into("<H", pf.raw, off["filial"], value & 0xFFFF)
    elif field_name in ("capacity", "members"):
        if pf.version == GameVersion.PCF6:
            struct.pack_into("<I", pf.raw, off[field_name], value & 0xFFFFFFFF)
        else:
            v = value & 0xFFFFFF
            pf.raw[off[field_name]:off[field_name] + 3] = bytes([v & 0xFF, (v >> 8) & 0xFF, (v >> 16) & 0xFF])
    elif field_name in ("budget_db", "budget_game"):
        # LÍMITES DEL JUEGO (evitan crash al cargar): el `budget_game` (presupuesto en el juego,
        # millones) NUNCA pasa de 1000 en la base (Real Madrid/Barça) → un valor mayor rompe el
        # juego ("la aplicación no puede continuar"). El `budget_db` (presupuesto de base de datos)
        # llega a ~12434 en la base; se acota generoso a u16 para no meter valores absurdos.
        cap = (budget_max or BUDGET_GAME_MAX) if field_name == "budget_game" else 0xFFFF
        struct.pack_into("<I", pf.raw, off[field_name], max(0, min(int(value), cap)))
    elif field_name == "standing" and "standing" in off:
        if pf.version == GameVersion.PCF6:
            struct.pack_into("<I", pf.raw, off["standing"], value & 0xFFFFFFFF)
        else:
            v = value & 0xFFFFFF
            pf.raw[off["standing"]:off["standing"] + 3] = bytes([v & 0xFF, (v >> 8) & 0xFF, (v >> 16) & 0xFF])
        return
    elif field_name == "latitude" and pf.version == GameVersion.PCF6:
        pf.raw[off["country"] + 1] = value & 0xFF
        return
    elif field_name == "stadium_year" and pf.version == GameVersion.PCF6:
        struct.pack_into("<H", pf.raw, off["founded"] + 2, value & 0xFFFF)
        return
    elif (so := _stats_offsets(pf, team)) is not None and field_name in (
            "grupo2b", "temporadas1a", "campeon", "subcampeon",
            *STATS_FIELDS, *PALMARES_FIELDS) \
            or field_name.startswith(("liga_pos_", "liga_div_", "jornada_")):
        if so is None:
            raise KeyError(field_name)
        if field_name in STATS_FIELDS:
            struct.pack_into("<H", pf.raw, so["stats"] + STATS_FIELDS.index(field_name) * 2,
                             value & 0xFFFF)
        elif field_name.startswith("liga_pos_"):
            i = int(field_name.rsplit("_", 1)[1])
            step = 2 if so["pairs"] else 1
            pf.raw[so["ligas"] + i * step] = value & 0xFF
        elif field_name.startswith("liga_div_"):
            if not so["pairs"]:
                raise KeyError(field_name)
            i = int(field_name.rsplit("_", 1)[1])
            pf.raw[so["ligas"] + i * 2 + 1] = value & 0xFF
        elif field_name.startswith("jornada_"):
            i = int(field_name.rsplit("_", 1)[1])
            if not 0 <= i < so["n_jornadas"]:
                raise KeyError(field_name)
            pf.raw[so["jornadas"] + i] = value & 0xFF
        elif field_name in PALMARES_FIELDS:
            pf.raw[so["palmares"] + PALMARES_FIELDS.index(field_name)] = value & 0xFF
        else:
            pf.raw[so[field_name]] = value & 0xFF
        return
    else:
        raise KeyError(field_name)
    setattr(team, field_name, value)


def set_block_field(pf: EquiposFile, player: PlayerRecord, field_name: str, value: int) -> None:
    """Edita un campo fijo (misma longitud → seguro, sin descuadrar el bloque)."""
    off = player.block_off
    layout = {
        "lineup_position": off + 0, "origin": off + 1,
        "country": off + 8, "skin": off + 9, "hair": off + 10, "ptype": off + 11,
        "birth_day": off + 12, "birth_month": off + 13,
        "height": off + 16, "weight": off + 17,
    }
    if field_name == "birth_year":
        struct.pack_into("<H", pf.raw, off + 14, value & 0xFFFF)
    elif field_name.startswith("demarcation"):
        idx = int(field_name[-1])
        pf.raw[off + 2 + idx] = value & 0xFF
        # `demarcations` es una LISTA, no un atributo suelto: hay que actualizar la posición
        # (antes `setattr(player, "demarcationN", v)` creaba un atributo basura y el objeto en
        # memoria quedaba desactualizado → la ficha mostraba el valor viejo tras guardar).
        if 0 <= idx < len(player.demarcations):
            player.demarcations[idx] = value & 0xFF
        return
    elif field_name in layout:
        pf.raw[layout[field_name]] = value & 0xFF
    else:
        raise KeyError(field_name)
    setattr(player, field_name, value)


def set_player_field(pf: EquiposFile, player: PlayerRecord, field_name: str, value: int) -> None:
    """Edita un campo numérico de jugador (dorsal, medias o campos del bloque fijo)."""
    if field_name == "number":
        pf.raw[player.offset + 2] = value & 0xFF
        player.number = value & 0xFF
    elif field_name in ("VE", "RE", "AG", "CA", "RG", "RM", "PA", "TI", "EN", "PO"):
        set_rating(pf, player, field_name, value)
    elif field_name == "birth_country":
        offs = player_db_offsets(pf, player)
        if offs is None:
            raise KeyError(field_name)
        pf.raw[offs["birth_country"]] = value & 0xFF
    else:
        set_block_field(pf, player, field_name, value)


# ---- edición de campos de texto (conservando la longitud del bloque) ----

class TextTooLong(ValueError):
    pass


def _slot_len(raw, len_off) -> int:
    """Tamaño (en bytes) del hueco de una cadena [len u16 LE][body]."""
    return struct.unpack_from("<H", raw, len_off)[0]


def _write_text(raw, len_off, new_text) -> None:
    """Escribe `new_text` en el hueco de [len u16 LE][body] conservando su tamaño.

    Textos más cortos se rellenan con espacios; más largos que el hueco lanzan
    TextTooLong. No cambia la longitud del bloque (seguro para el juego).
    """
    slot = _slot_len(raw, len_off)
    body = text.encode(new_text)
    if len(body) > slot:
        raise TextTooLong(f"máximo {slot} caracteres (has puesto {len(body)})")
    pad = text.encode(" ") * (slot - len(body))
    raw[len_off + 2:len_off + 2 + slot] = body + pad
    # la longitud (len_off) se mantiene = slot para no descuadrar el bloque


_TEAM_TEXT = {"short_name": "short", "stadium": "stadium", "long_name": "long",
              "president": "president", "sponsor": "sponsor", "supplier": "supplier",
              "coach_short": "coach_short", "coach_long": "coach_long",
              **{k: k for k in COACH_TEXT_FIELDS},
              "coach_tray_jugador": "coach_tray_jugador",
              "coach_declaraciones": "coach_declaraciones"}


def coach_texts(pf: EquiposFile, team: TeamRecord) -> dict:
    """Textos de BBDD del entrenador presentes (perfil, palmarés, trayectoria…)."""
    out = {}
    for key in (*COACH_TEXT_FIELDS, "coach_tray_jugador", "coach_declaraciones"):
        o = team._off.get(key)
        if o is None:
            continue
        n = _slot_len(pf.raw, o)
        out[key] = text.decode(bytes(pf.raw[o + 2:o + 2 + n]))
    return out


def set_team_tactic(pf: EquiposFile, team: TeamRecord, field_name: str, value: int) -> None:
    """Edita un byte de la táctica de equipo (toque, contragolpe, ataque…)."""
    if "tactics" not in team._off or field_name not in TACTIC_FIELDS:
        raise KeyError(field_name)
    idx = TACTIC_FIELDS.index(field_name)
    pf.raw[team._off["tactics"] + idx] = value & 0xFF
    team.tactics[idx] = value & 0xFF


def team_text_limits(team: TeamRecord, raw) -> dict:
    """Máximo de caracteres editable por campo de texto del equipo (hueco u16 LE)."""
    return {k: _slot_len(raw, team._off[o]) for k, o in _TEAM_TEXT.items() if o in team._off}


def coach_area_sane(raw, team: TeamRecord) -> bool:
    """¿Es seguro editar la zona de entrenador de este bloque?

    Algunos bloques traen la zona del míster DEGENERADA de fábrica (6.0 Oro set
    97: Levante/Deportivo/… con placeholders 'a','b','c' y "huecos" que solapan
    varios campos con sus longitudes internas). Escribir ahí conserva la longitud
    total pero machaca esas longitudes internas → MANAGER.EXE descarrila y
    CRASHEA (validado en juego: un solo DBC del Levante tumbaba el juego).
    Regla: corto y largo deben ser cadenas contiguas, de tamaño creíble y sin
    restos de bytes de control descifrados (p.ej. '\\x60')."""
    malos = {"`", "\x00", "\x7f"}
    os_ = team._off.get("coach_short")
    if os_ is None:
        return False
    n = struct.unpack_from("<H", raw, os_)[0]
    if not (2 <= n <= COACH_SHORT_MAX):
        return False
    if set(text.decode(bytes(raw[os_ + 2:os_ + 2 + n]))) & malos:
        return False
    ol = team._off.get("coach_long")
    if ol is None:
        return True   # foráneo: solo hay nombre corto, y es sano
    if os_ + 2 + n != ol:
        return False
    nl = struct.unpack_from("<H", raw, ol)[0]
    if not (2 <= nl <= COACH_LONG_MAX):
        return False
    return not set(text.decode(bytes(raw[ol + 2:ol + 2 + nl]))) & malos


def set_team_text(pf: EquiposFile, team: TeamRecord, field_name: str, value: str) -> None:
    o = _TEAM_TEXT.get(field_name)
    if o is None or o not in team._off:
        raise KeyError(field_name)
    if field_name.startswith("coach") and not coach_area_sane(pf.raw, team):
        raise KeyError(f"{field_name}: zona de entrenador atípica, no editable")
    _write_text(pf.raw, team._off[o], value)
    setattr(team, field_name, value)


def set_coach_text(pf: EquiposFile, team: TeamRecord, idx: int, field: str, value: str) -> None:
    """Edita un texto (o el nombre) de un entrenador CUALQUIERA del equipo.

    `idx` = su posición en `team.coaches` (0 = el que sale en la ficha). Los campos son
    `short_name`, `long_name` y los ocho de `COACH_TEXT_FIELDS` + `coach_tray_jugador` +
    `coach_declaraciones`. Escritura in-place: conserva la longitud del hueco."""
    cs = getattr(team, "coaches", None) or []
    if not 0 <= idx < len(cs):
        raise KeyError(f"entrenador {idx} no existe")
    if not coach_area_sane(pf.raw, team):
        raise KeyError("zona de entrenador atípica, no editable")
    c = cs[idx]
    off = ({"short_name": c["short_off"], "long_name": c["long_off"]}.get(field)
           or c["texts"].get(field))
    if off is None:
        raise KeyError(field)
    _write_text(pf.raw, off, value)
    if field in ("short_name", "long_name"):
        c[field] = value
        if idx == 0:                       # el primero es el de la ficha
            setattr(team, "coach_" + ("short" if field == "short_name" else "long"), value)


def coach_text_limits(pf: EquiposFile, team: TeamRecord, idx: int) -> dict:
    """Longitud máxima de cada campo de ese entrenador (el hueco que ocupa hoy)."""
    cs = getattr(team, "coaches", None) or []
    if not 0 <= idx < len(cs):
        return {}
    c = cs[idx]
    out = {}
    for k, off in [("short_name", c["short_off"]), ("long_name", c["long_off"])] + list(c["texts"].items()):
        out[k] = _slot_len(pf.raw, off)
    return out


# Tope de nuestro PROPIO anclaje al localizar entrenadores dentro de un bloque. No es un
# límite del juego: en el bloque no hay índice, al míster se le encuentra por gramática
# (marca 0x02 + dos cadenas creíbles), y estos números son la tolerancia de esa búsqueda.
# Escribir por encima nos dejaría sin poder releer lo que acabamos de escribir.
#
# Estaban en 30/40 y se quedaban CORTOS de fábrica: en PCF6 y 6.0 Oro, Valdano figura como
# "Jorge Alberto Francisco Valdano Castellanos" (43) y por pasarse del tope su registro se
# descartaba entero — esos dos equipos enseñaban a Ranieri como entrenador. Con 63/79 los
# ocho ficheros originales parsean IGUAL salvo ese entrenador, que ahora sí sale.
COACH_SHORT_MAX, COACH_LONG_MAX = 63, 79


def coach_names_pool(pf: EquiposFile, team: TeamRecord, idx: int = 0) -> int:
    """Caracteres que se pueden repartir entre el nombre corto y el largo del entrenador.

    Los dos van pegados en el fichero, así que el bloque solo obliga a respetar la SUMA:
    dentro de ella, uno puede crecer a costa del otro. Es lo que arregla el caso de los
    entrenadores a los que Dinamic puso un nombre corto minúsculo —hay huecos de 3 y 4
    letras— y que hasta ahora encadenaban al usuario a ese tamaño.

    Devuelve 0 si la pareja no es contigua o la zona no es editable."""
    cs = getattr(team, "coaches", None) or []
    if not 0 <= idx < len(cs) or not coach_area_sane(pf.raw, team):
        return 0
    c = cs[idx]
    so, lo = c.get("short_off"), c.get("long_off")
    if so is None or lo is None:
        return 0
    ns = _slot_len(pf.raw, so)
    if so + 2 + ns != lo:           # solo se reparte lo que va pegado
        return 0
    return ns + _slot_len(pf.raw, lo)


def fit_coach_names(pool: int, short_name: str, long_name: str,
                    priority: str = "short_name") -> tuple[str, str] | None:
    """Recorta la pareja de nombres a lo que quepa en `pool`, dando prioridad al campo que
    el usuario acaba de editar y SIN dejar ninguno de los dos por debajo de 2 caracteres.

    Ese mínimo no es capricho: al míster se le localiza por gramática dentro del bloque, y
    un nombre vacío lo volvería imposible de reencontrar — el equipo se quedaría sin
    entrenador. Devuelve None si el hueco no da ni para eso."""
    if pool < 4:
        return None
    bs, bl = text.encode(short_name), text.encode(long_name)
    if len(bs) + len(bl) <= pool:
        return short_name, long_name
    if priority == "short_name":
        ns = min(len(bs), pool - 2)
        nl = pool - ns
    else:
        nl = min(len(bl), pool - 2)
        ns = pool - nl
    return short_name[:ns], long_name[:nl]


def set_coach_names(pf: EquiposFile, team: TeamRecord, idx: int,
                    short_name: str, long_name: str) -> None:
    """Escribe los DOS nombres del entrenador repartiendo el hueco común entre ellos.

    Conserva el tamaño del bloque (lo que sobra se rellena con espacios en el largo), así
    que sigue valiendo para el PKF y no hace falta DBC. Lanza `TextTooLong` cuando la suma
    no cabe: ahí es donde toma el relevo el DBC, que no tiene esta restricción."""
    cs = getattr(team, "coaches", None) or []
    if not 0 <= idx < len(cs):
        raise KeyError(f"entrenador {idx} no existe")
    pool = coach_names_pool(pf, team, idx)
    if not pool:
        raise KeyError("zona de entrenador atípica, no editable")
    c = cs[idx]
    so, lo = c["short_off"], c["long_off"]
    fin = lo + 2 + _slot_len(pf.raw, lo)
    bs, bl = text.encode(short_name), text.encode(long_name)
    if len(bs) > COACH_SHORT_MAX:
        raise TextTooLong(f"el nombre corto admite {COACH_SHORT_MAX} caracteres")
    if len(bl) > COACH_LONG_MAX:
        raise TextTooLong(f"el nombre largo admite {COACH_LONG_MAX} caracteres")
    if len(bs) + len(bl) > pool:
        raise TextTooLong(f"entre los dos nombres caben {pool} caracteres "
                          f"(has puesto {len(bs) + len(bl)})")
    bl += text.encode(" ") * (pool - len(bs) - len(bl))     # el resto, al largo
    pf.raw[so:fin] = (struct.pack("<H", len(bs)) + bs
                      + struct.pack("<H", len(bl)) + bl)
    # el largo se ha MOVIDO (el corto ya no mide lo mismo); los textos de BBDD que van
    # detrás no, porque la suma —y por tanto el final de la zona— no ha cambiado
    nuevo_lo = so + 2 + len(bs)
    c["long_off"] = nuevo_lo
    c["short_name"], c["long_name"] = short_name, long_name
    if idx == 0:
        team._off["coach_long"] = nuevo_lo
        team.coach_short, team.coach_long = short_name, long_name


def rebuild_prefix_coach(prefix: bytes, team: TeamRecord,
                         short_name: str, long_name: str) -> bytes:
    """Reescribe los nombres del entrenador de la ficha dentro del `prefix` de un bloque DBC,
    a CUALQUIER longitud. Es el mismo recurso que ya usan el nombre de equipo y el estadio: un
    DBC no arrastra la longitud fija del PKF, y así lo hacen también los editores de la
    comunidad (calculan la longitud de la propia cadena, sin hueco previo).

    Si los offsets no encajan devuelve el prefix tal cual, que es el fallback seguro."""
    cs = getattr(team, "coaches", None) or []
    if not cs:
        return prefix
    c = cs[0]
    so, lo = c.get("short_off"), c.get("long_off")
    if so is None or lo is None:
        return prefix
    base = team.sig_off
    rs, rl = so - base, lo - base
    fin = rl + 2 + int.from_bytes(prefix[rl:rl + 2], "little") if 0 <= rl < len(prefix) else -1
    if not (0 <= rs < rl < fin <= len(prefix)):
        return prefix
    if rs + 2 + int.from_bytes(prefix[rs:rs + 2], "little") != rl:
        return prefix                      # no contiguos: no tocamos nada
    # Y que ahí haya DE VERDAD un registro de entrenador: los nombres van justo detrás de la
    # marca `02` y su puntero u16. Sin esta comprobación, un ancla mal calculada escribía el
    # nombre dentro de otro texto y dejaba el DBC ilegible a partir de ahí (6.0 original,
    # Cádiz). Ante la duda no se toca, que es el criterio de toda esta función.
    if rs < 3 or prefix[rs - 3] != 0x02:
        return prefix

    def enc(s: str) -> bytes:
        b = text.encode(s)
        return struct.pack("<H", len(b)) + b

    return bytes(prefix[:rs]) + enc(short_name) + enc(long_name) + bytes(prefix[fin:])


def coach_texts_at(pf: EquiposFile, team: TeamRecord, idx: int) -> dict:
    """Los textos de ese entrenador, ya descifrados."""
    cs = getattr(team, "coaches", None) or []
    if not 0 <= idx < len(cs):
        return {}
    out = {}
    for k, off in cs[idx]["texts"].items():
        n = struct.unpack_from("<H", pf.raw, off)[0]
        out[k] = text.decode(pf.raw[off + 2:off + 2 + n])
    return out


def rebuild_prefix_names(prefix: bytes, team: TeamRecord,
                         short_name: str, long_name: str,
                         stadium: str | None = None) -> bytes:
    """Reescribe los nombres corto y largo (y opcionalmente el ESTADIO) dentro del
    `prefix` de un bloque DBC a CUALQUIER longitud (un DBC no tiene la restricción de
    longitud fija del PKF). Conserva país y todo lo demás. Si faltan offsets, devuelve
    el prefix tal cual (fallback seguro). Layout: [corto][estadio][largo][aforo…]."""
    o = team._off
    if not all(k in o for k in ("short", "stadium", "long", "capacity")):
        return prefix
    base = team.sig_off
    rs, rst, rl, rc = (o["short"] - base, o["stadium"] - base,
                       o["long"] - base, o["capacity"] - base)
    if not (0 <= rs <= rst <= rl <= rc <= len(prefix)):
        return prefix

    def enc(s: str) -> bytes:
        b = text.encode(s)
        return bytes([len(b) & 0xFF, 0]) + b

    if stadium is None:
        stad = bytes(prefix[rst:rl])       # el estadio tal cual, con lo que lleve detrás
    else:
        # Entre el estadio y el nombre largo hay 2 BYTES que no modelamos —están en todos
        # los equipos, medidos en 6.0 Oro— y hay que conservarlos. Escribiendo solo el campo
        # del estadio se perdían, el bloque se descuadraba y el DBC dejaba de poder leerse:
        # al juego le impedía arrancar ("la aplicación no puede continuar") sin decir por
        # qué. Solo saltaba cuando el estadio NO cabía en su hueco y venía por override, o
        # sea en 3 equipos de 127 — por eso costó verlo.
        n_orig = int.from_bytes(bytes(prefix[rst:rst + 2]), "little")
        cola = bytes(prefix[rst + 2 + n_orig:rl])
        stad = enc(stadium) + cola
    return bytes(prefix[:rs]) + enc(short_name) + stad \
        + enc(long_name) + bytes(prefix[rc:])


def player_text_limits(player: PlayerRecord, raw) -> dict:
    return {"short_name": raw[player.short_off], "long_name": raw[player.long_off]}


# cadenas de BBDD del jugador nacional, en orden en disco (manual sec. 18.2)
PLAYER_DB_FIELDS = ["lugar_nacimiento", "club_debut", "internacional", "perfil",
                    "caracteristicas", "palmares", "internacionalidad", "anecdotas",
                    "ultima_temporada", "trayectoria"]


def player_db_offsets(pf: EquiposFile, player: PlayerRecord) -> dict | None:
    """Offsets de país de nacimiento + 10 cadenas de BBDD del jugador NACIONAL.
    Valida que el paseo termina exactamente donde empiezan las medias; si no
    (jugador foráneo o layout inesperado), devuelve None."""
    raw = pf.raw
    o = player.block_off + BLOCK_LEN
    out = {"birth_country": o}
    o += 1
    for key in PLAYER_DB_FIELDS:
        if o + 2 > len(raw):
            return None
        n = struct.unpack_from("<H", raw, o)[0]
        if n > 5000 or o + 2 + n > len(raw):
            return None
        out[key] = o
        o += 2 + n
    if player.ratings_off and o != player.ratings_off:
        return None
    return out


def player_db_texts(pf: EquiposFile, player: PlayerRecord) -> dict | None:
    """{campo: (texto, hueco)} de las cadenas de BBDD, o None si es foráneo."""
    offs = player_db_offsets(pf, player)
    if offs is None:
        return None
    out = {"birth_country": pf.raw[offs["birth_country"]]}
    for key in PLAYER_DB_FIELDS:
        o = offs[key]
        n = _slot_len(pf.raw, o)
        out[key] = (text.decode(bytes(pf.raw[o + 2:o + 2 + n])), n)
    return out


def set_player_text(pf: EquiposFile, player: PlayerRecord, field_name: str, value: str) -> None:
    off = {"short_name": player.short_off, "long_name": player.long_off}.get(field_name)
    if off is None and field_name in PLAYER_DB_FIELDS:
        offs = player_db_offsets(pf, player)
        if offs:
            off = offs[field_name]
    if off is None:
        raise KeyError(field_name)
    _write_text(pf.raw, off, value)
    if field_name in ("short_name", "long_name"):
        setattr(player, field_name, value)


def serialize(pf: EquiposFile) -> bytes:
    """Devuelve el fichero. Sin cambios → idéntico byte a byte al original."""
    return bytes(pf.raw)
