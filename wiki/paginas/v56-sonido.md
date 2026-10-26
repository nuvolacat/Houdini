# Música y sonido

## La música: módulos de tracker

En `MUSICAS.PKF` hay **ocho piezas en 5.0 Oro y diez en 6.0 Oro**, y no son ficheros de audio normales: son **módulos de tracker**, del formato que usaba ScreamTracker 3.

| Pieza | Ocupa |
|---|---|
| `DINABAS2.S3M` | 343.708 B |
| `DINAMIC1.S3M` | 330.322 B |
| `DINABASE.S3M` | 269.832 B |
| `DINAMIC5.S3M` | 238.812 B |
| `DINAMIC0.S3M` | 222.067 B |
| `DINAMIC4.S3M` | 220.816 B |
| `DINAMIC3.S3M` | 214.988 B |
| `DINAMIC2.S3M` | 179.300 B |

Se reconocen porque **a 44 bytes del principio llevan la marca `SCRM`**. Es la comprobación que confirma que has extraído bien uno.

Un módulo de tracker no guarda el sonido grabado, guarda **la partitura y los instrumentos por separado**: unas pocas muestras cortas más las instrucciones de cuándo suena cada una y a qué nota. Por eso una canción de tres minutos ocupa doscientos kilobytes en vez de treinta megas. Era la forma habitual de meter música en un juego cuando el espacio contaba.

**Consecuencia práctica:** no puedes meter un MP3 tal cual. Para poner tu propia música hay que convertirla a módulo, y eso implica reducir la canción a un puñado de muestras — se pierde calidad, inevitablemente, porque el formato funciona así.

Lo que sí es cómodo es **intercambiar las que ya hay**, o editarlas con cualquier programa de tracker de los que siguen existiendo. Los módulos son un formato vivo y bien documentado.

> Aparte de esto, el CD del juego trae audio de más calidad en ficheros sueltos, fuera de los contenedores. Eso no se instala en el disco duro: si lo quieres tocar, hay que copiarlo de tu CD del juego.

## Los efectos de interfaz

En la carpeta `SONIDOS` hay seis ficheros con extensión `.RAW`:

| Fichero | Ocupa | Qué es |
|---|---|---|
| `CORTIN8.RAW` | 48.117 B | La cortinilla |
| `ABRIR8.RAW` | 18.364 B | Abrir una pantalla |
| `INTRO8.RAW` | 8.207 B | La introducción |
| `SELEC8.RAW` | 6.144 B | Seleccionar |
| `PASA8.RAW` | 684 B | Pasar de pantalla |
| `BOTE.RAW` | 368 B | El bote del balón |

**Son audio en crudo, sin cabecera de ningún tipo.** Nada más que las muestras, una detrás de otra, de ocho bits. No dicen a qué frecuencia van ni cuántos canales tienen, porque el programa que los reproduce ya lo sabe.

Eso tiene dos consecuencias al sustituirlos: hay que **generar el fichero sin cabecera** —si dejas la de un WAV, sonará un chasquido al principio— y hay que **acertar con la frecuencia**, porque si no el sonido saldrá más agudo o más grave de lo que debe.

Se reconocen fácil en un editor: **empiezan con una racha larga del valor `0x80`**, que en audio de ocho bits sin signo es el silencio — el punto medio entre 0 y 255. Si tu conversor produce ceros donde debería haber `0x80`, el sonido empezará con un chasquido.

## Los comentarios y el ambiente

En la carpeta `SFX` van empaquetados, y son con diferencia lo más pesado del juego:

**Y aquí las dos ediciones no se parecen en nada**, ni en los nombres ni en el tamaño. Esto es lo que hay en cada una, medido:

**5.0 Edición de Oro**

| Contenedor | Ocupa | Cuántos sonidos | Qué lleva |
|---|---|---|---|
| `COMENT.PKF` | 43,0 MB | 512 | Los comentarios del partido |
| `compcf.pkf` | 43,2 MB | 480 | Comentarios, segundo juego |
| `AMBIENTE.PKF` | 2,8 MB | 37 | El público |

**6.0 Edición de Oro**

| Contenedor | Ocupa | Cuántos sonidos | Qué lleva |
|---|---|---|---|
| `compcf6.pkf` | **103 MB** | 576 | Los comentarios del partido |
| `Ambiente.pkf` | 20,9 MB | 150 | El público |
| `aviso022.pkf` | 18,1 MB | 367 | Avisos y locuciones |

Fíjate en el salto: el ambiente pasa de 37 sonidos a **150**, y aparece un contenedor de avisos que en 5.0 no existe. Si vas a por los sonidos de 6.0 buscando los nombres de 5.0, no vas a encontrar ninguno.

Son contenedores propios, distintos del de las imágenes: **no empiezan por la cabecera de 232 bytes**, sino por su propia marca.

Aquí el sonido sí es audio estándar dentro del paquete. Lo que manda es la regla de siempre: **el sustituto tiene que caber en el hueco del original**.
