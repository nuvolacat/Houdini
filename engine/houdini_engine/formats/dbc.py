"""Ficheros DBC de equipo (override por equipo que lee el juego).

Un DBC es EXACTAMENTE un bloque de equipo del PKF con una diferencia: tras la
firma de 36 bytes, donde el PKF lleva el puntero de equipo u16, el DBC lleva
``FF FF`` (confirmado con los DBC de mods reales que el juego carga; el manual
de carky12 cita ``FE 06``, pero en la práctica el juego necesita ``FF FF`` — verificado 2026-07-02). El juego lo lee
de ``DBDAT\\<nombre_pkf_sin_ext>\\EQ{96|97}{ptr:04d}.DBC`` (p. ej.
``DBDAT\\EQ030022\\EQ970004.DBC``) y entonces ignora ese equipo del PKF.

Al conservar el bloque byte a byte (mismo formato/versión que el PKF origen),
el juego lo parsea igual que parsearía su propio fichero.
"""
from __future__ import annotations

from . import block as B
from . import equipos_pkf as E

DBC_MARKER = b"\xff\xff"  # confirmado con DBCs reales de mods que funcionan
_MARKERS = (b"\xff\xff", b"\xfe\x06")  # el manual citaba FE06; aceptar ambos al leer
_SIG_LEN = E.TEAM_SIG_LEN  # 36


def _stream_block(data, sig_off, next_sig, foreign):
    """Construye el Block caminando el FLUJO de elementos (jugador 01 / entrenador
    02) tras la táctica, buscando el inicio de flujo cuya secuencia consuma hasta
    la firma. Devuelve None si no encuentra un flujo limpio. El entrenador (y todo
    lo previo) queda en el PREFIJO; los jugadores, en la lista. Así los foráneos
    atípicos (entrenador intercalado, Empoli/West Ham/…) se reconstruyen bien."""
    # se prueban todos los inicios candidatos y se elige el que da MÁS jugadores:
    # el flujo REAL consume toda la cola; los falsos inicios dan cadenas cortas
    best = None   # (n_players, o, players, coach_spans, end)
    o = sig_off + E.TEAM_SIG_LEN       # tras la firma; el flujo real está más allá
    while o < next_sig:
        if data[o] not in (0x01, 0x02):
            o += 1
            continue
        res = B.walk_elements(data, o, next_sig, foreign)
        if res is not None and res[0]:
            players, coach_spans, end = res
            if best is None or len(players) > best[0]:
                best = (len(players), o, players, coach_spans, end)
        o += 1
    if best is None:
        return None
    _, o, players, coach_spans, end = best
    coach_bytes = b"".join(bytes(data[a:b]) for a, b in coach_spans)
    prefix = bytes(data[sig_off:o]) + coach_bytes
    trailing = bytes(data[end:next_sig])
    return B.Block(prefix=prefix, players=players, trailing=trailing, foreign=foreign)


def _foreign_stream_start(data, sig, ver) -> int | None:
    """Offset del inicio del FLUJO (tras la táctica) de un bloque FORÁNEO,
    calculado de forma DETERMINISTA como el editor MultiEditorPCC (1Simo1)
    `LeggiSquadra`. Así se reconstruye bien incluso con la zona de entrenador
    degenerada de fábrica (Empoli, West Ham…): el entrenador se conserva INTACTO
    en el prefijo y solo se reemplazan los jugadores."""
    import struct
    try:
        def u16(o):
            return struct.unpack_from("<H", data, o)[0]
        lnc = u16(sig + 42)
        lnst = data[sig + 44 + lnc]
        off = sig + 47 + lnc + lnst
        if ver == 0x20D:           # 525: latitud (v6)
            off += 1
        lnl = u16(off)
        off += lnl + 10
        if ver in (0x20D, 0x1FE):  # 525/510: año del estadio
            off += 4
        off += 2                   # año de fundación
        off += 176 + 7            # táctica dibujada (176) + táctica de equipo (7)
        return off
    except Exception:  # noqa: BLE001
        return None


