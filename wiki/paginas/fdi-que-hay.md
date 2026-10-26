# PC Fútbol 7, 2000 y 2001: qué hay dentro

El mapa de la carpeta del juego en la familia FDI. Qué fichero guarda cada cosa, en qué se parece a 5.0 y 6.0 y qué ha cambiado de sitio.

> Documentación hecha por la comunidad con fines de interoperabilidad y modding. Trabaja siempre sobre tu propia copia del juego. PC Fútbol es una marca de sus titulares; este proyecto no está afiliado a ellos.

Las tres ediciones forman una familia propia. **PC Fútbol 7 es la familia 5.0/6.0 reorganizada**: el mismo cifrado de texto, la misma firma de Dinamic y los mismos códigos de equipo, pero con la base de datos partida en ficheros con índice. **2000 y 2001 son PC Fútbol 7 con retoques**: el mismo contenedor, tres bytes más en el jugador y un cuarto fichero para los estadios. Lo que aprendas en una vale casi entero para las otras dos.

(PC Calcio 7 es la edición italiana de PC Fútbol 7 y usa exactamente el mismo formato.)

## La base de datos: la carpeta `DBDAT`

En 5.0 y 6.0 todo iba en un único fichero de equipos con los jugadores dentro. Aquí no: **cada tipo de registro tiene su fichero**, y el equipo solo guarda una lista de punteros a sus jugadores y entrenadores.

| Fichero | Qué guarda | 7 | 2000 | 2001 |
|---|---|---|---|---|
| `EQ…022.FDI` | Equipos: datos del club, historial, palmarés, táctica y la lista de su plantilla | sí | sí | sí |
| `JUG…022.FDI` | Jugadores, uno por registro | sí | sí | sí |
| `ENT…022.FDI` | Entrenadores | sí | sí | sí |
| `EST…022.FDI` | **Estadios**: nombre, medidas, aforo, año | — | sí | sí |

Los números del nombre son la temporada y la edición. En PC Fútbol 7 hay **dos juegos de ficheros**, `98` y `99` (temporadas 98/99 y 99/00); en 2000, `99` en la base y `00` en la extensión, que trae su propio ejecutable. El `022` es el código de la edición española y se repite en otros nombres de fichero.

**Cuál de los dos juegos usa el juego.** En PC Fútbol 7 el ejecutable apunta a la temporada `99`: sus tablas de división incluyen equipos de 2ªB que solo existen en `EQ99`. Si vas a editar uno, edita ese; si quieres cubrirte, edita los dos igual.

Cuántos registros trae cada uno, para que sepas si tu lector se ha comido alguno:

| | Equipos | Jugadores | Entrenadores | Estadios |
|---|---|---|---|---|
| PCF7, temporada 98 | 876 | 18.717 | 925 | — |
| PCF7, temporada 99 | 898 | 19.045 | 880 | — |
| PCF2000, temporada 99 | 985 | 21.663 | 1.054 | 984 |
| PCF2000, temporada 00 | 1.051 | 22.576 | 1.052 | 1.046 |

Los cuatro tienen la misma estructura de contenedor, explicada en [el contenedor FDI](fdi-contenedor.html).

## Lo demás de `DBDAT`

| Fichero | Qué guarda |
|---|---|
| `textos.pkf` (7) · `TEXTOS.PAK` (2000 y 2001) | Los nombres de los países y las listas de nombres y apellidos con los que el juego bautiza a los jugadores que se inventa |
| Contenedores de imágenes | Escudos en tres tamaños, fotos de jugador, camisetas, banderas y, nuevo en esta familia, fotos de estadio. En 7 son `.pkf`; en 2000 y 2001, `.pak` |
| `*.dbc` | La parte de consulta: árbitros, resultados jornada a jornada, historial de cada competición, textos del comentarista |
| `FECHCONV.22` | Las fechas de partidos de selecciones, que liberan a los jugadores convocados |
| `TACTICS\PREDEF.001` a `.010` | En PC Fútbol 7, las diez tácticas predefinidas, de 1.848 bytes cada una |

Los `.dbc` son del mismo formato que en 5.0 y 6.0 y alimentan solo la parte de base de datos, no la simulación. **Para cambiar quién juega y cómo, no hace falta tocarlos.**

## La interfaz, el sonido y el simulador

| Edición | Pantallas | Sonido |
|---|---|---|
| 7 | `Recursos.pkf`, `Img.pkf`, `DAT.PKF`, `NGI.pkf`, `AYUDA.PKF` | `SONIDOS\` (interfaz), `SFX\` (comentarios y ambiente), `MUSICAS.PKF` (música de tracker) |
| 2000 | `Graficos.pak` y otros `.pak` en la raíz | `SFX\`: contenedores sin extensión con voces, cánticos, comentarios y la música en MIDI |
| 2001 | `GRAFICOS.PAK` y otros `.pak` | `SFX\`, como 2000, pero la música es MP3 |

Lo cuentan [las imágenes y pantallas](fdi-imagenes.html) y [el sonido](fdi-sonido.html).

## El ejecutable

`MANAGER.EXE` sigue decidiendo lo mismo que en 5.0 y 6.0: **qué equipos forman cada división, quién juega cada copa, el año de la temporada y los topes del juego**. Si añades un equipo a la base y no aparece en la liga, es porque la plaza está en el ejecutable. Está en [su propia página](fdi-manager.html).

## Qué cambia respecto a 5.0 y 6.0

- **Cada registro está en su fichero**, con un índice delante. Ya no hay que mantener tamaños: un nombre puede crecer y el índice se recalcula.
- **El jugador tiene dieciséis medias** en vez de diez: se añaden el pie bueno y cinco acciones a balón parado.
- **La táctica dibujada pasa de 4 a 40 posiciones por jugador.**
- **El palmarés de copas es una lista de longitud variable**, no un bloque fijo.
- **El texto se cifra igual**: XOR con `0x61`, con la longitud en dos bytes delante, como cuenta [la página del texto](v56-texto.html). La excepción es el ejecutable, que guarda sus textos en claro.

## Por dónde empezar

- **Plantillas, medias, datos de jugador** → [la ficha del jugador](fdi-jugador.html).
- **Datos del club, estadio, historial y palmarés** → [el registro de equipo](fdi-equipo.html).
- **La pizarra táctica** → [la táctica](fdi-tactica.html).
- **Quién juega cada liga y cada copa** → [el ejecutable](fdi-manager.html).
