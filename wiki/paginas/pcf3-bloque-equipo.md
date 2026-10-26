# PCF 3.0: el bloque de equipo

Cómo está organizada una base de Liga de 3.0: una cabecera corta, un bloque por equipo uno detrás de otro y, dentro de cada bloque, la cabecera del club, el entrenador y las fichas. Nada de esto está marcado: hay que deducirlo de la forma.

## El fichero entero

```
firma «Copyright (c)1994 DINAMIC MULTIMEDIA» + resto de la cabecera
bloque del equipo 1
bloque del equipo 2
…
```

La cabecera mide **48 bytes en Primera y 81 en Segunda**: la de Segunda trae además un campo de 32 caracteres. Seis bytes después del final de la palabra `MEDIA` de la firma hay un número de dos bytes que **declara cuántos equipos hay**: 20 en cada división.

Úsalo como comprobación, no como guía. Las Estrellas Mundiales, que van al final de Primera, no cuentan en ese 20.

Lo importante es lo que **no** hay: la cabecera no trae ninguna tabla con la posición de cada equipo. Se han buscado los inicios de todos los bloques dentro de ella, como números de dos y de cuatro bytes, y no aparece ninguno. El juego recorre el fichero de principio a fin.

Y los bloques **teselan** el fichero: cabecera más bloques concatenados da el fichero original, byte a byte, sin huecos ni sobrantes. Eso es lo que permite sacar un bloque entero y ponerlo en otro sitio.

## Cómo reconocer cada cosa

El fichero no tiene marcas de inicio de equipo ni de jugador. Lo que sí tiene es una forma muy regular, y con tres reglas se camina entero:

1. **Un jugador** son dos textos **pegados**, sin un solo byte entre ellos —el apodo y el nombre completo—, seguidos de 13 bytes que encajan: dos números de cuatro bytes razonables, un dorsal que no pasa de 99 y una demarcación que no pasa de 3. El detalle está en [la ficha del jugador](pcf3-ficha-jugador.html).
2. **La cabecera de un club** empieza por una pareja de textos pegados que **no** es un jugador.
3. **Un equipo sin cabecera** —solo las Estrellas Mundiales— se detecta porque el bloque de medias del último jugador deja de ir pegado al jugador siguiente.

La regla vieja, «un equipo empieza en un nombre largo que lleva `\`», parece funcionar y no lo hace: hay clubes cuyo nombre largo no lleva barra, y entonces sus jugadores se pegan al equipo anterior y salen plantillas de cuarenta y tantos.

## La cabecera del club

Los campos de texto van en este orden, y lo que la hace reconocible es que **los huecos binarios entre ellos son de tamaño fijo**:

| Campo | Bytes entre el anterior y este | Ejemplo |
|---|---|---|
| Nombre oficial | — | *opcional*; va pegado al corto |
| Nombre corto | 0 (pegado) | |
| Nombre largo | 0 (pegado) | `FUTBOL CLUB\BARCELONA` |
| Estadio | **19** | |
| Presidente | **12** | |
| Patrocinador | **4** | |
| Marca de ropa | 0 (pegado) | |
| Clave | **10** | `BARCELONA` |
| Entrenador | — | ver más abajo |

La barra `\` del nombre largo marca dónde parte la línea el juego al pintarlo.

**No todos los clubes traen todos los campos.** Hay alguno sin presidente, por ejemplo. Por eso los huecos sirven para **etiquetar** cada campo, no para delimitarlos: a cada texto se le da la primera etiqueta pendiente cuyo hueco coincida, y se descartan las que se han saltado. Cuando un texto no casa con ninguna, se acabó la cabecera.

Sobre el último campo: **no es la ciudad**, aunque lo parezca. En Primera es una clave en mayúsculas —`MADRID`, `ATHLETIC`— y en Segunda todos los clubes llevan la misma.

## Lo que hay en los huecos

Los huecos de tamaño fijo no son relleno. Esto es lo que se sabe de cada uno:

### Entre el nombre largo y el estadio (19 bytes)

| Posición | Tamaño | Qué es |
|---|---|---|
| 0 | 4 bytes | **Puntero al escudo** dentro del `.DGF` de la división |
| 4 | 4 bytes | otro puntero, sin identificar |
| 8 | 4 bytes | otro puntero, sin identificar |
| 12 | 2 + 2 + 1 bytes | tres valores, sin confirmar |
| 17 | 2 bytes | **Año de fundación** |

El año de fundación cuadra con la historia de cada club en todos los casos comprobados. Los tres valores de la posición 12 son iguales en cada filial y su primer equipo; se sospecha que tienen que ver con la equipación, pero está sin confirmar.

El puntero del escudo es lo único del bloque que apunta fuera del fichero, y es lo que hay que tocar si mueves el equipo de división (ver más abajo).

### Entre el estadio y el presidente (12 bytes)

| Posición | Tamaño | Qué es |
|---|---|---|
| 0 | 4 bytes | un puntero, sin identificar |
| 4 | 4 bytes | **Aforo** |
| 8 | 4 bytes | **Socios** |

### Entre el presidente y el patrocinador (4 bytes)

El **presupuesto**, en millones de pesetas.

Los tres son números de cuatro bytes en un sitio fijo: se cambian sin mover nada. Y cuadran con la realidad de la época, que es la mejor prueba de que se están leyendo bien: los dos grandes por encima de 7.000 millones de presupuesto, la mayoría de Primera en torno a mil, y Segunda entre 127 y algo más de 500.

Si un club no tiene presidente, el hueco de 12 bytes no se puede localizar por esta vía y te quedas sin esos tres datos.

### Entre la marca y la clave (10 bytes): la equipación del partido

```
[patrón] [R G B pantalón] [R G B camiseta 1] [R G B camiseta 2]
```

Es la equipación con la que el simulador pinta a los jugadores. Los colores son **VGA de 6 bits**: de 0 a 63, no de 0 a 255, y no son índices de una paleta sino el color directamente. Si escribes un valor por encima de 63, el juego no lo va a interpretar como esperas.

La prueba de que son colores de verdad y no una tabla fija: hay clubes con colores que no son puros, como un violeta `(45, 24, 39)`.

El **patrón** vale 0 en casi todos los clubes. Vale 1 en el único club con banda diagonal y 2 en otro más; el significado exacto de cada valor está sin confirmar.

No confundas esta equipación con la de la ficha del club, que es un dibujo de 71×37 guardado en el `.DGF`. Esta es la del partido; aquella, la de la base de datos.

## El entrenador

Va **siempre detrás de la cabecera del club** y antes del primer jugador. Tiene dos formas:

- Una pareja pegada, apodo y nombre completo, como un jugador.
- **Un nombre suelto**, sin nombre completo.

Precisamente porque la pareja tiene la misma pinta que un jugador, es fácil que un lector se lo trague como el primero de la plantilla. Reclámalo por posición: lo que va justo detrás de la clave es el técnico.

Algunos clubes encadenan **más de un técnico**, cada uno con sus declaraciones. El del equipo es el **primero**.

## Las Estrellas Mundiales

Detrás del último club de Primera hay un equipo que no es un club: una selección de estrellas internacionales de la época. Su cabecera es corta y distinta:

```
[nombre]   «Estrellas Mundiales»
[clave]
   … unos 270 bytes …
