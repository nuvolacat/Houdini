# El registro de equipo en 7, 2000 y 2001

El club guarda sus datos, su historial de liga, su palmarés de copas, su táctica y la lista de punteros de su plantilla. En 2000 y 2001 el estadio se va a un fichero propio. Aquí tienes los tres layouts y cómo se elige el código de un equipo nuevo.

## PC Fútbol 7

| Campo | Tamaño | Qué es |
|---|---|---|
| Firma | 36 bytes | `Copyright (c)1998 Dinamic Multimedia` |
| Suma de longitudes | 2 bytes | calculada; ver [el contenedor](fdi-contenedor.html) |
| Versión | 2 bytes | 700 |
| Relleno | 1 byte | `00` |
| Tipo de ficha | 1 byte | `0` liga jugable · `1` extranjero, ficha reducida |
| Nombre corto | texto | |
| Estadio | texto | |
| País | 1 byte | |
| Latitud | 1 byte | **con signo**: grados de la ciudad del club. Los clubes del hemisferio sur salen negativos |
| Nombre largo | texto | |
| Aforo sentado | 4 bytes | |
| Aforo de pie | 4 bytes | |
| Ancho del campo | 2 bytes | |
| Largo del campo | 2 bytes | |
| Año de fundación | 2 bytes | |
| Año del estadio | 2 bytes | *solo ficha completa* |
| Socios | 4 bytes | *solo ficha completa* |
| Presidente | texto | *solo ficha completa* |
| Presupuesto | 4 bytes | *solo ficha completa*. Ver más abajo |
| Potencia económica | 4 bytes | *solo ficha completa*. Ver más abajo |
| Patrocinador | texto | *solo ficha completa* |
| Proveedor | texto | *solo ficha completa* |
| Filial | 2 bytes | *solo ficha completa*. Código del filial; `FFFF` = no tiene |
| Historial de liga | 82 bytes | *solo ficha completa* |
| Palmarés de copas | 1 + 3·n bytes | *solo ficha completa* |
| Táctica dibujada | 1.760 bytes | ver [la táctica](fdi-tactica.html) |
| Estilo de juego | 7 bytes | ver [la táctica](fdi-tactica.html) |
| Nº de entrenadores | 1 byte | |
| Entrenadores | 4 bytes cada uno | código en el fichero de entrenadores |
| Nº de jugadores | 1 byte | |
| Jugadores | 5 bytes cada uno | 1 byte de marca + 4 bytes de código |

Respecto a 6.0 desaparecen los dos bytes reservados que había entre el proveedor y el filial: aquí van seguidos.

La **ficha reducida** de los clubes extranjeros termina en el año de fundación y salta directamente a la táctica: sin datos económicos, sin historial y sin palmarés.

### Los dos presupuestos

Son dos campos y miden cosas distintas:

- **Presupuesto**: el dinero con el que empiezas, en millones. El del Real Madrid de fábrica es 19.625.
- **Potencia económica**: un índice de **0 a 1.000** del músculo económico del club, que el juego usa como referencia general. El Madrid tiene 1.000.

### La lista de jugadores

Cada entrada es una **marca de un byte** y el **código del jugador** en cuatro. La marca vale `0` si está en la plantilla y `1` si no. El orden de esta lista no decide la alineación: eso lo hace la posición en la plantilla de cada ficha (ver [la ficha del jugador](fdi-jugador.html)).

## PC Fútbol 2000

El estadio sale del equipo y se va a su propio fichero. El resto de la cola es igual que en 7.

| Campo | Tamaño | Qué es |
|---|---|---|
| Firma | 36 bytes | `Copyright (c)2000 Dinamic Multimedia` |
| Suma de longitudes | 2 bytes | nombre corto y largo, y en ficha completa presidente, patrocinador y proveedor |
| Versión | 2 bytes | 800 |
| Relleno | 1 byte | |
| Tipo de ficha | 1 byte | `0` completa · `1` reducida |
| Nombre corto | texto | |
| **Estadio** | 2 bytes | **código del estadio** en `EST…FDI` |
| País | 1 byte | ya **no** hay latitud detrás |
| Nombre largo | texto | |
| Año de fundación | 2 bytes | |
| *(ficha completa)* | | socios, presidente, los dos presupuestos, patrocinador, proveedor, filial, historial de 82 bytes y palmarés, como en 7 |
| Táctica, estilo, entrenadores, jugadores | | como en 7; el número de jugadores es **un byte** |

Desaparecen del equipo el nombre del estadio, la latitud, los dos aforos, las medidas del campo y el año del estadio.

## PC Fútbol 2001

Igual que 2000 con **tres diferencias**, y las tres desplazan lo que va detrás:

1. **Un byte más tras el año de fundación**, cuyo significado está **sin confirmar**.
2. **El historial mide 83 bytes**, no 82: tiene un byte extra al principio (ver abajo).
3. **El número de jugadores ocupa dos bytes**, no uno. Por eso en 2001 cabe una plantilla de 463.

Como la versión es 800 en las dos ediciones, **no hay nada en el registro que te diga si es de 2000 o de 2001**. Tienes que saberlo por el juego del que viene. Si lees un fichero de 2001 como de 2000, el primer equipo ya se descuadra.

## El estadio (2000 y 2001)

El fichero `EST…FDI` es el más sencillo de la familia. Cada registro, sin firma ni versión:

| Campo | Tamaño | Qué es |
|---|---|---|
| Nombre | texto | |
| Ancho | 1 byte | metros |
| Largo | 1 byte | metros |
| Desconocido | 1 byte | **sin confirmar**; podría ser la latitud que antes iba en el equipo |
| País | 1 byte | |
| Año de construcción | 2 bytes | |
| Aforo sentado | 4 bytes | |
| Aforo de pie | 4 bytes | |

Un ejemplo de fábrica: el Camp Nou, 72 × 107 metros, país 22, de 1957, con 98.600 asientos.

Como el estadio es un registro aparte, **dos clubes pueden compartir el mismo**: basta con que apunten al mismo código.

## El historial de liga

82 bytes en 7 y 2000; 83 en 2001.

| Posición | Tamaño | Qué es |
|---|---|---|
| +0 | 1 byte | grupo de 2ªB (1 a 4) |
| +1 | 10 × 2 bytes | las últimas diez ligas, de la más antigua a la más reciente: **puesto** (1 byte) y **división** (1 byte) |
| +21 | 1 byte | temporadas en Primera |
| +22 | 2 bytes cada uno | partidos jugados, ganados, empatados, goles a favor, en contra y puntos en Primera |
| +34 | 1 byte | ligas ganadas |
| +35 | 1 byte | subcampeonatos |
| +36 | 46 bytes | posición jornada a jornada de la última temporada (Primera usa 38; Segunda y 2ªB, 42) |

La división usa los códigos de siempre: `0` Primera, `1` Segunda, `2` Segunda B, `3` Tercera. Un `0` en el puesto es «sin dato».

El grupo de 2ªB es fiable: coincide con las tablas del ejecutable en los 80 equipos de la categoría.

**En 2001 hay un byte más en +1**, el grupo de **Tercera**, y todo lo demás va un byte más allá. No es el grupo en el que juega el club, sino **el que le toca por región**: lo llevan todos los clubes españoles, también los de Primera. Son los 17 grupos de la Tercera de entonces, en el orden habitual —el 1 Galicia, el 2 Asturias, el 5 Cataluña, el 7 Madrid, el 12 Canarias…—, y `255` es «sin grupo».

Un aviso: en muchos equipos modestos los campos de temporadas y partidos en Primera traen **valores de relleno** copiados de otro club. Es un dato de fábrica, no un error de lectura.

## El palmarés de copas

En 5.0 y 6.0 era un bloque fijo. Aquí es una **lista**: un byte con el número de entradas y, por cada una, tres bytes —**competición**, **participaciones** y **títulos**—. Un club sin palmarés lleva un `0` y nada más. Por eso **añadir una copa cambia el tamaño del registro**, cosa que el contenedor admite sin problema.

| Código | Competición | | Código | Competición |
|---|---|---|---|---|
| 0 | Copa de la UEFA | | 11 | Primera inglesa anterior a la Premier |
| 1 | Copa del Rey (y la copa nacional de otros países) | | 12 | Segunda inglesa |
| 2 | Copa de Europa | | 13 | Tercera inglesa |
| 3 | Recopa | | 14 | Cuarta inglesa |
| 4 | Supercopa de España | | 15 | Copa de Italia |
| 5 | Copa Intercontinental | | 16 | Supercopa de Italia |
| 6 | Supercopa de Europa | | 17 | Copa Libertadores |
| 7 | F.A. Cup | | 18 | Copa CONMEBOL |
| 8 | Copa de la Liga inglesa | | 19 | Copa Interamericana |
| 9 | Charity Shield | | 20 | Supercopa Sudamericana |
| 10 | Premier League | | | |

Del 0 al 6 son comunes a todos los países; el resto son bloques de Inglaterra, Italia y Sudamérica. Los códigos del 17 al 20 aparecen en 2001. Los títulos de liga no están aquí: van en el historial.

Dos detalles que confunden:

- **Los títulos pueden superar a las participaciones.** En la Copa del Rey y en las copas inglesas, Dinamic solo llevaba la cuenta de títulos y dejó las participaciones a cero. No lo «corrijas» recortando los títulos.
- **Una entrada con las dos cifras a cero sobra**: el juego no las trae. Si quitas una copa, quita la entrada.

## El código de un equipo nuevo

El código no es un número cualquiera. **Van por países, en bloques de 50**: en PC Fútbol 7, España ocupa del 1 al 182, Italia del 201 al 292, Inglaterra del 301 al 393, Alemania del 401 al 465, Francia del 501 al 571… De los bloques posibles, el juego usa 87, y solo siete mezclan dos países.

El juego se fía de ese reparto para saber de dónde es cada club, aunque el registro lleve su país. **Un equipo extranjero metido en un hueco del bloque español da problemas al entrar en las divisiones españolas.** Así que, para dar de alta un club:

1. Busca un hueco **en el bloque de su país** (España acaba en 182 y su bloque llega al 200: caben 18 más).
2. Si el país no tiene bloque o está lleno, **reserva uno entero que no use nadie**.
3. Nunca pases de **9.999**: el escudo se busca por el código con cuatro cifras, y con cinco no lo encuentra.

Al crear un equipo, lo práctico es **copiar los bloques de otro club** —historial, palmarés, táctica y estilo— y poner a cero solo las estadísticas: las diez ligas y las 46 jornadas.
