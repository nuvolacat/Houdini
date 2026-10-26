# PCF 3.0: el texto

Cómo están guardados los nombres en las bases `.DBC` de 3.0: un cifrado que depende de la longitud y la posición, y un prefijo de longitud y una página de códigos que cambian de un fichero a otro.

## El cifrado

Es una codificación del texto, no una protección. No es el XOR fijo de 5.0 y 6.0. Aquí cada byte se combina con un valor que depende de **la longitud de la cadena** y de **la posición de la letra**:

```
claro[i] = cifrado[i] XOR ((0xC0 + longitud + i) AND 0xFF)
```

Donde `longitud` es la de la cadena entera e `i` empieza en 0. La operación es su propia inversa: la misma fórmula cifra y descifra.

Es exactamente el mismo esquema que usan los ficheros de rótulos `.GRC` de 3.0 y de 4.0, así que si ya tienes uno, tienes el otro.

La consecuencia práctica: **la misma palabra se cifra distinto según lo larga que sea la cadena**. Si buscas `Barcelona` cifrado en el fichero no lo encontrarás buscando los bytes de otra aparición, porque las letras de `Barcelona` se cifran de una forma dentro de una cadena de 9 caracteres y de otra dentro de `F.C. Barcelona`. Y si cambias la longitud de un texto, tienes que volver a cifrarlo entero, no solo las letras nuevas.

## Cada texto lleva su longitud delante

Cada campo es `[longitud][bytes cifrados]`. El ancho de ese prefijo **no es el mismo en todos los ficheros**:

| Fichero | Prefijo |
|---|---|
| `LIG94951.DBC`, `LIG94952.DBC` | **1 byte** |
| `COMMENT.DBC` | 1 byte |
| `LIGA.DBC`, `COPAREY.DBC`, `EUROPA.DBC`, `UEFA.DBC` | **2 bytes**, el bajo primero |

Para el resto, lo fiable es no suponerlo: prueba a leer el principio del fichero con los dos anchos y quédate con el que produzca más textos legibles seguidos. Es lo que hay que hacer de todas formas si no sabes de qué fichero se trata.

Entre texto y texto van datos binarios —dorsales, medias, fechas, goles— **sin cifrar**. El fichero no marca dónde empieza un texto: hay que localizarlos.

## Cómo localizar los textos

Al no haber índice, lo que se hace es recorrer el fichero byte a byte probando: «si esto fuera una longitud, ¿lo que viene detrás se descifra como texto?». Para que la prueba no se trague basura hace falta ser exigente:

- **El primer carácter es una letra sin acento o un dígito.** Es la prueba más barata y descarta casi todo: descifras un solo byte y, si no cuadra, sigues.
- **Casi todo son letras** y unos pocos signos (espacio, punto, guion, apóstrofo, barra, paréntesis, coma).
- **Pocos acentos.** El texto real es casi todo ASCII; la basura descifrada es casi toda bytes altos.
- **Una longitud razonable.** Entre 3 y 64 caracteres funciona bien en las bases de Liga.

Ese tope de 64 no es arbitrario. Con 30 se pierden cosas reales: hay nombres oficiales de club, nombres completos de jugador y lugares de nacimiento que pasan de 30 letras, y al no verlos se descuadra todo lo que va detrás. Por encima de unos 88 el escaneo empieza a colar falsos positivos.

Una excepción: los párrafos de `COMMENT.DBC` van troceados en líneas de unos 75 caracteres, por encima de ese tope. Ahí conviene usar los rótulos de apartado —`Novedades en el equipo`, `Sistema de juego`, `Objetivo en la Liga`— como anclas y recorrer lo que hay entre uno y otro como una secuencia limpia de `[longitud][texto]`. Entre bloque y bloque hay separadores binarios de dos o tres bytes que descolocan un recorrido sin anclas.

### La convención de la primera letra

En las bases de 3.0 hay cientos de textos con acentos dentro y **ni uno solo que empiece por una letra acentuada**. Es la convención de Dinamic: se escribe `Alvaro`, no `Álvaro`.

Respétala al escribir. No es solo estética: si un nombre empieza por acento, un lector que use la prueba de la primera letra no lo reconocerá como texto, y el jugador entero desaparecerá de su equipo.

## La página de códigos

El texto es de DOS, y aquí hay una pequeña trampa: **no todos los ficheros usan la misma página de códigos**.

| Ficheros | Página | Ejemplo |
|---|---|---|
| Las bases de Liga | **cp850** (DOS) | `ñ` = `A4`, `Ñ` = `A5`, `á` = `A0` |
| Las tablas de competición | **Latin-1** | `ñ` = `F1`, `á` = `E1` |

Si dudas con un fichero concreto, descífralo con las dos y quédate con la que dé letras acentuadas con sentido en vez de símbolos de dibujo de cajas.

Lo bueno es que el cifrado opera sobre bytes, no sobre letras: aunque te equivoques de página de códigos, si no tocas el texto el fichero sale idéntico. La página solo importa para enseñarlo y para escribirlo.

## ¿Se puede alargar un texto?

En las **bases de Liga, sí**. Y es una diferencia grande con 5.0 y 6.0.

Dentro de `LIG94951.DBC` y `LIG94952.DBC` no hay ni tabla de offsets ni punteros que apunten al propio fichero: los únicos punteros que hay apuntan a los ficheros de gráficos `.DGF`, que son otros ficheros. El juego **recorre** la base de principio a fin, así que si un texto crece y todo lo de detrás se desplaza, lo sigue leyendo bien.

Se ha comprobado alargando un apodo: el fichero crece y todos los equipos, plantillas, medias, dorsales, fechas y punteros de escudo se siguen leyendo exactamente igual. Lo que no se ha confirmado todavía es que el juego pinte bien un nombre más largo de lo que traía.

**El límite no lo pone el formato** —con un byte de longitud caben 255 caracteres— **sino el juego**: lo que le cabe en pantalla y en memoria. Como eso no se puede preguntar, la referencia prudente es lo más largo que el propio juego trae de fábrica:

| Campo | Lo más largo de fábrica |
|---|---|
| Apodo del jugador | 17 |
| Nombre completo del jugador | 30 |
| Entrenador, apodo / nombre | 15 / 30 |
| Club: nombre oficial / corto / largo | 30 / 19 / 23 |
| Estadio | 25 |
| Presidente | 29 |
| Patrocinador | 26 |

Hasta ahí el riesgo es bajo: son longitudes que el juego ya digiere. Más allá, pruébalo dentro del juego.

Si alargas un texto, recuerda que **todo lo que va detrás cambia de posición**. Si tu herramienta guardaba la posición de otros campos, tiene que volver a leer el fichero antes del siguiente cambio, o lo escribirá en el sitio de otro.

### Donde no se alarga

En las **tablas de competición** y en `COMMENT.DBC` no se ha comprobado que el juego no las lea por posición. Ahí haz lo de siempre: conserva la longitud, rellena con espacios lo que sobre y rechaza lo que no quepa.
