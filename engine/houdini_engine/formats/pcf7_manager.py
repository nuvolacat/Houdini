"""PCF 7 — `MANAGER.EXE`: divisiones jugables y año de inicio de temporada.

Las 14 divisiones de los 5 países jugables (Euro PCF) son arrays de u16 con
punteros de equipo en orden de clasificación (ids del `EQ99022.FDI`). Offsets de
fichero (= RVA; verificados). Tamaños por los constructores del manager + realidad
98/99. 

El **año de inicio de temporada** es una global limpia: struct fecha en `0x8C8B5C`
(año u16), `0x8C8B5E` (día u8), `0x8C8B5F` (mes u8), inicializado a 23-ago-1999 por
3 escritores `mov word [0x8C8B5C], 1999`. Cambiarlo reapunta el arranque de liga y
—como la edad = año − añoNacimiento— habilita las edades reales. VALIDAR EN JUEGO.
"""
from __future__ import annotations

import struct

# (país refdata, etiqueta, offset de fichero, nº de equipos) — temporada 99
DIVISIONS: list[tuple[int, str, int, int]] = [
    # España (22)
    (22, "Primera División", 0x49F058, 20),
    (22, "Segunda División", 0x49F190, 22),
    (22, "Segunda B · Grupo I", 0x49F254, 20),
    (22, "Segunda B · Grupo II", 0x49F27C, 20),
    (22, "Segunda B · Grupo III", 0x49F2A4, 20),
    (22, "Segunda B · Grupo IV", 0x49F2CC, 20),
    # Inglaterra (30)
    (30, "Premier League", 0x49D994, 20),
    (30, "First Division", 0x49D6A0, 24),
    (30, "Second Division", 0x49DA6C, 24),
    (30, "Third Division", 0x49DBC4, 24),
    # Italia (36)
    (36, "Serie A", 0x49E294, 18),
    (36, "Serie B", 0x49E3E8, 20),
    (36, "Serie C1 · Girone A", 0x49E490, 18),
    (36, "Serie C1 · Girone B", 0x49E4B4, 18),
    # Alemania (2)
    (2, "Bundesliga 1", 0x4A0370, 18),
    (2, "Bundesliga 2", 0x4A03F4, 18),
    # Francia (24)
    (24, "Ligue 1", 0x4A0108, 18),
    (24, "Ligue 2", 0x4A01A8, 20),
]

# países con ligas jugables (se les habilita la navegación por divisiones)
PLAYABLE_COUNTRIES = (22, 30, 36, 2, 24)

# struct de fecha de inicio de temporada — es una GLOBAL en memoria (VA, NO offset de
# fichero): año u16 @ VA 0x8C8B5C, día @ 0x8C8B5E, mes @ 0x8C8B5F. Se inicializa a
# 23-ago-1999 en runtime. Para EDITARLA se parchean los INMEDIATOS de los 3 escritores
# `66 c7 05 <addr32=5c8b8c00> <imm16>`: el imm16 va +4 tras la dirección (que aparece
# como bytes en 0xB0F0/0xB1D8/0x2EB4C5 del fichero). Verificado: los 3 valen 1999.
_YEAR_WRITE_IMM = (0xB0F0 + 4, 0xB1D8 + 4, 0x2EB4C5 + 4)


def division_map(manager: bytes) -> dict[int, tuple[int, str]]:
    """{código de equipo → (país, etiqueta de división)} para los 5 países jugables."""
    out: dict[int, tuple[int, str]] = {}
    for pais, label, off, n in DIVISIONS:
        for i in range(n):
            code = struct.unpack_from("<H", manager, off + i * 2)[0]
            if code and code not in out:      # 1ª aparición manda (evita duplicados de relleno)
                out[code] = (pais, label)
    return out


def divisions_of_country(pais: int) -> list[str]:
    """Etiquetas de división de un país jugable, en orden."""
    return [label for p, label, _, _ in DIVISIONS if p == pais]


# (país, etiqueta) -> (offset de fichero, nº de plazas)
_DIV_OFFSET: dict[tuple[int, str], tuple[int, int]] = {
    (p, label): (off, n) for p, label, off, n in DIVISIONS}


def read_divisions(manager: bytes) -> list[tuple[int, str, list[int]]]:
    """Tablas de división ORDENADAS del MANAGER.EXE: [(país, etiqueta, [códigos])]."""
    import struct as _s
    out = []
    n = len(manager)
    for pais, label, base, count in DIVISIONS:
        if base + count * 2 > n:
            continue
        codes = [_s.unpack_from("<H", manager, base + i * 2)[0] for i in range(count)]
        out.append((pais, label, [c for c in codes if c and c != 0xFFFF]))
    return out


# Alias de etiquetas de división: la fuente puede nombrarlas distinto que el MANAGER.EXE
# (Inglaterra: "Division One/Two/Three" ≡ "First/Second/Third Division"). Se normalizan.
_DIV_ALIASES: dict[tuple[int, str], str] = {
    (30, "Division One"): "First Division",
    (30, "Division Two"): "Second Division",
    (30, "Division Three"): "Third Division",
    (30, "Championship"): "First Division",
    (30, "League One"): "Second Division",
    (30, "League Two"): "Third Division",
}


def _div_offset(pais: int, label: str) -> tuple[int, int] | None:
    key = (pais, label)
    if key in _DIV_OFFSET:
        return _DIV_OFFSET[key]
    alt = _DIV_ALIASES.get(key)
    if alt is not None and (pais, alt) in _DIV_OFFSET:
        return _DIV_OFFSET[(pais, alt)]
    return None


def set_divisions(manager: bytes, tables: list[tuple[int, str, list[int]]]) -> bytes:
    """Reescribe las tablas de división del MANAGER.EXE. `tables` = lista de
    (país, etiqueta, [códigos en orden de clasificación]). Escribe cada array u16
    in-place en su offset; rellena hasta el nº de plazas y pone 0 en las que sobren.
    NO cambia el tamaño del binario (in-place). Una división cuya etiqueta NO casa con
    ninguna tabla conocida del binario se OMITE (no rompe la descarga). VALIDAR EN JUEGO."""
    b = bytearray(manager)
    # Escribe SOLO las plazas con equipo real. Las que sobran se DEJAN con un equipo válido de la
    # base, NUNCA a 0: el código 0 no existe → el juego CRASHEA al entrar en la división (pasaba
    # con divisiones foráneas incompletas, p.ej. la Third Division inglesa). Todas las tablas a la
    # vez, para que un equipo no acabe en dos divisiones: ver `rellena_divisiones`.
    escribir = []
    for pais, label, codes in tables:
        slot = _div_offset(pais, label)
        if slot is None:
            continue    # división desconocida para este MANAGER.EXE → se ignora
        off, n = slot
        escribir.append((off, n, codes))
    escribe_divisiones(b, escribir)
    return bytes(b)


