# El bloque de un equipo en 5.0 y 6.0

Todo lo de un club vive junto, en un bloque continuo: sus datos, su historial, su táctica, su entrenador y la lista completa de jugadores. Los bloques van uno detrás de otro, sin huecos.

> **La tabla completa campo a campo, sin explicaciones, está en [la referencia](v56-referencia.html).** Esta página cuenta el porqué; aquélla es para tenerla al lado mientras programas.

## Cómo se encuentra el principio

Cada bloque empieza con una cadena de texto **sin cifrar**, que se lee tal cual en cualquier editor hexadecimal:

```
Copyright (c)1996 Dinamic Multimedia
```

Treinta y seis caracteres, con el año según la edición. Es el delimitador más fiable que hay: buscando esa cadena localizas todos los equipos del fichero sin necesidad de entender nada más.

## La otra forma de delimitarlos: la tabla de índice

Buscar la firma funciona, pero el juego no lo hace así. Al principio del fichero hay **una tabla con un registro por equipo**, y de ahí saca dónde empieza y cuánto ocupa cada bloque.

**Esa tabla no es propia del fichero de equipos: es el índice normal de un contenedor**, exactamente igual que el de los escudos. Está descrito entero en [su propia página](v56-contenedor-pkf.html), y aquí solo va lo justo para seguir leyendo. Cada registro son **38 bytes**:

| Posición | Tamaño | Qué es |
|---|---|---|
| 0 | 1 | La marca de entrada, `02` |
| 1 | 20 | **El nombre del equipo dentro del contenedor**, cifrado: `EQ960001.DBC` |
| 21 | 1 | Siempre cero |
| 22 | 4 | Sin identificar |
| 26 | 4 | **Dónde empieza el bloque** |
| 30 | 4 | **Cuánto ocupa el bloque** |
| 34 | 4 | El número de sección del contenedor |

Lo que en otras descripciones aparece como «una firma de cinco bytes y un puntero con codificación peculiar» son en realidad **los primeros nueve bytes de ese nombre cifrado**. Se explica justo debajo.

Y esos cuatro bytes de posición y de tamaño **tienen el byte más alto a cero siempre**, así que también valen leídos como números de tres bytes. Es la misma cosa.

Se puede comprobar que se ha entendido bien con una cuenta sencilla: **el principio de un bloque más su tamaño tiene que dar el principio del siguiente**. Si cuadra en todos, la tabla está bien leída — con una salvedad: cada 32 equipos hay un hueco de 1.221 bytes, que es el siguiente tramo del índice metido entre los datos, y no un fallo tuyo.

Un detalle: la tabla **va agrupada por división**, y la cuenta de posiciones se reinicia al cambiar de grupo.

### El puntero codificado, y su truco

> Este apartado tiene una comprobación independiente: la herramienta de referencia que existe para este formato lleva **las cuatro tablas escritas a mano, entrada por entrada**. Sus veinte valores coinciden exactamente con la regla de abajo. O sea que la regla es correcta y, además, ahorra copiar cuarenta números.


Los cuatro bytes del puntero no son un número normal. Guardan **un byte por cada cifra decimal**, y a primera vista cada posición parece usar una tabla de correspondencia arbitraria y distinta.

Mucha documentación lo describe así: cuatro tablas de conversión de diez entradas que hay que copiar a mano. **Y no hay que copiar nada, porque no es una codificación aparte.**

### No es un cifrado propio: es el nombre del fichero

Esto es lo más útil de toda la página, así que va despacio.

**El fichero de equipos es un contenedor PKF corriente**, el mismo que los de escudos y los de fotos. Tiene la misma cabecera y el mismo índice, y **sus miembros se llaman `EQ96####.DBC`**, con el identificador del equipo en el nombre. El Barcelona es `EQ960001.DBC`.

Y en un PKF **los nombres van cifrados**, con la secuencia de claves por posición que está en la página del contenedor. Así que esos «cuatro bytes de puntero con codificación peculiar» son sencillamente **las cuatro cifras del nombre, cifradas como se cifra cualquier nombre**.

Las cuatro claves mágicas salen solas. La cifra `0` se escribe como el carácter `0`, que vale `0x30`; ciframos ese `0x30` con la clave que le toca a su posición del nombre, y lo que sale es la clave publicada:

