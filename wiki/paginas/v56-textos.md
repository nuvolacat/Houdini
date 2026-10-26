# Los nombres que el juego inventa

Cuando el juego necesita un jugador que no existe —un canterano, un relleno de plantilla— **se inventa el nombre**. Y no lo hace al azar: tiene listas de nombres y apellidos **por país**, para que un jugador italiano se llame como un italiano.

Esas listas viven en un contenedor propio y **casi nadie sabe que se pueden cambiar**.

## Qué hay dentro

Doscientas catorce listas, organizadas así:

| Lista | Cuántas | Qué contiene |
|---|---|---|
| `NOMBRES` | 108 | Nombres de pila, una lista por país |
| `APELLIDO` | 106 | Apellidos, una lista por país |
| `PAISES` | 4 | **El nombre de cada país, en cuatro idiomas** |

El número que sigue al nombre **es el código del país**. La lista número uno es la de Albania, y si la descifras verás apellidos albaneses reales: Shehi, Dervishi, Gjoni, Çanakue, Qato, Toskue, Vila.

Las cuatro listas de `PAISES` no son nombres de personas: son **cómo escribe el juego el nombre de cada país**, una lista por idioma —español, francés, inglés e italiano— con ciento veintiocho países cada una. Ahí es donde se cambia si quieres que un país aparezca con otro nombre.

Con esas hay un cuidado extra: **el juego las indexa por posición**, así que se puede cambiar un nombre por otro pero no añadir ni quitar entradas, porque desplazaría a todos los demás países.

## Cómo está construida cada lista

Cada entrada es un bloque con una estructura propia que **no se parece a nada más del juego**:

```
"DMLT"          4 bytes, la marca del bloque
cuánto ocupan   4 bytes  (ver abajo)
cuántos textos  4 bytes
    ── y luego, repetido tantas veces como diga el contador ──
longitud        2 bytes
texto           esos bytes, cifrados con el XOR de siempre
```

Es decir: **el bloque dice cuántos nombres trae**, y cada nombre lleva su longitud por delante. No hay separadores ni terminadores; se va avanzando con las longitudes.

### Los cuatro bytes del medio: cuánto sitio hay que reservar

Ese campo se describe muchas veces como «un identificador que no se sabe para qué sirve». **Sí se sabe, y hay que calcularlo bien si escribes el bloque tú.**

Es **la suma de las longitudes de todos los textos más el número de textos**. O dicho de la forma en que se entiende: **lo que ocuparían los nombres si cada uno terminase en un cero**, que es como los deja el juego en memoria una vez descifrados.

La fórmula acierta en **las 435 listas** de las dos ediciones que traen este fichero. En todas, sin una sola excepción.

Un ejemplo para comprobarlo de un vistazo: la lista de apellidos de Brasil trae **377 apellidos** que suman **2.310 letras**. El campo vale **2.687**, que es 2.310 más 377.

**Por qué importa:** el juego usa ese número para reservar memoria antes de leer la lista. Si añades nombres y lo dejas como estaba, le estás diciendo que reserve menos de lo que vas a darle. Así que al reescribir el bloque **hay que recalcularlo**, no conservarlo.

Para hacerte una idea del tamaño: la lista de España trae 105 nombres de pila y 522 apellidos.

## La trampa al programar un lector

Un aviso que ahorra una tarde entera. **El índice de este contenedor es el mismo que el de los escudos y las fotos**, así que la tentación es reutilizar el lector que ya tengas.

No funciona, y lo peor es *cómo* falla: los lectores de imágenes suelen filtrar las entradas por el patrón de nombre de un escudo. Aquí las entradas se llaman `APELLIDO.1`, no encajan con ese patrón, y el resultado es **cero entradas** — parece un fichero vacío o corrupto cuando está perfectamente bien.

Hay que recorrer el índice sin filtrar por el nombre.

## Para qué sirve cambiarlas

Es más útil de lo que parece:

- **Actualizar los nombres a la época.** Las listas son de los noventa; los canteranos que genera el juego se llaman como se llamaba la gente entonces.
- **Añadir países que se quedaron cortos.** Algunas listas tienen muy pocas entradas, y los jugadores generados de esos países se repiten constantemente.
- **Corregir la ortografía.** Hay acentos y caracteres especiales que quedaron mal en el original.

## Al editarlas

La regla de siempre: **el bloque de cada lista tiene su tamaño**. Puedes cambiar nombres por otros de la misma longitud sin problema. Para meter más entradas hay que reempaquetar el contenedor y ajustar el índice, con lo que eso implica.

Y un aviso sobre los acentos: estos textos usan la tabla de caracteres de MS-DOS. Una letra acentuada escrita con una tabla moderna saldrá como un símbolo raro dentro del juego.
