"""PCF 3.0 (DOS, temporada 94-95) — lector/escritor de las bases `.DBC`.

Ingeniería inversa 2026-07-16. Los `.DBC` son la familia clásica de
Dinamic:
- Cabecera ASCII `Copyright (c)1994 DINAMIC MULTIMEDIA` (+ `\n` y a veces `Todos los derechos…`).
- **Texto cifrado con el MISMO esquema que los `.GRC` de PCF4**:
  `claro[i] = cif[i] XOR ((0xC0 + longitud + i) & 0xFF)`  (NO es el XOR 0x61 de v5/6).
- Cada campo de texto = `[longitud][bytes cifrados]`. La longitud es **u8** en la base grande de
  jugadores (`LIG*.DBC`) y **u16 LE** en las tablas pequeñas (`LIGA.DBC`, `ARBITROS.DBC`…). Entre
  campos de texto hay campos binarios (dorsal, medias, fechas…) que se conservan VERBATIM.

Filosofía Houdini: edición **in-place byte-perfect**. No reserializamos el fichero; guardamos el
`bytearray` original y solo sobreescribimos el rango de bytes de un campo editado (misma longitud,
rellenando con espacios; se rechaza si excede). Así el round-trip es perfecto por construcción.
"""
from __future__ import annotations

import struct
import unicodedata
from dataclasses import dataclass, field

SIGNATURE = b"Copyright (c)1994 DINAMIC MULTIMEDIA"


def is_pcf3_dbc(data: bytes) -> bool:
    return data[:len(SIGNATURE)] == SIGNATURE


# --- cifrado (idéntico a codec/pcf4_grc: XOR 0xC0+len+i) --------------------------------------
# El texto va cifrado sobre BYTES (round-trip byte-perfect independiente del codepage), pero el
# codepage para mostrar/editar VARÍA por fichero: las plantillas grandes (LIG9495N) son **cp850**
# (DOS: ñ=0xA4, á=0xA0…) y las tablas de competición (EUROPA/UEFA/LIGA/COPA) son **latin-1/1252**
# (ñ=0xF1, á=0xE1…). Se autodetecta por fichero (`_detect_cp`).
_CP = "cp850"
_CANDIDATE_CPS = ("cp850", "latin-1")


def decode_text(buf: bytes, cp: str = _CP) -> str:
    n = len(buf)
    return bytes(b ^ ((0xC0 + n + i) & 0xFF) for i, b in enumerate(buf)).decode(cp, "replace")


def encode_text(s: str, cp: str = _CP) -> bytes:
    raw = s.encode(cp, "replace")
    n = len(raw)
    return bytes(b ^ ((0xC0 + n + i) & 0xFF) for i, b in enumerate(raw))


_ASCII_OK = set(" .-'\\/()+,&:0123456789ºª·")

# Longitud máxima de un texto (2026-08-30). ESTABA EN 30 y se perdía todo lo que pasara de ahí:
#   · el nombre oficial del RAYO ('Rayo Vallecano de Madrid, S.A.D.', 32) y con él TODA su ficha
#     —presidente, aforo, socios, presupuesto, año—, que parecía no existir;
#   · y unos 90 JUGADORES de las dos divisiones cuyo nombre completo pasa de 30 caracteres.
# Los textos reales llegan a ~60 (las biografías van troceadas en cachos de ese tamaño). Por
# encima de 88 el escaneo empieza a colar falsos positivos y descuadra la agrupación de equipos,
# así que 64 deja margen por los dos lados: recupera todo y no se acerca al borde.
_MAX_TEXTO = 64

# Rótulos de apartado de COMMENT.DBC. Sirven de ANCLA: ese fichero son párrafos ya partidos en
# líneas de ~75 caracteres, o sea POR ENCIMA de _MAX_TEXTO, así que el escaneo solo veía 2 de cada
# 9. Entre rótulo y rótulo el fichero sí es una secuencia limpia `[u8 longitud][texto]` y se puede
# caminar; entre bloques hay separadores binarios de tamaño variable, y por eso se camina ACOTADO.
_ROTULOS = ("Novedades en el equipo", "Sistema de juego", "Objetivo en la Liga")

# Ficheros que se editan SIN mover un byte (se rellena con espacios): no se ha comprobado que el
# juego no los indexe por offset, y ahí no se arriesga.
_LONGITUD_FIJA = {"COMMENT.DBC"}


def inicial_sin_acento(s: str) -> str:
    """Quita el acento SOLO de la primera letra, dejando el resto igual.

    En la base original hay **716 campos con acentos dentro y NI UNO que empiece por acento**: es
    la convención de Dinamic, y el escaneo se apoya en ella para localizar los campos. Si se
    escribe «Álvaro Cortés», ese campo deja de reconocerse: el jugador DESAPARECE del equipo y se
    descuadra el anclaje de las medias (le pasaba a la importación desde la caché). Ensanchar el
    escáner para admitirlo es peor —con `Í` aparecía un 'ÍJzwkpz' que se comía al 'Santiago
    Bernabéu' de al lado, y con `È` se partía en dos el Mallorca—, así que se escribe como lo
    escribiría el juego: «Alvaro Cortés».
    """
    if not s or s[0].isascii():
        return s
    base = unicodedata.normalize("NFD", s[0])[0]
    return (base + s[1:]) if base.isascii() else s


def _looks_text(s: str, ratio: float = 0.85) -> bool:
    """Acepta solo texto plausible (nombres). Descarta la basura del descifrado de bytes binarios:
    (a) símbolos de bloque/caja de cp850 (no-letra) y (b) rachas de letras ACENTUADAS — el texto
    real es casi todo ASCII (el español usa pocos acentos), la basura es casi toda bytes altos."""
    if len(s) < 2 or not (s[0].isalpha() and ord(s[0]) < 128 or (s[0].isdigit() and len(s) > 3)):
        return False
    if any(ord(c) < 32 or ord(c) == 127 for c in s):
        return False
    weird = sum(0 if (c.isalpha() or c in _ASCII_OK) else 1 for c in s)
    if weird > 1 or (weird == 1 and len(s) < 6):
        return False
    nonascii = sum(1 for c in s if ord(c) >= 128)
    if nonascii > max(1, len(s) * 0.30):               # demasiados acentos = basura
        return False
    return (len(s) - weird) >= len(s) * ratio