# ── CALENDARIO (solo PCF2001) ────────────────────────────────────────────────────────────
#
# El calendario de las ligas EXTRANJERAS de 2001 no es una tabla de datos: es CÓDIGO. El
# ejecutable trae instrucciones `mov word [dir], <id>` que rellenan el cuadro de partidos, y el
# id del equipo va como inmediato dentro de cada instrucción. Por eso, al recolocar una liga,
# la tabla quedaba con los equipos nuevos y el calendario seguía emparejando a los de 1999-2000:
# el fixture citaba clubes que ya no jugaban esa liga.
#
# La tabla de offsets (`refdata/pcf2001_calendario.json`) no se incluye en este repositorio:
# si no está, el calendario no se toca.
#
# España y Argentina NO tienen calendario compilado —su liga la sortea el juego al empezar—, así
# que no aparecen aquí y no se toca nada suyo.
_CALENDARIO: dict | None = None


def _calendario() -> dict:
    """{offset base de la división: [[offsets de calendario] por plaza]}."""
    global _CALENDARIO
    if _CALENDARIO is None:
        import json
        import pathlib
        f = pathlib.Path(__file__).parent.parent / "refdata" / "pcf2001_calendario.json"
        try:
            _CALENDARIO = {int(k): v for k, v in json.loads(f.read_text(encoding="utf-8")).items()}
        except Exception:  # noqa: BLE001
            _CALENDARIO = {}
    return _CALENDARIO


# Plazas de las COPAS QUE JUEGAN TODOS LOS CLUBES DE UNA DIVISIÓN (Copa del Rey, F.A. Cup,
# Copa de la Liga, y las de Italia, Francia y Alemania). Cada edición registra aquí las suyas
# —PCF7 desde `FDI_TABLES`, 2000 y 2001 desde `FDI_EUROCUPS`— y la clave es el TAMAÑO de su
# manager.exe, como en el resto del módulo.
#
# Para qué: al recolocar divisiones, un club que baja a 2ªB seguía jugando la Copa del Rey y el
# que subía no aparecía. Las copas de Alemania y Francia sí se arrastraban, pero solo porque son
# copia BYTE A BYTE de su liga y `escribe_divisiones` las encuentra buscando esos mismos bytes;
# la Copa del Rey (42 clubes de dos divisiones, en otro orden) o la F.A. Cup (124, con las
# inferiores) no se encuentran así y se quedaban con los equipos viejos.
CUP_SLOTS: dict[int, list[int]] = {}


def _clubes_en(b: bytearray, tablas) -> set:
    """Los clubes que hoy ocupan las divisiones que se van a reescribir."""
    out = set()
    for off, n, *_ in tablas:
        for i in range(n):
            if off + i * 2 + 2 <= len(b):
                c = struct.unpack_from("<H", b, off + i * 2)[0]
                if c and c != 0xFFFF:
                    out.add(c)
    return out


def _cambia_en_copas(b: bytearray, salen: list, entran: list) -> None:
    """Mete en las copas a los clubes que ENTRAN en la división y saca a los que SALEN.

    Va por MEMBRESÍA, no plaza a plaza. Es la diferencia entre que funcione y que destroce la
    copa: si se sustituyera plaza a plaza mientras se escribe la liga, una simple reordenación
    —que es lo normal, el orden de la liga cambia cada temporada— encadenaría los cambios (la
    plaza 1 pasa de A a B, así que toda A se vuelve B; luego la plaza 2 pasa de B a C y arrastra
    también las que acaban de escribirse) y la copa se quedaría con cuatro equipos. Medido: una
    rotación de Primera sacaba de la Copa del Rey a casi todos.

    Al club que se va se le pone el que ocupa su lugar, allí donde figure. Se lee TODO antes de
    escribir nada, y se respeta el orden propio de la copa (las rondas) y que un club pueda
    aparecer en más de una plaza."""
    if not (salen and entran):
        return
    cambio = dict(zip(sorted(salen), sorted(entran)))
    for co in CUP_SLOTS.get(len(b), ()):
        if co + 2 > len(b):
            continue
        nuevo = cambio.get(struct.unpack_from("<H", b, co)[0])
        if nuevo is not None:
            struct.pack_into("<H", b, co, nuevo)


def _pon_plaza(b: bytearray, off: int, i: int, code: int) -> None:
    """Pone el equipo en su plaza de liga Y en su calendario. (Las copas NO se tocan aquí: van
    al final, comparando quién entra y quién sale — ver `_cambia_en_copas`.)

    El guardarraíl va POR PLAZA y se comprueba en el momento: solo se escribe en un offset de
    calendario si HOY tiene el mismo id que la plaza que se está cambiando. Con eso, un build
    distinto, una liga ya tocada a mano o un offset que no fuera lo que creemos no se escriben
    nunca — en el peor caso el calendario se queda como estaba, que es lo de antes."""
    pos = off + i * 2
    if pos + 2 > len(b):
        return
    actual = struct.unpack_from("<H", b, pos)[0]
    struct.pack_into("<H", b, pos, code)
    if actual == code:
        return
    plazas = _calendario().get(off)
    if not plazas or i >= len(plazas):
        return
    for co in plazas[i]:
        if 0 <= co and co + 2 <= len(b) and struct.unpack_from("<H", b, co)[0] == actual:
            struct.pack_into("<H", b, co, code)


