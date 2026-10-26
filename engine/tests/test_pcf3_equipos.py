"""PCF 3.0: detectar los equipos de verdad (RE 2026-08-29).

No hay documentación de este formato —somos los primeros— y la regla vieja («un equipo empieza
en el nombre largo, que lleva `\\`») se equivocaba de dos maneras distintas:

  · Perdía al **LLEIDA**, cuyo nombre largo es 'U.E. LLEIDA', sin barra. Sus 21 jugadores se le
    pegaban al Rayo, que salía con 44, y 2ª se quedaba en 19 equipos de 20.
  · No veía a las **ESTRELLAS MUNDIALES** (los 20 astros del 94-95), que no tienen cabecera de
    club, así que acababan dentro del Compostela: 42 jugadores.

Ahora se camina la estructura: un JUGADOR son dos textos pegados seguidos de 13 bytes que
encajan, y una CABECERA DE EQUIPO es una pareja pegada que NO es un jugador. Lo que este fichero
vigila es justo eso: que no se vuelva a inflar ninguna plantilla y que el fichero siga saliendo
byte a byte igual que entró.
"""
import os

import pytest

from houdini_engine.formats.pcf3 import Pcf3DB

_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "gamedata", "FUTBOL3")


def _db(fn: str) -> Pcf3DB:
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


# --- el recuento ---

def test_la_cabecera_declara_veinte_equipos_por_division(primera, segunda):
    """El u16 que va tras la firma dice cuántos hay. Es la única comprobación que trae el propio
    fichero, así que conviene no perderla de vista."""
    assert primera.declared_teams() == 20
    assert segunda.declared_teams() == 20


def test_segunda_tiene_los_veinte_equipos_reales(segunda):
    nombres = [t.name for t in segunda.teams]
    assert len(nombres) == 20
    assert "Lleida" in nombres, "el Lleida se perdía por no llevar `\\` en el nombre largo"
    assert nombres[0] == "Rayo"


def test_primera_son_los_veinte_mas_las_estrellas(primera):
    nombres = [t.name for t in primera.teams]
    assert len(nombres) == 21
    assert nombres[-1] == "Estrellas Mundiales"
    for club in ("Barcelona", "Real Madrid", "Atl. de Madrid", "Compostela"):
        assert club in nombres


# --- las plantillas, que era donde se notaba ---

def test_ninguna_plantilla_se_infla(primera, segunda):
    """Los descuadres viejos: Compostela 42, Rayo 44, Logroñés 35, Valladolid 34, Sporting 31.
    Un equipo del 94-95 no pasa de la treintena larga."""
    for db in (primera, segunda):
        for t in db.teams:
            assert 10 <= len(t.players) <= 35, f"{t.name} con {len(t.players)} jugadores"


def test_el_rayo_y_el_compostela_ya_no_cargan_con_los_del_vecino(primera, segunda):
    rayo = next(t for t in segunda.teams if t.name == "Rayo")
    compos = next(t for t in primera.teams if t.name == "Compostela")
    assert len(rayo.players) == 22          # antes 44: llevaba dentro al Lleida
    assert len(compos.players) == 26        # antes 42: llevaba dentro a las Estrellas


def test_las_estrellas_son_las_estrellas(primera):
    e = primera.teams[-1]
    apodos = [p[0].text for p in e.players]
    assert len(apodos) == 20
    for astro in ("Batistuta", "Baggio", "Bergkamp", "Baresi"):
        assert astro in apodos


# --- lo que la cabecera nos da de regalo ---

def test_cada_club_trae_su_estadio_y_su_entrenador(primera, segunda):
    """Las Estrellas no son un club y no tienen ni uno ni otro; los 40 clubes, sí."""
    for db in (primera, segunda):
        for t in db.teams:
            if t.name == "Estrellas Mundiales":
                assert not t.coach
                continue
            assert t.coach, f"{t.name} sin entrenador"
            assert any(f.kind == "estadio" for f in t.fields), f"{t.name} sin estadio"


def test_los_entrenadores_son_los_del_94_95(primera, segunda):
    esperado = {"Barcelona": "Cruyff", "Real Madrid": "Valdano", "Athletic": "Irureta",
                "Sevilla": "Luis", "Español": "Camacho", "Rayo": "David Vidal",
                "Lleida": "Mané", "Real Madrid B": "Benítez"}
    dado = {t.name: (t.coach[0].text if t.coach else "")
            for db in (primera, segunda) for t in db.teams}
    for club, entrenador in esperado.items():
        assert dado.get(club) == entrenador, f"{club}: {dado.get(club)!r}"


