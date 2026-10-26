# Imágenes, pantallas y textos en 7, 2000 y 2001

PC Fútbol 7 guarda sus imágenes en contenedores PKF como los de 5.0 y 6.0; 2000 y 2001 estrenan un contenedor propio, el `PAK_`. Aquí tienes los dos, los nombres y tamaños de cada imagen, y el banco de textos de países y nombres.

## El atajo: imágenes sueltas

Como en 5.0 y 6.0, **el juego lee BMP sueltos** de las subcarpetas de `DBDAT` y los prefiere a los empaquetados. Para cambiar un escudo o una foto en PC Fútbol 7 no hace falta abrir ningún contenedor: dejas el BMP con el nombre adecuado en su carpeta y listo.

Las carpetas que el juego busca: `MINIESC`, `NANOESC`, `RIDIESC`, `BIGESC`, `MINIFOTO`, `BIGFOTO`, `CAMISAS`, `BANDERAS`, `MINIBAND` y `ESTADIO`.

## PC Fútbol 7: nombres y tamaños

| Imagen | Fichero suelto | Tamaño | Va por |
|---|---|---|---|
| Escudo pequeño | `MINIESC\eq98NNNN.bmp` | 48 × 64 | código de equipo, 4 cifras |
| Escudo diminuto | `NANOESC\eq98NNNN.bmp` | 24 × 32 | código de equipo |
| Escudo de clasificación | `RIDIESC\eq98NNNN.bmp` | 17 × 20 | código de equipo |
| Foto pequeña | `MINIFOTO\J98NNNNN.bmp` | 32 × 32 | código de jugador, **5 cifras** |
| Bandera | `BANDERAS\ba96NNNN.bmp` | 30 × 20 | código de país |
| Minibandera | `MINIBAND\…` | 14 × 10 | código de país |
| Camiseta | `CAMISAS\…` | 73 × 38 | código de equipo |
| Foto de estadio | `ESTADIO\eq98NNNN.bmp` | 320 × 240 | código de equipo |

Los de nombre incompleto —minibandera, camiseta, escudo grande y foto grande— tienen la carpeta confirmada, pero **el nombre exacto del fichero suelto está sin confirmar**: el juego lo compone al vuelo. Dentro de los contenedores se llaman `EQ98NNNN.BMP` (por equipo), `J98NNNNN.BMP` (por jugador) y `BA96NNNN.BMP` (por país).

De ahí salen dos techos: **un equipo con código de cinco cifras se queda sin escudo**, y por eso el código no debe pasar de 9.999; los jugadores, con cinco cifras, llegan hasta 99.999.

Y no olvides la **minibandera**: es la que se ve en las clasificaciones. Si solo cambias la bandera grande, la nueva sale en la ficha del país y la vieja sigue en las tablas.

### La foto grande es distinta

Las fotos de ficha no son BMP de paleta fija: son **GIF89a de 124 × 182**, cada uno con su propia tabla de colores (unos 161), agrupados en un contenedor por equipo: `BIGFOTO\EQ98NNNN.PKF`. Es la razón de que se vean mucho mejor que la foto pequeña.

## Las paletas de PC Fútbol 7

Los BMP son de 256 colores, pero **la paleta no es la de 5.0 y 6.0**. Son dos fijas:

- **La principal**: escudos y fotos pequeñas. Es la misma en todos —el BMP de un escudo y el de una foto llevan idéntica paleta—.
- **La de banderas**: banderas y minibanderas.

La principal **difiere de la de 5.0 y 6.0 en 19 colores** (los índices 16, 40, 73, 85 a 91, 111 a 116, 129, 197 y 208). Si reutilizas la vieja, casi todo se ve bien y algunos colores salen cambiados, que es peor que verlo todo mal porque cuesta darse cuenta. Lo seguro es sacar la paleta de cualquier BMP original del juego.

Las **fotos de estadio** llevan cada una su paleta propia.