def rellena_divisiones(b: bytearray, tablas) -> None:
    """Escribe TODAS las tablas de división de una vez: `tablas` = [(offset, plazas, códigos)].

    Hace falta verlas juntas porque `rellena_tabla` solo evita repetir un equipo DENTRO de su
    tabla. Cuando la fuente no llena una división, sus plazas libres se quedaban con el equipo
    de fábrica… que el plan ya había colocado en OTRA división. En un mod real de 2001 salieron
    **30 equipos en dos divisiones a la vez** —el Huesca en 2ªB y en Tercera— y el juego
    respondía «La aplicación no puede continuar» (foro, 14-sep-2026).

    Reglas:
    · Solo se escribe en las plazas que traen equipo DE FÁBRICA. Los grupos de Tercera de 2001
      tienen hueco para 22 y Dinamic juega con 20 (los dos últimos a 0); llenar esos dos
      cambiaba el tamaño de la división, y las divisiones no cambian de tamaño.
    · Primera pasada: los equipos del plan, en orden, en sus plazas. Los que no caben (el plan
      trae más que las plazas vivas) quedan de reserva.
    · Segunda pasada: cada plaza sin equipo conserva el de fábrica SI no juega ya en ninguna
      división; si juega, recibe uno de la reserva — primero los del plan que se quedaron sin
      sitio, luego los de fábrica que no están colocados en ningún lado.
    · Nunca 0: el código 0 no existe y cuelga el juego. Si no queda nadie en la reserva, la
      plaza conserva su equipo de fábrica aunque se repita (último recurso)."""
    tabs = []
    for off, n, codes in tablas:
        fabrica = list(struct.unpack_from(f"<{n}H", bytes(b[off:off + n * 2])))
        vivas = [i for i, c in enumerate(fabrica) if c and c != 0xFFFF]
        tabs.append((off, n, [int(c) & 0xFFFF for c in codes if c], fabrica, vivas))
    puestos: set = set()
    reserva: list = []
    pendientes = []                      # (off, índice, código de fábrica)
    for off, n, codes, fabrica, vivas in tabs:
        for k, i in enumerate(vivas):
            if k < len(codes) and codes[k] not in puestos:
                _pon_plaza(b, off, i, codes[k])
                puestos.add(codes[k])
            else:
                pendientes.append((off, i, fabrica[i]))
        reserva += [c for c in codes[len(vivas):] if c not in puestos]
    reserva += [c for _o, _n, _c, fabrica, vivas in tabs for c in (fabrica[i] for i in vivas)]
    r = 0
    for off, i, de_fabrica in pendientes:
        if de_fabrica not in puestos:
            elegido = de_fabrica
        else:
            while r < len(reserva) and reserva[r] in puestos:
                r += 1
            elegido = reserva[r] if r < len(reserva) else de_fabrica
        _pon_plaza(b, off, i, elegido)
        puestos.add(elegido)


def escribe_divisiones(b: bytearray, escribir) -> None:
    """Rellena todas las divisiones (`rellena_divisiones`) y lleva cada cambio a sus copias de
    copa nacional (`_replica`). `escribir` = [(offset, plazas, códigos)].

    Las copias se LOCALIZAN ANTES de tocar nada. Buscándolas después, la tabla nueva de una
    división podía coincidir con la ORIGINAL de otra —basta con que el plan suba a Primera a
    toda la Segunda de fábrica— y la copia la pisaba: dos divisiones idénticas."""
    vivos = {off for off, _n, _c in escribir}
    copias = []
    for off, n, _codes in escribir:
        original = bytes(b[off:off + n * 2])
        pos, i = [], b.find(original)
        while i >= 0:
            if i not in vivos:
                pos.append(i)
            i = b.find(original, i + 1)
        copias.append((off, n, original, pos))
    antes = _clubes_en(b, escribir)
    rellena_divisiones(b, escribir)
    _cambia_en_copas(b, sorted(antes - _clubes_en(b, escribir)),
                     sorted(_clubes_en(b, escribir) - antes))
    for off, n, original, pos in copias:
        nuevo = bytes(b[off:off + n * 2])
        if nuevo != original:
            for i in pos:
                b[i:i + n * 2] = nuevo


def rellena_tabla(b: bytearray, off: int, n: int, codes) -> None:
    """Escribe una tabla de división de `n` plazas con los equipos de `codes`.

    Las plazas que el plan no llena **conservan su equipo de fábrica**, porque dejarlas a 0
    cuelga el juego (el código 0 no existe). Pero ese equipo de fábrica puede estar YA colocado
    en otra plaza de la MISMA tabla, y entonces queda duplicado: un club enfrentado a sí mismo,
    y el juego revienta al crear la partida — no al entrar en esa división, sino al construir
    todas las competiciones, así que el usuario lo ve jugando a España y sin pistas.

    Pasó de verdad: Ligue 2 de PCF7, 20 plazas y un plan de 18; las dos plazas libres se
    rellenaron con los de fábrica (Sochaux y Montpellier) y el Montpellier ya estaba en la
    plaza 7 (mod de un usuario, 12-sep-2026). Ahora, si el de fábrica ya juega, se coge OTRO de los
    que esa misma tabla tenía de fábrica y se han quedado sin sitio. Solo si no queda ninguno
    se repite, que sigue siendo mejor que un 0."""
    fabrica = list(struct.unpack_from(f"<{n}H", bytes(b[off:off + n * 2])))
    puestos = {int(c) & 0xFFFF for c in codes[:n] if c}
    reserva = [c for c in fabrica if c and c not in puestos]
    k = 0
    for i in range(n):
        code = codes[i] if i < len(codes) else 0
        if code:
            struct.pack_into("<H", b, off + i * 2, int(code) & 0xFFFF)
            continue
        actual = fabrica[i]
        if actual and actual not in puestos:
            puestos.add(actual)          # el de fábrica sirve: se deja como está
            continue
        while k < len(reserva) and reserva[k] in puestos:
            k += 1
        if k < len(reserva):             # su equipo de fábrica ya juega → otro de la tabla
            struct.pack_into("<H", b, off + i * 2, reserva[k])
            puestos.add(reserva[k])
            k += 1


def _replica(b: bytearray, original: bytes, nuevo: bytes, saltar: int) -> int:
    """Escribe el mismo cambio allí donde esa misma lista de equipos vuelva a aparecer.

    CORRECCIÓN (2026-08-18): esas repeticiones NO son divisiones duplicadas, como creí al
    encontrarlas. Son las **copas nacionales**, que coinciden con la liga porque las
    disputan todos los clubes de la división: 0x4A0090 es la Copa de Francia y 0x4A0488 la
    de Alemania (offsets de josewolf22, verificados). Las inglesas viven dentro de un bloque
    mayor que incluye hasta la Conference.

    Por eso sincronizarlas sigue siendo lo correcto: si un club cambia de división, cambia
    también la ronda de copa a la que entra. Se busca la secuencia ORIGINAL completa y se
    sustituye entera; casar N códigos seguidos (36-48 bytes) no puede pisar otra cosa."""
    if original == nuevo:
        return 0
    hechas = 0
    i = b.find(original)
    while i >= 0:
        if i != saltar:
            b[i:i + len(nuevo)] = nuevo
            hechas += 1
        i = b.find(original, i + 1)
    return hechas


