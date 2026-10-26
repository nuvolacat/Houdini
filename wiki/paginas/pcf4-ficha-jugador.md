# La ficha de un jugador en 4.0 y 4.5

Cómo se guarda cada jugador dentro del fichero de equipo de la 4.x, con las tablas de códigos para interpretarlo. Son cuatro medias y cuatro habilidades sí/no, no las diez medias de 5.0 y 6.0.

Los jugadores van al final del fichero de equipo, uno detrás de otro, después de los entrenadores (ver [el equipo](pcf4-equipo.html)). Cada ficha empieza con `01`.

## Los campos, en orden

| Campo | Tamaño | Qué es |
|---|---|---|
| Marca | 1 byte | `01` (el `02` es el entrenador) |
| Puntero | 2 bytes | El identificador del jugador. Es el número de su foto: `MINIFOTO\J95NNNNN.DFG` |
| Nombre corto | texto | El de las alineaciones |
| Nombre largo | texto | El completo |
| Posición en la plantilla | 1 byte | De `1` a `40`, distinta para cada jugador del equipo |
| Situación | 1 byte | `0` seguía · `1` fichaje · `2` cantera |
| Demarcación principal | 1 byte | De `1` a `18`, nunca `0` |
| Demarcaciones secundarias | 5 bytes | `0` = vacía |
| Posición en la plantilla, otra vez | 1 byte | Repite la de arriba |
| Separador | 1 byte | `00` |
| Nacionalidad | 1 byte | `0` nacional · `1` extranjero |
| Piel | 1 byte | `0` · `1` · `2`: los tres tonos de cara que dibuja el juego |
| Pelo | 1 byte | Ver abajo |
| Puesto | 1 byte | `0` portero · `1` defensa · `2` medio · `3` delantero |
| Lugar de nacimiento *(BD)* | texto | |
| Fecha de nacimiento *(BD)* | 3 bytes | Día, mes y año con dos cifras |
| Equipo de procedencia *(BD)* | texto | |
| Internacional *(BD)* | texto | Veces internacional, como texto |
| Altura *(BD)* | 1 byte | En centímetros |
| Peso *(BD)* | 1 byte | En kilos |
| Comentario *(BD)* | texto troceado | La biografía |
| Precio *(BD)* | 2 bytes | En millones de pesetas, de 1 a 65.535 |
| Medias | 4 bytes | Velocidad, resistencia, agresividad, calidad |
| Habilidades | 4 bytes | Técnica, remate, pase, tiro: `0` no · `1` sí |
| Cierre | 1 byte | `00` |

Los campos *(BD)* solo existen si el equipo tiene base de datos (el byte `0x2A` de la cabecera vale `0`). En un equipo sin ella, la ficha salta del puesto directamente a las medias. Es exactamente la trampa de 5.0 y 6.0: si lees los campos de base de datos donde no los hay, te comes las medias y el jugador siguiente, y sale basura creíble.

## Un ejemplo, byte a byte

Así se ven algunos campos de la parte de base de datos:

| Bytes | Campo | Valor |
|---|---|---|
| `16 09 4C` | Fecha | 22 de septiembre del 76 |
| `B7 52` | Altura y peso | 183 cm, 82 kg |
| `D0 07` | Precio | 2.000 millones (byte bajo primero) |

El año va **en un solo byte y con dos cifras**: `0x4C` es 76. No es 1976 en dos bytes como en 5.0.

### El campo «internacional» es un texto

Despista porque parece un número, pero es una cadena normal, con su byte de longitud y cifrada:

| Bytes | Se lee |
|---|---|
| `01 51` | «0» |
| `02 58 59` | «98» |
| `02 32 28` | «SI» |
| `02 2F 2E` | «NO» |

Así que puedes poner un número o un sí/no, y crecer o encoger el campo como cualquier otro texto.

## Las medias y las habilidades

Al final de la ficha hay ocho bytes, y aquí está la diferencia gorda con las versiones posteriores:

- Los **cuatro primeros son medias** de 0 a 99: velocidad, resistencia, agresividad y calidad.
- Los **cuatro siguientes no son medias**: son habilidades especiales que el jugador tiene o no tiene. Técnica, remate, pase y tiro, cada una con `0` o `1`.

Si los lees como ocho medias, te salen jugadores con «remate 1» y «pase 0» y parece que la base esté rota. No lo está: ese jugador tiene remate y no tiene pase.