«Comentario»
[jugadores]
```

Sin nombre largo, estadio, presidente ni entrenador, y con sus campos **sin pegar** entre sí.

Dos avisos para quien escriba un lector:

- **Ese relleno de unos 270 bytes da falsos positivos** si buscas el bloque de medias del jugador anterior hacia atrás. Para saber dónde acaba el último club, busca su bloque de medias **hacia delante** desde su nombre, exigiendo que sea el último de la plantilla.
- **No trates a las Estrellas como un club.** Si tu herramienta sustituye plantillas por la de un club real, déjalas fuera: no tienen cabecera de club y escribir encima las destruye.

El mismo tipo de equipo, con una cabecera muy parecida, está documentado por pcnimdock en FUTBOL_RELOAD para PC Fútbol 4.5.

## La cola del bloque

Entre el bloque de medias del último jugador y el principio del equipo siguiente quedan **de 0 a 37 bytes**. Consérvalos tal cual.

## Mover un equipo de división

Como la división la da el fichero, mover un club de Segunda a Primera es, literalmente, **llevarse su bloque al otro fichero**. Las tres cosas que lo hacen posible:

1. Los bloques teselan el fichero, así que se pueden sacar y meter enteros.
2. No hay tabla de offsets que actualizar.
3. Las actas de los partidos se refieren a los equipos **por plaza**, no por nombre. Por eso lo sensato es **intercambiar** dos equipos, cada uno a la plaza del otro, y no añadir ni quitar.

Lo único que no viaja solo son **los gráficos**:

- **El escudo, el escudo grande, la equipación de la ficha y la foto del estadio** están en el `.DGF` de su división, y el bloque los apunta con el puntero de la cabecera. En el otro fichero ese puntero no vale. Hay que copiar el grupo de gráficos del equipo al `.DGF` de destino y cambiar el puntero. Cómo, sin romper nada, está en [gráficos y sonido](pcf3-graficos.html).
- **Las caras de los jugadores** están en un `.DGF` por equipo cuyo nombre lleva la plaza. Al intercambiar dos equipos, se intercambian también esos dos ficheros.

Todo esto está comprobado sobre los ficheros; que el juego lo acepte está sin confirmar.

Ojo con una cosa que no es del formato sino del juego: como el manager solo juega la Primera, subir un equipo a Primera sí cambia lo que juegas, pero bajarlo a Segunda lo saca de la partida.
