# Las pantallas del juego

Los fondos, los botones, los rótulos y los iconos que ves al navegar por el menú. Todo eso vive fuera de la carpeta de datos, en tres contenedores en la raíz del juego.

## Los tres ficheros

| Fichero | Qué guarda | En 5.0 Oro | En 6.0 Oro |
|---|---|---|---|
| `RECURSOS.PKF` | Fondos completos, barras, botones y sus estados | 64 elementos · 10 MB | 128 · 10 MB |
| `IMG.PKF` | Iconos: continentes, copas, escudetes, flechas | 128 elementos · 2 MB | 32 · **28 MB** |
| `DAT.PKF` | **Las paletas de color**, más índices y datos auxiliares | 41 elementos · 2 MB | 13 · 0,6 MB |

Fíjate en `IMG` de 6.0: **32 elementos que ocupan 28 MB**. Son pantallas completas, no iconos. El reparto entre los dos contenedores cambia bastante de una edición a otra, así que no des por hecho que lo que buscas está donde estaba.

## Son el mismo contenedor que las imágenes

Buena noticia si ya has abierto los contenedores de escudos: **la estructura es idéntica**. Misma cabecera, mismo índice repartido en trozos con saltos entre ellos, mismos nombres cifrados.

Con una diferencia que importa al programar: en los escudos y las fotos, el nombre siempre sigue un patrón numérico, así que se puede indexar por número. Aquí **los nombres son libres**: `FONDO7`, `BALON`, `BARRAPOPUP`.

> **Pero no los indexes solo por el nombre, porque se repiten.** Estos tres son contenedores **de varias secciones**, y cada sección tiene sus propios nombres. En el `RECURSOS` de 5.0 Oro hay **14 nombres repetidos** de 64 elementos, y en el `IMG` de 6.0 Oro cuatro de 32. Si los guardas en una tabla por nombre, unos pisan a otros y desaparecen sin avisar.
>
> La clave buena es **el nombre más el número de sección**, que va en cada entrada del índice. `RECURSOS` de 6.0 Oro tiene trece secciones; `IMG`, nueve. Está explicado en la página del contenedor.

## Qué hay dentro

Mapas de bits de 256 colores como los escudos, y también:

- **Animaciones en formato GIF.** En el `RECURSOS` de 6.0 Oro hay **8**, entre 120 mapas de bits. En 5.0 Oro no hay ninguna: sus 64 elementos son todos mapas de bits. Otra razón para mirar los primeros bytes en vez de fiarse del nombre.
- **Máscaras de transparencia**: imágenes aparte que dicen qué píxeles del original no se pintan. Se reconocen porque su nombre acaba en `_ALPHA`, y en el `RECURSOS` de 6.0 Oro hay **11**. **En 5.0 Oro no hay ninguna** — esa edición no usa este mecanismo. Si cambias un botón que tiene máscara y te olvidas de ella, saldrá con un recuadro alrededor.
- **Estados de los botones**: la mayoría tiene versión normal, al pasar por encima y pulsada. Hay que cambiarlas todas o el botón parpadeará entre tu diseño y el original.

## Las paletas: el detalle que arruina el trabajo

Esto es lo más importante de este capítulo.

Las imágenes **no llevan sus colores dentro**. Están en paletas guardadas aparte, en `DAT.PKF`, y **cuántas hay depende de la edición**:

| Paleta | Para qué | 5.0 Oro | 6.0 Oro |
|---|---|---|---|
| `MENU.PAL` | El menú principal | sí | sí |
| `MANAGER.PAL` | Las pantallas del manager | sí | sí |
| `DBASE.PAL` | La base de datos | sí | sí |
| `INFOSURF.PAL` | Las pantallas de información | sí | sí |
| `SIMUL0.PAL` a `SIMUL4.PAL` | El simulador, cinco variantes | sí | **no** |
| | **Total** | **9** | **4** |

Las cinco del simulador **solo están en 5.0**. En 6.0 el simulador es otro —el de tres dimensiones— y sus colores no salen de aquí.

Cada pantalla usa la suya. Una imagen preparada con los colores de una y puesta en otra **saldrá con los colores cambiados** — no un poco, radicalmente: los rojos en verde y las caras en azul.

### La buena noticia: son paletas estándar

No hay que reversear nada. **Son paletas RIFF de Microsoft**, el formato de toda la vida: mil cuarenta y ocho bytes con la cabecera `RIFF`, la marca `PAL `, y detrás 256 colores de cuatro bytes cada uno —rojo, verde, azul y un byte reservado—.

Eso significa que **cualquier programa de dibujo o biblioteca de imagen las abre directamente**. Sacas la paleta del contenedor, la cargas en tu editor, y ya trabajas con los colores exactos de esa pantalla.

Cada paleta ocupa **exactamente 1.048 bytes**, en las dos ediciones y todas ellas. Si la tuya mide otra cosa, no has sacado lo que crees.

Junto a cada paleta hay ficheros con su mismo nombre y otra extensión, y también cambian según la edición:

| Extensión | 5.0 Oro | 6.0 Oro |
|---|---|---|
| `.PAL` — la paleta | 9 | 4 |
| `.IND` | 9 | 4 |
| `.BRT` | 9 | **0** |
| `.MIX` | 9 | **0** |

En 5.0 hay tres acompañantes por paleta y en 6.0 solo uno. Ninguno está descifrado, pero **no hacen falta para sustituir una imagen**: los nombres sugieren un índice, una tabla de brillo y una de mezcla, que es lo que un motor de 256 colores necesita para atenuar y fundir sin recalcular. Es una suposición razonable, no un hecho comprobado.

## Un aviso sobre los nombres

Dentro del índice, los nombres largos aparecen **cortados**. Un `SEGUIMIENTO_ALPHA.BMP` puede figurar como `SEGUIMIENTO_ALPHA.B`.

Eso significa que **no te puedes fiar de la extensión** para saber qué tipo de imagen es. Hay que mirar los primeros bytes del contenido, que son los que de verdad lo dicen.

El corte está en **veinte caracteres**, que es lo que ocupa el nombre en el índice. Un `COPA_ITALIA CALENDARIO.BMP` aparece como `COPA_ITALIA CALENDA`, sin extensión siquiera. Los nombres pueden llevar espacios.

## No están en el disco duro

Como la música: estos tres ficheros **viven en el CD**, no en la instalación. Hay que copiarlos de tu CD del juego antes de poder trabajar con ellos.
