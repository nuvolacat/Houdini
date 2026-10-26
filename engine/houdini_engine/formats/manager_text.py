"""Edición de los NOMBRES de competición en manager.exe (cadenas de texto).

A diferencia de las divisiones (arrays de punteros, ver `manager.py`), aquí
editamos las CADENAS visibles: "PRIMERA DIVISIÓN" → "LaLiga", etc.

Claves del formato (validado por reconocimiento del 6.0 Oro, 2026-07-08):
- Las cadenas son C-strings (terminadas en `\\0`) en **texto plano** (NO cifrado),
  codificación **Windows-1252 / latin-1** (acentos en byte alto: Ó=0xD3, Ñ=0xD1,
  ª=0xAA). No van por el XOR 0x61 de los ficheros de datos.
- Cada competición aparece en VARIAS formas: mayúsculas ("PRIMERA DIVISIÓN"),
  minúsculas ("Primera división"), abreviadas ("1ª DIVISIÓN", "C. UEFA"), y
  compuestas de calendario ("LIGA - 1ª DIVISIÓN"). Para renombrar hay que tocar
  TODAS las de su registro.
- **Códigos internos NO editables** (prefijos de fichero .CPT): LIGA1, LIGA2,
  LIGA2B, CEUROPA, CUEFA, CREY… Esos NO están en el schema.

Cada manager.exe es DISTINTO (offsets propios por versión), así que el schema se
resuelve por **búsqueda de contenido**: se localizan las cadenas conocidas allá
donde estén. Lo no encontrado se ignora silenciosamente.

Regla de longitud: una cadena nueva cabe si `len(nueva) <= len(original) + zeros`
donde `zeros` = ceros de relleno tras el terminador (dejando 1 terminador). Al
escribir una cadena más corta se rellena el resto con `\\0`. El caso (MAYÚSCULAS
vs Minúsculas) se AUTODERIVA de cada ocurrencia para conservar el aspecto del
juego.
"""
from __future__ import annotations

from dataclasses import dataclass, field

_ENC = "latin-1"


# --- Schema: competición -> {campo: [cadenas conocidas de ese registro]} --------
# 'name' = nombre completo (huecos ~16-19); 'abbr' = abreviatura (huecos ~7-15).
# Se listan las formas de DISPLAY; los códigos internos .CPT quedan fuera aposta.
COMPETITIONS: list[dict] = [
    {"key": "primera", "label": "Primera División", "fields": {
        "name": ["PRIMERA DIVISIÓN", "PRIMERA DIVISION", "Primera división",
                 "LIGA 1ª DIVISIÓN", "LIGA - 1ª DIVISIÓN"],
        "abbr": ["1ª DIVISIÓN", "1ª DIVISION", "1ª División", "Liga 1ª"],
    }},
    {"key": "segunda", "label": "Segunda División", "fields": {
        "name": ["SEGUNDA DIVISIÓN", "SEGUNDA DIVISION", "Segunda División",
                 "Segunda división", "LIGA 2ª DIVISIÓN", "LIGA - 2ª DIVISIÓN"],
        "abbr": ["2ª DIVISIÓN", "2ª DIVISION", "2ª División", "Liga 2ª"],
    }},
    {"key": "segundab_g1", "label": "Segunda B · Grupo I", "fields": {
        "name": ["SEGUNDA B - GRUPO I", "Segunda B - Grupo I",
                 "SEGUNDA DIVISIÓN B - GRUPO I", "LIGA 2ª DIVISIÓN B - GRUPO I"],
    }},
    {"key": "segundab_g2", "label": "Segunda B · Grupo II", "fields": {
        "name": ["SEGUNDA B - GRUPO II", "Segunda B - Grupo II",
                 "SEGUNDA DIVISIÓN B - GRUPO II", "LIGA 2ª DIVISIÓN B - GRUPO II"],
    }},
    {"key": "segundab_g3", "label": "Segunda B · Grupo III", "fields": {
        "name": ["SEGUNDA B - GRUPO III", "Segunda B - Grupo III",
                 "SEGUNDA DIVISIÓN B - GRUPO III", "LIGA 2ª DIVISIÓN B - GRUPO III"],
    }},
    {"key": "segundab_g4", "label": "Segunda B · Grupo IV", "fields": {
        "name": ["SEGUNDA B - GRUPO IV", "Segunda B - Grupo IV",
                 "SEGUNDA DIVISIÓN B - GRUPO IV", "LIGA 2ª DIVISIÓN B - GRUPO IV"],
    }},
    {"key": "copadelrey", "label": "Copa del Rey", "fields": {
        "name": ["COPA DEL REY", "Copa del Rey"],
    }},
    {"key": "champions", "label": "Copa de Europa (Champions)", "fields": {
        "name": ["COPA DE EUROPA", "Copa de Europa", "Copa Europa"],
        "abbr": ["LIGA CAMP.", "C. DE EUROPA", "C. EUROPA", "C. Europa"],
    }},
    {"key": "uefa", "label": "Copa de la UEFA", "fields": {
        "name": ["COPA DE LA U.E.F.A.", "COPA DE LA UEFA", "Copa de la U.E.F.A.",
                 "Copa de la UEFA"],
        "abbr": ["C. UEFA"],
    }},
    {"key": "recopa", "label": "Recopa", "fields": {
        "name": ["RECOPA DE EUROPA", "Recopa de Europa"],
        "abbr": ["RECOPA", "Recopa"],
    }},
    {"key": "supercopa_eur", "label": "Supercopa de Europa", "fields": {
        "name": ["SUPERCOPA DE EUROPA", "Supercopa de Europa"],
        "abbr": ["SUPERCOPA EUR."],
    }},
    {"key": "supercopa_esp", "label": "Supercopa de España", "fields": {
        "name": ["SUPERCOPA DE ESPAÑA", "Supercopa España"],
        "abbr": ["SUPERCOPA ESP."],
    }},
    {"key": "intercontinental", "label": "Copa Intercontinental", "fields": {
        "name": ["COPA INTERCONTINENTAL", "Copa Intercontinental", "INTERCONTINENTAL"],
        "abbr": ["C. INTERCONT.", "C.INTERCONT.", "Intercont."],
    }},
]


