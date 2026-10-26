# El fichero de equipo en 4.0 y 4.5

Qué hay dentro de un `EQ95NNNN.DBC`, campo a campo: la cabecera, los datos del club, la táctica, el historial, los entrenadores y la plantilla. Es la misma familia de bloque que en 5.0 y 6.0, con otro orden y otros tamaños.

Antes de seguir necesitas [el texto](pcf4-texto.html): todas las cadenas de esta página son de longitud de un byte y cifrado de la 4.x.

## La cabecera: 43 bytes

Todo fichero de equipo empieza igual. Las posiciones son fijas:

| Posición | Tamaño | Qué es |
|---|---|---|
| `0x00` | 36 bytes | La firma `Copyright (c)1995 Dinamic Multimedia`, en claro |
| `0x24` | 1 byte | `00` |
| `0x25` | 1 byte | Tipo de fichero |
| `0x26` | 2 bytes | **Versión de formato: 400** (`90 01`) |
| `0x28` | 2 bytes | Sin confirmar |
| `0x2A` | 1 byte | **¿Tiene datos de base de datos?** `0` sí · otro valor, no |

La versión es lo que identifica el formato: **400** en 4.0 y 4.5, frente a 500 en 5.0 y 525 en 6.0. Compruébala antes de nada; si no es 400, este mapa no te sirve.

El byte `0x2A` es el que decide la forma de todo lo demás, como la distinción entre clubes nacionales y extranjeros de 5.0 y 6.0. Un equipo **con** base de datos guarda presidente, socios, presupuestos, biografías… Uno **sin** ella se salta todos esos campos. En las tablas de abajo, los campos marcados *(BD)* solo existen si `0x2A` vale `0`.

## Los datos del club

Justo detrás de la cabecera, en este orden:

| Campo | Tamaño | Qué es |
|---|---|---|
| País | 1 byte | Código de país (ver [las tablas](pcf4-ficha-jugador.html)) |
| Nombre largo | texto | «Fútbol Club Barcelona» |
| Nombre corto | texto | «Barcelona» |
| Nombre en mayúsculas | texto | El de los rótulos. La `\` marca el salto de línea: `FUTBOL CLUB\BARCELONA` |
| Posición del escudo *(BD)* | 5 bytes | Dónde se pinta el escudo grande: X (2 bytes), Y (2 bytes) y un byte más, de 0 a 9 |
| Año de fundación *(BD)* | 2 bytes | |
| Estadio | texto | |
| Aforo | 4 bytes | |
| Socios *(BD)* | 4 bytes | |
| Presidente *(BD)* | texto | |
| Presupuesto *(BD)* | 4 bytes | El que enseña la base de datos |
| Presupuesto en el juego *(BD)* | 4 bytes | El que tienes al empezar la partida |
| Patrocinador *(BD)* | texto | |
| Marca de ropa *(BD)* | texto | |
| Última década *(BD)* | 10 bytes | El puesto final en cada una de las diez últimas temporadas. `0x3F` (63) = no participó o sin dato |
| Nombre corto en mayúsculas | texto | |

Los dos presupuestos son números distintos y conviene no confundirlos: cambiar solo el de la base de datos no te da más dinero en la partida. La unidad exacta en que se guardan está sin confirmar.

El aforo ocupa **cuatro bytes**, como en 6.0 y a diferencia de los tres de 5.0. Y, como en todo el formato, el byte bajo va primero.

## La zona sin índice: táctica e historial

Después del nombre en mayúsculas viene un bloque de longitud variable que ningún campo anuncia. Tiene dos partes.

### Los primeros 176 bytes: la táctica

Es **la misma estructura de táctica que en 5.0 y 6.0**: once jugadores, y por cada uno ocho números de dos bytes.

| Número | Qué es |
|---|---|
| 1-4 | La zona por la que se mueve: x mínima, y mínima, ancho y alto |
| 5-6 | Dónde se coloca defendiendo (x, y) |
| 7-8 | Dónde se coloca atacando (x, y) |

La diferencia es la escala. En 5.0 y 6.0 son píxeles; aquí son **casillas de una rejilla de 16 × 9**. El portero lo deja claro: en todos los equipos de la base es idéntico, con su zona entre las casillas x 0-2 e y 3-6 y su posición en (0, 4), la línea de gol y el centro exacto de las nueve filas.

Para pintarla, usa el **centro** de cada casilla: `(x + 0,5) / 16` y `(y + 0,5) / 9`.

Una comprobación que te dice si has encontrado el sitio bueno: **cada posición tiene que caer dentro de su zona**. `xMin ≤ x ≤ xMin + ancho` y lo mismo con la y. Se cumple en los 235 equipos sin excepción, cosa imposible si estás leyendo otra cosa.

El juego ofrece seis formaciones con nombre (3-4-3, 3-5-2, 4-3-3, 4-4-2, 5-3-2 y 5-4-1), y muchos equipos de la base usan exactamente alguno de esos dibujos. Otros llevan uno propio: entre los 235 hay 66 dibujos distintos.

### El resto: el historial

Lo que va detrás de la táctica es el historial y el palmarés del club, y su longitud varía de un equipo a otro. Su estructura interna no está documentada aquí. Si no lo vas a editar, **consérvalo byte a byte**.

En los equipos **sin** base de datos, todo este bloque mide siempre **177 bytes**.

## Cómo encontrar dónde empiezan los entrenadores

Como el historial no dice cuánto mide, no hay forma directa de saltar al final. Lo que se hace es buscar hacia delante:

1. Busca un byte `01` seguido de algo que se lea como un jugador: dos bytes de puntero, dos nombres legibles y una posición en la plantilla entre 1 y 40. Comprueba que a partir de ahí puedes leer jugador tras jugador hasta el final del fichero y que lo que sobra son ceros.
2. Los entrenadores son los registros `02` que hay justo antes, pegados al primer jugador.
3. Lo que queda entre el nombre en mayúsculas y el primer entrenador es la táctica más el historial.

No te quedes con el primer `01` que encuentres: dentro del historial hay muchos, y por eso hace falta comprobar que los nombres se leen.

## Los entrenadores

Uno detrás de otro. En la 4.0 lo normal es uno; en la 4.5, algunos equipos llevan varios.

| Campo | Tamaño | Qué es |
|---|---|---|
| Marca | 1 byte | `02` |
| Puntero | 2 bytes | Su identificador |
| Nombre corto | texto | El apellido, con la inicial en mayúscula |
| Nombre largo *(BD)* | texto | |
| Información *(BD)* | texto troceado | La biografía |
| Declaraciones *(BD)* | texto troceado | |
| Cierre | 1 byte | `00` |

En un equipo sin base de datos, el nombre del entrenador puede ir vacío.

## Los jugadores y el final

Después de los entrenadores vienen los jugadores, cada uno empezando con `01`, hasta el final del fichero. Su estructura está en [la ficha del jugador](pcf4-ficha-jugador.html).

El fichero termina con uno o más bytes `00` detrás del último jugador. Hay equipos sin base de datos que no tienen jugadores en absoluto: el fichero acaba tras el entrenador.

## Escribir

Como explica [la página del texto](pcf4-texto.html), aquí puedes cambiar longitudes: reescribe el fichero entero en este mismo orden y listo.

La prueba de siempre sigue valiendo, y es la que te dice si tu lector está bien: **lee y reescribe sin cambiar nada; tiene que salir idéntico**. Con los 235 ficheros de la 4.0 y los de la 4.5 se consigue al byte, siempre que respetes el troceado original de los textos largos y conserves el historial tal cual.

## Crédito

El orden de los campos del equipo y del jugador lo documentó primero **pcnimdock** en su editor FUTBOL_RELOAD para la 4.5. La identificación de la táctica dentro del bloque que sigue a los nombres es de este proyecto.
