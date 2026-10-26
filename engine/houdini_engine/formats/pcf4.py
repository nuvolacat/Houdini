"""Formato de equipo de PCF 4.0 / 4.5 — parser + serializer in-place.

A diferencia de v5/v6 (un `EQUIPOS.PKF` con todos los equipos), en la 4.x cada equipo
es su propio fichero `EQ95NNNN.DBC`. Este módulo parsea UN dbc a un modelo editable y
lo re-serializa byte a byte (round-trip perfecto si no se toca nada).

Referencia: FUTBOL_RELOAD (`bbdd_futbol.cpp` = serializar, `mainwindow.cpp
::procesar_datos_equipo` = parsear) y los tutoriales de la comunidad.

"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field

from ..codec import pcf4_text as T

SIG = b"Copyright (c)1995 Dinamic Multimedia"
CABECERA_LEN = 43          # bytes 0x00..0x2A (incluye isBBDD_neg en 0x2A)
OFF_ISBBDD = 0x2A
OFF_TIPO = 0x25

# ---- tablas de referencia para el editor (del PDF PCF40-TUTORIAL + FUTBOL_RELOAD) ----
ROLES = {                  # demarcaciones (rol preferido 1-18; 00 = ninguna)
    0x00: "Ninguna", 0x01: "Portero", 0x02: "Lateral derecho", 0x03: "Lateral izquierdo",
    0x04: "Líbero", 0x05: "Central izquierdo", 0x06: "Central derecho",
    0x07: "Volante derecho", 0x08: "Interior derecho", 0x09: "Delantero centro",
    0x0A: "Volante tapón", 0x0B: "Volante izquierdo", 0x0C: "Extremo derecho",
    0x0D: "Media punta centro", 0x0E: "Extremo izquierdo", 0x0F: "Marcador central def.",
    0x10: "Media punta derecha", 0x11: "Media punta izquierda", 0x12: "Interior izquierdo",
}
POSITIONS = {0: "Portero", 1: "Defensa", 2: "Volante", 3: "Delantero"}
MAX_PLAYERS = 35           # slots 1..40 en disco; dejamos margen como en 5/6
SKIN = {0: "Blanco", 1: "Negro", 2: "Mulato"}
HAIR = {0: "Rubio", 1: "Calvo", 2: "Negro", 3: "Canoso", 4: "Rojo", 5: "Castaño"}
SIGNING = {0: "Sin cambio", 1: "Nuevo fichaje", 2: "Cantera"}
# Tabla de países (referencia: FUTBOL_RELOAD). El 0x20 figuraba allí como "República
# Checa" y ahí están el Oporto, el Benfica y el Sporting. Corregido a Portugal con doble
# evidencia (2026-08-26): los equipos que hay dentro, y la propia tabla del juego —40
# países en claro en `PCMANAG.DAT` desde 0x0A1100, donde el índice 32 es Portugal.
#
# OJO, la base agrupa: en el 0x20 Dinamic metió también a los checos (Sparta, Slavia, Hradec) y
# a los irlandeses (Dundalk, Derry City, Shelbourne). Pasa igual en el 0x14 (ingleses +
# norirlandeses), el 0x16 (islandeses + feroeses) y el 0x1D (noruegos + galeses). El juego SÍ
# distingue esos países —los tiene con nombre propio en su tabla—, así que la base los mete
# donde no van; no hay código propio para ellos y la correspondencia exacta sigue sin cerrar.
COUNTRIES = {
    0x01: "Albania", 0x02: "Alemania", 0x03: "Austria", 0x04: "Bélgica",
    0x05: "Bielorrusia", 0x06: "Bulgaria", 0x07: "Croacia", 0x09: "Chipre",
    0x0A: "Dinamarca", 0x0B: "Escocia", 0x0C: "Eslovaquia", 0x0D: "Eslovenia",
    0x0E: "España", 0x0F: "Finlandia", 0x10: "Francia", 0x11: "Grecia",
    0x12: "Países Bajos", 0x13: "Hungría", 0x14: "Inglaterra", 0x16: "Islas Feroe",
    0x18: "Israel", 0x19: "Italia", 0x1A: "Lituania", 0x1B: "Luxemburgo",
    0x1C: "Malta", 0x1D: "Noruega", 0x1F: "Polonia", 0x20: "Portugal",
    0x22: "Rumanía", 0x23: "Rusia", 0x24: "Suecia", 0x25: "Suiza",
    # 0x28 es YUGOSLAVIA, no Serbia: así lo llama el juego en su propia tabla y así se
    # llamaba en 1995. No es cosmético — el catálogo de fuentes deja FUERA a Serbia (51)
    # a propósito, porque esos clubes viven bajo Yugoslavia (58), así que con el nombre
    # moderno el país apuntaba a un puntero sin fuente y su equipo no se actualizaba nunca.
    0x26: "Turquía", 0x27: "Ucrania", 0x28: "Yugoslavia", 0x29: "Argentina",
}


def player_average(p) -> float:
    """Media del jugador = (VE+RE+AG+CA)/4 (igual que v5/v6)."""
    return (p.speed + p.stamina + p.aggression + p.quality) / 4


# Posición de la fuente de datos (nombre plegado) → (position 0..3, role_pref 1..18) de PCF4.
TM_POSITION = {
    "portero": (0, 0x01), "goalkeeper": (0, 0x01),
    "defensacentral": (1, 0x05), "centreback": (1, 0x05), "centralback": (1, 0x05),
    "defensa": (1, 0x05), "libero": (1, 0x04), "sweeper": (1, 0x04),
    "lateralderecho": (1, 0x02), "rightback": (1, 0x02),
    "lateralizquierdo": (1, 0x03), "leftback": (1, 0x03),
    "pivote": (2, 0x0A), "mediocentrodefensivo": (2, 0x0A), "defensivemidfield": (2, 0x0A),
    "mediocentro": (2, 0x07), "centralmidfield": (2, 0x07), "mediocampista": (2, 0x07),
    "mediapunta": (2, 0x0D), "attackingmidfield": (2, 0x0D),
    "mediocentroofensivo": (2, 0x0D),
    "interiorderecho": (2, 0x08), "interiorizquierdo": (2, 0x12),
    # extremos = atacantes en el fútbol moderno → delantero (para un once coherente)
    "extremoderecho": (3, 0x0C), "rightwinger": (3, 0x0C), "rightmidfield": (2, 0x07),
    "extremoizquierdo": (3, 0x0E), "leftwinger": (3, 0x0E), "leftmidfield": (2, 0x0B),
    "extremo": (3, 0x0C),
    "delantero": (3, 0x09), "delanterocentro": (3, 0x09), "centreforward": (3, 0x09),
    "segundodelantero": (3, 0x0D), "secondstriker": (3, 0x0D), "striker": (3, 0x09),
}


def new_player(pointer: int, slot: int, short_name: str, long_name: str,
               position: int, role_pref: int, nationality: int,
               medias: tuple[int, int, int, int],
               skills: tuple[int, int, int, int] = (0, 0, 0, 0),
               birth_date: bytes = b"\x00\x00\x00", height: int = 0, weight: int = 0,
               skin: int = 0, hair: int = 5, has_bbdd: bool = True) -> Player:
    """Construye un Player válido para volcar en un equipo (import masivo)."""
    ve, re_, ag, ca = (max(1, min(99, v)) for v in medias)
    p = Player(
        pointer=pointer, short_name=short_name, long_name=long_name,
        slot=slot, slot2=slot, signing_state=0, role_pref=role_pref,
        roles_sec=b"\x00\x00\x00\x00\x00", nationality=nationality,
        skin=skin, hair=hair, position=position,
        speed=ve, stamina=re_, aggression=ag, quality=ca,
        sk_technique=skills[0], sk_shot=skills[1], sk_pass=skills[2], sk_kick=skills[3],
        birth_date=birth_date, height=height, weight=weight, has_bbdd=has_bbdd,
    )
    if has_bbdd:
        # los campos pequeños de BBDD deben ir RELLENOS (un jugador NUEVO con todo
        # vacío peta el juego; los mods que funcionan ponen birth_place/origin/inter
        # con algo y international="0"). El comentario largo sí va vacío (troceado válido).
        p.birth_place = p.birth_place or "-"
        p.origin_team = p.origin_team or "-"
        p.international = p.international or "0"
        p._comment_orig, p._comment_raw = "￿", b""
    return p


# La estructura de ligas (qué equipo está en cada división) NO se deduce del tid:
# el juego la guarda en PCMANAG.DAT como una tabla ordenada de 96 registros de 4 bytes
# (u16 tid, u16 = 0), en el MISMO orden que muestra la pantalla de clasificación del
# juego, terminada en 0xFFFF. Es la temporada 95-96 (Primera de 22 equipos).
# Los cortes entre divisiones no van marcados en la tabla: son los tamaños de liga.
_DIV_SIZES = ((22, "Primera División"), (20, "Segunda División"), (54, "Segunda B"))


def parse_division_order(pcmanag: bytes) -> list[int] | None:
    """Tids (1..96) en el orden de la tabla de clasificación de PCMANAG.DAT."""
    off = _find_division_order_off(pcmanag)
    if off is None:
        return None
    return [int.from_bytes(pcmanag[off + k * 4:off + k * 4 + 2], "little")
            for k in range(96)]


def _find_division_order_off(pcmanag: bytes) -> int | None:
    """Offset de la tabla de clasificación de PCMANAG.DAT: 96×u32 que forman una
    PERMUTACIÓN de 1..96 (hi=0) terminada en 0xFFFF. Sin anclar al primer tid
    (tras mover equipos de división el orden puede empezar por cualquiera)."""
    N = 96
    end = len(pcmanag) - N * 4 - 2
    for off in range(0, end, 2):
        lo0 = int.from_bytes(pcmanag[off:off + 2], "little")
        if not (1 <= lo0 <= N):
            continue
        ok = True
        vistos = set()
        for k in range(N):
            lo = int.from_bytes(pcmanag[off + k * 4:off + k * 4 + 2], "little")
            hi = int.from_bytes(pcmanag[off + k * 4 + 2:off + k * 4 + 4], "little")
            if hi != 0 or not (1 <= lo <= N) or lo in vistos:
                ok = False
                break
            vistos.add(lo)
        if ok and int.from_bytes(pcmanag[off + N * 4:off + N * 4 + 2], "little") == 0xFFFF:
            return off
    return None


def set_division_order(pcmanag: bytes, order: list[int]) -> bytes:
    """Reescribe la tabla de clasificación (el orden define las divisiones por
    tamaños 22/20/54). IN-PLACE, mismo tamaño. VALIDAR EN JUEGO."""
    off = _find_division_order_off(pcmanag)
    if off is None or len(order) != 96 or len(set(order)) != 96:
        return pcmanag
    b = bytearray(pcmanag)
    for k, tid in enumerate(order):
        b[off + k * 4:off + k * 4 + 2] = int(tid).to_bytes(2, "little")
        b[off + k * 4 + 2:off + k * 4 + 4] = b"\x00\x00"
    return bytes(b)


# --- FILIALES (equipos que NO pueden ascender) ---------------------------------------------
# El manager (PCMANAG.DAT / PROMANAG.DAT) marca los filiales por tid HARDCODEADO en el código:
# de fábrica 26/28/34 (Castilla, Barça B, Athletic B). En dos bloques por fichero (un chequeo
# externo sobre el top-4 de la tabla de clasificación + el swap interno que lo baja de la zona
# de ascenso) hay instrucciones `cmp dword [reg+tabla_clasif], tid` → 6 inmediatos por fichero
# (2 por cada uno de los 3 filiales). Reasignar = cambiar esos inmediatos (imm8 sign-extendido;
# los tid 1..96 caben de sobra). Slot sin usar → inmediato 0: los tid reales van de 1..96, así
# que `cmp tabla[x], 0` no casa nunca → ese slot no afecta a ningún equipo (equivale a "sin
# filial"). Contra la tabla de clasificación SOLO se comparan estos 3 IDs (verificado) → cero
# daños colaterales. Se localiza por PATRÓN (no por offset fijo) → vale igual para PCMANAG y
# PROMANAG y es robusto a un fichero ya reordenado por divisiones. Cap del juego = 3 filiales
# (más requeriría inyección de código). VALIDAR EN JUEGO.
import re as _re


def _filial_triples(mgr: bytes, last_jcc: bytes) -> dict[tuple[int, tuple[int, int, int]], int]:
    """Bloques de 3 `cmp [reg+D], imm8` con MISMO disp32 D, cada uno seguido de je (0x74),
    salvo el 3º seguido de `last_jcc`. Devuelve {(disp, (a,b,c)): offset}."""
    rx = _re.compile(
        rb'\x83[\xB8-\xBF](....)(.)\x74.'
        rb'\x83[\xB8-\xBF](....)(.)\x74.'
        rb'\x83[\xB8-\xBF](....)(.)' + last_jcc + rb'.', _re.DOTALL)
    out: dict = {}
    for m in rx.finditer(mgr):
        if m.group(1) == m.group(3) == m.group(5):        # mismo disp32 → misma tabla
            out[(int.from_bytes(m.group(1), "little"),
                 (m.group(2)[0], m.group(4)[0], m.group(6)[0]))] = m.start()
    return out


# Filiales DE FÁBRICA de PCF 4.0 (fijos del juego): Castilla=26, Barça B=28, Athletic B=34.
# Hay OTRO bloque je/je/jne adyacente con ids (1,4,12) sobre otra tabla (equipos concretos, NO
# filiales) → hay que anclar en estos IDs para no confundirlos. La descarga parchea SIEMPRE
# desde el PCMANAG/PROMANAG original, así que el bloque siempre trae 26/28/34.
_FILIAL_FACTORY = (26, 28, 34)


def _find_filial_block(mgr: bytes) -> tuple[int, tuple[int, int, int]] | None:
    """Localiza el bloque de filiales: el mecanismo aparece DOS veces con el mismo (disp32 de la
    tabla de clasificación, 3 tid) — chequeo EXTERNO del top-4 (je·je·JNE) y swap INTERNO
    (je·je·JE) — y sus 3 tid son los filiales de fábrica (26/28/34). Ese doble criterio lo
    distingue del bloque adyacente (1,4,12). Devuelve (disp, (a,b,c)) o None."""
    outer = _filial_triples(mgr, b'\x75')                  # je · je · jne (chequeo externo)
    inner = _filial_triples(mgr, b'\x74')                  # je · je · je  (swap interno)
    fac = frozenset(_FILIAL_FACTORY)
    for disp, ids in outer:
        if (disp, ids) in inner and frozenset(ids) == fac:  # doble aparición + IDs de filial
            return disp, ids
    return None


def filial_tids(mgr: bytes) -> list[int]:
    """Los tid de filial ACTUALES del manager (los que están hardcodeados ahora), sin el 0
    (slots neutralizados). Vacío si no se localiza el bloque."""
    found = _find_filial_block(mgr)
    return [t for t in found[1] if t] if found else []


# --- CODE CAVE: bloqueo de ascenso de N filiales (sin límite de 3) ---------------------------
# El mecanismo de fábrica compara SOLO 3 tids hardcodeados. Para bloquear N equipos (los que
# detecte el sistema de filiales por nombre) inyectamos un "code cave" en el SLACK ejecutable al
# final del objeto de código (OBJ1) del ejecutable LE (DOS4GW): un bucle inline que compara la
# posición del top-4 de Segunda contra N tids y, si casa, salta al CALL del swap (que ya está
# validado en juego). Hacen falta DOS caves: el EXTERIOR (decide llamar al swap) y el INTERIOR
# (dentro del swap, salta filiales al buscar con quién intercambiar) — si no, con N>3 el swap
# podría meter a otro filial en zona de ascenso. Direccionamiento: la tabla (0x20A74) es absoluta
# y conocida; los saltos entre cave y bloque son RELATIVOS y, al estar en el MISMO objeto (delta
# archivo↔runtime constante), se calculan con offsets de FICHERO. Registros: el cave solo usa el
# reg de índice ya cargado (eax exterior / ebx interior) → nada que preservar.
_MAX_FILIALES = 96                       # tope práctico (caben de sobra en el slack)


def _le_obj1_slack(mgr: bytes):
    """(offset_fichero, size) del slack ejecutable al final de OBJ1 (código) del ejecutable LE.
    None si no es LE o no hay slack. El slack son las páginas cargadas más allá de `vsize` de
    OBJ1: memoria ejecutable, cargada y sin usar → segura para el cave."""
    import struct
    if len(mgr) < 0x40:
        return None
    e = struct.unpack_from("<I", mgr, 0x3C)[0]
    if mgr[e:e + 2] != b"LE":
        return None
    page_size = struct.unpack_from("<I", mgr, e + 0x28)[0]
    data_pages = struct.unpack_from("<I", mgr, e + 0x80)[0]
    obj_tab = struct.unpack_from("<I", mgr, e + 0x40)[0]
    vsize, base, flags, page_idx, page_cnt, _r = struct.unpack_from("<IIIIII", mgr, e + obj_tab)
    if not (flags & 0x4):                # OBJ1 debe ser ejecutable
        return None
    obj1_file = data_pages + (page_idx - 1) * page_size
    slack_file = obj1_file + vsize                       # borde de vsize (runtime) en fichero
    obj1_end = obj1_file + page_cnt * page_size          # fin de las páginas de OBJ1
    size = obj1_end - slack_file
    return (slack_file, size) if size > 64 else None


def _filial_blocks(mgr: bytes):
    """Localiza los DOS bloques de comprobación de filial (exterior je/je/JNE y swap interior
    je/je/JE) con IDs de fábrica. Devuelve (disp, outer, inner) donde:
      outer = (start, call_site, loop_back)   # start..call_site = región a sustituir
      inner = (start, next_off, do_swap)      # start..do_swap  = región a sustituir
    o None. Cada bloque = 3×[cmp(7)+jcc(2)] = 27 bytes."""
    def _sread(o):                       # rel8 con signo del jcc en offset o+1
        v = mgr[o + 1]
        return v - 256 if v >= 128 else v
    outer_t = _filial_triples(mgr, b"\x75")
    inner_t = _filial_triples(mgr, b"\x74")
    fac = frozenset(_FILIAL_FACTORY)
    for (disp, ids), o_start in outer_t.items():
        if (disp, ids) not in inner_t or frozenset(ids) != fac:
            continue
        i_start = inner_t[(disp, ids)]
        o_jne = o_start + 25                             # 3º jcc del bloque exterior (JNE)
        outer = (o_start, o_jne + 2, o_jne + 2 + _sread(o_jne))       # start, call_site, loop_back
        i_je0 = i_start + 7                              # 1er jcc del bloque interior (JE)
        inner = (i_start, i_start + 27, i_je0 + 2 + _sread(i_je0))    # start, do_swap, next_off
        return disp, outer, inner
    return None


def _cave_bytes(tids, disp: int, reg_modrm: int, hit: int, miss: int, at: int) -> bytes:
    """Bucle inline: por cada tid `cmp [reg+disp], tid ; je hit`, y al final `jmp miss`.
    `at` = offset de FICHERO donde arranca el cave (para calcular los rel32)."""
    import struct
    out = bytearray()
    pos = at
    for t in tids:
        out += bytes([0x83, reg_modrm]) + struct.pack("<I", disp) + bytes([t & 0xFF])  # cmp (7)
        pos += 7
        out += bytes([0x0F, 0x84]) + struct.pack("<i", hit - (pos + 6))                # je rel32 (6)
        pos += 6
    out += bytes([0xE9]) + struct.pack("<i", miss - (pos + 5))                         # jmp rel32 (5)
    return bytes(out)


# TERCERA comprobación de filial (2026-08-30). Además de los dos bloques que usan la tabla de
# clasificación (`cmp dword [reg+disp32], imm8`), hay una rutina de BÚSQUEDA DE CANDIDATO que
# compara el id contra un REGISTRO:
#
#     83 FE 1A 74 ..      cmp esi, 0x1a · je (descartar y seguir buscando)
#     83 FE 1C 74 ..      cmp esi, 0x1c · je
#     83 FE 22 0F 84 ..   cmp esi, 0x22 · je  (salto largo)
#
# Está en PCMANAG.DAT y en PROMANAG.DAT, en los cuatro ejecutables que tenemos. **Se nos había
# quedado sin parchear**, y eso explica el síntoma que reportó la comunidad al tocar solo las
# otras dos: el objetivo del equipo pasaba de «Ascenso» a «Zona alta» pero el filial seguía sin
# subir, porque esta tercera seguía descartándolo.
#
# Aquí no cabe un cave: se sustituyen los tres inmediatos. Con la lista vacía se escribe 0xFF en
# los tres, que con `83 /7 ib` se extiende con signo a -1 y no coincide con ningún equipo real
# (los tid van de 1 a 96), así que la rutina deja de descartar a nadie.
_FILIAL_REG = _re.compile(rb"\x83([\xF8-\xFF])\x1a\x74.\x83\1\x1c\x74.\x83\1\x22", _re.DOTALL)
_SIN_FILIAL = 0xFF


def filial_reg_offsets(mgr: bytes) -> list[int]:
    """Offsets de los TRES inmediatos de la rutina de búsqueda de candidato, o lista vacía."""
    m = _FILIAL_REG.search(mgr)
    return [m.start() + 2, m.start() + 7, m.start() + 12] if m else []


def _patch_filial_reg(b: bytearray, tids: list[int]) -> None:
    offs = filial_reg_offsets(bytes(b))
    if not offs:
        return
    for k, off in enumerate(offs):
        b[off] = tids[k] if k < len(tids) else _SIN_FILIAL


def set_filiales(mgr: bytes, tids: list[int]) -> bytes:
    """Fija los equipos que NO pueden ascender de Segunda a Primera. `tids`: lista de tid (1..96),
    SIN límite práctico (code cave). Lista vacía = ninguno (todos ascienden). Inyecta un cave en el
    slack de OBJ1 y desvía los dos bloques de comprobación de filial hacia él. Mismo tamaño de
    fichero. Vale para PCMANAG.DAT y PROMANAG.DAT. Si no es LE o no localiza el bloque, no toca nada.
    VALIDAR EN JUEGO (foco: cambio de temporada)."""
    import struct
    blocks = _filial_blocks(mgr)
    slack = _le_obj1_slack(mgr)
    if not blocks or not slack:
        return mgr
    disp, outer, inner = blocks
    slack_file, slack_size = slack
    seen: set = set()
    lst = [t for t in (int(x) for x in tids) if 1 <= t <= 96 and not (t in seen or seen.add(t))]
    lst = lst[:_MAX_FILIALES]
    b = bytearray(mgr)
    cave1 = slack_file + 16                               # margen tras el borde de vsize
    c1 = _cave_bytes(lst, disp, 0xB8, outer[1], outer[2], cave1)   # EXTERIOR: eax; hit=call, miss=loop
    cave2 = cave1 + len(c1)
    c2 = _cave_bytes(lst, disp, 0xBB, inner[2], inner[1], cave2)   # INTERIOR: ebx; hit=next, miss=do_swap
    if (cave2 - slack_file) + len(c2) + 16 > slack_size:          # no cabe (N enorme) → no tocar
        return mgr
    b[cave1:cave1 + len(c1)] = c1
    b[cave2:cave2 + len(c2)] = c2

    def _divert(start, end, cave):                       # start..end → jmp cave + NOPs
        b[start:start + 5] = bytes([0xE9]) + struct.pack("<i", cave - (start + 5))
        for i in range(start + 5, end):
            b[i] = 0x90
    _divert(outer[0], outer[1], cave1)                   # exterior: start..call_site
    _divert(inner[0], inner[1], cave2)                   # interior: start..do_swap
    _patch_filial_reg(b, lst)                            # y la tercera, la de buscar candidato
    return bytes(b)


def division_map(pcmanag: bytes | None) -> dict[int, str]:
    """tid (0001..0096) -> nombre de división, leído de la tabla real del juego.
    Si no se puede leer PCMANAG.DAT, cae a un reparto por tamaños sobre 1..96."""
    order = parse_division_order(pcmanag) if pcmanag else None
    if order is None:
        order = list(range(1, 97))     # respaldo: orden natural de tids
    out: dict[int, str] = {}
    i = 0
    for count, name in _DIV_SIZES:
        for t in order[i:i + count]:
            out[t] = name
        i += count
    return out


def spain_division(tid: int, dmap: dict[int, str] | None = None) -> str:
    """División de un equipo español. Con `dmap` (de division_map) usa la tabla real
    del juego; sin él, cae a un reparto aproximado por tamaños de liga."""
    n = tid % 10000            # 0001..0096
    if dmap is not None:
        return dmap.get(n, "Especiales")
    if 1 <= n <= 22:
        return "Primera División"
    if 23 <= n <= 42:
        return "Segunda División"
    if 43 <= n <= 96:
        return "Segunda B"
    return "Especiales"        # 9900 Estrellas Mundiales, etc.


# ---------------------------------------------------------------- modelos
@dataclass
class Coach:
    pointer: int
    short_name: str
    long_name: str = ""
    info: str = ""            # texto BBDD (troceado)
    declarations: str = ""    # texto BBDD (troceado)
    has_bbdd: bool = True
    # bytes originales de los troceados (el troceado de Dinamic no coincide con el
    # re-encode de FUTBOL_RELOAD → preservamos crudo salvo edición)
    _info_orig: str = ""
    _info_raw: bytes = b""
    _decl_orig: str = ""
    _decl_raw: bytes = b""


@dataclass
class Player:
    pointer: int
    short_name: str
    long_name: str
    slot: int                 # posición en el plantel (1-40, único)
    slot2: int                # 2ª aparición del slot (recuadro 10; casi siempre = slot)
    signing_state: int        # 0 seguía / 1 fichaje / 2 cantera
    role_pref: int            # rol preferido 1-18
    roles_sec: bytes          # 5 bytes de roles secundarios
    nationality: int          # 0 nacional / 1 extranjero
    skin: int                 # 0 blanco / 1 negro / 2 mulato
    hair: int                 # 0..5
    position: int             # 0 arquero / 1 def / 2 volante / 3 delantero
    # medias visibles (VE RE AG CA → media = (VE+RE+AG+CA)/4)
    speed: int = 0            # Velocidad (VE)
    stamina: int = 0          # Resistencia (RE)
    aggression: int = 0       # Agresividad (AG)
    quality: int = 0          # Calidad (CA)
    # skills ocultos (booleanos 0/1)
    sk_technique: int = 0
    sk_shot: int = 0
    sk_pass: int = 0
    sk_kick: int = 0
    # datos de BBDD (solo si has_bbdd)
    birth_place: str = ""
    birth_date: bytes = b"\x00\x00\x00"   # día, mes, año
    origin_team: str = ""
    international: str = ""
    height: int = 0
    weight: int = 0
    comment: str = ""
    price: int = 0
    has_bbdd: bool = True
    _comment_orig: str = ""
    _comment_raw: bytes = b""


@dataclass
class Team:
    cabecera: bytes           # 43 bytes opacos (firma + puntero + versión…)
    pais: int
    name_long: str
    name_short: str
    name_upper: str
    unk5: bytes = b""         # 5 bytes (solo bbdd)
    founded: int = 0          # año fundación (solo bbdd)
    stadium: str = ""
    capacity: int = 0
    members: int = 0          # nº socios (solo bbdd)
    president: str = ""       # solo bbdd
    budget_db: int = 0        # solo bbdd
    budget_game: int = 0      # solo bbdd
    sponsor: str = ""         # solo bbdd
    supplier: str = ""        # solo bbdd
    bytes10: bytes = b""      # 10 bytes (solo bbdd)
    name_short_upper: str = ""
    cosas_bbdd: bytes = b""   # TÁCTICA dibujada (176 B) + historial/palmarés (opaco)
    coaches: list[Coach] = field(default_factory=list)
    players: list[Player] = field(default_factory=list)
    terminator: bytes = b"\x00"   # 0x00(s) de fin de fichero

    @property
    def has_bbdd(self) -> bool:
        return self.cabecera[OFF_ISBBDD] == 0


def escudo_pos(t: Team) -> tuple[int, int, int]:
    """Posición en pantalla del escudo grande (BIGESC) — los 5 bytes `unk5` (solo equipos con
    BBDD). `+0 u16 LE` X, `+2 u16 LE` Y, `+4 u8` byte extra (0-9). Ident. FUTBOL_RELOAD/pcfutbolmania."""
    b = t.unk5
    if len(b) < 5:
        return (0, 0, 0)
    return (b[0] | (b[1] << 8), b[2] | (b[3] << 8), b[4])


def set_escudo_pos(t: Team, x: int | None = None, y: int | None = None,
                   extra: int | None = None) -> None:
    """Reescribe la posición del escudo en `unk5` conservando los bytes no tocados."""
    b = bytearray(t.unk5 if len(t.unk5) >= 5 else b"\x00" * 5)
    if x is not None:
        b[0], b[1] = x & 0xFF, (x >> 8) & 0xFF
    if y is not None:
        b[2], b[3] = y & 0xFF, (y >> 8) & 0xFF
    if extra is not None:
        b[4] = extra & 0xFF
    t.unk5 = bytes(b)


def last_decade(t: Team) -> list[int]:
    """Puestos finales de las últimas 10 temporadas (`bytes10`; 0x3F=63 = sin dato/no participó).
    Equivale al `lastdecade` del PKF de v5/6. Solo equipos con BBDD."""
    return list(t.bytes10) if len(t.bytes10) == 10 else []


def set_last_decade_pos(t: Team, i: int, v: int) -> None:
    """Reescribe el puesto de la temporada `i` (0-9) en `bytes10` (round-trip byte-perfecto)."""
    if len(t.bytes10) != 10 or not (0 <= i < 10):
        return
    b = bytearray(t.bytes10)
    b[i] = v & 0xFF
    t.bytes10 = bytes(b)


# ---------------------------------------------------------------- parser
def _u32(d, o):
    return d[o] | d[o + 1] << 8 | d[o + 2] << 16 | d[o + 3] << 24


def _dc(data, o):
    """decode_chunked que también devuelve los bytes crudos: (texto, raw, next)."""
    s, o2 = T.decode_chunked(data, o)
    return s, data[o:o2], o2


def _emit_chunked(text: str, orig: str, raw: bytes) -> bytes:
    """Emite el troceado crudo si no cambió; si se editó, re-encodea."""
    return raw if text == orig else T.encode_chunked(text)


def _parse_coach(data: bytes, o: int, has_bbdd: bool) -> tuple[Coach, int]:
    assert data[o] == 0x02
    o += 1
    ptr = struct.unpack_from("<H", data, o)[0]; o += 2
    short, o = T.decode_str(data, o)
    c = Coach(pointer=ptr, short_name=short, has_bbdd=has_bbdd)
    if has_bbdd:
        c.long_name, o = T.decode_str(data, o)
        c.info, c._info_raw, o = _dc(data, o); c._info_orig = c.info
        c.declarations, c._decl_raw, o = _dc(data, o); c._decl_orig = c.declarations
    assert data[o] == 0x00
    o += 1
    return c, o


def _parse_player(data: bytes, o: int, has_bbdd: bool) -> tuple[Player, int]:
    assert data[o] == 0x01
    o += 1
    ptr = struct.unpack_from("<H", data, o)[0]; o += 2
    short, o = T.decode_str(data, o)
    long_, o = T.decode_str(data, o)
    slot = data[o]; o += 1
    signing = data[o]; o += 1
    role_pref = data[o]; o += 1
    roles_sec = data[o:o + 5]; o += 5
    slot2 = data[o]; o += 1         # slot repetido (recuadro 10)
    assert data[o] == 0x00; o += 1  # separador
    nationality = data[o]; o += 1
    skin = data[o]; o += 1
    hair = data[o]; o += 1
    position = data[o]; o += 1
    p = Player(pointer=ptr, short_name=short, long_name=long_, slot=slot, slot2=slot2,
               signing_state=signing, role_pref=role_pref, roles_sec=roles_sec,
               nationality=nationality, skin=skin, hair=hair, position=position,
               has_bbdd=has_bbdd)
    if has_bbdd:
        p.birth_place, o = T.decode_str(data, o)
        p.birth_date = data[o:o + 3]; o += 3
        p.origin_team, o = T.decode_str(data, o)
        p.international, o = T.decode_str(data, o)
        p.height = data[o]; o += 1
        p.weight = data[o]; o += 1
        p.comment, p._comment_raw, o = _dc(data, o); p._comment_orig = p.comment
        p.price = struct.unpack_from("<H", data, o)[0]; o += 2
    p.speed, p.stamina, p.aggression, p.quality = data[o], data[o+1], data[o+2], data[o+3]
    o += 4
    p.sk_technique, p.sk_shot, p.sk_pass, p.sk_kick = data[o], data[o+1], data[o+2], data[o+3]
    o += 4
    assert data[o] == 0x00; o += 1  # separador de jugador
    return p, o


def _plausible(s: str) -> bool:
    """¿La cadena parece un nombre real (no bytes basura de cosas_bbdd)?"""
    if not s:
        return False
    for ch in s:
        o = ord(ch)
        if not (0x20 <= o < 0x7F or 0xA0 <= o < 0x100):
            return False
    return True


def _try_players(data: bytes, o: int, has_bbdd: bool):
    """Parsea una cadena de jugadores 0x01 hasta EOF (resto = ceros). Exige nombres
    plausibles y slot 1-40 → descarta 0x01 casuales dentro de cosas_bbdd.
    Devuelve (players, terminator) o None."""
    try:
        players = []
        while o < len(data) and data[o] == 0x01:
            p, o = _parse_player(data, o, has_bbdd)
            if not (_plausible(p.short_name) and 1 <= p.slot <= 40):
                return None
            players.append(p)
        rest = data[o:]
        if players and all(b == 0 for b in rest):
            return players, rest
    except (IndexError, AssertionError, struct.error):
        pass
    return None


def _coach_ok(c: Coach) -> bool:
    """El apellido del entrenador va con inicial en mayúscula (p.ej. "Cruyff") →
    descarta un 0x02 casual de cosas_bbdd cuyo "nombre" son bytes basura."""
    s = c.short_name
    return bool(s) and _plausible(s) and (s[0].isupper() or ord(s[0]) >= 0xC0)


def _try_coaches(data: bytes, o: int, has_bbdd: bool, stop: int):
    """Parsea entrenadores 0x02 que terminen EXACTAMENTE en `stop`. [] si o==stop."""
    if o == stop:
        return []
    try:
        coaches = []
        while o < stop and data[o] == 0x02:
            c, o = _parse_coach(data, o, has_bbdd)
            if not _coach_ok(c):
                return None
            coaches.append(c)
        if o == stop and coaches:
            return coaches
    except (IndexError, AssertionError, struct.error):
        pass
    return None


def parse(data: bytes) -> Team:
    """Parsea un fichero DBC de equipo de la 4.x."""
    if not data.startswith(SIG[:13]):
        raise ValueError("no es un DBC de PCF 4.x (firma)")
    cabecera = data[:CABECERA_LEN]
    has_bbdd = cabecera[OFF_ISBBDD] == 0
    o = CABECERA_LEN
    pais = data[o]; o += 1
    name_long, o = T.decode_str(data, o)
    name_short, o = T.decode_str(data, o)
    name_upper, o = T.decode_str(data, o)
    t = Team(cabecera=cabecera, pais=pais, name_long=name_long,
             name_short=name_short, name_upper=name_upper)
    if has_bbdd:
        t.unk5 = data[o:o + 5]; o += 5
        t.founded = struct.unpack_from("<H", data, o)[0]; o += 2
    t.stadium, o = T.decode_str(data, o)
    t.capacity = _u32(data, o); o += 4
    if has_bbdd:
        t.members = _u32(data, o); o += 4
        t.president, o = T.decode_str(data, o)
        t.budget_db = _u32(data, o); o += 4
        t.budget_game = _u32(data, o); o += 4
        t.sponsor, o = T.decode_str(data, o)
        t.supplier, o = T.decode_str(data, o)
        t.bytes10 = data[o:o + 10]; o += 10
    t.name_short_upper, o = T.decode_str(data, o)
    header_end = o
    # 1) localizar el inicio de la sección de JUGADORES (nombres legibles + slot
    #    válido = fiable, evita 0x01 casuales dentro de cosas_bbdd).
    pstart = None
    for start in range(header_end, len(data)):
        if data[start] != 0x01:
            continue
        res = _try_players(data, start, has_bbdd)
        if res:
            pstart, (t.players, t.terminator) = start, res
            break
    if pstart is None:
        # foráneos (isBBDD_neg): cosas_bbdd FIJA de 177 bytes; entrenador (nombre
        # puede ir vacío) + jugadores opcionales + ceros. Puede no haber jugadores.
        if not has_bbdd:
            cstart = header_end + 177
            try:
                o2 = cstart
                coaches, players = [], []
                while o2 < len(data) and data[o2] == 0x02:
                    c, o2 = _parse_coach(data, o2, False)
                    coaches.append(c)
                while o2 < len(data) and data[o2] == 0x01:
                    p, o2 = _parse_player(data, o2, False)
                    players.append(p)
                if all(b == 0 for b in data[o2:]):
                    t.cosas_bbdd = data[header_end:cstart]
                    t.coaches, t.players, t.terminator = coaches, players, data[o2:]
                    return t
            except (IndexError, AssertionError, struct.error):
                pass
        raise ValueError("no se encontró la sección de jugadores")
    # 2) los ENTRENADORES son los registros 0x02 justo antes de los jugadores.
    for cstart in range(header_end, pstart + 1):
        if cstart != pstart and data[cstart] != 0x02:
            continue
        coaches = _try_coaches(data, cstart, has_bbdd, pstart)
        if coaches is not None:
            t.coaches = coaches
            t.cosas_bbdd = data[header_end:cstart]
            return t
    # sin entrenadores: cosas_bbdd llega hasta los jugadores
    t.cosas_bbdd = data[header_end:pstart]
    return t


# ---------------------------------------------------------------- serializer
# ---- TÁCTICA DIBUJADA (descubierta 2026-08-16) ----------------------------------
# Los primeros 176 bytes de `cosas_bbdd` NO son historial: son la MISMA táctica de
# v5/6 (11 jugadores × 8 u16: zona + posición defendiendo + posición atacando), pero
# en CASILLAS de una rejilla 16×9 en vez de píxeles. Evidencia: los 235 DBC de la base
# cumplen los 88 invariantes `xMin ≤ x ≤ xMin+ancho` (imposible por azar) y el registro
# del portero es byte-idéntico en los 235: zona x[0..2] y[3..6], posición (0,4) = línea
# de gol, centrado. Hay 66 dibujos distintos. Ni FUTBOL_RELOAD ni nuestra spec lo habían
# identificado (él lo guardaba como "bloque compartido de Segunda B").
PITCH_CELLS = (16.0, 9.0)


def _pcf4_presets() -> dict:
    from .. import refdata
    return {x["Nom"]: bytes.fromhex(x["Hex"]) for x in refdata.pcf4_tactics()}


def tactic_preset_names() -> list[str]:
    return list(_pcf4_presets())


def get_tactic_name(t: "Team") -> str | None:
    """Nombre de la formación si el dibujo coincide con una de las 6 del juego."""
    blob = (t.cosas_bbdd or b"")[:176]
    for nom, b in _pcf4_presets().items():
        if blob == b:
            return nom
    return None


def set_tactic_preset(t: "Team", name: str) -> None:
    """Reemplaza el DIBUJO por el de una formación estándar (los otros bytes de
    `cosas_bbdd` —el historial— se conservan intactos)."""
    b = _pcf4_presets().get(name)
    if b is None or len(t.cosas_bbdd or b"") < 176:
        raise KeyError(name)
    t.cosas_bbdd = b + t.cosas_bbdd[176:]


def set_tactic_position(t: "Team", j: int, x: float, y: float,
                        which: str = "nat") -> None:
    """Mueve al jugador `j` (0-10) del dibujo a la casilla (x, y) de la rejilla 16×9.

    PCF4 guarda CASILLAS, no píxeles, así que el punto llega ya en esa escala. Los 176 B
    del dibujo se reescriben en el sitio y el resto de `cosas_bbdd` (el historial) no se
    toca."""
    from ..tactics import shift_player
    blob = (t.cosas_bbdd or b"")[:176]
    if len(blob) < 176:
        raise KeyError("este equipo no tiene táctica dibujada")
    # aquí el bloque está COMPLETO en el fichero (no hay cabecera implícita como en v5/6),
    # así que el portero también puede moverse a lo largo
    nuevo = shift_player(blob, j, x, y, PITCH_CELLS[0], PITCH_CELLS[1],
                         keep_x0=False, which=which)
    t.cosas_bbdd = nuevo + t.cosas_bbdd[176:]


def tactic_shape(t: "Team") -> list[dict]:
    """Las 11 posiciones de la táctica del equipo, normalizadas a 0..1."""
    from ..tactics import decode_shape
    blob = (t.cosas_bbdd or b"")[:176]
    if len(blob) < 176:
        return []
    return decode_shape(blob, PITCH_CELLS[0], PITCH_CELLS[1], cell=True)


def _u32b(v: int) -> bytes:
    return struct.pack("<I", v & 0xFFFFFFFF)


def _ser_coach(c: Coach) -> bytes:
    out = bytearray([0x02])
    out += struct.pack("<H", c.pointer)
    out += T.encode_str(c.short_name)
    if c.has_bbdd:
        out += T.encode_str(c.long_name)
        out += _emit_chunked(c.info, c._info_orig, c._info_raw)
        out += _emit_chunked(c.declarations, c._decl_orig, c._decl_raw)
    out += b"\x00"
    return bytes(out)


def _ser_player(p: Player) -> bytes:
    out = bytearray([0x01])
    out += struct.pack("<H", p.pointer)
    out += T.encode_str(p.short_name)
    out += T.encode_str(p.long_name)
    out += bytes([p.slot, p.signing_state, p.role_pref])
    out += p.roles_sec
    out += bytes([p.slot2, 0x00, p.nationality, p.skin, p.hair, p.position])
    if p.has_bbdd:
        out += T.encode_str(p.birth_place)
        out += p.birth_date
        out += T.encode_str(p.origin_team)
        out += T.encode_str(p.international)
        out += bytes([p.height, p.weight])
        out += _emit_chunked(p.comment, p._comment_orig, p._comment_raw)
        out += struct.pack("<H", p.price)
    out += bytes([p.speed, p.stamina, p.aggression, p.quality])
    out += bytes([p.sk_technique, p.sk_shot, p.sk_pass, p.sk_kick])
    out += b"\x00"
    return bytes(out)


def serialize(t: Team) -> bytes:
    out = bytearray()
    out += t.cabecera
    out += bytes([t.pais])
    out += T.encode_str(t.name_long)
    out += T.encode_str(t.name_short)
    out += T.encode_str(t.name_upper)
    if t.has_bbdd:
        out += t.unk5
        out += struct.pack("<H", t.founded)
    out += T.encode_str(t.stadium)
    out += _u32b(t.capacity)
    if t.has_bbdd:
        out += _u32b(t.members)
        out += T.encode_str(t.president)
        out += _u32b(t.budget_db)
        out += _u32b(t.budget_game)
        out += T.encode_str(t.sponsor)
        out += T.encode_str(t.supplier)
        out += t.bytes10
    out += T.encode_str(t.name_short_upper)
    out += t.cosas_bbdd
    for c in t.coaches:
        out += _ser_coach(c)
    for p in t.players:
        out += _ser_player(p)
    out += t.terminator
    return bytes(out)
