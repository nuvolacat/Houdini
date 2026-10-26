# Tablas de códigos

Las correspondencias que hacen falta para interpretar los bytes. Sin esto, una ficha de jugador es una fila de números sin significado.

## Demarcaciones

Cada jugador guarda seis, y son las posiciones en las que puede jugar. La primera es obligatoria; las otras cinco son alternativas y pueden ir vacías.

Casi nadie las llena todas. Recorriendo las ocho bases, de los 77.942 jugadores con demarcación: **la mitad lleva una sola** (38.980), un tercio lleva dos (23.995), y solo 234 llevan las seis.

| Código | Demarcación |
|---|---|
| 0 | *(vacío)* |
| 1 | Portero |
| 2 | Lateral derecho |
| 3 | Lateral izquierdo |
| 4 | Líbero |
| 5 | Central izquierdo |
| 6 | Central derecho |
| 7 | Centrocampista derecha |
| 8 | Interior derecho |
| 9 | Delantero centro |
| 10 | Medio centro organizador |
| 11 | Centrocampista izquierda |
| 12 | Extremo derecho |
| 13 | Media punta por el centro |
| 14 | Extremo izquierdo |
| 15 | Medio centro defensivo |
| 16 | Media punta derecha |
| 17 | Media punta izquierda |
| 18 | Interior izquierdo |

Los dieciocho códigos aparecen en los ficheros — no hay ninguno sin usar. El más repetido como demarcación principal es el `9`, delantero centro (11.200 jugadores).

No confundir la demarcación con el **puesto**, que es otro byte distinto y solo tiene cuatro valores: `0` portero, `1` defensa, `2` medio, `3` delantero. El puesto es el que agrupa al jugador en los listados; la demarcación es dónde juega exactamente.

### Cómo comprobar que has leído bien las dos

Estas dos tablas se pueden verificar **la una contra la otra**, y es la prueba que recomiendo hacer nada más escribir tu lector, porque no necesita el juego: si tu demarcación y tu puesto son correctos, **el portero tiene que ser portero en las dos**.

Al cruzarlas sobre las ocho bases sale esto:

- De los jugadores con demarcación `1`, el **99,77 %** tiene puesto `0`.
- De los que tienen puesto `0`, el **99,48 %** tiene demarcación `1`.

Dos campos que se leen de sitios distintos de la ficha y coinciden en ese porcentaje no coinciden por casualidad. Y el medio por ciento que sobra no es una excepción del juego: son los mismos bloques mal leídos de los que habla el apartado del final de esta página. Si a ti te sale bastante por debajo de ese 99 %, tu lector se está descolocando en algún sitio.

## Aspecto

| Tono de piel del avatar | | | Pelo | |
|---|---|---|---|---|
| 1 | Tono 1 (claro) | | 1 | Rubio |
| 2 | Tono 2 (oscuro) | | 2 | Sin pelo |
| 3 | Tono 3 (intermedio) | | 3 | Moreno |
| | | | 4 | Canoso |
| | | | 5 | Pelirrojo |
| | | | 6 | Castaño |

## Situación en el club

| Código | Significado | Cuántos hay |
|---|---|---|
| 0 | Seguía en el equipo | 65.528 |
| 1 | Fichaje | 15.110 |
| 2 | Cantera | 1.958 |
| 3 | **Baja en el equipo** | 481 |
| 4 | *sin confirmar* | 56 |

Los recuentos son de las ocho bases del juego, sumadas.

El valor 3 es el que el juego rotula «baja en el equipo»: el jugador sigue en la base de datos del club pero no cuenta para la plantilla. Va casi siempre acompañado de la posición 99 en el orden de la plantilla.

**Y hay un quinto valor.** El `4` aparece en 56 jugadores y **solo en la edición argentina de 6.0**. Qué significa **sigue sin confirmarse**, pero se ha avanzado lo suficiente como para ahorrarle trabajo al siguiente.

**Lo primero: no son fichas corruptas.** Es la duda razonable —un valor raro suele ser un lector descolocado— y se descarta midiendo. De esas 56 fichas, **48 tienen todos los demás campos dentro de rango**: piel, pelo, puesto, demarcaciones, estatura. Eso es un 86 %, cuando en la base entera solo lo cumple el 56 %. Son **más limpias que la media**, así que el valor está puesto a propósito.