# --- Año de la temporada (constantes u16 LE en el .exe) -------------------------
# Método validado por la comunidad (manual EDIPLUS de TRONIC/PC Futbolpedia): una
# ocurrencia de un año (p.ej. 1997 = CD 07) es una CONSTANTE de calendario real —y
# hay que desplazarla— si cumple AL MENOS UNA: el byte anterior es 0x00 (entrada de
# tabla / `mov` con byte alto 0), o los 2 bytes siguientes son 00 00 (`mov eax,año`).
# Si no, es una coincidencia de código y se deja. Filtra las falsas de las reales.
_YEAR_LO, _YEAR_HI = 1994, 2001

# Año: NO hay heurística universal — cada manager tiene sus propios offsets (lo
# confirma Carky: los editores hardcodean offsets por versión). La misma regla que
# en PCF5 Oro sale BYTE-IDÉNTICA al trucado de la comunidad (validado EN JUEGO),
# en PCF6 Oro rompe la detección del juego (desplaza saltos/aritmética 0x07xx que
# no son años). Por eso el año solo se aplica a managers VALIDADOS por hash.
import hashlib as _hashlib

# sha256 de managers cuyo desplazamiento de año está validado (byte-a-byte contra
# un manager de la comunidad que funciona + probado en juego).
_YEAR_VALIDATED = {
    # PCF 5.0 Oro (validado 2026-07-08: idéntico al trucado + fechas 2018 en juego)
    # (2026-08-15: la regla afinada difiere en 1 sitio — deja INTACTO el JMP
    #  `e9 cc 07` @0x1d2548 que el trucado desplazaba por suerte; más seguro.)
    "5b6f8fcc813234aef1268b1cb6ac1ee0e7fb10f4f83cd6e2653d214d192d003c",
    # PCF 6.0 Oro (2026-08-15): regla corroborada BUILD-CRUZADO — reproduce
    # EXACTOS los 68 sitios del diff comunitario 2017-18↔2k20 (build 2.654.208,
    # mods que FUNCIONAN en juego) y las mismas clases de instrucción aquí
    # (68 sitios tras excluir los 2 saltos Jcc). Pendiente confirmar en VM.
    "b1a9a88a5bf6413d42198ed91bc2d7216c2a26839cbd5b46f48c040dbe866003",
}


def year_validated(data) -> bool:
    """True si el desplazamiento de año está validado para ESTE manager exacto."""
    return _hashlib.sha256(bytes(data)).hexdigest() in _YEAR_VALIDATED


def _is_year_const(data, off: int) -> bool:
    front = off >= 1 and data[off - 1] == 0x00
    back = off + 3 < len(data) and data[off + 2] == 0x00 and data[off + 3] == 0x00
    return front or back


