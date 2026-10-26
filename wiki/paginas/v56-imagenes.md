# Escudos, fotos y banderas

Las imágenes van en sus propios contenedores, uno por tipo y tamaño. Pero antes de abrir ninguno conviene saber lo siguiente, porque ahorra casi todo el trabajo.

## El atajo: no hace falta abrirlos

**El juego busca primero una imagen suelta en la carpeta y solo si no la encuentra va al contenedor.** Es decir: para cambiar un escudo no tienes que reempaquetar nada. Basta con dejar el archivo con el nombre que toca en la carpeta correspondiente.

Es, con diferencia, la forma más práctica de trabajar. Y es lo que hacen los mods de la comunidad.

### El nombre exacto que tiene que llevar

Esto no hay que adivinarlo: **las rutas están escritas en texto plano dentro del ejecutable del juego** y se leen con cualquier editor. Son estas:

| Qué quieres cambiar | Dónde lo dejas |
|---|---|
| Escudo diminuto | `DBDAT\NANOESC\eq96####.bmp` |
| Escudo pequeño | `DBDAT\MINIESC\eq96####.bmp` |
| Camisetita de clasificaciones | `DBDAT\RIDIESC\eq96####.bmp` |
| Bandera grande | `DBDAT\BANDERAS\ba96####.bmp` |
| Bandera pequeña | `DBDAT\MINIBAND\ba96####.bmp` |
| Foto de jugador de los listados | `DBDAT\MINIFOTO\<nombre>.bmp` |

Los `####` son el identificador **en cuatro cifras, con ceros por delante**: el equipo 4 es `eq960004.bmp`.

### La regla de los nombres, entera

Los nombres de dentro de los contenedores siguen exactamente la misma regla, y es fácil de recordar en cuanto se ve el porqué:

| Entidad | Nombre | Cifras |
|---|---|---|
| Equipo | `EQ96####.BMP` | 4 |
| País | `BA96####.BMP` | 4 |
| Jugador | `J96#####.BMP` | **5** |
| Entrenador | `E96#####.BMP` | **5** |

¿Por qué unos cuatro y otros cinco? Porque **todos los nombres ocupan ocho caracteres**, que era el máximo de MS-DOS. Con dos letras de prefijo quedan cuatro cifras; con una letra, cinco. Los jugadores y los entrenadores son los que más hay, así que se les dio la letra corta.

Y es la misma regla que siguen los ficheros de datos sueltos: cuatro cifras para el equipo, cinco para el jugador y el entrenador. Dos partes del juego hechas por gente distinta que coinciden — buena señal de que la regla está bien leída.

> **El aviso más importante de esta página: el prefijo es `96` SIEMPRE, también en 6.0.**
>
> Es fácil equivocarse porque los ficheros de datos de 6.0 sí usan `97`. Las imágenes no: el ejecutable de 6.0 Oro lleva `eq96%04u` igual que el de 5.0. Si nombras tus escudos con `eq97`, el juego no los verá y no te dará ningún error — simplemente seguirá usando los suyos, que es el fallo más difícil de diagnosticar de todos.

### Dos carpetas más, solo en 6.0

El ejecutable de 6.0 y 6.0 Oro añade dos rutas que en 5.0 no existen:

| Qué | Dónde |
|---|---|
| Foto del estadio | `dbdat\estadio\<nombre>.bmp` |
| Fondos de pantalla | `dbdat\fondos\<nombre>.bmp` |

Y una curiosidad que sale del mismo sitio: 6.0 Oro busca además `img\previo2\estadios\eq96####.gif` — la imagen del estadio de la previa del partido, que **es un GIF y no un BMP**, y va por el identificador del equipo.

### Por qué en las ediciones Oro parece que no están

