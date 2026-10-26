# El ejecutable: posiciones concretas

La otra página explica **qué** hay en el ejecutable y **cómo** buscarlo. Esta da las posiciones exactas de los tres ejecutables que están mapeados, para que no tengas que buscarlas.

## Antes de nada: identifica tu ejecutable

**Por su tamaño en bytes.** Es lo único que distingue una compilación de otra sin lugar a dudas, y aplicar las posiciones de un ejecutable a otro **lo destroza**.

| Tamaño | Qué edición es | ¿Hay tabla aquí? |
|---|---|---|
| 2.507.264 | **5.0**, la original | No |
| **2.461.184** | **5.0 Edición de Oro** (96/97) | Sí, comprobada |
| 2.617.344 | **6.0**, la original | No |
| 2.630.144 | 6.0, primera extensión (97/98) | Sí, pero **sin comprobar** |
| **2.662.400** | **6.0 Edición de Oro** (97/98) | Sí, comprobada |

Los cinco tamaños están medidos sobre los ejecutables reales, uno a uno.

**Fíjate en cuáles tienen tabla y cuáles no.** Las dos ediciones que la tienen comprobada son las **de Oro**, no las originales. Si tu ejecutable mide 2.507.264 o 2.617.344 tienes una edición original, y **estas tablas no te sirven**: las posiciones son otras. Es un error fácil de cometer y caro, porque el fichero se deja escribir igual.

Si el tuyo no mide ninguno de estos cinco, o mide uno de los que no tienen tabla, **usa el método de búsqueda por rachas de la otra página**. Es más trabajo pero funciona con cualquier compilación.

> **Aviso sobre el de 2.630.144.** Las posiciones de los otros dos están comprobadas una a una contra el ejecutable: en cada una hay un identificador de equipo válido, y los equipos que salen coinciden con la historia real de aquellas temporadas —la Supercopa de Europa del 96 da Juventus y PSG, la Intercontinental del 97 da Dortmund y Cruzeiro—. Las de esta tercera **no se han podido comprobar** porque no tenemos ese ejecutable. Úsalas con cuidado y verifica antes de escribir.

## Comprueba antes de escribir

Siempre, sin excepción: **lee los dos bytes que hay en esa posición y comprueba que son un identificador de equipo que tiene sentido** antes de cambiarlos. Si esperas encontrar al Barcelona y encuentras un número disparatado, esa no es la tabla que crees.

Y recuerda: **solo se sustituye, nunca se añade ni se quita**. El fichero tiene que seguir midiendo exactamente lo mismo.

## Ejecutable de 2.461.184 bytes (5.0 y 6.0, 96/97)

### Participantes de cada competición

| Competición | Empieza en | Plazas |
|---|---|---|
| Liga inglesa — Premier | `0x23CD10` | 20 |
| Liga inglesa — Division One | `0x23CB80` | 24 |
| Liga inglesa — Division Two | `0x23CDC0` | 24 |
| Liga inglesa — Division Three | `0x23CE60` | 24 |
| Copa del Rey — bombo de 1ª y 2ª | `0x23D480` | 39 |
| Copa del Rey — bombo de 2ªB | `0x23D520` | 64 |
| Copa de Europa — participantes | `0x23DFA0` | 16 |
| Copa de Europa — campeón vigente | `0x23DFC0` | 1 |
| Copa de la UEFA — participantes | `0x23E318` | 64 |
| Recopa — participantes | `0x23E4E0` | 32 |

### Las plazas españolas de cada copa europea

Estas van sueltas porque el juego las guarda aparte de la lista general. Cuando hay varias posiciones para lo mismo, **hay que escribir en todas**: si cambias una y dejas otra, el juego se contradice a sí mismo.

| Competición | Posiciones |
|---|---|
| Supercopa de España | `0x23DB28`, `0x23DB2C` |
| Supercopa de Europa | `0x23E5A0`, `0x23E5A4` |
| Copa Intercontinental | `0x23CF00`, `0x23CF04` |
| Copa de Europa (plazas españolas) | `0x23DFB8` |
| Copa de la UEFA (plazas españolas) | `0x23E324`, `0x23E340`, `0x23E382` |
| Recopa (plaza española) | `0x23E4F2` |

### Límites del juego

| Límite | Posición | Valor de fábrica |
|---|---|---|
| Extracomunitarios en plantilla | `0x2AB81` (4 B) | 6 |
| Extracomunitarios en el once | `0x2ABA1` (4 B) | 4 |
| Ofertas por semana | `0x248068` (4 B) | 5 |

## Ejecutable de 2.662.400 bytes (6.0 Edición de Oro)

### Participantes de cada competición

| Competición | Empieza en | Plazas |
|---|---|---|
| Copa del Rey — bombo de 1ª y 2ª | `0x27CD68` | 40 |
| Copa del Rey — bombo de 2ªB | `0x27CE08` | 64 |
| Copa de Europa — 1ª ronda previa (15 cruces) | `0x27D838` | 30 |
| Copa de Europa — clasificados directos | `0x27D8C8` | 8 |
| Copa de la UEFA — plazas españolas | `0x27DA00` | 4 |
| Copa de la UEFA — campeón vigente | `0x27DA08` | 1 |
| Copa de la UEFA — participantes | `0x27DA10` | 23 |
| Copa de la UEFA — ganadores de la Intertoto | `0x27DA40` | 3 |
| Copa de la UEFA — resto de participantes | `0x27DA48` | 18 |
| Recopa — ronda previa (15 cruces) | `0x27DBC8` | 30 |
| Recopa — participantes | `0x27DC08` | 17 |
| Sudamericanos (Intercontinental) | `0x27D558` | 23 |