def test_teka_es_el_patrocinador_no_el_entrenador(primera):
    """Se coló una vez porque la cabecera lo tenía justo donde se buscaba al técnico."""
    madrid = next(t for t in primera.teams if t.name == "Real Madrid")
    assert next(f.text for f in madrid.fields if f.kind == "patrocinador") == "TEKA"
    assert madrid.coach[0].text == "Valdano"


# --- la regla de oro ---

def test_el_fichero_sale_byte_a_byte_igual(primera, segunda):
    for db in (primera, segunda):
        with open(os.path.join(_DIR, db.name), "rb") as f:
            assert bytes(db.to_bytes()) == f.read(), f"round-trip roto en {db.name}"


def test_escribir_dos_campos_seguidos_del_mismo_jugador(primera):
    """Regresión (2026-08-30): la importación desde la caché se rompía al segundo campo.

    Desde que los nombres pueden pasarse del hueco original, `set_field` RECOMPONE el fichero y
    lo vuelve a escanear. Eso deja OBSOLETO cualquier `Field` cogido antes: su offset ya no
    existe. El import tenía apodo y nombre largo en la mano y escribía los dos del tirón, así que
    el segundo moría con «campo no encontrado» y no se actualizaba ni un equipo. La regla es
    pedir el campo POR ÍNDICE justo antes de cada escritura.
    """
    apodo_viejo, largo_viejo = primera.teams[0].players[0][:2]   # cogidos ANTES, como hacía el import
    antes = len(primera.raw)
    primera.set_field(apodo_viejo.off, "Abc")
    assert len(primera.raw) != antes                   # se ha recompuesto de verdad

    with pytest.raises(ValueError, match="campo no encontrado"):
        primera.set_field(largo_viejo.off, "Nombre Largo De Prueba")   # el offset ya no existe

    largo = primera.teams[0].players[0][1]             # pedido DE NUEVO: ahora sí
    primera.set_field(largo.off, "Nombre Largo De Prueba")
    assert primera.teams[0].players[0][0].text == "Abc"
    assert primera.teams[0].players[0][1].text == "Nombre Largo De Prueba"


def test_un_nombre_que_empieza_por_acento_no_pierde_al_jugador(segunda):
    """Regresión (2026-08-30): «Álvaro Cortés» hacía DESAPARECER la ficha.

    En la base original hay 716 campos con acentos dentro y NI UNO que empiece por acento: el
    escaneo se apoya en esa convención para localizar los campos. Al importar desde la caché se
    escribían nombres como «Álvaro» y ese campo dejaba de reconocerse, así que el equipo perdía
    un jugador y el anclaje de las medias se descuadraba («bloque de medias no encontrado»).
    Ahora se escribe la inicial sin acento, como lo escribiría el juego.
    """
    antes = len(segunda.teams[0].players)
    campo = segunda.teams[0].players[0][1]
    segunda.set_field(campo.off, "Álvaro Cortés")
    assert len(segunda.teams[0].players) == antes            # no se pierde la ficha
    assert segunda.teams[0].players[0][1].text == "Alvaro Cortés"   # acento solo en la inicial


def test_equipacion_del_simulador(primera, segunda):
    """RE 2026-08-30: los 10 bytes entre `marca` y `clave` son la equipación del simulador 2D.

    Un byte de patrón y tres colores VGA de 6 bits. Se contrasta con las equipaciones REALES del
    94-95, que es lo que demuestra que la lectura es la buena y no una interpretación que cuadra
    consigo misma.
    """
    AZUL, ROJO, BLANCO, NEGRO, VERDE = [0, 0, 63], [63, 0, 0], [63, 63, 63], [0, 0, 0], [0, 63, 0]

    def kit(db, nombre):
        i = next(k for k, t in enumerate(db.teams) if t.name == nombre)
        return db.team_kit(i)

    assert kit(primera, "Barcelona")["colores"] == [AZUL, AZUL, ROJO]        # blaugrana
    assert kit(primera, "Real Madrid")["colores"] == [BLANCO] * 3            # todo blanco
    assert kit(primera, "Athletic")["colores"] == [NEGRO, ROJO, BLANCO]      # pantalón negro
    assert kit(primera, "Betis")["colores"] == [BLANCO, BLANCO, VERDE]       # verdiblanco
    # Valladolid es VIOLETA: no es un color puro, así que esto no es una tabla de colores fijos
    assert kit(primera, "Valladolid")["colores"][2] == [45, 24, 39]
    # el patrón: 0 en casi todos, 1 en el Rayo (su banda diagonal)
    assert kit(primera, "Barcelona")["patron"] == 0
    assert kit(segunda, "Rayo")["patron"] == 1


