# La táctica en 7, 2000 y 2001

Cada equipo lleva una pizarra de 1.760 bytes con la posición de sus once jugadores en 40 situaciones distintas, y siete bytes de estilo de juego. Es la misma idea que en 5.0 y 6.0, con diez veces más detalle.

## La pizarra: 1.760 bytes

Son **11 jugadores × 40 zonas × 2 coordenadas**, cada coordenada de dos bytes. Sin cabecera, sin separadores:

```
posición del jugador j en la zona z = (j × 40 + z) × 4
    +0  x  (2 bytes)
    +2  y  (2 bytes)
```

con `j` de 0 a 10 y `z` de 0 a 39.

En 5.0 y 6.0 la misma estructura tenía 4 zonas por jugador (176 bytes). Aquí cada jugador sabe dónde colocarse **según dónde esté el balón y según quién lo tenga**.

### Los jugadores

El jugador `0` es el **portero**, y los once van en el mismo orden que los once primeros puestos de la plantilla (el byte de posición de cada ficha). Por eso cambiar quién es titular no exige tocar la pizarra: el que ocupa el puesto se coloca donde diga su fila.

Una comprobación fácil: el jugador `0` no sale de su área en ninguna de las zonas, en ninguno de los equipos de la base.

### Las coordenadas

- **`x` es el avance**: `0` es tu portería y el máximo es la portería rival. El portero ronda el 40.
- **`y` es la banda**: valores bajos a la **izquierda**, altos a la **derecha**.

El terreno mide, en estas unidades, unos **420 × 252** en PC Fútbol 7 y 2000, y **480 × 288** en 2001. La proporción es la misma —la de un campo real—; lo que cambia es la escala. Si dibujas la pizarra, usa la escala de cada edición o los jugadores te saldrán encogidos o fuera del campo.

### Las cuarenta zonas

Cada zona es una **situación del balón** combinada con **quién lo tiene**:

```
z = situación × 2 + estado        estado: 0 = con balón · 1 = sin balón
```

O sea, las zonas pares son tu equipo atacando y las impares, defendiendo. La diferencia se ve en los datos: con el balón, el equipo está de media 86 unidades más adelantado, en todas las tácticas de la base.

Las **20 situaciones** dividen el campo en **cuatro carriles** de izquierda a derecha, y cada carril en **pasos de avance**: cuatro en los carriles exteriores y seis en los dos centrales.

| Carril | Pasos | Situaciones |
|---|---|---|
| 0 (izquierda) | 4 | 0 a 3 |
| 1 (centro izquierda) | 6 | 4 a 9 |
| 2 (centro derecha) | 6 | 10 a 15 |
| 3 (derecha) | 4 | 16 a 19 |

Un ejemplo: el balón en el carril 1, en su primer paso, con tu equipo atacando, es la situación 4 y la zona `4 × 2 + 0 = 8`.

La división por carriles se confirma con la simetría del propio campo: los dos carriles exteriores dan cifras casi idénticas entre sí, y los dos interiores también. Una lectura en filas y columnas, que es lo primero que se le ocurre a cualquiera, no encaja en ninguno de los equipos.

### Mover a un jugador

La posición «natural» de un jugador, la que dibujarías como formación, es **la media de sus cuarenta zonas**. Para moverlo sin deformar su comportamiento:

1. Calcula su media en las zonas que quieras tocar: las cuarenta, solo las veinte de ataque o solo las veinte de defensa.
2. Suma la misma diferencia a cada una de esas zonas.

Así conserva cómo se desplaza con el balón y solo cambia su sitio de referencia. Recuerda que son números de dos bytes sin signo: no bajes de 0.

### Compartir pizarras

La pizarra es **intercambiable entre equipos**: copiar los 1.760 bytes de un club a otro le da exactamente la misma táctica. En PC Fútbol 7, 797 de los 876 equipos de la temporada 98 llevan la misma pizarra de fábrica.

## El estilo de juego: 7 bytes

Detrás de la pizarra, idénticos a los de 5.0 y 6.0:

| Byte | Campo | Valores |
|---|---|---|
| 0 | Toque | porcentaje |
| 1 | Contragolpe | porcentaje |
| 2 | Ataque | 0 a 2 |
| 3 | Entradas | 0 a 2 |
| 4 | Marcaje | 0 a 1 |
| 5 | Despejes | 0 a 1 |
| 6 | Presión | 0 a 2 |

El valor neutro, el que llevan muchos equipos, es `50 50 1 0 0 0 0`.

## Las tácticas predefinidas

PC Fútbol 7 trae diez en `DBDAT\TACTICS\PREDEF.001` a `.010`, de 1.848 bytes cada una. Su contenido no se describe aquí.
