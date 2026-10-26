# PCF 3.0: el manager y sus reglas

Qué decide el ejecutable del modo Liga de 3.0 y no está en la base de datos: que solo se juega la Primera División y cuántos extranjeros puedes alinear. Y por qué en esta edición no hay filiales que no puedan ascender.

> Los cambios de esta página modifican reglas de juego en el ejecutable de tu propia copia. No tocan ninguna protección anticopia y no se distribuye ningún ejecutable modificado.

## Dos programas, dos papeles

| Fichero | Qué hace |
|---|---|
| `PCFUTBOL.DAT` | El programa principal. Es el que **consulta** la base de datos: las fichas, los equipos, la historia |
| `PCMANAG.DAT` | El manager del modo Liga. Un ejecutable de DOS de 16 bits |

Los dos son ejecutables aunque la extensión diga `.DAT`. Las [reglas de oro](reglas-de-oro.html) se aplican aquí al pie de la letra: **solo se sustituyen bytes**, nunca se añaden ni se quitan, y el fichero tiene que seguir midiendo exactamente lo mismo.

## Solo se juega la Primera

Es el dato que explica casi todo lo demás de esta edición. El análisis del ejecutable lo deja claro:

- `PCMANAG.DAT` lleva el nombre `lig94951.dbc` **escrito tal cual**. No menciona `lig94952.dbc` ni una vez, y no construye el nombre del fichero con un número variable.
- Quien sí lo construye, con un patrón del tipo `lig9495%d.dbc`, es `PCFUTBOL.DAT`. Por eso los equipos de Segunda **se ven en la base de datos pero no se juegan**.
- Los modos de juego —Manager, Arcade, Entrenador, Partido, Amistoso— no incluyen una carrera de varias temporadas.

Consecuencias que conviene tener presentes:

- **No hay ascensos ni descensos.** Entre los 143 rótulos de la interfaz no aparecen ni ascenso, ni descenso, ni promoción, y la temporada acaba en el cuadro de honor.
- **No hay filiales «que no pueden subir».** En 4.0 esos equipos están señalados en el ejecutable; en 3.0 no hay nada parecido, ni en los ejecutables ni en los datos: se ha comparado la cabecera de todos los clubes de Segunda byte a byte y no hay ninguna posición que distinga a los filiales del resto. No hace falta: si no se juega la Segunda, nadie asciende.
- **Si quieres jugar con un club de Segunda, tienes que subirlo a Primera** intercambiándolo con otro. Está explicado en [el bloque de equipo](pcf3-bloque-equipo.html).

## El tope de extranjeros en el once

El juego avisa con este mensaje: *«El máximo de jugadores extranjeros titulares es 3»*. Esa regla —la de la temporada 94-95— está en `PCMANAG.DAT`, y se puede cambiar.

La comprobación tiene esta forma:

```
llamada a la rutina que cuenta los extranjeros del once
guarda el resultado
compara el resultado con 3       ← el tope
si no pasa de 3, sigue
si pasa, enseña el aviso
```

En bytes, el trozo que hay que buscar es este, donde `··` es cualquier byte y `TT` es el tope:

```
9A ·· ·· ·· ··   59   89 46 ··   3D TT 00   76
```

`9A` es la llamada a la rutina, `59` y `89 46 ··` guardan el resultado, `3D TT 00` es la comparación con el tope —un número de dos bytes, así que el `00` que le sigue es su byte alto— y `76` es el salto «si no pasa de ahí».

Aparece **en dos sitios**, uno por cada pantalla desde la que alineas. En la copia analizada, el byte del tope está en las posiciones `0xBCFC` y `0x18A2B`, y en las dos vale `03`.

Para cambiarlo:

1. **Busca el patrón**, no vayas directo a la posición. Si tu ejecutable es de otra tirada, las posiciones pueden ser otras, y la forma es lo que no cambia.
2. Comprueba que salen **los dos sitios** y que en los dos el tope vale `03`. Si sale uno solo, o salen más, para: no es lo que crees.
3. Cambia el byte `TT` **en los dos**. Si cambias uno y dejas el otro, el juego te deja alinear cuatro en una pantalla y te lo prohíbe en la otra.

Un valor entre 0 y 11 tiene sentido; por encima de 11 es lo mismo que quitar el tope, porque el once no da para más.

## Lo que no está localizado

- **El cupo de extranjeros en plantilla**, si es que existe. La forma de la comprobación que funciona en 5.0 y 6.0 solo da tres coincidencias en este manager, y las tres son otra cosa.
- **`MANAGER.DAT` y `HISTORIA.DAT`**: son ejecutables de DOS con un empaquetado propio y no se han abierto.
- **El año de la temporada.** No se ha buscado en esta edición.