# --------------------------------------------------------------------------------
# NOMBRES DE COMPETICIÓN (texto plano NUL-terminado en el MANAGER.EXE de PCF7)
# Editor AUTOCONTENIDO (PCF7 es distinto de v5/6): búsqueda de contenido + reescritura
# in-place respetando el hueco. El mod de la comunidad NO renombra → EXPERIMENTAL,
# validar en la VM. 
# --------------------------------------------------------------------------------
_ENC = "latin-1"

# (clave, etiqueta, {campo: [formas conocidas de la cadena]}). 'name' = rótulo largo,
# 'abbr' = sigla. Solo se listan formas que existen NUL-terminadas en el binario.
COMPETITIONS: list[dict] = [
    {"key": "primera", "label": "Primera División (España)",
     "fields": {"name": ["PRIMERA DIVISIÓN", "Primera división"], "abbr": ["Primera"]}},
    {"key": "segunda", "label": "Segunda División (España)",
     "fields": {"name": ["SEGUNDA DIVISIÓN", "Segunda división"], "abbr": ["Segunda"]}},
    {"key": "segundab_i", "label": "2ªB Grupo I", "fields": {"name": ["2ªB-I"], "abbr": ["2B I"]}},
    {"key": "segundab_ii", "label": "2ªB Grupo II", "fields": {"name": ["2ªB-II"], "abbr": ["2B II"]}},
    {"key": "segundab_iii", "label": "2ªB Grupo III", "fields": {"name": ["2ªB-III"], "abbr": ["2B III"]}},
    {"key": "segundab_iv", "label": "2ªB Grupo IV", "fields": {"name": ["2ªB-IV"], "abbr": ["2B IV"]}},
    {"key": "premier", "label": "Premier League (Inglaterra)",
     "fields": {"name": ["PREMIER LEAGUE", "Premier League"], "abbr": ["Premier"]}},
    {"key": "first", "label": "First Division (Inglaterra)",
     "fields": {"name": ["FIRST DIVISION"], "abbr": ["First"]}},
    {"key": "second", "label": "Second Division (Inglaterra)",
     "fields": {"name": ["SECOND DIVISION"], "abbr": ["Second"]}},
    {"key": "third", "label": "Third Division (Inglaterra)",
     "fields": {"name": ["THIRD DIVISION"], "abbr": ["Third"]}},
    {"key": "seriea", "label": "Serie A (Italia)", "fields": {"name": ["SERIE A", "Serie A"]}},
    {"key": "serieb", "label": "Serie B (Italia)", "fields": {"name": ["SERIE B", "Serie B"]}},
    {"key": "c1a", "label": "Serie C1-A (Italia)", "fields": {"name": ["C1-A"]}},
    {"key": "c1b", "label": "Serie C1-B (Italia)", "fields": {"name": ["C1-B"]}},
    {"key": "bundes1", "label": "Bundesliga 1 (Alemania)",
     "fields": {"name": ["BUNDESLIGA 1", "Bundesliga 1"]}},
    {"key": "bundes2", "label": "Bundesliga 2 (Alemania)", "fields": {"name": ["Bundesliga 2"]}},
    {"key": "ligue1", "label": "Ligue 1 (Francia)", "fields": {"name": ["Division 1"]}},
    {"key": "ligue2", "label": "Ligue 2 (Francia)", "fields": {"name": ["Division 2"]}},
    {"key": "copadelrey", "label": "Copa del Rey", "fields": {"name": ["COPA DEL REY", "Copa del Rey"]}},
    {"key": "supercopa_esp", "label": "Supercopa de España",
     "fields": {"name": ["SUPERCOPA DE ESPAÑA", "Supercopa de España"]}},
    {"key": "supercopa_eur", "label": "Supercopa de Europa",
     "fields": {"name": ["SUPERCOPA DE EUROPA", "Supercopa de Europa"]}},
    {"key": "intercontinental", "label": "Copa Intercontinental",
     "fields": {"name": ["COPA INTERCONTINENTAL", "Copa Intercontinental"]}},
    {"key": "ceuropa", "label": "Copa de Europa",
     "fields": {"name": ["COPA DE EUROPA", "Copa de Europa"]}},
    {"key": "uefa7", "label": "Copa de la UEFA",
     "fields": {"name": ["COPA DE LA UEFA", "Copa de la UEFA"]}},
    {"key": "recopa", "label": "Recopa", "fields": {"name": ["RECOPA", "Recopa"]}},
]


def _find_cstring(data: bytes, needle: str):
    """(offset, room) de cada C-string EXACTA `needle` NUL-terminada (standalone: el
    byte previo no es imprimible). room = longitud máxima escribible (sin el \\0)."""
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
            yield i, ln + (z - after) - 1     # dejar 1 terminador
        i = after


def _cased(new: str, original: str) -> str:
    return new.upper() if original.isupper() else new


def competition_fields(manager: bytes, overrides: dict | None = None) -> list[dict]:
    """Campos de nombre editables encontrados en el manager. `overrides` = {key/field:
    valor} de la sesión. Devuelve la forma que espera la UI (misma que v5/6)."""
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


