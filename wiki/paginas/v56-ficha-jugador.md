# La ficha de un jugador en 5.0 y 6.0

Todos los jugadores de un club van uno detrás de otro, sin índice ni separadores especiales. Cada ficha empieza con un byte `01` y a partir de ahí los campos van en orden fijo.

## Los campos, en orden

| Campo | Tamaño | Qué es |
|---|---|---|
| Marca de inicio | 1 byte | siempre `01` (el `02` es el entrenador) |
| Puntero | 2 bytes | el identificador del jugador; único en todo el juego |
| Dorsal | 1 byte | el número de la camiseta |
| Nombre corto | texto | el que se ve en las alineaciones |
| Nombre largo | texto | el completo, para la base de datos |
| Bloque de datos | 18 bytes | todo lo de abajo |
| País de nacimiento | 1 byte | *solo en clubes de la liga nacional* |
| Diez textos de base de datos | texto | *solo en clubes de la liga nacional* |
| Medias | 10 bytes | los atributos |

Los dos campos marcados son la diferencia más importante entre un club de la liga que juegas y un club extranjero: **los extranjeros no guardan datos de base de datos**. No es un fallo ni un recorte del editor, es así en el juego original.

O sea que la ficha de un jugador extranjero es: marca, puntero, dorsal, los dos nombres, los 18 bytes y **directamente las diez medias**. Nada entre medias.

Es la diferencia que más lectores rompe, porque **no falla ruidosamente**: si tratas a un extranjero como nacional, te pones a leer diez textos donde hay medias y datos del jugador siguiente, y lo que sale es basura convincente.

## El bloque de 18 bytes

Es la parte densa. Cada byte es un dato distinto:

| Posición | Campo | Valores |
|---|---|---|
| 1 | Posición en la plantilla | ver más abajo |
| 2 | Situación en el club | `0` seguía · `1` fichaje · `2` cantera · `3` baja |
| 3-8 | Demarcaciones | seis; la primera es obligatoria, las otras cinco son las posiciones alternativas |
| 9 | País | el código de nacionalidad |
| 10 | Color de piel del avatar | `1` · `2` · `3` (los tres tonos de cara que dibuja el juego; las etiquetas son las del editor original de 1997) |
| 11 | Color de pelo | `1` rubio · `2` sin pelo · `3` moreno · `4` canoso · `5` pelirrojo · `6` castaño |
| 12 | Puesto | `0` portero · `1` defensa · `2` medio · `3` delantero |
| 13-16 | Fecha de nacimiento | día, mes y año (el año ocupa dos bytes) |
| 17 | Altura | en centímetros |
| 18 | Peso | en kilos |

Como todos ocupan lo mismo pase lo que pase, **estos campos se pueden cambiar sin ningún riesgo**: no alteran la longitud de nada.

### La posición en la plantilla

Este byte confunde a mucha gente porque no es lo que parece. **No es la alineación titular en el sentido de un once dibujado**: es el orden del jugador dentro del plantel, y el juego saca de titulares a los once primeros.

- `1` a `11`: el once
- `12` en adelante: el resto de la plantilla, por orden
- `99`: fuera del plantel

El `99` se combina normalmente con la situación «baja»: son jugadores que están en la base de datos del club pero que el juego no cuenta para el equipo. Los verás marcados como baja dentro del juego.

## Las diez medias

Van al final de la ficha, diez bytes seguidos, cada uno de 0 a 99:

**velocidad · resistencia · agresividad · calidad · regate · remate · pase · tiro · entradas · portero**

Con un aviso importante: **en 6.0, el regate y el remate van intercambiados** respecto a 5.0. Es el error clásico al portar datos de una versión a la otra — los jugadores acaban rematando como regatean.

### Cómo se calcula la media que ves

La media no es un campo del fichero. **Es un cálculo**, y ahí está el segundo malentendido habitual: el juego la saca de **seis** valores, no de cuatro. A las cuatro primeras (velocidad, resistencia, agresividad y calidad) les suma la forma y la moral del momento, y divide entre seis.

Por eso la media que ves en el juego baila aunque no hayas tocado nada: la forma y la moral cambian solas. Las otras seis medias —regate, remate, pase, tiro, entradas y portero— **no entran en el promedio**; describen cómo juega, no cuánto vale.

Y una advertencia sobre la agresividad: en los datos originales **no es una medida de temperamento**. Mírala en el fichero de fábrica y verás que los porteros la tienen tan alta como los delanteros. Funciona como un cuarto pilar de la calidad, no como «este jugador da patadas».

## El puntero del jugador

Es su identificador y es **único en todo el fichero**, no solo dentro de su equipo. Ahí no hay sorpresa.