| Cifra | Su sitio en el nombre | Clave del cifrado ahí | `0x30` cifrado |
|---|---|---|---|
| Millares | 5.ª letra | `0x6F` | **`0x5F`** |
| Centenas | 6.ª | `0x58` | **`0x68`** |
| Decenas | 7.ª | `0x43` | **`0x73`** |
| Unidades | 8.ª | `0x30` | **`0x00`** |

Las cuatro coinciden. Y no es aproximado: para las diez cifras en las cuatro posiciones, leer con la clave de la tabla y leer descifrando el nombre **dan siempre el mismo resultado**.

Un ejemplo: el Barcelona, que es el equipo 1, se guarda como `5F 68 73 01`. Descífralo como nombre y te sale `0001`.

**Lo que esto te ahorra:** si ya sabes abrir un contenedor —y para leer los escudos tienes que saberlo— **no tienes que aprender nada nuevo**. El fichero de equipos se abre con el mismo código. Y el identificador de cada equipo no hay que decodificarlo: **es el nombre de su miembro**, en texto, una vez descifrado.

### Y de paso resuelve el problema del número canónico

Lo que da nombre a los escudos, a las fotos y a los DBC es **este** identificador, el del índice — no el que va dentro del bloque, que es otro distinto. El Barcelona es el 1 en el índice y lleva el 2101 en su bloque, y su escudo es `eq960001.bmp`.

Mucha gente acaba adivinándolo emparejando nombres de club, que falla justo con los parecidos. No hace falta: **está escrito en el índice, en texto, para todos los equipos y sin repetirse**.

Y ahí se lee también, sin más trabajo, **el prefijo de temporada de esa edición** —`96` o `97`—, que es el que tienen que llevar los DBC que escribas. Comprobado en las ocho bases: 5.0, 5.0 Oro, 6.0 Oro, Apertura 97, Premier y Calcio usan `96`; **6.0 base y Apertura 98 usan `97`**. No lo supongas por el nombre del juego: míralo en el índice.

> **Cuidado, que no es lo mismo que las imágenes.** El prefijo de los DBC cambia según la edición, pero **el de las imágenes es `96` siempre**, incluso en las ediciones cuyos DBC son `97`. Son dos cosas distintas que se parecen mucho.

### ¿Cuál de las dos formas usar?

**Buscar la firma** es más simple, no necesita entender la tabla y funciona aunque el índice esté mal. Es lo que recomiendo para empezar.

**Usar la tabla** da los límites exactos sin depender de que la firma aparezca, y permite validar: si el bloque que delimita la tabla no empieza por la firma, algo va mal en tu lectura.

Lo ideal es usar las dos y comprobar que coinciden.

## Un fichero puede traer DOS temporadas

Antes de seguir, un aviso que descoloca a cualquiera que abra la edición Oro de 6.0 por primera vez: **ese fichero tiene novecientos sesenta y cinco equipos**, mientras que la edición normal tiene cuatrocientos ochenta y cuatro.

No es que haya el doble de clubes. Son **dos temporadas en el mismo fichero**, una detrás de otra, y —esto es lo importante— **cada una con un formato distinto**: un juego de equipos usa el diseño de 5.0 y el otro el de 6.0.

### Y se ve de un vistazo en el índice

No hay que deducirlo del contenido: **el nombre de cada equipo en el índice lleva la temporada delante**. Contando los prefijos de los 965 miembros de 6.0 Oro salen dos grupos exactos:

| Prefijo | Cuántos | Y resulta que… |
|---|---|---|
| `EQ96····` | **481** | son exactamente los equipos que trae **5.0 Edición de Oro** |
| `EQ97····` | **484** | son exactamente los que trae **6.0** |

Es decir que la edición de Oro de 6.0 **se lleva dentro las dos bases enteras**, la de la temporada anterior y la de la suya, sin mezclarlas. Los números cuadran clavados con los de las otras dos ediciones, así que no es una interpretación.

De ahí sale la regla que hay que retener: **el `96` y el `97` de los nombres son la TEMPORADA, no la versión del formato.** Es fácil confundirse porque en las demás ediciones coinciden. En ésta no:

| Edición | Prefijos de sus miembros |
|---|---|
| 5.0, 5.0 Oro, Apertura 97, Premier, Calcio | solo `96` |
| 6.0, Apertura 98 | solo `97` |
| **6.0 Oro** | **`96` y `97`, las dos** |

Y tiene una consecuencia que muerde: si escribes un fichero suelto para 6.0 Oro y le pones el prefijo del primer equipo del índice —que es `96`—, **el juego no lo verá**, porque lo que se juega es la temporada 97/98 y es la que busca. Mira qué prefijo corresponde a la temporada, no cuál sale primero.

Dos consecuencias prácticas más:

**No puedes decidir el formato por el fichero.** Hay que mirar el campo de versión de **cada bloque**, porque dentro del mismo fichero cambia.

**Y hay que cortar bien.** La lista de jugadores de un equipo termina donde empieza **la siguiente firma**, aunque ese bloque siguiente no lo hayas conseguido interpretar. Si no cortas ahí, el último equipo de la primera temporada se traga los nueve mil seiscientos jugadores de la segunda.

## Lo que viene detrás de la firma

| Campo | Tamaño | Notas |
|---|---|---|
| Puntero del equipo | 2 bytes | el identificador del club |
| Versión del fichero | 2 bytes | **el campo que decide todo lo demás** |
| Idioma | 1 byte | |
| Marca de liga | 1 byte | distingue club nacional de extranjero |
| Nombre corto | texto | |
| Nombre del estadio | texto | |
| País | 1 byte | |
| Nombre largo | texto | solo para la base de datos |
| Aforo | 4 bytes | valor en los 3 primeros + **un `00`** |
| Plazas de pie | 4 bytes | **en 6.0, siempre**; en 5.0, solo en clubes extranjeros |
| Ancho del terreno | 2 bytes | metros + **un `00`** |
| Largo del terreno | 2 bytes | metros + **un `00`** |
| Año de fundación | 2 bytes | |
| Socios | 4 bytes | valor en los 3 primeros + **un `00`** |
| Presidente | texto | |
| Presupuesto de base de datos | 4 bytes | el dato informativo de la ficha |
| Presupuesto del juego | 4 bytes | **el dinero con el que juegas**; ojo con el tope |
| Patrocinador y proveedor | texto | |
| Puntero del primer filial | 2 bytes | `FFFF` = sin filial |
| Puntero del segundo filial | 2 bytes | `FFFF` = ninguno |

**Son dos, y están en las dos versiones.** Es un punto donde es muy fácil equivocarse, porque casi todos los clubes tienen el segundo a `FFFF` y parece que no existe: si te lo saltas, **todo el historial se lee corrido dos bytes** y a partir de ahí no cuadra nada — ni el palmarés, ni la táctica, ni las fichas de los jugadores.

La forma de comprobar que lo has entendido: **busca al Real Madrid**. Es de los pocos que tienen los dos — su primer filial es el 26, que es el Real Madrid B, y el segundo el 98, que es el Real Madrid C. Si te salen esos dos números, vas bien. Si solo te sale uno, estás perdiendo dos bytes.

Los punteros de filial son **el identificador canónico** del club, el mismo que da nombre a su escudo.

### El cuidado con los ceros de relleno

Fíjate en la columna de tamaños: **el aforo, los socios y los presupuestos ocupan cuatro bytes pero solo usan tres**, y el cuarto es un cero. Y **cada dimensión del terreno ocupa dos**, aunque el valor sea un solo byte.

Es la trampa que más descoloca al escribir un lector: si avanzas tres bytes en el aforo y uno en cada dimensión, **te desplazas cuatro bytes antes de llegar al presidente** y a partir de ahí todo sale mal sin que nada avise.

### El campo que hay que mirar primero

La **versión del fichero** —esos dos bytes justo detrás del puntero— es lo que determina cómo se lee el resto del bloque. No te fíes del nombre del fichero ni de la carátula del juego: hay ediciones que se llaman como una versión y por dentro son de otra.

Las diferencias son pequeñas pero fatales si te equivocas. Estas son **todas**, comprobadas leyendo las ocho bases que existen:

| En 6.0 | Dónde |
|---|---|
| Un byte más tras el país | Es la latitud del estadio |
| **Cuatro bytes más tras el aforo** | Las plazas de pie, que en 5.0 solo llevan los extranjeros |
| Dos bytes más tras el año de fundación | El año del estadio |
| Las últimas diez ligas ocupan 20 bytes en vez de 10 | Llevan la división además del puesto |
| Las posiciones por jornada son 46 en vez de 42 | |


