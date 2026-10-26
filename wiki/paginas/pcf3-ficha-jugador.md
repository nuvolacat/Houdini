# PCF 3.0: la ficha del jugador

Campo a campo, cómo guarda 3.0 a cada jugador: dos nombres, un bloque fijo de 13 bytes, el lugar y la fecha de nacimiento, sus textos y, al final, las cuatro medias. Y por qué el once no está donde lo buscarías.

## La ficha, en orden

| Campo | Tamaño | Qué es |
|---|---|---|
| Apodo | texto | el que se ve en las alineaciones |
| Nombre completo | texto | **pegado** al apodo, sin un byte entre los dos |
| Bloque fijo | 13 bytes | todo lo de la tabla siguiente |
| Lugar de nacimiento | texto | empieza justo detrás del bloque fijo |
| Fecha de nacimiento | 3 bytes | día, mes y año menos 1900, pegados al lugar |
| Textos de base de datos | texto | procedencia, comentario y biografía, con datos binarios entre medias |
| Bloque de medias | 12 bytes | el valor, las cuatro medias y el byte de cierre |

Los textos van como todos los de la base: un byte de longitud y el texto cifrado. Está en [la página del texto](pcf3-texto.html).

A diferencia de 5.0 y 6.0, **aquí no hay marca de inicio de ficha ni puntero de jugador**. Una ficha se reconoce por la forma: dos textos pegados seguidos de 13 bytes que encajan.

## El bloque fijo de 13 bytes

| Posición | Tamaño | Campo | Valores |
|---|---|---|---|
| 0 | 4 bytes | Cara grande | posición de la foto de 124×182 en el `.DGF` del equipo; `0` = no tiene |
| 4 | 4 bytes | Cara pequeña | posición del retrato de 24×24; `0` = no tiene |
| 8 | 1 byte | **Dorsal** | `99` = sin dorsal |
| 9 | 1 byte | **Situación** | `0` nada · `1` NF, nuevo fichaje · `2` AS, ascendido del filial · `3` BJ, baja |
| 10 | 1 byte | Posición fina | dentro del puesto; ver más abajo |
| 11 | 1 byte | **Banderas** | bit 0 = extranjero |
| 12 | 1 byte | **Puesto** | `0` portero · `1` defensa · `2` medio · `3` delantero |

Todos son de tamaño fijo: **se cambian sin mover nada** del fichero.

### La situación

Las siglas están escritas en claro dentro del programa principal, tal cual: `NF=Nuevo Fichaje   AS=Ascendido del filial   BJ=Baja`. Son las que el juego pinta junto al nombre en la plantilla.

Cuadran con los movimientos reales del verano del 94: los fichajes de cada club llevan NF, los canteranos que subieron ese año llevan AS y los que se marcharon durante la temporada, BJ.

### Las banderas

El **bit 0 marca al extranjero**. Lo llevan 132 de las 959 fichas, y son exactamente los jugadores de fuera: ningún español lo lleva.

El **bit 4** lo llevan unos pocos jugadores españoles nacidos fuera, y también algunos extranjeros junto con el bit 0. Podría marcar al oriundo o nacionalizado, pero está **sin confirmar**.

**3.0 no guarda la nacionalidad**, solo esa bandera. Si quieres saber de dónde es un extranjero, el único sitio es el lugar de nacimiento: el juego suele poner el país entre paréntesis, como en `Zaandam (Holanda)`. Si no lo pone, no hay más dato.

### La posición fina

Afina el puesto: dentro de los defensas, distingue laterales derechos de izquierdos, centrales y líberos. Los porteros llevan `0`. Se sabe que `1` es lateral derecho y `2` lateral izquierdo, y que los valores son coherentes de un equipo a otro; la tabla completa está **sin confirmar**.

## La fecha de nacimiento

Tres bytes pegados detrás del lugar de nacimiento:

```
[día] [mes] [año − 1900]
```

**No la busques contando campos.** Localiza el lugar de nacimiento —el texto que empieza exactamente en el byte siguiente al bloque fijo— y la fecha va justo detrás de él. Si cuentas «el tercer texto de la ficha», en cuanto tu lector se salte un campo leerás tres bytes de cualquier sitio y te saldrán fechas como el mes 0 del año 2070.

Las 959 fichas tienen lugar y fecha. Dos cosas a tener en cuenta:

- **El mes puede valer `99`**, que significa desconocido, con el día y el año bien puestos. Es la misma convención que el dorsal 99. No descartes la fecha entera por eso.
- **Hay una ficha con un año imposible** para un jugador en activo en 1994. Es un error del propio juego.

## El bloque de medias

Cierra la ficha. Doce bytes, sin cifrar:

| Posición | Tamaño | Qué es |
|---|---|---|
| 0 | 2 bytes | **Valor** de mercado; la unidad está sin confirmar |
| 2 | 1 byte | **Velocidad** |
| 3 | 1 byte | **Resistencia** |
| 4 | 1 byte | **Agresividad** |
| 5 | 1 byte | **Calidad** |
| 6-9 | 4 bytes | valores pequeños, de 0 a 15; sin identificar |
| 10 | 1 byte | siempre `0` |
| 11 | 1 byte | **Hay más**: `1` si detrás viene otro jugador del mismo equipo, `0` si es el último |

En 3.0 hay **cuatro medias**, no diez: no existen el regate, el remate, el pase, el tiro, las entradas ni la de portero que verás en 5.0 y 6.0. Van de 1 a 99.

### Cómo encontrarlo

La ficha acaba en este bloque y la siguiente empieza justo detrás, sin nada en medio. Así que el bloque de medias de un jugador son **los 12 bytes anteriores al apodo del jugador siguiente**.

Para comprobar que lo has encontrado bien, todo tiene que cumplirse a la vez: el byte 10 vale 0, el 11 vale 0 o 1, las cuatro medias están entre 1 y 99 y los bytes 6 a 9 no pasan de 15.

Con el **último** jugador de un equipo no basta con eso: detrás viene la cola del bloque y luego la cabecera del equipo siguiente. Busca el bloque **hacia delante** desde el nombre del jugador y exige que el último byte valga 0. Hacia atrás, el relleno de algunas cabeceras —el de las Estrellas Mundiales sobre todo— da falsos positivos.

## Cuántos jugadores tiene un equipo

**No hay contador en ninguna parte.** El juego lee fichas hasta que encuentra una cuyo último byte vale 0.

Las fichas teselan el bloque del equipo: cabecera del club, fichas una detrás de otra y una cola corta. Así que **añadir o quitar un jugador** es recolocar fichas enteras y dejar bien ese último byte: `1` en todas menos en la última. No hay ningún número que actualizar.

Lo que no viaja con la ficha son **las fotos**. Los dos punteros del bloque fijo apuntan al `.DGF` de su equipo; si llevas al jugador a otro equipo, hay que copiar sus dos imágenes al `.DGF` del destino y cambiar los punteros. Cómo hacerlo sin desplazar nada está en [gráficos y sonido](pcf3-graficos.html).

## El once: lo decide el dorsal

Aquí es donde más se equivoca quien viene de 5.0. **La plantilla no está guardada en orden de titularidad, sino por puesto**: porteros primero, luego defensas, medios y delanteros. Si cogieras a los once primeros, en la mayoría de los equipos te saldrían dos porteros, y en algunos tres.

**El once va en el dorsal**, que es la convención de la época: los números no eran fijos por jugador y del 1 al 11 jugaban los titulares. La pantalla de plantilla del juego reparte a los jugadores así:

1. Se ordenan por **dorsal**, de menor a mayor.
2. Quien no tiene dorsal (`99`) recibe **el número libre más bajo** del equipo.
3. Si dos jugadores llevan el mismo número, se lo queda **el que va antes** en la plantilla y el otro pasa por la regla 2.
4. Sobre ese orden: del 1 al 11, **titulares**; del 12 al 16, **convocados**; del 17 en adelante, no convocados.

El caso que lo deja claro: un delantero del Barcelona de aquel año lleva `99` en el fichero, y el juego le da el 10, que es el único número que le falta al equipo. Por eso sale en el once.

Los dorsales repetidos existen de fábrica, y no son un error tuyo de lectura.

**Consecuencia: para cambiar el once, cambia dorsales.** No muevas fichas de sitio. Lo más limpio es repartir los números que el equipo ya tiene según el orden nuevo: así no inventas ninguno ni duplicas ninguno.

En la ficha no hay ningún otro byte que marque la titularidad: se han probado todos los bits del bloque fijo contra «dorsal del 1 al 11» y ninguno encaja. Tampoco hay alineaciones en la cabecera del club ni en las actas de los partidos.