Lo que sí conviene desmentir, porque manda a la gente por el camino equivocado: **la documentación antigua dice que a cada club le corresponden cincuenta punteros consecutivos**, calculables a partir del suyo. En los ficheros reales **eso no se cumple**: de los 9.299 jugadores de una edición, los que caen en el rango que predice esa fórmula son treinta y tres.

Lo que sí es cierto es que **los jugadores de un mismo club tienden a estar agrupados**: en muchos equipos, todos sus jugadores caben en una franja de cincuenta números. Pero es una **tendencia**, no una regla, y flojea muchísimo según la edición:

| Edición | Equipos cuya plantilla cabe en 50 números |
|---|---|
| Premier | 332 de 477 — **70 %** |
| Calcio · 5.0 Oro | 62 % |
| Apertura 97 | 58 % |
| 5.0 | 47 % |
| 6.0 Oro | 35 % |
| Apertura 98 | 15 % |
| **6.0** | **40 de 484 — 8 %** |

En la 6.0 base la agrupación **prácticamente no existe**. Así que ni siquiera como aproximación sirve: **no hay forma de calcular el rango de punteros de un equipo a partir de su identificador**. Hay que leer los que trae cada ficha.

Para añadir un jugador nuevo, entonces, la única regla segura es **coger un número que no use nadie**.

## ¿Y cuántos jugadores caben?

Otra creencia que conviene revisar. **El formato no impone ningún límite**: el bloque es simplemente la lista de fichas una detrás de otra, sin contador que diga cuántas hay.

Lo que hay son los tamaños que trae el juego. Estos son los mayores de cada edición:

| Edición | Plantilla más grande | Mediana |
|---|---|---|
| 5.0 y 5.0 Oro | 50 (los Juveniles) | 18-19 |
| 6.0 y 6.0 Oro | 50 (los Juveniles) | 18-20 |
| Premier | **51** | 18 |
| Calcio | 50 | 18 |
| Apertura 97 | 50 | 18 |
| Apertura 98 | **52** | 20 |

O sea que **el propio juego trae equipos de cincuenta y dos**, y son sus selecciones juveniles. Si alguna vez has leído que el tope son treinta y cinco, los ficheros lo desmienten.

Lo que sí exige el juego, y esto sí es firme: **al menos once jugadores y al menos un portero** por equipo.

## Sobre el orden de las fichas

Suelen ir **ordenadas por puesto** —porteros, defensas, medios y delanteros—, pero no siempre, y también depende de la edición:

| Edición | Equipos con la plantilla ordenada por puesto |
|---|---|
| 5.0 Oro | 358 de 478 — 75 % |
| Calcio | 74 % |
| Apertura 97 | 71 % |
| Premier · 5.0 | 68-69 % |
| 6.0 Oro | 61 % |
| Apertura 98 | 54 % |
| 6.0 | 52 % |

O sea que **entre uno y cada dos y cinco de cada diez equipos no lo cumplen**. Si tu lector se apoya en ese orden para decidir quién es portero, fallará en un montón de casos: el puesto está en su byte, y ese es el que hay que mirar.

Así que **no des el orden por hecho al leer**. Si tu lector espera encontrarlos ordenados, fallará en uno de cada cuatro equipos.

## Cómo encontrar las medias a ojo

Si estás mirando el fichero a mano, el truco más rápido es este: **desde donde empieza el nombre corto del jugador siguiente, cuenta dieciséis bytes hacia atrás**. Ahí empiezan las diez medias del jugador anterior.

## Los diez textos de base de datos

Solo los tienen los clubes de la liga nacional. Van seguidos, cada uno con su longitud por delante, **en este orden exacto**:

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

Los que no tienen contenido llevan una `x`; vacíos del todo no valen.

### Cómo están escritos por dentro

Los textos largos —perfil, características, palmarés, anécdotas— siguen una convención que conviene respetar si escribes los tuyos: **cada punto empieza por un asterisco** y las líneas se separan con **retorno de carro y salto de línea**, los dos.

La trayectoria es distinta: es **una tabla**. Una línea por temporada, y en cada una **cinco campos separados por comas**, con un guion donde no hay dato. Así se ve la de un jugador real:

```
-,Social Ramos,-,-,-
-,Sao Cristovao,-,-,-
1993,Cruzeiro,1,-,-
```

El primer campo es el año y el segundo el club. Si generas trayectorias, mantén los cinco campos aunque vayan vacíos: el juego cuenta las comas.

La regla de siempre: el hueco de cada uno es el que es.

Merece la pena saberlo por una razón práctica: **son el ochenta y cinco por ciento del tamaño de una ficha**. Si sacas un equipo a un fichero aparte y te olvidas de ellos, el juego se queda esperando datos que no están.