Un consejo para las fotos pequeñas: la paleta principal tiene trece verdes puros que **ninguna foto original usa**. Si conviertes una foto real dejando que use toda la paleta, aparecen puntitos verdes en las caras. Restringe la conversión a los colores que no sean verde ni azul intenso y el problema desaparece.

## PC Fútbol 7: las pantallas

`Recursos.pkf`, `Img.pkf`, `DAT.PKF`, `NGI.pkf` y `AYUDA.PKF` usan el mismo contenedor PKF paginado que [las pantallas de 5.0 y 6.0](v56-pantallas.html), con nombres libres en vez de códigos. Lo que aporta esta edición:

- **Entradas sin nombre.** Además de las entradas normales hay una de **9 bytes**: el byte `03`, la posición y el tamaño. En `Recursos.pkf` hay tres, y son los fondos de 640 × 480 de las portadas. Un lector que no las conozca se para en la primera.
- **GIF animados con apéndice.** Algunos GIF llevan, detrás del final del GIF, el texto `GIFCONnb1.0`, un byte, el número de fotogramas y un registro de 30 bytes por fotograma con su nombre. El GIF se ve bien sin leerlo.
- **`DAT.PKF` guarda las paletas** de las pantallas (`.PAL` y `.IND`).
- **`NGI.pkf` son 164 animaciones FLC**: las caras de los ayudantes del mánager.
- **Los nombres van truncados**: `SEGUIMIENTO_ALPHA.B` es un `.BMP`. Fíate de los primeros bytes del contenido, no de la extensión.

**Qué paleta usa cada pantalla no está en ningún fichero de datos**: lo decide el ejecutable. La regla más fiable es buscar un GIF con el mismo nombre base (`DESAFIO_OFF.BMP` usa la paleta de `DESAFIO.GIF`); los nombres con `_ALPHA` o `MASK` son máscaras en escala de grises. Unos pocos BMP son de 24 bits y no llevan paleta.

## PC Fútbol 2000 y 2001: el contenedor `PAK_`

Todas las imágenes, las pantallas y hasta los textos van en ficheros `.pak`. **No hay compresión**: lo que hay dentro son ficheros estándar —BMP, GIF, JPEG, paletas `RIFF`, fuentes, FLC, texto— uno detrás de otro.

| Posición | Tamaño | Qué es |
|---|---|---|
| 0 | 4 bytes | `PAK_` |
| 4 | 4 bytes | versión: `0x100` en 2000; `0x101` o `0x102` en 2001 |
| 8 | 4 bytes | `0x40000` si los nombres van cifrados, `0` si van en claro |
| 12 | 4 bytes | número de entradas |
| 16 | — | el índice |

**Las entradas del índice no miden lo mismo.** Cada una es:

| Campo | Tamaño |
|---|---|
| Posición del fichero, desde el inicio del `.pak` | 4 bytes |
| Tamaño | 4 bytes |
| Tamaño otra vez (sería el descomprimido; siempre coincide) | 4 bytes |
| Nombre, terminado en `00` | variable |
| Relleno hasta múltiplo de 4 | 0 a 3 bytes |

Es fácil equivocarse aquí: en los `.pak` de escudos los nombres miden todos 20 caracteres y cada entrada sale de 36 bytes justos, así que un lector de entradas fijas funciona… hasta que abres uno con rutas largas. El índice acaba donde empieza el primer fichero.

### Los nombres cifrados

Si el indicador vale `0x40000`, cada letra del nombre va con un XOR que **avanza una unidad por letra**:

```
letra[i] = cifrado[i] XOR ((K + i) & 0xFF)
```

