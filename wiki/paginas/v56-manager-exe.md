# El ejecutable: lo que no está en la base de datos

Aquí está la respuesta a la pregunta que más se repite: *«he añadido equipos a la base y no salen en la liga»*. No salen porque **la composición de las competiciones no vive en los datos, vive en el programa**.

> Los cambios de esta página modifican reglas de juego en el ejecutable de tu propia copia. No tocan ninguna protección anticopia y no se distribuye ningún ejecutable modificado.

Es un cambio de mentalidad importante. La base de datos dice **qué equipos existen y cómo son**. El ejecutable dice **qué se juega, quién lo juega y con cuántos**.

## La regla que no se puede saltar

Antes de nada: **el tamaño del ejecutable no puede cambiar. Ni un byte.**

En un fichero de datos, desplazar cosas rompe la lectura. En un programa, desplazar cosas rompe el programa entero: todos los saltos internos apuntan a direcciones concretas, y si se mueven, deja de arrancar.

Así que aquí solo se hace una cosa: **sustituir un valor por otro del mismo tamaño**. Nunca añadir, nunca quitar.

Y una consecuencia práctica: **los sitios donde está cada cosa dependen de la compilación exacta**. Dos ediciones distintas del mismo juego tienen sus tablas en posiciones diferentes. Una lista de posiciones sacada de otra edición no vale, y aplicarla a ciegas destroza el ejecutable. Lo primero es siempre comprobar el tamaño del fichero.

## Qué se puede cambiar

### Las divisiones

Cuántas hay, cuántos equipos tiene cada una y qué club ocupa cada plaza. Las plazas son tablas de identificadores de equipo, uno detrás de otro.

**El número de plazas es fijo.** Puedes cambiar quién ocupa cada una, pero no cuántas hay: eso está entretejido con el código que gestiona la competición. Es la limitación que más gente encuentra, y no tiene vuelta.

Los equipos que existen en la base pero no tienen plaza no desaparecen: salen en la base de datos y se pueden usar para amistosos, simplemente no compiten.

### Las competiciones europeas

Qué clubes juegan la Copa de Europa, la UEFA, la Recopa y las supercopas. Igual que las divisiones: listas de identificadores con un número fijo de puestos.

Un aviso: en algunas ediciones, **el equipo español de una competición está guardado dos veces** — suelto por un lado y dentro de la lista por otro. Cambiar solo uno deja el juego diciendo dos cosas distintas.

Y en otras ediciones estas listas **no son tablas de datos sino instrucciones del programa**, con cada equipo escrito dentro de su propia instrucción. Se distinguen porque los valores no van seguidos: entre uno y el siguiente hay una decena de bytes. Si buscas una lista compacta y no la encuentras, prueba a mirar así.

### El año de la temporada

El rótulo de la temporada. Parece trivial y tiene su miga: el año aparece en muchos sitios del programa y **algunos de esos bytes no son el año sino parte de una instrucción**. Cambiarlos a bulto cuelga el juego.

Además, pasar de 1999 tiene un efecto secundario propio: estos juegos son de los noventa y hay sitios donde el año se guarda con dos cifras.

### Los límites del juego

Cosas como cuántos extranjeros puedes alinear o qué fichajes te deja hacer. Son **funciones minúsculas que devuelven un número**: el programa pregunta «cuál es el máximo» y una rutina de tres líneas responde. Se cambia ese número y ya.

Otras reglas no son un número sino una comprobación: el programa mira algo y decide. Ahí se neutraliza el salto.

### Cómo se neutraliza un salto

Esto es lo más útil de todo el capítulo, porque **no depende de la compilación**. Cuando el programa comprueba algo y salta si no se cumple, el salto es un byte concreto:

| Byte | Qué hace | Cómo se anula |
|---|---|---|
| `74` | Salta **si se cumple** | Cámbialo por `EB`, que salta **siempre** |
| `75` | Salta **si NO se cumple** | Cámbialo por `EB` |
| `0F 84` | Igual que `74` pero salto largo, ocupa 6 bytes | Sustituye los **seis** por `90`, que no hace nada |

El `EB` y el `74` ocupan lo mismo, así que el fichero no cambia de tamaño. Y el `90` es la instrucción que no hace nada: sirve para tapar lo que sobre.

### La técnica que mejor funciona: buscar el AVISO

Esta es la más útil de todas y la más fácil de aplicar sin saber ensamblador.

**Cada regla del juego lleva su mensaje de error al lado.** Los mensajes están en texto plano dentro del ejecutable, así que se buscan con cualquier editor. Y donde está el mensaje está, a un par de instrucciones, la constante que lo gobierna.

Estos son reales, sacados de los ejecutables:

| Mensaje | Qué regla gobierna |
|---|---|
| «Ya tienes en tu plantilla a seis extracomunitarios, que es el número máximo.» | tope de fichar |
| «Ya has alineado cuatro extracomunitarios, que es el número máximo.» | tope de alinear |
| «La directiva sólo te deja hacer %u ofertas…» | ofertas por semana |

El procedimiento: **busca la frase, mira qué código la usa, y la constante está cerca**. Funciona en cualquier compilación porque el texto no cambia de sitio con la versión — es el mismo mensaje.

### Cuidado: hay mensajes que ya no se usan

Y aquí un aviso que vale por todo el capítulo, porque es fácil caer.

En el ejecutable de 5.0 Oro **hay cuatro mensajes sobre extracomunitarios, no dos**, y se contradicen entre sí:

```
«No se permite contratar más de 3 jugadores extracomunitarios.»
«No se permite alinear a más de 3 jugadores extracomunitarios.»
«Ya tienes en tu plantilla a seis extracomunitarios, que es el número máximo.»
«Ya has alineado cuatro extracomunitarios, que es el número máximo.»
```

