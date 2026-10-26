# El ejecutable en 7, 2000 y 2001

Qué equipos forman cada división, quién juega cada copa, en qué año empieza la temporada y los topes del juego: todo eso está en `MANAGER.EXE`, no en la base de datos. Aquí están las tablas localizadas en los tres ejecutables y las reglas para cambiarlas sin colgar el juego.

> Los cambios de esta página modifican reglas de juego en el ejecutable de tu propia copia. No tocan ninguna protección anticopia y no se distribuye ningún ejecutable modificado.

## Antes de nada: identifica tu ejecutable

**Por su tamaño en bytes.** Las posiciones de esta página solo valen para estos tres; en cualquier otro, búscalas primero.

| Tamaño | Edición |
|---|---|
| 4.939.776 | PC Fútbol 7 |
| 5.115.904 | PC Fútbol 2000 |
| 7.991.296 | PC Fútbol 2001 |

Los tres son ejecutables de Windows **planos**: la posición en el fichero coincide con la dirección en memoria menos `0x400000`. Todas las posiciones de esta página son **posiciones en el fichero**.

Y las reglas de siempre, sin excepción: **solo se sustituye, nunca se añade ni se quita**, y antes de escribir en una plaza **lee lo que hay** y comprueba que es un código de equipo con sentido.

## Cómo se leen las tablas

Cada plaza son **dos bytes** con el código del equipo, el mismo del fichero de equipos. Una tabla de veinte plazas son cuarenta bytes seguidos.

### Las tres reglas que cuelgan el juego si se rompen

1. **El número de plazas no se cambia.** Cada liga lleva su tamaño escrito en el código que la construye. Puedes cambiar quién ocupa cada plaza, no cuántas hay. Si una tabla trae plazas a cero de fábrica —los grupos de Tercera de 2001 tienen hueco para 22 y se juegan con 20—, déjalas a cero.
2. **Nunca escribas un 0 en una plaza viva.** El código 0 no existe y el juego se cae al entrar en la división. Si no tienes equipo para una plaza, deja uno válido.
3. **Ningún equipo en dos divisiones a la vez, ni dos veces en la misma.** Un club repetido hace que el juego aborte al crear la partida, no al entrar en esa liga, así que el fallo despista. Revisa todas las tablas juntas, no una por una.

### Las copas que siguen a la liga

Varias listas de equipos aparecen **dos o tres veces** en el ejecutable, con los mismos clubes en el mismo orden. No son divisiones duplicadas: son **las copas nacionales**, que coinciden con la liga porque las juegan todos los clubes de la división. Si cambias una división y no sus copias, un club que baja sigue jugando la copa de su categoría anterior.

Lo seguro: antes de escribir, **busca en todo el ejecutable la secuencia original completa** de la división y sustitúyela allí donde aparezca. Casar 36 o 48 bytes seguidos no puede pisar otra cosa por casualidad. Las copas que mezclan varias divisiones en otro orden —la Copa del Rey, la F.A. Cup— no se encuentran así: hay que cambiar en ellas, plaza por plaza, al club que sale por el que entra.

### Cómo saber qué tabla es cuál

**El ejecutable escribe el nombre de cada competición, en texto, justo detrás de su tabla**: `CREY`, `LIGA1`, `LIGA2`, `LIGA2B`, `FACUP`, `CCCUP`, `CITALIA`, `BUNDES1`, `CBUNDES`, `PREMIERLEAGUE`, `SERIEA`, `FRANCE1`…, junto a una ruta de calendario del tipo `actliga\…%03u.CPT`. Es la forma de distinguir una liga de su copa gemela sin adivinar. En los trofeos de verano el nombre va algo más lejos, a unos 200-270 bytes, con las rutas de sus imágenes por medio.

### Los calendarios

**La liga española no tiene calendario en el ejecutable**: el juego lo sortea al empezar. Por eso recolocar Primera, Segunda o 2ªB no exige tocar nada más. Los calendarios de las ligas extranjeras sí están dentro, y no como tabla sino **como código**: instrucciones que escriben cada partido con los códigos de los equipos dentro. No se documentan aquí.

## PC Fútbol 7

### Divisiones

Cinco países jugables, dieciocho divisiones:

| División | Posición | Plazas |
|---|---|---|
| Primera | `0x49F058` | 20 |
| Segunda | `0x49F190` | 22 |
| 2ªB, grupos I a IV | `0x49F254` · `0x49F27C` · `0x49F2A4` · `0x49F2CC` | 20 cada uno |
| Premier League | `0x49D994` | 20 |
| First · Second · Third Division | `0x49D6A0` · `0x49DA6C` · `0x49DBC4` | 24 cada una |
| Serie A · Serie B | `0x49E294` · `0x49E3E8` | 18 · 20 |
| Serie C1, grupos A y B | `0x49E490` · `0x49E4B4` | 18 cada uno |
| Bundesliga 1 · 2 | `0x4A0370` · `0x4A03F4` | 18 · 18 |
| Ligue 1 · 2 | `0x4A0108` · `0x4A01A8` | 18 · 20 |

Justo detrás de Primera, en `0x49F080`, están los cuatro recién ascendidos.

### Copas y trofeos

| Competición | Posición | Plazas |
|---|---|---|
| Copa del Rey — finalistas del año anterior | `0x49EDFC` | 2 |
| Copa del Rey — clubes de 1ª y 2ª | `0x49EE00` | 42 |
| Copa del Rey — clubes de 2ªB | `0x49EEA4` | 67 |
| F.A. Cup | `0x49D560` | 124 |
| Supercopa de España | `0x49F3F0` | 2 |
| Supercopa de Italia | `0x49E550` | 2 |
| Copa Intercontinental | `0x49DC8C` | 2 |
| Copa de Francia — clubes de Ligue 1 · Ligue 2 | `0x4A0090` · `0x4A00B8` | 18 · 20 |
| Copa de Alemania — clubes de 1ª · 2ª | `0x4A0488` · `0x4A04B0` | 18 · 18 |
| Copa de la Liga alemana | `0x455A40` | 6 |
| Trofeos Teresa Herrera · Ciutat de Palma · Bernabéu · Gamper | `0x49ED0C` · `0x49EB04` · `0x49E6B0` · `0x49E7E8` | 3 · 3 · 1 · 1 |
| Trofeos Colombino · Carranza · Naranja | `0x49E9F4` · `0x49E8F0` · `0x49EC20` | 3 · 3 · 2 |

Las tablas de copas y trofeos fueron documentadas por josewolf22; aquí están comprobadas una a una contra el ejecutable.

Dos más están localizadas pero **sin mapear a propósito**, porque no se entienden del todo: la Copa de la Liga inglesa (`CCCUP`, en `0x49D2D4`, cien plazas con clubes repetidos) y la Copa de Italia (`CITALIA`, en `0x49E170`, tres bloques con repetidos).

### Los participantes europeos

Aquí hay una trampa. En `0x453690` hay **136 códigos de equipo seguidos**, agrupados por país, que parecen los participantes de las copas europeas. **No lo son**: la misma lista, byte a byte, aparece en 7, en 2000 y en 2001 —tres temporadas distintas—, y cambiarla no cambia quién juega. Pasa lo mismo con una lista de 33 grandes del mundo en `0x44AF56`. Son datos fijos que se arrastraron de una edición a otra.

La lista que el juego usa de verdad **se construye al vuelo** con 34 instrucciones de la forma `66 C7 44 xx FE` seguidas del código del equipo. Cada plaza es el código dentro de su instrucción, y se cambia de una en una:

`0x1C4AA8` `0x1C4AC2` `0x1C4ADC` `0x1C4AF6` `0x1C4B10` `0x1C4B2A` `0x1C4B44` `0x1C4B61` `0x1C4B7B` `0x1C4B95` `0x1C4BAF` `0x1C4BC9` `0x1C4BE3` `0x1C4BFD` `0x1C4C17` `0x1C4C34` `0x1C4C4E` `0x1C4C70` `0x1C4D01` `0x1C4D1B` `0x1C4D35` `0x1C4D4F` `0x1C4D69` `0x1C4D83` `0x1C4D9D` `0x1C4DBA` `0x1C4DD4` `0x1C4DEE` `0x1C4E08` `0x1C4E22` `0x1C4E3C` `0x1C4E56` `0x1C4E70` `0x1C4E95`

### El año de la temporada

PC Fútbol 7 guarda la fecha de inicio de temporada en una variable propia: el año en dos bytes, en la dirección de memoria `0x8C8B5C`, y detrás el día y el mes. De fábrica, el 23 de agosto de 1999. Cambiar el año exige **cuatro cosas a la vez**; ninguna basta sola:

1. **Todas las instrucciones que escriben o comparan esa fecha con 1999.** Se encuentran buscando los bytes `5C 8B 8C 00 CF 07` (la dirección y el 1999); hay trece, y en cada una se cambian los dos últimos bytes por el año nuevo. Si dejas los comparadores, el juego te devuelve al menú al empezar la temporada.
2. **Dos instrucciones que recargan la fecha de la partida guardada** (`89 0D 5C 8B 8C 00`, en `0xAAB2` y `0xAEC0`), que se anulan con seis `90`. Si no, el año vuelve a 1999.
3. **El día y el mes de partida nueva**: en `0xB1C1` y `0x2EB4C0` hay un `B0 01` (que pone el 1 de enero); cambiado a `B0 08` arranca el 8 de agosto.
4. **El rango de años de nacimiento**: el juego solo acepta nacidos entre 1900 y 2000. Los bytes `6C 07 00 00 76 08 81 FD D0 07 00 00`, cambiados a `01 00 00 00 76 08 81 FD FF FF 00 00`, abren el rango y los nacidos en 2000 o después calculan su edad con normalidad.

Con eso, y marcando el envejecimiento de los jugadores al crear la partida, las edades salen de las fechas de nacimiento reales. El rótulo `TEMPORADA 97/98` es otra cosa: un texto en `0x43E2A8` que se cambia aparte, sin pasarse de su longitud.

### Los topes

| Tope | Dónde | De fábrica |
|---|---|---|
| Ofertas por semana | `0x4B197`, `0x4B2A0`, `0x4C140`, `0x4C161` (1 byte cada una) | 5 |
| Jugadores cedidos a la vez | `0x4B1AB` (1 byte) | 4 |

Las ofertas tienen **dos comprobaciones y el número del aviso**: cambia las cuatro posiciones o el tope seguirá aplicándose por un lado.

**Los extracomunitarios** son más delicados. El cupo no es un número suelto: cada competición pregunta su tope a una función diminuta, `mov eax, N` seguido de `ret`, y el mismo número vale para fichar y para alinear. Hay dos cupos según la competición: **4**, con la función en `0x1A5DC0`, y **3**, en `0x158480`. Van por separado: si subes uno y no el otro, en algunas competiciones seguirás topado.

Lo que no hay que hacer es cambiar la `N` de esa función: el compilador **reutiliza la misma función para todo el que devuelve ese número**, y la del 3 la comparten 107 tablas de las que solo 49 son del cupo. Cambiarla altera cosas que no tienen nada que ver; en PC Fútbol 7, la pantalla de elegir equipo llega a pintar grupos de 2ªB de más.

Lo limpio: detrás de la función hay diez bytes de relleno (`90`). Escribe ahí, ocho bytes después de su inicio, **una copia propia** con tu número, y haz que apunten a la copia **solo las entradas de las tablas del cupo**: las que tienen al lado la función que devuelve el texto del aviso de extracomunitarios. Para volver a fábrica, devuelves esas entradas a la original y el ejecutable queda idéntico.

### Los continentes

Qué países forman cada continente: un byte por país, en bloques separados por un cero.

| Continente | Posición | Plazas |
|---|---|---|
| Europa occidental | `0x43A4B8` | 23 |
| Europa oriental | `0x43A4D0` | 23 |
| Norteamérica | `0x43A4E8` | 3 |
| Sudamérica | `0x43A4EC` | 11 |
| Asia occidental | `0x43A4F8` | 7 |
| Asia oriental | `0x43A500` | 3 |
| Oceanía | `0x43A504` | 3 |
| África | `0x43A508` | 7 |

Comprobado contra el ejecutable (también lo recoge el editor EPCF7). No toques los ceros de separación.

### Los nombres de las competiciones

Van **en claro**, en latin-1, terminados en cero y con ceros de relleno: los largos (`PRIMERA DIVISIÓN`, `COPA DEL REY`, `SUPERCOPA DE EUROPA`…) y las siglas (`Primera`, `Premier`, `2B I`…). Se pueden cambiar en el sitio: el hueco es la longitud original más los ceros que la siguen, dejando siempre uno al final. Los nombres aparecen también dentro de frases de ayuda; si las cambias, que la frase entera siga cabiendo en su hueco. Que el juego muestre bien los nombres cambiados está **sin confirmar**.

## PC Fútbol 2000

### Divisiones

