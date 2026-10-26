# El contenedor PKF por dentro

Casi todo en 5.0 y 6.0 está empaquetado en ficheros con extensión `PKF`. Escudos, fotos, pantallas, música, banderas, equipaciones… todos usan **el mismo formato de contenedor**. Entendiendo uno, los entiendes todos.

## Cómo saber si un PKF es de verdad

Empieza por aquí, porque ahorra disgustos. **Todo contenedor auténtico lleva su propio nombre escrito en la cabecera**, cifrado. Si lo descifras y sale el nombre del fichero, es un contenedor. Si sale basura, no lo es aunque se llame `.PKF`.

Es la forma más rápida de comprobar que estás ante lo que crees. En 5.0 hay un fichero enorme que se llama `PCF5DAT.PKF` y **falla esta prueba**: no es un contenedor.

## Cómo comprobar que lo estás leyendo bien

Descifra el nombre de la primera entrada. Si sale algo como `EQ960003.BMP`, vas bien. Si sale basura, o has empezado en el sitio equivocado o has copiado mal la secuencia.

## La estructura

Tras una cabecera de doscientos treinta y dos bytes empieza el índice. Cada elemento del índice lleva delante una marca que dice qué es:

| Marca | Qué significa |
|---|---|
| `02` | Una entrada de fichero |
| `04` | Salto: el índice continúa en otra parte |
| `05` | Fin del contenedor |

Una entrada de fichero ocupa **treinta y ocho bytes**, repartidos así:

| Posición | Tamaño | Qué es |
|---|---|---|
| 0 | 1 | La marca, `02` |
| 1 | 20 | El nombre, cifrado |
| 21 | 1 | Siempre cero |
| 22 | 4 | Sin identificar. Hay una pista, abajo |
| 26 | 4 | **Dónde empieza el contenido**, desde el principio del fichero |
| 30 | 4 | **Cuánto ocupa** |
| 34 | 4 | **El número de sub-contenedor** (ver abajo) |

Un salto ocupa cinco bytes: la marca `04` y, en los cuatro siguientes, la posición donde continúa el índice.

Dos apuntes sobre esos cuatro bytes de posición y tamaño, medidos sobre **40.007 entradas** de las ocho ediciones: **el byte más alto es cero en todas**. O sea que en la práctica son números de tres bytes y ningún contenedor puede pasar de 16 MB. Puedes leerlos como número de cuatro bytes sin problema —es lo mismo— pero si te sale algo en ese cuarto byte, no es que el fichero sea enorme: es que te has descolocado.

### El campo sin identificar, y la pista que tiene

Los cuatro bytes del 22 al 25 son lo único del registro que sigue sin estar claro. Lo que se sabe, medido:

- **En muchos contenedores valen cero enteros.** En los de 5.0, 5.0 Oro, 6.0 base y Apertura 97 no hay nada ahí.
- Donde no son cero, **la mitad baja del número es la misma para todo el contenedor** y solo cambia la mitad alta.
- Esa mitad alta toma **muy pocos valores** —nueve en el contenedor de escudos pequeños de 6.0 Oro, para 681 entradas— y crece despacio a lo largo del fichero.
- **No es una suma de comprobación del contenido**: nueve valores para 647 imágenes distintas, y cada valor cubre decenas de ellas.

**La pista.** Esos números caen entre 33.949 y 34.033, que leídos como *días transcurridos desde el 1 de enero de 1904* dan esto:

> 12, 15, 16, 17, 18 y 19 de **diciembre de 1996** — y 4, 5 y 6 de **marzo de 1997**.

Dos tandas de días laborables consecutivos, con el juego publicado en 1997. Encaja tan bien con «cuándo se dibujó cada imagen» que cuesta creer que sea casualidad, y explicaría por qué crece a lo largo del fichero y por qué hay tan pocos valores distintos.

**Pero no está confirmado, y esto es lo que lo impide:** la misma lectura aplicada a Apertura 98 da fechas de 2033. O el punto de partida es otro en esa edición, o la interpretación es equivocada. Se publica como pista, no como hecho.