def _rename_in_prose(data: bytearray, needle: str, val: str) -> int:
    """Renombra `needle` también DENTRO de textos corridos (ayudas, frases tipo
    'ganador de la Copa Intercontinental.'), como hacen los mods de la comunidad
    (PCF7 19-20 renombra el rótulo Y las frases). La cadena contenedora se
    RECONSTRUYE dentro de su propio hueco NUL-terminado (no se desplaza nada
    fuera): si el texto nuevo no cabe en el hueco, se deja como está."""
    nb = needle.encode(_ENC)
    enc = _cased(val.strip(), needle).encode(_ENC, "replace")
    n = len(data)
    changed, i = 0, 0
    while True:
        i = bytes(data).find(nb, i)
        if i < 0:
            return changed
        after = i + len(nb)
        # solo apariciones EMBEBIDAS (las standalone ya las cubre _find_cstring)
        if not (i > 0 and 0x20 <= data[i - 1] <= 0xFF and data[i - 1] != 0):
            i = after
            continue
        # cadena contenedora: retroceder/avanzar hasta NUL; todo imprimible
        s = i
        while s > 0 and data[s - 1] != 0 and 0x09 <= data[s - 1] <= 0xFF:
            s -= 1
        e = after
        while e < n and data[e] != 0 and 0x09 <= data[e] <= 0xFF:
            e += 1
        if e >= n or data[e] != 0 or e - s > 4096:
            i = after
            continue
        z = e
        while z < n and data[z] == 0:
            z += 1
        room = (z - s) - 1                       # hueco total (dejar 1 terminador)
        nuevo = bytes(data[s:i]) + enc + bytes(data[after:e])
        if len(nuevo) > room:
            i = after
            continue
        data[s:s + room + 1] = nuevo + b"\x00" * (room + 1 - len(nuevo))
        changed += 1
        i = s + len(nuevo)


def apply_competitions(manager: bytes, overrides: dict) -> bytes:
    """Aplica todos los overrides {key/field: valor} al binario (in-place, respetando
    el hueco). Cubre el rótulo standalone Y las menciones dentro de textos corridos
    (mismo alcance que los mods de la comunidad). Devuelve el manager parcheado."""
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
                if fld == "name" and len(needle) >= 8:     # prosa solo con nombres largos
                    _rename_in_prose(data, needle, val)    # (evita falsos con siglas)
    return bytes(data)


def read_start_year(manager: bytes) -> int:
    """Año de inicio de temporada, leído del inmediato del 1er escritor."""
    return struct.unpack_from("<H", manager, _YEAR_WRITE_IMM[0])[0]


# loaders que CARGAN la fecha del objeto de partida y pisaban el año nuevo con 1999:
# 'mov dword [0x8C8B5C], ecx' = 89 0D 5C 8B 8C 00. Hay que anularlos (NOP) o el año
# vuelve a 1999. (Validado en juego 2026-07-14.)
_DATE_LOADERS = (0xAAB2, 0xAEC0)
_LOADER_BYTES = bytes.fromhex("890d5c8b8c00")
# escritores de fecha de PARTIDA NUEVA: ponen 'mov al,1' y luego día=al, mes=al → 1-ene.
# Cambiar el inmediato a 8 → 8 de agosto (inicio de temporada real). B0 01 → B0 08.
_DAYMONTH_MOVAL = (0xB1C1, 0x2EB4C0)
# patrón de instrucción que USA la fecha con el año 1999 (escritor o comparador):
# [operando 0x8C8B5C][imm16 0x07CF]. Son 13 en el manager base (3 escritores + 10
# comparadores); TODOS deben apuntar al año nuevo o la lógica de temporada rechaza
# el año y te echa al menú principal.
_DATE_1999 = b"\x5c\x8b\x8c\x00\xcf\x07"
# EFECTO 2000: chequeo de rango de nacimiento [1900, 2000] (el juego es de 1999 y a los
# nacidos en 2000+ les da edad aleatoria/rota). Mismo parche que v5/6 (spisemisu/Carky):
# rango → [1, 65535] para que TODA fecha de nacimiento calcule la edad normal. Único.
_EFECTO2000_OLD = bytes.fromhex("6c070000760881fdd0070000")
_EFECTO2000_NEW = bytes.fromhex("01000000760881fdffff0000")


def set_start_year(manager: bytes, year: int) -> bytes:
    """Cambia el AÑO de inicio de temporada de PCF7. VALIDADO EN JUEGO (2026-07-14):
    con esto el juego arranca en `year` y las edades reales cuadran. Tres pasos —
    ninguno basta por sí solo:
      1. Reapunta a `year` TODAS las instrucciones que escriben/comparan la fecha con
         1999 (3 escritores + 10 comparadores). Sin los comparadores, el juego te
         devuelve al menú al empezar temporada.
      2. Anula (NOP) los 2 loaders que recargaban 1999 desde el objeto de partida.
      3. Deja el día/mes en 8 de agosto (los escritores de partida nueva ponían 1-ene).
      4. Aplica el parche del EFECTO 2000 (nacidos en 2000+ calculan la edad normal).
    El día/mes es 8-ago fijo (día y mes salen del mismo registro; 8/8 = 8 de agosto).
    REQUIERE en juego marcar "envejecimiento de los jugadores" al crear la partida
    (así el juego calcula la edad de la fecha real; validado 2026-07-14)."""
    b = bytearray(manager)
    yb = struct.pack("<H", year & 0xFFFF)
    # 1) año 1999 → year en escritores y comparadores de la fecha
    i = 0
    while True:
        i = b.find(_DATE_1999, i)
        if i < 0:
            break
        b[i + 4:i + 6] = yb
        i += 6
    # 2) NOP de los loaders (si el build coincide)
    for off in _DATE_LOADERS:
        if bytes(b[off:off + 6]) == _LOADER_BYTES:
            b[off:off + 6] = b"\x90" * 6
    # 3) día/mes → 8 de agosto ('mov al,1' → 'mov al,8')
    for off in _DAYMONTH_MOVAL:
        if bytes(b[off:off + 2]) == b"\xb0\x01":
            b[off + 1] = 0x08
    # 4) efecto 2000: rango de nacimiento [1900,2000] → [1,65535]
    j = b.find(_EFECTO2000_OLD)
    if j >= 0:
        b[j:j + len(_EFECTO2000_NEW)] = _EFECTO2000_NEW
    return bytes(b)


