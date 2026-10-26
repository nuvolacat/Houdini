# El entrenador y la táctica del equipo

El entrenador va antes de la lista de jugadores, dentro del mismo bloque del club. Se distingue porque **empieza con un `02`**, mientras que las fichas de jugador empiezan con `01`.

## Puede haber más de uno

Lo primero, porque es lo que más lectores rompe: **un equipo puede tener varios entrenadores**, no uno.

No es teórico ni un caso raro. Son los técnicos que dirigieron al equipo esa temporada, y los trae **contados por edición**:

| Edición | Clubes con más de uno | El que más |
|---|---|---|
| **6.0 Oro** | **46** | 5 |
| 5.0 Oro | 25 | 4 |
| 6.0 | 15 | 3 |
| 5.0 | 12 | 3 |
| Premier | 5 | 2 |
| Calcio | 1 | 2 |
| **Apertura 97 y 98** | **ninguno** | 1 |

El récord es del **Levante**, con cinco en una temporada: Emilio Cruz, José Enrique Díaz, Roberto Álvarez, Txutxi Aranguren y Pepe Balaguer. Y el Zaragoza lleva cuatro —Víctor Fernández, Nieves, Espárrago y Luis Costa—, que es exactamente lo que pasó aquel año.

Fíjate en las dos ediciones argentinas: **no traen ni un solo club con dos**. Si pruebas tu lector solo con ellas, este caso no aparecerá nunca y creerás que lo tienes resuelto.

El formato lo permite sin límite: pueden alternarse entrenadores y jugadores en el bloque. Un lector que dé por hecho que hay uno solo y salte al siguiente `01` se saltará fichas.

## Los campos

| Campo | Notas |
|---|---|
| Marca de inicio | siempre `02` |
| Puntero | su identificador |
| Nombre corto y nombre largo | texto, con la longitud por delante |
| Perfil | texto |
| Sistemas habituales | texto |
| Palmarés | texto |
| Anécdotas | texto |
| Última temporada | texto |
| Trayectoria | texto, con un formato propio de campos separados |
| Marca | un `03` que anuncia lo siguiente |
| Trayectoria como jugador | texto |
| Declaraciones | texto |

Los textos que no tienen contenido llevan una `x`. Vacíos del todo no valen — como en todo este formato, el campo tiene que estar aunque no diga nada.

## Cómo leerlos sin perder ninguno

Aquí hay un error fácil de cometer y difícil de detectar. La tentación es parar de leer textos cuando aparece uno vacío, o poner un límite de longitud razonable. **Las dos cosas están mal.**

La regla que sigue el juego es:

- Se leen **los seis textos aunque estén vacíos**. Un texto vacío no significa que se hayan acabado.
- El separador **se consume siempre**, haya contenido o no.
- El único límite de longitud es **el final del bloque**. Hay textos de más de dos mil caracteres y son legítimos.

Un lector que corte en el primer vacío se dejará la mitad de los textos de unos cuarenta entrenadores por edición. Y lo malo es que no falla: simplemente devuelve menos de lo que hay, y parece que esos entrenadores no tienen datos.

**Los clubes extranjeros no llevan estos textos.** Solo su nombre. Es la misma regla que con los jugadores.

## El reparto del hueco entre los dos nombres

Un detalle práctico que sorprende: el nombre corto y el nombre largo del entrenador **comparten el espacio disponible**. Si uno se queda corto, el otro puede aprovecharlo.

Esto es útil cuando quieres poner un nombre completo largo: puedes acortar el corto para hacerle sitio. Y es la razón de que a veces un nombre que parece que cabría no quepa — depende de lo que esté ocupando el otro.

## La táctica del equipo: siete bytes

Aparte de la táctica dibujada —las posiciones en el campo, que se explican en el bloque de equipo—, hay siete bytes que definen **cómo juega el equipo**:

| Byte | Qué controla | Valores |
|---|---|---|
| 1 | Porcentaje de toque | |
| 2 | Porcentaje de contragolpe | |
| 3 | Ataque | `0` ofensivo · `1` especulativo · `2` mixto |
| 4 | Entradas | `0` a `2`, de más suave a más dura |
| 5 | Marcaje | `0` en zona · `1` al hombre |
| 6 | Despejes | `0` al jugador · `1` en largo |
| 7 | Presión | `0` a `2` |

Son siete valores de un byte, así que se pueden cambiar sin ningún riesgo de descuadrar el bloque.

## Las quince formaciones

El juego trae **quince formaciones estándar**, y la táctica dibujada de un equipo es una copia de una de ellas. Se puede sustituir por la de otro equipo copiando sus ciento setenta y seis bytes.

| Formación | |
|---|---|
| 3-3-3-1 | 4-4-2 |
| 3-3-4 | 4-5-1 |
| 3-4-3 | 4-5-1 DP |
| 3-5-2 | 5-2-3 |
| 4-2-4 | 5-3-2 |
| 4-3-3 | 5-4-1 |
| 4-3-3 FCB | 5-4-1 DP |
| Por defecto | |

Las que llevan sufijo son variantes: la `FCB` es un 4-3-3 con otro reparto, y las `DP` colocan un media punta.

Si los 176 bytes de un equipo no coinciden con ninguna de las quince, es que tiene **una formación propia** — perfectamente válida, solo que sin nombre.

Cada formación trae además **la demarcación que le corresponde a cada una de las once posiciones**, y por eso al cambiar de formación el juego sabe qué tipo de jugador quiere en cada sitio.

Si quieres comprobar que estás copiando bien, mira el portero: **es idéntico en las quince**, y sus ocho valores son `0, 66, 42, 66, 0, 88, 0, 88`. Si el tuyo sale distinto, has empezado a contar en el sitio equivocado.

> **Un detalle si sacas las formaciones de otra fuente.** La base de datos original de Dinamic guarda cada formación en **174 bytes**, no en 176: omite los dos primeros, que son la coordenada de la zona del portero y **siempre valen cero**. Si copias esos 174 tal cual dentro del fichero, te faltarán dos bytes y toda la táctica saldrá corrida.
