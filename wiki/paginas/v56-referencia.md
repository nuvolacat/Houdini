# Referencia: el bloque de equipo campo a campo

La tabla completa, en orden, sin prosa. Es la **transcripción exacta** del formato: cada campo con su tamaño, tal y como los lee el juego.

Para las explicaciones de por qué cada cosa es como es, ve a [el bloque de un equipo](v56-bloque-equipo.html). Esta página es para tenerla al lado mientras programas.

## La versión del bloque decide el layout — y no con un solo umbral

Antes que nada, porque **todo lo demás depende de esto**. Cada bloque lleva su propia versión en los dos bytes que siguen al puntero. Estos son los valores que existen y qué implica cada uno:

Este es el censo completo: **todos los valores que aparecen** en los ocho ficheros del juego, con cuántos bloques lleva cada uno.

| Versión | Cabecera | Últimas diez ligas | Jornadas | Cuántos bloques |
|---|---|---|---|---|
| `0x19F` (415) | de 5.0 | 10 bytes, solo el puesto | 42 | 1.070 |
| `0x1F4` (500) | de 5.0 | 10 bytes, solo el puesto | 42 | 1.013 |
| `0x1F9` (505) | de 5.0 | 10 bytes, solo el puesto | 42 | 252 |
| `0x1FE` (510) | de 5.0 | 10 bytes, solo el puesto | 42 | 181 |
| `0x203` (515) | **de 5.0** | **20 bytes, con la división** | **46** | 44 |
| `0x20D` (525) | de 6.0 | 20 bytes, con la división | 46 | 1.441 |
| `0x258` (600) | de 5.0 | 20 bytes, con la división | 46 | **1** |

Dos avisos sobre esta tabla, porque las dos cosas descolocan:

**Un mismo fichero mezcla varias versiones.** No es que cada edición tenga la suya: la Edición de Oro de 5.0 trae cuatro valores distintos entre sus 481 equipos, y Apertura 97 trae **seis**. Hay que mirar la versión de **cada bloque**, siempre.

**Y hay un bloque, uno solo en todo el juego, con `0x258`.** Está en Apertura 97. No es un error de lectura —la regla de los dos umbrales lo coloca bien— pero conviene saber que existe para no pensar que te has perdido cuando aparezca.

**Fuera de los ficheros de equipos aparece uno más.** En los 469 bloques sueltos que la Edición de Oro de 6.0 trae empaquetados aparte hay **dos con `0x208` (520)**, un valor que no sale en ningún fichero de equipos. Cae por encima del umbral, así que se lee con el historial de 6.0 y la cabecera de 5.0, igual que el `0x203`. Lo digo porque la tabla de arriba es el censo de los ficheros de equipos, y **hay vida fuera de ellos**: no des la lista por cerrada, aplica la regla.

**Fíjate en el `0x203`.** Es el de las ediciones argentinas, y es la trampa: tiene el historial de 6.0 pero **la cabecera de 5.0**. Si decides todo el layout con un solo umbral, ese caso te sale mal — y no falla ruidosamente, sale un aforo de ocho mil y pico donde debería haber ciento y pico.

La regla exacta, entonces, son **dos umbrales distintos**:

- **La cabecera es la de 6.0 solo si la versión es `0x20D`.**
- **El historial lleva pares y 46 jornadas si la versión es `0x200` o mayor.**

## Club de la liga nacional

| Campo | Bytes | Notas |
|---|---|---|
| Firma «Copyright (c)AAAA Dinamic Multimedia» | 36 | texto sin cifrar; delimita el bloque |
| Puntero del equipo | 2 | identificador interno del bloque |
| Versión del fichero | 2 | **decide el resto del layout** |
| Idioma | 1 | 0 = español |
| Marca de liga | 1 | 0 = club de la liga nacional |
| Nombre corto | texto | el que se ve en el juego |
| Nombre del estadio | texto |  |
| País | 1 |  |
| Latitud del estadio | 1 · solo v6 |  |
| Nombre largo | texto | solo base de datos |
| Aforo | 4 | valor en 3 bytes + un `00` |
| Plazas de pie | 4 en v6 · **variable en v5** | ver abajo |
| Ancho del terreno | 2 | metros + un `00` |
| Largo del terreno | 2 | metros + un `00` |
| Año de fundación | 2 |  |
| Año del estadio | 2 · solo v6 |  |
| Socios | 4 | valor en 3 bytes + un `00` |
| Presidente | texto |  |
| Presupuesto de base de datos | 4 |  |
| Presupuesto del juego | 4 | el dinero con el que juegas |
| Patrocinador | texto |  |
| Proveedor | texto |  |
| Puntero del primer filial | 2 | `FFFF` = ninguno |
| Puntero del segundo filial | 2 | `FFFF` = ninguno |
| Grupo de Segunda B | 1 | 0 si el club no es español |
| Últimas diez ligas | 10 en v5 · 20 en v6 | en v6, pares de puesto y división |
| Temporadas en Primera | 1 |  |
| Partidos jugados | 2 |  |
| Partidos ganados | 2 |  |
| Partidos empatados | 2 |  |
| Goles a favor | 2 |  |
| Goles en contra | 2 |  |
| Puntos | 2 |  |
| Veces campeón | 1 |  |
| Veces subcampeón | 1 |  |
| Posiciones por jornada de la temporada anterior | 42 en v5 · 46 en v6 | un byte por jornada |
| Palmarés | 14 + extensión | ver abajo |
| Táctica dibujada | 176 | 11 jugadores × 16 bytes |
| Táctica de equipo | 7 | toque, contragolpe, ataque, entradas, marcaje, despejes, presión |
| Entrenador | marca `02` | **puede haber varios seguidos** |
| Fichas de jugador | marca `01` | |
| Cierre del bloque | 1 | un byte `00` |

