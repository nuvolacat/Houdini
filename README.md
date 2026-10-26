# Houdini · motor de formatos de PC Fútbol

Biblioteca en Python para **leer y escribir los ficheros de datos de los PC Fútbol clásicos**
(PCF 3.0, 4.0, 5.0, 6.0, 7, 2000 y 2001, y PC Calcio / PC Premier): equipos, jugadores,
entrenadores, textos, imágenes, escudos, paletas, sonido y las tablas del ejecutable del juego.

Es el motor del editor web [PCFPLUS](https://pcfsite.com). Se publica para que cualquiera pueda
usarlo, estudiarlo y mejorarlo.

## Qué hay

| Carpeta | Contenido |
|---|---|
| `engine/houdini_engine/formats/` | Lectores y escritores de cada formato (round-trip byte a byte) |
| `engine/houdini_engine/codec/` | Texto cifrado, imágenes y paletas, sonido, contenedores |
| `engine/houdini_engine/refdata/` | Tablas de referencia (países, tácticas, paletas, punteros) |
| `engine/tests/` | Tests |
| `wiki/` | Documentación de los formatos, de PCF 3.0 a 2001 |

## Uso

```bash
cd engine
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Muchos tests necesitan los ficheros del juego y se saltan si no los encuentran. Para ejecutarlos,
copia los ficheros de tu juego en `gamedata/` en la raíz del repositorio (no se versiona) o apunta
la variable `HOUDINI_GAMEDATA` a donde los tengas.

## Ficheros del juego

Este repositorio **no incluye ningún fichero de los juegos**, solo tablas técnicas pequeñas para la
interoperabilidad. Cada uno trabaja con su propia copia legítima. Ver [NOTICE.md](NOTICE.md).

## Contribuir

Los pull requests son bienvenidos. Si encuentras un fallo en un formato, abre un issue con la
edición del juego, el fichero y qué esperabas ver.

## Licencia

[GNU AGPL-3.0](LICENSE). Créditos y material de terceros en [NOTICE.md](NOTICE.md).
