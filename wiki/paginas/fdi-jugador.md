# La ficha del jugador en 7, 2000 y 2001

Cada jugador es un registro propio del fichero `JUG…FDI`, con los mismos campos que en 6.0 más seis medias nuevas. 2000 y 2001 añaden tres bytes de aspecto. Al final, el entrenador, que sigue la misma lógica.

## Los campos, en orden

| Campo | Tamaño | Qué es |
|---|---|---|
| Suma de longitudes | 2 bytes | calculada; ver [el contenedor](fdi-contenedor.html) |
| Versión | 2 bytes | 700 en 7, 800 en 2000 y 2001 |
| Tipo de ficha | 1 byte | `0` completa · `1` corta |
| Foto | 2 bytes | **siempre igual al código del jugador** |
| Dorsal | 1 byte | |
| Nombre corto | texto | el de las alineaciones |
| Nombre largo | texto | |
| Posición en la plantilla | 1 byte | `1` a `11` el once, después el resto por orden; `99` fuera del primer equipo (filial) |
| Situación en el club | 1 byte | ver más abajo |
| Demarcaciones | 6 bytes | la primera obligatoria; los mismos 18 códigos que en [las tablas](v56-tablas.html) |
| Nacionalidad | 1 byte | código de país |
| Tono de piel del avatar | 1 byte | `1`, `2`, `3` |
| Color de pelo | 1 byte | `1` rubio · `2` sin pelo · `3` moreno · `4` canoso · `5` pelirrojo · `6` castaño |
| Puesto | 1 byte | `0` portero · `1` defensa · `2` medio · `3` delantero |
| *Tipo de pelo* | 1 byte | *solo 2000 y 2001* |
| *Vello facial* | 1 byte | *solo 2000 y 2001* |
| *Nacionalizado* | 1 byte | *solo 2000 y 2001* |
| Día, mes de nacimiento | 1 + 1 byte | |
| Año de nacimiento | 2 bytes | |
| Altura | 1 byte | en centímetros |
| Peso | 1 byte | en kilos |
| País de nacimiento | 1 byte | *solo ficha completa* |
| Ciudad natal | texto | *solo ficha completa* |
| Club de procedencia | texto | *solo ficha completa* |
| Internacionalidades | texto | *solo ficha completa*. Es **texto**, no número: puede decir `22` o `Portugal` |
| Siete textos de base de datos | texto | *solo ficha completa* |
| Medias | 16 bytes | ver más abajo |

Todos los textos son como en el resto de la saga: dos bytes de longitud y la cadena cifrada con XOR `0x61`.

## Ficha completa y ficha corta

Es la misma idea que en 5.0 y 6.0, con una diferencia que facilita la vida: **aquí la ficha dice de qué tipo es**, en su quinto byte. Ya no tienes que deducirlo del club.

La **ficha corta** termina en el peso y salta directamente a las dieciséis medias: sin país de nacimiento, sin ciudad, sin procedencia, sin internacionalidades y sin textos. Es la de los jugadores de ligas no jugables.

Si cambias una ficha de corta a completa, **tienes que añadirle todos esos campos**, aunque sea con el marcador de vacío. Si no, el juego lee como textos los bytes de las medias.

## Los tres bytes nuevos de 2000 y 2001

Van **entre el puesto y el día de nacimiento**. Son la diferencia entera entre el jugador de 7 y el de 2000: con un lector de PC Fútbol 7, a partir de ahí todo sale corrido tres bytes y ya nada cuadra.

- **Tipo de pelo** y **vello facial** dibujan el avatar. Los valores de fábrica más habituales son `3` y `1`. Un `0` no es «sin pelo»: **el pelo sale verde**. Si creas fichas nuevas, no los dejes a cero.
- **Nacionalizado** marca al jugador que cuenta como nacional aunque su país sea otro. Los valores exactos que acepta el juego están **sin confirmar**.

## La situación en el club

| Código | Significado |
|---|---|
| 0 | Sigue en el equipo |
| 1 | Fichaje |
| 2 | Ascendido del filial |
| 3 | **Baja en el equipo**: está en la base del club pero no cuenta para la plantilla |
| 4 y 5 | En 2000 y 2001 se describen como «cedido» y «regresa»; **sin confirmar** |