# --- PARTICIPANTES EUROPEOS (2026-08-16) ----------------------------------------------
# Tabla de datos con los clubes que pueden aparecer en las competiciones europeas.
# Localizada escaneando el ejecutable en busca de rachas largas de códigos de equipo
# válidos: 136 seguidos en 0x453690, todos reales. Se parte en dos porque el contenido
# lo pide: las 120 primeras van AGRUPADAS POR PAÍS (España 8, Francia 8, Italia 7,
# Alemania 6, Inglaterra 5… = el "pool" de cada federación) y las 16 últimas son una por
# país y son campeones/subcampeones de liga (Rosenborg, Man Utd, Bayern, Sparta Praga…),
# es decir los que entran en la Copa de Europa.
#
# OJO — esto NO está documentado por nadie: el editor comunitario de PCF7 (EPCF7) solo
# toca los continentes. La estructura está verificada (136/136 punteros son equipos y el
# reparto por país es coherente), pero el significado exacto es una deducción nuestra.
# Editarlo es reversible byte a byte; validar en la VM antes de fiarse.
# --- PARTICIPANTES EUROPEOS DE PCF7 (2026-10-01) --------------------------------------
# OJO: los bloques `euro_pool` (0x453690, 120) y `champions` (0x453780, 16) que había
# aquí son un SEÑUELO. Son byte a byte idénticos en 7/2000/2001 (tres temporadas), el
# mod comunitario 25-26 NO los toca, y editarlos no cambia quién juega: lo verificamos
# parcheándolos bien y arrancando partida (nada cambió). Se quedan fuera de la lista
# editable para no engañar a nadie.
#
# La lista VIVA la construye el juego en RUNTIME con 34 `mov word [..], <código>`
# (patrón `66 C7 44 xx FE <code>`) repartidos en 0x1C48DB-0x1C4E96: mezcla clubes de
# los 5 países grandes con clubes del resto de Europa. La prueba: el mod 25-26
# reescribe 33 de esas 34 plazas (y ninguna de las tablas de datos). Cada plaza va en
# el inmediato de su instrucción, así que se edita offset a offset, no como tabla.
# `imm` = offset de fichero del u16 (inicio de la instrucción + 5).
EURO7_SLOTS: list[int] = [
    0x1C4AA8, 0x1C4AC2, 0x1C4ADC, 0x1C4AF6, 0x1C4B10, 0x1C4B2A, 0x1C4B44, 0x1C4B61,
    0x1C4B7B, 0x1C4B95, 0x1C4BAF, 0x1C4BC9, 0x1C4BE3, 0x1C4BFD, 0x1C4C17, 0x1C4C34,
    0x1C4C4E, 0x1C4C70, 0x1C4D01, 0x1C4D1B, 0x1C4D35, 0x1C4D4F, 0x1C4D69, 0x1C4D83,
    0x1C4D9D, 0x1C4DBA, 0x1C4DD4, 0x1C4DEE, 0x1C4E08, 0x1C4E22, 0x1C4E3C, 0x1C4E56,
    0x1C4E70, 0x1C4E95,
]

FDI_TABLES: dict[int, list[dict]] = {
    4939776: [                                   # PCF 7
        {"key": "euro7", "label": "Participantes europeos (Copa de Europa / UEFA / Recopa)",
         "slots": EURO7_SLOTS},
        # COPAS Y TROFEOS: offsets del trabajo de josewolf22 (foro, vía peu7510), verificados
        # uno a uno contra el binario — 17/17 dan equipos válidos, y el contenido es el real
        # del 99/00: la Intercontinental es Man Utd vs Palmeiras, la Supercopa de España
        # Valencia + Barcelona y la de Italia Milan + Parma.
        # La tabla de 1ª y 2ª tenía 41 plazas y son 42: le faltaba la última. Y DELANTE hay
        # dos plazas más que no se habían visto — los FINALISTAS de la Copa del año anterior,
        # que de fábrica son el Barcelona y el Mallorca, justo quienes jugaron la final del
        # 97-98. (Se deja `copa_rey_2` donde estaba, con una plaza más, en vez de correrlo dos
        # atrás: hay mods con esta tabla ya guardada y moverla les desplazaría la copa entera.)
        {"key": "copa_rey_final", "sigue_liga": True, "label": "Copa del Rey — finalistas del año anterior",
         "off": 0x49EDFC, "n": 2},
        {"key": "copa_rey_2", "sigue_liga": True, "label": "Copa del Rey — 2ª ronda (1ª y 2ª división)",
         "off": 0x49EE00, "n": 42},
        {"key": "copa_rey_1", "sigue_liga": True, "label": "Copa del Rey — 1ª ronda (2ªB)",
         "off": 0x49EEA4, "n": 67},
        # COPAS INGLESAS (2026-09-22). Localizadas por el NOMBRE que el ejecutable escribe
        # detrás de cada tabla —«FACUP» y «CCCUP», el nombre viejo de la Coca-Cola Cup—, la
        # misma regla que destapó las copas de PCF2001 y el fallo de la Primera de PCF2000.
        # Las dos son bloques contiguos y todos sus códigos son clubes ingleses o galeses.
        {"key": "fa_cup", "sigue_liga": True, "label": "F.A. Cup",
         "off": 0x49D560, "n": 124},
        # Dos tablas más quedan LOCALIZADAS pero SIN mapear a propósito, porque no se
        # entienden del todo y mapear a medias es como se rompió la Copa de Alemania:
        #   · Copa de la Liga inglesa, «CCCUP» en 0x49D2D4: 100 plazas para 90 clubes
        #     distintos —Southampton, West Ham y ocho más salen dos veces— y le faltan dos de
        #     los 92 de la Liga (Southend y el W.B.A.). En PCF2001 la misma copa son 92 plazas
        #     sin repetir, así que aquí hay una estructura por rondas que todavía no se ve.
        #   · Copa de Italia, «CITALIA» en 0x49E170: tres bloques de 27 + 5 + 48, y en el
        #     último se repiten Lecce y Reggina. En 2001 ese bloque tiene 16.
        {"key": "supercopa_es", "label": "Supercopa de España",
         "off": 0x49F3F0, "n": 2},
        {"key": "supercopa_it", "label": "Supercopa de Italia",
         "off": 0x49E550, "n": 2},
        {"key": "intercontinental", "label": "Copa Intercontinental",
         "off": 0x49DC8C, "n": 2},
        {"key": "copa_fr_1", "sigue_liga": True, "label": "Copa de Francia — clubes de Ligue 1",
         "off": 0x4A0090, "n": 18},
        {"key": "copa_fr_2", "sigue_liga": True, "label": "Copa de Francia — clubes de Ligue 2",
         "off": 0x4A00B8, "n": 20},
        {"key": "copa_de_1", "sigue_liga": True, "label": "Copa de Alemania — clubes de 1ª",
         "off": 0x4A0488, "n": 18},
        {"key": "copa_de_2", "sigue_liga": True, "label": "Copa de Alemania — clubes de 2ª",
         "off": 0x4A04B0, "n": 18},
        {"key": "copa_liga_de", "label": "Copa de la Liga alemana",
         "off": 0x455A40, "n": 6},
        {"key": "trofeo_herrera", "label": "Trofeo Teresa Herrera",
         "off": 0x49ED0C, "n": 3},
        {"key": "trofeo_palma", "label": "Trofeo Ciutat de Palma",
         "off": 0x49EB04, "n": 3},
        {"key": "trofeo_bernabeu", "label": "Trofeo Santiago Bernabéu",
         "off": 0x49E6B0, "n": 1},
        {"key": "trofeo_gamper", "label": "Trofeo Joan Gamper",
         "off": 0x49E7E8, "n": 1},
        {"key": "trofeo_colombino", "label": "Trofeo Colombino",
         "off": 0x49E9F4, "n": 3},
        {"key": "trofeo_carranza", "label": "Trofeo Carranza",
         "off": 0x49E8F0, "n": 3},
        {"key": "trofeo_naranja", "label": "Trofeo Naranja",
         "off": 0x49EC20, "n": 2},
    ],
}


