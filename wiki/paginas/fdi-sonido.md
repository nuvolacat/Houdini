# El sonido en 7, 2000 y 2001

PC Fútbol 7 sigue el esquema de 6.0: sonidos sueltos, comentarios en contenedores PKF y música de tracker. 2000 y 2001 lo cambian todo por un contenedor sin índice, con comentarios comprimidos y música en MIDI o MP3.

## PC Fútbol 7

### Los sonidos de la interfaz: `SONIDOS\`

Ficheros sueltos, de dos tipos:

- **`.RAW`**: audio crudo, sin cabecera. **8 bits sin signo, mono, 11.025 Hz.** El silencio es `0x80`, así que todos empiezan por `80 80 80…`. Son los de abrir, el bote, la cortinilla, la introducción, pasar y seleccionar.
- **`.WAV`**: dos clics, en WAV normal de 8 bits a 22.050 Hz.

Para sustituir un `.RAW` basta con generar audio con esas características y quitarle la cabecera.

### La música: `MUSICAS.PKF`

Siete canciones, cada una un **módulo ScreamTracker 3 (`.S3M`)** completo. El fichero empieza con una cabecera de 1.458 bytes que hace de índice —por cada canción, su posición y su tamaño, cuatro bytes cada uno— y detrás van los siete módulos pegados.

Cada módulo se reconoce porque lleva la firma `SCRM` en su byte 44. Si cambias una canción por otra de distinto tamaño, recoloca los módulos y corrige las posiciones y tamaños del índice.

Un detalle si los escuchas fuera del juego: los módulos tienen apagado el indicador de estéreo, pero sus canales están repartidos a izquierda (0 a 7) y derecha (8 a 15), y **el juego los suena en estéreo**. Un reproductor que respete el indicador los oirá en mono.

Para meter una canción grabada, se puede «envolver» el audio en un S3M: guardarlo como uno o dos samples de 8 bits (uno por canal) y un patrón que los dispare. No es música de tracker de verdad, pero el juego la reproduce.

### Comentarios y ambiente: `SFX\`

| Fichero | Qué guarda |
|---|---|
| `COMPCF7\*.PKF` | Los comentarios del partido: **34 ficheros, uno por situación** (gol, penalti, falta, entrada, expulsión, córner, despeje, paradas, cambios, lesión, marcador…). El de gol tiene 178 frases |
| `COMPCF7.LST` | Un índice general, una tabla de números de 4 bytes |
| `AMBIENTE.PKF` | El público: 49 sonidos |
| `NGI022\*.PKF` | Nueve contenedores de unas 111 frases cada uno; su uso exacto está **sin confirmar** |

Todos son **WAV mono de 8 bits a 11.025 Hz** dentro de un contenedor PKF como [el de 5.0 y 6.0](v56-contenedor-pkf.html). El índice empieza en el byte 232 y está **paginado**: un bloque de índice, un grupo de sonidos, otro bloque de índice, otro grupo… Dos tipos de entrada:

- **`02`**, de 38 bytes: un sonido, con su posición en +26 y su tamaño en +30.
- **`04`**: un salto al siguiente bloque de índice, cuya posición va en +1.

Lee siempre por el índice. Buscar la firma `RIFF` parece más fácil, pero da falsos positivos dentro del propio audio.

Para meter un sonido de **otro tamaño** hay que recolocar todo lo que va detrás y corregir tres cosas en cada bloque de índice: las posiciones, los tamaños y los saltos a los bloques siguientes. Si el sonido nuevo cabe en el hueco del viejo, puedes ahorrártelo: sobrescribe y rellena con ceros, que el juego lee el tamaño real en la cabecera del WAV.

El texto que acompaña a los comentarios no está aquí: va en los `ROBIN*.DBC` de `DBDAT`.

## PC Fútbol 2000 y 2001

### El contenedor de `SFX\`

Los ficheros de `SFX\` no tienen extensión, y todos son iguales por fuera: **cuatro bytes `EF CD AB 00` y, a continuación, los sonidos pegados uno detrás de otro, sin índice**.

Cada sonido se delimita por su propio formato:

- **WAV**: el tamaño viene en su cabecera (el de la cabecera `RIFF` más 8).
- **MIDI**: va de una firma `MThd` a la siguiente.
- **MP3**: cada pista empieza con una etiqueta `ID3`. Ojo: los tres caracteres `ID3` aparecen también por azar dentro del audio. Una etiqueta real lleva detrás una versión 2, 3 o 4 y un tamaño de cuatro bytes, todos por debajo de `0x80`; si no, no es un corte.
- **DS1**: el formato de los comentarios, más abajo.

La ventaja de no tener índice: **reempaquetar es trivial**. Los cuatro bytes de cabecera y los sonidos en orden, del tamaño que quieras.

| Fichero | Qué guarda |
|---|---|
| `GUISnd` | 28 sonidos de interfaz, WAV estéreo de 16 bits a 22.050 Hz |
| `GUISpeech` | voces de la interfaz, WAV |
| `SimVoz` | 580 voces del partido, WAV mono de 8 bits a 11.025 Hz |
| `SimAmb` | 31 sonidos de ambiente |
| `SimCantic` | 110 cánticos |
| `SimFX` | efectos del partido |
| `SimComent` | **los comentarios**: casi diez mil frases en DS1. Es el más grande, entre 135 y 150 MB |
| `NGI` | 853 frases en DS1 de los ayudantes del mánager |
| `Musicas` | **3 MIDI en 2000; 2 MP3 en 2001** |

Para la música, la diferencia entre ediciones importa: **en 2000 solo puedes poner MIDI**, mientras que **en 2001 entra cualquier MP3** tal cual.

### El formato DS1

Cada frase de comentario:

| Campo | Tamaño | Qué es |
|---|---|---|
| Firma | 4 bytes | `DS1` y un salto de línea |
| Frecuencia | 2 bytes | 11.025 |
| Canales | 1 byte | 1 |
| Bits | 1 byte | 8 |
| Muestras totales | 4 bytes | |
| Tamaño de bloque | 2 bytes | 4.096 |
| Bloques | — | cada uno: 2 bytes de tamaño comprimido, 2 bytes de tamaño descomprimido y los datos comprimidos con zlib estándar |

Dos cosas que hay que saber o la frase suena mal:

1. **Lo descomprimido no son las muestras, son las diferencias** entre cada muestra y la anterior, como bytes con signo. Para obtener el audio, parte de 128 y ve sumando cada diferencia, sin bajar de 0 ni pasar de 255. Si te saltas este paso, oirás algo seco y chirriante. Para codificar, al revés: guarda la diferencia con la muestra anterior, limitada a −128…127.
2. **No busques la firma `DS1` para separar frases**: aparece también dentro de los datos comprimidos. Recorre el contenedor por longitudes: la cabecera de 14 bytes más la suma de los bloques hasta completar las muestras totales. En 2001, buscar la firma parte 15 frases por la mitad.