**«texto»** significa: dos bytes con la longitud, byte bajo primero, y después esos bytes cifrados con XOR `0x61`.

### Las plazas de pie no se deciden por la versión

El campo más incómodo de todos. En 6.0 están siempre y ocupan cuatro bytes. **En 5.0 unos clubes lo llevan y otros no, y no hay ninguna versión ni bandera que lo diga.**

La única forma de saberlo es **probar**: después del aforo, mira si los bytes siguientes parecen unas dimensiones de campo creíbles —un ancho entre 30 y 90 metros, un largo entre 80 y 130, cada uno con su cero detrás—.

- Si lo parecen, no hay plazas de pie.
- Si no, prueba **tres bytes más allá**. Si ahí sí lo parecen, las plazas de pie ocupan tres.
- Si tampoco, prueba **cuatro**. Es el caso de las ediciones argentinas, donde llevan su cero de separación.

Suena a chapuza y lo es, pero es exactamente lo que hay que hacer: probado sobre los 1.066 clubes nacionales de las ocho bases, resuelve todos.

## Club extranjero

Mucho más corto. Se salta todo el bloque de datos de club.

| Campo | Bytes | Notas |
|---|---|---|
| Firma | 36 | igual |
| Puntero del equipo | 2 | |
| Versión del fichero | 2 | |
| Idioma | 1 | |
| Marca de liga | 1 | normalmente 1 |
| Nombre corto | texto | |
| Nombre del estadio | texto | |
| País | 1 | |
| Latitud del estadio | 1 · solo v6 | |
| Nombre largo | texto | |
| Aforo | 4 | |
| Plazas de pie | 4 · solo v6 | |
| Ancho del terreno | 2 | |
| Largo del terreno | 2 | |
| Año de fundación | 2 | |
| Táctica dibujada | 176 | |
| Táctica de equipo | 7 | |
| Entrenador y jugadores | | |

**No tienen** año del estadio —aunque los nacionales de v6 sí—, ni socios, presidente, presupuestos, patrocinador, proveedor, filiales, historial, palmarés ni jornadas.

## La ficha de un jugador

| Campo | Bytes | Notas |
|---|---|---|
| Marca | 1 | `01` |
| Puntero del jugador | 2 | |
| Dorsal | 1 | |
| Nombre corto | texto | |
| Nombre largo | texto | |
| Bloque fijo | 18 | ver abajo |
| País de nacimiento | 1 | **solo en clubes nacionales** |
| Diez textos de base de datos | texto ×10 | **solo en clubes nacionales**; ver el orden abajo |
| Medias | 10 | |

### El bloque de 18 bytes

| Posición | Bytes | Campo |
|---|---|---|
| 0 | 1 | Posición en la plantilla |
| 1 | 1 | Situación en el club |
| 2 | 6 | Las seis demarcaciones |
| 8 | 1 | País |
| 9 | 1 | Color de piel |
| 10 | 1 | Color de pelo |
| 11 | 1 | Puesto |
| 12 | 1 | Día de nacimiento |
| 13 | 1 | Mes de nacimiento |
| 14 | 2 | Año de nacimiento |
| 16 | 1 | Altura en centímetros |
| 17 | 1 | Peso en kilos |

### Las diez medias, en orden de fichero

| | 5.0 | 6.0 |
|---|---|---|
| 1 | Velocidad | Velocidad |
| 2 | Resistencia | Resistencia |
| 3 | Agresividad | Agresividad |
| 4 | Calidad | Calidad |
| 5 | **Regate** | **Remate** |
| 6 | **Remate** | **Regate** |
| 7 | Pase | Pase |
| 8 | Tiro | Tiro |
| 9 | Entradas | Entradas |
| 10 | Portero | Portero |

**El quinto y el sexto van intercambiados entre versiones.** Es el error clásico al portar datos.

### Los diez textos, en orden

