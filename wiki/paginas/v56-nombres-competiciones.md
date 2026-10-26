# Renombrar las competiciones

«Primera División» se puede convertir en el nombre comercial de hoy. Los nombres de las competiciones **son cadenas de texto dentro del ejecutable**, y ahí sí se pueden cambiar.

## No van cifradas

Detalle que sorprende después de pelearse con la base de datos: **estos textos están en claro**. No pasan por el XOR del resto del juego. Si abres el ejecutable con un editor hexadecimal y buscas «PRIMERA DIVISIÓN», lo encuentras tal cual.

Usan la codificación de Windows de la época, así que los acentos y la eñe son bytes altos: la `Ó` es `D3`, la `Ñ` es `D1`, la `ª` es `AA`.

## Cada competición aparece muchas veces

Aquí está la trampa, y es la razón de que los renombrados a medias se vean tan mal. **Un mismo nombre está escrito en varias formas distintas**, cada una para un sitio del juego:

Esta es la lista real de las trece competiciones y todas sus formas, tal cual están escritas dentro del ejecutable:

| Competición | Formas que hay que cambiar |
|---|---|
| Primera División | `PRIMERA DIVISIÓN` · `PRIMERA DIVISION` · `Primera división` · `LIGA 1ª DIVISIÓN` · `LIGA - 1ª DIVISIÓN` · `1ª DIVISIÓN` · `1ª DIVISION` · `1ª División` · `Liga 1ª` |
| Segunda División | `SEGUNDA DIVISIÓN` · `SEGUNDA DIVISION` · `Segunda División` · `Segunda división` · `LIGA 2ª DIVISIÓN` · `LIGA - 2ª DIVISIÓN` · `2ª DIVISIÓN` · `2ª DIVISION` · `2ª División` · `Liga 2ª` |
| Segunda B, cada grupo | `SEGUNDA B - GRUPO I` · `Segunda B - Grupo I` · `SEGUNDA DIVISIÓN B - GRUPO I` · `LIGA 2ª DIVISIÓN B - GRUPO I`, y lo mismo con II, III y IV |
| Copa del Rey | `COPA DEL REY` · `Copa del Rey` |
| Copa de Europa | `COPA DE EUROPA` · `Copa de Europa` · `Copa Europa` · `LIGA CAMP.` · `C. DE EUROPA` · `C. EUROPA` · `C. Europa` |
| Copa de la UEFA | `COPA DE LA U.E.F.A.` · `COPA DE LA UEFA` · `Copa de la U.E.F.A.` · `Copa de la UEFA` · `C. UEFA` |
| Recopa | `RECOPA DE EUROPA` · `Recopa de Europa` · `RECOPA` · `Recopa` |
| Supercopa de Europa | `SUPERCOPA DE EUROPA` · `Supercopa de Europa` · `SUPERCOPA EUR.` |
| Supercopa de España | `SUPERCOPA DE ESPAÑA` · `Supercopa España` · `SUPERCOPA ESP.` |
| Copa Intercontinental | `COPA INTERCONTINENTAL` · `Copa Intercontinental` · `INTERCONTINENTAL` · `C. INTERCONT.` · `C.INTERCONT.` · `Intercont.` |

Fíjate en que la Primera aparece **en nueve formas** y la Copa de Europa en siete. Si cambias solo una, el juego enseñará el nombre nuevo en una pantalla y el viejo en otra.

No todas están en todas las ediciones: en el ejecutable de 5.0 Oro se encuentran ocho de las nueve de Primera. **Búscalas todas y cambia las que existan.**

Y conviene conservar el aspecto de cada una: si la original estaba en mayúsculas, la nueva también, porque el juego cuenta con ello para que las pantallas queden alineadas.

## Lo que no se puede tocar

Junto a los nombres visibles hay **códigos internos** que parecen nombres pero no lo son: `LIGA1`, `LIGA2`, `LIGA2B`, `CEUROPA`, `CUEFA`, `CREY`. Son los prefijos con los que el juego construye los nombres de sus ficheros de calendario.

**Cambiarlos rompe el juego**, porque después irá a buscar ficheros que no existen. Se distinguen porque son cortos, sin espacios ni acentos.

## Cuánto cabe

La regla es la de siempre —el ejecutable no puede cambiar de tamaño— pero aquí hay un margen que se puede aprovechar.

Cada cadena termina en un byte cero, y detrás suele haber **más ceros de relleno**. El nombre nuevo puede ocupar el original más todos esos ceros, dejando siempre uno como terminador.

Es decir: no estás limitado a la longitud exacta del original, sino **a la del hueco real**. Y la diferencia es grande. Estos son huecos medidos en el ejecutable de 5.0 Oro:

| Cadena | Posición | Ocupa | Ceros detrás | Caben |
|---|---|---|---|---|
| `PRIMERA DIVISIÓN` | `0x23D230` | 16 | 4 | **19** |
| `SEGUNDA DIVISIÓN` | `0x23D19C` | 16 | 0 | **15** |
| `COPA DEL REY` | `0x23D6E4` | 12 | 4 | **15** |
| `COPA DE EUROPA` | `0x23E2DC` | 14 | 2 | **15** |
| `Copa de la UEFA` | `0x23E474` | 15 | 1 | **15** |
| `C. UEFA` | `0x23E484` | 7 | 1 | **7** |
| `RECOPA DE EUROPA` | `0x23F7B4` | 16 | 4 | **19** |
| `SUPERCOPA DE EUROPA` | `0x23F808` | 19 | 5 | **23** |
| `COPA INTERCONTINENTAL` | `0x23F4BC` | 21 | 7 | **27** |

Dos cosas que enseña esta tabla. Que **el hueco varía de una forma a otra de la misma competición** —«SEGUNDA DIVISIÓN» no tiene relleno y «PRIMERA DIVISIÓN» tiene cuatro—, así que hay que medir cada una. Y que **las abreviaturas son las más apretadas**: en `C. UEFA` no cabe ni un carácter más.

Si escribes un nombre más corto, hay que **rellenar el resto con ceros**. Dejar los restos del nombre anterior hace que aparezcan textos mezclados.

## Cómo localizarlas

Como con todo lo del ejecutable, **por contenido y no por posición**: cada edición del juego tiene sus cadenas en sitios distintos, así que la única forma fiable es buscar el texto conocido allá donde esté.

Es además la parte más agradecida de trabajar sobre el ejecutable, porque el resultado se ve a simple vista y un error no cuelga nada: como mucho, sale un nombre raro.
