# PCF 3.0: qué hay dentro

El mapa de la carpeta de PC Fútbol 3.0, la edición de DOS de la temporada 94-95. Qué guarda cada fichero, cuál te interesa según lo que quieras cambiar y qué no se sabe todavía abrir.

> Documentación hecha por la comunidad con fines de interoperabilidad y modding. Trabaja siempre sobre tu propia copia del juego. PC Fútbol es una marca de sus titulares; este proyecto no está afiliado a ellos.

Lo primero que hay que tener claro: **3.0 no es un 5.0 antiguo**. Conserva la firma de Dinamic, pero el formato es otro y más viejo. No hay `EQUIPOS.PKF` ni contenedores PKF; nada de lo que sepas de 5.0 y 6.0 se puede aplicar a ciegas aquí. Ni siquiera el cifrado del texto es el mismo.

## Los datos: las bases `.DBC`

Todos empiezan con la firma en claro `Copyright (c)1994 DINAMIC MULTIMEDIA`. Es la forma rápida de saber que tienes un fichero de 3.0 entre manos.

| Fichero | Qué guarda |
|---|---|
| `LIG94951.DBC` | **El corazón.** Primera División: 20 clubes, cada uno con su cabecera, su entrenador y su plantilla, y detrás un equipo especial, las **Estrellas Mundiales** |
| `LIG94952.DBC` | Segunda División: 20 clubes con la misma estructura |
| `LIGA.DBC` | La clasificación final de cada Liga desde 1928-29, y al pie el palmarés |
| `COPAREY.DBC` | Las finales de Copa desde 1902, con el once del campeón, y el palmarés |
| `EUROPA.DBC` | Copa de Europa: ranking histórico de clubes y finales |
| `UEFA.DBC` | Copa de la UEFA: lo mismo, con las finales a doble partido |
| `ARBITROS.DBC` | Los colegiados: nombre, provincia, profesión y comité |
| `COMMENT.DBC` | Los comentarios de pretemporada de cada club de Primera |
| `JORNAD1.DBC` `JORNAD2.DBC` | Las actas de los partidos de cada división: árbitro, estado del campo, temperatura, hora, incidencias y declaraciones |
| `RECOPA.DBC` | Equipos de la Recopa. Sin documentar |

Entre las dos bases de Liga suman **959 jugadores**: 527 en Primera y 432 en Segunda.

Una cosa que sorprende y conviene saber pronto: **en 3.0 no hay ningún campo que diga en qué división juega un equipo**. Lo dice el fichero en el que está. Un club de `LIG94951.DBC` es de Primera porque vive ahí, y nada más. Está explicado en [el bloque de equipo](pcf3-bloque-equipo.html).

Las actas de `JORNAD1` y `JORNAD2` no nombran a ningún equipo: se refieren a ellos por su **plaza** dentro de la división. Tenlo presente si cambias el orden de los clubes.

## Los gráficos

| Fichero | Qué guarda |
|---|---|
| `LIG94951.DGF` `LIG94952.DGF` | Por cada club de la división: escudo pequeño, escudo grande, equipación de la ficha y, solo en Primera, la foto del estadio |
| `EQUIP/LIG1EQ00.DGF` … | **Uno por equipo**: las caras de sus jugadores, en pequeño y en grande. El número del nombre es la plaza del equipo en su división |
| `1.EMP` … `20.EMP` | El escudo que sale **en el partido**, uno por club de Primera, en el orden de la división |
| Los demás `.EMP` | Las animaciones del simulador: correr, chutar, el balón… |
| `GFX00.DAT` | Iconos, botones y rótulos del manager |
| `PCFTEX.DAT` | Los gráficos del arranque y del actualizador por módem |
| `FONDOS.EMF` `FONDOS1.EMF` | Fondos de pantalla montados por baldosas. Sin documentar |
| `PALETA.BBM` `PAL1.BBM` … `PAL5.BBM` | Paletas de color en formato de Deluxe Paint |

Cuidado con la extensión: aquí es **`.DGF`**. En 4.0 el fichero equivalente se llama `.DFG`, con las letras cambiadas. Es el mismo tipo de contenedor, pero si buscas uno con el nombre del otro no lo vas a encontrar.

Todo esto está en [gráficos y sonido](pcf3-graficos.html).

## La interfaz y el sonido

| Fichero | Qué guarda |
|---|---|
| `PCFRES00.GRC` | Los 143 rótulos de la interfaz: `PALMARES`, `LA PLANTILLA`, `LUGAR DE NACIMIENTO`… |
| `V08*.VOC` `V11*.VOC` | Los once sonidos del juego, **en la raíz** de la carpeta y no en una subcarpeta |

## Los ejecutables

| Fichero | Qué es |
|---|---|
| `PCFUTBOL.DAT` | El programa principal: la base de datos que consultas |
| `PCMANAG.DAT` | El manager del modo Liga |
| `MANAGER.DAT` `HISTORIA.DAT` | Ejecutables de DOS con un empaquetado propio. Sin documentar |

Hay un dato de los ejecutables que lo cambia todo: **el manager de 3.0 solo juega la Primera División**. Los equipos de Segunda están en la base y los ves en sus fichas, pero no hay forma de jugar con ellos. Por eso en esta edición no hay ascensos, ni descensos, ni filiales que no puedan subir. Lo explica [la página del manager](pcf3-manager.html).

## Por dónde empezar

- **Antes de nada** → [el texto](pcf3-texto.html): sin el cifrado no verás ni un nombre.
- **Cambiar un club: nombre, estadio, aforo, equipación** → [el bloque de equipo](pcf3-bloque-equipo.html).
- **Cambiar jugadores, medias o el once** → [la ficha del jugador](pcf3-ficha-jugador.html).
- **Cambiar la historia de la Liga, la Copa o Europa** → [las tablas de competición](pcf3-competiciones.html).
- **Cambiar escudos, caras o sonidos** → [gráficos y sonido](pcf3-graficos.html).
- **Cambiar el tope de extranjeros** → [el manager](pcf3-manager.html).

Y las [reglas de oro](reglas-de-oro.html) valen aquí igual que en las demás ediciones, con un matiz importante: en las bases de Liga de 3.0 **sí se puede alargar un texto**. Por qué, y dónde no, está en la página del texto.
