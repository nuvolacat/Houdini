"""Modelo COMPLETO de bloque de equipo (base para exportar DBC).

A diferencia de equipos_pkf.py (edición in-place con longitud fija), este módulo
deserializa un bloque de equipo a un modelo editable y lo re-serializa. Al no tener
la restricción de longitud fija (un DBC es un fichero autónomo), permite:
  - nombres de cualquier longitud
  - añadir / eliminar jugadores

Estructura de jugador (validada v5/v6):
  nacional: 01, puntero u16, dorsal u8, corto[u16], largo[u16], bloque(18),
            país_nac u8, 10 cadenas BBDD[u16], medias(10)
  foráneo:  01, puntero u16, dorsal u8, corto[u16], largo[u16], bloque(18), medias(10)

Las cadenas usan prefijo de longitud **u16 LE**. El bloque fijo de 18 bytes y las
cadenas de BBDD se conservan en crudo (round-trip byte-perfecto por construcción).
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field

from ..codec import text

DB_STRINGS = 10  # nº de cadenas de BBDD en un jugador nacional
# Tope de plantilla. Estaba en 35 «por límite práctico del juego», pero los propios ficheros lo
# desmienten: las CUATRO ediciones v5/6 traen de fábrica un equipo de **50** —los Juveniles
# Españoles— y el R. Sporting de 6.0 Oro tiene 37. O sea que el juego lee 50 todos los días y el
# 35 era nuestro. Se sube a 50, que es lo que está demostrado; pasar de ahí ya habría que
# validarlo en la VM (pedido en el foro, 2026-08-29).
MAX_PLAYERS = 50

# offsets dentro del bloque fijo de 18 bytes del jugador
_FIXED = {
    "lineup_position": 0, "origin": 1,
    # demarcation0..5 -> 2..7
    "country": 8, "skin": 9, "hair": 10, "ptype": 11,
    "birth_day": 12, "birth_month": 13,  # año u16 en 14-15
    "height": 16, "weight": 17,
}


def _rd_u16str(data, o):
    ln = struct.unpack_from("<H", data, o)[0]
    return bytes(data[o + 2:o + 2 + ln]), o + 2 + ln


def _wr_u16str(body: bytes) -> bytes:
    return struct.pack("<H", len(body)) + body


@dataclass
class FullPlayer:
    pointer: int
    number: int
    short_raw: bytes          # nombre corto codificado
    long_raw: bytes
    fixed: bytes              # 18 bytes: slot, proc, roles[6], nac, piel, pelo, tipo, d, m, año, alt, peso
    medias: bytes             # 10 bytes
    foreign: bool
    birth_country: int = 0    # país de nacimiento (solo nacional)
    db_strings: list = field(default_factory=list)  # 10 cadenas BBDD en crudo (nacional)
    # Puntero ORIGINAL a escribir al serializar. Se usa cuando el editor asigna un `pointer`
    # SINTÉTICO único (para equipos especiales con varios jugadores a puntero 0, que si no
    # colisionan en el direccionamiento). None = escribir el propio `pointer`. Así el fichero
    # del juego queda idéntico (round-trip) aunque internamente el jugador tenga otro id.
    orig_pointer: "int | None" = None

    @property
    def short_name(self) -> str:
        return text.decode(self.short_raw)

    @property
    def long_name(self) -> str:
        return text.decode(self.long_raw)

    def set_short(self, s: str) -> None:
        self.short_raw = text.encode(s)

    def set_long(self, s: str) -> None:
        self.long_raw = text.encode(s)

    def set_field(self, name: str, value: int) -> None:
        """Edita un campo del bloque fijo (mismos nombres que el editor in-place)."""
        b = bytearray(self.fixed)
        if name.startswith("demarcation"):
            i = int(name[len("demarcation"):] or 0)
            if not 0 <= i <= 5:
                raise KeyError(name)
            b[2 + i] = value & 0xFF
        elif name == "birth_year":
            struct.pack_into("<H", b, 14, value & 0xFFFF)
        elif name == "number":
            self.number = value & 0xFF
            return
        elif name == "birth_country":
            self.birth_country = value & 0xFF
            return
        elif name in _FIXED:
            b[_FIXED[name]] = value & 0xFF
        else:
            raise KeyError(name)
        self.fixed = bytes(b)

    def set_rating(self, index: int, value: int) -> None:
        """Media por índice EN DISCO (0..9); el mapeo de etiquetas v5/v6 va aparte."""
        if not 0 <= index < len(self.medias):
            raise IndexError(index)
        m = bytearray(self.medias)
        m[index] = max(0, min(99, value))
        self.medias = bytes(m)

    @property
    def ptype(self) -> int:
        return self.fixed[11]

    def db_text(self, index: int) -> str:
        if not 0 <= index < len(self.db_strings):
            return ""
        return text.decode(self.db_strings[index])

    def set_db_string(self, index: int, value: str) -> None:
        """Cadena de BBDD por índice (orden del manual 18.2). Sin límite (DBC)."""
        if not 0 <= index < len(self.db_strings):
            raise IndexError(index)
        self.db_strings[index] = text.encode(value)

    def serialize(self) -> bytes:
        out = bytearray()
        out.append(0x01)
        out += struct.pack("<H", self.pointer if self.orig_pointer is None else self.orig_pointer)
        out.append(self.number & 0xFF)
        out += _wr_u16str(self.short_raw)
        out += _wr_u16str(self.long_raw)
        out += self.fixed
        if not self.foreign:
            out.append(self.birth_country & 0xFF)
            for s in self.db_strings:
                out += _wr_u16str(s)
        out += self.medias
        return bytes(out)


def parse_player(data, o, foreign):
    """Parsea un jugador desde su marcador 01. Devuelve (FullPlayer, offset_siguiente)."""
    assert data[o] == 0x01, f"no hay marcador 01 en 0x{o:x}"
    o += 1
    pointer = struct.unpack_from("<H", data, o)[0]; o += 2
    number = data[o]; o += 1
    short_raw, o = _rd_u16str(data, o)
    long_raw, o = _rd_u16str(data, o)
    fixed = bytes(data[o:o + 18]); o += 18
    birth_country = 0
    db_strings = []
    if not foreign:
        birth_country = data[o]; o += 1
        for _ in range(DB_STRINGS):
            s, o = _rd_u16str(data, o)
            db_strings.append(s)
    medias = bytes(data[o:o + 10]); o += 10
    return FullPlayer(
        pointer=pointer, number=number, short_raw=short_raw, long_raw=long_raw,
        fixed=fixed, medias=medias, foreign=foreign, birth_country=birth_country,
        db_strings=db_strings,
    ), o


def _skip_coach(data, o, foreign):
    """Salta un elemento ENTRENADOR (marcador 0x02) y devuelve el offset siguiente.
    Modelo del editor MultiEditorPCC (1Simo1): 02 + id(2) + corto[u16]; en equipos
    JUGABLES (nacionales) sigue largo[u16] + 6 textos + [03 + trayectoria jugador]
    + declaraciones. En FORÁNEOS acaba tras el nombre corto."""
    assert data[o] == 0x02
    p = o + 1 + 2                       # marcador + id
    n = struct.unpack_from("<H", data, p)[0]; p += 2 + n     # nombre corto
    if foreign:
        return p
    n = struct.unpack_from("<H", data, p)[0]; p += 2 + n     # nombre largo
    for _ in range(6):                 # perfil/sistemas/palmarés/anécdotas/última/trayectoria
        n = struct.unpack_from("<H", data, p)[0]; p += 2 + n
    if data[p] == 0x03:                # separador: trayectoria como jugador
        p += 1
        n = struct.unpack_from("<H", data, p)[0]; p += 2 + n
    else:
        p += 1
    n = struct.unpack_from("<H", data, p)[0]; p += 2 + n     # declaraciones
    return p


def walk_elements(data, start, next_sig, foreign):
    """Camina el FLUJO tras la táctica: cada elemento empieza por 0x01 (jugador) o
    0x02 (entrenador), hasta un byte que no es 1 ni 2 (modelo del editor de
    1Simo1). Devuelve (players, coach_spans, end) o None si no consume limpio.
    Resuelve los bloques foráneos atípicos (Empoli, West Ham…) donde el
    entrenador va INTERCALADO y nuestro anclaje por gramática fallaba."""
    o = start
    players, coach_spans = [], []
    try:
        while o < next_sig and data[o] in (0x01, 0x02):
            if data[o] == 0x01:
                pl, o = parse_player(data, o, foreign)
                players.append(pl)
            else:
                nxt = _skip_coach(data, o, foreign)
                coach_spans.append((o, nxt))
                o = nxt
    except Exception:  # noqa: BLE001
        return None
    if next_sig - o > 20:              # la cola buena queda pegada a la firma
        return None
    return players, coach_spans, o


@dataclass
class Block:
    """Bloque de equipo completo = prefijo (cabecera+entrenador+táctica) + jugadores."""
    prefix: bytes             # todo hasta el primer jugador (en crudo)
    players: list             # FullPlayer
    trailing: bytes = b""     # relleno posterior (normalmente vacío)
    foreign: bool = False

    def serialize(self) -> bytes:
        return self.prefix + b"".join(p.serialize() for p in self.players) + self.trailing


_DEFAULT_TRAJECTORY = "ND,ND,ND,ND,ND=="


def new_player(*, pointer: int, number: int, short: str, long: str, demarcation: int,
               ptype: int, country: int, foreign: bool, skin: int = 1, hair: int = 3,
               birth_day: int = 1, birth_month: int = 1, birth_year: int = 1975,
               height: int = 180, weight: int = 75,
               secondary: tuple | list = ()) -> FullPlayer:
    """Jugador nuevo con los valores por defecto del editor de referencia.
    `secondary` = roles compatibles extra (demarcaciones 2-6, como los originales)."""
    fixed = bytearray(18)
    fixed[0] = 0            # slot en alineación
    fixed[1] = 0            # procedencia (00 = continúa)
    fixed[2] = demarcation & 0xFF
    for i, r in enumerate(list(secondary)[:5]):
        fixed[3 + i] = int(r) & 0xFF
    fixed[8] = country & 0xFF
    fixed[9] = skin & 0xFF
    fixed[10] = hair & 0xFF
    fixed[11] = ptype & 0xFF
    fixed[12] = birth_day & 0xFF
    fixed[13] = birth_month & 0xFF
    struct.pack_into("<H", fixed, 14, birth_year & 0xFFFF)
    fixed[16] = height & 0xFF
    fixed[17] = weight & 0xFF
    db_strings = []
    if not foreign:
        db_strings = [text.encode("x")] * (DB_STRINGS - 1) + [text.encode(_DEFAULT_TRAJECTORY)]
    return FullPlayer(
        pointer=pointer, number=number, short_raw=text.encode(short),
        long_raw=text.encode(long), fixed=bytes(fixed), medias=bytes([50] * 10),
        foreign=foreign, birth_country=country, db_strings=db_strings,
    )


def add_player(blk: "Block", player: FullPlayer) -> int:
    """Inserta manteniendo el orden por tipo (portero→defensa→medio→delantero).
    Devuelve el índice donde quedó. Lanza ValueError si el equipo está lleno o
    el puntero ya existe en el bloque."""
    if len(blk.players) >= MAX_PLAYERS:
        raise ValueError(f"el equipo ya tiene el máximo de {MAX_PLAYERS} jugadores")
    if any(p.pointer == player.pointer for p in blk.players):
        raise ValueError(f"puntero {player.pointer} repetido en el equipo")
    player.foreign = blk.foreign
    if blk.foreign:
        player.db_strings = []
    elif len(player.db_strings) != DB_STRINGS:
        # nacional necesita SIEMPRE 10 cadenas de BBDD (p.ej. al venir de un foráneo)
        player.db_strings = ([text.encode("x")] * (DB_STRINGS - 1)
                             + [text.encode(_DEFAULT_TRAJECTORY)])
    idx = len(blk.players)
    for i, p in enumerate(blk.players):
        if p.ptype > player.ptype:
            idx = i
            break
    blk.players.insert(idx, player)
    return idx


def remove_player(blk: "Block", index: int, allow_empty: bool = False) -> FullPlayer:
    """Saca al jugador `index` del bloque.

    Un CLUB sin jugadores no tiene sentido para el juego, de ahí el tope. Pero el pozo de
    «Jugadores Libres» sí: es el sitio de donde el juego va fichando, y las ocho bases de v5/6
    lo traen con UN SOLO jugador, así que sacarlo —que es justo lo que se quiere hacer con
    él— chocaba contra esta regla (foro, 31-ago-2026: Collymore en 6.0 Oro). Para ese
    caso el llamante pasa `allow_empty`; el bloque se serializa igual de bien vacío."""
    if not 0 <= index < len(blk.players):
        raise IndexError(index)
    if len(blk.players) <= 1 and not allow_empty:
        raise ValueError("el equipo no puede quedarse sin jugadores")
    return blk.players.pop(index)


# La tabla de jugadores del JUEGO no admite punteros arbitrarios: el 97-set
# original de 6.0 Oro llega a 22060 y meter punteros muy por encima (los rangos
# canónicos de equipos foráneos: ptr*50 = 20000..65535) CRASHEA MANAGER.EXE al
# cargar los DBC (cazado por bisección: Milan ptr 201→~10000 carga,
# Bayern 401→>20000 peta). Además en v5 los punteros >19999 no muestran foto.
MAX_PLAYER_POINTER_SAFE = 19999   # preferente (foto garantizada)
MAX_PLAYER_POINTER = 22060        # tope demostrado por los datos originales


# PUNTEROS RESERVADOS A LAS SELECCIONES DEL DESAFÍO (v5/6).
#
# Estos 33 punteros de jugador no son unos cualesquiera: son los que el juego usa para armar las
# **selecciones de Europa y América del Desafío**. El dato no está en la base —por eso no se
# podía deducir mirando el fichero—, viene de la lista de punteros especiales que circula en la
# comunidad, y se ha comprobado contra la base de 6.0 Oro: los 33 existen y son justo quienes
# uno esperaría (Hierro, Redondo y Raúl, Figo, Guardiola, Mijatovic, Kluivert, Köhler, Zanetti,
# Ronaldo…). De los 33, **31 cuadran con la nacionalidad** que marca la lista; los dos que no
# —Redondo y Aldair— son naturalizados, y el Desafío los cuenta por su país de NACIMIENTO
# (Aldair tiene dos fichas y la suya dice Brasil).
#
# Por qué importa: al crear un jugador se le da el primer puntero libre. Si un «Actualizar todo»
# se lleva por delante a Raúl o a Figo, su puntero queda libre y el siguiente jugador nuevo se
# lo queda — y acaba en la selección continental del Desafío sin que nadie lo haya pedido. Así
# que se reparten los últimos, solo si no queda ningún otro sitio.
PUNTEROS_DESAFIO = frozenset({
    10, 12, 20, 31, 34, 144, 1802, 1870, 1872, 1995, 2004, 2685, 2814, 3149, 3371, 3385,
    3411, 3612, 4067, 4150, 4302, 4327, 4331, 7278, 8452, 8492, 8577, 8837, 8857, 9911,
    14626, 16856, 16875,
})


class SinPunteros(ValueError):
    """No queda ni un puntero de jugador libre bajo el tope del juego.

    Es un ValueError para no romper a quien ya lo capturaba, pero con su propio tipo para poder
    distinguirlo: no es «este equipo ha fallado», es «el mod está lleno» y hasta que se libere
    espacio van a fallar TODOS los que queden. En un mod real de 5.0 Oro se llevó por delante
    746 equipos de golpe."""


def free_pointer(used: set[int], team_pointer: int | None = None) -> int:
    """Puntero libre para un jugador nuevo. Se intenta primero el rango canónico
    del equipo (50 por equipo: (P-1)*50+1 .. P*50, manual sec. 6) si cae bajo el
    tope seguro; después huecos globales bajo el tope seguro; como último
    recurso, la franja 20000-22060 (existente en los datos originales).

    Los 33 de `PUNTEROS_DESAFIO` se dejan para el final: meterían al jugador en la selección
    de Europa o de América sin que nadie lo pida. Solo se usan si no queda ningún otro."""
    if team_pointer and team_pointer > 0:
        lo = (team_pointer - 1) * 50 + 1
        for ptr in range(lo, lo + 50):
            if ptr <= MAX_PLAYER_POINTER_SAFE and ptr not in used \
                    and ptr not in PUNTEROS_DESAFIO:
                return ptr
    for cand in range(1, MAX_PLAYER_POINTER + 1):
        if cand not in used and cand not in PUNTEROS_DESAFIO:
            return cand
    # el mod está tan lleno que ya solo quedan los del Desafío: mejor eso que no poder crear
    for cand in sorted(PUNTEROS_DESAFIO):
        if cand not in used:
            return cand
    raise SinPunteros(
        f"el juego solo admite {MAX_PLAYER_POINTER} fichas de jugador y este mod las tiene "
        "todas ocupadas. Suele pasar por ampliar la base en muchos países: cada equipo nuevo "
        "se lleva unas 20. Puedes liberar espacio borrando equipos que no uses ("
        "Libres → «Borrar los añadidos») o ampliar menos países")


def parse_block(data, sig_off, next_sig, first_player_off, foreign):
    """Parsea un bloque de equipo entre su firma y la siguiente.

    first_player_off = offset del marcador 01 del primer jugador.
    """
    prefix = bytes(data[sig_off:first_player_off])
    players = []
    o = first_player_off
    while o < next_sig and data[o] == 0x01:
        p, o = parse_player(data, o, foreign)
        players.append(p)
    trailing = bytes(data[o:next_sig])
    return Block(prefix=prefix, players=players, trailing=trailing, foreign=foreign)
