"""Tests del parser de EQUIPOS.PKF contra ficheros reales.

Los ficheros del juego no se versionan; estos tests se saltan si no están en
`gamedata/`.
"""
from pathlib import Path

import pytest

from houdini_engine import refdata
from houdini_engine.formats import equipos_pkf as E

_MATERIAL = Path(__file__).resolve().parents[2] / "gamedata" / "material-v56"
_FILES = {
    "5.0": _MATERIAL / "PC Fútbol 5.0/DBDAT/EQUIPOS.PKF",
    "6.0": _MATERIAL / "PC Fútbol 6.0/Dbdat/EQ022022.PKF",
}
_available = [(v, p) for v, p in _FILES.items() if p.exists()]
skip_no_files = pytest.mark.skipif(not _available, reason="ficheros del juego no disponibles")


@skip_no_files
@pytest.mark.parametrize("ver,path", _available)
def test_roundtrip_byte_perfect(ver, path):
    data = path.read_bytes()
    pf = E.parse(data, path.name)
    assert E.serialize(pf) == data, f"round-trip no idéntico en {ver}"


@skip_no_files
@pytest.mark.parametrize("ver,path", _available)
def test_player_count_and_coherence(ver, path):
    from collections import Counter

    pf = E.parse(path.read_bytes(), path.name)
    assert len(pf.players) > 3000, f"muy pocos jugadores en {ver}: {len(pf.players)}"
    # España debe ser el país más frecuente
    top = Counter(p.country for p in pf.players).most_common(1)[0][0]
    esp = next(c["pointer"] for c in refdata.countries() if c["name"] == "España")
    assert top == esp, "España debería ser el país más frecuente"


@skip_no_files
def test_teams_v5_headers():
    path = _FILES["5.0"]
    if not path.exists():
        pytest.skip("5.0 no disponible")
    pf = E.parse(path.read_bytes(), path.name)
    assert len(pf.teams) >= 150, f"pocos equipos: {len(pf.teams)}"
    by_name = {t.short_name: t for t in pf.teams}
    rma = by_name.get("Real Madrid")
    fcb = by_name.get("Barcelona")
    assert rma and rma.founded == 1902 and rma.capacity > 90000
    assert fcb and fcb.founded == 1899
    # los equipos con cabecera completa tienen año coherente
    assert all(1850 <= t.founded <= 1998 for t in pf.teams if t.complete)
    # jugadores asignados a equipos
    assert sum(len(t.players) for t in pf.teams) > 3000


@skip_no_files
@pytest.mark.parametrize("ver,path", _available)
def test_team_coverage_and_assignment(ver, path):
    pf = E.parse(path.read_bytes(), path.name)
    # todos los jugadores quedan asignados a un equipo
    assigned = sum(len(t.players) for t in pf.teams)
    assert assigned == len(pf.players), f"{ver}: {len(pf.players) - assigned} jugadores sin equipo"
    # cada equipo queda clasificado como nacional (completo) o extranjero (foráneo)
    assert all(t.complete or t.foreign for t in pf.teams)
    # hay equipos nacionales con detalle financiero
    assert sum(1 for t in pf.teams if t.complete) >= 100
    # todos con nombre y país válidos
    assert all(t.short_name and 0 <= t.country <= 210 for t in pf.teams)


@skip_no_files
def test_team_edit_roundtrip():
    path = _FILES["5.0"]
    if not path.exists():
        pytest.skip("5.0 no disponible")
    data = path.read_bytes()
    pf = E.parse(data, path.name)
    t = next(t for t in pf.teams if t.complete)
    ob, oc = t.budget_game, t.capacity
    E.set_team_field(pf, t, "budget_game", 4321)
    E.set_team_field(pf, t, "capacity", 12345)
    assert E.serialize(pf) != data
    E.set_team_field(pf, t, "budget_game", ob)
    E.set_team_field(pf, t, "capacity", oc)
    assert E.serialize(pf) == data


