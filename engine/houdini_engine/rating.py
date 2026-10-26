"""Ajuste de la MEDIA objetivo de un jugador / un equipo (mejora global, todas las ediciones).

La media mostrada de un jugador es, en TODAS las ediciones, el promedio de sus 4 primeras
medias: (VE + RE + AG + CA) / 4. Estas funciones son PURAS (operan sobre listas de enteros);
cada edición aporta el adaptador que lee/escribe esas 4 medias del jugador.

Reglas:
- Jugador → media objetivo M: se reparte el cambio entre las 4 stats lo más EQUILIBRADO
  posible (al subir se da primero a la más baja; al bajar, a la más alta), respetando [floor,
  cap]. Si es alcanzable, el promedio queda EXACTO en M.
- Equipo → media objetivo T: se reparte el cambio de media entre los jugadores con PRIORIDAD
  a los que ya tienen más media (los buenos suben más; un jugador de 55 sube poco, "sin
  pasarse", no salta a 80). Solo cuando los de arriba topan en el máximo, el sobrante baja a
  los que aún tienen margen, para que el promedio del equipo llegue justo a T. Nadie conserva
  las mismas stats: cada jugador se adapta.
"""
from __future__ import annotations

CORE = 4  # nº de medias que forman la media mostrada (VE, RE, AG, CA)

# cuánto se concentra la subida/bajada de equipo en los jugadores de más media (0 = uniforme,
# todos el mismo cambio; 1 = proporcional a la media; >1 = fuerte prioridad a los buenos).
# 0.5 = prioridad LEVE: los de más media suben algo más, pero el reparto es bastante parejo.
TEAM_SKEW = 0.5


def media_of(core4: list[int]) -> int:
    """Media mostrada a partir de las 4 primeras medias (redondeo como el juego)."""
    if not core4:
        return 0
    return round(sum(core4[:CORE]) / min(CORE, len(core4)))


def _distribute(vals: list[int], delta: int, floor: int, cap: int) -> tuple[list[int], int]:
    """Reparte `delta` puntos (±) entre `vals` de UNO EN UNO, lo más uniforme posible,
    respetando [floor, cap]. Al subir alimenta primero al valor más bajo; al bajar, al más
    alto → mantiene el conjunto equilibrado. Devuelve (nuevos_valores, puntos_no_repartidos)."""
    out = list(vals)
    if delta == 0 or not out:
        return out, delta
    step = 1 if delta > 0 else -1
    remaining = abs(delta)
    while remaining > 0:
        # orden de reparto: subir→menor primero; bajar→mayor primero
        order = sorted(range(len(out)), key=lambda i: out[i], reverse=(step < 0))
        moved = False
        for i in order:
            if remaining == 0:
                break
            nv = out[i] + step
            if floor <= nv <= cap:
                out[i] = nv
                remaining -= 1
                moved = True
        if not moved:              # nadie tiene ya margen en esa dirección
            break
    return out, step * remaining   # lo que no se pudo repartir (con signo)


def stats_for_target(core4: list[int], target: int,
                     floor: int = 1, cap: int = 99) -> list[int]:
    """Nuevas 4 stats cuyo promedio redondeado = `target` (si es alcanzable), partiendo de
    `core4` y repartiendo el cambio equilibradamente dentro de [floor, cap]."""
    cur = [max(floor, min(cap, int(v))) for v in core4[:CORE]]
    if len(cur) < CORE:                       # por si viniera incompleto
        cur += [floor] * (CORE - len(cur))
    target = max(floor, min(cap, int(target)))
    delta = target * CORE - sum(cur)          # puntos totales a mover para media exacta
    new, _ = _distribute(cur, delta, floor, cap)
    return new


def _distribute_weighted(vals: list[int], delta: int, weights: list[float],
                         floor: int, cap: int) -> tuple[list[int], int]:
    """Reparte `delta` puntos (±) de UNO EN UNO con PRIORIDAD a mayor peso (round-robin
    ponderado tipo D'Hondt), solo a quien tenga margen en [floor, cap]. Al topar los de más
    peso, el resto va bajando a los siguientes. Devuelve (nuevos, puntos_no_repartidos)."""
    out = list(vals)
    if delta == 0 or not out:
        return out, delta
    step = 1 if delta > 0 else -1
    remaining = abs(delta)
    w = [max(1e-6, float(x)) for x in weights]
    acc = [0.0] * len(out)                     # acumulador de cuota (D'Hondt en streaming)
    while remaining > 0:
        cand = [i for i in range(len(out)) if floor <= out[i] + step <= cap]
        if not cand:
            break
        for i in cand:
            acc[i] += w[i]
        i = max(cand, key=lambda k: (acc[k], w[k]))   # el de mayor cuota acumulada
        out[i] += step
        remaining -= 1
        acc[i] -= sum(w[k] for k in cand)     # "paga" su punto
    return out, step * remaining


