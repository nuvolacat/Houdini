"""Creative Voice File (`.VOC`) — el formato de sonido de PC Fútbol 3.0 (2026-08-30).

Es el formato estándar de las Sound Blaster, no un invento de Dinamic. Estructura:

    "Creative Voice File\\x1a"  (20 B)
    [u16 offset de los datos][u16 versión][u16 checksum]      → 26 B de cabecera
    y luego BLOQUES: [u8 tipo][u24 tamaño][datos]

Los tipos que aparecen en PCF3:
  · **1** — sonido: `[u8 constante de tiempo][u8 compresión]` + PCM de 8 bits SIN SIGNO.
    La frecuencia sale de la constante: `1.000.000 / (256 - tc)`.
  · **8** — cabecera extendida que precede a un bloque 1 y trae la frecuencia con más precisión:
    `[u16 constante][u8 compresión][u8 canales]` → `256.000.000 / (canales * (65536 - tc))`.
  · **9** — bloque «nuevo» (VOC 1.20+): frecuencia en u32, bits y canales explícitos.
  · **0** — fin. **2** — continuación (más PCM, sin cabecera). **3** — silencio. **6/7** — bucle.

Solo se admite **8 bits mono sin comprimir**, que es lo que usa el juego; cualquier otra cosa se
rechaza en vez de devolver ruido.
"""
from __future__ import annotations

import struct

_FIRMA = b"Creative Voice File\x1a"


def es_voc(data: bytes) -> bool:
    return data[:len(_FIRMA)] == _FIRMA


def _freq_de_tc(tc: int) -> int:
    return int(round(1_000_000 / (256 - tc))) if tc < 256 else 8000


def _tc_de_freq(freq: int) -> int:
    return max(0, min(255, 256 - int(round(1_000_000 / max(1, freq)))))


def decode(data: bytes) -> tuple[bytes, int]:
    """(PCM 8 bits sin signo, frecuencia). Junta todos los bloques de sonido del fichero."""
    if not es_voc(data):
        raise ValueError("no es un Creative Voice File")
    ini = struct.unpack_from("<H", data, 20)[0]
    pcm = bytearray()
    freq = 0
    p = ini
    while p + 1 <= len(data):
        tipo = data[p]
        if tipo == 0:                                   # fin
            break
        if p + 4 > len(data):
            break
        tam = data[p + 1] | (data[p + 2] << 8) | (data[p + 3] << 16)
        cuerpo = data[p + 4:p + 4 + tam]
        if tipo == 1:
            if len(cuerpo) < 2:
                break
            if cuerpo[1] != 0:
                raise ValueError("VOC comprimido: no soportado")
            freq = freq or _freq_de_tc(cuerpo[0])
            pcm += cuerpo[2:]
        elif tipo == 2:                                 # continuación: PCM a secas
            pcm += cuerpo
        elif tipo == 8:                                 # cabecera del bloque siguiente
            if len(cuerpo) >= 4:
                tc, comp, canales = struct.unpack_from("<HBB", cuerpo, 0)
                if comp != 0:
                    raise ValueError("VOC comprimido: no soportado")
                freq = int(round(256_000_000 / ((canales + 1) * (65536 - tc))))
        elif tipo == 9:                                 # bloque nuevo, con todo explícito
            if len(cuerpo) >= 12:
                f, bits, canales = struct.unpack_from("<IBB", cuerpo, 0)
                if bits != 8 or canales != 1:
                    raise ValueError("solo se admite 8 bits mono")
                freq = f
                pcm += cuerpo[12:]
        elif tipo == 3:                                 # silencio: se rellena con el punto medio
            if len(cuerpo) >= 3:
                n, tc = struct.unpack_from("<HB", cuerpo, 0)
                freq = freq or _freq_de_tc(tc)
                pcm += b"\x80" * (n + 1)
        p += 4 + tam
    if not pcm:
        raise ValueError("el VOC no trae sonido")
    return bytes(pcm), freq or 11025


def bucle_de(data: bytes) -> int | None:
    """Nº de repeticiones si el fichero envuelve su sonido en un bucle (bloques 6/7), o None.
    Hay que saberlo para no cargárselo al regrabar: el ambiente del público y el gol se repiten,
    y sin el bucle sonarían una sola vez."""
    if not es_voc(data):
        return None
    p = struct.unpack_from("<H", data, 20)[0]
    while p + 4 <= len(data) and data[p] != 0:
        tam = data[p + 1] | (data[p + 2] << 8) | (data[p + 3] << 16)
        if data[p] == 6 and tam >= 2:
            return struct.unpack_from("<H", data, p + 4)[0]
        p += 4 + tam
    return None


def encode(pcm: bytes, freq: int, bucle: int | None = None) -> bytes:
    """VOC nuevo con ese PCM. Se escribe un bloque de tipo 1, que es el que entiende cualquier
    versión del formato (los de tipo 8/9 son extensiones posteriores). Si el original venía en
    bucle, se conserva envolviéndolo en los bloques 6/7."""
    out = bytearray(_FIRMA)
    out += struct.pack("<HH", 26, 0x010A)               # datos en 26, versión 1.10
    out += struct.pack("<H", (~0x010A + 0x1234) & 0xFFFF)   # checksum que manda el formato
    if bucle is not None:
        out += bytes([6, 2, 0, 0]) + struct.pack("<H", bucle)
    # Bloque 8 delante, como hacen los 11 ficheros del juego: su constante es de 16 bits y
    # guarda la frecuencia EXACTA. Con solo el bloque 1 (constante de 8 bits) los 13000 Hz del
    # silbato se quedaban en 12987.
    tc16 = max(0, min(65535, 65536 - int(round(256_000_000 / max(1, freq)))))
    out += bytes([8, 4, 0, 0]) + struct.pack("<HBB", tc16, 0, 0)
    tam = len(pcm) + 2
    out += bytes([1, tam & 0xFF, (tam >> 8) & 0xFF, (tam >> 16) & 0xFF])
    out += bytes([_tc_de_freq(freq), 0])
    out += pcm
    if bucle is not None:
        out += bytes([7, 0, 0, 0])
    out += b"\x00"                                     # bloque de fin
    return bytes(out)
