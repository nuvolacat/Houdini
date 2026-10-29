<div align="center">

<img src="docs/readme/icono.png" width="128" alt="Houdini">

# Houdini · motor de formatos de PC Fútbol

**Cómo están hechos por dentro los PC Fútbol clásicos, y cómo tocarlos sin romperlos.**

Documentación y biblioteca en Python para leer y escribir los ficheros de PCF 3.0, 4.0, 5.0, 6.0, 7, 2000 y 2001,
y de PC Calcio / PC Premier.

![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776ab?logo=python&logoColor=white)
![Pillow](https://img.shields.io/badge/Pillow-imágenes-8a2be2)
![pytest](https://img.shields.io/badge/pruebas-pytest-0a9edc?logo=pytest&logoColor=white)
![Round-trip](https://img.shields.io/badge/round--trip-byte%20a%20byte-3c8d5a)
![Licencia AGPL-3.0](https://img.shields.io/badge/licencia-AGPL--3.0-c9a227)

</div>

---

## ⚽ Qué es

Equipos, jugadores, entrenadores, textos, imágenes, escudos, paletas, sonido y las tablas del ejecutable del juego:
dónde está cada dato, cómo leerlo y cómo modificarlo sin romper el fichero.

Esto **no es un editor**: es la base técnica para construir uno. El editor [Houdini](https://editor.pcfsite.com) se basa
en esta documentación. Se publica para que cualquiera pueda usarla, estudiarla y mejorarla.

### 📦 El motor (`engine/`)
- **Formatos**: lectores y escritores de cada fichero (bases de datos, contenedores PKF y FDI, manager, competiciones,
  pantallas, textos, músicas y efectos), con **round-trip byte a byte**.
- **Códecs**: texto cifrado, imágenes y paletas (también FLC e ILBM), fotos, sonido (VOC) y contenedores.
- **Datos de referencia**: países, tácticas, paletas, camisetas y punteros.
- **Tests** con pytest; los que necesitan ficheros del juego se saltan si no los encuentran.

### 📖 La wiki (`wiki/`)
Más de 40 páginas de documentación de los formatos, de PCF 3.0 a 2001: qué hay en cada edición, ficha del jugador,
bloque del equipo, entrenador, imágenes, paletas, textos, sonido, el ejecutable del manager y sus offsets, el simulador
y las **reglas de oro** para modificar sin romper nada.

| Familia | Páginas |
|---|---|
| PCF 3.0 | `pcf3-*` (bloque de equipo, ficha, competiciones, gráficos, manager, texto) |
| PCF 4.0 | `pcf4-*` (equipo, ficha, imágenes, manager, pantallas y sonido, texto) |
| PCF 5.0 y 6.0 | `v56-*` (contenedor PKF, DBC, ficha, entrenador, imágenes, paleta, manager.exe, simulador…) |
| PCF 7, 2000 y 2001 | `fdi-*` (contenedor, equipo, jugador, imágenes, manager, sonido, táctica) |
| Común | `reglas-de-oro.md` |

---

## 🧱 Qué hay

| Carpeta | Contenido |
|---|---|
| `engine/houdini_engine/formats/` | Lectores y escritores de cada formato (round-trip byte a byte) |
| `engine/houdini_engine/codec/` | Texto cifrado, imágenes y paletas, sonido, contenedores |
| `engine/houdini_engine/refdata/` | Tablas de referencia (países, tácticas, paletas, punteros) |
| `engine/tests/` | Tests |
| `wiki/` | Documentación de los formatos, de PCF 3.0 a 2001 (`wiki/paginas/`, índice en `wiki/wiki.json`) |

## 🚀 Uso

```bash
cd engine
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Muchos tests necesitan los ficheros del juego y se saltan si no los encuentran. Para ejecutarlos, copia los ficheros
de tu juego en `gamedata/` en la raíz del repositorio (no se versiona) o apunta la variable `HOUDINI_GAMEDATA` a donde
los tengas.

## 💿 Ficheros del juego

Este repositorio **no incluye ningún fichero de los juegos**, solo tablas técnicas pequeñas para la
interoperabilidad. Cada uno trabaja con su propia copia legítima. Ver [NOTICE.md](NOTICE.md).

## 🤝 Contribuir

Los pull requests son bienvenidos. Si encuentras un fallo en un formato, abre un issue con la edición del juego, el
fichero y qué esperabas ver.

## 📜 Licencia

[GNU AGPL-3.0](LICENSE). Créditos y material de terceros en [NOTICE.md](NOTICE.md).

---

<div align="center">
<br>

Hecho por fans, sin afiliación con los titulares de las marcas

© NUVOLACAT
</div>
