# Los contenedores menos conocidos

Además de los escudos y las fotos, la carpeta del juego trae unos cuantos ficheros que casi nadie abre. Aquí está lo que hay en cada uno.

Algunos solo existen en 6.0: la 5.0 no los trae.

| Contenedor | Tamaño | Elementos | Tamaño típico de cada uno |
|---|---|---|---|
| `SIMULDAT.PKF` | 83,8 MB | 128 | 66.612 B |
| `fondos.pkf` | 6,1 MB | 20 | 307.226 B |
| `DATSIM.PKF` | 5,8 MB | 1.609 | 192 B |
| `RC_DBASE.PKF` | 3,5 MB | 234 | variable |
| `eqpcplus.pkf` | 2,7 MB | 469 | variable |
| `MUSICAS.PKF` | 2,0 MB | 8 | ~250.000 B |
| `estadio.pkf` | 1,5 MB | 20 | 76.828 B |
| `BIGARBIT.PKF` | 334 KB | 43 | 7.706 B |
| `textos.pkf` | 149 KB | 218 | variable |

Que **todos los elementos de un contenedor midan lo mismo** es una pista útil: significa que son imágenes de tamaño fijo, y del tamaño se deducen las dimensiones.

## `RC_DBASE` — la interfaz de la base de datos

Más de doscientos elementos: iconos, fondos de pantalla completos, cuadros y **botones en sus distintos estados** — sin pulsar, pulsado, iluminado.

Es donde hay que mirar si quieres cambiar el aspecto de las pantallas de consulta. Los nombres son descriptivos y se entienden solos, del tipo `ICO_ENTRADA` o `BOT_PLAY SIN PULSAR`.

Ojo con los botones: **cada uno tiene varias imágenes**, una por estado. Si cambias solo una, el botón parpadeará entre tu diseño y el original al pasar por encima.

## `BIGARBIT` — las fotos de los árbitros

Cuarenta y tres retratos, con el mismo formato que las fotos de jugador y numerados por el identificador del árbitro.

Es de los pocos sitios donde el juego guarda gente que no juega. Si actualizas la base a una temporada moderna y quieres que los árbitros se correspondan, están aquí.

## `estadio` y `fondos` — las panorámicas

Dos contenedores con veinte imágenes cada uno, numeradas por equipo: `estadio` a 320 × 240 y `fondos` a pantalla completa, 640 × 480.

Junto con la de `BIGCAMP`, que mide 200 × 140, son **tres imágenes distintas del mismo estadio** para tres sitios distintos del juego. Se detallan en [escudos, fotos y banderas](v56-imagenes.html).

## `eqpcplus` — un contenedor lleno de DBC

Este es el más curioso de todos. Contiene **cuatrocientos sesenta y nueve ficheros DBC**, es decir, cuatrocientos sesenta y nueve equipos completos empaquetados juntos.

Es la prueba de que el propio juego usa el mecanismo de los DBC para distribuir equipos, no solo los editores. Si quieres ver cómo es un DBC bien formado, aquí tienes cuatrocientos ejemplos oficiales para comparar con lo que generes tú.

**Pero es más que un ejemplo: es una segunda base de datos jugable.** La edición Oro de 6.0 tiene un «modo Plus» que es la temporada siguiente, y este contenedor es su base. Los datos son distintos de los de la principal — el Barcelona de aquí tiene veintitrés jugadores y ciento veinte mil de aforo, y el de la base normal veintiocho y ciento ocho mil.

O sea que **un mod que solo toque el fichero de equipos deja el modo Plus sin actualizar**. Quien entre por ahí seguirá viendo las plantillas originales.

## `SIMULDAT` — el simulador en tres dimensiones

El más grande de todos: **más de ochenta megabytes**. Dentro hay ficheros con extensión `.P3D`, y no son solo cámaras: son **todo lo que el simulador dibuja en tres dimensiones**.