Para lo que importa en la práctica: **cópialo tal cual** al reescribir un índice. Nada de lo que hemos probado depende de él.

### El número de sub-contenedor: lo que resuelve los nombres repetidos

El último campo se describe muchas veces como «un valor que siempre vale 1». **Vale 1 en la mayoría de contenedores porque la mayoría tiene una sola sección.** En los que tienen varias, va de 1 a 13, y es el número de la sección.

Se comprueba mirando dónde caen los contenidos: en el contenedor del simulador de 6.0 Oro las siete secciones ocupan tramos **seguidos y sin solaparse** —una acaba justo donde empieza la siguiente—, que es exactamente lo que significa que el fichero sean varios contenedores pegados uno detrás de otro.

**Y esto arregla un problema real.** En esos contenedores **hay nombres repetidos**: `0GRADA1.BMP` aparece cinco veces en el del simulador, y `ALINEACION_ON.BMP` dos veces en el de imágenes. Si buscas un elemento por su nombre, no sabes cuál te va a tocar.

La cuenta, sobre los 109 contenedores de las ocho ediciones:

| Cómo identificas un elemento | Cuántos chocan |
|---|---|
| Solo por el nombre | **126** |
| Por el nombre **y su número de sección** | **0** |

Ninguno. Así que la regla es: **la clave de un elemento no es su nombre, es su nombre más su sección.** Quien lo guarde solo por el nombre irá perdiendo elementos por el camino sin enterarse.

Y un detalle que hace tropezar nada más empezar: **el índice puede arrancar con un salto**, no con una entrada. En varios contenedores, el primer byte tras la cabecera es un `04`. Da igual — se trata igual que cualquier otro salto.

## El índice no está todo junto

Esta es la particularidad que confunde al escribir un lector. El índice **va troceado y repartido entre los datos**: lees entradas hasta topar con un salto, que te dice dónde continúa por encima de un bloque de imágenes, sigues leyendo allí, y así hasta la marca de fin.

Si tu lector se detiene tras las primeras entradas, es que estás ignorando los saltos.

### Los tramos son de treinta y dos

El troceado no es caprichoso, y saber su medida ayuda a comprobar que vas bien: **cada tramo del índice trae exactamente 32 entradas** y termina en un salto. El último trae las que sobren.

Con eso sale la cuenta de lo que ocupa un tramo entero: 32 entradas de 38 bytes más los 5 del salto son **1.221 bytes**. Si al recorrer los datos de un contenedor te topas con un agujero de exactamente 1.221 bytes entre el final de un elemento y el principio del siguiente, **no es espacio desperdiciado: es el siguiente tramo del índice**, metido ahí en medio.

Está comprobado en los contenedores de las ocho ediciones —equipos, escudos, banderas y fotos— y sale 32 en todos.

Sirve además como prueba de cordura barata: si tus tramos salen de un tamaño irregular, no estás leyendo bien los saltos. Y si te salen de 32 pero el primero te sale vacío, eso sí es normal — es el salto de arranque del que habla el párrafo anterior.

## El cifrado de los nombres

Los nombres van cifrados, pero **con un sistema distinto al del texto de la base de datos**. Allí todos los bytes usan la misma clave; aquí **cada posición del nombre tiene la suya**, siguiendo esta secuencia fija de veinte valores:

```
DF C0 A3 88 6F 58 43 30 1F 10 03 F8 EF E8 E3 E0 DF E0 E3 E8
```

Se aplica igual que el otro cifrado —un XOR— pero usando el valor que corresponde a la posición: el primer carácter del nombre con `DF`, el segundo con `C0`, y así.

La secuencia no es aleatoria y eso ayuda a comprobar que la has copiado bien: **las diferencias entre valores consecutivos son los impares en orden descendente** —31, 29, 27, 25… hasta 1— y a partir de ahí vuelven a subir. Si al restar dos valores seguidos no te sale un impar, has copiado mal alguno.

