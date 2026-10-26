"""PCF 2000 / 2001 — contenedor FDI y registros (equipo/jugador/entrenador/ESTADIO).

Misma familia FDI que PCF 7 (ver `pcf7.py` y la wiki de formatos): mismo
contenedor (magic `DMFIv1.0`, u32 count @16, índice de 13 B), mismo cifrado XOR 0x61 y
longitudes u16 LE. Diferencias (registro `version = 800` en vez de 700):

- **4º fichero de ESTADIOS** (`est*022.fdi`): entidad propia. El equipo referencia un
  `estadio_id` u16 en vez de llevar los campos de estadio embebidos.
- **Jugador**: +3 bytes (`pelo_tipo`, `bello_facial`, `nacionalizado`) tras `demarcacion`.
- **Equipo**: `estadio_id` u16 en vez de la cadena de estadio; sin sentados/de_pie/ancho/
  largo/año-estadio/latitud (ahora en el estadio). Sin `unk1` tras la fundación; historial 82B.
- **Entrenador**: idéntico a PCF7 (se reutiliza su parser).

Historial (82 B) y táctica dibujada (1760 B) se guardan como blobs opacos (round-trip
byte-perfecto); accesores tipados reutilizados de PCF7.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field

from . import pcf7 as _P7
from .pcf7 import (  # helpers e infraestructura compartidos, idénticos
    HEADER_LEN, INDEX_ENTRY, MAGIC, MEDIA_NAMES, PLAYER_BBDD, TACTIC_FIELDS,
    TACTIC_PLAYERS, TACTIC_XMAX, TACTIC_YMAX, TACTIC_ZONES, Coach,
    # la pizarra: 4 carriles × (4,6,6,4) pasos × 2 estados. Medida también en las 1.451
    # tácticas de PCF2001, donde el orden de carriles sale en 1.451 de 1.451
    ZONAS_POR_CARRIL, carril_y_paso, zona_de,
    # las zonas de cada disposición del campo (def = sin balón, atk = con balón) y el
    # tamaño del terreno por edición (PCF7/2000 420×252 · PCF2001 480×288)
    ZONAS_CON, ZONAS_SIN, field_dims, zonas_de,
    # el reparto de códigos de equipo por bloques de país, que es igual en las tres
    BLOQUE_CODIGOS, CODIGO_MAX, bloques_de_pais, codigo_para_pais,
    _R, _W, _parse_coach, _ser_coach, _sumalargos, apply_tactic_preset,
    COMPETICIONES, fdi_tactic_presets, set_historial_field, set_palmares,
    set_palmares_field,
    set_tactic_field, set_tactic_position, shift_tactic_player,
    PITCH_2001, PITCH_H, PITCH_W, TERCERA_GRUPOS,
    tactic_base, tactic_positions, tactic_shape, team_historial, team_palmares,
    team_tactic,
)

VERSION_800 = 800         # versión de registro de PCF2000/2001 (PCF7 = 700)


# ------------------------------------------------------------------ modelos
@dataclass
class Player:
    code: int
    tipo: int                       # 0 liga jugable (ficha completa) / 1 no jugable
    id_foto: int
    dorsal: int
    apodo: str
    nombre: str
    slot: int
    estado: int
    roles: bytes                    # 6 bytes (posiciones)
    nacionalidad: int
    piel: int
    pelo: int                       # color de pelo
    demarcacion: int
    pelo_tipo: int                  # NUEVO vs PCF7 (hairType)
    bello: int                      # NUEVO vs PCF7 (facialHair)
    nacionalizado: int              # NUEVO vs PCF7 (isNationalized)
    dia: int
    mes: int
    anyo: int
    altura: int
    peso: int
    version: int = VERSION_800
    pais_natal: int = 0
    ciudad: str = ""
    procedencia: str = ""
    internacional: str = ""
    bbdd: list = field(default_factory=list)   # 7 textos
    medias: bytes = b"\x00" * 16
    raw: bytes = b""                # ver Team.raw (registro no reconocido)
    opaque: bool = False

    def media(self, name: str) -> int:
        return self.medias[MEDIA_NAMES.index(name)]

    def set_media(self, name: str, value: int):
        m = bytearray(self.medias)
        m[MEDIA_NAMES.index(name)] = value & 0xFF
        self.medias = bytes(m)


@dataclass
class Team:
    code: int
    firma: bytes                    # 36 B "Copyright (c)2000 Dinamic Multimedia"
    tipo: int                       # 0 liga jugable / 1 foráneo
    pad: int
    nombre_corto: str
    estadio_id: int                 # u16 → puntero al FDI de estadios (NUEVO vs PCF7)
    pais: int
    nombre: str
    fundacion: int
    version: int = VERSION_800
    # solo si tipo == 0
    socios: int = 0
    presidente: str = ""
    presupuesto: int = 0
    presupuesto_gen: int = 0
    patrocinador: str = ""
    proveedor: str = ""
    filial: int = 0xFFFF
    palmares: bytes = b""           # historial (blob; 82B en 2000 / 83B en 2001)
    competiciones: list = field(default_factory=list)   # [(id, part, tit)]
    tactica: bytes = b"\x00" * 1760
    tactica_equipo: bytes = b"\x00" * 7
    entrenadores: list = field(default_factory=list)    # punteros u32
    jugadores: list = field(default_factory=list)       # [(en_plantilla, puntero_u32)]
    unk1: int = 0                   # u8 tras fundación — SOLO en 2001 (ausente en 2000)
    # registro que NO cuadra con el layout conocido (mods de terceros): se guarda tal
    # cual y se re-emite byte a byte, para no perder el mod entero por un equipo raro.
    raw: bytes = b""
    opaque: bool = False


@dataclass
class Stadium:
    code: int                       # puntero de estadio (id de índice)
    nombre: str
    ancho: int                      # width (m del terreno)
    largo: int                      # length
    unk: int                        # u8 desconocido (¿latitud?)
    pais: int
    anyo: int                       # constructionYear u16
    sentados: int                   # sittingCapacity u32
    de_pie: int                     # standingCapacity u32


@dataclass
class FdiFile:
    kind: str                       # "EQ" | "JUG" | "ENT" | "EST"
    records: list = field(default_factory=list)
    variant: str = "2000"           # "2000" o "2001" (afecta SOLO al layout de equipo)


# ------------------------------------------------------------------ jugador
def _parse_player(d: bytes, ini: int, largo: int, code: int) -> Player:
    r = _R(d, ini)
    r.u16()                                     # sumaLargos (derivado)
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
    pelo_tipo = r.u8(); bello = r.u8(); nacionalizado = r.u8()   # +3 bytes vs PCF7
    dia = r.u8(); mes = r.u8(); anyo = r.u16()
    altura = r.u8(); peso = r.u8()
    p = Player(code=code, tipo=tipo, id_foto=id_foto, dorsal=dorsal, apodo=apodo,
               nombre=nombre, slot=slot, estado=estado, roles=roles, nacionalidad=nac,
               piel=piel, pelo=pelo, demarcacion=dem, pelo_tipo=pelo_tipo, bello=bello,
               nacionalizado=nacionalizado, dia=dia, mes=mes, anyo=anyo,
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
    w.u8(p.pelo_tipo); w.u8(p.bello); w.u8(p.nacionalizado)
    w.u8(p.dia); w.u8(p.mes); w.u16(p.anyo)
    w.u8(p.altura); w.u8(p.peso)
    if p.tipo == 0:
        w.u8(p.pais_natal)
        w.st(p.ciudad); w.st(p.procedencia); w.st(p.internacional)
        for t in p.bbdd:
            w.st(t)
    w.raw(p.medias)
    return bytes(w.b)


# ------------------------------------------------------------------ equipo
# Layout de equipo por variante: (bloque historial, njug es u16, hay unk1 tras fundación).
# 2000 y 2001 comparten version=800 pero el equipo difiere (validado por round-trip):
_TEAM_LAYOUT = {"2000": (82, False, False), "2001": (83, True, True)}

# TOPE DE PLANTILLA por formato (medido 2026-09-29 sobre las bases reales).
# El número de jugadores del equipo lo escribe el FORMATO: u8 en PCF7 y PCF2000 → 255;
# u16 en PCF2001 (versión 800) → 65535. El motor NO impone tope al serializar (conserva
# todos los punteros y escribe `len()`), y las bases lo demuestran: PCF2001 trae un equipo
# de **463** jugadores («Juveniles Españoles»), PCF2000 de 55, PCF7 de 49-50. El 35 que se
# devolvía en la ficha era NUESTRO (y hacía que la web pintara «463/35» y deshabilitara
# «Añadir jugador» antes de tiempo). Este es el tope REAL, para la UI.
MAX_PLAYERS = {"2000": 255, "2001": 65535}


def max_players(variant: str = "2000") -> int:
    """Tope de plantilla de la variante, según el ancho del contador en el fichero."""
    return MAX_PLAYERS.get(variant, 255)


def _parse_team(d: bytes, ini: int, largo: int, code: int, variant: str = "2000") -> Team:
    stats_size, njug_u16, has_unk1 = _TEAM_LAYOUT[variant]
    r = _R(d, ini)
    firma = r.raw(36)
    r.u16()                                     # sumaLargos
    version = r.u16()
    pad = r.u8()
    tipo = r.u8()
    corto = r.st()
    estadio_id = r.u16()
    pais = r.u8()
    nombre = r.st()
    fundacion = r.u16()
    unk1 = r.u8() if has_unk1 else 0
    t = Team(code=code, firma=firma, tipo=tipo, pad=pad, nombre_corto=corto,
             estadio_id=estadio_id, pais=pais, nombre=nombre, fundacion=fundacion,
             version=version, unk1=unk1)
    if tipo == 0:
        t.socios = r.u32()
        t.presidente = r.st()
        t.presupuesto = r.u32(); t.presupuesto_gen = r.u32()
        t.patrocinador = r.st(); t.proveedor = r.st()
        t.filial = r.u16()
        t.palmares = r.raw(stats_size)
        n_comp = r.u8()
        t.competiciones = [(r.u8(), r.u8(), r.u8()) for _ in range(n_comp)]
    t.tactica = r.raw(1760)
    t.tactica_equipo = r.raw(7)
    n_ent = r.u8()
    t.entrenadores = [r.u32() for _ in range(n_ent)]
    n_jug = r.u16() if njug_u16 else r.u8()
    t.jugadores = [(r.u8(), r.u32()) for _ in range(n_jug)]
    if r.p != ini + largo:
        raise ValueError(f"equipo {code}: {r.p - ini} != {largo}")
    return t


def _ser_team(t: Team, variant: str = "2000") -> bytes:
    if t.opaque and t.raw:
        return t.raw          # registro no reconocido: se re-emite tal cual
    _stats_size, njug_u16, has_unk1 = _TEAM_LAYOUT[variant]
    w = _W()
    w.raw(t.firma)
    if t.tipo == 0:
        w.u16(_sumalargos(t.nombre_corto, t.nombre, t.presidente, t.patrocinador, t.proveedor))
    else:
        w.u16(_sumalargos(t.nombre_corto, t.nombre))
    w.u16(t.version)
    w.u8(t.pad); w.u8(t.tipo)
    w.st(t.nombre_corto)
    w.u16(t.estadio_id)
    w.u8(t.pais)
    w.st(t.nombre)
    w.u16(t.fundacion)
    if has_unk1:
        w.u8(t.unk1)
    if t.tipo == 0:
        w.u32(t.socios)
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
    if njug_u16:
        w.u16(len(t.jugadores))
    else:
        w.u8(len(t.jugadores))
    for en_plantilla, ptr in t.jugadores:
        w.u8(en_plantilla); w.u32(ptr)
    return bytes(w.b)


# ------------------------------------------------------------------ estadio (NUEVO)
def _parse_stadium(d: bytes, ini: int, largo: int, code: int) -> Stadium:
    r = _R(d, ini)
    nombre = r.st()
    ancho = r.u8(); largo_c = r.u8(); unk = r.u8(); pais = r.u8()
    anyo = r.u16()
    sentados = r.u32(); de_pie = r.u32()
    s = Stadium(code=code, nombre=nombre, ancho=ancho, largo=largo_c, unk=unk,
                pais=pais, anyo=anyo, sentados=sentados, de_pie=de_pie)
    if r.p != ini + largo:
        raise ValueError(f"estadio {code}: {r.p - ini} != {largo}")
    return s


def _ser_stadium(s: Stadium) -> bytes:
    w = _W()
    w.st(s.nombre)
    w.u8(s.ancho); w.u8(s.largo); w.u8(s.unk); w.u8(s.pais)
    w.u16(s.anyo)
    w.u32(s.sentados); w.u32(s.de_pie)
    return bytes(w.b)


# ------------------------------------------------------------------ contenedor FDI
_KIND_PARSE = {"EQ": _parse_team, "JUG": _parse_player,
               "ENT": _parse_coach, "EST": _parse_stadium}
_KIND_SER = {"EQ": _ser_team, "JUG": _ser_player,
             "ENT": _ser_coach, "EST": _ser_stadium}


def _detect_kind(name: str) -> str:
    u = name.upper()
    for pref in ("EQ", "JUG", "ENT", "EST"):
        if u.startswith(pref):
            return pref
    raise ValueError(f"no sé qué FDI es: {name}")


def _skip_2000(r) -> None:
    r.u16(); r.u8()                             # estadio_id, país (aquí NO hay latitud)


def _opaque_team(d: bytes, ini: int, largo: int, code: int) -> Team:
    """Equipo que no cuadra con el layout: cabecera a la brava + bytes crudos."""
    blob = d[ini:ini + largo]
    corto, nombre = _P7._hdr_names(d, ini, _skip_2000)
    return Team(code=code, firma=blob[:36], tipo=1, pad=0, nombre_corto=corto,
                estadio_id=0, pais=0, nombre=nombre or corto or f"Equipo {code}",
                fundacion=0, raw=blob, opaque=True)


def _opaque_player(d: bytes, ini: int, largo: int, code: int) -> Player:
    return _P7.opaque_player(d, ini, largo, code, cls=Player)


_KIND_OPAQUE = {"EQ": _opaque_team, "JUG": _opaque_player,
                "ENT": _P7.opaque_coach, "EST": None}


def parse(data: bytes, kind: str, variant: str = "2000") -> FdiFile:
    """Parsea un FDI de PCF2000/2001. `kind` ∈ {'EQ','JUG','ENT','EST'} o nombre de fichero.
    `variant` ('2000'|'2001') solo afecta al layout de EQUIPO (jug/ent/est son idénticos)."""
    if kind not in _KIND_PARSE:
        kind = _detect_kind(kind)
    if data[:8] != MAGIC:
        raise ValueError("no es un FDI (falta DMFIv1.0)")
    n = struct.unpack_from("<I", data, 16)[0]
    parse_fn = _KIND_PARSE[kind]
    records = []
    for i in range(n):
        code, ini, largo = struct.unpack_from("<IxII", data, HEADER_LEN + i * INDEX_ENTRY)
        try:
            if kind == "EQ":
                records.append(_parse_team(data, ini, largo, code, variant))
            else:
                records.append(parse_fn(data, ini, largo, code))
        except Exception:  # noqa: BLE001 — registro raro: se conserva en crudo
            op_fn = _KIND_OPAQUE.get(kind)
            if op_fn is None:
                raise
            records.append(op_fn(data, ini, largo, code))
    return FdiFile(kind=kind, records=records, variant=variant)


def serialize(f: FdiFile) -> bytes:
    """Reconstruye el FDI (reindexa contiguo en orden de la lista)."""
    ser_fn = _KIND_SER[f.kind]
    if f.kind == "EQ":
        blocks = [_ser_team(rec, f.variant) for rec in f.records]
    else:
        blocks = [ser_fn(rec) for rec in f.records]
    n = len(blocks)
    out = bytearray(MAGIC + b"\x00" * 8 + struct.pack("<I", n))
    inicio = HEADER_LEN + n * INDEX_ENTRY
    index = bytearray()
    for rec, blk in zip(f.records, blocks):
        index += struct.pack("<IxII", rec.code, inicio, len(blk))
        inicio += len(blk)
    out += index
    for blk in blocks:
        out += blk
    return bytes(out)
