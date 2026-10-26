# PCF 3.0: gráficos y sonido

Dónde están los escudos, las caras, las equipaciones y los sonidos de 3.0, cómo está hecha cada imagen por dentro y cómo sustituirlas sin mover ni un puntero.

## Los `.DGF`: escudos, estadios y caras

Son los contenedores que más te van a interesar. Empiezan con una firma en claro, `Copyright (c)1993,94 Dinamic Multimedia` —algunos arrancan directamente con la primera imagen—, y detrás vienen las imágenes **una tras otra, sin índice ni contador**.

Hay dos tipos:

| Fichero | Qué guarda |
|---|---|
| `LIG94951.DGF`, `LIG94952.DGF` | Por cada club de la división, su grupo de gráficos |
| `EQUIP/LIG1EQ00.DGF` …, `EQUIP/LIG2EQ00.DGF` … | Uno por equipo: las caras de sus jugadores |

### Cómo es una imagen

Cada imagen se describe a sí misma:

| Parte | Tamaño | Qué es |
|---|---|---|
| Marca | 2 bytes | `00 10` |
| Paleta | 48 bytes | **16 colores**, tres bytes cada uno (rojo, verde, azul) |
| Cabecera | 8 bytes | `01`, ancho (2 bytes), alto (2 bytes), `04 00 00` |
| Imagen | alto × 4 × ⌈ancho / 8⌉ | cuatro planos de bits por fila |
| Cierre | 1 byte | `FF` |

El `04` de la cabecera son los cuatro planos: cuatro bits por píxel, de ahí los 16 colores. En cada fila van los cuatro planos seguidos, cada uno de ⌈ancho / 8⌉ bytes, con el píxel de la izquierda en el bit más alto. El índice de color del píxel se forma con el bit del primer plano como bit 0, el del segundo como bit 1, y así.

Lo bueno de este formato es que **cada imagen lleva su propia paleta**. No hay una paleta común que respetar: cada escudo y cada cara tiene sus 16 colores.

Es el mismo formato de imagen que usa PC Fútbol 4.0 en sus fotos grandes y escudos grandes.

### El grupo de gráficos de un club

En el `.DGF` de la división, cada club tiene cuatro imágenes —tres en Segunda—, y **no van en el mismo orden en las dos divisiones**:

| División | Orden |
|---|---|
| Primera | escudo 48×64 · escudo grande · equipación 71×37 · estadio 200×140 |
| Segunda | escudo grande · escudo 48×64 · equipación 71×37 · *(sin estadio)* |

Si agrupas «desde un escudo pequeño hasta el siguiente», en Primera aciertas y en Segunda le das a cada club el escudo grande del siguiente. En Segunda, el escudo grande que va **justo antes** del pequeño es el suyo.

Las medidas: el escudo pequeño siempre es 48×64, la equipación 71×37 (en un par de clubes, 70×37) y el estadio 200×140. **El escudo grande cambia de un club a otro** —entre unos 105 y 140 de ancho y entre 150 y 180 de alto—, aunque cada club tiene el suyo fijo.

No recorras el `.DGF` por orden para saber qué gráficos son de quién: usa el **puntero al escudo** que va en la cabecera del club (está en [el bloque de equipo](pcf3-bloque-equipo.html)). Hay más grupos en el contenedor que clubes en la base, y el orden no siempre coincide.

### Las caras de los jugadores

En el `.DGF` de cada equipo, cada jugador tiene un **retrato de 24×24** y, si tiene foto, una **cara grande de 124×182** justo detrás.

El jugador las apunta con los dos primeros números de su bloque fijo (ver [la ficha](pcf3-ficha-jugador.html)): la posición de cada imagen dentro de este fichero, o `0` si no tiene. Usa esos punteros, no el orden: es el emparejamiento real.

En Primera, el retrato del entrenador es también un 24×24, hacia el final del fichero. En Segunda los entrenadores no tienen foto.

## Sustituir una imagen

Es lo más sencillo y lo más seguro: **escribe la imagen nueva con las mismas medidas que la vieja**. Como el tamaño en bytes depende solo de las medidas, ocupará exactamente lo mismo, el contenedor no cambiará de tamaño y ningún puntero —ni el del escudo, ni los de las caras— se moverá de sitio.

Reescala tu imagen a las medidas del hueco antes de convertirla. Y **hazle una paleta nueva** de 16 colores pensada para ella en vez de reaprovechar la que había: como cada imagen guarda la suya, no rompes nada, y una foto metida a la fuerza en los colores de otra sale con colores que no son. Recodificada así, una foto real a 16 colores queda sorprendentemente bien.

Un desplazamiento de un solo byte dejaría a todos los equipos de detrás apuntando a la imagen equivocada. Comprueba el tamaño antes de escribir.

## Añadir imágenes