**El de las plazas de pie es el que más despista**, porque en 5.0 ese campo solo aparece en los clubes extranjeros y es fácil dar por hecho que en 6.0 pasa lo mismo. No: en 6.0 lo llevan todos. Si te lo saltas, a partir de ahí lees el terreno de juego como 0×0 y el presidente sale ilegible.

Comprobación que confirma que has acertado con el año del estadio: al Barcelona le tiene que salir **1957**, que es cuando se inauguró el Camp Nou.

## Distinguir un club nacional de uno extranjero

Importa mucho, porque **sus fichas de jugador tienen distinta longitud**: los extranjeros no guardan país de nacimiento ni los diez textos de base de datos. Si te equivocas al clasificar, leerás los campos corridos y todo lo que venga después será basura.

La pista directa es **un byte de la cabecera**: cuarenta y uno más allá del comienzo de la firma. Un cero significa club de la liga nacional.

Pero **ese byte no basta**. En las ediciones argentinas los clubes locales llevan un uno pese a tener la cabecera completa, así que fiarse solo de él los clasifica mal.

La forma robusta es **intentar el parseo completo y comprobar si el resultado tiene sentido**. Si el byte dice extranjero pero al leerlo como nacional salen datos coherentes, es nacional. Coherente quiere decir:

- El presidente, el patrocinador y el proveedor **son texto legible**, y el presidente no está vacío.
- Las dimensiones del terreno caen en un rango plausible: entre 30 y 90 metros de ancho, entre 80 y 130 de largo.
- Los socios y el presupuesto no son cifras absurdas.

Si algo de eso falla, es extranjero. Es un método de andar por casa pero funciona: las probabilidades de que un bloque extranjero produzca por azar un nombre de presidente legible **y** un campo de fútbol de medidas razonables son mínimas.

### Cómo se lee un club extranjero

Y esto es lo que casi nunca se cuenta, aunque **son más de la mitad de los bloques del fichero** — unos trescientos cincuenta por edición frente a ciento treinta nacionales.

Su cabecera es **la misma que la nacional pero mucho más corta**: llega hasta el año de fundación y ahí se acaba. Se salta de golpe todo el bloque de datos de club.

| Campo | Tamaño | |
|---|---|---|
| Puntero, versión, idioma, marca de liga | 6 bytes | igual que un nacional |
| Nombre corto | texto | |
| Nombre del estadio | texto | |
| País | 1 byte | + 1 más de latitud en 6.0 |
| Nombre largo | texto | |
| Aforo | 4 bytes | |
| Plazas de pie | 4 bytes | **solo en 6.0** |
| Ancho y largo del terreno | 2 bytes cada uno | |
| Año de fundación | 2 bytes | |
| Táctica dibujada | 176 bytes | |
| Táctica de equipo | 7 bytes | |
| Entrenador y jugadores | | |

**Lo que NO tienen:** socios, presidente, presupuestos, patrocinador, proveedor, filiales, historial, palmarés ni posiciones por jornada. Nada de eso existe en su bloque; no es que esté vacío, es que no está.

Y **tampoco el año del estadio**, aunque los nacionales de 6.0 sí lo lleven. Este es un despiste fácil: si se lo pones, te comes los dos primeros bytes de la táctica y todo lo demás se descoloca.

### Y su entrenador acaba antes

Otra diferencia que rompe lectores: **el entrenador de un club extranjero termina después de su nombre corto**. No tiene nombre largo ni los seis textos.

Igual que sus jugadores no tienen país de nacimiento ni los diez textos de base de datos. La regla general es sencilla de recordar: **en un club extranjero no hay nada que sea "de base de datos"**, solo lo que el simulador necesita para jugar.

## La cuenta que lo valida todo

Antes de seguir, la comprobación que confirma que la cabecera está bien leída, porque **si falla aquí, todo lo demás falla en cascada y sin avisar**.

Desde donde acaba el palmarés, sumando **176 bytes de táctica dibujada y 7 de táctica de equipo**, tienes que caer exactamente en el byte `02` del entrenador.

