# Avisos y créditos

## Marcas

PC Fútbol, PC Calcio y PC Premier son marcas de sus respectivos titulares. Este proyecto no está
afiliado a ellos ni cuenta con su respaldo.

## Ficheros de los juegos

Este repositorio **no contiene ficheros de los juegos** (ejecutables, bases de datos, gráficos ni
sonido). El motor trabaja sobre la copia del juego que aporte cada usuario. Lo único que incluye son
tablas técnicas pequeñas en `engine/houdini_engine/refdata/` (paletas, las tácticas predefinidas
de PCF 7, punteros de equipos y países), necesarias para la interoperabilidad con esos ficheros.

Los parches que el motor sabe aplicar al ejecutable del juego tocan solo **reglas de juego**
(plazas de las divisiones, competiciones, límites de extranjeros, años de nacimiento…). Ninguno toca
la protección anticopia.

## Material de terceros

- **FUTBOL_RELOAD** (pcnimdock), con licencia LGPL v3: las tablas de colores y el mapa de sprites
  de las camisetas del simulador de PCF 4 (`formats/pcf4_kits.py`), la tabla de países de PCF 4
  (`formats/pcf4.py`), las paletas de las minifotos de PCF 4 (`codec/pcf4_image.py`) y la tabla
  de caracteres de PCF 4 (`codec/pcf4_text.py`) parten de su trabajo.
- **PCx-Utils**, con licencia AGPL v3: algunos patrones de búsqueda en el ejecutable y el criterio
  para recorrer los bloques de datos se basan en su documentación y su código.
- **Editores y documentación de la comunidad**: offsets y estructuras documentados por los
  editores de carky12, MultiEditorPCC (1Simo1), EPCF7, el editor de 2001 de Jordi Gironés, el
  editor de PCF2001 y los hilos de pcfutbolmania, KeksPatch, J-Competiciones y Manager5Oro. Todo
  se ha verificado contra los ficheros del juego.
- **Datos de referencia** (`refdata/`): la numeración de equipos (`community_pointers.json`) es la
  tabla «Punteros Equipos V.2020» de peu7510; países, equipos y tácticas proceden de la base de
  datos de un editor comunitario de PCF 5.0/6.0.
- Las tablas de tácticas de PCF 2000/2001 y de calendario de PCF 2001, sacadas del editor de
  pcfutbolmania, **no se incluyen**. El motor funciona sin ellas.

Si eres autor de alguno de estos trabajos y quieres que se cite de otra forma o que se retire
algo, abre un issue.

## Créditos

Casi todo lo que se sabe de estos formatos viene de la comunidad: **carky12**, **peu7510**,
**pcnimdock** (FUTBOL_RELOAD), **1Simo1** (MultiEditorPCC), **Pablinho** (EPCF7 y el editor de
2001), **josewolf22**, **Mourg5**, **Jordi Gironés**, **Marchi (LSSL)**, **lupus** y la gente de
pcfutbolmania, TRONIC, KeksPatch y PCx-Utils.