def _cola_aceptable(data, o: int, next_sig: int) -> bool:
    """¿Es válido lo que queda entre el final del recorrido y la firma siguiente?

    Sí en dos casos. Uno, que no quede casi nada (≤4 bytes de relleno). Y dos —el que faltaba—
    que ahí esté el **terminador del bloque**: PCx-Utils lo tiene escrito como `termP` en
    `Parse/Team.hs` (`teamP = alt <*> termP`, `termP = byteP 0x00`). El equipo TERMINA en ese
    `00`; lo que venga detrás no es suyo.

    Y lo que suele venir detrás es una **página del índice del contenedor**: 1.221 bytes
    (38×32+1+4, la cuenta que documenta `Parse/Pointers.hs`), intercalada entre los datos. Como
    exigíamos consumir hasta la firma siguiente, esos equipos se rechazaban y se caía al parseo
    heurístico —o, si además recuperaba pocos jugadores, al guardarraíl que conserva el equipo
    original—. Medido en `gamedata`, le pasaba a **51 equipos foráneos**: 22 en 6.0 Oro, 12 en
    6.0 original, 11 en 5.0 Oro y 6 en 5.0 original (Milan, Sheffield W., Girondins, Estrella
    Roja, Udinese, Feyenoord, Parma… y el Maribor B, que era el que llegaba al guardarraíl).
    Todos ellos con exactamente 1.222 bytes de cola: el `00` y la página.

    La página se conserva: va en `trailing`, que se vuelve a escribir tal cual en el PKF (el
    round-trip sigue siendo byte a byte) y NO entra en el DBC, que solo lleva prefijo y fichas.
    """
    if next_sig - o <= 4:
        return True
    return 0 <= o < next_sig and data[o] == 0x00


def _foreign_deterministic(data, sig, next_sig, ver):
    """Block de un foráneo por parseo determinista del flujo (entrenador(es) al
    prefijo, jugadores a la lista). Devuelve None si no camina limpio hasta la
    firma (equipo genuinamente roto → el guardarraíl lo excluye)."""
    o0 = _foreign_stream_start(data, sig, ver)
    if o0 is None or not (sig < o0 < next_sig) or data[o0] not in (0x01, 0x02):
        return None
    players, coach_spans, o = [], [], o0
    try:
        while o < next_sig and data[o] in (0x01, 0x02):
            if data[o] == 0x01:
                pl, o = B.parse_player(data, o, True)
                players.append(pl)
            else:
                nxt = B._skip_coach(data, o, True)
                coach_spans.append((o, nxt))
                o = nxt
    except Exception:  # noqa: BLE001
        return None
    if not players or not _cola_aceptable(data, o, next_sig):
        return None
    coach_bytes = b"".join(bytes(data[a:b]) for a, b in coach_spans)
    prefix = bytes(data[sig:o0]) + coach_bytes       # cabecera+táctica + entrenador INTACTO
    return B.Block(prefix=prefix, players=players,
                   trailing=bytes(data[o:next_sig]), foreign=True)


def _national_deterministic(pf: E.EquiposFile, t, next_sig: int):
    """Block de un NACIONAL por parseo DETERMINISTA del flujo, como `LeggiSquadra` de 1Simo1
    (MultiEditorPCC): calcula el inicio del flujo (tras historial + palmarés + táctica) con
    `_stats_offsets` y camina entrenador(es) (0x02) + jugadores (0x01) en orden. Así NO se crea el
    jugador FALSO que el escaneo heurístico generaba DENTRO de las declaraciones de un entrenador
    'largo' (Getafe y similares → block_for_team daba 0 jugadores y el guardarraíl los excluía).
    None si no camina limpio hasta la firma (→ cae al camino antiguo)."""
    data = pf.raw
    so = E._stats_offsets(pf, t)
    if not so:
        return None
    # táctica dibujada = 176 B; táctica de equipo = 7 B. El PALMARÉS cambia de tamaño por versión
    # (1Simo1: 525→42, 505-524→34; PCF5 Oro 500→14): se prueban los 3 y se usa el que camina limpio.
    for plen in (14, 34, 42):
        o0 = so["palmares"] + plen + 176 + 7
        if not (t.sig_off < o0 < next_sig) or data[o0] not in (0x01, 0x02):
            continue
        players, coach_spans, o, clean = [], [], o0, True
        try:
            while o < next_sig and data[o] in (0x01, 0x02):
                if data[o] == 0x01:
                    pl, o = B.parse_player(data, o, False)
                    players.append(pl)
                else:
                    nx = B._skip_coach(data, o, False)
                    coach_spans.append((o, nx))
                    o = nx
        except Exception:  # noqa: BLE001
            clean = False
        if not clean or not players or not _cola_aceptable(data, o, next_sig):
            continue
        coach_bytes = b"".join(bytes(data[a:b]) for a, b in coach_spans)
        prefix = bytes(data[t.sig_off:o0]) + coach_bytes
        return B.Block(prefix=prefix, players=players,
                       trailing=bytes(data[o:next_sig]), foreign=False)
    return None


