# Los DBC: sacar un equipo a su propio fichero

Un DBC es **el bloque de un equipo guardado aparte**, en su propio fichero. Misma estructura, mismo contenido; lo único que cambia es que ya no vive dentro del fichero grande.

Esto resuelve el problema más molesto del formato: **dentro del fichero de equipos los textos no pueden crecer**, porque desplazarían todo lo que va detrás. En un fichero suelto no hay nada detrás, así que un nombre puede medir lo que haga falta.

## Dónde van y cómo se llaman

Esto no hay que deducirlo: **las rutas están escritas dentro del ejecutable del juego**, en texto plano, y se pueden leer con cualquier editor. Estas son, tal cual:

| Edición | Dónde busca los DBC de equipo |
|---|---|
| 5.0 Oro | `DBDAT\EQ###···\EQ96####.DBC` |
| 6.0 y 6.0 Oro | `dbdat\eq###···\eq97####.dbc` |
| Apertura 98 | `eq97####.dbc` |
| Apertura 97, Premier, Calcio | `EQ96####.DBC` |
| **5.0 base** | `DBDAT\EQUIPOS\<nombre>.dbc` — **otro esquema** |

La carpeta lleva **dos números de tres cifras** y coincide con el nombre del fichero de equipos: si el tuyo es `EQ022022.PKF`, la carpeta es `EQ022022`. El fichero lleva el prefijo de la edición —`96` o `97`— y el identificador del equipo **en cuatro cifras**.

> **Ese número es la TEMPORADA, no la versión del formato**, y en 6.0 Oro importa: ese fichero trae las dos temporadas dentro y sus equipos van con los dos prefijos. Lo que el juego busca es el `97`. Si sacas el prefijo del primer equipo del índice te dará `96` y **el juego no verá tu fichero**. Está explicado en [el bloque de un equipo](v56-bloque-equipo.html).

El juego los busca al **crear una liga nueva**, no en una partida ya empezada.

### En 5.0 base el mecanismo es distinto

Fíjate en la tercera fila: la 5.0 original **no usa números**, usa un nombre, y la carpeta es otra. Es la única de las cuatro que funciona así, y tiene una consecuencia que verás más abajo.

## También se puede sustituir UN jugador o UN entrenador

Y esto casi nadie lo sabe. Además de los DBC de equipo, **6.0 busca ficheros sueltos por jugador y por entrenador**:

| Qué | Dónde lo busca |
|---|---|
| Un jugador | `dbdat\ju###···\j97#####.dbc` |
| Un entrenador | `dbdat\EN###···\E97#####.DBC` |

El identificador va aquí en **cinco cifras**, no en cuatro, porque los jugadores son muchos más.

La ventaja es evidente: para cambiar a un jugador **no hace falta reconstruir el bloque entero de su equipo**, que es la parte delicada. Basta con dejar su ficha en su fichero.

Esta vía **no está explorada del todo** —no sabemos si el fichero debe contener solo la ficha o algo más— pero las rutas están ahí, en el ejecutable, y es de las cosas que más simplificarían el trabajo si alguien la remata.

Esto último es importante y explica muchas frustraciones: haces el cambio, cargas tu partida guardada y no ha pasado nada. Hay que empezar una liga nueva.

## Las dos diferencias con el bloque de dentro

Son solo dos, pero equivocarse en cualquiera de ellas cuelga el juego.

**Primera: los dos bytes que van tras la firma.** Aquí hay más matiz del que se suele contar, y conviene decirlo con precisión porque hay mucha información contradictoria circulando.

- **Los DBC del propio juego llevan un valor real ahí**, distinto para cada equipo. Comprobado sobre los 469 que trae la edición Oro de 6.0: hay 294 valores distintos, así que no es una marca fija.
- **Poner `FF FF` funciona**, y es lo que hacen los mods modernos. Está probado dentro del juego.
- **Pero hay un valor concreto que lo cuelga**, el que daba un manual clásico y que se ha copiado durante años en tutoriales. Si has seguido uno antiguo y te crashea al crear liga, mira esos dos bytes.

La lectura práctica: la identidad del equipo se la da el **nombre del fichero**, no ese campo. Lo más seguro es **conservar el valor que tuviera el bloque original**; y si generas uno desde cero, `FF FF` es la opción probada.

