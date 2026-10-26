# Primeros pasos: leer el fichero desde cero

Si vienes sin saber nada del formato y quieres escribir tu propio lector, esta es la ruta más corta. Cada paso es comprobable, así que sabes si vas bien antes de seguir.

## Antes de empezar

**Trabaja sobre una copia.** Y ten a mano el original sin tocar, porque el paso final consiste en compararlos.

Los datos que vas a leer están en la carpeta `DBDat` de la instalación del juego. El fichero grande, el que empieza por `EQ` o se llama `EQUIPOS`, es el que tiene todos los equipos y jugadores.

Algunos contenedores —los gráficos de las pantallas y la música— no se instalan en el disco duro y se quedan en el CD. Para esos hay que copiarlos de tu CD del juego.

## Paso 1: encontrar los equipos

Busca en el fichero, **en texto plano**, esta cadena:

```
Copyright (c)
```

Aparece una vez por equipo, seguida del año y de `Dinamic Multimedia`. Son 36 caracteres y no están cifrados.

**Cómo sabes que vas bien:** el número de veces que aparece debería ser el número de equipos del juego — unos cuantos cientos. Si te sale una sola vez o ninguna, no estás leyendo el fichero que crees.

## Paso 2: leer un texto

Ponte justo detrás de la firma de un equipo. A pocos bytes está su nombre, guardado así: dos bytes con la longitud, y después esos bytes de texto **cifrados**.

El cifrado es un XOR con `0x61` byte a byte. Descífralo y tendrás el nombre del club.

**Cómo sabes que vas bien:** te sale el nombre de un equipo real. Si sale algo casi legible pero desplazado —le falta una letra al principio o le sobra— has empezado a contar en el sitio equivocado por uno o dos bytes.

Truco: muchos editores hexadecimales permiten aplicar una máscara XOR a toda la vista. Con `0x61` puesto, verás el fichero descifrado y localizar cosas se vuelve trivial.

## Paso 3: recorrer la cabecera del equipo

A partir del nombre, los campos van seguidos y en orden fijo: estadio, país, nombre largo, aforo, dimensiones del campo, año de fundación, socios, presidente, presupuestos, patrocinador…

**Aquí está la primera trampa.** El tamaño de algunos campos **depende de la versión**, y la versión está en un campo del propio bloque, no en el nombre del fichero. Léelo primero.

**Cómo sabes que vas bien:** los números tienen que tener sentido. Un aforo entre unos miles y unos cientos de miles, un año de fundación entre 1880 y 1990, un campo de entre 60 y 75 metros de ancho, y un nombre de presidente legible. Si te salen cifras absurdas, te has descolocado.

**Pruébalo con varios juegos, no solo con uno.** Un lector puede funcionar perfectamente en 5.0 y fallar en 6.0 porque esta trae campos que aquella no tiene. Con las ocho bases que existen —5.0, 6.0, sus ediciones de Oro, Premier, Calcio y las dos de Apertura— si el presidente sale legible en todas, tu lector es correcto.

**Y aquí está la segunda trampa, que es la que más tiempo cuesta:** varios números ocupan **más bytes de los que usan**. El aforo, los socios y los presupuestos ocupan cuatro y solo llenan tres; cada dimensión del campo ocupa dos y solo llena una. El resto son ceros de relleno.

Si avanzas solo lo que ocupa el valor, te vas desplazando poco a poco y el fallo no aparece hasta varios campos después, cuando ya no sabes de dónde viene.

Esta comprobación no es solo para depurar: es la misma que sirve para **distinguir un club nacional de uno extranjero**, porque sus fichas tienen distinta longitud.

## Paso 4: llegar a los jugadores

Detrás de la cabecera viene el historial, el palmarés y las tácticas. Son tramos que puedes saltar sin interpretarlos, **pero cuidado: dos de ellos cambian de tamaño según la versión** —las últimas diez ligas y las posiciones por jornada— y un tercero, el palmarés, admite tres tamaños distintos.

Si no estás seguro de cuál toca, **pruébalos**: solo con el correcto la lista de jugadores terminará justo donde empieza el equipo siguiente.

Cada ficha empieza con un byte que la identifica: **`01` un jugador, `02` un entrenador**. Vas leyendo fichas hasta que el siguiente byte no sea ninguno de los dos: ahí se acabó el equipo.

**Cómo sabes que vas bien:** al terminar deberías estar justo donde empieza la firma del equipo siguiente. Si te pasas o te quedas corto, alguna ficha se ha leído mal.

Esta comprobación es la más valiosa de todas, porque **te dice que lo has entendido bien sin necesidad de mirar el resultado**. Si cuadra en los cientos de equipos del fichero, tu lector es correcto.

## Paso 5: la prueba definitiva

Cuando puedas leer el fichero entero, haz esto: **vuelve a escribirlo sin cambiar nada y compáralo con el original**.

Si sale idéntico byte a byte, has entendido el formato. Si no, hay algo que estás leyendo mal o algo que estás perdiendo por el camino — y es mucho mejor descubrirlo así que cuando el juego se cuelgue.

Es la prueba que hay que superar **antes** de escribir el primer cambio.

## Y a partir de ahí

Con eso ya tienes el esqueleto. Lo demás son detalles que puedes ir añadiendo:

- Las [tablas de códigos](v56-tablas.html) para traducir los números a demarcaciones, países y demás.
- La [paleta](v56-paleta.html) si vas a tocar imágenes.
- Los [DBC](v56-dbc.html) cuando choques con el límite de longitud de los textos.

## El error más común

Cambiar el tamaño de algo. **Todo el formato se sostiene sobre posiciones fijas**: si un texto crece un byte, todo lo que va detrás se desplaza y el juego empieza a leer cada campo un poco corrido.

Así que mientras aprendes, edita solo **números**, que ocupan siempre lo mismo. Los textos, cuando ya te fíes de tu lector.