Cuidado al reutilizar una ficha para otro jugador: si no reescribes este byte, **el nuevo hereda la baja del anterior** y no sale en la plantilla.

## Las dieciséis medias

Diez son las de siempre; seis son nuevas. Cada una es un byte:

| # | Media | | # | Media |
|---|---|---|---|---|
| 0 | Velocidad | | 8 | Entradas |
| 1 | Resistencia | | 9 | Portero |
| 2 | Agresividad | | 10 | **Pie bueno** |
| 3 | Calidad | | 11 | **Penaltis** |
| 4 | Remate | | 12 | **Córner izquierdo** |
| 5 | Regate | | 13 | **Córner derecho** |
| 6 | Pase | | 14 | **Falta izquierda** |
| 7 | Tiro | | 15 | **Falta derecha** |

El orden de las diez primeras es **el de 6.0**: remate antes que regate. Si traes datos de 5.0, recuerda que allí van al revés.

**El pie bueno no es una media**: es `0` diestro, `1` zurdo o `2` ambidiestro. En la base de fábrica, el 93 % son diestros.

Las cinco de balón parado van de 0 a 99 como las demás. Si no tienes datos para ellas, salen muy parecidas al **tiro** (penaltis y faltas) y a la media entre tiro y pase (córners): en la base original la correlación ronda el 0,8.

## Los siete textos de base de datos

Van seguidos, cada uno con su longitud por delante:

1. Perfil
2. Características
3. Palmarés
4. Internacionalidad
5. Anécdotas
6. Última temporada
7. Trayectoria

Con la ciudad, la procedencia y las internacionalidades, son **los mismos diez textos de 5.0 y 6.0**, en el mismo orden; lo que cambia es que los tres primeros se han separado del bloque. El texto vacío es una `x`, como siempre, y la trayectoria sigue siendo una tabla de líneas con campos separados por comas.

## Lo que no está en la ficha

**El equipo.** El jugador no dice de qué club es: lo dice el club, que guarda la lista de punteros de su plantilla (ver [el registro de equipo](fdi-equipo.html)). Un mismo jugador referenciado por dos equipos aparece en los dos.

**La foto.** Va por el código del jugador, con cinco cifras en el nombre del fichero. Por eso el campo «foto» de la ficha tiene que ser igual al código: si creas un jugador, ponlos iguales.

## Cuántos jugadores caben

**El formato no fija un máximo por equipo**: lo fija el ancho del contador en el registro del club. Es un byte en 7 y en 2000 (hasta 255) y dos bytes en 2001. Las bases de fábrica lo aprovechan: hay equipos de **49 y 50** en PC Fútbol 7, de **55** en 2000 y uno de **463** en 2001, todos selecciones juveniles. Lo que sí pide el juego, como siempre, es un mínimo de once con al menos un portero.

## El entrenador

Fichero `ENT…FDI`. Mismo esquema en las tres ediciones.

| Campo | Tamaño | Qué es |
|---|---|---|
| Suma de longitudes | 2 bytes | apodo, más el nombre si la ficha es completa |
| Versión | 2 bytes | 700 / 800 |
| Tipo de ficha | 1 byte | `0` completa · `1` de relleno, solo con apodo |
| Código | 2 bytes | el identificador del entrenador |
| Apodo | texto | |
| Nombre | texto | *solo ficha completa* |
| Seis textos | texto | *solo ficha completa* |
| Marca de exjugador | 1 byte | `0` no fue jugador · `3` sí lo fue |
| Uno o dos textos más | texto | uno si la marca es `0`, dos si es `3` |

Algo más de la mitad son de relleno. Los seis textos son, en orden: actualidad, estilo de juego, palmarés, biografía, temporada pasada y trayectoria como entrenador. Esta última es una tabla con cinco campos por línea: temporada, equipo, división, puesto y notas.

Detrás de la marca va, si fue jugador, **su trayectoria como jugador** (otra tabla) y después **sus declaraciones**; si no lo fue, solo las declaraciones. Es lo que hace que esa marca no sea un dato suelto: **decide cuántos textos hay después**. Si la cambias de `0` a `3`, añade el texto que falta.
