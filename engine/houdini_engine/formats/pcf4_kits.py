"""Camisetas del SIMULADOR 2D de PCF 4 — `PALETAS/EQUIPOS.DAT`.

Info de la comunidad (verificado 2026-07-16):
- Fichero = **bloques de 190 bytes**, cada uno = UNA equipación. Firma `90 51 52 53 54 55 56 3E`
  (`.QRSTUV>`, 8 B) + **182 bytes de ÍNDICES de color** de la paleta del simulador
  (`refdata/pcf4_palette_sim.json` — la misma que el escudo `.EMP`).
- **2 equipaciones por equipo**: equipo N (1-based) → kit1 = bloque `2*(N-1)`, kit2 = `2*(N-1)+1`.
  Dirección = `190 * bloque`.
- Los bytes son colores: 0x81-0x84 rojos, 0x8A-0x8C azules, 0x60 negro (botas)… No se renderiza como
  bitmap (mapeo byte→píxel planar "enrevesado", sin descifrar), así que la edición es por **RECOLOR de
  índices** (cambiar un color por otro), que es como lo hace la comunidad.
"""
from __future__ import annotations

from collections import Counter

BLOCK = 190
HEADER = 8            # 90 51 52 53 54 55 56 3E
COLOR_OFF = HEADER
_SIG = bytes([0x51, 0x52, 0x53, 0x54, 0x55, 0x56])   # "QRSTUV"


def kit_count(data: bytes) -> int:
    return len(data) // BLOCK


def team_blocks(team_n: int) -> tuple[int, int]:
    """Índices de bloque de las 2 equipaciones de un equipo (N 1-based = EQ95NNNN)."""
    return (2 * (team_n - 1), 2 * (team_n - 1) + 1)


def is_valid(data: bytes) -> bool:
    """Comprueba que parece un EQUIPOS.DAT (firma QRSTUV al inicio de los bloques)."""
    return len(data) >= BLOCK and data[1:7] == _SIG and len(data) % BLOCK == 0


def color_bytes(data: bytes, block_idx: int) -> bytes:
    a = block_idx * BLOCK + COLOR_OFF
    return data[a:a + (BLOCK - HEADER)]


def colors_used(data: bytes, block_idx: int) -> list[tuple[int, int]]:
    """[(índice_color, nº de bytes)] de un bloque, más usados primero."""
    return Counter(color_bytes(data, block_idx)).most_common()


# --- FAMILIAS de color AUTODETECTADAS de la paleta del simulador ------------------------------
# La paleta del sim NO tiene rangos fijos: los degradados (rampas) están repartidos por toda la
# tabla (verde en 0x8F, 0xB7, 0xE2…; hay naranja, turquesa, magenta…). Antes se hardcodeaban 9
# rangos adivinados y colores reales (p.ej. el verde 0xE2-0xE8 de la 2ª del Barça) NO salían en el
# selector aunque SÍ se veían. Ahora se DETECTAN las rampas de la propia paleta: un color usado en
# una camiseta SIEMPRE cae en una familia seleccionable.
import colorsys

_HUE_NAMES = [(15, "rojo"), (40, "naranja"), (68, "amarillo"), (160, "verde"),
              (195, "turquesa"), (252, "azul"), (300, "morado"), (338, "magenta"), (361, "rojo")]


def _hsv(palette, i):
    r, g, b = _rgb(palette, i)
    return colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)


def _bucket(palette, i) -> str:
    h, s, v = _hsv(palette, i)
    if s < 0.15:
        return "gris"
    deg = h * 360
    for hi, name in _HUE_NAMES:
        if deg < hi:
            return name
    return "rojo"


def _detect_ramps(palette) -> list[list[int]]:
    """Segmenta la paleta (0x60-0xFF, la zona de camisetas) en rampas = tramos consecutivos del
    MISMO tono cuyo brillo crece (un degradado). Corta al cambiar de tono o al resetear el brillo."""
    ramps: list[list[int]] = []
    cur: list[int] = []
    for i in range(0x60, 0x100):
        if not cur:
            cur = [i]
            continue
        pv = _hsv(palette, cur[-1])[2]
        v = _hsv(palette, i)[2]
        if _bucket(palette, i) == _bucket(palette, cur[-1]) and v >= pv - 0.06:
            cur.append(i)
        else:
            if len(cur) >= 2:
                ramps.append(cur)
            cur = [i]
    if len(cur) >= 2:
        ramps.append(cur)
    return ramps