**Y dos explicaciones que parecían buenas no se sostienen.** Las dejo escritas porque son las dos primeras que se le ocurren a cualquiera:

| Hipótesis | Qué predice | Qué sale |
|---|---|---|
| Vuelve de una cesión | Su ficha estaría también en el club que lo cedió | Solo **2 de 56** aparecen en otro equipo |
| Es extranjero o extracomunitario | Serían de otro país que su club | **31 de 56 son del mismo país**, y 25 son de la Unión Europea |

Lo que sí se sabe de los 56: están repartidos por **37 clubes de once países** —España, Italia, Argentina, Portugal, Inglaterra, Bélgica…— y ocupan puestos de plantilla de lo más normal, sin concentrarse ni en el once ni en la cola.

O sea que no es una marca de una liga concreta ni de un tipo de jugador evidente. Si alguien lo comprueba dentro del juego, se agradece.

## Sobre los valores que no encajan en estas tablas

Al recorrer las ocho bases aparecen, muy de vez en cuando, valores fuera de rango: una piel 116, un puesto 109, una demarcación 195. Son **uno o dos casos entre decenas de miles**: en las demarcaciones, los valores por encima de 18 salen **70 veces sobre 468.000 leídas**, un 0,015 %.

No son valores del juego: son **síntoma de que tu lector se ha descolocado** en ese bloque. Es la mejor prueba de cordura que puedes montar — si al recorrer un fichero te salen pieles fuera de 1 a 3 o puestos fuera de 0 a 3, no busques el significado exótico: revisa por dónde te has perdido.

## Divisiones

Aparece en el historial de las últimas diez ligas.

| Código | División |
|---|---|
| 0 | Primera |
| 1 | Segunda |
| 2 | Segunda B |
| 3 | Tercera |

## Países

El código que llevan el jugador (su nacionalidad), el equipo y el país de nacimiento. Son los mismos números en todas las versiones.

Son **206, numerados del 1 al 206 sin ningún hueco**. La lista es el mundo entero, no los países que salen en el juego: al recorrer las ocho bases, **80 de los 206 no aparecen ni una sola vez** —Nepal, Tonga, Vanuatu, San Marino…— y **solo 60 llegan a tener equipo**. Los demás existen para que un jugador pueda ser de donde sea aunque su país no tenga liga en el juego.

Dicho de otra forma: que un código no aparezca en tu fichero **no significa que esté mal**. Estaba previsto y nunca se usó.

Un aviso pequeño: el `0` no está en la tabla, pero aparece **una vez** en toda la base de datos, en un jugador de la edición argentina de 5.0. Trátalo como «sin país», no como un error de lectura.

