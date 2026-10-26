# La paleta: por qué todo sale negro

La pieza que falta en casi todos los intentos de abrir estas imágenes. Si has extraído un escudo y lo has visto **completamente negro**, no está corrupto: le falta la paleta.

## Cómo funciona una imagen de 256 colores

Estas imágenes no guardan colores, guardan **números**. Cada píxel es un byte de 0 a 255, y ese número es una **posición en una tabla de colores** — la paleta. El byte 37 no significa «este píxel es rojo»: significa «este píxel usa el color que ocupe la posición 37 de la tabla».

Normalmente esa tabla viaja dentro del propio fichero de imagen. Aquí **no**: las imágenes del juego traen la tabla **a ceros**, las 256 posiciones en negro, y la de verdad la pone el juego desde fuera.

De ahí que al extraer una y abrirla salga negra sobre negro. Los píxeles están perfectamente; lo que falta es con qué colorearlos.

## La paleta

Es **la misma para los escudos y para las fotos** de jugador. Son 256 colores en el orden en que van en la tabla, uno por índice, en formato hexadecimal `RRGGBB`:

```
  0  000000 800000 008000 808000 000080 800080 008080 C0C0C0
  8  C0E3C0 A6CAF0 2A3FAA 2A5FAA 1E3462 3B5582 4B6DAC 7593BB
 16  2AFFAA 2A00AA 8EA5C4 551FAA 7F1FAA AA1FAA 000032 D400AA
 24  FF00AA 5500AA 2A0055 001E00 003F00 005F00 DCFAD2 009F00
 32  00BF00 00DF00 00FF00 2A0000 550000 960000 AA0000 D20000
 40  E1D2EB D43F00 D45F00 D47F00 D49F00 D4BF00 D4DF00 D4FF00
 48  B56909 841A1A 6C1515 DCAC79 553F00 555F00 3C3C64 505078
 56  64648C 7878A0 8C8CB4 A0A0C8 A42020 AA1F55 AA0055 D40055
 64  FF0055 2A1F55 2A3F55 2E4552 2A5F55 2A7F55 2A9F55 2ABF55
 72  2ADF55 2AFF55 550055 7F0055 7F1F55 7F3F55 7F5F55 7F7F55
 80  7F9F55 7FBF55 7FDF55 7FFF55 551F55 64820A 789614 8CAA1E
 88  A0BE28 B4D232 C8E63C DCFA46 3C5064 506478 64788C 788CA0
 96  8CA0B4 A0B4C8 B4C8DC C8DCF0 2C2C2C 7F00AA 7F3FAA 7F5FAA
104  5C7EAE 559FAA 55BFAA 55DFAA 55FFAA 0000A0 5500FF 0A0F00
112  141E00 1E3200 324600 3C5A00 506E05 AA3F00 FF1F00 115A22
120  117F2B 279F3B 3DBF52 46DF6C 53FF82 481E02 66320C 874916
128  505050 00FFAA 0000DC 646464 0000BE AA9F00 909090 161616
136  14283C 283C50 D41F55 FF1F55 555FAA 007FAA 009FAA 00BFAA
144  00DFAA 00DFFF AADF55 FFDF00 AABF55 AA9F55 AA7F55 AA5F55
152  AA3F55 D45F55 D47F55 D49F55 D4BF55 D4DF55 D4FF55 FF3F55
160  2A1FFF 2A3FFF 2A5FFF 2A7FFF 2A9FFF 2ABFFF 2ADFFF 14005A
168  B97B45 7F00FF AA00FF D400FF AA1FFF 7F1FFF 7F3FFF 7F5FFF
176  7F7FFF 7F9FFF 7FBFFF 7FDFFF 7FFFFF 553FFF 555FFF 557FFF
184  559FFF 55BFFF 55DFFF 55FFFF 8C6E96 A082AA B496BE C8AAD2
192  D7BEDC CCCCFF D4DFFF D4FFFF 640000 F0F0F0 FFDFFF FFCCFF
200  FFBFFF FF9FFF FF7FFF AA7FFF AA5FFF AA9FFF AABFFF 727272
208  DCDCDC D4DFAA D4BFAA D49FAA D47FAA D45FAA AA5FAA AA7FAA
216  C97802 AABFAA AADFAA AAFFAA D4FFAA FFFFAA FFDFAA FFBFAA
224  FF9FAA FF7FAA FF5FAA FF5F55 FF7F55 FF9F55 FFBF55 FFDF55
232  FFFF55 3D0000 A05A02 14143C 282850 B4B4DC C8C8F0 AA7F00
240  AADFFF 280A32 462850 6E5078 009FFF 007FFF FFFBF0 A0A0A4
248  808080 FF0000 00FF00 FFFF00 0000FF FF00FF 00FFFF FFFFFF
```