@skip_no_files
@pytest.mark.parametrize("ver,path", _available)
def test_player_ratings(ver, path):
    pf = E.parse(path.read_bytes(), path.name)
    con = sum(1 for p in pf.players if p.ratings)
    assert con >= len(pf.players) * 0.95, f"pocas medias en {ver}: {con}/{len(pf.players)}"
    # todas las medias en rango 0..99
    assert all(all(0 <= v <= 99 for v in p.ratings) for p in pf.players if p.ratings)
    # etiquetas correctas por versión
    labels = E.rating_labels(pf.version)
    assert labels[-1] == "PO"
    assert (labels[4], labels[5]) == (("RM", "RG") if ver == "6.0" else ("RG", "RM"))


@skip_no_files
def test_rating_edit_roundtrip():
    path = _FILES["5.0"]
    if not path.exists():
        pytest.skip("5.0 no disponible")
    data = path.read_bytes()
    pf = E.parse(data, path.name)
    p = next(p for p in pf.players if p.ratings)
    orig = p.ratings[3]
    E.set_rating(pf, p, "CA", 99)
    assert sum(a != b for a, b in zip(data, E.serialize(pf))) == 1
    E.set_rating(pf, p, "CA", orig)
    assert E.serialize(pf) == data


@skip_no_files
@pytest.mark.parametrize("ver,path", _available)
def test_foreign_teams(ver, path):
    pf = E.parse(path.read_bytes(), path.name)
    foreign = [t for t in pf.teams if t.foreign]
    assert foreign, f"{ver}: no se detectaron equipos foráneos"
    # todos con aforo plausible y la mayoría con entrenador
    assert all(0 <= t.capacity < 500000 for t in foreign)
    with_coach = sum(1 for t in foreign if t.coach_short)
    assert with_coach >= len(foreign) * 0.8


@skip_no_files
def test_text_edit_length_preserving():
    path = _FILES["5.0"]
    if not path.exists():
        pytest.skip("5.0 no disponible")
    data = path.read_bytes()
    pf = E.parse(data, path.name)
    t = next(x for x in pf.teams if x.complete and x.stadium)
    n = len(data)
    slot = E.team_text_limits(t, pf.raw)["stadium"]
    # nombre más corto: se acepta y no cambia la longitud del fichero
    E.set_team_text(pf, t, "stadium", "X")
    assert len(E.serialize(pf)) == n
    # demasiado largo: se rechaza
    with pytest.raises(E.TextTooLong):
        E.set_team_text(pf, t, "stadium", "Y" * (slot + 1))
    # el hueco (len byte) se conserva
    assert pf.raw[t._off["stadium"]] == slot


@skip_no_files
def test_inplace_edit_single_byte():
    path = _FILES["5.0"]
    if not path.exists():
        pytest.skip("5.0 no disponible")
    data = path.read_bytes()
    pf = E.parse(data, path.name)
    p = pf.players[0]
    orig = p.height
    E.set_block_field(pf, p, "height", 199)
    mod = E.serialize(pf)
    assert sum(a != b for a, b in zip(data, mod)) == 1
    E.set_block_field(pf, p, "height", orig)
    assert E.serialize(pf) == data


@skip_no_files
def test_stats_coach_dbtexts_tactic():
    """Campos profundos: historial, textos de entrenador, BBDD de jugador, táctica base."""
    path = _FILES.get("5.0")
    if not path or not path.exists():
        pytest.skip("5.0 no disponible")
    data = path.read_bytes()
    pf = E.parse(data, path.name)
    t = next(x for x in pf.teams if x.short_name == "Real Madrid")
    st = E.team_stats(pf, t)
    assert st["campeon"] == 26 and st["temporadas1a"] == 65 and st["pj"] == 1960
    assert len(st["ligas"]) == 10 and st["ligas"][0]["pos"] == 1
    ct = E.coach_texts(pf, t)
    assert "Capello" in ct["coach_perfil"]
    raul = next(p for p in t.players if "Raúl" in p.short_name)
    db = E.player_db_texts(pf, raul)
    assert db["lugar_nacimiento"][0] == "Madrid" and db["birth_country"] == 22
    # edición conservando longitud
    E.set_team_field(pf, t, "campeon", 30)
    E.set_tactic_preset(pf, t, "4-4-2")
    E.set_player_text(pf, raul, "club_debut", "x")
    out = E.serialize(pf)
    assert len(out) == len(data)
    pf2 = E.parse(out, path.name)
    t2 = next(x for x in pf2.teams if x.short_name == "Real Madrid")
    assert E.team_stats(pf2, t2)["campeon"] == 30
    assert E.get_tactic_name(pf2, t2) == "4-4-2"