def _is_code_displacement(data, off: int) -> bool:
    """True si el 0x07xx en `off` es un DESPLAZAMIENTO de código (no un año):
    - `E8 xx 07 00 00` = CALL rel32 (el 0x07xx es el destino relativo).
    - `E9 xx 07 00 00` = JMP rel32 (visto en 5.0 Oro @0x1d2548: el trucado de la
      comunidad lo desplazaba POR SUERTE sin romper; se conserva intacto).
    - `0F 8x xx 07 00 00` = Jcc rel32 (JA/JE…). CAZADO 2026-08-15 en 6.0 Oro
      (0x11df42/0x1b16e1): desplazarlos corrompe el flujo → era LO que rompía la
      detección del año en 6.0 Oro.
    - `8D .. 24 xx 07 00 00` = LEA reg,[esp+disp32] (offset de pila).
    Verificado contra la comunidad: en el build 2.654.208 de PCF6 (mods 2017-18 y
    2k20, diff = 68 sitios) esta regla da EXACTAMENTE esos 68; en el pristino del
    CD (2.617.344) y en 6.0 Oro (2.662.400) salen también 68 con las mismas
    clases de instrucción (51× mov [glob],año · 8× cmp [glob],año · 6× mov
    reg,año · 3× mov esi,imm32)."""
    if off >= 1 and data[off - 1] in (0xE8, 0xE9):
        return True
    if off >= 2 and data[off - 2] == 0x0F and 0x80 <= data[off - 1] <= 0x8F:
        return True
    if off >= 3 and data[off - 3] == 0x8D and data[off - 1] == 0x24 and (data[off - 2] & 0xC7) == 0x84:
        return True
    # `MOV r/m32 con disp32` (89/8B + modrm mod=10): el 0x07xx es un DESPLAZAMIENTO de
    # estructura, no un año. Cazados en 5.0 Oro @0x11C9B6 (`89 85 cc07`) y @0x11D3E1
    # (`8b 83 cc07`) — el trucado comunitario los desplazaba POR SUERTE (2026-08-16).
    if off >= 2 and data[off - 2] in (0x88, 0x89, 0x8A, 0x8B) and (data[off - 1] & 0xC0) == 0x80:
        return True
    return False


def _year_offsets(data, year: int) -> list[int]:
    nb = year.to_bytes(2, "little")
    offs, i = [], 0
    while True:
        i = data.find(nb, i)
        if i < 0:
            return offs
        if _is_year_const(data, i) and not _is_code_displacement(data, i):
            offs.append(i)
        i += 1


def detect_base_year(data) -> int:
    """Año base de la temporada del juego. La temporada es base/base+1, así que la
    base es el año MENOR del PAR ADYACENTE con más constantes combinadas (en el
    rango de temporada 1995-1999). PCF6 → 1997 (97/98); PCF5 → 1996 (96/97)."""
    counts = {y: len(_year_offsets(data, y)) for y in range(1995, 2000)}
    best, best_n = 1997, -1
    for y in range(1995, 1999):
        pair = counts.get(y, 0) + counts.get(y + 1, 0)
        if pair > best_n:
            best, best_n = y, pair
    return best


def shift_years(data: bytearray, delta: int, base: int | None = None) -> int:
    """Desplaza las constantes de año de la TEMPORADA {base, base+1} un `delta`
    fijo. Ventana ESTRECHA validada por la comunidad (2026-08-15): los mods de
    PCF6 solo tocan base/base+1 y DEJAN los 19 sitios de 1996 que la regla
    también casaría — y el juego funciona. En 5.0 Oro es equivalente a la
    ventana antigua ±2 (1994/1995/1998 dan 0 sitios). CRÍTICO: NO tocar años
    redondos como 2000/2001 (`push 0x07D0` es constante común, no año)."""
    if base is None:
        base = detect_base_year(bytes(data))
    changed = 0
    for y in (base, base + 1):
        ny = y + delta
        if not (0 <= ny <= 65535):
            continue
        nb = ny.to_bytes(2, "little")
        for off in _year_offsets(data, y):
            data[off:off + 2] = nb
            changed += 1
    return changed