**Segunda: el cierre del fichero.** Detrás de las medias del último jugador tiene que ir **al menos un byte a cero**. Los DBC oficiales llevan exactamente uno. Sin él, el juego sigue leyendo más allá del final.

## El error que arruina más DBC

Los clubes de la liga nacional guardan, por cada jugador, **diez textos de base de datos** — lugar de nacimiento, club de debut, perfil, características, palmarés y demás; la lista completa y en orden está en [la ficha de un jugador](v56-ficha-jugador.html).

**Esos textos son alrededor del ochenta y cinco por ciento del tamaño del fichero.** Es tentador omitirlos porque no se ven en el simulador, y es exactamente lo que rompe el juego al crear la liga: espera encontrarlos.

Si no tienes esos datos, escribe algo — una `x` basta. Lo que no puede es faltar.

## Un detalle donde el manual clásico se equivoca

En 6.0, **entre el país y el nombre largo hay un byte más** —la latitud del estadio—. Un byte, no dos.

Lo menciono porque la documentación antigua dice dos, y con dos el nombre largo sale desplazado una letra: en vez de «Fútbol Club Barcelona» lees «útbol Club Barcelona» y a partir de ahí todo se descuadra.

Es fácil de comprobar: prueba a saltar uno y a saltar dos, y quédate con el que te dé un nombre limpio.

## La versión del fichero manda

Dentro del bloque hay un campo de versión, y **de él depende cómo se lee todo lo demás**. Los valores que circulan van de 500 a 600, y cada salto cambia cosas concretas:

| Qué cambia | Cuándo |
|---|---|
| Latitud del estadio | solo en un rango concreto de versiones |
| Plazas de pie | a partir de cierta versión |
| Últimas diez ligas | con la división, o solo con el puesto, según la versión |
| Posiciones por jornada | 46 valores o 42, según la versión |
| Palmarés | 42, 34 o 14 apartados, según la versión |

Si un DBC no le cuadra al juego, este campo es el primer sitio donde mirar.

## Lo que el juego exige

Comprobaciones que hace y que, si fallan, dan desde un comportamiento raro hasta un cuelgue:

- **Al menos once jugadores**, y **al menos un portero**.
- Altura por encima de cien centímetros y peso por encima de cincuenta.
- Un año de nacimiento que tenga sentido.

## Dónde ver ejemplos oficiales

La edición Oro de 6.0 trae **469 DBC hechos por Dinamic**, empaquetados en su propio contenedor. Son la mejor referencia que hay: si generas uno y no funciona, compáralo con el del mismo equipo ahí dentro y verás dónde te apartas.

## Añadir equipos que no existían

Aquí viene lo interesante, y es algo que mucha gente no sabe que se puede hacer.

El juego no se limita a buscar el DBC de cada equipo que ya conoce: **explora la carpeta con un comodín**. La ruta está escrita en el ejecutable y se puede comprobar:

```
EQ###···\EQ96*.DBC      (5.0 Oro)
EQ###···\EQ97*.DBC      (6.0 y 6.0 Oro)
```

Ese asterisco lo cambia todo. La consecuencia es directa: **un DBC con un puntero que no ocupa ningún equipo añade un equipo nuevo a la base de datos**.

Está validado por la comunidad: hay mods que meten así ochenta clubes que no existían en el juego original, cada uno con su escudo puesto como imagen suelta.

> **En 5.0 base, no.** Ese ejecutable no tiene ningún patrón con comodín — solo busca ficheros por su nombre exacto. Así que ahí se pueden **sustituir** equipos pero no **añadirlos**. Es la consecuencia de que use otro esquema.

Dos avisos:

**El puntero puede ser cualquiera que esté libre**, no tiene que seguir la numeración oficial. Y los punteros de los jugadores nuevos conviene ponerlos por encima del más alto que ya use el fichero, para no pisar a nadie.

**Añadir un equipo a la base no lo mete en una liga.** El número de plazas de cada división está en el ejecutable. Un club nuevo existirá, saldrá en la base de datos y jugará amistosos, pero para que compita hay que hacerle sitio ahí.

## Los juveniles y sus medias infladas

Un detalle desconcertante: en los equipos juveniles **los atributos están guardados más altos de lo que el juego enseña**, unos cuarenta y pico puntos por encima.

O sea que si abres un juvenil en crudo verás medias imposibles. No están mal: hay que restar esa cantidad para ver el valor real, y volver a sumarla al escribir.
