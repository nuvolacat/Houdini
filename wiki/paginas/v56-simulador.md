# Las equipaciones del partido

> `DATSIM` guarda las equipaciones, pero **no solo eso**: de sus mil seiscientos elementos, mil quinientos ochenta y cuatro son camisetas y el resto son los gráficos del partido. Se detallan en [los contenedores menos conocidos](v56-otros-contenedores.html).

Las camisetas que se ven durante el partido no son ninguna de las imágenes de la base de datos. Van en su propio fichero, `DATSIM.PKF`, y funcionan de una manera muy distinta.

## No son imágenes: son colores

La clave está aquí. Una equipación del simulador **no es un dibujo de una camiseta**: son **192 bytes** que son índices de la paleta de colores del juego, con los que el simulador colorea el muñeco.

Cada club tiene dos: la primera equipación y la segunda. Se distinguen por la letra de su nombre — una `A` para la primera y una `B` para la segunda, seguidas del identificador del equipo.

## Qué es cada byte

El reparto de los 192 está resuelto casi entero:

| Bytes | Qué son |
|---|---|
| 0 a 127 | **La textura de la camiseta**: una rejilla de 16 columnas por 8 filas |
| 128 a 133 | Rampa de sombreado del color base: seis tonos, de oscuro a claro |
| 134 a 152 | Detalles y constantes: botas, piel, bordes |
| 153 a 155 | El pantalón |
| 156 a 161 | Las medias: dos piernas por tres tonos |
| 162 a 191 | **Una tercera zona, con la estructura resuelta y el significado abierto** (ver abajo) |

Lo importante es la primera parte. **Los 128 primeros bytes son una rejilla, no una tira.** Cada byte es una celda de la camiseta, y por eso se puede dibujar entera y volver a convertirla en bytes.

Se ve a simple vista imprimiendo los bytes de dieciséis en dieciséis: el Barcelona repite ocho filas idénticas alternando dos colores —sus rayas verticales— y el Real Madrid las tiene todas al mismo valor. Ninguna equipación del juego tiene el patrón que tendría si fuera una tira, así que la rejilla no es una interpretación: es lo que dicen los datos.

Justo después de esos 128 viene la rampa de sombreado, y se reconoce sola porque son seis valores descendentes seguidos.

Esto tiene una consecuencia práctica agradable: **cambiar una equipación es cambiar números, no dibujar**. Y otra menos agradable: no puedes hacer cualquier diseño, solo los que la rejilla permite.

## No confundir con la camiseta de la ficha

Son cosas distintas y es un lío habitual:

- **`CAMISAS.PKF`** es la camiseta que se ve en la ficha del club, en la base de datos. Es una imagen normal.
- **`DATSIM.PKF`** es la que se ve en el partido. Son índices de color.
- **`RIDIESC`** es la camisetita de las clasificaciones. Otra imagen distinta.

Cambiar una no cambia las otras. Si has cambiado los colores del equipo y en el partido sigue saliendo la vieja, es que has tocado la que no era.

## Al reemplazar

Como todas las entradas ocupan lo mismo, se sustituye una por otra sin problema de tamaño. Lo que hay que respetar es la correspondencia: cada equipo tiene su sitio, identificado por su puntero, y hay dos entradas por club — la de campo y la del portero.

## Lo que queda por saber

**Los treinta últimos bytes**, del 162 al 191. No son ni la camiseta ni el pantalón ni las medias. Lo que se sabía hasta ahora era eso y nada más; midiéndolos sobre **3.704 equipaciones** de 5.0, 5.0 Oro y 6.0 Oro, la zona se deja partir en seis trozos con forma propia:

| Bytes | Qué se observa |
|---|---|
| 162 | Vale `127` en el **93 %**. Prácticamente una constante |
| 163 a 168 | **El mismo trío de valores repetido dos veces**, en el 84,5 % |
| 169 a 172 | **La misma pareja repetida dos veces**, en el 90,9 % |
| 173 a 175 | `96`, `113`, `97` en el **94 %**. Constantes |
| 176 | Varía mucho y por equipo. Se comporta como un color |
| 177 a 191 | **Quince copias del mismo valor**, en el 94 % — y ese valor es `0` o `96`, casi nunca otro |

**Lo del trío y la pareja repetidos merece explicación, porque es el hallazgo.** Las medias, que sí sabemos qué son, están guardadas como *dos piernas por tres tonos*: el mismo trío dos veces. Si aplicamos esa misma prueba a las medias sale 93,9 %, y a los bytes 163-168 sale 84,5 %. **Es la misma firma.** O sea que ahí hay otra prenda simétrica, guardada igual que las medias — con toda probabilidad las dos mangas.

Digo «con toda probabilidad» y no lo doy por hecho: intenté confirmarlo comprobando si esos bytes usan colores de la camiseta, y el resultado fue que **no discrimina** — las medias y el pantalón, que sí conocemos, puntúan igual de bajo. Cada prenda tiene su propio juego de índices. Así que la estructura está establecida y el significado no.

**Y los quince del final tienen una pista buena.** No son basura: son quince copias de un mismo valor, y ese valor es `0` en unos equipos y `96` en otros. Cuál de los dos **es una propiedad del equipo, no de la equipación**: comparando la primera y la segunda equipación de los 812 clubes de 6.0 Oro, coinciden en **810**. Además los clubes de puntero bajo —los grandes españoles— llevan `96` y los de puntero alto llevan `0`, lo que apunta a que marca a los equipos con material completo.

Con esto, de los treinta bytes «sin identificar» quedan abiertos **el significado de dos trozos**, no la zona entera. Sigue agradeciéndose cualquier hallazgo, pero ahora se sabe dónde mirar.

Todo lo demás está confirmado de la forma más exigente que hay: **dibujar la camiseta a partir de los bytes y volver a convertir el dibujo en bytes devuelve exactamente los mismos 192**, en las mil seiscientas veinticinco equipaciones de la 6.0. Lo que el dibujo no representa —la rampa, las constantes y esa tercera zona— se conserva del original.
