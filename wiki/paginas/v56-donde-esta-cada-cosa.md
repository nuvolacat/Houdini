# Dónde está cada cosa

Índice al revés: partiendo de lo que quieres cambiar, dónde está y qué hay que leer.

## Los datos de la base

| Quiero cambiar… | Está en | Cómo se accede |
|---|---|---|
| Nombre, dorsal, físico, demarcaciones de un jugador | El fichero de equipos, dentro del bloque de su club | [La ficha de un jugador](v56-ficha-jugador.html) |
| Sus diez atributos | Los diez últimos bytes de su ficha | [La ficha de un jugador](v56-ficha-jugador.html) |
| Su fecha de nacimiento, o sea su edad | Cuatro bytes del bloque fijo de la ficha | [La ficha de un jugador](v56-ficha-jugador.html) |
| Quién es titular | El byte de posición en la plantilla | [La ficha de un jugador](v56-ficha-jugador.html) |
| Nombre del club, estadio, aforo, presidente, presupuesto | La cabecera de su bloque | [El bloque de un equipo](v56-bloque-equipo.html) |
| Historial, palmarés, posiciones por jornada | Detrás de la cabecera del bloque | [El bloque de un equipo](v56-bloque-equipo.html) |
| Cómo se coloca el equipo en el campo | Los 176 bytes de táctica dibujada | [El bloque de un equipo](v56-bloque-equipo.html) |
| Estilo de juego: presión, marcaje, entradas | Los 7 bytes de táctica de equipo | [El entrenador y la táctica](v56-entrenador.html) |
| El entrenador y sus textos | Antes de los jugadores, marcado con `02` | [El entrenador y la táctica](v56-entrenador.html) |
| Meter un nombre más largo de lo que cabe | Sacando el equipo a un DBC | [Los DBC](v56-dbc.html) |
| Añadir un equipo que no existe | Un DBC con un puntero libre | [Los DBC](v56-dbc.html) |

## Las imágenes

| Quiero cambiar… | Está en |
|---|---|
| Escudo | `NANOESC`, `MINIESC`, `RIDIESC`, `BIGESC` — los cuatro tamaños |
| Foto de jugador | `MINIFOTO` y `BIGFOTO` |
| Foto de entrenador | `MINIENTR` y `BIGENTR`, numeradas por el entrenador y no por el club |
| Bandera de país | `BANDERAS` y `MINIBAND` |
| Camiseta de la ficha | `CAMISAS` |
| Foto del estadio | `BIGCAMP`, `estadio` y `fondos` — **tres imágenes distintas** |
| La camiseta del partido | `DATSIM`, y no son imágenes sino colores |
| Foto de árbitro | `BIGARBIT` |

Todo esto se explica en [escudos, fotos y banderas](v56-imagenes.html), y el atajo que evita abrir los contenedores está ahí también.

## El aspecto del juego

| Quiero cambiar… | Está en |
|---|---|
| Fondos, botones e iconos del menú | `RECURSOS` e `IMG` |
| Las paletas de color de cada pantalla | `DAT` |
| Los gráficos de la base de datos | `RC_DBASE` |

En [las pantallas del juego](v56-pantallas.html) y [los contenedores menos conocidos](v56-otros-contenedores.html).

## El sonido

| Quiero cambiar… | Está en |
|---|---|
| La música | `MUSICAS`, en formato de tracker |
| Clics y cortinillas | La carpeta `SONIDOS`, audio en crudo sin cabecera |
| Público y comentarios | La carpeta `SFX` |

En [música y sonido](v56-sonido.html).

## Lo que no está en los datos

| Quiero cambiar… | Está en |
|---|---|
| Cuántas divisiones hay y qué equipos las forman | El ejecutable |
| Quién juega las competiciones europeas | El ejecutable |
| El año de la temporada | El ejecutable |
| Cuántos extranjeros se pueden alinear | El ejecutable |
| **El nombre de las competiciones** | El ejecutable, en texto sin cifrar |
| Los nombres que el juego inventa para la cantera | El contenedor de textos |

En [el ejecutable](v56-manager-exe.html), [renombrar las competiciones](v56-nombres-competiciones.html) y [los nombres que el juego inventa](v56-textos.html).

## Lo que no se puede cambiar

Conviene saberlo antes de perder el tiempo:

- **El número de plazas de una división.** Puedes cambiar quién las ocupa, no cuántas hay.
- **El tamaño de cualquier texto dentro del fichero de equipos**, salvo sacando el equipo a un DBC.
- **El tamaño del ejecutable.** Ni un byte.

## Lo que sigue sin resolverse

Honestidad por delante: queda esto, y solo esto.

- **Cuatro bytes de cada registro del índice**, los que van del 22 al 25. Hay una pista razonable —podrían ser la fecha en que se hizo cada elemento— pero **no está confirmada**, y en la página del contenedor se explica qué la sostiene y qué la rompe. Nada de lo demás depende de ellos: se copian tal cual.
- **El significado de dos trozos** de la equipación del partido. Su estructura sí está resuelta: se sabe dónde empieza y acaba cada uno y cómo están montados; lo que falta es qué prenda pintan.
- **Qué significa el quinto valor** de «situación en el club», que solo aparece en la edición argentina de 6.0. Las dos explicaciones evidentes están descartadas con datos, así que quien lo retome no empieza de cero.
- **Cómo se leen los ficheros de geometría y de animación** del simulador en tres dimensiones. Las trayectorias de cámara, que eran la parte difícil, ya están resueltas.

Y una advertencia sobre esta lista: **es corta a propósito**. No están aquí las cosas que se sabe leer pero no se han probado dentro del juego — eso va dicho en cada página, donde toca.

### Cosas que estaban en esta lista y ya no

Se dejan escritas porque a alguien le pueden sonar de otras documentaciones, donde siguen apareciendo como misterios:

- El «puntero con codificación peculiar» de la tabla de cabecera. **No existe**: es el nombre del fichero, cifrado como se cifra cualquier nombre.
- Los «veintidós bytes sin identificar» de cada registro del índice. Eran, casi todos, **el nombre**.
- El campo «que siempre vale 1» al final del registro. Es **el número de sección** del contenedor, y es lo que distingue elementos con el mismo nombre.
- Los «dos bytes que nadie ha identificado» entre el estadio y el nombre largo. Son **el país y la latitud**.
- El «identificador» de los bloques de nombres. Es **cuánto sitio ocupan los textos**, y hay que recalcularlo al escribir.
- Cómo se codifica cada posición de las **trayectorias de cámara**. Son tres números decimales: X, Y y altura.
