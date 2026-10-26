# PCF 5.0 y 6.0: qué hay dentro

El mapa de la carpeta del juego. Qué guarda cada fichero, cuál te interesa según lo que quieras cambiar y cuáles conviene no tocar.

Las dos versiones comparten formato. **El nombre del fichero no dice de qué versión es**: hay ediciones que se llaman `EQ0…` y por dentro son formato 5.0. Se distingue por el contenido, no por el nombre.

## Los datos: la carpeta `DBDat`

Aquí vive prácticamente todo lo editable.

| Fichero | Qué guarda |
|---|---|
| `EQUIPOS.PKF` o `EQ******.PKF` | **El corazón.** Todos los equipos, sus jugadores, sus entrenadores, el historial, el palmarés y las tácticas |
| `NANOESC.PKF` `MINIESC.PKF` `RIDIESC.PKF` `BIGESC.PKF` | Escudos de club en cuatro tamaños |
| `MINIFOTO.PKF` y la carpeta `BIGFOTO` | Fotos de jugador: la pequeña de los listados y la grande de la ficha |
| `MINIENTR.PKF` `BIGENTR.PKF` | Fotos de entrenador |
| `BANDERAS.PKF` `MINIBAND.PKF` | Banderas de país |
| `CAMISAS.PKF` | La camiseta que se ve en la ficha del club |
| `BIGCAMP.PKF` | Fotos de estadio. **61**, ni una más, en las dos ediciones |
| `DATSIM.PKF` | Las equipaciones del partido —**1.566** en 5.0 Oro y **1.624** en 6.0 Oro— **y además** unos 45 elementos que no lo son: el balón, el reloj, el cielo y los gráficos del terreno |
| `BIGARBIT.PKF` | Fotos de árbitro: **43**. Solo en 6.0 |
| `estadio.pkf` y `fondos.pkf` | Panorámicas de estadio: **20 en cada uno**. Solo en 6.0 |
| `textos.pkf` | **Los nombres y apellidos que el juego inventa**, por país. Solo en 6.0 |
| `eqpcplus.pkf` | Un contenedor con **469** equipos en formato DBC. Solo en 6.0 |
| `RC_DBASE.PKF` | Los gráficos de la interfaz de la base de datos |
| `SIMULDAT.PKF` | **Todo el simulador en tres dimensiones**: las diez trayectorias de cámara, el césped, el estadio, las vallas, el balón y las nueve animaciones del juez de línea. 83 MB. Solo en 6.0 |

Cuidado con un despiste habitual: **`RIDIESC` no es un escudo aunque lo parezca**. Es la camisetita que sale en las clasificaciones. Si cambias ahí un escudo, lo que rompes es otra cosa.

Y otro: **`DATSIM` no son solo las camisetas**. De sus mil seiscientos y pico elementos, las equipaciones son la inmensa mayoría —1.566 o 1.624 según la edición—, pero los **45 restantes** son otra cosa: el balón, el reloj del marcador, el cielo, la hierba y los fondos del terreno. Se distinguen a simple vista porque **las equipaciones miden exactamente 192 bytes** y se llaman `P96A····` o `P96B····`; lo demás, ni una cosa ni la otra.

## La interfaz y el sonido

| Fichero | Qué guarda |
|---|---|
| `RECURSOS.PKF` `IMG.PKF` `DAT.PKF` | Las pantallas del juego: fondos, botones, rótulos y sus paletas de color |
| `MUSICAS.PKF` | La música en formato de tracker: **8 piezas en 5.0 Oro y 10 en 6.0 Oro** |
| `SFX` y `SONIDOS` | Efectos de sonido y ambiente |
| `RC_DBASE.PKF` | Recursos de la base de datos |

## El ejecutable

`manager.exe` no es un fichero de datos, pero **decide cosas que la gente busca en la base de datos y no están ahí**: cuántas divisiones hay y de cuántos equipos, qué clubes juegan cada competición europea, el año de la temporada, y los límites del juego —cuántos extranjeros puedes alinear, qué fichajes te deja hacer—.

Es la confusión más común: alguien añade equipos a la base y luego no aparecen en la liga. No aparecen porque el número de plazas de cada división está escrito en el ejecutable, no en los datos.

## Lo que no hay que tocar

En 5.0 hay un fichero enorme, `PCF5DAT.PKF`, que ocupa casi 100 MB y no contiene datos editables. No lo toques.

## Por dónde empezar

- **Cambiar plantillas, medias o datos de un club** → el fichero de equipos.
- **Cambiar escudos, fotos o banderas** → los contenedores de imágenes, aunque hay un atajo que evita abrirlos.
- **Cambiar quién juega la liga, o cuántos equipos tiene** → el ejecutable.
- **Cambiar el aspecto del juego** → las pantallas, y `RC_DBASE` para la base de datos.
- **Cambiar los nombres que el juego se inventa** → el contenedor de textos.

## Cómo saber si un fichero es un contenedor de verdad

Un truco que ahorra tiempo: **todo contenedor auténtico lleva su propio nombre escrito en la cabecera**, cifrado. Si lo descifras y sale el nombre del fichero, es un contenedor. Si sale basura, no lo es.

Es exactamente lo que delata a `PCF5DAT`: se llama `.PKF` y no pasa la prueba.
