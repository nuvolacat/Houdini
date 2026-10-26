"""Edición de las divisiones de manager.exe (competiciones de liga).

Las divisiones son ARRAYS de punteros canónicos u16 (los de refdata/teams.json:
Barcelona=1, R.Madrid=4, At.Madrid=12…) en offsets fijos del ejecutable. El juego
lee de ahí qué equipos juegan cada competición. Confirmado en juego real
(2026-07-04): editar la tabla de Primera y meter otros equipos → el juego los
muestra en Primera.

La tabla de PRIMERA se autolocaliza por firma: la secuencia de u16 (valores
1-450) más plausible que contiene a Barça(1)+R.Madrid(4)+At.Madrid(12). Su
LONGITUD es el nº de equipos de la temporada (96/97=22, 97/98=20), así que el
propio manager.exe nos dice cuántas plazas tiene la división — no lo adivinamos.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

_PTR_MIN, _PTR_MAX = 1, 450          # rango de punteros canónicos españoles
_SIG = {1, 4, 12}                    # Barcelona, R.Madrid, At.Madrid


@dataclass
class DivTable:
    offset: int          # offset de fichero del primer puntero
    count: int           # nº de plazas (equipos) de la división
    pointers: list[int]  # punteros canónicos actuales


def _runs(data: bytes):
    """Genera (offset, longitud) de cada secuencia de ≥8 u16 en rango de puntero."""
    i, n = 0, len(data)
    while i < n - 16:
        if _PTR_MIN <= struct.unpack_from("<H", data, i)[0] <= _PTR_MAX:
            k = 0
            while i + k * 2 < n and _PTR_MIN <= struct.unpack_from("<H", data, i + k * 2)[0] <= _PTR_MAX:
                k += 1
            if k >= 8:
                yield i, k
            i += max(2, k * 2)
        else:
            i += 1


def find_primera(data: bytes) -> DivTable | None:
    """Localiza la tabla de Primera División (18-24 plazas con la firma de los
    tres grandes). Elige la candidata más corta (la tabla real; las copias
    largas incluyen Segunda pegada)."""
    best: DivTable | None = None
    for off, k in _runs(data):
        if not 18 <= k <= 26:
            continue
        ptrs = [struct.unpack_from("<H", data, off + j * 2)[0] for j in range(k)]
        if not _SIG.issubset(set(ptrs)):
            continue
        # recortar a la división real: hasta la 1ª repetición de puntero
        # (tras Primera empieza Segunda, que suele repetir descendidos)
        vistos: set[int] = set()
        real = 0
        for p in ptrs:
            if p in vistos:
                break
            vistos.add(p)
            real += 1
        cand = DivTable(off, real, ptrs[:real])
        if best is None or cand.count < best.count:
            best = cand
    return best


def set_primera(data: bytearray, pointers: list[int]) -> int:
    """Reescribe la tabla de Primera con `pointers` (respetando su longitud:
    no cambia el nº de plazas, solo qué equipos las ocupan). Devuelve cuántas
    plazas se escribieron. `pointers` de más se ignoran; de menos, deja el resto."""
    tab = find_primera(bytes(data))
    if tab is None:
        return 0
    n = min(len(pointers), tab.count)
    for j in range(n):
        struct.pack_into("<H", data, tab.offset + j * 2, pointers[j] & 0xFFFF)
    return n


def read_primera_pointers(data: bytes) -> list[int]:
    tab = find_primera(data)
    return tab.pointers if tab else []


# ---------------------------------------------------------------------------
# EDICIÓN DE DIVISIONES (validado EN JUEGO REAL, 2026-07-04)
#
# El juego carga cada división con `push <VA tabla>; push <contador>`. Cambiar el
# contador cambia el nº de equipos (Primera 22→20 confirmado). Para SUBIR una
# división por encima de su tabla original, se reubica la tabla a un hueco de
# ceros del ejecutable (.rdata) y se repunta el `push` del cargador (Segunda
# 20→22 confirmado). 2ªB son 4 grupos con UN contador compartido (bucle).
#
# Mapa por juego (clave = tamaño del manager.exe). Offsets de FICHERO validados.
#
# ⚠️⚠️  SPAIN_MAP / patch_spain: VÍA INACTIVA — NO REACTIVAR SIN LEER ESTO  ⚠️⚠️
#
# La recolocación de divisiones de HOY (2026-09) NO pasa por aquí: la hace `leagues.py` con
# PUNTEROS CANÓNICOS + overrides de ficha (`ptr_overrides`, `name_override`, `grupo2b`) y SIN
# TOCAR el .exe. Ese camino cubre las 6 ediciones y no necesita offsets.
#
# Este bloque es la vía ANTIGUA: reescribe las tablas de división DENTRO del ejecutable, con
# contadores y —cuando la división no cabe (5.0: Segunda 20→22)— inyecta una `code cave` de
# 345 bytes en .rdata y REPUNTA el cargador. Es cirugía del .exe: los offsets de la cave
# (`va`) y los `count_off`/`addr_off` son PROPIOS DE CADA BUILD y NO se pueden derivar de otro.
#
# Estado: DESACTIVADA. `Session.spain_divisions` está a `None` y NADIE lo llena (ni la API ni
# la web), así que `patch_spain` no se ejecuta nunca. Solo hay UNA entrada (5.0 Oro) y **no
# tiene ni un test**. Los otros builds NO la necesitan: 6.0 base y Oro ya tienen Segunda=22 de
# fábrica (ver `DIVISION_MAP`), así que no hay nada que reubicar.
#
# Si algún día hay que reactivarla: (1) escribir el `count_off`/`addr_off`/`cave` de CADA build
# buscándolos en SU binario, (2) añadir tests que lean la tabla tras el parche y comparen contra
# la realidad, (3) VALIDAR EN JUEGO. Mientras no se haga eso, usar `leagues.py`.
#
# Lo que SÍ se usa de esta zona: `find_primera` / `read_primera_pointers` (autolocalizan la
# tabla de Primera por ESTRUCTURA, sin offsets) — esos no son parte de la vía inactiva.
# ---------------------------------------------------------------------------

SPAIN_MAP: dict[int, dict] = {
    # pcf5oro / 6.0 Oro (manager raíz, mismo MD5) — temporada 96/97
    2461184: {
        "primera": {"table": 2348816, "count_off": 0x551c6, "cap": 22},
        "segunda": {"table": 2349064, "count_off": 0x5b0db,
                    "addr_off": 0x5b0d6, "cap": 20},
        "grupos2b": {"table": 2349480, "count_off": 0x61ddc,
                     "groups": 4, "stride": 20, "cap": 20},
        "cave": {"file": 0x23aca7, "va": 0x63bca7, "size": 345},
    },
}

# estructura objetivo (actual): Primera 20, Segunda 22, 2ªB 18×4
TARGET = {"primera": 20, "segunda": 22, "grupos2b": 18}


def supports_divisions(size: int) -> bool:
    """VÍA INACTIVA (ver el aviso de `SPAIN_MAP`). Devuelve si el parche del .exe está mapeado
    para ese build — hoy solo el 5.0 Oro. NO lo usa la recolocación actual (`leagues.py`)."""
    return size in SPAIN_MAP


# Offsets de las TABLAS de división por tamaño de manager.exe (para LEER las plazas
# nativas; no se toca el .exe). (offset, nº plazas). 2ªB = (offset, por_grupo, grupos).
DIVISION_MAP: dict[int, dict] = {
    2461184: {  # 5.0 Oro / 6.0 Oro raíz (96/97)
        "primera": (2348816, 22),
        "segunda": (2349064, 20),
        "grupos2b": (2349480, 20, 4),
    },
    2662400: {  # 6.0 Oro Futbol6 (97/98) — Primera 20, Segunda 22 (= realidad)
        "primera": (2609200, 20),
        "segunda": (2609648, 22),
        # FIX 2026-08-15: la tabla de 2ªB estaba en 2610022 (2 bytes ANTES) → G1 cogía un 103
        # espurio del borde y salía con 19 (creíamos que era un 103 duplicado de Dinamic; NO,
        # era el offset mal). En 2610024 los 4 grupos dan 20/20/20/20 únicos y válidos.
        "grupos2b": (2610024, 20, 4),
    },
}

# Extensión 1 (2.630.144): mismas tablas que el build Oro con el desplazamiento −0x74D8,
# verificado leyendo las tres y comparándolas con las del Oro (idénticas).
DIVISION_MAP[2630144] = {k: ((v[0] - 0x74D8,) + v[1:]) for k, v in DIVISION_MAP[2662400].items()}

# 6.0 ORIGINAL (2.617.344) — añadido el 1-sep-2026. Sin esto, «Actualizar España» en 6.0 base
# no sabía cuáles son las plazas reales y recolocaba con el reparto genérico (1-22 Primera,
# 23-44 Segunda), que en esta edición NO coincide: su Primera son 20 plazas y sus punteros no
# van en orden. De ahí el reparto de divisiones incorrecto que se corrigió.
#
# Los offsets NO se copiaron: se BUSCARON en el binario por estructura. La zona de divisiones
# es una sucesión de tramos de u16 que son todos punteros canónicos de clubes ESPAÑOLES de esa
# base, y las dos builds tienen la MISMA forma, tramo a tramo y a las mismas distancias:
#
#     +0 (40 valores) · +160 (64) · +712 (Primera) · +1160 (Segunda) · +1534 (2ªB)
#
# De ahí sale el desplazamiento −0x8D48. Verificado además leyendo las tablas: dan la Primera
# real del 97-98 (Madrid, Barcelona, Deportivo, Betis, At. Madrid… 20 equipos), 22 en Segunda y
# 20 distintos en cada grupo de 2ªB, coherentes por zonas.
DIVISION_MAP[2617344] = {k: ((v[0] - 0x8D48,) + v[1:]) for k, v in DIVISION_MAP[2662400].items()}

# 5.0 ORIGINAL (2.507.264) — mismo día y mismo método, pero aquí las tres tablas van SEGUIDAS
# (un solo tramo de 127 valores en 2342760) en vez de separadas como en las Oro. Partido en
# 22 + 20 + 4×20 da la Primera real del 95-96 (Barcelona, Deportivo, Zaragoza, Real Madrid…,
# 22 equipos, que son los que tuvo esa temporada), Segunda con 20 y los cuatro grupos de 2ªB
# con 20 cada uno.
DIVISION_MAP[2507264] = {
    "primera": (2342760, 22),
    "segunda": (2342760 + 22 * 2, 20),
    "grupos2b": (2342760 + 42 * 2, 20, 4),
}


# ---------------------------------------------------------------------------
# COPAS EUROPEAS / SUPERCOPAS (2026-08-15): los PARTICIPANTES son punteros
# canónicos en offsets fijos de datos del manager.exe. Descubierto con el
# hexwork de lupus + el diff de los mods comunitarios del build PCF6 2.654.208,
# y ANCLADO a nuestros builds por contexto.
# Verificado contra la realidad de cada temporada de fábrica:
#   6.0 Oro (97/98): Supercopa España = Barcelona+R.Madrid ✓ · Supercopa Europa
#   = Dortmund+Barcelona ✓ · Intercontinental = Dortmund+Cruzeiro ✓ · Recopa
#   España = Betis ✓ (lo que decía lupus) · UEFA españoles = Depor, At.Madrid,
#   Valladolid, Athletic ✓.
#   5.0 Oro (96/97): Supercopa España = Barcelona+At.Madrid ✓ · Supercopa
#   Europa = Juventus+PSG ✓ · Intercontinental = Juventus+River ✓.
# Cada slot es u32 (valor u16 + 2 ceros) salvo la tabla UEFA (u16 seguidos).
# PENDIENTE VM. Clave del mapa = tamaño del manager.exe (como SPAIN_MAP).
# ---------------------------------------------------------------------------

# Cada competición = lista de SLOTS; cada slot = lista de offsets u16 (se escribe el
# MISMO puntero en todos: la Copa de Europa lleva el 2º equipo español DUPLICADO en dos
# offsets — el editor de carky escribe ambos; si difieren, el juego mete un 3er equipo).
# Champions de 6.0 Oro anclada desde los offsets EXACTOS del editor de carky12
# (verificados en el manager original del juego).
EUROCUPS_MAP: dict[int, dict[str, list[list[int]]]] = {
    2662400: {   # 6.0 Oro Futbol6 (97/98)
        "supercopa_es": [[0x27d4e8], [0x27d4ec]],
        "supercopa_eu": [[0x27dcb8], [0x27dcbc]],
        "intercontinental": [[0x27c8f0], [0x27c8f4]],
        # el equipo español se guarda DOS veces: suelto y dentro de la lista de
        # participantes; aquí se escriben los dos para que no se contradigan.
        "recopa": [[0x27dc04, 0x27dc0a]],
        "champions": [[0x27d894], [0x27d8bc, 0x27d8cc]],
        "uefa": [[0x27da00], [0x27da02], [0x27da04], [0x27da06]],
    },
    2630144: {   # 6.0 Extensión 1 (97/98) — mismos sitios que Oro con delta −0x74D8
        "supercopa_es": [[0x276010], [0x276014]],
        "supercopa_eu": [[0x2767e0], [0x2767e4]],
        "intercontinental": [[0x275418], [0x27541c]],
        # el equipo español se guarda DOS veces: suelto y dentro de la lista de
        # participantes; aquí se escriben los dos para que no se contradigan.
        "recopa": [[0x27672c, 0x276732]],
        "champions": [[0x2763bc], [0x2763e4, 0x2763f4]],
        "uefa": [[0x276528], [0x27652a], [0x27652c], [0x27652e]],
    },
    2617344: {   # 6.0 BASE (97/98) — mismos sitios que Oro con delta −0x8D48
        # Petición del foro (11-sep-2026): en el juego base salía «no disponible».
        # El build no estaba medido, y las tablas se localizaron como siempre, POR ESTRUCTURA:
        # se cogen los bytes de alrededor de cada tabla en 6.0 Oro y se buscan aquí. Recopa,
        # Champions y UEFA aparecen UNA sola vez cada una y las tres dan el MISMO delta
        # (−36168). Las otras tres no se localizan por contexto —su entorno cambia entre
        # builds—, pero a ese delta leen exactamente los mismos participantes que en Oro, y el
        # entorno de cada tabla coincide en un 84-97% (los 8 KB que las contienen, en un 82%).
        "supercopa_es": [[0x2747a0], [0x2747a4]],
        "supercopa_eu": [[0x274f70], [0x274f74]],
        "intercontinental": [[0x273ba8], [0x273bac]],
        # el equipo español se guarda DOS veces: suelto y dentro de la lista de participantes;
        # se escriben los dos para que no se contradigan (ver la nota de 6.0 Oro)
        "recopa": [[0x274ebc, 0x274ec2]],
        "champions": [[0x274b4c], [0x274b74, 0x274b84]],
        "uefa": [[0x274cb8], [0x274cba], [0x274cbc], [0x274cbe]],
    },
    2461184: {   # manager raíz 5.0 Oro / 6.0 Oro (96/97)
        "supercopa_es": [[0x23db28], [0x23db2c]],
        "supercopa_eu": [[0x23e5a0], [0x23e5a4]],
        "intercontinental": [[0x23cf00], [0x23cf04]],
        # Las plazas europeas de este build son ÍNDICES FIJOS dentro de las listas
        # completas de participantes (2026-08-16, validado contra el binario: Champions 17×u16 @0x23DFA0
        # con la plaza española en el índice 12 = Atlético 96/97 ✓; UEFA 64×u16
        # @0x23E318 con las españolas en 6/20/53 = Espanyol/Tenerife/Valencia ✓;
        # Recopa 32×u16 @0x23E4E0 con la española en 9 = Barcelona ✓).
        "champions": [[0x23dfa0 + 12 * 2]],
        "uefa": [[0x23e318 + 6 * 2], [0x23e318 + 20 * 2], [0x23e318 + 53 * 2]],
        "recopa": [[0x23e4e0 + 9 * 2]],
    },
}

EUROCUP_LABELS: dict[str, tuple[str, list[str]]] = {
    "supercopa_es": ("Supercopa de España", ["Campeón de Copa", "Campeón de Liga"]),
    "supercopa_eu": ("Supercopa de Europa", ["Campeón de Europa", "Campeón de la Recopa"]),
    "intercontinental": ("Copa Intercontinental", ["Campeón de Europa", "Campeón de Libertadores"]),
    "recopa": ("Recopa (plaza española)", ["Equipo español"]),
    "champions": ("Copa de Europa (plazas españolas)", ["Equipo español 1", "Equipo español 2"]),
    "uefa": ("Copa de la UEFA (plazas españolas)", ["Plaza 1", "Plaza 2", "Plaza 3", "Plaza 4"]),
}


def eurocups_read(data: bytes) -> dict[str, list[int]] | None:
    """Participantes actuales de las copas por clave, o None si el build no está
    mapeado. Valores = punteros canónicos u16 (se lee el 1er offset de cada slot)."""
    m = EUROCUPS_MAP.get(len(data))
    if m is None:
        return None
    return {key: [struct.unpack_from("<H", data, offs[0])[0] for offs in slots]
            for key, slots in m.items()}


def eurocups_write(data: bytearray, values: dict[str, list[int]]) -> int:
    """Escribe los participantes indicados (u16 en TODOS los offsets de su slot,
    incl. duplicados como el 2º de la Copa de Europa). Devuelve slots escritos."""
    m = EUROCUPS_MAP.get(len(data))
    if m is None:
        return 0
    written = 0
    for key, vals in (values or {}).items():
        slots = m.get(key)
        if slots is None:
            continue
        for i, v in enumerate(vals[:len(slots)]):
            if v is None or not (0 < int(v) <= 0xFFFF):
                continue
            for off in slots[i]:
                struct.pack_into("<H", data, off, int(v))
            written += 1
    return written


# ---------------------------------------------------------------------------
# RESTRICCIONES DEL MOTOR (2026-08-16). Estos juegos guardan sus reglas en el
# CÓDIGO del manager.exe, no en la BBDD: se cambian neutralizando saltos
# condicionales. Offsets del trainer comunitario "KeksPatch" v0.16, VERIFICADOS
# byte a byte contra nuestro manager de 5.0 Oro (11/11 sitios con los bytes
# originales exactos que dice la fuente).
#
# Los offsets son de UN BUILD CONCRETO: la clave del mapa es el tamaño del .exe,
# y antes de escribir se comprueba que los bytes de destino son los esperados
# (originales o ya parcheados). Si no casan, NO se toca — será otro build.
# El 6.0 Oro (2.662.400) NO está: los offsets publicados son del build de CD
# (2.617.344), que es otro ejecutable, y las firmas de contexto del 5.0 Oro no
# aparecen en él (recompilado). Habría que localizar los sitios a mano.
# ---------------------------------------------------------------------------
# CATÁLOGO ÚNICO de reglas del motor: la MISMA lista en todas las ediciones, para que el
# editor no cambie de aspecto según el juego. Lo que no esté localizado en un build sale
# igualmente, marcado y sin poder tocarse — así se ve que existe y que falta.
#
# Aquí SOLO van las reglas que no son un número. Los topes (extracomunitarios, ofertas…)
# viven en LIMITS: un número dice más que una casilla (99 = "sin límite") y evita tener
# dos controles peleándose por los mismos bytes.
RULES = [
    ("traspaso_jugadores", "Los jugadores siempre aceptan el traspaso",
     "Ningún jugador rechaza tu oferta."),
    ("traspaso_clubes", "Los clubes siempre aceptan el traspaso",
     "Ningún club rechaza tu oferta por su jugador."),
    ("nacimiento", "Admitir jugadores nacidos después de 1999",
     "De fábrica el juego solo acepta años de nacimiento entre 1901 y 1999 (compara "
     "contra 1900 y 2000 y da error fuera de ahí). Con plantillas actuales eso deja "
     "fuera a cualquiera menor de 26 años. El parche sube el tope a 65534."),
    ("extranjeros_fichar", "Fichar extracomunitarios sin límite",
     "Quita la comprobación del cupo al FICHAR. El juego lo mira en varios sitios y se "
     "desactivan todos los que estén localizados en tu ejecutable."),
    ("extranjeros_alinear", "Alinear extracomunitarios sin límite",
     "Quita la comprobación del cupo al ALINEAR. Es independiente de la de fichar: "
     "el juego las hace por separado."),
    ("estadios_3d", "Desactivar los estadios 3D (dibujar siempre el genérico)",
     "En la pantalla de Estadio, los equipos grandes traen un dibujo en 3D de su campo y el "
     "resto ven el estadio genérico, el que va creciendo según construyes gradas. Con esto el "
     "juego no busca el dibujo de nadie y todos ven el genérico. NO toca la fotografía del "
     "campo de la base de datos, que es otra imagen y sigue saliendo en la ficha del club."),
    ("caja_divisiones", "Respetar la caja de la base en Segunda y Segunda B",
     "EXPERIMENTAL. Al empezar la partida el juego recalcula el dinero según la división: en "
     "Primera respeta la caja de la base (mínimo 75 M), pero en Segunda usa una tabla fija según "
     "la media de la plantilla (la caja solo sirve para bajarlo) y en Segunda B te deja entre 75 "
     "y 84 M. Con esto Segunda y Segunda B usan la caja que pongas, como Primera. Validado en el "
     "código del juego, todavía no jugando (foro, #322)."),
]
# Reglas que solo existen en unas ediciones: en las demás NO se enseñan (ni en gris), porque
# allí no hay nada que arreglar. La caja ya manda en 5.0/6.0, que usan el presupuesto tal cual.
RULES_SOLO: dict[str, set[int]] = {"caja_divisiones": {4939776}}

# Parches por build. Offsets de KeksPatch verificados en 5.0 Oro.
RESTRICTIONS: dict[int, dict[str, list]] = {
    2461184: {                                   # PCF 5.0 Edición de Oro
        "traspaso_jugadores": [(0x1BBEE0, "0F84B1020000", "909090909090")],
        "traspaso_clubes": [(0x15EDCF, "74", "EB"), (0x1BBE50, "75", "EB")],
        "nacimiento": [(0x1B3DF5, "D007", "FFFF")],
        # Extracomunitarios: sus patrones LITERALES no aparecen aquí, pero era un falso
        # negativo — llevan dentro el desplazamiento del salto, que cambia de compilación.
        # Buscando por ESTRUCTURA (2026-08-20) aparece el sitio de ALINEAR:
        #   0x179F8E: 8B F8 8B 01 FF 50 70 3B F8 76 2B  ← la misma rutina byte a byte que en
        #   6.0 Oro (allí 0x69ADB; solo cambia el 2B/2A del salto). `mov edi,eax; mov eax,
        #   [ecx]; call [eax+70]; cmp edi,eax; jbe +2B` → el salto se hace incondicional.
        # Los otros dos sitios de alinear que sí tiene 6.0 Oro (0xE554 y 0xDA7D) NO existen
        # aquí ni con patrones laxos: este build hace la comprobación en un solo sitio. Los
        # de FICHAR siguen sin localizar porque usa otros offsets de vtable (0x90/0x88 en
        # vez de 0x94/0x8C), así que esa opción se queda sin ofrecer en 5.0 Oro.
        # PENDIENTE VM: comprobar que deja alinear al cuarto extracomunitario.
        "extranjeros_alinear": [(0x179F8E, "76", "EB")],
    },
    2662400: {                                   # PCF 6.0 Edición de Oro
        # Los traspasos NO están localizados en este build: los offsets publicados son
        # del build de CD (recompilado, 5 de 10 sitios encontrados), en su manager.exe no
        # hay ni un texto de "rechazo" que seguir, y el diálogo ACEPTAR/RECHAZAR solo
        # aparece para dibujar los botones. Hace falta un manager ya parcheado y diffear.
        "nacimiento": [(0xAF0C9, "D007", "FFFF")],
        # Extracomunitarios: sitios localizados por estructura en este ejecutable
        # (referencia: PCx-Utils, cuyos offsets son de otro build). Solo se listan los que aparecen UNA vez; el sitio
        # `92 8C 00 00 00 85 C0 74 49` no existe aquí y se omite.
        "extranjeros_fichar": [(0x4EF0D, "74", "EB"), (0x7CA24, "74", "EB"),
                               (0x73BFD, "74", "EB"), (0x9FA82, "74", "EB")],
        # El TERCER sitio de alinear (0xDA7D) faltaba hasta el 2026-08-20: su patrón lleva
        # dentro el desplazamiento del salto (59 01 en su build, 51 01 en el nuestro), así
        # que la búsqueda literal no lo encontraba. Buscando por estructura sale UNO solo y
        # es la misma rutina byte a byte. Aquí el salto es `jz rel32`, 6 bytes → 6 NOPs.
        "extranjeros_alinear": [(0xE554, "75", "EB"), (0x69ADB, "76", "EB"),
                                (0xDA7D, "0F8451010000", "909090909090")],
    },
    2617344: {                                   # PC Fútbol 6.0 (build de CD, sin Oro)
        # Offsets de KeksPatch (su tabla trae este build con el TAMAÑO exacto, 2.617.344),
        # verificados 10/10 contra nuestro ejecutable: en los diez sitios están los bytes de
        # fábrica que su tabla dice. Además cuatro de ellos coinciden con los que habíamos
        # localizado por nuestra cuenta desensamblando el entorno del parche de 6.0 Oro
        # (con una herramienta de búsqueda de patrones), lo que los confirma por dos vías independientes — y de
        # paso descartó un falso positivo de esa búsqueda (0xA4CEE, otra rutina parecida).
        "extranjeros_fichar": [(0x516ED, "74", "EB"), (0x7F664, "74", "EB"),
                               (0x44F5E, "74", "EB"), (0x766BD, "74", "EB"),
                               (0xBE4B4, "74", "EB")],
        "extranjeros_alinear": [(0xE4D4, "75", "EB"), (0x6C1FB, "76", "EB"),
                                (0xD9CD, "0F8459010000", "909090909090")],
        # El año de nacimiento NO está en KeksPatch: este sitio lo localizamos nosotros con
        # una búsqueda de patrones (patrón único; el entorno desensambla igual que en 6.0 Oro:
        # `push 5` · `call` · `mov ecx,[global]` · `mov edx,[esp+0x28]`). Los bytes de
        # fábrica son los esperados. PENDIENTE DE VALIDAR EN LA VM.
        "nacimiento": [(0xB45FF, "D007", "FFFF")],
    },
    2601472: {                                   # PC Calcio 6 (del CD de 6.0 Oro)
        "nacimiento": [(0xAD649, "D007", "FFFF")],
        # uno de los sitios de fichar sale DOS veces aquí (ambiguo) → se omite
        "extranjeros_fichar": [(0x4ED0D, "74", "EB"), (0x7B0B4, "74", "EB"),
                               (0x722BD, "74", "EB")],
        "extranjeros_alinear": [(0xE594, "75", "EB"), (0x6818B, "76", "EB")],
        # OJO: a este build no se le ha buscado el TERCER sitio de alinear (el `jz rel32`
        # que sí tiene 6.0 Oro en 0xDA7D) porque aún no se ha localizado en ese ejecutable.
        # Al recuperarlo, buscar el patrón estructural 53 55 8B CE E8 ?? ?? 00 00 84 C0
        # 0F 84 ?? ?? 00 00 33 C9 33 C0 8A 4B y NOPear sus 6 bytes de salto.
    },
    2545152: {                                   # manager2.exe del CD de 6.0 Oro
        "nacimiento": [(0xAB449, "D007", "FFFF")],
        "extranjeros_alinear": [(0xE3D4, "75", "EB"), (0x656BB, "76", "EB")],
        # OJO: a este build no se le ha buscado el TERCER sitio de alinear (el `jz rel32`
        # que sí tiene 6.0 Oro en 0xDA7D) porque aún no se ha localizado en ese ejecutable.
        # Al recuperarlo, buscar el patrón estructural 53 55 8B CE E8 ?? ?? 00 00 84 C0
        # 0F 84 ?? ?? 00 00 33 C9 33 C0 8A 4B y NOPear sus 6 bytes de salto.
    },
    4939776: {                                   # PC Fútbol 7 — MISMA comprobación de año
        "nacimiento": [(0xC8E72, "D007", "FFFF")],
        # Caja de la partida nueva (11-oct-2026, foro #322). FUN_004ba350 normaliza el dinero de
        # cada club: `cmp ecx, 0x3EA` (2ªB → 75-84 M fijos) en VA 0x4BA462 y `cmp ecx, 0x3E9`
        # (Segunda → tope T[categoría por media], tabla de floats en 0x83C808) en VA 0x4BA4AD.
        # Cambiando el id de liga del `cmp` por uno que no existe (0xFFFF) esas dos ramas no
        # se toman nunca y Segunda/2ªB caen en la de Primera: B = max(caja, índice)·1e6, con el
        # mínimo de 75 M. Mismos bytes en el ejecutable de fábrica y en el de la Actualización
        # 25-26. Se cambia solo el inmediato (los 2 bytes bajos del imm32).
        "caja_divisiones": [(0xBA464, "EA03", "FFFF"), (0xBA4AF, "E903", "FFFF")],
    },
}


# ---------------------------------------------------------------------------
# ESTADIO GENÉRICO SIEMPRE (parche comunitario, 10-sep-2026)
#
# El juego carga la foto del estadio con una ruta con formato, `dbdat\estadio\%s.bmp`.
# Cambiando el `%s` por `%u` el nombre sale como un NÚMERO (el puntero de la cadena
# formateado como entero), el fichero no existe y el juego dibuja el estadio genérico: el que
# va cambiando de forma según las gradas que construyes. Vale para TODOS los equipos de golpe
# y desactiva de paso el contenedor, porque el `.PKF` lo deduce de la carpeta.
#
# Se localiza por la CADENA, no por offset, así que funciona en cualquier build de 6.0
# —incluidos los que no están en RESTRICTIONS, que va por tamaño de ejecutable— y no puede
# escribir en el sitio equivocado. En 5.0 esa ruta no existe (su manager no carga foto de
# estadio por equipo): allí no hay nada que parchear y la opción no se ofrece.
_ESTADIO_RUTA = b"dbdat\\estadio\\%"
_ESTADIO_COLA = b".bmp"


def _estadio_sitios(data) -> list[int]:
    """Offsets del byte de formato (`s`/`u`) en la ruta de la foto de estadio."""
    out, i = [], data.find(_ESTADIO_RUTA)
    while i != -1:
        pos = i + len(_ESTADIO_RUTA)
        if data[pos:pos + 1] in (b"s", b"u") and data[pos + 1:pos + 5] == _ESTADIO_COLA:
            out.append(pos)
        i = data.find(_ESTADIO_RUTA, i + 1)
    return out


def estadio_generico_estado(data: bytes) -> str | None:
    """"off" (el juego enseña la foto real), "on" (parcheado: siempre el genérico) o None
    si este ejecutable no tiene esa ruta (5.0 y anteriores)."""
    sitios = _estadio_sitios(data)
    if not sitios:
        return None
    return "on" if all(data[i:i + 1] == b"u" for i in sitios) else "off"


def estadio_generico_write(data: bytearray, on: bool) -> int:
    """Aplica o revierte el parche. Devuelve cuántos sitios se han tocado."""
    n = 0
    for i in _estadio_sitios(data):
        nuevo = b"u" if on else b"s"
        if data[i:i + 1] != nuevo:
            data[i:i + 1] = nuevo
            n += 1
    return n


def restrictions_read(data: bytes) -> list[dict] | None:
    """Restricciones del build, con su estado. None si el build no está mapeado.

    `state`: "off" bytes de fábrica · "on" ya parcheado · "?" ni una cosa ni otra
    (manager tocado por otra herramienta) → esa se muestra pero no se deja tocar."""
    build = RESTRICTIONS.get(len(data))
    generico = estadio_generico_estado(data)
    if build is None and generico is None:
        return None                      # ni build mapeado ni nada localizable: no hay qué ofrecer
    build = build or {}
    out = []
    for key, label, help_ in RULES:
        if key in RULES_SOLO and len(data) not in RULES_SOLO[key]:
            continue
        if key == "estadios_3d":         # esta se localiza por la ruta, no por offset
            out.append({"key": key, "label": label, "help": help_,
                        "available": generico is not None,
                        "state": generico or "na"})
            continue
        parches = build.get(key)
        if not parches:                  # existe, pero no localizada en este ejecutable
            out.append({"key": key, "label": label, "help": help_,
                        "state": "na", "available": False})
            continue
        est = set()
        for off, orig, nuevo in parches:
            n = len(orig) // 2
            real = data[off:off + n].hex()
            est.add("off" if real == orig.lower() else "on" if real == nuevo.lower() else "?")
        out.append({"key": key, "label": label, "help": help_, "available": True,
                    "state": "?" if "?" in est or len(est) > 1 else est.pop()})
    return out


def restrictions_write(data: bytearray, values: dict[str, bool]) -> int:
    """Aplica/revierte restricciones. Solo escribe donde los bytes son los
    esperados (originales o ya parcheados): cualquier otra cosa se deja intacta."""
    build = RESTRICTIONS.get(len(data)) or {}
    tocados = 0
    for key, on in (values or {}).items():
        if key == "estadios_3d":
            if estadio_generico_write(data, bool(on)):
                tocados += 1
            continue
        parches = build.get(key)
        if not parches:
            continue
        sitios = []
        for off, orig, nuevo in parches:
            n = len(orig) // 2
            real = data[off:off + n].hex()
            if real not in (orig.lower(), nuevo.lower()):
                sitios = []                      # build inesperado → no tocar NADA
                break
            sitios.append((off, bytes.fromhex(nuevo if on else orig)))
        for off, b in sitios:
            data[off:off + len(b)] = b
        if sitios:
            tocados += 1
    return tocados


# ---------------------------------------------------------------------------
# LISTAS COMPLETAS DE PARTICIPANTES (2026-08-16). Hasta ahora solo editábamos la
# PLAZA ESPAÑOLA de cada copa; estas son las tablas enteras, más los dos bombos
# de la Copa del Rey. Offsets documentados por el editor comunitario Manager5Oro,
# verificados leyéndolos de nuestro manager: los 216 punteros de las 5 tablas son
# equipos reales y el contenido casa con la temporada 95/96 de fábrica.
# ---------------------------------------------------------------------------
TOURNAMENT_LISTS: dict[int, list[dict]] = {
    # PCF 6.0 EXTENSIÓN 1 (manager de 2.630.144 B). MISMAS tablas que el build Oro con un
    # desplazamiento CONSTANTE de -0x74D8, verificado una por una: mismos tamaños, mismo
    # contenido y hasta las mismas 7 plazas vacías en la UEFA. El tamaño del manager de
    # cada variante está documentado en el manual del editor de carky12.
    2630144: [
        {"key": "copa_rey_1a2a", "label": "Copa del Rey — bombo de 1ª y 2ª",
         "off": 0x275890, "n": 40, "es": []},
        {"key": "copa_rey_2b", "label": "Copa del Rey — bombo de 2ªB",
         "off": 0x275930, "n": 64, "es": []},
        {"key": "champions_prev", "label": "Copa de Europa — 1ª ronda previa (15 cruces)",
         "off": 0x276360, "n": 30, "es": [],
         # 15 cruces de 4 B, como la 2ª previa. Aquí NO se etiqueta local/visitante: el
         # orden de los dos equipos no casa con el del sorteo real y no se puede afirmar.
         "labels": [f"{i // 2 + 1} · {'A' if i % 2 == 0 else 'B'}" for i in range(30)],
         "empty_label": "sin equipo"},
        # 2ª RONDA PREVIA: 16 cruces de 4 bytes, (local, visitante). Los ceros NO son
        # plazas vacías: son la plaza que ocupará el ganador de la previa, que el juego
        # resuelve al simular — por eso hay 15 (los 15 ganadores de los 30 de la previa) y
        # el único cruce con los dos equipos puestos es Salzburg–Sparta, que entran
        # directos a esta ronda. La plaza española 1 es el local del cruce 8.
        {"key": "champions_previa2", "label": "Copa de Europa — 2ª ronda previa (16 cruces)",
         "offs": [0x2763A0, 0x2763A2, 0x2763A4, 0x2763A6, 0x2763A8, 0x2763AA, 0x2763AC, 0x2763AE, 0x2763B0, 0x2763B2, 0x2763B4, 0x2763B6, 0x2763B8, 0x2763BA, 0x2763BC, 0x2763BE, 0x2763C0, 0x2763C2, 0x2763C4, 0x2763C6, 0x2763C8, 0x2763CA, 0x2763CC, 0x2763CE, 0x2763D0, 0x2763D2, 0x2763D4, 0x2763D6, 0x2763D8, 0x2763DA, 0x2763DC, 0x2763DE],
         "labels": [f"{i // 2 + 1} · {'local' if i % 2 == 0 else 'visit.'}" for i in range(32)],
         "empty_label": "ganador de la previa",
         "off": 0, "n": 32, "es": [14]},
        {"key": "champions_directos", "label": "Copa de Europa — clasificados directos",
         "off": 0x2763F0, "n": 8, "es": [2]},

        # La UEFA NO es una lista de 56 seguidas: el ejecutable la recorre en 5 trozos con
        # separadores a cero. Los límites salen del propio código (bucles `mov edi,ini` +
        # `cmp edi,fin`), no de mirar dónde hay equipos. Y los trozos tienen sentido: el
        # escalar es el campeón vigente (Schalke, ganador del 96/97) y los 3 de la Intertoto
        # son Lyon, Bastia y Auxerre — los tres ganadores reales de la Intertoto del 97.
        {"key": "uefa_es", "label": "Copa de la UEFA — plazas españolas",
         "off": 0x276528, "n": 4, "es": [0, 1, 2, 3]},
        {"key": "uefa_campeon", "label": "Copa de la UEFA — campeón vigente",
         "off": 0x276530, "n": 1, "es": []},
        {"key": "uefa_principales", "label": "Copa de la UEFA — participantes",
         "off": 0x276538, "n": 23, "es": []},
        {"key": "uefa_intertoto", "label": "Copa de la UEFA — ganadores de la Intertoto",
         "off": 0x276568, "n": 3, "es": []},
        {"key": "uefa_resto", "label": "Copa de la UEFA — resto de participantes",
         "off": 0x276570, "n": 18, "es": []},
        # RONDA PREVIA de la Recopa: 30 plazas (15 cruces) justo antes de la lista de
        # participantes. Solo la mitad tiene equipo — 15 puestos y 15 a cero, que es
        # exactamente el número de clubes de la previa real que este juego no trae en su
        # base. Los emparejamientos NO coinciden con el sorteo del 97/98 (Legia jugó
        # contra Glenavon, no contra Kilmarnock), así que no se etiqueta local/visitante.
        {"key": "recopa_previa", "label": "Recopa — ronda previa (15 cruces)",
         "off": 0x2766F0, "n": 30, "es": [],
         "labels": [f"{i // 2 + 1} · {'A' if i % 2 == 0 else 'B'}" for i in range(30)],
         "empty_label": "sin equipo"},
        {"key": "recopa_full", "label": "Recopa — participantes",
         "off": 0x276730, "n": 17, "es": [1]},
        {"key": "intercontinental_pool", "label": "Sudamericanos (Intercontinental)",
         "off": 0x276080, "n": 23, "es": []},
    ],
    2461184: [
        # LIGA INGLESA: este manager la lleva entera (la edición Premier comparte motor).
        # 20/24/24/24 es justo la estructura real del 96/97, y cada bloque termina en seco.
        {"key": "eng_premier", "label": "Liga inglesa — Premier",
         "off": 0x23CD10, "n": 20, "es": []},
        {"key": "eng_div1", "label": "Liga inglesa — Division One",
         "off": 0x23CB80, "n": 24, "es": []},
        {"key": "eng_div2", "label": "Liga inglesa — Division Two",
         "off": 0x23CDC0, "n": 24, "es": []},
        {"key": "eng_div3", "label": "Liga inglesa — Division Three",
         "off": 0x23CE60, "n": 24, "es": []},
        # Participantes europeos AGRUPADOS POR PAÍS. Cada tramo tiene su propio bucle en
        # el código, y de ahí salen los tamaños; entre tramos hay huecos que no son plazas.
        {"key": "europa_por_pais", "label": "Participantes europeos por país",
         "offs": [0x23DC00, 0x23DC04, 0x23DC08, 0x23DC0A, 0x23DC0C, 0x23DC10, 0x23DC12, 0x23DC14, 0x23DC16, 0x23DC18, 0x23DC1A, 0x23DC20, 0x23DC22, 0x23DC24, 0x23DC26, 0x23DC28, 0x23DC30, 0x23DC32, 0x23DC34, 0x23DC36, 0x23DC38, 0x23DC3A, 0x23DC3C, 0x23DC40, 0x23DC42, 0x23DC44, 0x23DC46, 0x23DC48, 0x23DC4A],
         "labels": ['España', 'España', 'Francia', 'Francia', 'Francia', 'Alemania', 'Alemania', 'Portugal', 'Portugal', 'Holanda', 'Holanda', 'Italia', 'Italia', 'Italia', 'Italia', 'Italia', 'Inglaterra', 'Inglaterra', 'Inglaterra', 'Inglaterra', 'Turquía', 'Turquía', 'Turquía', 'Escocia', 'Escocia', 'Polonia', 'Polonia', 'Austria', 'Austria'],
         "off": 0, "n": 29, "es": [0, 1]},
        {"key": "copa_rey_1a2a", "label": "Copa del Rey — bombo de 1ª y 2ª",
         "off": 0x23D480, "n": 39, "es": []},
        {"key": "copa_rey_2b", "label": "Copa del Rey — bombo de 2ªB",
         "off": 0x23D520, "n": 64, "es": []},
        # 16, no 17: la liguilla del 96/97 eran 4 grupos de 4 y la lista casa con ella
        # exactamente. El 17º repetía al Juventus, que ya está dentro — es el escalar del
        # campeón vigente (ganó la del 95/96), el mismo patrón que el Schalke en la UEFA de 6.0.
        {"key": "champions_full", "label": "Copa de Europa — participantes",
         "off": 0x23DFA0, "n": 16, "es": [12]},
        {"key": "champions_campeon", "label": "Copa de Europa — campeón vigente",
         "off": 0x23DFC0, "n": 1, "es": []},
        {"key": "uefa_full", "label": "Copa de la UEFA — participantes",
         "off": 0x23E318, "n": 64, "es": [6, 20, 53]},
        {"key": "recopa_full", "label": "Recopa — participantes",
         "off": 0x23E4E0, "n": 32, "es": [9]},
    ],
    # 6.0 Oro (2026-08-18). Localizadas por CONTENIDO, que es lo que las hace fiables: se
    # decodifican con los punteros canónicos de Dinamic (Barcelona=1, R.Madrid=4) y se
    # contrasta con la composición REAL de la 97-98, que es la temporada del juego. La de 40
    # da la Primera y Segunda de ese año; la Recopa da Chelsea, Stuttgart, Vicenza y Betis,
    # que es literalmente la Recopa 97-98 (la ganó el Chelsea).
    #
    # NO se incluye el cuadro de la Copa de Europa (0x27D880): ahí los equipos van
    # INTERCALADOS con huecos —parece el cuadro de eliminatorias, no una lista— y no se
    # puede acotar con la misma certeza. Antes de escribir en el manager.exe de nadie,
    # mejor dejar fuera lo que no se entiende del todo.
    2662400: [
        {"key": "copa_rey_1a2a", "label": "Copa del Rey — bombo de 1ª y 2ª",
         "off": 0x27CD68, "n": 40, "es": []},
        {"key": "copa_rey_2b", "label": "Copa del Rey — bombo de 2ªB",
         "off": 0x27CE08, "n": 64, "es": []},
        {"key": "champions_prev", "label": "Copa de Europa — 1ª ronda previa (15 cruces)",
         "off": 0x27D838, "n": 30, "es": [],
         # 15 cruces de 4 B, como la 2ª previa. Aquí NO se etiqueta local/visitante: el
         # orden de los dos equipos no casa con el del sorteo real y no se puede afirmar.
         "labels": [f"{i // 2 + 1} · {'A' if i % 2 == 0 else 'B'}" for i in range(30)],
         "empty_label": "sin equipo"},
        # Los CLASIFICADOS DIRECTOS: lista densa de 8, sin huecos, con los cabezas de
        # serie del 97-98 (Dortmund vigente campeón, Juventus finalista, Madrid, Mónaco,
        # Bayern, PSV, Oporto y Man Utd). Justo antes hay un CUADRO de eliminatorias
        # —parejas (equipo, equipo) donde el 0 es "el ganador de la ronda anterior"— que
        # NO se mapea: es un bracket, no una lista, y escribir ahí exige entender el
        # emparejamiento.
        # 2ª RONDA PREVIA: 16 cruces de 4 bytes, (local, visitante). Los ceros NO son
        # plazas vacías: son la plaza que ocupará el ganador de la previa, que el juego
        # resuelve al simular — por eso hay 15 (los 15 ganadores de los 30 de la previa) y
        # el único cruce con los dos equipos puestos es Salzburg–Sparta, que entran
        # directos a esta ronda. La plaza española 1 es el local del cruce 8.
        {"key": "champions_previa2", "label": "Copa de Europa — 2ª ronda previa (16 cruces)",
         "offs": [0x27D878, 0x27D87A, 0x27D87C, 0x27D87E, 0x27D880, 0x27D882, 0x27D884, 0x27D886, 0x27D888, 0x27D88A, 0x27D88C, 0x27D88E, 0x27D890, 0x27D892, 0x27D894, 0x27D896, 0x27D898, 0x27D89A, 0x27D89C, 0x27D89E, 0x27D8A0, 0x27D8A2, 0x27D8A4, 0x27D8A6, 0x27D8A8, 0x27D8AA, 0x27D8AC, 0x27D8AE, 0x27D8B0, 0x27D8B2, 0x27D8B4, 0x27D8B6],
         "labels": [f"{i // 2 + 1} · {'local' if i % 2 == 0 else 'visit.'}" for i in range(32)],
         "empty_label": "ganador de la previa",
         "off": 0, "n": 32, "es": [14]},
        {"key": "champions_directos", "label": "Copa de Europa — clasificados directos",
         "off": 0x27D8C8, "n": 8, "es": [2]},

        # La tabla EMPIEZA en 0x27DA00, con las 4 plazas españolas al principio (mismas
        # que edita EUROCUPS_MAP["uefa"], igual que en 5.0 Oro: la lista completa las
        # incluye y las marca en `es`). Son 56 plazas y no 64 como en 5.0 — esa tabla es
        # más corta en este build, no está truncada. Antes de 0x27DA00 hay texto.
        # La UEFA NO es una lista de 56 seguidas: el ejecutable la recorre en 5 trozos con
        # separadores a cero. Los límites salen del propio código (bucles `mov edi,ini` +
        # `cmp edi,fin`), no de mirar dónde hay equipos. Y los trozos tienen sentido: el
        # escalar es el campeón vigente (Schalke, ganador del 96/97) y los 3 de la Intertoto
        # son Lyon, Bastia y Auxerre — los tres ganadores reales de la Intertoto del 97.
        {"key": "uefa_es", "label": "Copa de la UEFA — plazas españolas",
         "off": 0x27DA00, "n": 4, "es": [0, 1, 2, 3]},
        {"key": "uefa_campeon", "label": "Copa de la UEFA — campeón vigente",
         "off": 0x27DA08, "n": 1, "es": []},
        {"key": "uefa_principales", "label": "Copa de la UEFA — participantes",
         "off": 0x27DA10, "n": 23, "es": []},
        {"key": "uefa_intertoto", "label": "Copa de la UEFA — ganadores de la Intertoto",
         "off": 0x27DA40, "n": 3, "es": []},
        {"key": "uefa_resto", "label": "Copa de la UEFA — resto de participantes",
         "off": 0x27DA48, "n": 18, "es": []},
        # RONDA PREVIA de la Recopa: 30 plazas (15 cruces) justo antes de la lista de
        # participantes. Solo la mitad tiene equipo — 15 puestos y 15 a cero, que es
        # exactamente el número de clubes de la previa real que este juego no trae en su
        # base. Los emparejamientos NO coinciden con el sorteo del 97/98 (Legia jugó
        # contra Glenavon, no contra Kilmarnock), así que no se etiqueta local/visitante.
        {"key": "recopa_previa", "label": "Recopa — ronda previa (15 cruces)",
         "off": 0x27DBC8, "n": 30, "es": [],
         "labels": [f"{i // 2 + 1} · {'A' if i % 2 == 0 else 'B'}" for i in range(30)],
         "empty_label": "sin equipo"},
        {"key": "recopa_full", "label": "Recopa — participantes",
         "off": 0x27DC08, "n": 17, "es": [1]},
        {"key": "intercontinental_pool", "label": "Sudamericanos (Intercontinental)",
         "off": 0x27D558, "n": 23, "es": []},
    ],
}


def _desplazada(tablas: list[dict], delta: int) -> list[dict]:
    """Las mismas tablas de otro build, corridas `delta` bytes.

    Se DERIVAN en vez de copiarse a mano: son 13 tablas con 293 punteros y hasta una lista
    de 32 offsets sueltos, y una cifra mal transcrita aquí se escribe dentro del código del
    ejecutable. Derivarlas hace imposible ese error; lo que hay que comprobar es el delta,
    y eso se hace leyendo las dos y exigiendo que digan lo mismo."""
    out = []
    for t in tablas:
        t2 = dict(t)
        if t.get("offs"):
            t2["offs"] = [o + delta for o in t["offs"]]
        if t.get("off"):                      # `off` 0 = tabla de posiciones sueltas
            t2["off"] = t["off"] + delta
        out.append(t2)
    return out


# PCF 6.0 BASE (manager de 2.617.344 B). Petición del foro (20-sep-2026): en la
# 6.0 base solo se podían tocar las plazas españolas y las dos copas de dos equipos, porque
# este build tenía mapeadas las plazas sueltas (EUROCUPS_MAP) pero NO las listas completas.
# Son las mismas tablas que el build Oro con el desplazamiento CONSTANTE de -0x8D48 —el que
# ya usaba EUROCUPS_MAP para este build—, y aquí se ha vuelto a verificar de forma
# independiente: las 13 tablas leen EXACTAMENTE los mismos 293 punteros que en Oro, incluidas
# las plazas vacías, una por una.
TOURNAMENT_LISTS[2617344] = _desplazada(TOURNAMENT_LISTS[2662400], -0x8D48)


# Los ASCENDIDOS son una lista aparte de 3 plazas justo detrás de la tabla de Primera:
# en 5.0 van en otro orden que en la tabla, así que no es una repetición del final sino
# una lista propia (5.0: Hércules/Extremadura/Logroñés · 6.0: Mérida/Salamanca/Mallorca).
#   6.0 BASE 0x274310: el mismo delta -0x8D48 de las otras tablas de esta zona, y además
#   los 6 bytes (Mérida/Salamanca/Mallorca) están ahí tal cual.
ASCENDIDOS_OFF: dict[int, int] = {2461184: 0x23D740, 2662400: 0x27D058, 2630144: 0x275B80,
                                  2617344: 0x274310}


# Lista FIJA de clubes europeos, una por país, en `.rdata` (o sea: constante, el juego no
# la reescribe nunca). El final sale del código: `mov eax, 0x64D908` = 120 entradas.
#   6.0 BASE: 0x245560. OJO — aquí el desplazamiento respecto a Oro es -0x74B8 y NO el
#   -0x8D48 de las copas: cada zona del ejecutable se mueve lo suyo, así que esta tabla se
#   localizó BUSCANDO SUS 240 BYTES en el binario (una única coincidencia), no aplicando el
#   delta de al lado. Con el delta equivocado se escribiría en medio del código.
EUROPEOS_OFF: dict[int, int] = {2662400: 0x24CA18, 2630144: 0x247C48, 2617344: 0x245560}

# Clubes destacados de cada país del mundo (sudamericanos incluidos), en `.data`. El formato
# lo dice el propio dato: [código de país u16][sus clubes][0], repetido — la "cabecera" que
# parecía un equipo español era el país. 39 países en los tres builds.
#   6.0 BASE: 0x2768C8, localizado igual (por sus bytes, coincidencia única). Aquí el
#   desplazamiento sí resulta ser -0x8D48, el mismo que las copas, pero eso se comprobó, no
#   se dio por hecho (ver la nota de EUROPEOS_OFF).
CLUBES_PAIS_INI: dict[int, int] = {2662400: 0x27F610, 2630144: 0x278138, 2461184: 0x2414A0,
                                   2617344: 0x2768C8}


def _tabla_europeos(size: int) -> list[dict]:
    off = EUROPEOS_OFF.get(size)
    if off is None:
        return []
    return [{"key": "europeos_fijos", "label": "Clubes europeos (lista fija por país)",
             "off": off, "n": 120, "es": [], "empty_label": "sin equipo"}]


def _tabla_clubes_pais(data: bytes) -> list[dict]:
    """Recorre [país][clubes][0] y devuelve UNA tabla con solo las plazas de club, cada una
    etiquetada con su país. Se parsea sobre el fichero porque la longitud de cada país varía."""
    from .. import refdata
    ini = CLUBES_PAIS_INI.get(len(data))
    if ini is None:
        return []
    paises = {p["pointer"]: p["name"] for p in refdata.countries()}
    validos = {t["pointer"] for t in refdata.community_pointers()}
    offs: list[int] = []
    etiquetas: list[str] = []
    off = ini
    while off + 4 < len(data):
        pais = struct.unpack_from("<H", data, off)[0]
        if pais not in paises:
            break
        o = off + 2
        tramo: list[int] = []
        while o + 2 < len(data):
            v = struct.unpack_from("<H", data, o)[0]
            if v == 0:
                break
            if v not in validos:      # dato inesperado: se corta en seco, sin inventar
                return []
            tramo.append(o)
            o += 2
        if not tramo:
            break
        offs.extend(tramo)
        etiquetas.extend([paises[pais]] * len(tramo))
        off = o + 2
    if not offs:
        return []
    # `solo_equipos`: esta tabla DEDUCE SU ESTRUCTURA DE SU PROPIO CONTENIDO —recorre
    # [país][clubes][0]—, así que un valor que no sea un equipo conocido desplazaría el
    # recorrido y la tabla ya no se podría volver a leer ni deshacer. Las de offset fijo no
    # tienen ese problema. Lo destapó el round-trip: escribir y restaurar dejaba 130 bytes
    # cambiados (en los tres builds, no solo en el nuevo).
    return [{"key": "clubes_por_pais", "label": "Clubes destacados por país",
             "offs": offs, "labels": etiquetas, "off": 0, "n": len(offs), "es": [],
             "solo_equipos": True}]


def _tablas_de_liga(size: int) -> list[dict]:
    """Las divisiones españolas COMO TABLAS del panel, desde los offsets que ya usa
    `DIVISION_MAP` para leerlas. No son competiciones, pero están en el manager.exe y el
    editor tiene que enseñar lo que hay dentro."""
    m = DIVISION_MAP.get(size)
    if not m:
        return []
    out: list[dict] = []
    for clave, etiqueta in (("primera", "Liga — Primera División"),
                            ("segunda", "Liga — Segunda División")):
        off, n = m[clave]
        out.append({"key": f"liga_{clave}", "label": etiqueta, "off": off, "n": n, "es": []})
    off, por_grupo, grupos = m["grupos2b"]
    for gi in range(grupos):
        out.append({"key": f"liga_2b_g{gi + 1}",
                    "label": f"Liga — Segunda B, grupo {'I' * (gi + 1) if gi < 3 else 'IV'}",
                    "off": off + gi * por_grupo * 2, "n": por_grupo, "es": []})
    asc = ASCENDIDOS_OFF.get(size)
    if asc:
        out.append({"key": "liga_ascendidos", "label": "Liga — recién ascendidos",
                    "off": asc, "n": 3, "es": []})
    return out


def tournament_lists_read(data: bytes) -> list[dict] | None:
    """Listas completas del build (punteros canónicos), o None si no está mapeado.
    `es` = índices que son la plaza española (los que ya se editan en Competiciones)."""
    lista = TOURNAMENT_LISTS.get(len(data))
    if lista is None:
        return None
    lista = (list(lista) + _tablas_de_liga(len(data))
             + _tabla_europeos(len(data)) + _tabla_clubes_pais(data))
    out = []
    for t in lista:
        # una tabla puede ser CONTIGUA (off + n) o de posiciones SUELTAS (`offs`). Lo
        # segundo hace falta para el cuadro de la Copa de Europa, donde los equipos no van
        # seguidos sino repartidos por las eliminatorias.
        offs = t.get("offs") or [t["off"] + 2 * i for i in range(t["n"])]
        if max(offs) + 2 > len(data):
            continue
        out.append({**{k: t[k] for k in ("key", "label", "es")},
                    "labels": t.get("labels") or [],
                    "empty_label": t.get("empty_label") or "",
                    "pointers": [struct.unpack_from("<H", data, o)[0] for o in offs]})
    return out


_ESPEJOS: dict[int, dict] = {}


def _espejos(build: int) -> dict[tuple[str, int], list[int]]:
    """`{(clave de tabla, índice): [offsets SUELTOS con el mismo equipo]}`.

    Algunas plazas están escritas DOS VECES en el ejecutable: dentro de la lista de
    participantes y además en un sitio suelto que el juego lee por su cuenta. Pasa con la
    plaza española de la Recopa y con la segunda de la Copa de Europa.

    Ya lo sabíamos por `EUROCUPS_MAP` —sus slots llevan los dos offsets justo por esto, y
    `eurocups_write` escribe ambos—, pero al abrir las LISTAS COMPLETAS se coló el problema
    por el otro lado: cambiar la plaza española desde la tarjeta de participantes escribía
    la lista y dejaba el sitio suelto con el equipo de fábrica, o sea el juego
    contradiciéndose consigo mismo (destapado por el aviso de un usuario en el foro,
    21-sep-2026).

    Se DERIVA de `EUROCUPS_MAP` en vez de transcribirse: cualquier offset de un slot que no
    caiga dentro de una tabla es un espejo de los que sí caen. Así no hay dos listas de
    números que puedan separarse, que es como se escriben cifras mal dentro del código de un
    ejecutable.
    """
    if build in _ESPEJOS:
        return _ESPEJOS[build]
    tablas = TOURNAMENT_LISTS.get(build)
    em = EUROCUPS_MAP.get(build)
    out: dict[tuple[str, int], list[int]] = {}
    if tablas and em:
        # (offset -> (clave, índice)) de todas las posiciones de las tablas del build
        donde: dict[int, tuple[str, int]] = {}
        for t in list(tablas) + _tablas_de_liga(build) + _tabla_europeos(build):
            offs = t.get("offs") or [t["off"] + 2 * i for i in range(t["n"])]
            for i, o in enumerate(offs):
                donde.setdefault(o, (t["key"], i))
        for slots in em.values():
            for offs in slots:
                if len(offs) < 2:
                    continue
                dentro = [donde[o] for o in offs if o in donde]
                sueltos = [o for o in offs if o not in donde]
                for sitio in dentro:
                    out.setdefault(sitio, []).extend(sueltos)
    _ESPEJOS[build] = out
    return out


def eurocup_keys_cubiertas(build: int) -> set:
    """Claves de `EUROCUPS_MAP` que las LISTAS COMPLETAS de ese build ya editan enteras.

    Desde que se abrieron las listas de participantes hay dos sitios para lo mismo: la plaza
    española de la Recopa, las dos de la Copa de Europa y las cuatro de la UEFA salen tanto
    en la tarjeta de copas europeas como dentro de su lista completa. Dos mandos para el
    mismo interruptor confunden —un usuario escribió al foro creyendo que faltaban cosas— y además
    se contradicen en pantalla, porque cada tarjeta se refresca por su cuenta.

    Así que se calcula cuáles están YA cubiertas y esas dejan de ofrecerse por duplicado. Lo
    que no cubre ninguna lista —los finalistas de la Supercopa de España, la de Europa y la
    Intercontinental, que son dos equipos sueltos y no una tabla— se sigue editando donde
    siempre. Cubierta = TODAS sus plazas caen dentro de alguna tabla; con que una se quede
    fuera, la clave se mantiene o esa plaza se volvería inaccesible.
    """
    tablas = TOURNAMENT_LISTS.get(build)
    em = EUROCUPS_MAP.get(build)
    if not tablas or not em:
        return set()
    dentro = set()
    for t in list(tablas) + _tablas_de_liga(build) + _tabla_europeos(build):
        offs = t.get("offs") or [t["off"] + 2 * i for i in range(t["n"])]
        dentro.update(offs)
    return {key for key, slots in em.items()
            if all(any(o in dentro for o in offs) for offs in slots)}


def tournament_lists_write(data: bytearray, values: dict[str, list[int]]) -> int:
    """Escribe listas completas. Se respeta la LONGITUD de cada tabla (es fija: el
    juego lee N entradas); las posiciones que no vengan se dejan como estaban.

    Las plazas que el ejecutable guarda por duplicado se escriben en los DOS sitios (ver
    `_espejos`): si no, el juego acaba con dos respuestas distintas a la misma pregunta."""
    lista = TOURNAMENT_LISTS.get(len(data))
    if lista is None:
        return 0
    espejos = _espejos(len(data))
    porclave = {t["key"]: t for t in (list(lista) + _tablas_de_liga(len(data))
                                      + _tabla_europeos(len(data))
                                      + _tabla_clubes_pais(data))}
    escritos = 0
    for key, ptrs in (values or {}).items():
        t = porclave.get(key)
        if t is None:
            continue
        offs = t.get("offs") or [t["off"] + 2 * i for i in range(t["n"])]
        if max(offs) + 2 > len(data):
            continue
        # Tabla que se parsea a sí misma (ver `solo_equipos`): solo admite punteros de
        # equipos REALES, porque cualquier otra cosa le rompe el recorrido y la deja
        # ilegible. En las de offset fijo no hace falta y no se pide.
        validos = None
        if t.get("solo_equipos"):
            from .. import refdata
            validos = {x["pointer"] for x in refdata.community_pointers()}
        for i, v in enumerate(ptrs[:len(offs)]):
            if v is None or not (0 < int(v) <= 0xFFFF):
                continue
            if validos is not None and int(v) not in validos:
                continue
            struct.pack_into("<H", data, offs[i], int(v))
            escritos += 1
            # y su copia suelta, si esa plaza está escrita dos veces en el ejecutable
            for o in espejos.get((key, i), ()):
                if o + 2 <= len(data):
                    struct.pack_into("<H", data, o, int(v))
    return escritos


# ---------------------------------------------------------------------------
# LÍMITES DEL MOTOR (2026-08-16). A diferencia de las restricciones de arriba, que se
# quitan neutralizando un salto, estos son NÚMEROS: funciones minúsculas del tipo
# `mov eax, N; ret` que devuelven el tope. Se cambia el inmediato y ya.
#
# Los publicó el hilo "Modificando Restricciones" de pcfutbolmania para la 5.0 BASE
# (manager de 2.507.264 bytes, donde casan exactamente;
# ojo, el hilo da 0x53045 para los extracomunitarios y el bueno es 0x53050).
# En NUESTRO 5.0 Oro las mismas funciones están en otro sitio: se localizaron por su
# patrón —la racha 6, 4, 3, 1 con idéntica separación entre ellas (0x20 y 0x10)— y
# aparece una sola vez en el fichero.
# En los builds de 6.0 no hay ninguna pareja 6→4 cercana: ahí no están mapeados.
# EXPERIMENTAL: la correspondencia es estructural, no verificada en juego.
# ---------------------------------------------------------------------------
# Cada tope = uno o VARIOS sitios, porque a veces el número está en la comprobación y
# otra vez en el texto del aviso: `sites` = [(offset, ancho en bytes)]. Si solo se
# cambiara la comprobación, el juego levantaría el tope pero seguiría diciendo "5".
#
# CÓMO SE LOCALIZARON (método bueno, 2026-08-16): por el MENSAJE, no por offsets de
# terceros. Cada regla lleva su aviso al lado ("La directiva sólo te deja hacer %u
# oferta%s"), y los textos SÍ son comunes a todos los builds aunque el código se mueva.
# Se busca la frase, se mira qué código la usa y a un par de instrucciones está el
# número. En v5/6 los topes de extracomunitarios son además funciones virtuales
# `mov eax,N; ret` enlazadas en la tabla junto al getter del mensaje.
LIMITS: dict[int, list[dict]] = {
    2461184: [                                   # PCF 5.0 Edición de Oro
        {"key": "extracom_fichar", "label": "Extracomunitarios en plantilla",
         "help": "Cuántos jugadores de fuera de la UE puedes tener fichados. El juego "
                 "avisa: «Ya tienes en tu plantilla a seis extracomunitarios, que es el "
                 "número máximo. No puedes contratar a más.»",
         "sites": [(0x2AB80 + 1, 4)], "factory": 6, "min": 0, "max": 99},
        {"key": "extracom_alinear", "label": "Extracomunitarios en el once",
         "help": "Cuántos puedes alinear a la vez. El juego avisa: «Ya has alineado "
                 "cuatro extracomunitarios, que es el número máximo. No puedes alinear más.»",
         "sites": [(0x2ABA0 + 1, 4)], "factory": 4, "min": 0, "max": 99},
        # Aquí el tope NO está incrustado en el código: es una VARIABLE en .data que el
        # juego lee tanto para comprobar como para escribir el número en el aviso. Un solo
        # sitio y se cambian las dos cosas a la vez. (El parche del foro «73 49 → EB 00»
        # ataca el salto que la usa; nuestro build tiene ese mismo salto en 0x15E115, pero
        # tocar el número es menos invasivo y deja el aviso coherente.)
        {"key": "ofertas", "label": "Ofertas por semana",
         "help": "«La directiva sólo te deja hacer N ofertas o contratar a un jugador a "
                 "la semana.» El aviso enseña este mismo número.",
         "sites": [(0x248068, 4)], "factory": 5, "min": 1, "max": 99},
    ],
    2662400: [                                   # PCF 6.0 Edición de Oro
        {"key": "extracom_fichar", "label": "Extracomunitarios en plantilla",
         "help": "Cuántos jugadores de fuera de la UE puedes tener fichados.",
         "sites": [(0x8700 + 1, 4)], "factory": 6, "min": 0, "max": 99},
        {"key": "extracom_alinear", "label": "Extracomunitarios en el once",
         "help": "Cuántos puedes alinear a la vez.",
         "sites": [(0xE1CB0 + 1, 4)], "factory": 4, "min": 0, "max": 99},
        {"key": "ofertas", "label": "Ofertas por semana",
         "help": "«La directiva sólo te deja hacer N ofertas o contratar a un jugador a "
                 "la semana.» Se cambian a la vez la comprobación y el número del aviso.",
         "sites": [(0x42396, 1), (0x423CC, 1), (0x42EEC, 1), (0x42F27, 1)],
         "factory": 5, "min": 1, "max": 99},
    ],
}


def limits_read(data: bytes) -> list[dict] | None:
    """Límites del build con su valor actual, o None si no está mapeado."""
    lista = LIMITS.get(len(data))
    if lista is None:
        return None
    out = []
    for lim in lista:
        o, ancho = lim["sites"][0]
        if o + ancho > len(data):
            continue
        v = data[o] if ancho == 1 else struct.unpack_from("<I", data, o)[0]
        out.append({**{k: lim[k] for k in ("key", "label", "help", "factory", "min", "max")},
                    "value": v})
    return out


def limits_write(data: bytearray, values: dict[str, int]) -> int:
    """Fija los límites indicados (inmediato u32 del `mov eax`). Solo escribe donde el
    valor actual es plausible: si no lo es, este no es el build que creemos y no se toca."""
    lista = LIMITS.get(len(data))
    if lista is None:
        return 0
    por_clave = {x["key"]: x for x in lista}
    n = 0
    for key, v in (values or {}).items():
        lim = por_clave.get(key)
        if lim is None or v is None:
            continue
        val = max(lim["min"], min(int(v), lim["max"]))
        # todos los sitios de un tope deben ser plausibles ANTES de tocar ninguno: si uno
        # solo no lo es, este no es el build que creemos y se deja el fichero como está.
        sitios = []
        for o, ancho in lim["sites"]:
            if o + ancho > len(data):
                sitios = []
                break
            actual = data[o] if ancho == 1 else struct.unpack_from("<I", data, o)[0]
            if not (0 <= actual <= 999) or (ancho == 1 and val > 255):
                sitios = []
                break
            sitios.append((o, ancho))
        for o, ancho in sitios:
            if ancho == 1:
                data[o] = val & 0xFF
            else:
                struct.pack_into("<I", data, o, val)
        if sitios:
            n += 1
    return n


def division_slots(data: bytes) -> dict | None:
    """Plazas (punteros canónicos) de cada división NATIVA del juego, en orden.
    {"primera":[...], "segunda":[...], "grupos2b":[[g1],[g2],[g3],[g4]]}."""
    m = DIVISION_MAP.get(len(data))
    if m is None:
        return None

    def read(off, n):
        return [struct.unpack_from("<H", data, off + i * 2)[0] for i in range(n)]

    def uniq(seq):
        # red de seguridad anti-duplicados (por si un offset quedara medio byte corrido, como
        # pasó en G1 de 6.0 Oro Futbol6): con los offsets correctos no elimina nada.
        seen: set = set()
        return [x for x in seq if not (x in seen or seen.add(x))]

    po, pn = m["primera"]
    so, sn = m["segunda"]
    go, gn, gk = m["grupos2b"]
    return {
        "primera": uniq(read(po, pn)),
        "segunda": uniq(read(so, sn)),
        "grupos2b": [uniq(read(go + gi * gn * 2, gn)) for gi in range(gk)],
    }


# ---------------------------------------------------------------------------
# PAÍSES QUE EL JUEGO OFRECE (2-sep-2026)
#
# La BASE dice qué equipos hay; el `manager.exe` dice qué se OFRECE. Es el mismo patrón que
# las divisiones, el año y las copas europeas, y explica una pregunta vieja del foro:
# Andorra existe en la base —con su club y sus jugadores— pero el juego no la ofrece en
# ninguna pantalla por muchos equipos que se le añadan.
#
# Son listas de códigos de país de UN BYTE, terminadas en `00`. En 6.0 hay dos, seguidas:
# Sudamérica (10) y Europa (47), con 38 bytes a cero entre ellas. En 5.0 solo está la europea.
# Los offsets se BUSCARON por estructura —un tramo de bytes distintos que son todos códigos de
# país CON EQUIPOS en esa misma base— y se comprobó lo que importa: de los que aparecen en la
# lista, NI UNO carece de equipos. Los que tienen equipos y NO están son los diez sudamericanos
# (que van en su propia lista), USA, Islas Feroe y Andorra.
#
# LÍMITE: la lista europea está pegada a datos de punteros —el `00` que la cierra es ya el
# primer byte del siguiente—, así que NO se puede alargar en su sitio; solo cambiar unos países
# por otros. Los 38 bytes libres están entre las dos tablas.
# PENDIENTE VALIDAR EN VM: que la pantalla lea la lista y no un número escrito en el código.
# ---------------------------------------------------------------------------
COUNTRY_MAP: dict[int, dict] = {
    2507264: {"europa": (2157384, 34)},                                   # 5.0 original
    2461184: {"europa": (2232077, 36)},                                   # 5.0 Oro
    2617344: {"sudamerica": (2346856, 10), "europa": (2346904, 47)},      # 6.0 original
    2662400: {"sudamerica": (2382616, 10), "europa": (2382664, 47)},      # 6.0 Oro
}


def country_slots(data: bytes) -> dict | None:
    """{grupo: [códigos de país]} de las listas que ofrece el juego. None si no se conoce
    este build."""
    m = COUNTRY_MAP.get(len(data))
    if m is None:
        return None
    return {g: list(data[off:off + n]) for g, (off, n) in m.items()}


def countries_write(data: bytearray, grupos: dict) -> bool:
    """Reescribe las listas de países. Cada una debe traer EXACTAMENTE sus mismas plazas: la
    tabla no se puede alargar sin moverla, y moverla es otro trabajo (hay que repuntar quien la
    referencia). Devuelve True si escribió algo."""
    m = COUNTRY_MAP.get(len(data))
    if m is None:
        return False
    hecho = False
    for grupo, codigos in (grupos or {}).items():
        sitio = m.get(grupo)
        if not sitio:
            continue
        off, n = sitio
        vals = [int(c) & 0xFF for c in codigos][:n]
        if len(vals) != n or 0 in vals or len(set(vals)) != n:
            continue                      # ni huecos ni repetidos: el juego los recorre en orden
        data[off:off + n] = bytes(vals)
        hecho = True
    return hecho


def _write_table(data: bytearray, file_off: int, ptrs: list[int]) -> None:
    for i, p in enumerate(ptrs):
        struct.pack_into("<H", data, file_off + i * 2, p & 0xFFFF)


def patch_spain(data: bytearray, primera: list[int], segunda: list[int],
                grupos2b: list[list[int]]) -> bool:
    """Reescribe las divisiones españolas del manager.exe con los punteros dados
    y sus contadores objetivo (20 / 22 / 18×4). Reubica Segunda al hueco si su
    objetivo excede la tabla original. Devuelve True si parcheó."""
    m = SPAIN_MAP.get(len(data))
    if m is None:
        return False

    # PRIMERA: cabe siempre (objetivo 20 ≤ 22). Escribir y fijar contador.
    p = m["primera"]
    n = min(len(primera), p["cap"])
    _write_table(data, p["table"], primera[:n])
    data[p["count_off"]] = n

    # SEGUNDA: objetivo 22 > tabla original (20) → reubicar al hueco de .rdata.
    sg = m["segunda"]
    n = len(segunda)
    if n <= sg["cap"]:
        _write_table(data, sg["table"], segunda)
        data[sg["count_off"]] = n
    else:
        cave = m["cave"]
        if n * 2 + 2 > cave["size"]:
            n = (cave["size"] - 2) // 2
            segunda = segunda[:n]
        _write_table(data, cave["file"], segunda)
        struct.pack_into("<H", data, cave["file"] + n * 2, 0)  # terminador
        struct.pack_into("<I", data, sg["addr_off"], cave["va"] & 0xFFFFFFFF)
        data[sg["count_off"]] = n

    # 2ªB: 4 grupos contiguos (stride) con contador compartido.
    g = m["grupos2b"]
    tgt = min(TARGET["grupos2b"], g["stride"])
    for gi, ptrs in enumerate(grupos2b[:g["groups"]]):
        base = g["table"] + gi * g["stride"] * 2
        _write_table(data, base, ptrs[:tgt])
    data[g["count_off"]] = tgt
    return True