### Las plazas españolas de cada copa europea

| Competición | Posiciones |
|---|---|
| Supercopa de España | `0x27D4E8`, `0x27D4EC` |
| Supercopa de Europa | `0x27DCB8`, `0x27DCBC` |
| Copa Intercontinental | `0x27C8F0`, `0x27C8F4` |
| Recopa (plaza española) | `0x27DC04`, `0x27DC0A` |
| Copa de Europa (plazas españolas) | `0x27D894`, `0x27D8BC`, `0x27D8CC` |
| Copa de la UEFA (plazas españolas) | `0x27DA00`, `0x27DA02`, `0x27DA04`, `0x27DA06` |

### Límites del juego

| Límite | Posición | Valor de fábrica |
|---|---|---|
| Extracomunitarios en plantilla | `0x8701` (4 B) | 6 |
| Extracomunitarios en el once | `0xE1CB1` (4 B) | 4 |
| Ofertas por semana | `0x42396` (1 B), `0x423CC` (1 B), `0x42EEC` (1 B), `0x42F27` (1 B) | 5 |

## Ejecutable de 2.630.144 bytes (6.0, primera extensión)

Mismas tablas que la Edición de Oro, desplazadas.

### Participantes de cada competición

| Competición | Empieza en | Plazas |
|---|---|---|
| Copa del Rey — bombo de 1ª y 2ª | `0x275890` | 40 |
| Copa del Rey — bombo de 2ªB | `0x275930` | 64 |
| Copa de Europa — 1ª ronda previa (15 cruces) | `0x276360` | 30 |
| Copa de Europa — clasificados directos | `0x2763F0` | 8 |
| Copa de la UEFA — plazas españolas | `0x276528` | 4 |
| Copa de la UEFA — campeón vigente | `0x276530` | 1 |
| Copa de la UEFA — participantes | `0x276538` | 23 |
| Copa de la UEFA — ganadores de la Intertoto | `0x276568` | 3 |
| Copa de la UEFA — resto de participantes | `0x276570` | 18 |
| Recopa — ronda previa (15 cruces) | `0x2766F0` | 30 |
| Recopa — participantes | `0x276730` | 17 |
| Sudamericanos (Intercontinental) | `0x276080` | 23 |

### Las plazas españolas de cada copa europea

| Competición | Posiciones |
|---|---|
| Supercopa de España | `0x276010`, `0x276014` |
| Supercopa de Europa | `0x2767E0`, `0x2767E4` |
| Copa Intercontinental | `0x275418`, `0x27541C` |
| Recopa (plaza española) | `0x27672C`, `0x276732` |
| Copa de Europa (plazas españolas) | `0x2763BC`, `0x2763E4`, `0x2763F4` |
| Copa de la UEFA (plazas españolas) | `0x276528`, `0x27652A`, `0x27652C`, `0x27652E` |

## Las reglas que se pueden quitar

Aparte de los números, hay comprobaciones que el programa hace y que se pueden desactivar neutralizando su salto. **No todas existen en todas las compilaciones** — depende de qué trajera cada una:

| Regla | 5.0 Oro y 6.0 base | 6.0 Edición de Oro | Calcio | Premier |
|---|---|---|---|---|
| Admitir nacidos después de 1999 | **sí** | **sí** | **sí** | **sí** |
| Fichar extracomunitarios sin límite | — | **sí** | **sí** | — |
| Alinear extracomunitarios sin límite | **sí** | **sí** | **sí** | **sí** |
| Traspasos entre jugadores | **sí** | — | — | — |
| Traspasos entre clubes | **sí** | — | — | — |

Que una casilla esté vacía **no significa que la regla no exista en ese juego**: significa que en esa compilación no se ha localizado dónde está. Y en algunos casos ni siquiera existe — en el ejecutable base de 5.0 y 6.0 no hay ninguno de los ocho sitios que en la Edición de Oro controlan el fichaje de extracomunitarios.

La técnica para desactivarlas —cambiar el `74` por `EB`, o tapar el `0F 84` con seis `90`— está en [la otra página](v56-manager-exe.html).

## Cómo se leen estas tablas

Cada plaza son **dos bytes**, con el byte bajo primero, y el valor es **el identificador del equipo** en la numeración de Dinamic — la misma que da nombre a los escudos y que está en [las tablas de códigos](v56-tablas.html).

Una tabla de veinte plazas ocupa cuarenta bytes seguidos desde la posición indicada.

Un valor a cero no siempre significa lo mismo: en una lista de participantes es **una plaza que el juego no usa**; en un cuadro de eliminatorias es **la plaza que ocupará el ganador de la ronda anterior**, y el juego la rellena solo al simular.

## Las divisiones no están aquí

Las tablas de la Liga española **no llevan posición fija en esta lista** porque se localizan buscándolas: son la única racha larga de identificadores que empieza por los equipos de Primera en el orden en que quedaron la temporada anterior. El método está en [la otra página](v56-manager-exe.html).

## Lo que falta por mapear

Dicho abiertamente, por si alguien quiere completarlo:

- Del ejecutable de 5.0 y 6.0 base faltan las listas completas de participantes de la UEFA y la Recopa: solo están localizadas las plazas españolas.
- El cuadro de eliminatorias de la Copa de Europa de la Edición de Oro está identificado pero **no mapeado**: los equipos van intercalados con huecos y no se puede acotar con la misma certeza. Antes de escribir en el ejecutable de alguien, mejor dejar fuera lo que no se entiende del todo.
- Los ejecutables de las ediciones Premier, Calcio y Apertura no están mapeados.
