# El texto en 4.0 y 4.5

Cómo se guardan los nombres y los textos largos en los ficheros de equipo de la 4.x, y el cifrado distinto que usan los textos de los menús. Se parece al de 5.0 y 6.0 lo justo para engañarte.

## Los caracteres: XOR `0x61`, pero los acentos no son latin-1

La base es la misma que en las versiones posteriores: cada byte del fichero es el carácter pasado por un **XOR con `0x61`**.

```
byte en el fichero = carácter XOR 0x61
```

La `B` (`0x42`) se guarda como `0x23`; la `a` (`0x61`), como `0x00`. Por eso las zonas de texto de un volcado están llenas de ceros: son aes.

La diferencia está en los acentos. Si al quitar el XOR te sale un valor con el bit alto encendido (`0x80` o más), **no es un carácter latin-1**: es un carácter del juego de caracteres de MS-DOS, el **Code Page 437**. El juego trabaja en DOS y guarda el texto tal como lo pinta la pantalla de texto de la época.

| Al quitar el XOR sale | Es | Se guarda en el fichero |
|---|---|---|
| `0x82` | é | `0xE3` |
| `0xA0` | á | `0xC1` |
| `0xA4` | ñ | `0xC5` |
| `0xA5` | Ñ | `0xC4` |

Las 48 posiciones de `0x80` a `0xAF` cubren las vocales con tilde, diéresis y circunflejo, la ñ, la ç, ª, º, ¿, ¡ y las comillas « ». Dos de ellas, `0x9E` y `0x9F`, son símbolos de DOS que no tienen ningún uso en nombres de fútbol; trátalas como huecos.

El error típico es descifrar con XOR y luego interpretar el resultado como latin-1. Los nombres sin tildes salen perfectos y te confías; luego «Coruña» sale con un símbolo raro en lugar de la ñ, y parece que el cifrado esté mal cuando lo que está mal es la tabla.

### Lo que no cabe

Al escribir, cualquier carácter que no esté en ASCII ni en esa zona alta **no tiene representación**. Si metes una `ø` o una `ł`, lo sensato es pasarla antes a su letra base (`o`, `l`) y quitar los diacríticos que el juego no conoce (`ć` → `c`). Las comillas tipográficas y las rayas largas tampoco existen: pásalas a `"` y `-`.

## Las cadenas: un byte de longitud

Aquí es donde se separan de verdad de 5.0 y 6.0. Cada cadena va precedida de su longitud, y **la longitud ocupa un solo byte**:

```
[longitud: 1 byte] [caracteres cifrados...]
```

Ni dos bytes, ni relleno detrás. Con lo que el techo de cualquier nombre es **255 caracteres**, y una cadena vacía es un solo byte `00`.

Si vienes de 5.0 y lees la longitud como dos bytes, te comes el primer carácter y a partir de ahí todo se desplaza en uno. El síntoma es claro: el primer nombre sale casi bien y todo lo que va detrás es basura.

## Los textos largos van troceados

La biografía del jugador y la información y las declaraciones del entrenador son demasiado largas para una sola cadena. Se guardan **en trozos**:

```
[N: 1 byte]
[longitud: 1 byte][caracteres]   ← trozo 1
[longitud: 1 byte][caracteres]   ← trozo 2
...                               ← N + 1 trozos en total
```

Ojo al detalle: el primer byte dice cuántos trozos hay **menos uno**. Un `00` significa un trozo, no ninguno. Un texto vacío es `00 00`: un trozo de longitud cero.

Para leer, se concatenan los trozos y listo; el corte no tiene significado. Para escribir, los editores de la comunidad trocean cada 16 caracteres. **Los ficheros originales no siempre siguen esa medida**, así que si vas a comparar byte a byte un fichero leído y reescrito, conserva los trozos originales de los textos que no hayas tocado.

## Puedes cambiar la longitud

Al contrario que en el `EQUIPOS.PKF` de 5.0 y 6.0, aquí **un nombre puede crecer o encoger**. Cada `.DBC` es un solo equipo, se lee de principio a fin y no hay posiciones apuntando a su interior, así que basta con reescribir el fichero entero con las longitudes nuevas.

Lo que no puedes es meter una cadena de más de 255 caracteres, ni un trozo de texto largo de más de 255.

## Los textos de los menús: otro cifrado

Los ficheros `RES*.GRC` (los rótulos y botones de la interfaz) **no usan el XOR fijo**. Usan uno que depende de la longitud de la cadena y de la posición de cada letra:

```
carácter[i] = byte[i] XOR (0xC0 + longitud + i)     (quedándote con el byte bajo)
```

Es simétrico: la misma operación cifra y descifra. Como la clave cambia con la longitud, **una misma palabra se guarda con bytes distintos según lo larga que sea la cadena** que la contiene, y no la encontrarás buscándola cifrada.

Estos textos sí tienen el tamaño fijo: van en una estructura con posiciones, así que se editan en el sitio, rellenando con espacios o recortando. Y van siempre en mayúsculas. El detalle está en [pantallas y sonido](pcf4-pantallas-sonido.html).

## Siguiente paso

Con esto ya puedes leer cualquier nombre. [El fichero de equipo](pcf4-equipo.html) explica dónde está cada uno.