## Dos detalles que hay que conocer

**El índice 0 es el transparente.** Es negro en la tabla, pero el juego no lo pinta: deja ver lo que hay detrás. Por eso el fondo de los escudos es ese índice y no otro negro cualquiera.

Y por eso mismo hay que tener cuidado al preparar una imagen nueva: **si el dibujo lleva negro de verdad y cae en el índice 0, esa parte se volverá transparente**. Si tu escudo tiene contorno negro y en el juego se ve agujereado, es esto.

### El negro que usaba Dinamic: el índice 135

No hay que inventarse cuál usar, porque el juego original ya resolvió esto. **Dinamic reservó el índice 0 para el fondo y pintó el negro del dibujo con el índice 135**, que es un casi-negro (22, 22, 22) indistinguible a simple vista.

Está comprobado sobre los escudos originales: **las cuatro esquinas de todos son el índice 0**, y el negro de los dibujos es el 135 — en el escudo del Barakaldo, sus rayas negras son 9.676 píxeles del índice 135.

Así que la regla al convertir es sencilla: **el fondo al 0, y cualquier negro del dibujo al 135**. Si dejas que el conversor elija por su cuenta, mandará los negros al 0 porque es el más parecido, y el escudo saldrá agujereado.

### Y no estires la imagen

Otra convención del original que conviene respetar: **Dinamic no deformaba los escudos**. Los escalaba conservando su proporción y los centraba en el lienzo, dejando los márgenes que hicieran falta.

Se ve en los originales: el del Zaragoza, estrecho y alto, ocupa 30 píxeles de ancho en un lienzo de 48, con 8 y 10 de margen a los lados. Otros llenan el ancho y dejan margen arriba y abajo.

Si estiras hasta el tamaño exacto, los escudos estrechos salen ensanchados y los anchos achatados. Es de esas cosas que no rompen nada pero cantan mucho.

**Los dieciséis primeros colores** son los clásicos de las tarjetas gráficas de la época. A partir de ahí la paleta es propia del juego, con rampas de tonos pensadas para el césped, las pieles y las camisetas.

## Cómo convertir una imagen tuya

El proceso, paso a paso:

1. **Escala la imagen** al tamaño exacto que toque. Cada tipo tiene el suyo y no admite otro.
2. **Reduce a esos 256 colores**, sustituyendo cada píxel por el índice del color más parecido de la tabla. Cualquier biblioteca de imagen sabe hacerlo si le das la paleta.
3. Decide si quieres **difuminado**. Repartir el error entre píxeles vecinos disimula las bandas en fotos y degradados; en escudos, que son planos y pequeños, suele quedar peor.
4. **Pon el fondo al índice 0** si quieres transparencia.
5. Guarda el mapa de bits **con la tabla de colores a ceros**, como hacen los originales, o déjala puesta: el juego la ignora de todos modos.

## Las paletas de las pantallas son otra cosa

Aviso importante para no perder una tarde: **la paleta de arriba vale para los escudos, las fotos, las banderas y las camisetas**. Los gráficos de las pantallas del menú **no la usan**.

Esos tienen sus propias paletas, varias, guardadas en un contenedor aparte: una para el menú, otra para el manager, otra para la base de datos, otras para el simulador. Una imagen preparada con la paleta de los escudos y puesta en una pantalla saldrá con los colores cambiados de forma radical.