La media que se enseña se calcula a partir de las cuatro medias; no hay un campo con ella. Si el juego le añade forma y moral como hace 5.0, está sin confirmar.

## La posición en la plantilla

Igual que en 5.0 y 6.0, no es la alineación dibujada: es el **orden** del jugador dentro del plantel, y cada valor solo puede usarlo un jugador del equipo. Va repetido dos veces en la ficha; mantenlas iguales.

En los ficheros de fábrica **no aparece el `99`** de «fuera del plantel» ni la situación «baja» de 5.0 y 6.0: la posición va de 1 a 40 y la situación solo toma `0`, `1` o `2`.

Según los tutoriales de la comunidad, el juego admite plantillas de **12 a 37 jugadores**. Por debajo o por encima, está sin confirmar qué pasa exactamente; no te salgas.

## Si añades un jugador

Un jugador nuevo en un equipo con base de datos necesita **todos** sus textos, aunque sean de relleno. Con el lugar de nacimiento, el equipo de procedencia o el campo de internacional vacíos el juego puede colgarse. Lo seguro es poner un `-` en los dos primeros y un `0` en el de internacional. El comentario sí puede ir vacío (`00 00`).

El puntero tiene que ser único en todo el juego, no solo en el equipo.

## Las tablas

### Demarcaciones

Los códigos son **los mismos que en 5.0 y 6.0** (ver [las tablas de 5.0 y 6.0](v56-tablas.html)). Aquí van con los nombres que usa la documentación de la 4.0: volante, marcador, interior.

| Código | Demarcación |
|---|---|
| 0 | *(vacía)* |
| 1 | Portero |
| 2 | Lateral derecho |
| 3 | Lateral izquierdo |
| 4 | Líbero |
| 5 | Central izquierdo |
| 6 | Central derecho |
| 7 | Volante derecho |
| 8 | Interior derecho |
| 9 | Delantero centro |
| 10 | Volante tapón |
| 11 | Volante izquierdo |
| 12 | Extremo derecho |
| 13 | Media punta por el centro |
| 14 | Extremo izquierdo |
| 15 | Marcador central defensivo |
| 16 | Media punta derecha |
| 17 | Media punta izquierda |
| 18 | Interior izquierdo |

Dos reglas para las secundarias: **no repitas la principal** y **no pongas el `1`** (portero) como secundaria de un jugador de campo.

### Pelo

| Código | Pelo |
|---|---|
| 0 | Rubio |
| 1 | Sin pelo |
| 2 | Moreno |
| 3 | Canoso |
| 4 | Pelirrojo |
| 5 | Castaño |

Fíjate en que empiezan en `0`, no en `1` como en 5.0 y 6.0. Lo mismo pasa con la piel: en la 4.x los tres tonos son `0`, `1` y `2`. Si portas datos de una versión a otra, resta o suma uno.

### Los países

El byte de país del equipo usa esta tabla:

| Código | País | Código | País |
|---|---|---|---|
| `01` | Albania | `16` | Islas Feroe |
| `02` | Alemania | `18` | Israel |
| `03` | Austria | `19` | Italia |
| `04` | Bélgica | `1A` | Lituania |
| `05` | Bielorrusia | `1B` | Luxemburgo |
| `06` | Bulgaria | `1C` | Malta |
| `07` | Croacia | `1D` | Noruega |
| `09` | Chipre | `1F` | Polonia |
| `0A` | Dinamarca | `20` | Portugal |
| `0B` | Escocia | `22` | Rumanía |
| `0C` | Eslovaquia | `23` | Rusia |
| `0D` | Eslovenia | `24` | Suecia |
| `0E` | España | `25` | Suiza |
| `0F` | Finlandia | `26` | Turquía |
| `10` | Francia | `27` | Ucrania |
| `11` | Grecia | `28` | Yugoslavia |
| `12` | Países Bajos | `29` | Argentina |
| `13` | Hungría | | |
| `14` | Inglaterra | | |

El `20` es **Portugal**: ahí están el Oporto, el Benfica y el Sporting. Alguna tabla antigua lo da como República Checa, y el motivo es curioso: **la base agrupa países**. En el `20` hay también clubes checos e irlandeses; en el `14`, ingleses y norirlandeses; en el `16`, islandeses y feroeses; en el `1D`, noruegos y galeses. El juego sí tiene esos países por separado en su propia lista, pero la base los mete donde no van y no hay código propio para ellos.

Y el `28` es **Yugoslavia**, no Serbia: así lo llama el juego y así se llamaba en 1995.