1. Lugar de nacimiento
2. Club de debut
3. Internacional
4. Perfil
5. Características
6. Palmarés
7. Internacionalidad
8. Anécdotas
9. Última temporada
10. Trayectoria

## La ficha del entrenador

| Campo | Bytes | Notas |
|---|---|---|
| Marca | 1 | `02` |
| Puntero | 2 | |
| Nombre corto | texto | |
| Nombre largo | texto | **solo en clubes nacionales** |
| Perfil | texto | solo nacionales |
| Sistemas habituales | texto | solo nacionales |
| Palmarés | texto | solo nacionales |
| Anécdotas | texto | solo nacionales |
| Última temporada | texto | solo nacionales |
| Trayectoria | texto | solo nacionales |
| Marca | 1 | `03`, si viene lo siguiente |
| Trayectoria como jugador | texto | |
| Declaraciones | texto | |

En un club extranjero, **la ficha del entrenador acaba tras el nombre corto**.

Y puede haber **varios entrenadores seguidos** antes de los jugadores.

## El palmarés

Catorce números, en parejas de participaciones y títulos: UEFA, Copa del Rey, Copa de Europa, Recopa, Supercopa de España, Intercontinental y Supercopa de Europa.

| Tamaño del bloque | Ediciones |
|---|---|
| 14 bytes | 5.0, 5.0 Oro y la primera temporada de 6.0 Oro |
| 42 bytes | 6.0, la segunda temporada de 6.0 Oro, y las dos de Apertura |
| 48 bytes | Premier y Calcio |

## La táctica dibujada: 176 bytes

Once jugadores de dieciséis bytes cada uno. Cada jugador, ocho valores de dos bytes:

| Valor | Qué es |
|---|---|
| 1 y 2 | Esquina de su zona: x, y |
| 3 y 4 | Tamaño de su zona: ancho, alto |
| 5 y 6 | Dónde se coloca **defendiendo** |
| 7 y 8 | Dónde se coloca **atacando** |

El eje x recorre el campo a lo largo, con el 0 en la portería propia. El eje y a lo ancho, con el centro alrededor de 88.

El primer jugador es el portero y **es idéntico en las quince formaciones del juego**. Sus ocho valores son exactamente estos:

```
0, 66, 42, 66, 0, 88, 0, 88
```

Es decir: zona con esquina en (0, 66) y tamaño 42 × 66, y posición (0, 88) tanto defendiendo como atacando. Son los primeros dieciséis bytes de cualquier táctica y sirven de comprobación inmediata: **si no te salen esos números, no estás leyendo una táctica**.

### Por qué esta lectura y no otra

Circula una interpretación que lee los cuatro primeros valores como **dos esquinas** del rectángulo en vez de como esquina más tamaño. Las dos dan números creíbles, así que no se puede decidir a ojo.

Los datos sí deciden. Comprobando las quince formaciones por sus once jugadores y sus dos situaciones —**330 casos**— las posiciones de defender y atacar caen dentro de su rectángulo **en los 330** leyéndolo como esquina y tamaño. Con la otra lectura, no.

### Y una comprobación bonita

**El número de jugadores cuya zona empieza pegada a la portería reproduce el primer dígito de la formación.** En un 4-4-2 hay cuatro (más el portero); en un 5-3-2, cinco. Se cumple en las catorce formaciones que llevan números en el nombre.

Sirve para verificar que has leído bien sin tener que dibujar nada.

Los ejes: el primero recorre el campo a lo largo, con el 0 en la portería propia; el segundo a lo ancho, con el centro en 88.

## La táctica de equipo: 7 bytes

| Byte | Qué controla | Valores |
|---|---|---|
| 1 | Porcentaje de toque | lo normal es **50** |
| 2 | Porcentaje de contragolpe | lo normal es **50** |
| 3 | Ataque | 0 ofensivo · 1 especulativo · 2 mixto |
| 4 | Entradas | 0 a 2; lo más común es **1** |
| 5 | Marcaje | 0 en zona · 1 al hombre |
| 6 | Despejes | 0 al jugador · 1 en largo |
| 7 | Presión | 0 a 2; lo más común es **1** |

Para saber qué es «normal», estos son los repartos reales sobre los 1.052 equipos de las ocho bases que llevan táctica: el toque y el contragolpe están en 50 en siete de cada diez equipos; el marcaje y los despejes se reparten casi a la mitad entre sus dos valores; y en el ataque gana el ofensivo, seguido del mixto.

Si al leer te salen valores fuera de estos rangos, **revisa por dónde te has descolocado**: en los 1.052 equipos comprobados solo dos dan valores imposibles, y son bloques mal leídos.

## La comprobación que valida todo

Desde el final del palmarés, **176 + 7 bytes** tienen que caer exactamente en el `02` del entrenador. Y al terminar de leer las fichas, tienes que estar justo donde empieza la firma del equipo siguiente.

Si las dos cuadran en todos los equipos del fichero, tu lector es correcto.
