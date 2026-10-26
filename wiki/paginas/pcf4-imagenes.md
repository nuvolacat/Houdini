# Escudos, fotos y camisetas en 4.0 y 4.5

Los formatos de imagen de la 4.x: los `.DFG` de la base de datos, el escudo del partido en `.EMP` y las camisetas del partido en `EQUIPOS.DAT`. Todo son ficheros sueltos; no hay contenedor que abrir.

## Los `.DFG`: 16 colores en planos de bits

Todos los escudos, fotos y camisetas de la base de datos son `.DFG` de **16 colores**. Y no se guardan píxel a píxel, sino **en planos de bits**, como se hacía en las tarjetas gráficas de la época.

La idea es esta: el color de cada píxel es un número de 0 a 15, que son cuatro bits. En lugar de guardar los cuatro bits juntos, el fichero guarda **cuatro imágenes de un bit**, una por cada bit del número. Para saber el color de un píxel coges su bit en cada uno de los cuatro planos y los juntas.

### La cabecera de dimensiones

Todos los `.DFG` tienen esta cabecera de 8 bytes en algún sitio:

| Posición | Tamaño | Qué es |
|---|---|---|
| +0 | 1 byte | `01` |
| +1 | 2 bytes | Ancho |
| +3 | 2 bytes | Alto |
| +5 | 1 byte | Número de planos: siempre `04` |
| +6 | 2 bytes | `00 00` |

### Los píxeles

Detrás de la cabecera, **fila a fila**. Cada fila son cuatro tramos de `⌈ancho / 8⌉` bytes: primero el plano 0, luego el 1, el 2 y el 3. Dentro de cada byte, **el bit más alto es el píxel de la izquierda**.

```
color = bit(plano 0) + 2·bit(plano 1) + 4·bit(plano 2) + 8·bit(plano 3)
```

La imagen termina con un byte `FF`.

Hay dos variantes, según dónde esté la paleta.

### Con paleta fija: escudos y fotos pequeños

`MINIESC`, `MINIFOTO` y `CAMISAS` empiezan directamente por la cabecera de dimensiones. **La paleta no va en el fichero**: es fija y la pone el juego. Hay dos:

- una para los **escudos pequeños** (`MINIESC`),
- otra para las **fotos pequeñas y las camisetas** (`MINIFOTO`, `CAMISAS`).

Las dos empiezan por el negro y acaban en grises y blanco. En la de escudos el **15 es blanco**, y es el fondo: el escudo se pinta sobre recuadro blanco. En la de camisetas, el fondo es el **13, un gris** (`9A 9A 9A`) que casa con el de la ficha del club.

Si haces un escudo con fondo transparente y lo conviertes sin más, el transparente acaba en negro. Compón antes el dibujo sobre el color de fondo que toque.

### Con paleta propia: las imágenes grandes

`BIGESC`, `BIGFOTO` y las fotos de estadio de `BIGCAMP` llevan **su propia paleta** delante:

| Posición | Tamaño | Qué es |
|---|---|---|
| 0 | 2 bytes | `00 10` |
| 2 | 48 bytes | La paleta: 16 colores de tres bytes (rojo, verde, azul), de 0 a 255 |
| 50 | 8 bytes | La cabecera de dimensiones |
| 58 | … | Los planos de bits y el `FF` final |

Como cada imagen tiene su paleta, aquí sí puedes elegir los 16 colores que mejor le vayan a tu foto. Para las fotos ayuda el tramado; para los escudos, no: con tan pocos colores, el tramado llena un escudo plano de puntitos.

**Las medidas mandan desde la cabecera.** La foto grande de jugador mide **124 × 182**. Los escudos grandes y las fotos de estadio cambian de un fichero a otro; el juego las lee de la cabecera. Al sustituir una foto de estadio, respeta las medidas del original.

## El escudo del partido: `ESCUDOS\EQ95NNNN.EMP`

Es otro fichero distinto del escudo de la ficha, y tiene otro formato: **256 colores, un byte por píxel**.

| Parte | Tamaño | Qué es |
|---|---|---|
| Cabecera | 24 bytes | Consérvala del original |
| Píxeles | ancho × alto | Un byte por píxel, en un orden especial |
| Cola | 4 bytes | Consérvala también |

Las medidas no van escritas: se deducen del tamaño del fichero.

| Tamaño del fichero | Medidas | Edición |
|---|---|---|
| 3.408 bytes | **52 × 65** | La española |
| 1.468 bytes | 32 × 45 | La italiana (PC Calcio) |

**El orden de los píxeles** es lo que hace que salga basura si lo lees como una imagen normal. Se guardan **en cuatro pasadas por columnas**: en la primera, las columnas 0, 4, 8, 12…; en la segunda, las 1, 5, 9…; luego las 2, 6, 10… y por último las 3, 7, 11…. Dentro de cada pasada, fila a fila.

La paleta de 256 colores **no va en el fichero** ni es la VGA estándar: es la del simulador, la misma que usan las camisetas del partido. El índice `0` es el fondo.

## Las camisetas del partido: `PALETAS\EQUIPOS.DAT`

Un solo fichero con **bloques de 190 bytes**, uno por equipación:

| Posición | Tamaño | Qué es |
|---|---|---|
| 0 | 8 bytes | `90 51 52 53 54 55 56 3E`: un `90` y luego `QRSTUV>` en claro |
| 8 | 168 bytes | La textura de la camiseta: 24 × 7 colores de la paleta del simulador |
| 176 | 14 bytes | Un cierre fijo, igual en todos los bloques |

Cada equipo tiene **dos bloques seguidos**: el equipo número *N* tiene la primera equipación en el bloque `2·(N−1)` y la segunda en el `2·(N−1) + 1`. Para llegar al bloque, multiplica por 190.

Los 168 bytes **no son una imagen**: son una textura. El icono que dibuja el juego es de 20 × 20 píxeles y solo toma **37 de esas 168 posiciones**; cada píxel del icono sale de una posición concreta de la textura. Esa correspondencia está documentada por **pcnimdock** en FUTBOL_RELOAD. La posición 7 es el contorno negro (`0x60`) y no conviene tocarla.

Y solo es la camiseta: **no hay pantalón ni medias** en este fichero.

### Cómo se cambia el color

Como los bytes son índices de la paleta, la forma más sencilla de editar es **cambiar unos índices por otros**. La paleta está organizada en **degradados**: tramos de índices seguidos del mismo tono, del oscuro al claro. Una camiseta usa varios tonos de un mismo degradado para el sombreado.

Para pasar una camiseta de roja a azul sin perder el sombreado, cambia **todo el degradado**: el tono más oscuro del rojo por el más oscuro del azul, el siguiente por el siguiente, y así. Si cambias solo el índice más frecuente, te queda una camiseta azul con manchas rojas.