Los dos primeros hablan de tres y los otros dos de seis y cuatro. **Son restos de una versión anterior**: la constante que el juego usa de verdad vale **seis** para fichar y **cuatro** para alinear, igual que en 6.0 Oro.

O sea que el primer mensaje que encuentras buscando **puede no ser el que manda**. La regla es sencilla: **el mensaje te lleva al sitio, pero quien decide es la constante**. Compruébala antes de dar por bueno un número, y si hay varios candidatos, quédate con el que coincida con lo que el juego hace de verdad al jugar.

> En 5.0 y 6.0 los topes de extracomunitarios son además **funciones diminutas** que solo devuelven un número. Si junto al mensaje no ves ninguna constante, mírala en la función vecina: van enlazadas la una al lado de la otra.

### Y el aviso que ahorra un fallo desconcertante

**El mismo tope suele estar escrito en varios sitios.** El juego lo comprueba más de una vez —al pedir algo y al confirmarlo— y además **escribe el número en el mensaje**.

Si cambias solo uno, el resultado es de los que vuelven loco a cualquiera: el aviso dice un número nuevo pero el juego sigue aplicando el viejo, o al revés. Hay que cambiarlos todos.

### Buscar por patrón en vez de por posición

Y aquí la técnica que hace todo esto portable entre ediciones. En vez de anotar «en la posición tal», se busca **la secuencia de bytes alrededor de la comprobación** y se sustituye ahí.

Por ejemplo, el límite de años de nacimiento: el programa comprueba que el año esté **entre 1900 y 2000**. En el fichero eso aparece como los dos años seguidos —`6C 07` y `D0 07`— con la instrucción de comparación en medio. Buscando esa secuencia completa y subiendo el tope a `FF FF`, se admiten jugadores nacidos después de 1999 **en cualquier compilación**, sin saber en qué posición está.

La ventaja es enorme: un patrón de diez o doce bytes es único en el fichero, mientras que una posición solo vale para una compilación concreta.

> **Y el error que se comete al hacerlo mal.** Si en vez de buscar el patrón completo buscas solo el año —`CD 07` para 1997, por ejemplo— y lo sustituyes en todo el fichero, machacas cientos de sitios que no son el año: en una edición aparece **más de setecientas veces**, y la mayoría son partes de instrucciones. El juego deja de arrancar. El año hay que cambiarlo **con su contexto**, nunca a ciegas.

## Cómo localizar una tabla sin una lista de posiciones

Esto es lo más útil de todo el capítulo, porque **sirve para cualquier edición**, incluidas las que nadie ha documentado nunca.

### Lo que NO funciona

Buscar el identificador de un equipo conocido. Probado: el del Barcelona aparece **25.867 veces** en el ejecutable, porque es el número 1 y ese valor está por todas partes. Ni siquiera exigiendo que haya un Real Madrid cerca sirve — quedan más de cinco mil sitios.

### Lo que sí funciona

**Buscar rachas.** Una tabla de participantes es una tira de identificadores de equipo seguidos, todos válidos y ninguno repetido. Eso casi no ocurre por azar.

El procedimiento:

1. Recorre el fichero **leyendo dos bytes cada vez**, como una lista de números.
2. Cuenta cuántos seguidos son **identificadores de equipo que existen** y **no se repiten** entre sí.
3. Quédate con las rachas de dieciocho o más.

Sobre el ejecutable de 5.0 eso deja **veintiuna rachas**, una lista que se revisa a mano en cinco minutos. Y se reconocen solas al traducir los números a nombres:

- Una empieza por Atlético de Madrid, Valencia, Barcelona, Espanyol, Tenerife, Real Madrid… que es la Primera del 96/97 **en el orden en que quedaron el año anterior**.
- Otra da equipos ingleses de tercera y cuarta.
- Otra, clubes alemanes y austriacos seguidos: los participantes europeos agrupados por país.

Cuando una racha te devuelve una competición reconocible, **has encontrado esa tabla**. No hay ambigüedad posible.

### Antes de escribir

Siempre: leer los bytes que hay, comprobar que son lo que esperas, y solo entonces cambiarlos. Y no cambiar cuántos hay — solo quién ocupa cada sitio.

## Las posiciones concretas

Todo lo anterior explica el método. Si tu ejecutable es uno de los tres que están mapeados, **no hace falta que busques nada**: las posiciones exactas de cada tabla están en [posiciones concretas](v56-manager-offsets.html) — participantes de cada competición, plazas españolas de las copas europeas y límites del juego, con su valor de fábrica.

## Cómo saber en qué edición estás

Por el **tamaño exacto del fichero**. Es lo que distingue una compilación de otra sin lugar a dudas, y es la primera comprobación que hace cualquier herramienta seria antes de tocar nada.

| Tamaño en bytes | Qué es | ¿Mapeado? |
|---|---|---|
| 2.461.184 | Manager base de 5.0 y 6.0 (96/97) | Sí |
| 2.507.264 | 5.0 base | Parcial |
| 2.617.344 | 6.0 base | No |
| 2.630.144 | 6.0, primera extensión (97/98) | Sí |
| 2.662.400 | 6.0 Edición de Oro (97/98) | Sí |

Los tres marcados como mapeados tienen sus posiciones publicadas. Para los otros hay que usar el método de las rachas.

Y conviene insistir: **las posiciones de uno no sirven para otro**. No es que fallen un poco — apuntan a sitios completamente distintos del programa, y escribir ahí lo destroza sin remedio.
