"""Codec de texto de PCF 5/6 ("mapa de lupus").

El cifrado base es **XOR 0x61** sobre cada byte, verificado contra el mapa de
caracteres de Hex Workshop (Mapas/PCFLA.map): la tabla de 256 entradas del .map
coincide con `i ^ 0x61` para todo el rango imprimible; el resto son marcadores de
visualización del editor, no una transformación distinta.

    byte_en_fichero = ord(caracter) ^ 0x61
    caracter        = byte_en_fichero ^ 0x61

Los caracteres acentuados de latin-1 sobreviven al XOR como bytes altos; la
fidelidad exacta de esos bytes se validará en Fase 1 con ficheros reales. El round-trip encode∘decode es identidad por construcción.
"""
from __future__ import annotations

XOR_KEY = 0x61
# XOR 0x61 es una permutación fija de 256 valores → tabla de traducción a nivel C
# (bytes.translate) en vez de un bucle Python por byte. Idéntico resultado, ~30x
# más rápido (el parser de v5/6 llama a decode cientos de miles de veces).
_XOR_TABLE = bytes(i ^ XOR_KEY for i in range(256))


def decode(data: bytes | bytearray) -> str:
    """Bytes del fichero -> texto (latin-1)."""
    return bytes(data).translate(_XOR_TABLE).decode("latin-1")


# no descomponibles por NFKD que sí tienen ASCII razonable, + PUNTUACIÓN TIPOGRÁFICA
# (2026-08-16): las fuentes web traen comillas/apóstrofos/guiones "bonitos" que NO están
# en latin-1 — el apóstrofo curvo de "O’Neill" es habitual en las fuentes de datos. Sin este mapa acababan
# como '?' en el juego. Los equivalentes son los del editor comunitario (Codificació.cs:
# “ ” → " · ` ´ → ' · • → · · € → e).
_XLAT = str.maketrans({
    "ł": "l", "Ł": "L", "đ": "d", "Đ": "D", "ħ": "h", "Ħ": "H",
    "ı": "i", "İ": "I", "œ": "oe", "Œ": "OE", "ŋ": "n", "Ŋ": "N",
    # ESCANDINAVAS Y GERMÁNICAS. Son latin-1, así que se colaban CRUDAS en el fichero —y
    # Dinamic no las escribió jamás: cero apariciones de øØæÆåÅßþÞ en los 38.384 nombres de
    # 6.0 Oro, frente a 119 «ü» y 117 «ö», que sí usa. Las equivalencias son LAS SUYAS, sacadas
    # de su propia base: Bjørnebye→«Bjornebye», Sørensen→«Sorensen», Brøndby→«Brondby» (ø→o);
    # Ødegård→«Odegaard», Stensås→«Stensaas», Ålborg→«Aalborg», Århus→«Aarhus» (å→aa); e
    # Idræts→«Idraets» (æ→ae). Ojo: el editor comunitario hace ø→ö, que no es lo que hizo el
    # juego. PCF4 ya las tenía en su propia tabla (`pcf4_text`); faltaban en las otras cinco.
    "ø": "o", "Ø": "O", "å": "aa", "Å": "Aa", "æ": "ae", "Æ": "Ae",
    "ß": "ss", "ẞ": "SS", "þ": "th", "Þ": "Th", "ð": "d", "Ð": "D",
    "“": '"', "”": '"', "„": '"', "‟": '"', "«": '"', "»": '"',
    "‘": "'", "’": "'", "‚": "'", "‛": "'", "′": "'", "″": '"',
    "–": "-", "—": "-", "‑": "-", "‒": "-", "―": "-", "­": "-",
    "•": "·", "…": "...", "€": "E", "™": "", " ": " ", "​": "",
    # OJO: NO plegar ` ´ × ¢ aunque el editor comunitario lo haga — son latin-1 y
    # aparecen en los textos ORIGINALES del juego (0xD5 = ´); plegarlos rompería el
    # round-trip byte-perfecto (lo cazaron los tests de FDI, 2026-08-16).
})


def _to_latin1(s: str) -> str:
    """Transliteración CARÁCTER A CARÁCTER: cada uno se conserva si es latin-1 y solo
    se translitera el que no lo es. (Antes se normalizaba la cadena ENTERA en cuanto
    UN carácter fallaba, así que 'Vinícius “Vini” Júnior' perdía TODAS las tildes por
    culpa de las comillas. Las tildes SÍ existen en la fuente del juego.)"""
    import unicodedata
    out = []
    for ch in s.translate(_XLAT):
        try:
            ch.encode("latin-1")
            out.append(ch)
            continue
        except UnicodeEncodeError:
            pass
        norm = unicodedata.normalize("NFKD", ch)
        limpio = "".join(c for c in norm if not unicodedata.combining(c))
        try:
            limpio.encode("latin-1")
            out.append(limpio)
        except UnicodeEncodeError:
            out.append("?")
    return "".join(out)