@dataclass
class Field:
    """Un campo de texto localizado en el fichero."""
    off: int          # offset del prefijo de longitud
    lenw: int         # ancho del prefijo (1 = u8, 2 = u16)
    text: str         # texto en claro
    kind: str = ""    # etiqueta heurística (equipo_corto, equipo_largo, estadio, entrenador…)

    @property
    def data_off(self) -> int:
        return self.off + self.lenw

    cp: str = _CP

    @property
    def length(self) -> int:
        return len(self.text.encode(self.cp, "replace"))


@dataclass
class Team:
    name: str
    fields: list[Field] = field(default_factory=list)     # campos de club (corto, largo, estadio…)
    coach: list[Field] = field(default_factory=list)
    players: list[list[Field]] = field(default_factory=list)   # cada jugador = lista de campos
    start: int = 0
    end: int = 0


class Pcf3DB:
    """Base `.DBC` de PCF 3.0, editable in-place."""

    def __init__(self, data: bytes, name: str = ""):
        self.raw = bytearray(data)
        self.name = name
        self.header_end = self._header_end()
        self.lenw = self._detect_lenw()
        self.cp = self._detect_cp()
        self.fields: list[Field] = self._scan_fields()
        if self.name.upper() in _LONGITUD_FIJA:
            self.fields = self._completa_lineas(self.fields)
        self.teams: list[Team] = self._group_teams()

    def _detect_cp(self) -> str:
        """Codepage del fichero: cp850 (plantillas DOS) vs latin-1 (tablas de competición). Se elige
        el que produce más letras ACENTUADAS válidas (y menos símbolos raros) en los campos."""
        best, best_score = _CP, -10 ** 9
        for cp in _CANDIDATE_CPS:
            score = 0
            for f in self._scan_fields(cp):
                for c in f.text:
                    if ord(c) >= 128:
                        score += 1 if c.isalpha() else -3
            if score > best_score:
                best, best_score = cp, score
        return best

    # -- cabecera --
    def _header_end(self) -> int:
        i = self.raw.find(b"MEDIA")
        return i + 5 if i >= 0 else 0

    def _detect_lenw(self) -> int:
        """u8 vs u16: se decide por cuál produce más campos de texto válidos al inicio."""
        return 1 if self._count_fields(1, limit=4000) >= self._count_fields(2, limit=4000) else 2

    def _count_fields(self, lenw: int, limit: int) -> int:
        d = self.raw
        p = self.header_end
        n = 0
        end = min(len(d), self.header_end + limit)
        while p < end - lenw:
            ln = d[p] if lenw == 1 else struct.unpack_from("<H", d, p)[0]
            if 3 <= ln <= 30 and p + lenw + ln <= len(d):
                s = decode_text(bytes(d[p + lenw:p + lenw + ln]))
                if _looks_text(s):
                    n += 1
                    p += lenw + ln
                    continue
            p += 1
        return n

    # -- escaneo de campos de texto --
    def _scan_fields(self, cp: str | None = None) -> list[Field]:
        cp = cp or getattr(self, "cp", _CP)
        d = self.raw
        lw = self.lenw
        out: list[Field] = []
        p = self.header_end
        while p < len(d) - lw:
            ln = d[p] if lw == 1 else struct.unpack_from("<H", d, p)[0]
            if 3 <= ln <= _MAX_TEXTO and p + lw + ln <= len(d):
                # Filtro barato ANTES de descifrar: el primer carácter de un texto real es una
                # letra ASCII (o un dígito). Descifrar solo ese byte descarta la inmensa mayoría
                # de candidatos sin construir la cadena entera — subir el tope de 30 a 64 había
                # duplicado los intentos y el parseo se fue a 5 s por fichero.
                c0 = d[p + lw] ^ ((0xC0 + ln) & 0xFF)
                if not (65 <= c0 <= 90 or 97 <= c0 <= 122 or 48 <= c0 <= 57):
                    p += 1
                    continue
                s = decode_text(bytes(d[p + lw:p + lw + ln]), cp)
                if _looks_text(s):
                    out.append(Field(p, lw, s, cp=cp))
                    p += lw + ln
                    continue
            p += 1
        return out

    def _completa_lineas(self, campos: list[Field]) -> list[Field]:
        """Recupera las líneas que el escaneo se deja por largas, caminando entre rótulos."""
        anclas = [i for i, f in enumerate(campos) if f.text.startswith(_ROTULOS)]
        if not anclas:
            return campos
        out = campos[:anclas[0] + 1]
        for k, i in enumerate(anclas):
            f = campos[i]
            tope = campos[anclas[k + 1]].off if k + 1 < len(anclas) else len(self.raw)
            p, bloque = f.data_off + f.length, []
            while p < tope:
                ln = self.raw[p]
                if ln == 0 or p + 1 + ln > tope:
                    break
                bloque.append(Field(p, 1, decode_text(bytes(self.raw[p + 1:p + 1 + ln]), self.cp),
                                    cp=self.cp))
                p += 1 + ln
            # solo se acepta el paseo si llega hasta el rótulo siguiente (si no, se deja lo de antes)
            viejos = [x for x in campos[i + 1:] if x.off < tope]
            out += bloque if bloque and tope - p <= 4 else viejos
            if k + 1 < len(anclas):
                out.append(campos[anclas[k + 1]])
        return out

    # -- agrupar en equipos (RE 2026-08-29) -----------------------------------------------
    # El fichero NO marca los equipos, hay que deducirlos. La regla vieja («un equipo empieza en el
    # nombre largo, que lleva `\\`») fallaba de dos maneras: perdía al LLEIDA —su nombre largo es
    # 'U.E. LLEIDA', sin barra— y no veía a las ESTRELLAS MUNDIALES, que no tienen cabecera de club.
    # Sus jugadores se pegaban al equipo anterior (Rayo 44, Compostela 42). Ahora se camina:
    #
    #   · JUGADOR = dos textos PEGADOS (apodo + nombre) seguidos de 13 bytes que encajan: 2 u32 de
    #     offset de foto, dorsal <= 99 y demarcación <= 3.
    #   · CABECERA DE EQUIPO = pareja de textos pegados que NO es un jugador. Forma fija, con huecos
    #     CONSTANTES entre campos (verificado en los 40 equipos del 94-95):
    #        [oficial] corto·largo PEGADO · estadio h=19 · presidente h=12 · patrocinador h=4
    #        · marca PEGADO · ciudad h=10 · entrenador corto · entrenador largo PEGADO
    #     Rayo y Lleida no traen presidente, así que los huecos ETIQUETAN pero no DELIMITAN.
    #   · El ENTRENADOR tiene la misma pinta que un jugador y a veces cuela como tal (Valdano en el
    #     Madrid). Va SIEMPRE detrás de la ciudad, así que se reclama por posición.
    #   · Equipo SIN cabecera (Estrellas Mundiales): el bloque de 12 bytes de medias deja de estar
    #     pegado al arranque del jugador siguiente.
    #
    # Comprobación: la cabecera declara cuántos equipos hay (u16 tras la firma) y cuadra: 20 por
    # división, más las Estrellas Mundiales en 1ª.
    _HUECOS_CABECERA = (19, 12, 4, 0, 10)      # estadio, presidente, patrocinador, marca, ciudad
    # OJO: el último NO es la ciudad (así estaba etiquetado antes). En 1ª guarda la clave del
    # equipo en mayúsculas —'BARCELONA', 'MADRID', 'ATHLETIC'— y en 2ª todos comparten 'rayo'.
    _ETIQUETAS = ("estadio", "presidente", "patrocinador", "marca", "clave")

    def _hueco(self, i: int) -> int | None:
        """Bytes entre el fin del campo i-1 y el principio del i (0 = pegados)."""
        if i <= 0 or i >= len(self.fields):
            return None
        ant = self.fields[i - 1]
        return self.fields[i].off - (ant.data_off + ant.length)

    def _es_jugador(self, i: int) -> bool:
        """¿Los campos i (apodo) e i+1 (nombre) arrancan un registro de JUGADOR?"""
        f = self.fields
        if i + 1 >= len(f) or self._hueco(i + 1) != 0:
            return False
        p = f[i + 1].data_off + f[i + 1].length
        if p + 13 > len(self.raw):
            return False
        b = self.raw[p:p + 13]
        tope = len(self.raw) * 4                     # los offsets apuntan al .DGF, no aquí
        return (b[8] <= 99 and b[12] <= 3
                and struct.unpack_from("<I", b, 0)[0] < tope
                and struct.unpack_from("<I", b, 4)[0] < tope)

    def declared_teams(self) -> int | None:
        """Nº de equipos que declara la cabecera (u16 tras la firma). Comprobación, no dogma."""
        try:
            return struct.unpack_from("<H", self.raw, self.header_end + 6)[0]
        except Exception:
            return None

    def _group_teams(self) -> list[Team]:
        import bisect
        n = len(self.fields)
        jug = [i for i in range(n) if self._es_jugador(i)]
        if not jug:
            return []
        cabs: dict[int, list[int]] = {}
        for i in range(n - 1):
            if self._hueco(i + 1) == 0 and not self._es_jugador(i):
                cabs.setdefault(bisect.bisect_left(jug, i), []).append(i)
        cortes = {k for k in cabs if k > 0}
        for k in range(1, len(jug)):                 # equipos sin cabecera
            sig = self.fields[jug[k]].off
            if not self._is_ratings(self.raw[sig - 12:sig]):
                cortes.add(k)
        limites = [0] + sorted(cortes) + [len(jug)]

        teams: list[Team] = []
        for a, b in zip(limites, limites[1:]):
            ids = cabs.get(a, [])
            ini = ids[0] if ids else jug[a]
            sueltos: list[Field] = []
            if not ids and a > 0:
                # Equipo SIN cabecera de club (Estrellas Mundiales): sus campos —nombre, clave y
                # 'Comentario'— no van pegados entre sí, así que se recogen los que quedan detrás
                # del bloque de medias del último jugador del equipo anterior.
                # La cabecera arranca justo detrás del bloque de medias del ÚLTIMO jugador del
                # equipo anterior. Ese bloque se busca HACIA DELANTE desde el nombre de ese
                # jugador y exigiendo `hasNext == 0` (es fin de equipo): hacia atrás no vale
                # —los ~270 B de relleno de esta misma cabecera dan falsos positivos— y por el
                # "hueco más grande" tampoco, que era lo que había y se rompía en cuanto cambiaba
                # el equipo anterior (al mover equipos de división, las Estrellas se quedaban con
                # el nombre de una frase de la biografía del vecino).
                prev = jug[a - 1]
                desde = self.fields[prev + 1].data_off + self.fields[prev + 1].length
                tope = self.fields[jug[a]].off
                r = next((q for q in range(desde, max(desde, tope - 12))
                          if self._is_ratings(self.raw[q:q + 12]) and self.raw[q + 11] == 0), None)
                if r is not None:
                    corte = next((k for k in range(prev, jug[a])
                                  if self.fields[k].off >= r + 12), None)
                    if corte is not None:
                        sueltos = self.fields[corte:jug[a]]
                        ini = corte
            t = Team(name=self.fields[ini].text, start=self.fields[ini].off)
            if sueltos:
                t.fields = sueltos
                sueltos[0].kind = "corto"
                if len(sueltos) > 1:
                    sueltos[1].kind = "clave"
            if ids:
                club, entre, tras = self._label_header(ini, jug[a])
                t.fields, t.coach = club, entre
                if not entre and tras == jug[a] and b - a > 1:
                    t.coach = self.fields[tras:tras + 2]      # colaba como jugador (Valdano)
                    t.coach[0].kind = "entrenador_corto"
                    if len(t.coach) > 1:
                        t.coach[1].kind = "entrenador_largo"
                    a += 1
                t.name = next((f.text for f in club if f.kind == "corto"), t.name)
            t.players = []
            for i in jug[a:b]:
                ficha = self.fields[i:i + 2]
                ficha[0].kind = "apodo"                    # etiquetadas para saber su tope
                if len(ficha) > 1:
                    ficha[1].kind = "nombre"
                t.players.append(ficha)
            teams.append(t)
        for t, sig in zip(teams, teams[1:]):
            t.end = sig.start
        if teams:
            teams[-1].end = len(self.raw)
        return teams

    def _label_header(self, ini: int, fin: int) -> tuple[list[Field], list[Field], int]:
        """Etiqueta la cabecera [ini, fin). Devuelve (campos de club, entrenador, índice siguiente)."""
        campos = self.fields[ini:fin]
        if not campos:
            return [], [], fin
        c = next((k for k in range(len(campos) - 1) if self._hueco(ini + k + 1) == 0), None)
        if c is None:
            return campos, [], fin
        # el nombre OFICIAL, cuando lo hay, va pegado al corto: la racha es de TRES, no de dos
        if c + 2 < len(campos) and self._hueco(ini + c + 2) == 0:
            campos[c].kind = "oficial"
            c += 1
        campos[c].kind, campos[c + 1].kind = "corto", "largo"
        # Los huecos son constantes, pero no todos los clubes traen todos los campos (Rayo no
        # tiene presidente) y alguno mete uno de más. Se casa cada campo con la PRIMERA etiqueta
        # que le cuadre y se descartan las que quedan por detrás; en cuanto un campo no casa con
        # ninguna, se acabó el bloque de club.
        pendientes = list(zip(self._HUECOS_CABECERA, self._ETIQUETAS))
        k = c + 2
        while k < len(campos) and pendientes:
            h = self._hueco(ini + k)
            for idx, (hh, lbl) in enumerate(pendientes):
                if h == hh:
                    campos[k].kind = lbl
                    pendientes = pendientes[idx + 1:]
                    break
            else:
                break
            k += 1
        # El ENTRENADOR es la PRIMERA entrada tras el bloque de club: o pareja pegada
        # (Cruyff/'Johan CRUYFF') o un nombre suelto sin nombre largo (Valdano). Algunos clubes
        # encadenan varios técnicos con sus declaraciones; el del equipo es el primero.
        entre: list[Field] = []
        j = k
        while j < len(campos):
            if j + 1 < len(campos) and self._hueco(ini + j + 1) == 0:
                # ...salvo que detrás venga un campo de club que aún faltaba por casar: entonces
                # esta pareja era del bloque de club, no el técnico (Rayo, que no trae presidente,
                # colaba 'Dhul'/'Joma' —patrocinador y marca— como entrenador).
                if (j + 2 < len(campos)
                        and any(self._hueco(ini + j + 2) == h for h, _ in pendientes)):
                    j += 2
                    continue
                entre = campos[j:j + 2]
                break
            if ini + j + 1 == fin:                       # último campo antes del 1er jugador
                entre = campos[j:j + 1]
                break
            j += 1
        # los dos campos del técnico, etiquetados por separado: así cada uno sabe su tope de
        # texto (el apodo y el nombre completo no admiten lo mismo)
        if entre:
            entre[0].kind = "entrenador_corto"
            if len(entre) > 1:
                entre[1].kind = "entrenador_largo"
        club = [f for f in campos if f.kind and not f.kind.startswith("entrenador")]
        return club, entre, ini + k

    # -- datos binarios del jugador (RE 2026-08-29/30) --------------------------------------
    # Tras el nombre completo van 13 bytes: [u32 cara][u32 mini][dorsal][b9][b10][b11][demarcación]
    #   · dorsal        99 = sin dorsal
    #   · b10           POSICIÓN FINA dentro de la demarcación (lateral derecho, líbero, central…):
    #                   Ferrer y Chendo 1, Sergi y Lasa 2, Koeman y Abelardo 3, Nadal y Nando 4,
    #                   Sanchís/Alkorta/Hierro 5. Coherente en las 40 plantillas.
    #   · b11           BANDERAS. bit0 = EXTRANJERO, validado contra las plantillas reales del
    #                   94-95: lo llevan 127 de 869 fichas (14,6%) y son exactamente los de fuera
    #                   (Koeman, Stoitchkov, Hagi, Romário, Redondo, Laudrup, Zamorano, Djukic…),
    #                   ningún español. bit4 = probable ORIUNDO/nacionalizado: lo llevan Donato y
    #                   Engonga —españoles de origen brasileño y guineano— SIN el bit de
    #                   extranjero, y Romário o Mauro Silva con los dos. (bit4 sin confirmar.)
    #   · b9            ESTADO del jugador en la temporada, que el juego pinta junto a su nombre
    #                   en la plantilla: 0 = nada, 1 = **NF** (nuevo fichaje), 2 = **AS**
    #                   (ascendido del filial), 3 = **BJ** (baja). Las siglas están en
    #                   `PCFUTBOL.DAT`: "NF=Nuevo Fichaje   AS=Ascendido del filial   BJ=Baja".
    #                   Verificado contra el 94-95: en el Madrid son NF Cañizares, Quique,
    #                   Redondo, Laudrup y Amavisca (sus cinco fichajes) y AS **Raúl**, que subió
    #                   del Castilla; en el Barça, AS **Jordi Cruyff** y BJ **Romário**, que se
    #                   marchó al Flamengo en enero.
    # Después va el lugar de nacimiento [u8 len][texto] y, pegados, DÍA, MES y AÑO-1900.
    # OJO: la fecha NO se puede localizar contando campos — hay fichas sin lugar de nacimiento
    # (Tomás, del Atlético) y entonces se lee basura. Por eso se ancla en el campo de texto que
    # empieza EXACTAMENTE donde toca, y si no está, no hay fecha.
    def _campo_en(self, off: int) -> "Field | None":
        if getattr(self, "_idx_off", None) is None:
            self._idx_off = {f.off: f for f in self.fields}
        return self._idx_off.get(off)

    def player_info(self, team_i: int, k: int) -> dict:
        """{dorsal, demarcacion, posicion, extranjero, oriundo, lugar, nacimiento} del jugador k."""
        if not (0 <= team_i < len(self.teams)):
            return {}
        pls = self.teams[team_i].players
        if not (0 <= k < len(pls)) or len(pls[k]) < 2:
            return {}
        p = pls[k][1].data_off + pls[k][1].length
        b = self.raw[p:p + 13]
        if len(b) < 13:
            return {}
        out = {"dorsal": None if b[8] == 99 else b[8], "demarcacion": b[12],
               "posicion": b[10], "extranjero": bool(b[11] & 1), "oriundo": bool(b[11] & 16),
               "estado": b[9] if b[9] in (0, 1, 2, 3) else 0,
               "lugar": "", "nacimiento": None}
        campo = self._campo_en(p + 13)
        if campo is not None:
            out["lugar"] = campo.text
            q = campo.data_off + campo.length
            if q + 3 <= len(self.raw):
                d, mes, anyo = self.raw[q], self.raw[q + 1], self.raw[q + 2]
                # el mes puede venir 99 = DESCONOCIDO (misma convención que el dorsal 99): el
                # panameño Moreno del Real Madrid B es 29/99/74, con día y año buenos. El año, en
                # cambio, manda: Jafa (Orense) trae 08, imposible en el 94-95, y se descarta.
                if 1 <= d <= 31 and 30 <= anyo <= 85 and (1 <= mes <= 12 or mes == 99):
                    out["nacimiento"] = (1900 + anyo, mes if mes != 99 else None, d)
        return out

    # -- sacar y meter FICHAS de un equipo (RE 2026-08-30) ---------------------------------
    # Igual que los bloques teselan el fichero, las FICHAS teselan el bloque del equipo:
    #   bloque = cabecera de club + fichas concatenadas + una cola de 0 a 37 bytes
    # (comprobado en los 41 equipos). Una ficha va desde su apodo hasta el final de su bloque de
    # medias, y **su ÚLTIMO BYTE es el `hasNext`**: 1 si detrás viene otro jugador, 0 en el
    # último. No hay contador de plantilla en ninguna parte —el juego recorre hasta ese 0—, así
    # que añadir o quitar jugadores es recolocar fichas y dejar bien ese byte.

    def player_range(self, team_i: int, k: int) -> "tuple[int, int] | None":
        """(inicio, fin) de la ficha del jugador k dentro del fichero."""
        if not (0 <= team_i < len(self.teams)):
            return None
        t = self.teams[team_i]
        if not (0 <= k < len(t.players)):
            return None
        r = self._ratings_off(t, k)
        return (t.players[k][0].off, r + 12) if r is not None else None

    def player_bytes(self, team_i: int, k: int) -> bytes | None:
        r = self.player_range(team_i, k)
        return bytes(self.raw[r[0]:r[1]]) if r else None

    def player_photo_ptr_pos(self, team_i: int, k: int) -> int | None:
        """Dónde caen, DENTRO de la ficha, los dos u32 de foto (cara grande y mini). Hacen falta
        para repuntarlos cuando el jugador cambia de equipo: cada equipo tiene su propio `.DGF`."""
        r = self.player_range(team_i, k)
        pl = self.teams[team_i].players[k]
        if not r or len(pl) < 2:
            return None
        return (pl[1].data_off + pl[1].length) - r[0]

    @staticmethod
    def con_has_next(ficha: bytes, hay_mas: bool) -> bytes:
        """La misma ficha con el byte final puesto a 1 (viene otro detrás) o a 0 (es el último)."""
        b = bytearray(ficha)
        if b:
            b[-1] = 1 if hay_mas else 0
        return bytes(b)

    def replace_team_players(self, team_i: int, fichas: "list[bytes]") -> bytes:
        """Fichero nuevo con la plantilla del equipo `team_i` sustituida por `fichas`.
        Se respeta la cabecera de club y la cola, y se arregla el `hasNext` de todas."""
        t = self.teams[team_i]
        if not t.players:
            raise ValueError("ese equipo no tiene plantilla que sustituir")
        if not fichas:
            raise ValueError("un equipo no se puede quedar sin jugadores")
        ini = t.players[0][0].off
        fin = self._ratings_off(t, len(t.players) - 1)
        if fin is None:
            raise ValueError("no se localiza el final de la plantilla")
        cola = bytes(self.raw[fin + 12:t.end])
        arregladas = [self.con_has_next(f, i < len(fichas) - 1) for i, f in enumerate(fichas)]
        bloque = bytes(self.raw[t.start:ini]) + b"".join(arregladas) + cola
        bloques = [self.team_block(i) for i in range(len(self.teams))]
        bloques[team_i] = bloque
        return self.rebuild(bloques)

    # -- fecha de nacimiento, escribible ---------------------------------------------------
    def player_birth_off(self, team_i: int, k: int) -> int | None:
        """Offset de los 3 bytes [día][mes][año-1900], o None si la ficha no los tiene (hay 14
        jugadores sin lugar de nacimiento y ahí no hay dónde escribir)."""
        pls = self.teams[team_i].players if 0 <= team_i < len(self.teams) else []
        if not (0 <= k < len(pls)) or len(pls[k]) < 2:
            return None
        campo = self._campo_en(pls[k][1].data_off + pls[k][1].length + 13)
        if campo is None:
            return None
        q = campo.data_off + campo.length
        return q if q + 3 <= len(self.raw) else None

    def set_player_birth(self, team_i: int, k: int, *, anyo: int | None = None,
                         mes: int | None = None, dia: int | None = None) -> bool:
        """Cambia la fecha in-place (3 bytes de longitud fija: no mueve nada). False si la ficha
        no tiene fecha donde escribir."""
        off = self.player_birth_off(team_i, k)
        if off is None:
            return False
        if dia is not None:
            self.raw[off] = max(1, min(31, int(dia)))
        if mes is not None:
            self.raw[off + 1] = 99 if mes == 99 else max(1, min(12, int(mes)))
        if anyo is not None:
            self.raw[off + 2] = int(anyo) % 100
        return True

    # -- datos económicos del club (RE 2026-08-30) ----------------------------------------
    # Salieron comparando un filial con su club padre . En los huecos fijos de
    # la cabecera hay tres u32:
    #   estadio → presidente (12 B): [u32 puntero][u32 AFORO][u32 SOCIOS]
    #   presidente → patrocinador (4 B): [u32 PRESUPUESTO] (millones de pesetas)
    # Verificado: Camp Nou 112.000, Bernabéu 107.000, San Mamés 47.000, Sánchez Pizjuán 61.000;
    # y el presupuesto ordena la liga como tocaba en el 94-95 (Barça 7.895, Madrid 8.100, media
    # tabla ~1.000, 2ª entre 127 y 500).
    # **El filial COMPARTE socios y presupuesto con su club padre** —son el mismo club— pero
    # tiene su propio aforo (Barcelona B: Miniestadi, 16.500).
    ECONOMIA = {"aforo": 4, "socios": 8}          # desplazamiento dentro del hueco de 12
    # Hueco largo→estadio (19 B): [u32 ptr][u32 ptr][u32 ptr][u16 A][u16 B][u8 C][u16 FUNDACIÓN]
    # A, B y C los COPIA el filial de su club padre (Barça y Barça B: 23/89/0; Madrid y Madrid B:
    # 35/68/1; Athletic y Athletic B: 26/83/4) → son la equipación, que el filial hereda. El año
    # de fundación, en cambio, es suyo: Barcelona 1899 pero Barcelona B 1970.
    # Verificado: Palamós 1898, Athletic 1898, Barcelona 1899, Español 1900, Madrid 1902,
    # Getafe 1983, Barcelona B 1970, Osasuna 1920, Rayo 1924.
    FUNDACION_OFF = 17

    def _hueco_fundacion(self, i: int) -> int | None:
        if not (0 <= i < len(self.teams)):
            return None
        g = {f.kind: f for f in self.teams[i].fields}
        largo, est = g.get("largo"), g.get("estadio")
        if not largo or not est:
            return None
        a = largo.data_off + largo.length
        return a + self.FUNDACION_OFF if est.off - a == 19 else None

    def _hueco_eco(self, i: int) -> "tuple[int, int] | None":
        """(offset del hueco estadio→presidente, offset del hueco presidente→patrocinador)."""
        if not (0 <= i < len(self.teams)):
            return None
        t = self.teams[i]
        g = {f.kind: f for f in t.fields}
        est, pre, pat = g.get("estadio"), g.get("presidente"), g.get("patrocinador")
        if not est or not pre:
            return None
        a = est.data_off + est.length
        if pre.off - a != 12:
            return None
        b = pre.data_off + pre.length
        return (a, b if (pat and pat.off - b == 4) else -1)

    def team_economy(self, i: int) -> dict:
        """{aforo, socios, presupuesto} del club, o {} si su cabecera no los trae (las Estrellas
        Mundiales y el Rayo, que no tiene campo de presidente)."""
        h = self._hueco_eco(i)
        if h is None:
            return {}
        a, b = h
        out = {k: struct.unpack_from("<I", self.raw, a + d)[0] for k, d in self.ECONOMIA.items()}
        if b >= 0:
            out["presupuesto"] = struct.unpack_from("<I", self.raw, b)[0]
        f = self._hueco_fundacion(i)
        if f is not None:
            out["fundacion"] = struct.unpack_from("<H", self.raw, f)[0]
        return out

    def set_team_economy(self, i: int, campo: str, valor: int) -> bool:
        """Cambia uno de los tres. Son u32 de sitio fijo: no mueven nada."""
        h = self._hueco_eco(i)
        if h is None:
            return False
        a, b = h
        valor = max(0, min(0xFFFFFFFF, int(valor)))
        if campo == "fundacion":
            return self.set_team_founded(i, valor)
        if campo in self.ECONOMIA:
            struct.pack_into("<I", self.raw, a + self.ECONOMIA[campo], valor)
            return True
        if campo == "presupuesto" and b >= 0:
            struct.pack_into("<I", self.raw, b, valor)
            return True
        return False

    def set_team_founded(self, i: int, anyo: int) -> bool:
        off = self._hueco_fundacion(i)
        if off is None:
            return False
        struct.pack_into("<H", self.raw, off, max(1800, min(2100, int(anyo))))
        return True

    ESTADOS = {0: "", 1: "NF", 2: "AS", 3: "BJ"}

    def set_player_estado(self, team_i: int, k: int, estado: int) -> bool:
        """0 = nada · 1 = nuevo fichaje · 2 = ascendido del filial · 3 = baja. Un byte de sitio
        fijo: se escribe donde está y no mueve nada."""
        if estado not in self.ESTADOS:
            raise ValueError("estado 0-3")
        pls = self.teams[team_i].players if 0 <= team_i < len(self.teams) else []
        if not (0 <= k < len(pls)) or len(pls[k]) < 2:
            return False
        self.raw[pls[k][1].data_off + pls[k][1].length + 9] = estado
        return True

    def set_player_dorsal(self, team_i: int, k: int, dorsal: int | None) -> bool:
        """Dorsal del jugador (None = sin dorsal, que el fichero guarda como 99).

        En PCF 3.0 el dorsal NO es decorativo: **el once inicial son los dorsales 1-11**. Es la
        convención de la época (entonces los números no eran fijos por jugador, del 1 al 11
        jugaban los titulares) y el fichero la respeta: 35 de los 41 equipos traen exactamente
        once jugadores con dorsal 1-11, y 30 de ellos forman un once coherente —un portero, de
        tres a cinco defensas y algún delantero—. La plantilla, en cambio, está ORDENADA POR
        PUESTO, así que «los once primeros» no son el once: en 32 equipos saldrían con dos
        porteros.

        Un byte de sitio fijo: se escribe donde está y no mueve nada.
        """
        d = 99 if dorsal is None else int(dorsal)
        if not (0 <= d <= 99):
            raise ValueError("dorsal 0-99 (99 = sin dorsal)")
        pls = self.teams[team_i].players if 0 <= team_i < len(self.teams) else []
        if not (0 <= k < len(pls)) or len(pls[k]) < 2:
            return False
        self.raw[pls[k][1].data_off + pls[k][1].length + 8] = d
        return True

    def player_photo_offset(self, pl: list) -> tuple[int, int]:
        """(offset_cara_grande, offset_mini) de un jugador. En el registro DBC, justo tras el NOMBRE
        completo hay 2 u32 LE: el offset de la cara 124×182 y el del mini 24×24 dentro del `.DGF`
        del equipo (0 = no tiene). VERIFICADO: es el mapeo REAL jugador→foto (no por posición)."""
        if len(pl) < 2:
            return (0, 0)
        pos = pl[1].data_off + pl[1].length
        if pos + 8 > len(self.raw):
            return (0, 0)
        return (struct.unpack_from("<I", self.raw, pos)[0],
                struct.unpack_from("<I", self.raw, pos + 4)[0])

    def team_escudo_ptr(self, i: int, esc_offsets) -> "tuple[int, int] | None":
        """(posición del puntero dentro del fichero, valor) del escudo del equipo `i`. Igual que
        `team_escudo_offset` pero diciendo DÓNDE está, que es lo que hace falta para repuntarlo al
        mover el equipo de división."""
        t = self.teams[i]
        for p in range(t.start, t.end - 4):
            v = struct.unpack_from("<I", self.raw, p)[0]
            if v in esc_offsets:
                return p, v
        return None

    # -- mover un equipo de división (RE 2026-08-29) ---------------------------------------------
    # Los bloques TESELAN el fichero: cabecera + bloques concatenados = fichero original, byte a
    # byte, en las dos divisiones (comprobado). Y no hay tabla de offsets en la cabecera —el juego
    # recorre—, así que un bloque se puede llevar tal cual al otro fichero. Lo único que NO viaja
    # es el puntero del escudo, que apunta al `.DGF` de SU división: hay que anexar los gráficos al
    # del destino y repuntar (ver `pcf3_dgf.append_group`).

    def header_bytes(self) -> bytes:
        """Los bytes anteriores al primer equipo (firma + contador declarado)."""
        return bytes(self.raw[:self.teams[0].start]) if self.teams else bytes(self.raw)

    def team_block(self, i: int) -> bytes:
        t = self.teams[i]
        return bytes(self.raw[t.start:t.end])

    def rebuild(self, blocks: "list[bytes]") -> bytes:
        """Fichero nuevo = cabecera + los bloques dados, en ese orden."""
        return self.header_bytes() + b"".join(blocks)

    def team_escudo_offset(self, i: int, esc_offsets) -> int | None:
        """Offset (en el `.DGF` de división) del escudo 48×64 del equipo `i`. En el bloque del equipo,
        cerca del inicio (~20 B), hay un u32 LE que apunta a su escudo. Devolvemos el PRIMER u32 del
        bloque que casa con un escudo conocido → mapeo REAL (robusto a equipos de más en el DGF, p.ej.
        Lleida en 2ª, que descuadraban el mapeo por orden)."""
        r = self.team_escudo_ptr(i, esc_offsets)
        return r[1] if r else None

    # -- medias (RE 2026-07-17) -------------------------------------------------------------
    # Al FINAL del registro de cada jugador hay un bloque fijo de 12 bytes:
    #   [valor u16 LE][VE RE AG CA][4 flags 0/1][00][flagSiguiente]
    # VE/RE/AG/CA = las 4 medias (0-99, sin cifrar; validadas con la calidad real: Stoitchkov
    # 95/80/99/90, Angoy 67/61/57/63…). valor = precio de mercado. flagSiguiente=1 salvo el
    # último jugador del equipo (=0). El bloque va justo antes del apodo del jugador siguiente
    # (o, para el último, antes del fin del equipo, tras un pequeño trailer).
    @staticmethod
    def _is_ratings(b) -> bool:
        return (len(b) == 12 and b[10] == 0 and b[11] in (0, 1)
                and all(1 <= b[i] <= 99 for i in (2, 3, 4, 5))
                and all(b[i] <= 15 for i in (6, 7, 8, 9)))

    def _ratings_off(self, team: "Team", k: int) -> int | None:
        players = team.players
        if not (0 <= k < len(players)):
            return None
        lo = players[k][0].off
        hi = players[k + 1][0].off if k + 1 < len(players) else team.end
        for p in range(hi - 12, lo, -1):            # el ÚLTIMO bloque válido antes del límite
            if self._is_ratings(self.raw[p:p + 12]):
                return p
        return None

    def player_ratings(self, team_i: int, k: int) -> dict | None:
        """{off, valor, medias:[VE,RE,AG,CA], media} del jugador k, o None si no se localiza."""
        off = self._ratings_off(self.teams[team_i], k)
        if off is None:
            return None
        b = self.raw[off:off + 12]
        medias = [b[2], b[3], b[4], b[5]]
        return {"off": off, "valor": b[0] | (b[1] << 8), "medias": medias,
                "media": round(sum(medias) / 4)}

    # ---- EQUIPACIÓN DEL SIMULADOR (RE 2026-08-30) --------------------------------------------
    # Los 10 bytes que hay entre `marca` y `clave` no son relleno: son la equipación con la que el
    # simulador 2D dibuja a los jugadores. Un byte de PATRÓN y tres colores VGA de 6 bits (0-63):
    #
    #     [patrón] [R G B pantalón] [R G B camiseta 1] [R G B camiseta 2]
    #
    # Contrastado con las equipaciones reales del 94-95: Barcelona azul·azul·granate, Real Madrid
    # todo blanco, Athletic con el pantalón negro, Betis verdiblanco, Celta celeste, Villarreal
    # amarillo con pantalón azul y Valladolid violeta (45,24,39 — no es un color puro, así que no
    # es una tabla de colores fijos sino RGB de verdad). El patrón vale 0 en casi todos, **1 en el
    # Rayo** (su banda diagonal) y 2 en el Compostela.
    KIT_BYTES = 10

    def kit_off(self, team_i: int) -> int | None:
        """Offset de los 10 bytes de equipación, o None si el club no trae cabecera completa."""
        if not (0 <= team_i < len(self.teams)):
            return None
        fs = {f.kind: f for f in self.teams[team_i].fields}
        a, b = fs.get("marca"), fs.get("clave")
        if a is None or b is None:
            return None
        off = a.data_off + a.length
        return off if b.off - off == self.KIT_BYTES else None

    def team_kit(self, team_i: int) -> dict | None:
        off = self.kit_off(team_i)
        if off is None:
            return None
        g = bytes(self.raw[off:off + self.KIT_BYTES])
        return {"patron": g[0],
                "colores": [[g[1 + 3 * k], g[2 + 3 * k], g[3 + 3 * k]] for k in range(3)]}

    def set_team_kit(self, team_i: int, patron: int, colores) -> None:
        """Escribe la equipación. In-place: el hueco es fijo, el fichero no se mueve."""
        off = self.kit_off(team_i)
        if off is None:
            raise ValueError("este equipo no tiene equipación de simulador")
        if not (0 <= patron <= 255) or len(colores) != 3:
            raise ValueError("hacen falta un patrón y tres colores")
        vals = [patron]
        for c in colores:
            if len(c) != 3 or any(not (0 <= int(x) <= 63) for x in c):
                raise ValueError("los colores son VGA de 6 bits (0-63)")
            vals += [int(x) for x in c]
        self.raw[off:off + self.KIT_BYTES] = bytes(vals)

    def set_player_media(self, team_i: int, k: int, idx: int, value: int) -> None:
        """Fija la media `idx` (0=VE,1=RE,2=AG,3=CA) del jugador k. In-place byte-perfect."""
        if not (0 <= idx <= 3):
            raise ValueError("índice de media 0-3")
        off = self._ratings_off(self.teams[team_i], k)
        if off is None:
            raise ValueError("bloque de medias no encontrado")
        self.raw[off + 2 + idx] = max(0, min(99, int(value)))

    def set_player_valor(self, team_i: int, k: int, valor: int) -> None:
        """Fija el valor de mercado (u16 LE) del jugador k. In-place byte-perfect."""
        off = self._ratings_off(self.teams[team_i], k)
        if off is None:
            raise ValueError("bloque de medias no encontrado")
        v = max(0, min(65535, int(valor)))
        self.raw[off] = v & 0xFF
        self.raw[off + 1] = (v >> 8) & 0xFF

    def team_dict(self, i: int) -> dict:
        """Vista serializable de un equipo (para la API)."""
        t = self.teams[i]

        def fd(f: Field) -> dict:
            return {"off": f.off, "text": f.text, "max": self.tope_de(f), "kind": f.kind}
        return {
            "i": i, "name": t.name,
            "club": [fd(f) for f in t.fields],
            "coach": [fd(f) for f in t.coach],
            "players": [[fd(f) for f in pl] for pl in t.players],
            "economia": self.team_economy(i),
        }

    # -- edición in-place byte-perfect --
    # -- topes de texto (RE 2026-08-30) ---------------------------------------------------------
    # El formato NO impone ningún límite: cada texto va `[u8 longitud][texto]`, así que caben 255
    # caracteres, y dentro del `.DBC` no hay ni tabla de offsets ni punteros absolutos (los del
    # escudo y las fotos apuntan a los `.DGF`, no aquí). Alargar un nombre solo desplaza bytes
    # dentro del fichero y el juego, que RECORRE, lo sigue leyendo.
    #
    # Lo que sí puede tener límite es el JUEGO: cuánto le cabe en su buffer y en pantalla. Como no
    # se puede preguntar, se toma como tope lo que él mismo trae de fábrica, que es la única
    # prueba que hay de lo que digiere sin despeinarse:
    #     apodo 17 ('Txomin Larrainzar')      · nombre 30 ('José Francisco BELMAN González')
    #     entrenador 15/30 · estadio 25 · presidente 29 · patrocinador 26 · club 19/23/30
    TOPES = {"apodo": 17, "nombre": 30, "entrenador_corto": 15, "entrenador_largo": 30,
             "oficial": 30, "corto": 19, "largo": 23, "estadio": 25, "presidente": 29,
             "patrocinador": 26, "marca": 12, "clave": 13}

    def tope_de(self, f: "Field") -> int:
        """Cuánto se puede escribir en este campo: lo que ya ocupa o el tope de su clase, lo que
        sea mayor (nunca se recorta por debajo de lo que el fichero ya trae)."""
        return max(f.length, self.TOPES.get(f.kind or "", f.length))

    def set_field(self, off: int, new_text: str) -> None:
        """Escribe el campo de texto en `off`. Si el texto nuevo NO cabe en el hueco, el fichero
        se recompone con el campo más largo (o más corto) y se vuelve a leer: no hay offsets
        absolutos dentro del `.DBC` que se rompan al desplazar bytes."""
        f = next((x for x in self.fields if x.off == off), None)
        if f is None:
            raise ValueError("campo no encontrado")
        tope = self.tope_de(f)
        raw = inicial_sin_acento(new_text).encode(self.cp, "replace")
        if len(raw) > tope:
            raise ValueError(f"máximo {tope} caracteres")
        if len(raw) == f.length:                            # cabe justo: se escribe en el sitio
            enc = self._cifra(raw, f.length)
            self.raw[f.data_off:f.data_off + f.length] = enc
            f.text = raw.decode(self.cp)
            return
        if self.lenw != 1 or self.name.upper() in _LONGITUD_FIJA:
            # los ficheros de competición usan prefijo de 2 bytes y no se ha comprobado que no
            # tengan tablas de offsets: ahí se sigue conservando la longitud
            if len(raw) > f.length:
                raise ValueError(f"máximo {f.length} caracteres")
            raw = raw + b" " * (f.length - len(raw))
            self.raw[f.data_off:f.data_off + f.length] = self._cifra(raw, f.length)
            f.text = raw.decode(self.cp)
            return
        nuevo = (bytes(self.raw[:f.off]) + bytes([len(raw)]) + self._cifra(raw, len(raw))
                 + bytes(self.raw[f.data_off + f.length:]))
        self._recarga(nuevo)

    def _cifra(self, claro: bytes, length: int) -> bytes:
        return bytes(b ^ ((0xC0 + length + i) & 0xFF) for i, b in enumerate(claro))

    def _recarga(self, data: bytes) -> None:
        """Sustituye el contenido y vuelve a leerlo entero (campos, equipos y plantillas)."""
        self.raw = bytearray(data)
        self._idx_off = None
        self.fields = self._scan_fields()
        self.teams = self._group_teams()

    def to_bytes(self) -> bytes:
        return bytes(self.raw)


def _chunk_players(fields: list[Field]) -> list[list[Field]]:
    """Agrupa los campos en jugadores. VERIFICADO con el formato: cada jugador = [apodo][nombre
    completo PEGADO, gap 0][lugar nac.][trayectoria…]. El apodo va SIEMPRE seguido inmediatamente
    (sin bytes en medio) por el nombre completo; el resto de campos (clubes anteriores, cola de la
    biografía) van con hueco binario. Así que un jugador EMPIEZA donde el campo siguiente es
    contiguo (gap 0); lo que hay entre jugadores (colas de biografía) NO empieza jugador."""
    n = len(fields)

    def adjacent(a: Field, b: Field) -> bool:
        return b.off == a.data_off + a.length          # b pegado justo tras a (sin bytes en medio)

    starts = [i for i in range(n - 1) if adjacent(fields[i], fields[i + 1])]
    players: list[list[Field]] = []
    for k, si in enumerate(starts):
        end = starts[k + 1] if k + 1 < len(starts) else n
        players.append(fields[si:end])
    return players
