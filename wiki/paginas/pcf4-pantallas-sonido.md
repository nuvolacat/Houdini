# Pantallas, animaciones y sonido en 4.0 y 4.5

Los gráficos de la interfaz (`GFX*.DAT`), los textos de los menús (`.GRC`), los fondos por baldosas, las animaciones del partido, las pantallas del arranque y los efectos de sonido. Cinco formatos distintos, todos sin compresión salvo uno.

## Iconos, trofeos y logos: `GFX01.DAT` … `GFX06.DAT`

Seis contenedores con los trofeos, botones, iconos, marcadores, los logos del juego y los rótulos de las competiciones europeas.

| Fichero | Imágenes | Paletas dentro |
|---|---|---|
| `GFX01.DAT` | 22 | Sí |
| `GFX02.DAT` | 227 | Sí |
| `GFX03.DAT` | 86 | Sí |
| `GFX04.DAT` | 115 | Sí |
| `GFX05.DAT` | 275 | **No** |
| `GFX06.DAT` | 1 | **No** |

No hay índice: las imágenes y las paletas van una detrás de otra y se encuentran por su forma.

### Las imágenes

Cada una empieza con **la misma cabecera de 8 bytes que los `.DFG`** de la base de datos: `01`, ancho (2 bytes), alto (2 bytes), `04`, `00 00`. Detrás, los píxeles en el mismo formato: 16 colores en cuatro planos de bits, fila a fila, con el bit alto a la izquierda (ver [las imágenes](pcf4-imagenes.html)). La más grande mide 640 × 365.

### Las paletas

Bloques de 51 bytes: `00 10`, 48 bytes de color (16 × rojo, verde, azul) y un `FF`. Los valores son los de la VGA, de 6 bits, pasados a 8: son `0` o terminan en binario `11`. Esa regularidad es lo que permite reconocerlos en medio del fichero.

**El fichero no dice qué paleta usa cada imagen**: lo decide el código del juego. Lo razonable es empezar probando con la primera de su fichero. Una excepción documentada por pcnimdock: el rótulo grande de `GFX02` con el logo de Dinamic (las imágenes que caen más o menos entre los bytes 380.000 y 530.000) usa la novena paleta del mismo fichero.

`GFX05` y `GFX06` no llevan ninguna. Sus imágenes se pintan con paletas de los otros cuatro, y cuál exactamente está sin confirmar: prueba hasta que la imagen se vea con sentido.

Editar es sustituir píxeles con las mismas medidas. Así el tamaño no cambia y nada se mueve.

## Los textos de los menús: `RES*.GRC`

Uno por programa: el del juego, el del modo manager y el del Pro Manager (llevan `PCFUT`, `PCMAN` y `PROMG` en el nombre).

Empiezan con una cabecera de texto en claro, la presentación del fichero, que termina en un byte `1A`. Detrás van los objetos de la interfaz. Los que llevan texto tienen delante un descriptor de **12 bytes**, seis números de dos bytes:

| Número | Qué es |
|---|---|
| 1 | Tipo de objeto |
| 2-3 | Parámetros |
| 4-5 | Posición en pantalla (x, y) |
| 6 | Longitud del texto |

Y detrás, el texto con el cifrado posicional explicado en [el texto](pcf4-texto.html): `carácter[i] = byte[i] XOR (0xC0 + longitud + i)`.

Los textos van **en mayúsculas** y tienen sitio fijo. Edita en el sitio: recorta lo que sobre o rellena con espacios hasta la longitud original.

## Los fondos de pantalla: baldosas

Los fondos no son imágenes enteras. Se montan con **baldosas de 16 × 16** a partir de tres ficheros de `GRAFICOS`:

| Fichero | Qué es |
|---|---|
| `PALETA.BBM` | La paleta de 256 colores, en formato IFF (bloque `CMAP`) |
| `FON_*.BLO` | Las baldosas: 256 bytes cada una, sin cabecera |
| `MAP_*.BIN` | El mapa: qué baldosa va en cada sitio |