Si caes en cualquier otra cosa, el error no está en la táctica: está más atrás, en la cabecera o en el historial. Los sitios donde más se pierde la cuenta son los ceros de relleno del aforo y los socios, el segundo filial, y las plazas de pie de 6.0.

## El historial

Después de la cabecera viene el pasado del club, en este orden exacto:

| Campo | Tamaño | Notas |
|---|---|---|
| Grupo de Segunda B | 1 byte | `0` si el club no es español |
| Las últimas diez ligas | **10 o 20 bytes** | ver abajo |
| Temporadas en Primera | 1 byte | |
| Partidos jugados | 2 bytes | |
| Partidos ganados | 2 bytes | |
| Partidos empatados | 2 bytes | |
| Goles a favor | 2 bytes | |
| Goles en contra | 2 bytes | |
| Puntos | 2 bytes | |
| Veces campeón | 1 byte | |
| Veces subcampeón | 1 byte | |
| Posiciones por jornada | 42 o 46 bytes | **según la versión** |

Las últimas diez ligas son el sitio donde más se falla, porque **su tamaño cambia con la versión**:

- En **5.0** son **diez bytes**: solo el puesto en el que quedó cada año.
- En **6.0** son **veinte**: parejas de puesto y división, y la división se codifica `0` Primera, `1` Segunda, `2` Segunda B, `3` Tercera.

Y las posiciones por jornada son **42 en 5.0 y 46 en 6.0**.

Las dos cosas se deciden con **la versión del bloque**, esos dos bytes que van justo detrás del puntero. Pero cuidado, porque **no hay un solo umbral, hay dos**:

- La **cabecera** es la de 6.0 **solo si la versión es exactamente `0x20D`**.
- El **historial** lleva pares y 46 jornadas **si la versión es `0x200` o mayor**.

La diferencia importa por las ediciones argentinas, que valen `0x203`: tienen el historial de 6.0 y **la cabecera de 5.0**. Con un solo umbral ese caso sale mal — y no falla ruidosamente, te da un aforo de ocho mil donde debería haber ciento y pico.

La tabla completa de versiones está en [la referencia](v56-referencia.html). Y no lo decidas nunca por el nombre del fichero ni por la carátula del juego.

Comprobación rápida de que has acertado: los números tienen que ser creíbles. El Barcelona debe darte sesenta y tantas temporadas en Primera, cerca de dos mil partidos jugados y más goles a favor que en contra. Si te salen más partidos ganados que jugados, te has descolocado.

## El palmarés: catorce números

Van seguidos, en parejas de participaciones y títulos, y en este orden:

1. Copa de la UEFA — participaciones
2. Copa de la UEFA — títulos
3. Copa del Rey — participaciones
4. Copa del Rey — títulos
5. Copa de Europa — participaciones
6. Copa de Europa — títulos
7. Recopa — participaciones
8. Recopa — títulos
9. Supercopa de España — participaciones
10. Supercopa de España — títulos
11. Intercontinental — participaciones
12. Intercontinental — títulos
13. Supercopa de Europa — participaciones
14. Supercopa de Europa — títulos

Cada uno ocupa **un byte**, así que el palmarés propiamente dicho son **siempre catorce**.

Lo que cambia con la edición es **lo que viene detrás**: un bloque extra de 0, 28 o 34 bytes.

| Bloque extra | Total | Dónde | Qué lleva |
|---|---|---|---|
| 0 | 14 | 5.0, 5.0 Oro, primera temporada de 6.0 Oro | nada |
| 28 | 42 | 6.0, segunda temporada de 6.0 Oro, las dos de Apertura | casi siempre ceros |
| 34 | 48 | **Premier y Calcio** | **las competiciones de esa liga** |

Y son **estos tres y ningún otro**: probando las cuatro longitudes que se han llegado a proponer sobre los clubes nacionales de las ocho bases, la de 34 en total **no acierta ni una sola vez**. Las otras tres reparten así:

| Edición | Qué longitud gana |
|---|---|
| 5.0 · 5.0 Oro | 14 en todos |
| 6.0 · Apertura 98 | 42 en todos |
| **6.0 Oro** | **las dos**: 14 en los 126 equipos de la temporada vieja, 42 en los 128 de la nueva |
| Premier · Calcio | 48 |