A veces hace falta, por ejemplo al mover un club de división o un jugador de equipo: sus gráficos tienen que estar en el `.DGF` de destino.

Como el contenedor no tiene índice y el juego lo recorre imagen a imagen, **anexar al final es seguro**: la imagen nueva se alcanza siguiendo la ristra y no se mueve nada de lo que ya había. Pégala justo detrás de la última imagen y apunta a ella desde la ficha o el club.

Si el grupo de gráficos de un club ya está en el destino —porque ya lo llevaste allí antes—, **reutilízalo** en vez de anexar otra copia. Así, llevar un club y traerlo de vuelta deja los ficheros como estaban, y el contenedor no engorda con copias que nadie usa: cada grupo de club ocupa unos 28 KB.

## El escudo del partido: `1.EMP` … `20.EMP`

El escudo que se ve en el simulador no está en la base ni en el `.DGF`: son veinte ficheros sueltos de 48×51, **uno por club de Primera en el orden de la división**: `1.EMP` es el del primero. Segunda no tiene, porque no se juega.

Son del mismo tipo que las animaciones `.EMP` del simulador (correr, chutar, el balón…), que en total son 71. **Los `.EMP` no llevan paleta dentro**: la del juego está en `PALETA.BBM`.

## Los demás gráficos

| Fichero | Formato | Qué hay |
|---|---|---|
| `GFX00.DAT` | El de los gráficos de interfaz de 4.0, con paletas dentro | 455 imágenes y 24 paletas: iconos, botones y rótulos del manager |
| `PCFTEX.DAT` | **IFF ILBM**, el de Deluxe Paint | 49 imágenes: el arranque y el actualizador por módem |
| `PALETA.BBM`, `PAL1.BBM` … | IFF de Deluxe Paint | Las paletas del juego |
| `FONDOS.EMF`, `FONDOS1.EMF` | Fondos por baldosas | Sin documentar |

Con `GFX00.DAT` hay una trampa: trae 24 paletas, y si pintas todas las imágenes con la primera, medio contenedor sale con colores que no son. No se ha encontrado dónde dice cada imagen qué paleta usa; lo práctico es elegir para cada una la que mejor le encaje.

Si sustituyes una imagen de estos contenedores, la regla es la misma de siempre: mismas medidas, mismo tamaño en bytes.

## Los rótulos: `PCFRES00.GRC`

Los 143 textos que el juego pinta por pantalla. Cada uno lleva delante un descriptor de seis números de dos bytes —tipo, dos parámetros, la x y la y en pantalla, y la longitud— y luego el texto, con **el mismo cifrado que las bases** (ver [el texto](pcf3-texto.html)).

El hueco de cada rótulo es fijo: rellena con espacios y no alargues.

## El sonido: Creative Voice

Los once sonidos están **en la raíz** de la carpeta del juego, y son **Creative Voice** (`.VOC`), el formato estándar de las Sound Blaster. Cualquier programa de audio de la época los abre.

```
«Creative Voice File» + 1A          20 bytes
[posición de los datos] [versión] [comprobación]     2 bytes cada uno
bloques: [tipo, 1 byte] [tamaño, 3 bytes] [datos]
```

Los tipos de bloque que aparecen:

| Tipo | Qué es |
|---|---|
| 1 | Sonido: constante de tiempo, compresión y el audio en **8 bits sin signo, mono** |
| 8 | Cabecera extendida que va antes de un bloque 1 y da la frecuencia con más precisión |
| 6 y 7 | Principio y fin de un **bucle** |
| 0 | Fin |

En el bloque 1, la frecuencia es `1.000.000 / (256 − constante)`.

| Fichero | Qué es | Frecuencia |
|---|---|---|
| `V08AMBI` | ambiente del público | 8.000 Hz |
| `V08GOL` | gol | 8.000 Hz, **en bucle ×3** |
| `V08OE`, `V08OOH` | el público | 8.000 Hz |
| `V11CHUT` `V11ENTRA` `V11FALTA` `V11PEPIN` `V11POSTE` | jugadas | 11.000 Hz |
| `V11FIN` | final del partido | **13.000 Hz, en bucle ×3** |
| `V11SILBA` | silbato | **13.000 Hz** |

Dos trampas al sustituirlos:

1. **El nombre miente sobre la frecuencia.** El prefijo `V08` o `V11` parece decirla, pero el final y el silbato están a 13 kHz. Léela del fichero y graba el sonido nuevo a la misma, o sonará desafinado.
2. **Respeta los bucles.** El gol y el final repiten su sonido tres veces con bloques 6 y 7. Si los quitas, el gol suena una sola vez.

Y un detalle de precisión: con solo el bloque 1, la constante es de un byte y 13.000 Hz se quedan en 12.987. Escríbelos como el juego, con un bloque 8 delante del 1.