# --- Efecto 2000: rango de año de nacimiento válido -----------------------------
# El manager valida el año de nacimiento contra un rango hardcodeado [1900, 2000]
# (`cmp ebp,1900 … cmp ebp,2000`); los nacidos en 2000+ reciben una edad ALEATORIA.
# Parche de spisemisu/PatchBirthdayPCFV6: ampliar el rango a [1, 65535] → acepta
# cualquier año. Patrón único y estable en PCF5 y PCF6.
_BDAY_PAT = bytes.fromhex("6c 07 00 00 76 08 81 fd d0 07 00 00")  # 1900 … 2000
_BDAY_REP = bytes.fromhex("01 00 00 00 76 08 81 fd ff ff 00 00")  # 1 … 65535


def has_birthday_fix(data) -> bool:
    return _BDAY_PAT in data


def patch_birthday_range(data: bytearray) -> bool:
    """Amplía el rango de año de nacimiento a [1,65535] (corrige el efecto 2000).
    Devuelve True si aplicó el parche."""
    i = data.find(_BDAY_PAT)
    if i < 0:
        return False
    data[i:i + len(_BDAY_REP)] = _BDAY_REP
    return True


@dataclass
class Occurrence:
    offset: int
    original: str
    room: int          # longitud máxima de cadena que cabe aquí (sin contar el \0)


@dataclass
class CompField:
    key: str            # p.ej. "primera"
    label: str
    field: str          # "name" | "abbr"
    current: str        # cadena representativa actual
    max_len: int        # longitud máxima (mínimo room de sus ocurrencias)
    occurrences: list = field(default_factory=list)


def _find_cstring(data: bytes, needle: str):
    """Genera (offset, room) de cada C-string EXACTA `needle` (standalone: el byte
    previo no es imprimible y va seguida de \\0). room = len + ceros - 1."""
    nb = needle.encode(_ENC)
    n, ln = len(data), len(nb)
    i = 0
    while True:
        i = data.find(nb, i)
        if i < 0:
            return
        after = i + ln
        prev_ok = i == 0 or not (0x20 <= data[i - 1] <= 0xFF and data[i - 1] != 0)
        if after < n and data[after] == 0 and prev_ok:
            z = after
            while z < n and data[z] == 0:
                z += 1
            room = ln + (z - after) - 1     # dejar 1 terminador
            yield i, room
        i = after


def scan(data: bytes) -> list[CompField]:
    """Resuelve el schema sobre `data`: devuelve los campos editables encontrados,
    cada uno con sus ocurrencias y la longitud máxima real."""
    out: list[CompField] = []
    for comp in COMPETITIONS:
        for fld, needles in comp["fields"].items():
            occ: list[Occurrence] = []
            for needle in needles:
                for off, room in _find_cstring(data, needle):
                    occ.append(Occurrence(off, needle, room))
            if not occ:
                continue
            # representativa: la primera en registro "bonito" (con minúsculas si hay)
            rep = next((o.original for o in occ if not o.original.isupper()),
                       occ[0].original)
            max_len = min(o.room for o in occ)
            out.append(CompField(comp["key"], comp["label"], fld, rep, max_len, occ))
    return out


def _cased(new: str, original: str) -> str:
    """Adapta el caso del nuevo texto al de la ocurrencia original (MAYÚSCULAS si
    la original iba toda en mayúsculas), para conservar el aspecto del juego."""
    if original.isupper():
        return new.upper()
    return new


def apply(data: bytearray, key: str, fld: str, new_value: str) -> tuple[int, list[str]]:
    """Escribe `new_value` en TODAS las ocurrencias del campo (key, fld). Devuelve
    (nº escritas, avisos de las que no cupieron). Rellena con \\0 el sobrante."""
    new_value = new_value.strip()
    escritas, avisos = 0, []
    comp = next((c for c in COMPETITIONS if c["key"] == key), None)
    if not comp or fld not in comp["fields"]:
        return 0, [f"campo desconocido: {key}/{fld}"]
    for needle in comp["fields"][fld]:
        for off, room in list(_find_cstring(bytes(data), needle)):
            txt = _cased(new_value, needle)
            enc = txt.encode(_ENC, "replace")
            if len(enc) > room:
                avisos.append(f"«{txt}» no cabe en {needle!r} (máx {room})")
                continue
            old_len = len(needle.encode(_ENC))
            # escribir nueva + rellenar a cero hasta cubrir la original + su hueco
            span = old_len + (room - old_len)     # = room (bytes utilizables)
            data[off:off + span + 1] = enc + b"\x00" * (span + 1 - len(enc))
            escritas += 1
    return escritas, avisos
