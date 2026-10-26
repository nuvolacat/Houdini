"""PCF 3.0 — aforo, socios y presupuesto del club (RE 2026-08-30).

Salieron de una idea: **comparar un filial con su club padre**. Barcelona B contra
Barcelona, Real Madrid B contra Real Madrid, Athletic B contra Athletic — y mirar qué comparten
que ningún otro par comparta.

El único campo idéntico en las tres parejas resultó ser un u32 de la cabecera. Tirando de ahí
aparecieron tres datos que estaban sin identificar, en los huecos de tamaño fijo:

    estadio → presidente (12 B):  [u32 puntero][u32 AFORO][u32 SOCIOS]
    presidente → patrocinador (4 B):  [u32 PRESUPUESTO]  (millones de pesetas)

**OJO con la conclusión fácil.** El presupuesto SÍ es idéntico en las tres parejas
(7.895 / 8.100 / 2.000), pero **eso no lo convierte en un marcador de filial**: también coincide
entre clubes sin ninguna relación (el Español tiene 2.000 igual que el Athletic; Sporting y Betis
1.200; Toledo y Badajoz 242). Y los **socios NO se comparten** —Madrid 67.000 frente a Madrid B
65.000, Athletic 30.000 frente a 31.000—; que el Barça y su filial tengan 100.000 los dos es
casualidad. Cada equipo tiene su propio aforo: Camp Nou 112.000, Miniestadi 16.500.
"""
import os

import pytest

from houdini_engine.formats.pcf3 import Pcf3DB

_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "gamedata", "FUTBOL3")


def _db(fn):
    p = os.path.join(_DIR, fn)
    if not os.path.exists(p):
        pytest.skip("sin gamedata/FUTBOL3")
    with open(p, "rb") as f:
        return Pcf3DB(f.read(), name=fn)


@pytest.fixture(scope="module")
def primera():
    return _db("LIG94951.DBC")


@pytest.fixture(scope="module")
def segunda():
    return _db("LIG94952.DBC")


def _eco(db, nombre):
    i = next(k for k, t in enumerate(db.teams) if t.name == nombre)
    return db.team_economy(i)


# --- que los números sean los de verdad ---

def test_el_aforo_es_el_de_cada_estadio(primera):
    """Contrastado con la realidad: si el campo estuviera mal leído, no cuadraría ninguno."""
    assert _eco(primera, "Barcelona")["aforo"] == 112000        # Camp Nou
    assert _eco(primera, "Real Madrid")["aforo"] == 107000      # Bernabéu
    assert _eco(primera, "Athletic")["aforo"] == 47000          # San Mamés
    assert _eco(primera, "Sevilla")["aforo"] == 61000           # Sánchez Pizjuán


def test_el_presupuesto_ordena_la_liga_como_tocaba(primera):
    e = lambda n: _eco(primera, n)["presupuesto"]
    assert e("Real Madrid") == 8100 and e("Barcelona") == 7895
    assert e("Barcelona") > e("Valencia") > e("Betis") > e("Compostela")
    assert e("Compostela") == 550


def test_los_de_segunda_manejan_mucho_menos(segunda):
    assert _eco(segunda, "Eibar")["presupuesto"] == 127
    assert _eco(segunda, "Villarreal")["presupuesto"] == 150
    for t in segunda.teams:
        eco = segunda.team_economy(segunda.teams.index(t))
        if eco.get("presupuesto") and t.name not in ("Real Madrid B", "Barcelona B", "Athletic B"):
            assert eco["presupuesto"] < 1000, t.name


def test_todos_los_clubes_traen_los_tres_datos(primera, segunda):
    """40 de 41: solo se queda fuera las Estrellas Mundiales, que no es un club. (El Rayo también
    faltaba, pero era un fallo NUESTRO: su nombre oficial tiene 32 caracteres y el lector
    descartaba todo lo que pasara de 30, así que perdía su ficha entera.)"""
    con = sin = 0
    for db in (primera, segunda):
        for i, t in enumerate(db.teams):
            eco = db.team_economy(i)
            if eco.get("aforo") and eco.get("presupuesto"):
                con += 1
                assert 1000 <= eco["aforo"] <= 130000, t.name
                assert eco["socios"] <= 150000, t.name
            else:
                sin += 1
    assert (con, sin) == (40, 1)


# --- el hallazgo: el filial comparte con su padre ---

def test_el_filial_lleva_el_presupuesto_de_su_padre(primera, segunda):
    for padre, hijo in (("Barcelona", "Barcelona B"), ("Real Madrid", "Real Madrid B"),
                        ("Athletic", "Athletic B")):
        p, h = _eco(primera, padre), _eco(segunda, hijo)
        assert p["presupuesto"] == h["presupuesto"], padre