| # | País | # | País | # | País | # | País |
|---|---|---|---|---|---|---|---|
| 1 | Albania | 53 | Suecia | 105 | Gambia | 157 | Indonesia |
| 2 | Alemania | 54 | Suiza | 106 | Ruanda | 158 | Irak |
| 3 | Argentina | 55 | Turquía | 107 | Kenia | 159 | Jordania |
| 4 | Australia | 56 | Ucrania | 108 | Mauritania | 160 | Kazakhstan |
| 5 | Austria | 57 | Uruguay | 109 | Mali | 161 | Kiribati |
| 6 | Azerbaiyán | 58 | Yugoslavia | 110 | Uganda | 162 | Kuwait |
| 7 | Bielorusia | 59 | Perú | 111 | República del Congo | 163 | Kirguizistán |
| 8 | Bolivia | 60 | Canadá | 112 | Letonia | 164 | Laos |
| 9 | Bosnia | 61 | USA | 113 | Costa de Marfil | 165 | Ciudad Vaticano |
| 10 | Brasil | 62 | Georgia | 114 | Armenia | 166 | Líbano |
| 11 | Bulgaria | 63 | Costa Rica | 115 | Nicaragua | 167 | Lesotho |
| 12 | Bélgica | 64 | Paraguay | 116 | Cataluña | 168 | Malawi |
| 13 | Camerún | 65 | Japón | 117 | Níger | 169 | Malasia |
| 14 | Chile | 66 | Argelia | 118 | Barbados | 170 | Maldivas |
| 15 | Chipre | 67 | Trinidad y Tobago | 119 | Irán | 171 | Islas Marshall |
| 16 | Colombia | 68 | Senegal | 120 | Qatar | 172 | Mónaco |
| 17 | Croacia | 69 | Surinam | 121 | Túnez | 173 | Mongolia |
| 18 | Dinamarca | 70 | Zambia | 122 | Gabón | 174 | Myanmar |
| 19 | Escocia | 71 | Cabo Verde | 123 | Tahití | 175 | Namibia |
| 20 | Eslovaquia | 72 | Venezuela | 124 | Islas Mauricio | 176 | Nauru |
| 21 | Eslovenia | 73 | Rodesia | 125 | Madagascar | 177 | Nepal |
| 22 | España | 74 | Singapur | 126 | Martinica | 178 | Corea Del Norte |
| 23 | Finlandia | 75 | Andorra | 127 | Vietnam | 179 | Omán |
| 24 | Francia | 76 | Mozambique | 128 | Haití | 180 | Pakistán |
| 25 | Ghana | 77 | Liechtenstein | 129 | Antigua y Barbuda | 181 | Palau |
| 26 | Grecia | 78 | Liberia | 130 | Bahrein | 182 | Papua Nueva Guinea |
| 27 | Holanda | 79 | Panamá | 131 | Bangladesh | 183 | Filipinas |
| 28 | Honduras | 80 | Rep. Dem. del Congo | 132 | Belize | 184 | Saint Kitts and Nevis |
| 29 | Hungría | 81 | Tayikistán | 133 | Benin | 185 | Santa Lucia |
| 30 | Inglaterra | 82 | Uzbekistán | 134 | Bhutan | 186 | Samoa |
| 31 | Irlanda | 83 | México | 135 | Botswana | 187 | San Marino |
| 32 | Irlanda del Norte | 84 | Guinea | 136 | Brunei | 188 | Santo Tome y Príncipe |
| 33 | Islandia | 85 | Angola | 137 | Burundi | 189 | Arabia Saudí |
| 34 | Islas Feroe | 86 | Zimbabwe | 138 | Camboya | 190 | Seychelles |
| 35 | Israel | 87 | Sierra Leona | 139 | Republica Centro | 191 | Islas Salomón |
| 36 | Italia | 88 | Guadalupe | 140 | China | 192 | Somalia |
| 37 | Lituania | 89 | Ecuador | 141 | Comoros | 193 | Corea Del Sur |
| 38 | Luxemburgo | 90 | Estonia | 142 | Yemen | 194 | Sri Lanka |
| 39 | Macedonia | 91 | Guinea Bissau | 143 | Cuba | 195 | Sudan |
| 40 | Malta | 92 | Libia | 144 | Yibuti | 196 | Suazilandia |
| 41 | Marruecos | 93 | Egipto | 145 | Dominica | 197 | Siria |
| 42 | Moldavia | 94 | Jamaica | 146 | Republica Dominicana | 198 | Taiwán |
| 43 | Nigeria | 95 | Nueva Caledonia | 147 | El Salvador | 199 | Tailandia |
| 44 | Noruega | 96 | Bermudas | 148 | Guinea Ecuatoriana | 200 | Bahamas |
| 45 | País de Gales | 97 | Nueva Zelanda | 149 | Eritrea | 201 | Tonga |
| 46 | Polonia | 98 | Guayana Francesa | 150 | Etiopia | 202 | Turkmenistan |
| 47 | Portugal | 99 | San Vicente | 151 | E.F. de Micronesia | 203 | Tuvalu |
| 48 | Rep. Checa | 100 | Chad | 152 | Fiji | 204 | Emiratos Árabes |
| 49 | Rumania | 101 | Togo | 153 | Granada | 205 | Reino Unido |
| 50 | Rusia | 102 | Guinea Conakry | 154 | Guatemala | 206 | Vanuatu |
| 51 | Serbia | 103 | Tanzania | 155 | Afganistán |  |  |
| 52 | Sudáfrica | 104 | Burkina Faso | 156 | India |  |  |

No todos aparecen en todas las ediciones: las más antiguas usan solo una parte de la lista.

Cada país tiene además **un aspecto por defecto** —un color de piel y uno de pelo— que el juego aplica a los jugadores de ese país cuando no se le dice otra cosa. Es la convención que usaba Dinamic, y explica por qué a veces un jugador sale con un aspecto que no le corresponde: se le está aplicando el de su selección.
