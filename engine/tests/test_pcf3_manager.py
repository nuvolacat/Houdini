"""PCF 3.0 — el tope de extranjeros del `PCMANAG.DAT` (RE 2026-08-30, DESENSAMBLADO).

Se buscó primero por patrones de bytes y salió que «no está». **Era un error mío**: al calcular
la longitud de `cmp ax, imm16` le sumé un byte de más, y el `jbe` que va detrás quedaba fuera de
la ventana de búsqueda. El fichero siempre lo tuvo.

Desensamblando de verdad (capstone, 16 bits) aparece a la primera, en dos sitios:

    push  word ptr [bp-8]      ; el equipo
    lcall <rutina>             ; cuenta los extranjeros del once
    pop   cx
    mov   word ptr [bp-4], ax
    cmp   ax, 3                ; ← el tope
    jbe   ok                   ; si no pasa de 3, adelante
    ...                        ; si no, «El máximo de jugadores extranjeros titulares es 3»

Se localiza por esa FORMA, nunca por offset fijo.
"""
import os

import pytest

from houdini_engine.formats import pcf3_manager as M

_MGR = os.path.join(os.path.dirname(__file__), "..", "..", "gamedata", "FUTBOL3", "PCMANAG.DAT")


@pytest.fixture(scope="module")
def mgr():
    if not os.path.exists(_MGR):
        pytest.skip("sin gamedata/FUTBOL3")
    with open(_MGR, "rb") as f:
        return f.read()


def test_el_tope_de_fabrica_son_tres(mgr):
    """Lo dice el propio aviso del juego: «El máximo de jugadores extranjeros titulares es 3»."""
    assert M.limite_extranjeros(mgr) == 3


def test_esta_en_DOS_sitios(mgr):
    """El juego lo comprueba en dos pantallas. Tocar solo una dejaría la otra bloqueando."""
    assert len(M.sitios_extranjeros(mgr)) == 2


def test_subirlo_cambia_los_dos_y_nada_mas(mgr):
    nuevo = M.set_limite_extranjeros(mgr, 11)
    assert M.limite_extranjeros(nuevo) == 11
    assert len(nuevo) == len(mgr), "el ejecutable no puede cambiar de tamaño"
    assert sum(1 for a, b in zip(mgr, nuevo) if a != b) == 2


def test_se_puede_volver_a_dejar_como_estaba(mgr):
    ida = M.set_limite_extranjeros(mgr, 7)
    assert M.set_limite_extranjeros(ida, 3) == mgr, "la vuelta no deja el fichero igual"


def test_no_se_admiten_topes_absurdos(mgr):
    for malo in (-1, 12, 99):
        with pytest.raises(ValueError):
            M.set_limite_extranjeros(mgr, malo)


def test_en_un_ejecutable_que_no_es_se_dice_claro(mgr):
    with pytest.raises(ValueError, match="no se localiza"):
        M.set_limite_extranjeros(b"esto no es el manager" * 50, 5)


def test_el_resumen_es_el_que_espera_la_pantalla(mgr):
    r = M.resumen(mgr)
    assert r == {"disponible": True, "extranjeros": 3, "sitios": 2, "maximo": 11}