| División | Posición | Plazas |
|---|---|---|
| Primera | `0x4AC6A4` | 20 |
| Segunda | `0x4AC880` | 22 |
| 2ªB, grupos I a IV | `0x4AC944`, y cada 40 bytes | 20 cada uno |
| Premier League | `0x4AA344` | 20 |
| Division One · Two · Three | `0x4A9FC0` · `0x4AA41C` · `0x4AA4E4` | 24 cada una |
| Serie A · Serie B | `0x4AACAC` · `0x4AAECC` | 18 · 20 |
| Serie C1, grupos A y B | `0x4AAF88` · `0x4AAFAC` | 18 cada uno |
| Division 1 · 2 (Francia) | `0x4AE194` · `0x4AE234` | 18 · 20 |
| Bundesliga 1 · 2 | `0x4AE494` · `0x4AE518` | 18 · 18 |

Dos trampas en España. **La tabla que hay en `0x4AC3C8` no es Primera**: es la Copa del Rey, con los mismos veinte clubes en otro orden (las dos plazas de delante son los finalistas del año anterior). Leerla parece funcionar; escribir en ella recoloca la copa. Y **Segunda tiene otra tabla en `0x4AC3F0`**, la de clasificación, a la que le falta un equipo: la buena es la de `0x4AC880`.

PC Fútbol 2000 **no tiene Tercera**. **Argentina también es jugable** —con tres divisiones—, pero sus tablas no están localizadas: no cambies su número de equipos.

Francia y Alemania tienen cada una una tabla gemela de su primera división (`0x4AE11C` y `0x4AE5AC`), que por analogía con 7 y 2001 serían las copas nacionales. **Sin confirmar**, así que no están mapeadas.

### Topes

| Tope | Dónde | De fábrica |
|---|---|---|
| Ofertas por semana | `0xE7881`, `0xE7B6F`, `0xEB512`, `0xEB532` | 4 |
| Jugadores cedidos | `0xE78BE` | 4 |
| Extracomunitarios, cupo general · reducido | funciones en `0x2249C0` · `0x16DA70` | 4 · 3 |

Los extracomunitarios, con el mismo método que en 7.

## PC Fútbol 2001

### Divisiones

España, con Tercera:

| División | Posición | Plazas |
|---|---|---|
| Primera | `0x73496C` | 20 |
| Segunda | `0x734AEC` | 22 |
| 2ªB, grupos I a IV | `0x734B40`, y cada 40 bytes | 20 cada uno |
| Tercera, grupos I a XVII | `0x734C48`, y cada 44 bytes | 22 de hueco, 20 jugadas |

Y las extranjeras. **Cada liga extranjera aparece dos veces**, una por temporada; estas son las de la temporada en curso. Leerlas está comprobado; que el juego acepte los cambios está **sin confirmar**.

| País | Divisiones | Posiciones | Plazas |
|---|---|---|---|
| Inglaterra | Premier · One · Two · Three | `0x7329F8` · `0x732754` · `0x732A50` · `0x732AB0` | 20 · 24 · 24 · 24 |
| Italia | Serie A · B · C1-A · C1-B | `0x73310C` · `0x7332DC` · `0x733340` · `0x733364` | 18 · 20 · 18 · 18 |
| Francia | Division 1 · 2 | `0x737098` · `0x7370E4` | 18 · 20 |
| Alemania | Bundesliga 1 · 2 · Regionalliga Nord · Süd | `0x7372C8` · `0x7372F8` · `0x737328` · `0x737360` | 18 · 18 · 19 · 18 |
| Argentina | Primera · B Interior · B Metropolitana | `0x737794` · `0x737A08` · `0x737A28` | 20 · 16 · 18 |
| Portugal | 1ª · 2ª | `0x737A64` · `0x737A94` | 18 · 18 |
| Escocia | Premier · First | `0x737AD8` · `0x737AFC` | 12 · 10 |
| Holanda | Eredivisie · Eerste | `0x737B30` · `0x737B60` | 18 · 18 |
| Bélgica | 1ª · 2ª | `0x737B9C` · `0x737BCC` | 18 · 18 |

En 2001 son jugables diez países: los cinco de siempre más Argentina, Portugal, Escocia, Holanda y Bélgica.

Ojo con Argentina: la segunda categoría son **dos tablas seguidas**, de 16 y de 18. Tratarlas como una de 20 escribe cuatro equipos dentro de la otra división. Y con Alemania: la Copa de Alemania es **espejo exacto** de las Bundesligas y está 216 bytes más allá (`0x7373A0` y `0x7373C8`); no la confundas con la liga.

### Los promedios argentinos