Si buscas estas rutas en el ejecutable de 5.0 Oro no las encontrarás enteras, y podrías concluir que ahí no funciona el atajo. **Sí funciona.** Lo que cambia es cómo está montado: en las ediciones Oro el nombre de la carpeta (`DBDAT\NANOESC\`) y el del fichero (`eq96%04u`) están **guardados por separado**, y el juego los junta al vuelo con un patrón genérico. El resultado es el mismo nombre, y está comprobado en el juego.

## Qué contenedor es cada cosa

| Contenedor | Qué lleva | Medida | Cuántas |
|---|---|---|---|
| `NANOESC` | Escudo diminuto | **24 × 32** dentro del contenedor | 528 |
| `MINIESC` | Escudo pequeño | 48 × 64 | 528 |
| `BIGESC` | Escudo grande | 160 × 194 | 166 |
| `RIDIESC` | **La camisetita de las clasificaciones** | **17 × 20** | 644 |
| `MINIFOTO` | Foto de jugador de los listados | 32 × 32 | 2.009 |
| `BIGARBIT` | Foto de árbitro (solo 6.0) | 80 × 96 | 43 |
| `BIGFOTO` | Foto de la ficha | 124 × 182 | ver abajo |
| `MINIENTR` y `BIGENTR` | Fotos de entrenador | 32 × 32 y 124 × 182 | 67 |
| `BANDERAS` y `MINIBAND` | Banderas de país | 30 × 20 y 14 × 10 | 117 cada uno |
| `CAMISAS` | Camiseta de la ficha del club | 73 × 38 | 42 |
| `BIGCAMP` | Foto del estadio | 200 × 140 | **61** |

### Las fotos grandes van en cien contenedores

`BIGFOTO` no es un fichero: es **una carpeta con un contenedor por equipo**, cada uno con las fotos de sus jugadores. El nombre del contenedor lleva el identificador del club, con la misma regla que todo lo demás: `EQ960001.PKF`.

**Cuántos hay depende de la edición**, y conviene saberlo porque marca hasta dónde llega el material:

| Edición | Contenedores |
|---|---|
| 5.0 | 42 |
| 6.0 | 46 |
| 5.0 Oro | 100 |
| 6.0 Oro, Premier, Calcio | 104 |

Fíjate en el salto: las ediciones Oro traen **más del doble**. Y en ningún caso hay uno por equipo — las bases tienen cientos de clubes. Sale de aquí una regla práctica: **la mayoría de los equipos no tiene fotos grandes, y eso es normal**, no es que falte nada en tu copia.

Tiene sentido — son las imágenes más pesadas del juego y así solo se carga la del equipo que estés mirando. Pero significa que para tocar la foto de un jugador hay que saber **en qué club está**, no solo su identificador.

Un aviso sobre el escudo diminuto: **dentro del contenedor mide 24 de ancho, pero los ficheros sueltos que se dejan en la carpeta son de 25** y el juego acepta los dos. Es una diferencia real, no un error de medida, y explica que circulen las dos cifras.

### Dos contenedores que NO llevan BMP

Aquí hay una trampa que hace fallar a cualquier lector que dé por hecho que todo es BMP. **Dos contenedores guardan GIF**, y además con el prefijo `95` en vez de `96`:

| Edición | Contenedor | Qué lleva dentro |
|---|---|---|
| 6.0 base | `MINIENTR` | `E9500001.GIF` — GIF, prefijo 95 |
| Apertura 98 | `MINIFOTO` | `J9500001.GIF` — GIF, prefijo 95 |

Son las **únicas dos excepciones** de las ocho bases. En el resto de ediciones esos mismos contenedores llevan BMP con prefijo 96, como todos los demás.

La lección práctica: **no supongas el formato por el nombre del contenedor — míralo**. Los tres primeros bytes te lo dicen: `BM` o `DM` es mapa de bits, `GIF` es GIF. Cuesta una línea y te ahorra el rato de no entender por qué justo esa edición da basura.

Las medidas están leídas de la cabecera de cada imagen y confirmadas con el tamaño del elemento, no estimadas: una imagen de 256 colores ocupa ancho por alto más la cabecera, con las filas rellenadas hasta un múltiplo de cuatro bytes. Si te sale la cuenta, has acertado con las dimensiones.

## Las fotos de entrenador van por su propio número

Detalle que despista: las fotos de entrenador **no se numeran por el equipo sino por el entrenador**. Cada técnico tiene su identificador en su ficha, y ese es el que da nombre a su foto. Si cambias el entrenador de un club, la foto no le sigue.

## Tres fotos de estadio distintas

Y aquí una que confunde a todo el mundo, porque hay **tres imágenes distintas del mismo estadio** repartidas en tres sitios:

| Dónde | Medida | Cuántos clubes |
|---|---|---|
| `BIGCAMP` | 200 × 140 | 61 |
| `estadio` | 320 × 240 | 20 |
| `fondos` | 640 × 480 | 20 |

La primera es la que sale en la base de datos. La segunda es la de la ficha del club. La tercera es un fondo a pantalla completa.

Que sean **solo veinte** en las dos últimas no es un recorte: Dinamic solo las hizo para un puñado de equipos. El resto se queda sin ellas y el juego funciona igual.

Al sustituir una hay que acordarse de las tres, o el estadio saldrá cambiado en una pantalla y con el original en otra.

**`RIDIESC` no es un escudo.** Es el error más repetido: por el nombre parece uno más de la serie, y lo que contiene es la camisetita que sale al lado del equipo en las tablas de clasificación.

## Cómo se llaman las imágenes

El nombre lleva dentro el identificador: los escudos por el puntero del club y las fotos por el del jugador. Ese identificador es el de **la lista maestra de Dinamic**, no un número inventado — el Barcelona es el 1, el Real Madrid el 4, el Atlético el 12.

### Dónde encontrar ese número

Aquí hay una confusión muy extendida, y conviene deshacerla porque ahorra muchísimo trabajo.

**En el bloque del equipo no está.** El campo que hay justo detrás de la firma es otro identificador distinto, que además cambia de una edición a otra. Si lo usas para nombrar el escudo, te saldrá el escudo de otro club.

**Pero sí está en el fichero**, en la tabla de índice de la cabecera: cada entrada tiene un nombre, y ese nombre **lleva dentro el puntero canónico**. Ahí es donde hay que leerlo.

Eso significa que **no hace falta adivinarlo emparejando nombres de equipo**, que es lo que mucha gente acaba haciendo y falla justo con los clubes de nombre parecido. Está escrito, solo hay que mirar en el sitio correcto. Y como está para todos los equipos y sin repetirse, ninguno se queda sin número.

Es un detalle que cuesta caro si se hace mal: un escudo mal numerado es un escudo que no sale, y un fichero de equipo mal numerado ha llegado a **colgar el juego**.

## El formato de las imágenes

Son mapas de bits de 256 colores, pero con una particularidad que despista mucho:

**Los que están dentro de los contenedores no llevan paleta.** La tabla de colores va a ceros y la pone el juego desde fuera. Si extraes uno tal cual y lo abres, lo verás **completamente negro** y pensarás que está corrupto. No lo está: le falta la paleta.

La paleta es fija y la misma para todo el juego. Al preparar una imagen nueva hay que ajustarla a esos colores; si usas otros, el juego los sustituirá por los suyos y el resultado no se parecerá a lo que esperabas.

Otro detalle: muchas imágenes del juego traen **los últimos bytes recortados** — les falta un trozo del final de la última fila. El juego lo tolera y pinta el resto. Al leerlas hay que rellenar lo que falte con el índice 0, y al reconstruirlas no pasa nada por escribirlas completas.

## Dos cabeceras distintas conviviendo

Dentro de un mismo contenedor conviven dos formas de cabecera. Se distinguen por **los dos primeros bytes**:

| Empieza por | Qué es | Dimensiones | Los píxeles empiezan en el byte |
|---|---|---|---|
| `BM` | La cabecera antigua estándar | dos bytes cada una | **26** |
| `DM` | La propia de Dinamic | cuatro bytes cada una, con signo | **54** |

Y una curiosidad que hace perder mucho tiempo: en la variante de Dinamic, **el campo que dice dónde empiezan los píxeles miente**. Suele poner 1078, que es donde estarían si hubiera una tabla de colores de 256 entradas delante… y no la hay. Ignóralo y usa el 54.

## Cómo leer los píxeles

Tres cosas que hay que saber y que no se deducen mirando el fichero:

**Van de abajo arriba.** La primera fila que encuentras en el fichero es **la de abajo del todo** de la imagen. Si no lo tienes en cuenta, el escudo sale boca abajo y parece que has entendido mal el formato cuando en realidad solo falta darle la vuelta.

**Cada fila se rellena hasta un múltiplo de cuatro bytes.** Una imagen de 19 píxeles de ancho ocupa 20 bytes por fila, y esos bytes de más no son parte del dibujo. Si no los saltas, la imagen sale inclinada — cada fila un poco más desplazada que la anterior.

**Un byte por píxel**, y ese byte es un índice de la paleta.

Con eso y la [paleta](v56-paleta.html) ya tienes la imagen. Si al montarla te sale el escudo del club correcto y con sus colores, has acertado en todo.

## Comprobación

La cuenta que confirma que lo has entendido: **el tamaño del elemento tiene que ser la cabecera más el ancho redondeado a múltiplo de cuatro, multiplicado por el alto**.

Para el balón del menú, que es de 38 por 38: 54 de cabecera más 40 por 38 son 1.574 bytes, y el elemento ocupa 1.576. Los dos de diferencia son cola sobrante, que el juego tolera.

## La estructura del contenedor

Por si necesitas abrirlos de verdad: tras una cabecera de doscientos treinta y dos bytes empiezan los registros. Cada uno lleva una marca que dice qué es —una entrada de fichero, un salto a otra parte del índice, o el final—.

Lo llamativo es que **el índice no está todo junto**: va en trozos intercalados entre las imágenes, y cada trozo termina con un salto que indica dónde continúa. Hay que ir siguiendo esos saltos hasta la marca de fin.

Los nombres de los ficheros dentro del índice también van cifrados, pero **con un cifrado distinto al del texto de la base de datos**: aquí cada posición del nombre usa su propia clave.