# Letras que el juego NO usa y que hay que transliterar cuando el texto viene DE FUERA.
# Son latin-1, así que `encode` las dejaría pasar crudas — y Dinamic no escribió ni una:
# cero apariciones de øØæÆåÅßþÞ en los 154.778 nombres de PCF7/2000/2001 ni en los 38.384 de
# 6.0 Oro. Las equivalencias son LAS SUYAS, leídas de su base: Bjørnebye→«Bjornebye»,
# Sørensen→«Sorensen», Brøndby→«Brondby» (ø→o) · Ødegård→«Odegaard», Stensås→«Stensaas»,
# Århus→«Aarhus» (å→aa) · Idræts→«Idraets» (æ→ae).
#
# NO se aplica en `encode`: esta tabla iría también sobre los textos ORIGINALES del juego, y
# ahí hay bytes que parecen letras y no lo son (el 0xD0 de una nota de prensa de PCF2001), más
# el espacio duro y el guion blando de `_XLAT`. Tocarlos rompe el round-trip byte-perfecto —lo
# cazaron los tests de PCF7 y 2000/2001—. Por eso se llama en la IMPORTACIÓN, donde el texto
# viene de la web y no hay round-trip que preservar.
_XLAT_IMPORT = str.maketrans({
    "ø": "o", "Ø": "O", "å": "aa", "Å": "Aa", "æ": "ae", "Æ": "Ae",
    "ß": "ss", "ẞ": "SS", "þ": "th", "Þ": "Th", "ð": "d", "Ð": "D",
})


def pliega_letras(s: str) -> str:
    """Letras sin descomposición NFKD cambiadas por su equivalente ASCII, para COMPARAR.

    Los plegados de nombres (`match._fold` y los de la aplicación) normalizan con NFD y tiran lo que no es
    a-z0-9. Pero NFD no descompone `ø ł đ ı æ ß þ ð`, así que esas letras no se doblaban: se
    convertían en SEPARADOR y partían el nombre en trozos. Medido el 22-sep-2026:

        Brøndby     -> «br ndby»      (dos tokens)
        Bayındır    -> «bay nd r»     (tres)
        Bodø/Glimt  -> «bod glimt»    (se pierde la ø)
        Łódź        -> «odz»          (se pierde la Ł)
        København   -> «k benhavn»

    Con eso, un club nórdico, turco o polaco no casaba consigo mismo. Que el plegado de la aplicación llevara ya
    parches sueltos (ñ→ny, oe→o) era el síntoma: se iba tapando caso a caso."""
    return (s or "").translate(_XLAT).translate(_XLAT_IMPORT)


def de_fuera(s: str) -> str:
    """Texto que viene de una fuente externa, con las letras que el juego no usa ya cambiadas
    por las que él mismo usaba. Ver `_XLAT_IMPORT`."""
    return (s or "").translate(_XLAT_IMPORT)


def encode(text: str) -> bytes:
    """Texto -> bytes del fichero (latin-1).

    Los caracteres FUERA de latin-1 (checo ě, polaco ł, turco ş, croata č…) se
    TRANSLITERAN quitando diacríticos (ě→e, ş→s…). Antes se colaba el byte
    crudo (ord&0xFF), que produce un byte de CONTROL: el bloque deja de parsear
    y MANAGER.EXE lo rechaza — así perdimos al Banik Ostrava por la 'ě' de
    'Městský stadion' y descuadramos el fichero entero (localizado por bisección)."""
    try:
        raw = text.encode("latin-1")
    except UnicodeEncodeError:
        raw = _to_latin1(text).encode("latin-1", "replace")
    return bytes(b ^ XOR_KEY for b in raw)


def decode_lenprefixed(data: bytes, offset: int) -> tuple[str, int]:
    """Lee una cadena con prefijo de longitud [len:u8][00][bytes].

    Devuelve (texto, offset_siguiente)."""
    length = data[offset]
    # data[offset+1] es un 00 de relleno
    start = offset + 2
    end = start + length
    return decode(data[start:end]), end


def encode_lenprefixed(text: str) -> bytes:
    """Serializa una cadena como [len:u8][00][bytes]."""
    body = encode(text)
    if len(body) > 0xFF:
        raise ValueError("cadena demasiado larga para prefijo de 1 byte")
    return bytes([len(body), 0x00]) + body