def team_player_targets(medias: list[int], target_team: int,
                        floor: int = 1, cap: int = 99) -> list[int]:
    """Nueva media OBJETIVO de cada jugador para que el promedio del equipo = `target_team`,
    repartiendo el cambio con PRIORIDAD a los de más media (los buenos suben/bajan más; los
    flojos se mueven poco). El sobrante, si los de arriba topan, baja a los que tengan margen.
    `medias` = medias actuales por jugador."""
    n = len(medias)
    if n == 0:
        return []
    cur = [max(floor, min(cap, int(m))) for m in medias]
    target_team = max(floor, min(cap, int(target_team)))
    want_sum = round(target_team * n)          # suma de medias que da el promedio objetivo
    delta = want_sum - sum(cur)                # puntos de media a repartir (±)
    # peso = media^SKEW → prioridad a los que ya tienen más media
    weights = [max(floor, m) ** TEAM_SKEW for m in cur]
    new, _ = _distribute_weighted(cur, delta, weights, floor, cap)
    return new


# ---- arrastrar los atributos SECUNDARIOS al fijar la media (foro, 2026-08-30) ----------
#
# La media ES (VE+RE+AG+CA)/4, así que solo esas cuatro tienen que moverse para alcanzarla. El
# resto —regate, remate, pase, tiro, entradas y portero— se quedaba como estaba, y eso deja
# incoherencias: un portero con media 90 y su atributo de portero en 20.
#
# Aquí van los PESOS con los que cada atributo secundario sigue al cambio de media, según el
# PUESTO. Un peso de 1 sube lo mismo que la media; 0,2 sube una quinta parte. No es una
# simulación: es un reparto sensato y, sobre todo, PREDECIBLE.
PERFILES = {
    0: {"PO": 1.0, "EN": 0.2, "PA": 0.2, "TI": 0.2, "RM": 0.2, "RG": 0.2},   # portero
    1: {"EN": 1.0, "PA": 0.5, "RG": 0.3, "TI": 0.3, "RM": 0.3, "PO": 0.0},   # defensa
    2: {"PA": 1.0, "RG": 0.9, "EN": 0.5, "TI": 0.5, "RM": 0.4, "PO": 0.0},   # medio
    3: {"RM": 1.0, "TI": 0.9, "RG": 0.6, "PA": 0.4, "EN": 0.2, "PO": 0.0},   # delantero
}

# Cada edición llama a los atributos a su manera; se traducen a las claves de arriba.
# SOLO nombres que existen de verdad: v5/6 usa las siglas tal cual (RG, RM, PA…) y FDI las
# palabras en minúscula. Había además una fila de siglas de tres letras (REG, REM, PAS…) que no
# corresponde a ninguna edición y que sí colisionaba con una real: en PCF4, **REG es la
# RESISTENCIA**, no el regate, así que "ajustar también el resto" le reescribía una de las cuatro
# medias que acababa de fijar y rompía el objetivo. PCF4 y PCF3 no tienen atributos secundarios.
_ALIAS = {
    "regate": "RG", "remate": "RM", "pase": "PA", "tiro": "TI",
    "entradas": "EN", "portero": "PO",
}


def secundarias_por_media(ratings: dict, delta: int, ptype: int) -> dict:
    """Cuánto cambia cada atributo SECUNDARIO al mover la media `delta` puntos.

    `ratings` = {etiqueta: valor} tal y como los llama su edición. Devuelve solo los que cambian,
    con las MISMAS etiquetas que entraron. Los que no están en el perfil (penaltis, córners,
    faltas…) no se tocan: no dependen de lo bueno que sea el jugador.
    """
    if not delta:
        return {}
    perfil = PERFILES.get(int(ptype), PERFILES[2])
    out: dict = {}
    for etq, val in (ratings or {}).items():
        clave = _ALIAS.get(etq, etq if etq in ("RG", "RM", "PA", "TI", "EN", "PO") else None)
        peso = perfil.get(clave) if clave else None
        if not peso:
            continue
        nuevo = max(1, min(99, int(round(int(val) + delta * peso))))
        if nuevo != int(val):
            out[etq] = nuevo
    return out