La clave inicial `K` **cambia de una entrada a otra** (en la práctica es `0x80` más la longitud del nombre). La forma robusta de sacarla es otra: dentro de un mismo `.pak` todos los nombres empiezan por la misma letra —la `g` de `graficos\` en el de gráficos—, así que `K` es el primer byte cifrado XOR esa letra. El `00` final y el relleno **no van cifrados**, que es lo que permite saber dónde acaba cada nombre.

En 2001 los nombres van en claro, pero **varios `.pak` de 2001 son copias de los de 2000 y siguen cifrados**. Decide por el indicador, no por la edición. Hay una excepción conocida: `Simuldat\gestos.PAK` de 2001 usa un XOR constante, `0xA5`.

### Editar un `.pak`

Como las posiciones son absolutas, no hace falta reescribir el fichero entero: **añade el fichero nuevo al final y cambia los 12 bytes de su entrada** (posición, tamaño y tamaño). El nombre no se toca, y los demás ficheros no se mueven. Así se puede cambiar un gráfico de un `.pak` de 90 MB sin rehacerlo.

Los BMP de dentro pueden venir comprimidos con el RLE estándar de BMP (de 8 o de 4 bits), que no todos los visores entienden.

### Qué hay en cada `.pak`

| Fichero | Entradas | Contenido |
|---|---|---|
| `Graficos.pak` (2000) · `GRAFICOS.PAK` (2001) | 3.891 · 4.594 | todas las pantallas, por secciones, con carpetas de idioma |
| `img.pak` | 185 | iconos |
| `dat.pak` | 13 | las paletas de pantalla, las mismas de PC Fútbol 7 |
| `rc_dbase.pak` | 265 | la base de datos |
| `Winfonts.pak` | 98 | fuentes |
| `NGI.pak` | 108 | GIF de los ayudantes |
| `Simuldat\TEXTURAS.PAK` | 5.413 | texturas del simulador |

Las cifras son de 2000 salvo donde se indica. En `DBDAT` van los de escudos, fotos, banderas y estadios, y el de textos.

El juego también lee BMP sueltos en las subcarpetas como en 7; el nombre exacto que espera cada edición está **sin confirmar**.

## Los textos: países y nombres inventados

Es el equivalente de [los nombres que el juego inventa](v56-textos.html) de 6.0. En PC Fútbol 7 está en `DBDAT\textos.pkf` (341 entradas, contenedor PKF); en 2000 y 2001, en `DBDAT\TEXTOS.PAK` (219 entradas). Dentro, cada entrada es una lista de textos con esta forma:

| Campo | Tamaño | Qué es |
|---|---|---|
| Marca | 4 bytes | `DMLT` |
| Reserva | 4 bytes | suma de las longitudes **más** el número de textos |
| Número de textos | 4 bytes | |
| Textos | — | cada uno con sus dos bytes de longitud, cifrado con XOR `0x61` |

El segundo campo **se calcula**: es lo que ocuparían los textos con un cero detrás de cada uno, la memoria que el juego reserva antes de leer. Si añades nombres y no lo recalculas, le estás diciendo que reserve menos de lo que le vas a dar.

Las entradas se llaman por familia y número:

- **`PAISES.N`**: los 207 nombres de país, donde `N` es el idioma (22 español, 24 francés, 30 inglés, 36 italiano y, solo en 2000 y 2001, 2 alemán). **La posición en la lista es el código de país**, el mismo de [la tabla de países](v56-tablas.html), con un `XXX` en el 0. La lista es posicional: puedes renombrar, pero **nunca quites una entrada** o todos los países siguientes se corren.
- **`NOMBRES.N`** y **`APELLIDO.N`**: los nombres y apellidos que el juego usa para la cantera, aquí con `N` = país. Unos cien países por edición. PC Fútbol 7 trae además `APELLIDOS.N`, una lista más larga.

Que el juego los lee está comprobado en el propio ejecutable de las tres ediciones, que lleva las rutas `dbdat\textos\paises.%u`, `nombres.%u` y `apellido.%u`.

Aquí **no hay** nombres de competiciones ni textos de la interfaz: esos están en claro en el ejecutable.
