# Cómo se guarda el texto en 5.0 y 6.0

Lo primero que desconcierta al abrir el fichero: no se ve ni un nombre. No es que estés en el sitio equivocado — el texto está cifrado, y con algo muy sencillo.

## El cifrado

Cada byte del texto está pasado por una operación **XOR con el valor `0x61`**. Nada más. Y como el XOR es su propio inverso, descifrar es exactamente la misma operación:

```
byte en el fichero  =  letra  XOR  0x61
letra               =  byte en el fichero  XOR  0x61
```

No es más que una codificación; se descubre en un rato con un editor hexadecimal. Pero explica por qué un volcado en crudo parece basura.

Un detalle que ayuda muchísimo a orientarse: el byte `0x00`, al descifrarlo, da la letra **`a`**. Como el relleno del fichero está lleno de ceros, en un volcado descifrado verás rachas largas de `aaaaaaaa`. Eso es hueco vacío, no texto.

## Cómo se delimitan las cadenas

Los textos no acaban en un byte cero como en tantos formatos. Llevan **la longitud por delante**:

```
[longitud]  [00]  [bytes cifrados del texto]
```

La longitud son dos bytes, con el byte bajo primero — así que un texto de 12 caracteres empieza por `0C 00`.

Ese `00` de la segunda posición es el que se ve como `a` al descifrar. En la práctica, cuando recorres el fichero descifrado, cada nombre aparece precedido de una `a` suelta. Es la pista más útil para reconocer dónde empieza y acaba cada cadena sin llevar la cuenta de bytes.

## La regla que no se puede saltar

Aquí está la trampa que rompe más ficheros. **El hueco de cada texto tiene un tamaño reservado y no se puede pasar de ahí.**

Si escribes un nombre más corto que el original, no pasa nada: se rellena con espacios y la longitud declarada se ajusta. Pero si escribes uno más largo, no cabe — y forzarlo desplaza todo lo que viene detrás, con lo que el juego empieza a leer cada campo un poco corrido y acaba mostrando disparates o colgándose.

Por eso los editores tienen un tope por campo que parece arbitrario. No lo es: es el hueco que dejó el fichero original.

> Hay una forma de saltarse este límite, pero no consiste en forzar el hueco: consiste en sacar el equipo a un fichero aparte donde las longitudes ya no están fijadas. Se explica en el capítulo de los DBC.

## Acentos y eñes

Los caracteres acentuados y la eñe también pasan por el mismo XOR, pero **su valor de partida no es el del teclado moderno**: los juegos son de la época de MS-DOS y usan la tabla de caracteres de entonces.

En la práctica esto importa poco si copias texto de un sitio a otro dentro del mismo juego. Importa mucho si generas texto desde fuera: una `ñ` escrita con la tabla equivocada sale como un símbolo raro dentro del juego.

## Un truco para leerlo a mano

Si quieres inspeccionar el fichero sin herramientas, la mayoría de editores hexadecimales permiten aplicar una máscara XOR a la vista. Poniendo `0x61` verás el fichero descifrado directamente sobre la pantalla, y localizar un equipo es tan fácil como buscar su nombre.