# Las copas de PCF7 que juegan todos los clubes de una división (ver `CUP_SLOTS`).
CUP_SLOTS.update({
    tam: [t["off"] + 2 * i for t in lista if t.get("sigue_liga") for i in range(t["n"])]
    for tam, lista in FDI_TABLES.items()
})


def table_offsets(t: dict) -> list[int]:
    """Offsets de fichero de las plazas de una tabla.

    Las tablas normales son u16 CONTIGUOS (`off` + 2·i). Los participantes europeos van
    dentro de instrucciones (`mov word [..], <código>`) y traen sus `slots` explícitos."""
    if "slots" in t:
        return list(t["slots"])
    return [t["off"] + 2 * i for i in range(t["n"])]


def tables_read(manager: bytes) -> list[dict] | None:
    lista = FDI_TABLES.get(len(manager))
    if lista is None:
        return None
    out = []
    for t in lista:
        offs = table_offsets(t)
        if any(o + 2 > len(manager) for o in offs):
            continue
        out.append({"key": t["key"], "label": t["label"],
                    "pointers": [struct.unpack_from("<H", manager, o)[0] for o in offs]})
    return out


def tables_write(manager: bytes, values: dict[str, list[int]]) -> bytes:
    """Escribe las tablas indicadas conservando su longitud (es fija) y el tamaño del exe."""
    lista = FDI_TABLES.get(len(manager))
    if lista is None or not values:
        return manager
    b = bytearray(manager)
    por_clave = {t["key"]: t for t in lista}
    for key, ptrs in values.items():
        t = por_clave.get(key)
        if t is None:
            continue
        offs = table_offsets(t)
        for o, v in zip(offs, ptrs):
            if v is None or not (0 < int(v) <= 0xFFFF) or o + 2 > len(b):
                continue
            struct.pack_into("<H", b, o, int(v))
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
         "help": "«La directiva sólo te deja hacer N ofertas.» Hay DOS comprobaciones en "
                 "el juego (una al ofertar y otra al confirmar) más el número del aviso: "
                 "se cambian las cuatro, o el tope seguiría aplicándose por un lado.",
         "sites": [(0x4B197, 1), (0x4B2A0, 1), (0x4C140, 1), (0x4C161, 1)],
         "factory": 5, "min": 1, "max": 99},
        {"key": "cedidos", "label": "Jugadores cedidos",
         "help": "Cuántos puedes tener cedidos a la vez. El juego avisa: «No puedes tener "
                 "más jugadores cedidos.»",
         "sites": [(0x4B1AB, 1)], "factory": 4, "min": 0, "max": 99},
        # EXTRACOMUNITARIOS (foro, 19-sep-2026: «al actualizar a años recientes
        # hay demasiados extranjeros»). El cupo es de 1997 y las plantillas de hoy no caben.
        #
        # Aquí no hay un salto que neutralizar como en v5/6: el juego pregunta el tope a una
        # función diminuta —`mov eax, N; ret`— que cada competición tiene en su tabla de
        # métodos, justo al lado de la que devuelve el texto del aviso. Por eso se localiza
        # por el MENSAJE («No se permite contratar más de N jugadores extracomunitarios») y
        # de ahí a la vtable que lo usa. El MISMO número sirve para fichar y para alinear:
        # los dos avisos cuelgan de la misma tabla, con el tope en medio.
        #
        # Hay DOS cupos, 4 y 3, según la competición. Van por separado a propósito: con un
        # solo control, restaurar el original pondría 4 donde el juego trae 3 — un cambio que
        # nadie ha pedido. Para quitar el límite de verdad hay que subir los dos.
        {"key": "extracom", "label": "Extracomunitarios (cupo general)",
         "help": "Cuántos jugadores de fuera de la UE puedes fichar Y alinear. El juego "
                 "avisa: «No se permite contratar más de 4 jugadores extracomunitarios.» "
                 "Súbelo si al actualizar a una temporada reciente no te caben las "
                 "plantillas de hoy.",
         "vtable": 0x1A5DC0, "factory": 4, "min": 0, "max": 99},
        {"key": "extracom_bajo", "label": "Extracomunitarios (cupo reducido)",
         "help": "El mismo tope, para las competiciones donde el juego solo admite 3. Si "
                 "subes el general y este no, seguirás topado en esas.",
         "vtable": 0x158480, "factory": 3, "min": 0, "max": 99},
    ],
}


# --- TOPES POR FUNCIÓN PROPIA (11-oct-2026) -----------------------------------------------
# El cupo de extracomunitarios es una función diminuta, `mov eax, N; ret`, a la que apunta la
# tabla de métodos de cada competición. Hasta hoy se cambiaba el N de esa función, y era un
# error GRAVE: el compilador FUSIONA las funciones idénticas, así que la misma `mov eax, 4; ret`
# la usan también otras clases que no tienen nada que ver con el cupo (en PCF7, una de 9; la de
# `mov eax, 3` la comparten 107 tablas y solo 49 son del cupo). Subir el cupo a 10 cambiaba esos
# otros valores: en PCF7 la pantalla de elegir equipo pintaba diez grupos de 2ªB y los botones
# tapaban «Seguir» (foro, #295).
#
# Ahora la función original NO se toca. En el relleno de NOPs que el compilador deja detrás de
# ella (10 bytes, comprobado) se escribe una copia propia `mov eax, N; ret` y SOLO las ranuras de
# las tablas del cupo —las que tienen al lado el método que devuelve el texto del aviso de
# extracomunitarios— pasan a apuntar a la copia. Restaurar el valor de fábrica deja el
# ejecutable idéntico byte a byte.
_IMAGE_BASE = 0x400000
_CUEVA = 8                                   # la copia va 8 bytes detrás de la función (6 + 2)