| Fichero | Qué es |
|---|---|
| `1CAMARA` … `10CAMARA` + su `TARGET` | Las diez cámaras: por dónde va el punto de vista y hacia dónde mira |
| `CESPED`, `ESTADIO`, `VALLAS` | El césped, el estadio y las vallas |
| `BALON` | El balón |
| `LINPARADO`, `LINANDANDO`, `LINTROTANDO`, `LINCORRIENDO`, `LINSPRINT`, `LINDERECHA`, `LINIZQUIERDA`, `LINCORNER`, `LINJUEGO` | **Las animaciones del juez de línea**: parado, andando, trotando, corriendo, esprintando… |

Todos empiezan igual: cuatro bytes de marca, `FE FF 7F FF`, y **detrás un nombre en texto plano** — `Box01`, `Box02`. Ese nombre es la pista de dónde salieron: es el que pone por defecto la herramienta de modelado en tres dimensiones con la que Dinamic los hizo.

### Cómo se leen las trayectorias de cámara

Esto ya está resuelto, y es más sencillo de lo que parecía.

Los veinte ficheros de cámara y objetivo ocupan **exactamente lo mismo: 32.244 bytes**. Tras una cabecera de **444 bytes** viene la trayectoria, que son **2.650 puntos de doce bytes cada uno**. La cuenta cierra al byte: 444 más 2.650 por 12 son los 32.244. Sin sobrar nada, en los veinte.

Cada punto son **tres números decimales de cuatro bytes**: las coordenadas X, Y y Z.

Y se puede comprobar que la lectura es la buena sin salir de los propios números, porque **son metros de un campo de fútbol**:

- **X e Y** se mueven entre unos −55 y +58, que es un terreno de juego visto desde el centro.
- **Z nunca es negativo.** Va de 0 a 28,6. Es **la altura**, y ninguna cámara se mete bajo tierra.

Esa última es la comprobación decisiva: si al leerlo te salen alturas negativas, el orden de las coordenadas o el arranque no son los correctos.

La altura además distingue las cámaras entre sí de forma reconocible: la primera no pasa de **4,9 metros** —una cámara a pie de campo— y la décima llega a **28,6**, que es la de la grada alta.

### Y en los 444 bytes de cabecera hay poco que buscar

Merece la pena decirlo porque ahorra perder una tarde. De esos 444 bytes, los primeros veinticuatro llevan la marca, el nombre del objeto y unos pocos números. **El resto tiene toda la pinta de ser memoria sobrante del programa que escribió el fichero**, no datos.

Leídos como números de cuatro bytes, lo que aparece son cosas como `0x0012E398` y `0x0012E41C` —dos direcciones de la pila separadas por unos pocos bytes—, `0x77E711A0` —el rango donde Windows carga sus bibliotecas— y grupos de valores casi iguales entre sí. Es el aspecto clásico de un trozo de memoria sin inicializar que se vuelca a disco tal cual, y era comunísimo en el software de los noventa.

No está probado al cien por cien —hay un tercio de valores que no encajan en ningún rango reconocible—, pero la conclusión práctica no cambia y es la de siempre en estos casos: **copia la cabecera tal cual del fichero original y no intentes generarla**. No hay nada que calcular ahí.

Lo que sí queda por resolver es cómo se leen los ficheros de geometría y de animación, que no siguen la estructura de las trayectorias.

## `DATSIM` — mucho más que las equipaciones

Se le conoce por las camisetas del partido, pero eso es solo una parte. De sus mil seiscientos elementos:

- **Mil quinientos ochenta y cuatro son las equipaciones**, dos por equipo — la de campo y la del portero.
- El resto son **los gráficos del partido**: el balón, el reloj del marcador, el fondo del terreno y los carteles de gol y de penalti fallado.

Los gráficos del partido usan formatos propios distintos de los del resto del juego. Están identificados pero no descritos byte a byte.