def _ramps_cached(palette) -> list[list[int]]:
    key = id(palette)
    c = _RAMP_CACHE.get(key)
    if c is None:
        c = _detect_ramps(palette)
        _RAMP_CACHE[key] = c
    return c


_RAMP_CACHE: dict = {}


def _ramp_rep(ramp: list[int], palette) -> tuple[int, int, int]:
    """Color representativo de una rampa (un tono medio-alto, para el swatch)."""
    return _rgb(palette, ramp[len(ramp) * 2 // 3])


def _ramp_name(ramp: list[int], palette, ramps: list[list[int]]) -> str:
    """Nombre legible: color base + matiz claro/oscuro para desambiguar rampas del mismo tono."""
    base = _bucket(palette, ramp[len(ramp) // 2])
    v = _hsv(palette, ramp[len(ramp) * 2 // 3])[2]
    same = [r for r in ramps if _bucket(palette, r[len(r) // 2]) == base]
    if len(same) > 1:
        if v < 0.4:
            return base + " oscuro"
        if v > 0.72:
            return base + " claro"
    return base


def _index_to_ramp(palette) -> dict[int, list[int]]:
    out: dict[int, list[int]] = {}
    for r in _ramps_cached(palette):
        for i in r:
            out[i] = r
    return out


def families_used(data: bytes, block_idx: int, palette) -> list[dict]:
    """Familias de color usadas en el bloque → [{id, name, rgb, count}], más usadas primero.
    `id` = "R<inicio>" para una rampa detectada, "I<idx>" para un color suelto sin rampa (detalle)."""
    ramps = _ramps_cached(palette)
    i2r = _index_to_ramp(palette)
    ramp_by_start = {r[0]: r for r in ramps}
    cnt_ramp: Counter = Counter()
    cnt_single: Counter = Counter()
    for b in color_bytes(data, block_idx):
        r = i2r.get(b)
        if r is not None:
            cnt_ramp[r[0]] += 1
        else:
            cnt_single[b] += 1
    out = []
    for start, n in cnt_ramp.most_common():
        r = ramp_by_start[start]
        out.append({"id": f"R{start}", "name": _ramp_name(r, palette, ramps),
                    "rgb": list(_ramp_rep(r, palette)), "count": n})
    for idx, n in cnt_single.most_common():
        if n < 2:            # 1 px = ruido de antialias, se ignora
            continue
        out.append({"id": f"I{idx}", "name": "otro", "rgb": list(_rgb(palette, idx)), "count": n})
    return out


def ramp_swatches(palette) -> list[dict]:
    """Todas las familias de la paleta → [{id, name, rgb}] para el selector de color destino."""
    ramps = _ramps_cached(palette)
    return [{"id": f"R{r[0]}", "name": _ramp_name(r, palette, ramps),
             "rgb": list(_ramp_rep(r, palette))} for r in ramps]


def _shade_map(src: list[int], dst: list[int]) -> dict[int, int]:
    """Mapa índice→índice que lleva cada tono de la rampa `src` al tono correspondiente de `dst`
    (conserva el degradado: posición relativa dentro de la rampa)."""
    out = {}
    for k, si in enumerate(src):
        pos = k / (len(src) - 1) if len(src) > 1 else 0
        out[si] = dst[round(pos * (len(dst) - 1))]
    return out


def remap(data: bytes, block_idx: int, mapping: dict, palette=None) -> bytes:
    """Recolorea un bloque. `mapping` = {id_origen: id_destino} con ids "R<inicio>"/"I<idx>":
      - R→R: remapea TODOS los tonos de la rampa conservando el degradado.
      - I→R: el color suelto pasa al tono representativo de la rampa destino.
      - I→I: cambio de índice directo.
    (Compat: también admite {int: int}.) `palette` obligatoria salvo para ids enteros."""
    ramp_by_start = {}
    if palette is not None:
        ramp_by_start = {r[0]: r for r in _ramps_cached(palette)}

    def _resolve(tok):
        """Devuelve (tipo, valor): ('R', ramp_indices) o ('I', idx)."""
        if isinstance(tok, int):
            return ("I", tok)
        if tok and tok[0] == "R":
            return ("R", ramp_by_start.get(int(tok[1:]), []))
        if tok and tok[0] == "I":
            return ("I", int(tok[1:]))
        return ("I", int(tok))

    idx_map: dict[int, int] = {}
    for k, v in mapping.items():
        ks, kv = _resolve(k)
        ds, dv = _resolve(v)
        dst_indices = dv if ds == "R" else [dv]
        if not dst_indices:
            continue
        if ks == "R":
            if not kv:
                continue
            idx_map.update(_shade_map(kv, dst_indices))
        else:                                   # color suelto → tono medio del destino
            idx_map[kv] = dst_indices[len(dst_indices) * 2 // 3]
    out = bytearray(data)
    a = block_idx * BLOCK + COLOR_OFF
    b = block_idx * BLOCK + BLOCK
    for i in range(a, b):
        nv = idx_map.get(out[i])
        if nv is not None:
            out[i] = nv & 0xFF
    return bytes(out)


# --- ZONAS ANATÓMICAS + PATRONES (CALIBRADOS) --------------------------------------------------
# Posiciones de textura (0-167 = offset dentro de los bytes de color) de cada región de la camiseta,
# calibradas contra 470 kits reales. Portado de FUTBOL_RELOAD (pcnimdock, LGPL v3): datos factuales de
# ingeniería inversa reimplementados en Python. El sprite es SOLO la camiseta (NO hay pantalón/medias).
_SOMBRA = 7            # contorno negro (0x60) — no se toca
COLOR_SOMBRA = 0x60
_POS = {
    "cuello":  [16],
    "ribete":  [15],
    "manga_izq": [4, 27, 28, 31],          # manga izquierda (pcnimdock ZONA_MANGA_I)
    "manga_der": [25, 29, 30, 32],          # manga derecha (pcnimdock ZONA_MANGA_D)
    "mangas":  [4, 25, 27, 28, 29, 30, 31, 32],
    "hombros": [72, 77],
    "torso":   [97, 102, 107, 109, 112, 117, 120, 126, 131, 134,
                137, 141, 145, 150, 155, 158, 160, 165],
    "faldon":  [1, 34, 43, 47, 50, 52],
}
# CUERPO = todo lo que lleva el color base (torso + hombros + faldón + mangas)
_CUERPO = _POS["torso"] + _POS["hombros"] + _POS["faldon"] + _POS["mangas"]

ZONE_LABELS = {"camiseta": "Camiseta", "franjas": "2º color", "mangas": "Ambas mangas",
               "manga_izq": "Manga izq.", "manga_der": "Manga der.",
               "hombros": "Hombros", "faldon": "Faldón (bajo)",
               "cuello": "Cuello", "ribete": "Ribete"}
EDITABLE_ZONES = ("camiseta", "franjas", "mangas", "manga_izq", "manga_der",
                  "hombros", "faldon", "cuello", "ribete")

PATTERN_NAMES = ("liso", "rayas", "franjas", "banda", "banda_inv")
PATTERNS = {p: [] for p in PATTERN_NAMES}   # compat: el patrón se genera a nivel de textura

# 13 colores validados = rampas de índices de la paleta del simulador (de oscuro a claro).
COLORS = [
    ("Rojo",        [0x80, 0x81, 0x82, 0x83, 0x84]),
    ("Azul",        [0x8A, 0x8B, 0x8C, 0x8D, 0x8E]),
    ("Blanco",      [0x78, 0x79, 0x7A, 0x7B, 0x7C, 0x7D, 0x7E, 0x7F]),
    ("Negro",       [0x60, 0x61, 0x62, 0x63, 0x64, 0x65, 0x66, 0x67]),
    ("Gris",        [0x68, 0x69, 0x6A, 0x6B, 0x6C, 0x6D, 0x6E, 0x6F]),
    ("Amarillo",    [0x85, 0x86, 0x87, 0x88, 0x89]),
    ("Verde",       [0x8F, 0x90, 0x91, 0x92, 0x93]),
    ("Celeste",     [0x94, 0x95, 0x96, 0x97, 0x98]),
    ("Azul marino", [0x99, 0x9A, 0x9B, 0x9C, 0x9D]),
    ("Granate",     [0x9E, 0x9F, 0xA0, 0xA1, 0xA2]),
    ("Naranja",     [0xAD, 0xAE, 0xAF, 0xB0, 0xB1]),
    ("Turquesa",    [0xB2, 0xB3, 0xB4, 0xB5, 0xB6]),
    ("Morado",      [0xC1, 0xC2, 0xC3, 0xC4, 0xC5]),
]

_CIERRE = bytes([0x00, 0xA6, 0x68, 0x6C, 0x70, 0x72, 0x77, 0x7B, 0x29, 0xD1, 0xD1, 0x50, 0x00, 0xFF])
_CABECERA = bytes([0x90]) + b"QRSTUV>"


def _centros_visibles() -> dict:
    """{posición de textura: (x, y) medio en el icono} de las posiciones que el juego DIBUJA.

    De las 168 posiciones de la textura, el icono 20×20 solo usa 37, pero cada una cae siempre
    en el mismo sitio y ocupa una zona pequeña y compacta: el torso es en la práctica una
    rejilla de 6 columnas × 4 filas. Eso es lo que permite dibujar formas GEOMÉTRICAS —una banda
    diagonal, por ejemplo— en vez de limitarse a rayas y franjas."""
    from collections import defaultdict
    celdas = defaultdict(list)
    for i, pos in enumerate(_SPRITE_MAP):
        if pos >= 0 and pos != _SOMBRA:
            celdas[pos].append((i % SPRITE_W, i // SPRITE_W))
    out = {}
    for pos, v in celdas.items():
        cx = sum(x for x, _ in v) / len(v)
        cy = sum(y for _, y in v) / len(v)
        # el contorno ocupa media camiseta: no es una "zona" con sitio propio
        disp = max(max(abs(x - cx) for x, _ in v), max(abs(y - cy) for _, y in v))
        if disp <= 4:
            out[pos] = (cx, cy)
    return out


def _textura_banda(rampa_a: list, rampa_b: list, ancho: float = 0.30,
                   invertida: bool = False) -> bytes:
    """Banda DIAGONAL (la del Rayo Vallecano) sobre el color base.

    Se decide color por la posición REAL de cada trozo en el icono, no por su índice en la
    textura: la banda es la franja donde `x` e `y` normalizados están cerca de la diagonal."""
    tex = bytearray(TEX_W * TEX_H)
    base = rampa_a[len(rampa_a) // 2] if rampa_a else 0
    for i in range(TEX_W * TEX_H):
        tex[i] = base
    centros = _centros_visibles()
    if centros:
        xs = [c[0] for c in centros.values()]
        ys = [c[1] for c in centros.values()]
        x0, x1 = min(xs), max(xs)
        y0, y1 = min(ys), max(ys)
        for pos, (cx, cy) in centros.items():
            nx = (cx - x0) / (x1 - x0) if x1 > x0 else 0.5
            ny = (cy - y0) / (y1 - y0) if y1 > y0 else 0.5
            # de hombro a cadera contraria. Las dos direcciones: `invertida` es la del Rayo
            # (del hombro derecho a la cadera izquierda), la otra su espejo.
            d = (nx + ny - 1.0) if invertida else (nx - ny)
            if abs(d) <= ancho / 2 and pos < len(tex):
                # el tono se aclara hacia abajo, como en el resto de patrones
                k = min(len(rampa_b) - 1, int(ny * len(rampa_b)))
                tex[pos] = rampa_b[max(0, k)]
    tex[_SOMBRA] = COLOR_SOMBRA
    return bytes(tex)


def generar_textura(pattern: str, rampa_a: list, rampa_b: list | None = None, ancho: int = 4) -> bytes:
    """168 bytes (24×7) a partir de un patrón + 1-2 rampas. 'rayas' = por columnas, 'franjas' = por
    filas; dentro de cada franja el tono va de claro a oscuro (como los kits reales). Pos 7 = sombra."""
    if not rampa_a:
        return bytes(TEX_W * TEX_H)
    rb = rampa_b if rampa_b else rampa_a
    if pattern in ("banda", "banda_inv"):
        return _textura_banda(rampa_a, rb, invertida=(pattern == "banda_inv"))
    ancho = max(1, ancho)
    tex = bytearray(TEX_W * TEX_H)
    for y in range(TEX_H):
        for x in range(TEX_W):
            if pattern == "rayas":
                usar_b, pos = (x // ancho) % 2 == 1, x % ancho
            elif pattern == "franjas":
                usar_b, pos = (y // ancho) % 2 == 1, y % ancho
            else:
                usar_b, pos = False, x % ancho
            rampa = rb if usar_b else rampa_a
            tonos = min(ancho, len(rampa))
            k = 0 if tonos <= 1 else (tonos - 1) - (pos * tonos) // ancho
            tex[y * TEX_W + x] = rampa[max(0, min(k, len(rampa) - 1))]
    tex[_SOMBRA] = COLOR_SOMBRA
    return bytes(tex)


def bloque_desde_textura(tex168: bytes) -> bytes:
    """Envuelve una textura de 168 B en su bloque de 190 (cabecera + textura + cierre fijo)."""
    t = bytes(tex168[:TEX_W * TEX_H]).ljust(TEX_W * TEX_H, b"\0")
    return _CABECERA + t + _CIERRE


def _ramp_of(idx: int, palette) -> list:
    """Rampa (índices oscuro→claro) a la que pertenece un color; si no cae en ninguna, [idx]."""
    if palette is not None:
        r = _index_to_ramp(palette).get(idx)
        if r:
            return r
    for _n, r in COLORS:
        if idx in r:
            return r
    return [idx]


def palette_options(palette) -> list[dict]:
    """Paleta de colores SELECCIONABLES para los pickers: TODOS los colores VISUALMENTE
    distintos del simulador → [{index, rgb, name}]. Se recorren los 256 índices y se
    descartan los casi-idénticos (mismo color en distinto índice) para dar una gama rica
    (~40-60 colores) sin degradados redundantes."""
    seen: list[tuple] = []
    out: list[dict] = []
    for i in range(256):
        rgb = _rgb(palette, i)
        # descartar casi-duplicados (suma de |dif| pequeña) → un color por tono real
        if any(abs(rgb[0] - s[0]) + abs(rgb[1] - s[1]) + abs(rgb[2] - s[2]) <= 70 for s in seen):
            continue
        seen.append(rgb)
        out.append({"index": i, "rgb": list(rgb), "name": _bucket(palette, i)})
    return out


_ZONEMAP = {"camiseta": _CUERPO, "mangas": _POS["mangas"],
            "manga_izq": _POS["manga_izq"], "manga_der": _POS["manga_der"],
            "hombros": _POS["hombros"], "faldon": _POS["faldon"],
            "cuello": _POS["cuello"], "ribete": _POS["ribete"]}


def zone_colors(data: bytes, block_idx: int, palette) -> dict:
    """Color ACTUAL (índice dominante) de cada zona anatómica → {zona: {index, rgb}}.
    'camiseta' = cuerpo (torso+hombros+faldón+mangas); 'franjas' se deriva (2º color del cuerpo)."""
    cb = color_bytes(data, block_idx)
    out = {}
    for zone, positions in _ZONEMAP.items():
        vals = [cb[o] for o in positions if o < len(cb)]
        if not vals:
            continue
        top = Counter(vals).most_common(2)
        idx = top[0][0]
        out[zone] = {"index": int(idx), "rgb": list(_rgb(palette, idx))}
        if zone == "camiseta" and len(top) > 1:                # 2º color del cuerpo = franjas
            sec = top[1][0]
            out["franjas"] = {"index": int(sec), "rgb": list(_rgb(palette, sec))}
    return out


def apply_zones(data: bytes, block_idx: int, colors: dict, pattern: str = "liso",
                palette=None) -> bytes:
    """Genera la equipación (modelo del editor de FUTBOL_RELOAD): color base + patrón (rayas/franjas
    con el 2º color) sobre la textura 24×7, y superpone los acentos (mangas/cuello/ribete).
    `colors` = {camiseta|franjas|mangas|cuello|ribete: índice de paleta}. 'liso' = un solo color."""
    out = bytearray(data)
    base = block_idx * BLOCK + COLOR_OFF
    ca = colors.get("camiseta")
    if ca is not None:                                          # cuerpo = base (+ patrón con franjas)
        ra = _ramp_of(int(ca), palette)
        cb = colors.get("franjas")
        rb = _ramp_of(int(cb), palette) if cb is not None else ra
        tex = generar_textura(pattern, ra, rb)
        for o in range(TEX_W * TEX_H):
            if base + o < len(out):
                out[base + o] = tex[o]
    # acentos = color plano. 'mangas' (ambas) primero; manga_izq/der DESPUÉS para poder
    # sobreescribir una sola manga. hombros/faldón/cuello/ribete al final.
    for zone in ("mangas", "manga_izq", "manga_der", "hombros", "faldon", "cuello", "ribete"):
        idx = colors.get(zone)
        if idx is None:
            continue
        for o in _POS[zone]:
            if o != _SOMBRA and base + o < len(out):
                out[base + o] = int(idx) & 0xFF
    if base + _SOMBRA < len(out):                              # contorno negro del juego
        out[base + _SOMBRA] = COLOR_SOMBRA
    return bytes(out)


def texture_of(data: bytes, block_idx: int) -> list:
    """Los 168 índices de paleta de la textura (posiciones 0-167 del sprite) de un bloque."""
    a = block_idx * BLOCK + COLOR_OFF
    return list(data[a:a + TEX_W * TEX_H])


def write_texture(data: bytes, block_idx: int, tex: list) -> bytes:
    """Reescribe los 168 índices de textura de un bloque (para el editor por PÍXEL).
    Protege la sombra (posición 7 = negro del contorno del juego)."""
    out = bytearray(data)
    base = block_idx * BLOCK + COLOR_OFF
    n = min(len(tex), TEX_W * TEX_H)
    for i in range(n):
        if base + i < len(out):
            out[base + i] = int(tex[i]) & 0xFF
    if base + _SOMBRA < len(out):
        out[base + _SOMBRA] = COLOR_SOMBRA
    return bytes(out)


def sprite_map() -> list:
    """Mapa 20×20 (400) píxel del sprite → posición de textura (0-167) o -1 (fondo).
    Calibrado con el `mapaSprite` de pcnimdock/FUTBOL_RELOAD (ver NOTICE.md); base del editor por píxel."""
    return list(_SPRITE_MAP)


def copy_block(data: bytes, src_idx: int, dst_idx: int) -> bytes:
    """Copia una equipación entera sobre otra (swap de camiseta entre equipos)."""
    out = bytearray(data)
    s = src_idx * BLOCK
    d = dst_idx * BLOCK
    out[d:d + BLOCK] = data[s:s + BLOCK]
    return bytes(out)


TEX_W = 24                # la TEXTURA de la camiseta es 24×7 = 168 índices (offset 8-175 del bloque)
TEX_H = 7
KIT_BODY = 168

SPRITE_W = 20             # el ICONO que pinta el juego es 20×20 y muestra 37 de las 168 posiciones
SPRITE_H = 20

# MAPA DE SPRITE CALIBRADO CONTRA EL JUEGO REAL (píxel del icono 20×20 → posición 0-167 de la
# textura; -1 = fondo). Portado de FUTBOL_RELOAD (pcnimdock, LGPL v3): se generaron EQUIPOS.DAT de
# prueba con valores conocidos, se capturó el icono en el juego y se cruzó contra la paleta → resuelve
# los 281 píxeles opacos sin ambigüedad. Reemplaza nuestra silueta estimada de 8 px (que salía mal).
_SPRITE_MAP = [
    -1, -1, -1, 28, 28, 16, -1, -1, -1, -1, -1, -1, 16, 30, 30, -1, -1, -1, -1, -1,
    -1, -1, 28,  4,  4, 16,  7, -1, -1, -1, -1, -1, 16, 25, 25, 30,  7, -1, -1, -1,
    -1, 28,  4,  4,  4, 16, 16,  7, -1, -1, -1, 16, 16, 25, 25, 25, 30,  7, -1, -1,
    28,  4,  4,  4,  4, 72, 16, 16,  7,  7, 16, 16, 77, 25, 25, 25, 25, 30,  7, -1,
    28,  4,  4,  4,  4, 72, 72, 16, 16, 16, 16, 77, 77, 25, 25, 25, 25, 30,  7,  7,
    31,  4,  4,109,109, 97, 97,112,112,117,117,102,102,107,107, 25, 25, 32,  7,  7,
    31, 27,  4,109,109, 97, 97,112,112,117,117,102,102,107,107, 25, 29, 32,  7,  7,
    -1, -1, 27,109,109, 97, 97,112,112,117,117,102,102,107,107, 29,  7,  7,  7,  7,
    -1, -1,  7,134,134,120,120,137,137,141,141,126,126,131,131,  7,  7,  7,  7,  7,
    -1, -1, -1,134,134,120,120,137,137,141,141,126,126,131,131,  7,  7,  7, -1, -1,
    -1, -1, -1,158,158,145,145,160,160,165,165,150,150,155,155,  7,  7, -1, -1, -1,
    -1, -1, -1,158,158,145,145,160,160,165,165,150,150,155,155,  7,  7, -1, -1, -1,
    -1, -1, -1,158,158,145,145,160,160,165,165,150,150,155,155,  7,  7, -1, -1, -1,
    -1, -1, -1, -1, 43,  1,  1, 47, 47, 50, 50, 34, 34, 52,  7,  7,  7, -1, -1, -1,
    -1, -1, -1, -1, 43,  1,  1, 47, 47, 50, 50, 34, 34, 52,  7,  7,  7, -1, -1, -1,
    -1, -1, -1, -1, -1,  1,  1, 47, 47, 50, 50, 34, 34,  7,  7,  7,  7, -1, -1, -1,
    -1, -1, -1, -1, -1, 15, 15, 15, 15, 15, 15, 15, 15,  7,  7,  7,  7, -1, -1, -1,
    -1, -1, -1, -1, -1, 15, 15, 15, 15, 15, 15, 15, 15,  7,  7,  7, -1, -1, -1, -1,
    -1, -1, -1, -1, -1, -1,  7,  7,  7,  7,  7,  7,  7,  7,  7,  7, -1, -1, -1, -1,
    -1, -1, -1, -1, -1, -1, -1,  7,  7,  7,  7,  7,  7,  7,  7, -1, -1, -1, -1, -1,
]


def _rgb(palette, i):
    c = palette[i]
    return (c >> 16 & 255, c >> 8 & 255, c & 255) if isinstance(c, int) else tuple(c[:3])


def strip_png(data: bytes, block_idx: int, palette: list, scale: int = 9,
              preview_remap: dict | None = None) -> bytes:
    """Render REAL del icono de camiseta (20×20), pintando cada píxel con la posición de textura que
    le corresponde según el mapa calibrado del juego (`_SPRITE_MAP`). `preview_remap` (familias o
    índices) se aplica SOLO al render para previsualizar sin guardar. La posición 7 es la sombra
    (contorno negro 0x60)."""
    from io import BytesIO

    from PIL import Image
    if preview_remap:
        data = remap(data, block_idx, preview_remap, palette=palette)
    a = block_idx * BLOCK + HEADER
    body = data[a:a + KIT_BODY]                       # 168 índices (textura 24×7)
    im = Image.new("RGBA", (SPRITE_W, SPRITE_H), (0, 0, 0, 0))
    px = im.load()
    for sy in range(SPRITE_H):
        for sx in range(SPRITE_W):
            pos = _SPRITE_MAP[sy * SPRITE_W + sx]
            if pos < 0 or pos >= len(body):
                continue
            r, g, b = _rgb(palette, body[pos])
            px[sx, sy] = (r, g, b, 255)
    im = im.resize((SPRITE_W * scale, SPRITE_H * scale), Image.NEAREST)
    out = BytesIO()
    im.save(out, format="PNG")
    return out.getvalue()