def _texto_de(manager: bytes, va: int) -> str:
    o = va - _IMAGE_BASE
    if 0 <= o < len(manager) - 6 and manager[o] == 0xB8 and manager[o + 5] == 0xC3:
        p = struct.unpack_from("<I", manager, o + 1)[0]
        if _IMAGE_BASE <= p < _IMAGE_BASE + len(manager):
            return manager[p - _IMAGE_BASE:p - _IMAGE_BASE + 90].split(b"\0")[0].decode("latin-1")
    return ""


def _ranuras_cupo(manager: bytes, fn: int) -> tuple[list[int], list[int]]:
    """(ranuras del cupo, todas las ranuras) que apuntan a la función `fn` (offset de fichero)
    o a su copia. Del cupo = las que tienen al lado el texto del aviso de extracomunitarios."""
    out, todas = [], []
    for destino in (fn, fn + _CUEVA):
        pat = struct.pack("<I", destino + _IMAGE_BASE)
        i = manager.find(pat)
        while i != -1:
            if i % 4 == 0 and 4 <= i < len(manager) - 8:
                todas.append(i)
                vecinos = (_texto_de(manager, struct.unpack_from("<I", manager, i - 4)[0])
                           + _texto_de(manager, struct.unpack_from("<I", manager, i + 4)[0]))
                if "extracomunitario" in vecinos:
                    out.append(i)
            i = manager.find(pat, i + 1)
    return out, todas


def _es_fn(b: bytes, o: int) -> bool:
    return b[o] == 0xB8 and b[o + 2:o + 5] == b"\0\0\0" and b[o + 5] == 0xC3


def vtable_limit_read(manager: bytes, fn: int) -> int | None:
    if fn + _CUEVA + 6 > len(manager) or not _es_fn(manager, fn):
        return None
    ranuras, _ = _ranuras_cupo(manager, fn)
    if not ranuras:
        return None
    cueva_va = fn + _CUEVA + _IMAGE_BASE
    if any(struct.unpack_from("<I", manager, r)[0] == cueva_va for r in ranuras) \
            and _es_fn(manager, fn + _CUEVA):
        return manager[fn + _CUEVA + 1]
    return manager[fn + 1]


def vtable_limit_write(b: bytearray, fn: int, val: int, factory: int) -> bool:
    """Pone el cupo `val`. Comprueba antes que la función es `mov eax, imm8; ret` y que detrás
    hay relleno (NOPs) o ya nuestra copia; si algo no cuadra, no toca NADA."""
    if fn + _CUEVA + 6 > len(b) or not _es_fn(b, fn) or not (0 <= val <= 255):
        return False
    cueva = fn + _CUEVA
    hueco = bytes(b[fn + 6:fn + 16])
    if not (hueco == b"\x90" * 10 or (hueco[:2] == b"\x90\x90" and _es_fn(b, cueva)
                                      and hueco[8:] == b"\x90\x90")):
        return False
    ranuras, _ = _ranuras_cupo(bytes(b), fn)
    if not ranuras:
        return False
    if b[fn + 1] != factory:                 # ejecutable con el parche VIEJO: se devuelve a fábrica
        b[fn + 1] = factory
    if val == factory:                       # de fábrica: todo como estaba, byte a byte
        for r in ranuras:
            struct.pack_into("<I", b, r, fn + _IMAGE_BASE)
        b[cueva:cueva + 6] = b"\x90" * 6
        return True
    b[cueva:cueva + 6] = bytes([0xB8, val, 0, 0, 0, 0xC3])
    for r in ranuras:
        struct.pack_into("<I", b, r, cueva + _IMAGE_BASE)
    return True


def limits_read(manager: bytes) -> list[dict] | None:
    lista = FDI_LIMITS.get(len(manager))
    if lista is None:
        return None
    out = []
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


# --- COMPOSICIÓN DE CONTINENTES (según EPCF7) ---------------------------------------------------
# Qué países integran cada uno de los 8 continentes: bytes (1 código de país por slot) en el
# MANAGER.EXE, en offsets FIJOS, con 1 byte de separación (0) entre bloques. Ident. por EPCF7
# (pcnimdock) y verificado contra nuestro MANAGER.EXE (España=22, Inglaterra=30, Italia=36 en
# Europa Occ.; los códigos coinciden con nuestra refdata de países).
CONTINENTS: list[tuple[int, str, int, int]] = [
    (1, "Europa Occidental", 4433080, 23),
    (2, "Europa Oriental", 4433104, 23),
    (3, "Norteamérica", 4433128, 3),
    (4, "Sudamérica", 4433132, 11),
    (5, "Asia Occidental", 4433144, 7),
    (6, "Asia Oriental", 4433152, 3),
    (7, "Oceanía", 4433156, 3),
    (8, "África", 4433160, 7),
]


def read_continents(manager: bytes) -> dict[int, list[int]]:
    """{id_continente: [código_de_país, …]} de la tabla de composición del MANAGER.EXE.
    Los 0 son slots vacíos (se conservan)."""
    return {cid: list(manager[off:off + n]) for cid, _lab, off, n in CONTINENTS}


def set_continents(manager: bytes, comp: dict[int, list[int]]) -> bytes:
    """Reescribe la tabla de continentes. `comp` = {id_continente: [códigos]}; cada bloque se recorta
    o rellena con 0 hasta sus `n` slots (los separadores NO se tocan). Round-trip byte-perfecto si se
    reescribe con la misma composición."""
    out = bytearray(manager)
    for cid, _lab, off, n in CONTINENTS:
        if cid in comp:
            codes = [c & 0xFF for c in comp[cid][:n]]
            codes += [0] * (n - len(codes))
            out[off:off + n] = bytes(codes)
    return bytes(out)