def block_for_team(pf: E.EquiposFile, tid: int) -> B.Block:
    """Construye el modelo de bloque completo del equipo `tid` desde el buffer actual.

    FORÁNEOS: parseo DETERMINISTA (como el editor de 1Simo1) — el entrenador
    (incluso degenerado de fábrica) se conserva INTACTO en el prefijo y solo se
    reemplazan los jugadores. Resuelve Empoli/West Ham/Vitoria/Grevenmacher/
    Skonto sin crash. El único que no camina limpio (Maribor B) cae al camino
    rápido → el guardarraíl lo excluye."""
    t = pf.teams[tid]
    data = pf.raw
    sigs = sorted(x.sig_off for x in pf.teams)
    next_sig = min([s for s in sigs if s > t.sig_off], default=len(data))
    foreign = E.is_foreign_block(data, t.sig_off, pf.version)
    # El recorrido determinista se intenta SIEMPRE, aunque el pre-escaneo rápido no haya
    # encontrado ni un jugador. Antes se exigía `t.players` y, cuando el escaneo fallaba —pasa
    # con bloques reinyectados por el import y con los gemelos de temporada de 6.0 Oro—, se caía
    # al camino de abajo con `first = next_sig`, que devuelve el equipo SIN PLANTILLA. Eso tenía
    # dos caras feas: al releer un DBC parecía roto uno que estaba bien, y al EXPORTAR se
    # escribía de verdad un equipo sin jugadores, que impide elegir equipo en el juego (mod de
    # foro, 13-sep-2026: 108 equipos así, entre ellos el Real Sociedad B con 31
    # jugadores en el editor). El determinista los lee bien: es el mismo recorrido que hace el
    # juego.
    if foreign:
        ver = int.from_bytes(bytes(data[t.sig_off + 38:t.sig_off + 40]), "little")
        blk = _foreign_deterministic(data, t.sig_off, next_sig, ver)
        if blk is not None:
            return blk
    if not foreign and t.complete:                   # NACIONAL: determinista tipo 1Simo1
        blk = _national_deterministic(pf, t, next_sig)
        if blk is not None:
            return blk
    if t.players:
        first = min(p.offset for p in t.players) - 1  # marcador 01 (gramática)
    else:
        first = next_sig
    return B.parse_block(data, t.sig_off, next_sig, first, foreign)


DBC_PADDING = 16  # relleno a cero final: SIN él, MANAGER.EXE crashea (validado en juego)


def _sin_textos_bbdd(p):
    """Copia del jugador SIN sus textos de base de datos (biografía, palmarés, trayectoria…).

    Es lo que hace el escritor de referencia de la comunidad, **PCx-Utils** (`pcf-v6-bytesteams`,
    función `notxt`): antes de volcar cada DBC vacía todos esos campos, tanto del jugador como
    del entrenador y del club. No es un capricho, y los números dicen por qué: **esos textos son
    el 85% del fichero** — un DBC pasa de 42,7 KB a 6,6 KB sin ellos.

    Importa cuando hay MUCHOS. Bajar la portería a todos los porteros marca ~478 equipos, y el
    juego se los lee todos AL CREAR LIGA: 21 MB de golpe en un motor de 1997 frente a 3,2 MB.
    Un usuario reportó que 6.0 Oro se cerraba con «La aplicación no puede continuar» justo ahí,
    mientras que los amistosos —que no leen estos ficheros— le funcionaban.

    No se pierde nada: los textos siguen en el fichero principal, que también va en la descarga y
    es de donde el juego los lee para la ficha de la base de datos. El DBC solo aporta la
    plantilla y los datos de club.
    """
    import copy
    q = copy.copy(p)
    if getattr(q, "db_strings", None):
        q.db_strings = [b""] * len(q.db_strings)
    return q


def write_dbc(blk: B.Block, con_textos: bool = False) -> bytes:
    """Serializa el bloque como fichero DBC autónomo: puntero → FFFF y relleno
    a cero al final (el lector del juego mira más allá del último jugador).

    Por defecto **sin los textos de base de datos** (ver `_sin_textos_bbdd`)."""
    jugadores = blk.players if con_textos else [_sin_textos_bbdd(p) for p in blk.players]
    body = blk.prefix + b"".join(p.serialize() for p in jugadores)
    out = bytearray(body)
    out[_SIG_LEN:_SIG_LEN + 2] = DBC_MARKER
    return bytes(out) + b"\x00" * DBC_PADDING


def parse_dbc(data: bytes, filename: str = "") -> B.Block:
    """Parsea un fichero DBC. Reutiliza el parser del PKF (misma estructura):
    se restaura temporalmente un puntero neutro donde va el FE06."""
    buf = bytearray(data)
    if bytes(buf[_SIG_LEN:_SIG_LEN + 2]) in _MARKERS:
        buf[_SIG_LEN:_SIG_LEN + 2] = b"\x00\x00"
    pf = E.parse(bytes(buf), filename)
    if not pf.teams:
        raise ValueError("el DBC no contiene un bloque de equipo reconocible")
    blk = block_for_team(pf, 0)
    return blk


def dbc_filename(ver_prefix: str, pointer: int) -> str:
    return f"EQ{ver_prefix}{pointer:04d}.DBC"


def dbc_folder(equipos_filename: str) -> str:
    """Carpeta bajo DBDAT donde el juego busca los DBC: nombre del PKF sin extensión."""
    name = equipos_filename.rsplit("/", 1)[-1]
    return name.rsplit(".", 1)[0].upper()
