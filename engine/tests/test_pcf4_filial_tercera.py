"""PCF 4.0 — la TERCERA comprobación de filial que se nos había quedado sin parchear (2026-08-30).

Se detectó al revisar el ejecutable. Nosotros
parcheábamos DOS bloques —los que consultan la tabla de clasificación con
`cmp dword [reg+disp32], imm8`— pero hay un TERCERO, en la rutina que busca al siguiente
candidato al ascenso, que compara contra un REGISTRO:

    83 FE 1A 74 ..      cmp esi, 0x1a · je (descartar y seguir buscando)
    83 FE 1C 74 ..      cmp esi, 0x1c · je
    83 FE 22 0F 84 ..   cmp esi, 0x22 · je

Está en `PCMANAG.DAT` y en `PROMANAG.DAT` de las dos ediciones que tenemos. Y explica el síntoma
que se reportó al tocar solo los otros dos: el objetivo del equipo pasaba de «Ascenso» a «Zona
alta», pero el filial seguía sin subir — porque esta seguía descartándolo.

Con la lista vacía se escribe **0xFF** en los tres: `83 /7 ib` extiende el inmediato con signo, así
que queda -1 y no coincide con ningún equipo (los tid van de 1 a 96).
"""
import os

import pytest

from houdini_engine.formats import pcf4 as P4

_RAIZ = os.path.join(os.path.dirname(__file__), "..", "..", "gamedata")
_MGRS = ["pcf4/PCMANAG.DAT", "pcf4/PROMANAG.DAT",
         "pcf4_cd/FILES/PCMANAG.DAT", "pcf4_cd/FILES/PROMANAG.DAT"]


def _lee(rel):
    p = os.path.join(_RAIZ, *rel.split("/"))
    if not os.path.exists(p):
        pytest.skip(f"sin {rel}")
    with open(p, "rb") as f:
        return f.read()


@pytest.mark.parametrize("rel", _MGRS)
def test_la_tercera_rutina_existe_en_los_cuatro(rel):
    d = _lee(rel)
    offs = P4.filial_reg_offsets(d)
    assert len(offs) == 3, f"no se localiza en {rel}"
    assert [d[o] for o in offs] == [26, 28, 34], "de fábrica son Madrid B, Barça B y Athletic B"


@pytest.mark.parametrize("rel", _MGRS)
def test_sin_filiales_se_neutraliza_con_FF(rel):
    """Es lo que hace que un filial pueda ascender de verdad."""
    d = _lee(rel)
    offs = P4.filial_reg_offsets(d)
    nuevo = P4.set_filiales(d, [])
    assert [nuevo[o] for o in offs] == [0xFF, 0xFF, 0xFF]
    assert len(nuevo) == len(d), "el ejecutable no puede cambiar de tamaño"


@pytest.mark.parametrize("rel", _MGRS)
def test_se_pueden_poner_otros_equipos(rel):
    d = _lee(rel)
    offs = P4.filial_reg_offsets(d)
    nuevo = P4.set_filiales(d, [5, 9])
    assert [nuevo[o] for o in offs] == [5, 9, 0xFF], "los huecos que sobran se neutralizan"


def test_dejar_los_de_fabrica_no_cambia_esos_bytes():
    d = _lee("pcf4/PCMANAG.DAT")
    offs = P4.filial_reg_offsets(d)
    nuevo = P4.set_filiales(d, [26, 28, 34])
    assert [nuevo[o] for o in offs] == [26, 28, 34]


def test_los_otros_dos_bloques_se_siguen_parcheando():
    """La tercera se AÑADE, no sustituye a lo que ya había."""
    d = _lee("pcf4/PCMANAG.DAT")
    assert P4._find_filial_block(d), "el bloque de la tabla de clasificación sigue localizándose"
    nuevo = P4.set_filiales(d, [])
    dif = [i for i, (a, b) in enumerate(zip(d, nuevo)) if a != b]
    assert len(dif) > 3, "solo se han tocado los tres inmediatos: falta el resto del parche"
    offs = set(P4.filial_reg_offsets(d))
    assert offs <= set(dif), "los tres inmediatos tienen que estar entre los cambios"


def test_en_un_fichero_que_no_es_no_revienta():
    assert P4.filial_reg_offsets(b"nada de esto es un manager" * 100) == []