def test_pero_los_SOCIOS_no_se_comparten(primera, segunda):
    """Lo di por hecho al ver que el Barça y su filial tienen 100.000 los dos, y era casualidad."""
    assert _eco(primera, "Real Madrid")["socios"] != _eco(segunda, "Real Madrid B")["socios"]
    assert _eco(primera, "Athletic")["socios"] != _eco(segunda, "Athletic B")["socios"]


def test_pero_el_filial_tiene_su_propio_estadio(primera, segunda):
    """El Barça juega en el Camp Nou y su filial en el Miniestadi."""
    assert _eco(primera, "Barcelona")["aforo"] == 112000
    assert _eco(segunda, "Barcelona B")["aforo"] == 16500


def test_el_presupuesto_NO_sirve_para_detectar_filiales(primera, segunda):
    """Coincide en las tres parejas, sí — pero también entre clubes que no tienen nada que ver, así
    que usarlo para deducir quién es filial de quién daría falsos positivos. Se deja fijado para
    que a nadie (yo el primero) se le ocurra."""
    from collections import Counter
    c = Counter()
    for db in (primera, segunda):
        for i in range(len(db.teams)):
            v = db.team_economy(i).get("presupuesto")
            if v:
                c[v] += 1
    repetidos = {v: n for v, n in c.items() if n > 1}
    assert 2000 in repetidos and repetidos[2000] == 3     # Athletic, Athletic B y Español
    assert len(repetidos) > 3, "hay más coincidencias que las tres parejas filial-padre"


# --- editar ---

def test_cambiarlos_no_mueve_nada(primera):
    """Son u32 de sitio fijo."""
    tam = len(primera.raw)
    plantillas = [len(t.players) for t in primera.teams]
    i = next(k for k, t in enumerate(primera.teams) if t.name == "Compostela")
    assert primera.set_team_economy(i, "aforo", 25000)
    assert primera.set_team_economy(i, "socios", 9000)
    assert primera.set_team_economy(i, "presupuesto", 1500)
    eco = primera.team_economy(i)
    assert (eco["aforo"], eco["socios"], eco["presupuesto"]) == (25000, 9000, 1500)
    assert len(primera.to_bytes()) == tam
    assert [len(t.players) for t in primera.teams] == plantillas


def test_un_equipo_sin_esos_datos_lo_dice(primera):
    e = len(primera.teams) - 1                       # Estrellas Mundiales
    assert primera.team_economy(e) == {}
    assert primera.set_team_economy(e, "aforo", 100) is False


def test_un_campo_inventado_se_rechaza(primera):
    i = next(k for k, t in enumerate(primera.teams) if t.name == "Barcelona")
    assert primera.set_team_economy(i, "loquesea", 5) is False


# --- año de fundación (mismo hueco, RE 2026-08-30) --------------------------------------------

def test_el_ano_de_fundacion_es_el_de_verdad(primera, segunda):
    """Los dos últimos bytes del hueco largo→estadio. Contrastado con la historia real."""
    esperado_1a = {"Palamós": None, "Athletic": 1898, "Barcelona": 1899, "Español": 1900,
                   "Real Madrid": 1902, "Atl. de Madrid": 1903, "Compostela": 1962}
    for club, anyo in esperado_1a.items():
        if anyo:
            assert _eco(primera, club)["fundacion"] == anyo, club
    assert _eco(segunda, "Palamós")["fundacion"] == 1898        # de los más viejos de España
    assert _eco(segunda, "Getafe")["fundacion"] == 1983
    assert _eco(segunda, "Osasuna")["fundacion"] == 1920


def test_el_filial_tiene_SU_ano_no_el_de_su_padre(primera, segunda):
    """Es lo que distingue este campo de la equipación, que sí la copia del padre."""
    assert _eco(primera, "Barcelona")["fundacion"] == 1899
    assert _eco(segunda, "Barcelona B")["fundacion"] == 1970
    assert _eco(primera, "Real Madrid")["fundacion"] == 1902
    assert _eco(segunda, "Real Madrid B")["fundacion"] == 1943


def test_todos_los_anos_son_creibles(primera, segunda):
    for db in (primera, segunda):
        for i, t in enumerate(db.teams):
            a = db.team_economy(i).get("fundacion")
            if a is not None:
                assert 1890 <= a <= 1994, f"{t.name}: {a}"


def test_editar_el_ano_no_mueve_nada(primera):
    i = next(k for k, t in enumerate(primera.teams) if t.name == "Betis")
    tam = len(primera.raw)
    assert primera.set_team_economy(i, "fundacion", 1907)
    assert primera.team_economy(i)["fundacion"] == 1907
    assert len(primera.to_bytes()) == tam