# --- palmarés: las 7 competiciones, ancladas a la historia real -----------------
# Las etiquetas estuvieron MAL en 5 de los 14 bytes hasta 2026-08-20 y nadie lo notó
# porque los valores seguían siendo plausibles. Este test las ata a hechos que no
# cambian: los títulos europeos y de Copa de los clubes españoles a la altura de 1997.
_GAMEDATA = Path(__file__).resolve().parents[2] / "gamedata"
_PKF6 = _GAMEDATA / "pcf6oro" / "EQ022022.PKF"

# club → (uefa_titulos, copa_titulos, ce_titulos, recopa_titulos, supercopa_esp_titulos)
_PALMARES_REAL = {
    "F.C. Barcelona":   (None, 23, 1, 4, 5),   # la UEFA del Barça varía 3/4 entre copias
    "Real Madrid C.F.": (2,    17, 6, 0, 3),
    "Athletic Club":    (0,    23, 0, 0, None),
    "C. At. Madrid":    (0,     9, 0, 1, 1),
    "Valencia C.F.":    (2,     5, 0, 1, None),
    "R. Zaragoza":      (1,     4, 0, 1, None),
    "Sevilla F.C.":     (0,     3, 0, 0, None),
    "R.C. Deportivo":   (0,     1, 0, 0, 1),
}


@pytest.mark.skipif(not _PKF6.exists(), reason="gamedata/pcf6oro no disponible")
def test_palmares_cuadra_con_la_historia():
    pf = E.parse(_PKF6.read_bytes(), _PKF6.name)
    vistos = 0
    for t in pf.teams:
        esperado = _PALMARES_REAL.get((t.short_name or "").strip())
        if esperado is None:
            continue
        s = E.team_stats(pf, t)
        if not s or "palmares" not in s:
            continue
        vistos += 1
        p = s["palmares"]
        for clave, valor in zip(("uefa_titulos", "copa_titulos", "ce_titulos",
                                 "recopa_titulos", "supercopa_esp_titulos"), esperado):
            if valor is not None:
                assert p[clave] == valor, f"{t.short_name}: {clave} = {p[clave]}, esperado {valor}"
    assert vistos >= 6, f"solo se comprobaron {vistos} clubes"


@pytest.mark.skipif(not _PKF6.exists(), reason="gamedata/pcf6oro no disponible")
def test_palmares_solo_lo_ganan_los_que_lo_ganaron():
    """Cada byte de TÍTULOS lo tienen muy pocos clubes, y son los de verdad.

    (No se comprueba `participaciones >= títulos`, que parecería lo natural: Dinamic
    dejó las participaciones a cero en casi todos los clubes —solo las rellenó en 29—,
    así que el Depor figura con 1 Copa y 0 participaciones. Es su dato, no un fallo
    nuestro.)"""
    pf = E.parse(_PKF6.read_bytes(), _PKF6.name)
    campeones = {"ce_titulos": set(), "recopa_titulos": set(), "supercopa_esp_titulos": set()}
    for t in pf.teams:
        s = E.team_stats(pf, t)
        if not s or "palmares" not in s:
            continue
        for k in campeones:
            if s["palmares"][k]:
                campeones[k].add((t.short_name or "").strip())
    # la Copa de Europa la habían ganado 2 españoles en 1997: Madrid y Barça
    assert {"Real Madrid C.F.", "F.C. Barcelona"} <= campeones["ce_titulos"]
    assert "Sevilla F.C." not in campeones["ce_titulos"]
    # la Supercopa de España es SOLO española: nadie de fuera puede tenerla
    assert "Milan" not in campeones["supercopa_esp_titulos"]
    assert len(campeones["supercopa_esp_titulos"]) <= 12
