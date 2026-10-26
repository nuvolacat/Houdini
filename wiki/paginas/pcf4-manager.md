# El manager de 4.0 y 4.5: divisiones, filiales y competiciones

Qué decide `PCMANAG.DAT` y no está en los ficheros de equipo: qué clubes juegan cada división, cuáles no pueden ascender y cómo se llaman las competiciones. Todo se cambia sustituyendo bytes en el sitio, sin alterar el tamaño.

> Los cambios de esta página modifican reglas de juego en el ejecutable de tu propia copia. No tocan ninguna protección anticopia y no se distribuye ningún ejecutable modificado.

## Son programas, no datos

`PCMANAG.DAT` es el modo manager y `PROMANAG.DAT`, el Pro Manager. La extensión engaña: son **ejecutables de 32 bits para DOS**, y cumplen el papel del `manager.exe` de 5.0 y 6.0 (ver [el ejecutable de 5.0 y 6.0](v56-manager-exe.html)).

Así que aplica la regla de siempre con los ejecutables: **solo se sustituye, nunca se añade ni se quita**. Si el fichero cambia de tamaño, deja de arrancar. Y haz copia antes de tocarlo.

Todo lo que sigue vale para los dos ficheros. Hazlo en los dos si quieres que el cambio se vea en ambos modos.

## El número de equipo

Cada club se identifica por las cuatro últimas cifras de su fichero: `EQ950026.DBC` es el equipo 26. Los equipos españoles de las tres categorías son del **1 al 96**.

Ese número no dice en qué división juega. Lo dice la tabla siguiente.

## Qué equipos juegan cada división

`PCMANAG.DAT` lleva una tabla de **96 registros de 4 bytes**, uno por equipo español:

| Tamaño | Qué es |
|---|---|
| 2 bytes | Número de equipo, de 1 a 96 |
| 2 bytes | `00 00` |

Y tras el último registro, `FF FF`.

El orden de la tabla es el de la pantalla de clasificación, y **las divisiones salen de cortarla por tamaños**: los 22 primeros son Primera, los 20 siguientes Segunda y los 54 últimos Segunda B. Es la temporada 95-96. Los cortes no están marcados en la tabla; están en el código.

**Cómo encontrarla:** busca 96 registros seguidos en los que los dos primeros bytes sean un número entre 1 y 96, los dos siguientes `00 00`, **ningún número se repita** y detrás venga `FF FF`. No te ancles en que empiece por un equipo concreto: si ya has reordenado la tabla, puede empezar por cualquiera.

**Para mover un equipo de división**, reordena la tabla: intercambia su número con el de un equipo de la otra división. La tabla tiene que seguir conteniendo los 96 números, cada uno una vez. Cambiar el **tamaño** de las divisiones ya no es tocar la tabla, y no está documentado aquí.

El efecto completo dentro del juego al cambiar de temporada está sin confirmar.

## Los filiales: quién no puede ascender

De fábrica, tres equipos no pueden subir a Primera aunque acaben arriba: los números **26, 28 y 34**, los filiales de la temporada 95-96. Están escritos directamente en el código, en **tres comprobaciones**, y para cambiar los filiales hay que cambiarlas las tres.

### Las dos primeras: contra la tabla de clasificación

Dos bloques casi idénticos, cada uno con tres comparaciones seguidas de saltos:

```
83 Bx [4 bytes de dirección] 1A   74 ..
83 Bx [4 bytes de dirección] 1C   74 ..
83 Bx [4 bytes de dirección] 22   75 ..   ← en el primer bloque
                                  74 ..   ← en el segundo
```

`1A`, `1C` y `22` son 26, 28 y 34. Los cuatro bytes de dirección son **los mismos en las seis comparaciones**: es la tabla de clasificación. El primer bloque decide si hay que bajar a un filial de los puestos de ascenso; el segundo, con quién se intercambia.

Cuidado: justo al lado hay **otro bloque con la misma forma** que compara los números 1, 4 y 12 contra otra tabla. No son filiales. Lo que distingue el bueno es que aparece dos veces, con la misma dirección y con 26, 28 y 34.

### La tercera: la que se olvida

Una tercera rutina compara el número de equipo contra un registro, no contra la tabla:

```
83 FE 1A 74 ..
83 FE 1C 74 ..
83 FE 22 0F 84 ..
```

Es fácil pasarla por alto porque no se parece a las otras dos. Si cambias solo las dos primeras, el síntoma es característico: el objetivo del filial en el juego pasa de «Ascenso» a «Zona alta», pero el equipo **sigue sin subir**. Es esta tercera comprobación la que lo sigue descartando.

### Cómo cambiarlos

Sustituye los tres números (el byte detrás de cada dirección o detrás de `83 FE`) por los de tus filiales, **en los tres bloques**. Los números de equipo van de 1 a 96, así que caben en un byte.

Para dejar un hueco sin filial, pon un número que no sea ningún equipo:

- en los dos primeros bloques, `00`: ningún equipo es el 0;
- en el tercero, `FF`: el procesador lo lee como −1, que tampoco es ningún equipo.

Con los tres huecos vacíos en los tres bloques, **todos los equipos pueden ascender**.

Por sustitución caben **tres filiales como mucho**, que son los huecos que hay. Las comprobaciones están localizadas en el análisis del ejecutable en los cuatro ejecutables examinados, entre `PCMANAG.DAT` y `PROMANAG.DAT`; el comportamiento en el cambio de temporada está sin confirmar del todo.

## Los nombres de las competiciones

Aquí no hay cifrado: **son texto en claro** dentro de los dos ficheros. Se cambian como en 5.0 y 6.0, sustituyendo en el sitio con la misma longitud y rellenando con espacios.

Cada competición aparece en una o dos formas:

| Competición | En los rótulos | En los textos |
|---|---|---|
| Primera | `PRIMERA DIVISION` | — |
| Segunda | `SEGUNDA DIVISION` | — |
| Copa del Rey | `COPA DEL REY` | `Copa del Rey` |
| Copa de Europa | `COPA DE EUROPA` | `Copa de Europa` |
| Copa de la UEFA | `COPA DE LA UEFA` | `Copa de la UEFA` |
| Recopa | `RECOPA DE EUROPA` | `Recopa` |

Tres cosas a tener en cuenta:

- **Cambia las dos formas.** Si solo cambias la de los rótulos, los textos corridos siguen diciendo el nombre viejo.
- **Cambia todas las apariciones.** Un mismo nombre sale varias veces en el fichero.
- **Ojo con los nombres que contienen otros.** `COPA DE EUROPA` está dentro de `RECOPA DE EUROPA`. Si buscas el corto primero, le cambias el final a la Recopa. Busca y sustituye **primero los largos** y no vuelvas a tocar lo que ya has cambiado.

Las mayúsculas de los rótulos son una decisión de estilo de Dinamic, no del formato: el juego imprime el texto tal cual.
