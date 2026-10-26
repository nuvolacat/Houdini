"""Nombres de competición de PCF 4.0 (PCMANAG.DAT / PROMANAG.DAT).

PCF4 no tiene `manager.exe`: los nombres de las competiciones viven como TEXTO PLANO
dentro de los dos ficheros de datos del manager. Se editan por reemplazo IN-PLACE
conservando la longitud (relleno con espacios), igual que el manager.exe de v5/6.
Un mismo nombre aparece varias veces → se reemplazan TODAS las apariciones.

Cada competición tiene una o dos VARIANTES en el fichero: la de los ROTULOS de pantalla
(que Dinamic escribió en mayúsculas, por estilo — el formato NO lo exige: es texto plano
y el juego lo imprime tal cual) y la de los TEXTOS corridos: p.ej. "COPA DEL REY" +
"Copa del Rey". Se exponen agrupadas por competición (key) con un campo por variante
(field), igual que el editor de v5/6 — así no se puede cambiar una y olvidar la otra.

Cuidado con las SUBCADENAS ("COPA DE EUROPA" ⊂ "RECOPA DE EUROPA"): se procesan los
nombres LARGOS primero y se marcan los rangos ya consumidos.
"""
from __future__ import annotations

FILES = ["PCMANAG.DAT", "PROMANAG.DAT"]

# (key, etiqueta, [(field, etiqueta de variante, cadena original en el fichero)])
# El editor reemplaza cada variante en su MISMA longitud.
COMPETITIONS: list[tuple[str, str, list[tuple[str, str, str]]]] = [
    ("primera", "Primera División", [
        ("upper", "Rótulo de pantalla", "PRIMERA DIVISION")]),
    ("segunda", "Segunda División", [
        ("upper", "Rótulo de pantalla", "SEGUNDA DIVISION")]),
    ("copa", "Copa del Rey", [
        ("upper", "Rótulo de pantalla", "COPA DEL REY"),
        ("name", "En textos", "Copa del Rey")]),
    ("europa", "Copa de Europa", [
        ("upper", "Rótulo de pantalla", "COPA DE EUROPA"),
        ("name", "En textos", "Copa de Europa")]),
    ("uefa", "Copa de la UEFA", [
        ("upper", "Rótulo de pantalla", "COPA DE LA UEFA"),
        ("name", "En textos", "Copa de la UEFA")]),
    ("recopa", "Recopa de Europa", [
        ("upper", "Rótulo de pantalla", "RECOPA DE EUROPA"),
        ("name", "En textos", "Recopa")]),
]

# "key/field" → (etiqueta de competición, etiqueta de variante, cadena original)
_BY_KF: dict[str, tuple[str, str, str]] = {
    f"{key}/{field}": (lab, vlab, orig)
    for key, lab, variants in COMPETITIONS
    for field, vlab, orig in variants
}


def _occurrences(data: bytes) -> dict[str, list[int]]:
    """Offsets de cada variante ("key/field" → offsets), procesando las cadenas LARGAS
    primero y marcando rangos consumidos (si no, "COPA DE EUROPA" se comería el final de
    "RECOPA DE EUROPA")."""
    consumed: list[tuple[int, int]] = []
    out: dict[str, list[int]] = {}
    items = sorted(_BY_KF.items(), key=lambda kv: -len(kv[1][2]))
    for kf, (_lab, _vlab, orig) in items:
        ob = orig.encode("latin-1")
        offs: list[int] = []
        start = 0
        while True:
            i = data.find(ob, start)
            if i < 0:
                break
            if any(a <= i < b for a, b in consumed):
                start = i + 1
                continue
            consumed.append((i, i + len(ob)))
            offs.append(i)
            start = i + len(ob)
        if offs:
            out[kf] = offs
    return out


def present_keys(data: bytes) -> set[str]:
    """Variantes ("key/field") presentes en este fichero."""
    return set(_occurrences(data).keys())


def patch_file(data: bytes, edits: dict[str, str]) -> bytes:
    """Aplica los nuevos nombres ("key/field" → nombre) a un fichero, en su misma longitud."""
    out = bytearray(data)
    for kf, offs in _occurrences(data).items():
        new = edits.get(kf)
        if new is None:
            continue
        _lab, _vlab, orig = _BY_KF[kf]
        L = len(orig)
        repl = new.encode("latin-1", "replace")[:L].ljust(L, b" ")
        for i in offs:
            out[i:i + L] = repl
    return bytes(out)


def fields(present: set[str], edits: dict[str, str]) -> list[dict]:
    """Campos editables con la MISMA forma que el editor de competiciones de v5/6:
    agrupados por competición (key), un campo por variante (field)."""
    out = []
    for key, lab, variants in COMPETITIONS:
        for field, vlab, orig in variants:
            kf = f"{key}/{field}"
            if kf not in present:
                continue
            out.append({
                "key": key, "field": field, "label": lab, "field_label": vlab,
                "value": edits.get(kf, orig), "original": orig, "max_len": len(orig),
            })
    return out
