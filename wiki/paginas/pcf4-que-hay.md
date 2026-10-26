# PCF 4.0 y 4.5: qué hay dentro

El mapa de la carpeta del juego en PC Fútbol 4.0 y 4.5: qué guarda cada fichero y cuál te interesa según lo que quieras cambiar. La gran diferencia con 5.0 y 6.0 es que aquí no hay contenedores: casi todo son ficheros sueltos.

> Documentación hecha por la comunidad con fines de interoperabilidad y modding. Trabaja siempre sobre tu propia copia del juego. PC Fútbol es una marca de sus titulares; este proyecto no está afiliado a ellos.

Las dos versiones comparten formato. El fichero de equipo lleva el mismo número de versión, **400**, en las dos, y el mismo lector abre los de una y otra sin cambiar nada. La 4.5 trae más contenido —más jugadores y, en algunos clubes, **varios entrenadores**—, pero la estructura es la misma.

## La diferencia que lo cambia todo: un fichero por equipo

En 5.0 y 6.0 todos los clubes viven juntos en un `EQUIPOS.PKF`. En la 4.x **no existe ese fichero**: cada equipo es su propio `.DBC`.

```
DBDAT\EQ950001.DBC
DBDAT\EQ950002.DBC
...
```

El `95` es la temporada (1995) y las cuatro cifras finales son el número de equipo. En la 4.0 hay **235**. Cada fichero lleva una sola vez la firma `Copyright (c)1995 Dinamic Multimedia`, así que un fichero es un equipo y solo uno.

Esto tiene una ventaja enorme para el que edita: **si estropeas un club, solo estropeas ese club**. Y un inconveniente: no hay índice central, así que el juego decide qué equipo va en cada liga por otro lado (ver [el manager](pcf4-manager.html)).

## Los datos: la carpeta `DBDAT`

| Fichero o carpeta | Qué guarda |
|---|---|
| `EQ95NNNN.DBC` | **El corazón.** Un equipo: nombres, estadio, datos económicos, táctica, historial, entrenador y plantilla |
| `ARBITROS.DBC` `COMMENT.DBC` `COPAREY.DBC` `EUROPA.DBC` | Otras tablas del juego, no equipos. Su formato no está documentado aquí |
| `MINIESC\EQ95NNNN.DFG` | Escudo pequeño, uno por equipo |
| `BIGESC\EQ95NNNN.DFG` | Escudo grande de la ficha del club |
| `CAMISAS\EQ95NNNN.DFG` | La camiseta de la ficha. **Solo 44 equipos**: los 22 de Primera y los 22 de Segunda |
| `MINIFOTO\J95NNNNN.DFG` | Foto pequeña de jugador, cinco cifras de puntero |
| `BIGFOTO\` | Foto grande de jugador, 124×182 |
| `MINIENTR\E95NNNNN.DFG` | Foto de entrenador |
| `BIGCAMP\ES95NNNN.DFG` | Foto de estadio |

Fíjate en lo que **no** hay: ni `NANOESC` ni `RIDIESC`. La 4.x solo tiene escudo mini y grande. Y como son ficheros sueltos, **cambiar un escudo es reescribir un `.DFG`**: no hay contenedor que reconstruir ni índice que actualizar. El formato está en [las imágenes](pcf4-imagenes.html).

## El partido en dos dimensiones

| Fichero o carpeta | Qué guarda |
|---|---|
| `ESCUDOS\EQ95NNNN.EMP` | El escudo que se ve **durante el partido**. No es el de la ficha: es otro fichero con otro formato |
| `PALETAS\EQUIPOS.DAT` | Las camisetas del partido: dos por equipo |
| `GRAFICOS\*.EMP` | Las animaciones: andar, chutar, tarjetas, el balón… 155 ficheros y más de 5.100 fotogramas |

Un despiste frecuente: cambias el escudo en `MINIESC` y `BIGESC`, entras en un partido y sigue saliendo el viejo. Es porque el del partido está aparte, en `ESCUDOS`.

## La interfaz y el sonido

| Fichero | Qué guarda |
|---|---|
| `GFX01.DAT` … `GFX06.DAT` | Trofeos, iconos, botones, logos y rótulos de competición |
| `RES*.GRC` | Los textos de los menús. Uno por ejecutable |
| `GRAFICOS\FON_*.BLO` + `MAP_*.BIN` | Los fondos de pantalla, montados a base de baldosas |
| `GRAFICOS\PALETA.BBM` | La paleta de esos fondos |
| `PCFTEX4.DAT` `PCFTEX.DAT` `LGR.DAT` | Las pantallas del programa de arranque, con el rótulo «PC FUTBOL 4.0». En la raíz del juego; si no los tienes, cópialos de tu CD del juego |
| `SONIDOS\*.RAW` | Los efectos de sonido |

Todo esto está en [pantallas y sonido](pcf4-pantallas-sonido.html).

## Los ejecutables

En la 4.x no hay un `manager.exe`. El modo manager vive en **`PCMANAG.DAT`**, y el Pro Manager en **`PROMANAG.DAT`**. A pesar de la extensión, **son programas**, no datos, y deciden lo mismo que el ejecutable en 5.0 y 6.0: qué equipos hay en cada división, qué clubes no pueden ascender y cómo se llaman las competiciones.

Es la misma confusión de siempre: añades un equipo a la base y no aparece en la liga. No aparece porque el reparto de divisiones está en `PCMANAG.DAT`, no en los `.DBC`. Ver [el manager](pcf4-manager.html).

## Por dónde empezar

- **Cambiar plantillas, medias o datos de un club** → su `EQ95NNNN.DBC`: [el equipo](pcf4-equipo.html) y [la ficha del jugador](pcf4-ficha-jugador.html).
- **Leer un nombre** → antes que nada, [el texto](pcf4-texto.html): no es el mismo cifrado que en 5.0 y 6.0.
- **Cambiar escudos, fotos o camisetas** → [las imágenes](pcf4-imagenes.html). Recuerda que el escudo del partido va aparte.
- **Cambiar quién juega cada división** → [el manager](pcf4-manager.html).
- **Cambiar menús, fondos o sonidos** → [pantallas y sonido](pcf4-pantallas-sonido.html).