Descifrado, un nombre tiene esta pinta: un prefijo que dice de qué es, un número que identifica al equipo o al jugador, y la extensión.

| Ejemplo | Qué es |
|---|---|
| `EQ960001.BMP` | El escudo del equipo 1 |
| `J9600123.BMP` | La foto del jugador 123 |
| `P96A0000.DAT` | La primera equipación del equipo 0 |
| `APELLIDO.1` | La lista de apellidos del país 1 |

El identificador va **con ceros a la izquierda**: cuatro cifras para los equipos y cinco para los jugadores.

Tras el nombre hay bytes de relleno que **no descifran a nada legible**. No te preocupes por ellos: el nombre acaba en el primer cero.

## Un detalle sobre el prefijo numérico

Los nombres de dentro llevan casi siempre el prefijo `96`, **en todas las versiones**, incluida la 6.0. No es un error ni indica la edición: es simplemente cómo se llaman dentro del contenedor.

Los ficheros sueltos que se dejan en la carpeta para sustituir a los de dentro sí usan a veces otro prefijo. Es una fuente de confusión conocida.

## Cómo sustituir el contenido

Dos caminos:

**El fácil, y el que recomiendo:** no tocar el contenedor. **El juego mira primero si hay un fichero suelto en la carpeta** y solo si no lo encuentra abre el contenedor.

Los nombres y las carpetas son estos. Todos van dentro de `DBDAT`, cada uno en una subcarpeta con el nombre del contenedor al que sustituye:

| Qué quieres cambiar | Dónde va | Cómo se llama |
|---|---|---|
| Escudo diminuto | `DBDAT\NANOESC\` | `eq96NNNN.bmp` |
| Escudo pequeño | `DBDAT\MINIESC\` | `eq96NNNN.bmp` |
| Camisetita de clasificaciones | `DBDAT\RIDIESC\` | `eq96NNNN.bmp` |
| Foto de jugador | `DBDAT\MINIFOTO\` | `j96NNNNN.bmp` |
| Camiseta de la ficha | `DBDAT\CAMISAS\` | `eq96NNNN.bmp` |
| Bandera de país | `DBDAT\BANDERAS\` | `ba96NNNN.bmp` |
| Foto de estadio | `DBDAT\BIGCAMP\` | `eq96NNNN.bmp` |

`NNNN` es el identificador del equipo con **cuatro cifras** y ceros a la izquierda; `NNNNN` el del jugador con **cinco**. Los del país usan el código de país.

### El prefijo: 96 o 97

Ese `96` del nombre **no siempre es 96**. Es el prefijo que use el contenedor al que sustituyes, y en algunas ediciones es `97`.

La forma de saberlo sin adivinar: **mira el prefijo del primer elemento del contenedor** y usa ese. Si te equivocas, el fichero suelto simplemente se ignora — el juego seguirá cogiendo la imagen de dentro y parecerá que tu cambio no ha servido de nada.

**El difícil:** reempaquetar. Hay que reescribir el índice con las nuevas posiciones y tamaños, respetando la cadena de saltos. Solo merece la pena si vas a sustituir cientos de elementos.

## Cómo QUITAR una imagen sin borrarla

Un truco que resuelve un problema que parece imposible: **hacer que el juego se comporte como si un equipo nunca hubiera tenido esa imagen**.

Borrar la entrada del contenedor es complicado —hay que recolocar todo lo de detrás— y además no hace falta. **El juego busca cada imagen por su nombre**, así que basta con **renombrar la entrada** para que no la encuentre. La imagen sigue ahí, ocupando su sitio, pero es invisible.

Y el resultado no es un hueco negro: el juego hace lo mismo que con cualquier equipo que no tenga esa imagen. Con la foto del estadio, por ejemplo, **dibuja el estadio genérico**, ese que va cambiando de forma según las gradas que construyes.

Es la diferencia entre «poner una imagen vacía» —que se vería como una imagen vacía— y «no tener imagen», que es lo que casi siempre se quiere.
