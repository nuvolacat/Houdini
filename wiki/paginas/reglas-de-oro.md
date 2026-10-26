# Reglas de oro

> Documentación hecha por la comunidad con fines de interoperabilidad y modding. Trabaja siempre sobre tu propia copia del juego. PC Fútbol es una marca de sus titulares; este proyecto no está afiliado a ellos.

Cinco cosas que hay que tener claras antes de tocar un byte. Saltárselas es la causa de casi todos los ficheros rotos.

## 1. El tamaño manda

En estos juegos, muchísimas estructuras se localizan **por posición**, no por búsqueda. Si alargas un nombre y el bloque crece, todo lo que va detrás se desplaza y el juego lee basura donde esperaba un dato.

La consecuencia práctica es que **editar en el sitio no puede cambiar la longitud**. Si un nombre nuevo es más corto que el hueco, se rellena con espacios; si es más largo, no cabe y hay que buscar otra vía.

Esto vale también para el ejecutable del juego. Ahí es todavía más estricto: cambiar un solo byte de tamaño desplaza el código y el programa deja de arrancar. Se sustituyen valores, nunca se añade ni se quita.

> La prueba que lo cierra todo: lee el fichero, vuélvelo a escribir sin cambiar nada y compara. Si no sale **idéntico byte a byte**, tu lector no ha entendido algo y aún no estás listo para escribir.

## 2. El texto va cifrado

Ningún texto se guarda en claro. En 4.0, 5.0, 6.0 y la familia de 7, 2000 y 2001 cada byte va pasado por un XOR fijo (en 4.0 con sus propios acentos); en 3.0, y en los rótulos `.GRC` de 3.0 y 4.0, el cifrado depende de la longitud de la cadena y de la posición de cada letra.

No es más que una codificación —se descubre en cinco minutos con un editor hexadecimal—, pero explica por qué al abrir el fichero no ves ni un nombre reconocible y parece que te has equivocado de sitio.

## 3. Cada dato tiene su tamaño, y hay que respetarlo

| Se guarda como | Ocupa | Rango | Se usa para |
|---|---|---|---|
| `u8` | 1 byte | 0-255 | dorsal, atributos, país |
| `u16` | 2 bytes | 0-65535 | punteros de equipo, longitud de texto, año |
| `u24` | 3 bytes | 0-16,7 M | aforo y socios en 5.0 |
| `u32` | 4 bytes | 0-4.294 M | aforo y socios en 6.0 |

Los números de varios bytes van **con el byte bajo primero**, que es la convención de los procesadores de Intel y se cumple en todo el formato.

Con un ejemplo, porque es donde más se falla: si en el fichero encuentras los bytes `7B 04`, el número **no** es 0x7B04. El primero es el bajo, así que el valor es **0x047B**, es decir 1147. Leerlo al revés da 31.492 — un número perfectamente plausible que te llevará a buscar un equipo que no existe.

Un atributo de jugador es un solo byte, así que 255 es el techo absoluto; pero el juego solo entiende de 0 a 99, y por encima hace cosas raras.

## 4. Estar en la base de datos no es estar en el equipo

Un error muy común. Que la ficha de un jugador exista dentro del bloque de un club **no significa** que el juego lo vaya a alinear. Eso lo deciden otros campos de la propia ficha: su posición en el orden de la plantilla y su situación en el club.

Por eso verás jugadores marcados como baja que siguen apareciendo: están en la base de datos —el juego los enseña a propósito, son las bajas de aquella temporada— pero no cuentan para el equipo.

## 5. Trabaja siempre sobre una copia

Obvio, pero conviene decirlo: haz copia del fichero original antes de nada, y guárdala aparte de la carpeta del juego. Cuando algo se rompe, casi nunca se rompe de forma evidente — el juego arranca, y el fallo aparece tres pantallas después.

Y prueba los cambios **dentro del juego**, no solo en el editor. Que un fichero se lea bien no garantiza que el juego lo entienda igual.