def test_editar_la_equipacion_no_mueve_el_fichero(primera):
    antes = len(primera.raw)
    primera.set_team_kit(0, 2, [[63, 63, 0], [0, 0, 0], [10, 20, 30]])
    assert len(primera.raw) == antes
    assert primera.team_kit(0) == {"patron": 2, "colores": [[63, 63, 0], [0, 0, 0], [10, 20, 30]]}
    with pytest.raises(ValueError):
        primera.set_team_kit(0, 0, [[64, 0, 0], [0, 0, 0], [0, 0, 0]])   # 63 es el máximo VGA


def test_el_escudo_grande_es_el_del_equipo_en_LAS_DOS_divisiones(primera, segunda):
    """Regresión (2026-08-30): en 2ª la ficha del Rayo enseñaba el escudo del Lleida.

    Las dos divisiones NO guardan los gráficos en el mismo orden:

        1ª:  [escudo 48×64] [escudo grande] [equipación] [estadio]
        2ª:  [escudo grande] [escudo 48×64] [equipación]

    Tomar el bloque «del escudo pequeño al siguiente escudo pequeño» vale en 1ª pero en 2ª deja el
    escudo grande de cada equipo dentro del bloque del ANTERIOR, así que salían todos corridos uno.
    """
    import os as _os

    from houdini_engine.formats import pcf3_dgf as DGF
    for db, dgf, n in ((primera, "LIG94951.DGF", 4), (segunda, "LIG94952.DGF", 4)):
        p = _os.path.join(_DIR, dgf)
        if not _os.path.exists(p):
            pytest.skip("sin gamedata/FUTBOL3")
        with open(p, "rb") as f:
            data = f.read()
        offs = [im["off"] for im in DGF.images(data) if (im["w"], im["h"]) == (48, 64)]
        vistos = []
        for i in range(n):
            off = db.team_escudo_offset(i, offs)
            g = DGF.team_graphics_at(data, off)
            assert g and g["escbig"], f"{dgf} equipo {i} sin escudo grande"
            # el grande tiene que ser el PEGADO a su escudo pequeño, no el del vecino
            assert abs(g["escbig"]["off"] - off) < 40000
            vistos.append(g["escbig"]["off"])
        assert len(set(vistos)) == n, f"{dgf}: dos equipos comparten escudo grande"


def test_el_once_inicial_son_los_dorsales_1_11(primera, segunda):
    """RE 2026-08-30: el once NO es «los once primeros de la plantilla».

    La plantilla está ORDENADA POR PUESTO (porteros, defensas, medios, delanteros), así que
    tomar los once primeros da un once con DOS porteros en la mayoría de los equipos. El once de
    verdad va en el DORSAL: es la convención de 1994 —los números no eran fijos por jugador y del
    1 al 11 jugaban los titulares— y el fichero la respeta.
    """
    equipos, once_exacto, dos_porteros = 0, 0, 0
    for db in (primera, segunda):
        for i, t in enumerate(db.teams):
            infos = [db.player_info(i, k) for k in range(len(t.players))]
            infos = [x for x in infos if x]
            if len(infos) < 11:
                continue
            equipos += 1
            if sum(1 for x in infos if x["dorsal"] and 1 <= x["dorsal"] <= 11) == 11:
                once_exacto += 1
            if sum(1 for x in infos[:11] if x["demarcacion"] == 0) >= 2:
                dos_porteros += 1
    # casi todos traen EXACTAMENTE once dorsales del 1 al 11...
    assert once_exacto >= equipos * 0.8, f"{once_exacto}/{equipos}"
    # ...y en cambio «los once primeros» sacarían dos porteros en la mayoría
    assert dos_porteros >= equipos * 0.7, f"{dos_porteros}/{equipos}"


def test_escribir_el_dorsal_no_mueve_el_fichero(primera):
    antes = len(primera.raw)
    assert primera.set_player_dorsal(0, 0, 7)
    assert primera.player_info(0, 0)["dorsal"] == 7
    assert len(primera.raw) == antes
    primera.set_player_dorsal(0, 0, None)          # 99 en el fichero = sin dorsal
    assert primera.player_info(0, 0)["dorsal"] is None
    with pytest.raises(ValueError):
        primera.set_player_dorsal(0, 0, 120)