Lo de Premier es bonito de comprobar: al Manchester United le salen ahí un 9, un 1, un 11 y un 10 — sus FA Cups, su Copa de la Liga, sus Ligas y sus Charity Shields tal como estaban en 1997.

O sea que esto **no son tres tamaños arbitrarios**: es un tronco común de catorce números y una extensión con los trofeos que existen en cada edición. El de 34 **no está en ninguna documentación anterior**; salió de escribir un lector siguiendo esta misma guía y comprobar que Premier y Calcio no caminaban.

Aquí hay un truco que usan todos los lectores serios, porque la versión no basta para decidirlo: **se prueban los tamaños y se queda el que funciona**. ¿Cómo se sabe cuál funciona? Porque con el correcto, y solo con él, el recorrido de las fichas de jugador termina justo donde empieza el equipo siguiente. Los demás dejan la cuenta descuadrada.

Si tu lector funciona en 5.0 y en 6.0 pero no en Premier ni en Calcio, **es esto**.

Es un buen ejemplo de cómo se trabaja con este formato: cuando un dato es ambiguo, **se prueba y se valida con la comprobación de que todo encaje**.

Que el palmarés está bien leído se comprueba solo: al Barcelona le tienen que salir veintidós Copas del Rey y tres Recopas, que es lo que llevaba en 1996.

Toda esta parte ocupa bastante y desplaza lo que va después, así que aunque casi nunca se toque, hay que saber recorrerla para llegar a la táctica y a los jugadores.

## La táctica dibujada

Ciento setenta y seis bytes que describen **dónde se coloca cada jugador en el campo**. Son once jugadores por dieciséis bytes cada uno, y cada jugador guarda tres cosas:

- **Su zona**: el rectángulo por el que se puede mover, dado como esquina y tamaño.
- **Dónde se pone defendiendo**, cuando el equipo no tiene el balón.
- **Dónde se pone atacando**, cuando sí lo tiene.

Los ejes van así: uno recorre el campo a lo largo, con el cero en tu propia portería; el otro a lo ancho, con el centro alrededor del valor 88.

El primer jugador es siempre el portero, y **es idéntico en todas las formaciones del juego**: misma zona y misma posición. Es una buena forma de comprobar que estás leyendo bien — si tu portero sale distinto, has empezado a contar en el sitio equivocado.

### Cuidado con una interpretación que circula

Hay documentación por ahí que lee esos cuatro primeros valores como **dos esquinas** del rectángulo, en vez de como una esquina más el ancho y el alto. Es un error fácil de cometer y difícil de notar, porque ambas lecturas dan números plausibles.

Los datos lo resuelven: comprobando las once posiciones de todas las formaciones, **las posiciones de defender y atacar caen siempre dentro del rectángulo** si se lee como esquina y tamaño, y no si se lee como dos esquinas. Son más de trescientos casos y no falla ninguno.

Si tus jugadores aparecen colocados fuera de su propia zona, es esto.

Un detalle bonito: el número de jugadores cuya zona empieza pegada a la portería reproduce el primer número de la formación. En un 4-4-2 hay cuatro.

## Después: el entrenador y los jugadores

Al final del bloque va el entrenador —marcado con un `02` en vez del `01` de los jugadores— y detrás la lista de fichas, una tras otra hasta que empieza el bloque del equipo siguiente.

## El presupuesto tiene un techo, y pasarse cuelga el juego

Son dos campos distintos y conviene no confundirlos: uno es **el dato que se enseña en la ficha del club** y el otro es **el dinero con el que juegas de verdad**. El segundo es el que importa.

El campo ocupa cuatro bytes, así que técnicamente admite cifras enormes. **Pero el juego no.** Por encima de cierto valor se **niega a cargar el equipo**, y el fallo aparece al entrar en la partida, no al guardar — con lo que cuesta relacionarlo con lo que tocaste.

Dónde está ese techo lo decide el ejecutable de cada edición, así que la única referencia fiable es **lo que trae el juego de fábrica**:

| Edición | Presupuesto más alto de fábrica |
|---|---|
| 5.0, 5.0 Oro, 6.0, 6.0 Oro | **1.000** (Real Madrid y Barcelona, clavados ahí) |
| Premier y Calcio | 1.500 |
| Apertura 97 | 25.000 (va en otra moneda) |
| Apertura 98 | 75 |

