# PCF 3.0: las tablas de competición

Cómo están hechos `LIGA.DBC`, `COPAREY.DBC`, `EUROPA.DBC`, `UEFA.DBC`, `ARBITROS.DBC` y `COMMENT.DBC`. Parecen listas de textos sueltos, pero son registros con sus números entre medias, y el año de cada temporada va escrito donde menos lo esperas.

## La regla común

Si solo buscas textos, estos ficheros parecen una ristra de nombres de club sin orden. No lo son: **entre cada texto y el siguiente van los números del registro** —partidos, goles, puntos—, todos de dos bytes con el byte bajo primero.

Los cuatro ficheros históricos comparten la misma forma:

```
registro = [texto…] + números de 2 bytes + una MARCA de 2 bytes
```

La marca vale **0** dentro de un grupo. En el último registro de un grupo lleva **el año del grupo siguiente**, y `9999` significa que se acabó la lista.

Fíjate en lo que implica: **el año va delante del grupo que nombra, no detrás**. Por eso el primer grupo de cada fichero no lleva su año escrito en ninguna parte y hay que saberlo: 1928-29 en la Liga y 1902 en la Copa.

Cómo se sabe que el año abre y no cierra: por **la Guerra Civil**. Los años saltan de 1935 a 1939, y solo si el año abre el grupo cuadran las temporadas con el número de equipos que tuvo cada una de verdad. Si cerrara, la última Liga antes de la guerra saldría con el año de la primera de después.

Todos los textos de estos cuatro ficheros llevan **dos bytes de longitud**, no uno, y van en Latin-1, no en la página de códigos de DOS. Está en [la página del texto](pcf3-texto.html).

## `LIGA.DBC`: la clasificación de cada temporada

Sesenta y tres temporadas, de 1928-29 a 1993-94. Cada fila de la clasificación es:

| Campo | Tamaño |
|---|---|
| Nombre del equipo | texto |
| Partidos jugados | 2 bytes |
| Ganados | 2 bytes |
| Empatados | 2 bytes |
| Perdidos | 2 bytes |
| Goles a favor | 2 bytes |
| Goles en contra | 2 bytes |
| Puntos | 2 bytes |
| Marca | 2 bytes |

Dieciséis bytes de números detrás de cada nombre. Las filas van **en orden de clasificación**: la posición no está guardada, es el orden.

Al pie del fichero, cuando los huecos entre textos se acortan, empieza **el palmarés**: el nombre de cada club y, detrás, un número de dos bytes con sus Ligas ganadas.

## `COPAREY.DBC`: las finales

Noventa y una finales, desde 1902. Cada una es:

```
[fecha]                      texto, p. ej. «20-4»
[campeón] [goles]            texto + 2 bytes
[subcampeón] [goles] [once del campeón] [marca]
```

El **once del campeón** es un texto con su propia longitud de dos bytes delante, metido dentro del hueco del subcampeón. Es largo —los once nombres seguidos— y por eso un escaneo de textos normal no lo ve.

Al pie, igual que en la Liga, el palmarés: club y número de Copas.

## `EUROPA.DBC`: la Copa de Europa

Tres partes, en este orden:

1. **El ranking histórico** de 45 clubes. Detrás de cada nombre, ocho números: puntos, participaciones, partidos jugados, ganados, empatados, perdidos, goles a favor y en contra; y la marca.
2. **Las finales**: la sede y la fecha, el campeón con sus goles, y el subcampeón con sus goles, el once del campeón y la marca, igual que en la Copa.
3. **Los clubes españoles**, con sus puntos.

Los puntos del ranking son **dos por victoria y uno por empate**. Es la comprobación perfecta de que estás leyendo bien las columnas: si las tienes corridas una posición, no cuadrará ni una fila. En unas pocas no cuadra por erratas del propio juego, que también las hay en los nombres de algún club.

## `UEFA.DBC`: a doble partido

La misma estructura, con dos diferencias en las finales: **no hay sede** y se juegan **a ida y vuelta**.

```
[equipo A] [quién ganó]
[equipo B] [goles de A] [goles de B] [goles de A] [goles de B] [marca]
```

El número detrás del equipo A dice quién se llevó la copa: `0` el equipo A, `1` el equipo B. No des por hecho que el primero es el campeón.

Si el **tercer número vale `99`**, la final fue a partido único: no hay vuelta y la marca va justo detrás del segundo.

## `ARBITROS.DBC`

Cuarenta y cuatro colegiados, cada uno con **cuatro textos** seguidos: nombre, provincia de nacimiento, profesión y comité. Sin números.

## `COMMENT.DBC`

Por cada club de Primera, tres apartados: `Novedades en el equipo`, `Sistema de juego` y `Objetivo en la Liga`. Cada uno lleva su párrafo **ya partido en líneas** de unos 75 caracteres, cada línea un texto con un byte de longitud.

Entre bloque y bloque hay separadores binarios de dos o tres bytes. Usa los rótulos de apartado como anclas y recorre lo que hay entre uno y otro.

## Cómo editarlos

- **Los números** se cambian en su sitio: son dos bytes y el fichero no se mueve.
- **Los textos**, conservando la longitud: rellena con espacios lo que sobre y rechaza lo que no quepa. En estos ficheros no se ha comprobado que el juego no los lea por posición, así que no se alargan. Lo mismo vale para el once del campeón: tiene su propio hueco y se queda con él.
- **La marca de año** es también un número de dos bytes. Si cambias un año, ten en cuenta que estás cambiando el del grupo **siguiente**.

Lo que no conviene hacer es añadir o quitar filas, temporadas o finales: no se ha estudiado si el juego espera un número fijo de registros.
