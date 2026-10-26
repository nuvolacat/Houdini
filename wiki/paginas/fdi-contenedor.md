# El contenedor FDI por dentro

Los ficheros de equipos, jugadores, entrenadores y estadios de PC Fútbol 7, 2000 y 2001 usan el mismo contenedor: una cabecera, un índice y los registros uno detrás de otro. Es el formato más cómodo de editar de toda la saga.

## La estructura

| Posición | Tamaño | Qué es |
|---|---|---|
| 0 | 8 bytes | la firma `DMFIv1.0`, en texto claro |
| 8 | 8 bytes | ceros |
| 16 | 4 bytes | cuántos registros hay (`n`) |
| 20 | `n` × 13 bytes | el índice |
| 20 + 13·`n` | — | los registros, pegados |

Cada entrada del índice mide 13 bytes:

| Dentro de la entrada | Tamaño | Qué es |
|---|---|---|
| +0 | 4 bytes | el código del registro: el puntero de equipo, de jugador, de entrenador o de estadio |
| +4 | 1 byte | relleno, siempre `00` |
| +5 | 4 bytes | dónde empieza el registro, contado desde el principio del fichero |
| +9 | 4 bytes | cuánto mide |

Como siempre, los números van con el byte bajo primero.

## Lo que hay que respetar al escribir

Tres cosas, comprobadas en todos los ficheros de las tres ediciones:

- **El índice va ordenado por código** y, a la vez, **por posición**: el registro de código más bajo es también el primero del fichero.
- **Los registros son contiguos.** Sin huecos y sin solapes: cada uno empieza donde acaba el anterior, y el fichero termina exactamente al final del último.
- **El primer registro empieza justo después del índice**, en la posición 20 + 13·`n`.

De ahí sale la buena noticia. **Aquí el tamaño no manda** como en 5.0 y 6.0: si un nombre crece, el registro crece, y basta con volver a escribir el índice recalculando las posiciones en orden. Altas y bajas de registros, igual. La regla de oro de no cambiar longitudes sigue valiendo para el ejecutable, pero no para estos ficheros.

La forma segura de editar es siempre la misma: **lee todos los registros, cambia lo que quieras y vuelve a emitir el fichero entero**, índice incluido. Si lo haces sin cambiar nada, tiene que salir idéntico byte a byte; los seis ficheros de PC Fútbol 7 y los ocho de PC Fútbol 2000 lo cumplen con un lector campo a campo.

## Lo que llevan todos los registros

Jugadores, equipos y entrenadores empiezan con dos campos de dos bytes que conviene conocer antes de leer nada más. (El equipo lleva antes una firma de 36 bytes: `Copyright (c)1998 Dinamic Multimedia` en 7 y `Copyright (c)2000 Dinamic Multimedia` en 2000 y 2001.)

### La suma de longitudes

El primer campo **no es un dato, es un cálculo**: la suma de la longitud de los textos con nombre propio del registro, **más uno por cada texto**. Se cumple sin una sola excepción en los 41.341 registros de PC Fútbol 7.

| Registro | Textos que entran en la suma |
|---|---|
| Jugador | nombre corto y nombre largo; si tiene ficha completa, también ciudad natal, club de procedencia e internacionalidades |
| Equipo (7) | nombre corto, estadio y nombre largo; si es de liga jugable, también presidente, patrocinador y proveedor |
| Equipo (2000 y 2001) | lo mismo sin el estadio, que ya no va en el equipo |
| Entrenador | el apodo; con ficha completa, también el nombre |

Los diez textos largos de base de datos **no cuentan**. La consecuencia: **si cambias un nombre, recalcula este campo**. Copiar el viejo deja un registro que no cuadra.

### La versión

El segundo campo vale **700 en PC Fútbol 7 y 800 en 2000 y 2001**. El juego no lo comprueba: ficheros de PC Fútbol 7 con 800 en todos los equipos cargan igual. Aun así, lo prudente es dejar el valor que traía.

Un aviso: la versión **no basta para distinguir 2000 de 2001**, que comparten el 800 y aun así tienen un registro de equipo distinto. Lo explica [la página del equipo](fdi-equipo.html).

## Si te encuentras un registro que no encaja

Hay bases retocadas a mano con otros editores que traen algún registro que no sigue el formato. Lo sensato no es rechazar el fichero entero: **guarda ese registro tal cual y vuelve a escribirlo igual**. El índice te dice dónde empieza y cuánto mide, así que puedes saltártelo sin entenderlo, y el resto del fichero se edita con normalidad.

## Cómo identificar cada fichero

| Empieza por | Qué es |
|---|---|
| `EQ` | equipos |
| `JUG` | jugadores |
| `ENT` | entrenadores |
| `EST` | estadios (solo 2000 y 2001) |

El contenedor no dice qué tipo de registro lleva: lo dice el nombre del fichero. Y la edición, el tamaño del ejecutable que lo acompaña, como cuenta [la página del ejecutable](fdi-manager.html).