**El mapa** es una rejilla de **128 × 48** casillas, cada una de dos bytes. Los 15 bits bajos son el número de baldosa; el bit alto dice si la baldosa va **en espejo** horizontal. Montado entero da un lienzo de 2.048 × 768, del que el juego enseña solo una parte; el resto es relleno.

**Cada baldosa** guarda sus píxeles en el orden de la VGA de la época («modo X»): primero las columnas 0, 4, 8 y 12; luego las 1, 5, 9 y 13; y así. El píxel (x, y) de una baldosa está en

```
inicio + (x mod 4)·64 + y·4 + (x div 4)
```

Al hacer un fondo nuevo, aprovecha lo mismo que el original: si una baldosa ya existe, o existe su espejo, no la repitas; apunta a ella desde el mapa.

## Las animaciones del partido: `GRAFICOS\*.EMP`

155 ficheros con más de 5.100 fotogramas: los jugadores andando y chutando, las tarjetas, el balón. No confundir con el `.EMP` del escudo, que está en `ESCUDOS` y es otro formato.

- **Cabecera de 16 bytes.** Si su segundo byte es `41`, los descriptores de fotograma son de 8 bytes; si no, de 6.
- **Cada fotograma**: un descriptor y cuatro planos.
  - Descriptor: bytes por fila **más uno** (2 bytes), alto (2 bytes), tamaño de cada plano (2 bytes) y, en la variante de 8, dos bytes a cero.
  - Cuatro planos en «modo X», como las baldosas: el plano *p* tiene las columnas *p*, *p*+4, *p*+8… El ancho es cuatro veces los bytes por fila.
- **El índice 0 es transparente.**
- Entre fotograma y fotograma puede haber unos pocos bytes de relleno de alineación.

El primer fotograma no está en una posición fija tras la cabecera. Lo fiable es probar a empezar en distintos puntos y quedarte con el recorrido que consume el fichero entero.

Para editar, sustituye los píxeles de un fotograma con sus mismas medidas.

## Las pantallas del arranque: `PCFTEX4.DAT`, `PCFTEX.DAT`, `LGR.DAT`

Aquí está el rótulo «PC FUTBOL 4.0» del programa de arranque. Están en la raíz del juego; si no los tienes, cópialos de tu CD del juego.

No usan nada propio de Dinamic: son varias imágenes **IFF ILBM** (el formato de Deluxe Paint) **puestas una detrás de otra**, 110 en total. Cada una es un bloque `FORM` que dice su propio tamaño, así que se recorren en orden sin necesidad de índice. El fichero `.GLL` que las acompaña es una paleta.

Dentro de cada imagen:

- `BMHD`: ancho, alto, número de planos y compresión. **Estos números van con el byte alto primero**, al revés que en el resto del juego: es el convenio del formato IFF.
- `CMAP`: la paleta, 16 colores.
- `BODY`: los planos de bits, fila a fila. Cada fila de cada plano ocupa un número par de bytes. Con compresión `1`, van comprimidos en ByteRun1, el método de Deluxe Paint.

Un truco para sustituir una imagen sin mover nada: comprime la nueva y, si queda más corta que la original, rellena hasta la longitud original con bytes `80`, que en ByteRun1 significan «no hacer nada». Si no cabe, rehaz ese `FORM` con su tamaño nuevo; como cada uno anuncia su tamaño, el resto se sigue leyendo bien.

## Los efectos de sonido: `SONIDOS\*.RAW`

Lo más sencillo de todo el juego: **audio sin cabecera**.

| | |
|---|---|
| Muestras | 8 bits **sin signo** |
| Canales | Uno |
| Frecuencia | 11.025 Hz |
| Silencio | `80` |

La frecuencia no está escrita en ningún sitio; la fija el juego. Si lo abres en un editor de audio como datos en bruto con estos parámetros, suena bien a la primera. Para meter un sonido propio, pásalo a ese formato exacto antes de copiarlo.

En las carpetas de datos de la 4.x no hay ficheros de música.