En Argentina desciende quien tiene peor **promedio** de las últimas temporadas, y el juego guarda los datos de las dos anteriores en `0x7377BC`: **54 registros de 10 bytes**, uno por club de las tres divisiones, cada uno con cinco números de dos bytes —código del equipo, partidos y puntos de la última temporada, partidos y puntos de la penúltima—. Si recolocas equipos, actualiza también esta tabla, o el que sube hereda los números del que estaba. Y nunca más de tres puntos por partido.

### Copas

Aquí las plazas no siempre son seguidas: algunas copas van en bloques por rondas con bytes de separación entre ellos.

| Competición | Empieza en | Plazas |
|---|---|---|
| Copa del Rey — finalistas y clubes de 1ª y 2ª | `0x7346A8` | 2 + 42 |
| Copa del Rey — 2ªB y Tercera | `0x734754` | 68 |
| F.A. Cup | `0x732638` | 124 |
| Copa de la Liga inglesa | `0x73239C` | 92, en tres bloques |
| Copa de Italia | `0x733084` (y una copia idéntica en `0x732338`) | 48, en tres bloques |
| Copa de Francia — clubes de 1ª · 2ª | `0x73703C` · `0x737064` | 18 · 20 |
| Copa de Alemania — clubes de 1ª · 2ª | `0x7373A0` · `0x7373C8` | 18 · 18 |
| Copa de la Liga alemana | `0x687320` | 6 |

La Copa de Italia está **dos veces** y no se sabe cuál lee el juego: escribe en las dos.

Los trofeos de verano son doce: los siete de PC Fútbol 7 más el Ciutat de Barcelona, el Ciudad de Vigo, el de La Línea, el Villa de Gijón y el Villa de Madrid. Sus participantes son **invitados**, no una división, y el anfitrión no figura en la tabla.

Las plazas de cada país en la Copa de Europa y la UEFA son códigos dentro de instrucciones, como los europeos de 7:

| Plazas | Posiciones |
|---|---|
| Copa de Europa — España | `0x219367` `0x21924B` `0x219193` `0x219306` |
| Copa de Europa — Inglaterra | `0x21934B` `0x2192C1` `0x2191AA` `0x21914B` |
| Copa de Europa — Italia | `0x2192D8` `0x219206` `0x219162` `0x219062` |
| UEFA — España | `0x226753` `0x2267A7` `0x2267B3` `0x2267BF` |
| UEFA — Inglaterra | `0x226837` `0x226843` `0x22684F` |
| UEFA — Italia | `0x22678F` `0x22679B` `0x226783` |
| Campeones de copa para las supercopas (España, Inglaterra, Italia) | `0x734F9C` `0x73248C` `0x7333B0` |

Si usas posiciones publicadas por herramientas antiguas, comprueba si cuentan desde 1: algunas lo hacen, y entonces hay que restar uno. Las de esta tabla ya están corregidas.

### Topes

En 2001 no hay un tope único de ofertas, sino una cascada de comparaciones; mientras no se entienda, **no está mapeado**.

## 2000 y 2001: economía y fechas

Los dos ejecutables comparten la misma estructura para los precios y el merchandising, en posiciones distintas. Cada valor es un número de 4 bytes, en pesetas.

| Bloque | 2000 | 2001 | Qué es |
|---|---|---|---|
| Precios | `0x43F050` | `0x673B4C` | 16 valores: entrada y abono, máximo y mínimo, para grada, tribuna, palco y VIP |
| Merchandising | `0x433CAC` | `0x673034` | 12 productos: precio mínimo (+0), precio máximo (+48), salto de precio (+120), nivel de ventas (+168), autofabricación (+228); en +96, un máximo de fábrica para 6 de ellos |

El orden de los precios: las cuatro entradas máximas, las cuatro mínimas, los cuatro abonos máximos y los cuatro mínimos, siempre grada, tribuna, palco, VIP.

**Las fechas fijas** del calendario se encuentran por su forma: `B1 mes`, `B8 año (4 bytes)` y una instrucción que guarda un día fijo (`C6 05` con dirección, o `C6 44 24`, seguido del día). En 2001 salen cinco y son **los cinco partidos de pretemporada**, del 10 de julio al 19 de agosto. En 2000 salen siete de tipos distintos, y qué es cada una está **sin confirmar**.

**Los continentes** usan el mismo esquema que en 7. Se localizan buscando los bytes `02 4B 05 0C 12 13 16 18 1B 1E` (el principio de Europa occidental); desde ahí, los bloques empiezan en +0, +24, +52, +56, +68, +76, +80 y +84, con 23, 27, 3, 11, 7, 3, 3 y 7 plazas.