O sea que **1.000 no es el tope del motor** —el mismo formato trae 1.500 y 25.000 en otras ediciones—, pero sí es hasta donde llegó Dinamic en las españolas. Subir de ahí es probable que funcione y **hay que comprobarlo en el juego**, equipo por equipo.

Y para hacerse una idea de la escala: la mediana de las ediciones españolas es **75**. Los mil del Madrid son la excepción, no la norma.

## Entre el estadio y el nombre largo: el país y la latitud

Aquí circula el aviso de que hay «dos bytes que nadie ha identificado y que están en todos los equipos». **Ni son dos en todas las ediciones, ni están sin identificar.** Se sabe qué son los dos.

### El primero es el país del club

Comprobado contra el país que el juego le asigna a cada equipo: **acierta en los 3.002 clubes** de las ocho bases. No es un byte misterioso, es la nacionalidad del club, con los mismos códigos que usan los jugadores.

### El segundo es la latitud, y solo existe en 6.0

Este no está en todas las ediciones. Aparece en **6.0, 6.0 Oro y Apertura 98** —las de la versión de fichero más moderna— y **no existe en 5.0, 5.0 Oro, Apertura 97, Premier ni Calcio**, donde detrás del país viene ya el nombre largo. Es exactamente la misma diferencia que separa los demás campos de las dos versiones.

Y lo que guarda es **la latitud de la ciudad del club, en grados**, con signo. Se ve solo al agrupar por países y comparar con el mapa:

| País | Valor medio en el fichero | Latitud real |
|---|---|---|
| España | **40,0** | 40 |
| Portugal | 38,9 | 39 |
| Italia | 43,4 | 43 |
| Austria | 47,4 | 47 |
| Alemania | 50,6 | 51 |
| Holanda | 51,6 | 52 |
| Inglaterra | 52,0 | 53 |
| Escocia | 55,3 | 56 |
| Chile | **−33,0** | −33 |
| Uruguay | −33,0 | −34 |

La desviación media es de **medio grado**. Y ninguno de los valores se sale de −37 a 69, que es un rango de latitudes posible.

**Dos detalles que rematan la comprobación**, y que son de esos que convencen más que la tabla:

- El hemisferio sur se guarda **como número negativo** — el byte va con signo. Los clubes argentinos, chilenos y uruguayos salen en negativo, como toca.
- El valor más bajo de España es **28**, y ese es exactamente el paralelo de **Canarias**. Los clubes canarios están donde deben estar.

### Aun así, cópialos

Que ahora se sepan no quita el aviso práctico, que es el que cuesta caro: si reconstruyes el bloque campo a campo y **te los dejas fuera**, el bloque queda descuadrado. Y la forma en que falla es de las peores — el juego **no arranca** y solo dice que la aplicación no puede continuar, sin explicar por qué.

Si vas a reescribir el bloque en vez de editarlo en el sitio, y no vas a cambiar de ciudad al club, cópialos tal cual.

## Sobre recorrer la lista de jugadores

Dos formas de hacerlo, y una es mala.

**La mala:** buscar el patrón de una ficha por el fichero. Funciona la mayoría de las veces y falla justo donde duele: en algunos bloques extranjeros **se inventa fichas fantasma** cuyo supuesto nombre es en realidad el final del nombre anterior pegado a la cabecera de la ficha siguiente. Si luego escribes sobre esa ficha imaginaria, borras una cabecera de verdad y **partes la cadena**: el equipo se queda sin plantilla.

**La buena:** recorrer el flujo de forma determinista desde el principio del bloque, avanzando ficha a ficha con las longitudes que cada una declara, y comprobando al final que se llega justo donde empieza el equipo siguiente. Si no cuadra, es que algo se ha entendido mal — y más vale saberlo que seguir adelante.

## La invariante de todo el bloque

**El bloque entero mide lo que mide.** Puedes cambiar cualquier valor numérico sin miedo, porque ocupan siempre lo mismo. Pero si acortas un texto y no compensas, o alargas otro y te pasas, el bloque cambia de tamaño y arrastras todo el fichero.

La comprobación que zanja la duda es siempre la misma: leer, volver a escribir sin cambiar nada, y verificar que el resultado es idéntico byte a byte al original.
