# REVISIÓN EXTERNA del paper 2 ("¿ayuda que un LLM elija dónde entrenar?")

**Fecha:** 2026-11-10. **Papel:** revisor externo y escéptico (tipo "revisor 2"). No participé en el proyecto.
**Qué leí:** `resultados/ANALISIS_FINAL.md`, `PLAN.md`, `BITACORA.md`, `RELACIONADO.md`, los scripts de análisis y los CSV por problema.
**Qué NO hice:** no usé la GPU, no generé respuestas nuevas, no cambié ningún archivo existente. No revisé el código de entrenamiento ni las transcripciones de las sesiones de Opus. No recalifiqué IFEval (ahí confío en la columna `correcto`).
**Todo lo nuevo está en esta carpeta** (`resultados/revision/`), con prefijo `rev_`. Son análisis de revisión, hechos **después** de ver los datos: valen como comprobación de robustez, no como pruebas fijadas.

---

## Veredicto en corto

- **La conclusión principal aguanta:** con estos datos, las capas elegidas por Opus no superaron a las elegidas al azar ni a la regla de gradiente. La probé de siete formas distintas y ninguna la cambia.
- **Pero la frase que la acompaña NO aguanta:** "lo que importó fueron los datos, no el lugar" (líneas 5 y 10 del resumen). Ningún brazo cambia los datos, así que eso no se midió. Y los propios datos dan pistas de que el lugar **sí** importa (problema 1).
- **Falta una referencia que el PLAN sí listaba:** el modelo editado del MIT (p50c). En IFEval los 6 LoRA quedan entre 6 y 12.5 puntos **por debajo** de él (problema 3).
- **Varias afirmaciones secundarias "significativas" son más frágiles de lo que parecen** cuando se cuenta que cada brazo son solo 4 LoRA entrenados (problema 2).
- No encontré errores de cálculo: **468 cifras recalculadas desde cero, 0 diferencias.**

---

## Términos nuevos de esta revisión

- **Pseudo-replicación:** contar como datos independientes cosas que se parecen entre sí (aquí, las 4 semillas del mismo problema). Hace que los valores p salgan más bajos de lo justo.
- **Permutación de signos por problema:** prueba que respeta esa dependencia. Para cada problema se calcula "aciertos de X menos aciertos de Y" sumando sus 4 semillas (un número de −4 a +4). Luego se pregunta: si X e Y fueran iguales, cada problema podría tener el signo al revés; ¿qué tan seguido saldría una suma tan grande como la observada? La calculé exacta (sin sorteo).
- **Unidad de análisis:** qué cosa cuenta como "una observación". Si la pregunta es sobre *formas de elegir capas*, la unidad no es el problema, es el *grupo de capas elegido* (y aquí hay 4 por brazo).
- **Bootstrap de dos vías:** como el bootstrap por problema, pero sorteando también las semillas (es decir, los LoRA). Da intervalos más anchos y más honestos cuando se quiere hablar de "el método" y no de "estos 4 LoRA".
- **Prueba de equivalencia (TOST):** sirve para afirmar "son iguales dentro de un margen ±δ". Exige fijar δ **antes**. No es lo mismo que "no encontré diferencia".
- **Maldición del ganador:** si eliges al mejor de 6 con unos datos, su ventaja en esos mismos datos está inflada por suerte.
- **Control positivo:** una prueba de que el experimento *puede* detectar el efecto si existe.

---

## Verificación de números (lo que sí cuadra)

| Qué verifiqué | Resultado | Archivo |
|---|---|---|
| 468 cifras de los CSV de resultados originales de las etapas 2, 3 y P5 (% por brazo, IC, al límite, tokens, varios cierres, diferencias, McNemar) recalculadas desde los CSV por problema | **0 no coinciden** | `rev_verificacion_csv.csv` |
| Calificación de las 4,800 respuestas LoRA de MATH y GSM8K, rehecha desde los textos con math-verify | **0 diferencias** con la columna `correcto` | `rev_regla_cierre_items.csv` |
| Sorteo del placebo: `random.Random(20261106+s).sample(range(24), 4)` | Reproduce exactamente las 4 listas de capas de (c) | (cálculo directo) |
| Rangos de ‖ΔW‖/‖W‖ por brazo (línea 57 de ANALISIS_FINAL) | Coinciden con los 24 archivos de `p3/fusion/` | `rev_dw_resumen.csv` (el CSV resumen que faltaba) |
| Fechas en git: decisión 15 y `mejor_brazo.py` (commit `7483729`, 11-07 18:42) antes de la etapa 1 (11-08 00:37) | Cierto | `git log` |

Los números del documento son fieles a los CSV. Los problemas están en **qué se concluye** de ellos y en **qué se dejó fuera**.

---

## Problemas, de más grave a menos grave

### 1. GRAVE — "Lo que importó fueron los datos, no el lugar" no está sostenido por ningún contraste

**Qué dice el documento:** resumen, línea 5: "Lo que sí funcionó fue la receta de datos, no el lugar". Línea 10: "lo que importó fueron los datos de entrenamiento". Frase segura en inglés: "...regardless of which layers were trained".

**Por qué no se sostiene:**
- **Ningún brazo cambia los datos.** Los 24 LoRA usan los mismos 388 ejemplos. Para decir "fueron los datos" hace falta un brazo con las mismas capas y datos distintos (el "sham" de doubleAI, que `RELACIONADO.md` reconoce que aquí no existe). Sin eso, "fueron los datos" es una suposición razonable, no un resultado.
- **Los propios datos sugieren que el lugar sí importa** (todo exploratorio, hecho por mí después de ver datos):
  - (e) − (d) = **+7.25 puntos [+3.0, +11.75]**, p = 0.002; sobrevive a Holm incluso metiendo las 9 parejas posibles entre brazos de 4 capas (p Holm 0.018; `rev_holm.csv`). Los dos brazos usan **las mismas capas en sus 4 semillas**, así que son 4 entrenamientos contra 4: por semilla, (e) 57/57/60/60 contra (d) 51/54/54/46. ANALISIS_FINAL no reporta esta pareja.
  - **Respuestas limpias** (un solo `</think>` y sin llegar al límite, que es justo lo que se quería arreglar) en MATH: (a) 81.25%, (c) 77.75%, (e) 74.25%, (f) 69.0%, (d) 66.0%, **(b) 57.0%** (`rev_respuestas_limpias.csv`). Dentro del placebo, por grupo de capas: 75 / **53** / 92 / 91. El grupo de capas tardías (12 14 18 21) da 53; los de capas tempranas (7 9 10 14 y 1 5 9 15) dan 91–92. Eso es una diferencia enorme *entre lugares*.
  - El propio B1 del documento dice que los brazos de 4 capas llegan más al límite que (a), con significancia.
- Ojo con no pasarse al otro lado: (e) fue elegido como mejor brazo con estos mismos datos (maldición del ganador) y a 1.0 solo se midió (e).

**Qué habría que hacer:**
1. Quitar las líneas 5 y 10 tal como están. Versión que sí se sostiene: *"todos los LoRA, en cualquiera de las capas probadas, sacan al modelo del bucle; no medimos qué parte se debe a los datos"*.
2. Quitar "regardless of which layers were trained" de las frases seguras: el % al límite va de 2.5 a 10.5 y las respuestas limpias de 57 a 81 según el brazo.
3. Reportar (e) − (d) y las respuestas limpias como exploratorio. La lectura honesta es: *"hay indicios de que el lugar importa; Opus no encontró un lugar mejor que el azar"*. Es una conclusión más interesante y más fiel que "el lugar no importó".
4. Si algún día hay GPU: un brazo con datos falsos (mismas capas, mismos pasos, ejemplos sin la receta de "cortar y cerrar"). Sin él, no afirmar nada sobre los datos.

---

### 2. GRAVE — La unidad de análisis: son 4 grupos de capas de Opus contra 4 al azar, y los intervalos lo ignoran

**Qué pasa:** la pregunta es sobre *formas de elegir capas*. De cada forma hay solo 4 muestras (4 sesiones de Opus, 4 sorteos). Además, la semilla fija tres cosas a la vez: el entrenamiento del LoRA, el muestreo de la evaluación y, en (b), (c) y (f), el grupo de capas. Cada grupo de capas se entrenó **una sola vez**. El bootstrap por problema trata a esos 4 LoRA como fijos: responde "¿estos 4 LoRA difieren de aquellos 4 en otros problemas?", no "¿elegir con Opus difiere de elegir al azar?".

**Evidencia** (`rev_nivel_lora.csv`, `rev_comparaciones.csv`):
- Con capas **idénticas**, las semillas de (a) dan 53 / 40 / 49 / 40 (13 puntos de extremo a extremo). El ruido de reentrenar es del mismo tamaño que las diferencias entre brazos.
- Por semilla, (b) − (c) = −4, −6, +1, +3.
- Intervalos al contar también el azar entre LoRA (bootstrap de dos vías, aproximado porque solo hay 4):

| Comparación (MATH 0.6) | IC original (por problema) | IC de dos vías | p con 4 contra 4 LoRA |
|---|---|---|---|
| (b) − (c) | [−6.25, +3.25] | [−8.75, +5.75] | 0.54 |
| (b) − (d) | [−2.25, +8.0] | [−5.25, +10.75] | 0.37 |
| (b) − (a) "sobrevive" | [+3.5, +13.75] | **[−0.25, +17.75]** | **0.11** |
| (e) − sin thinking "por poco" | [+1.5, +12.0] | [−0.5, +14.25] | 0.086 |
| (f) − (e) "sobrevive" | [−11.0, −2.25] | **[−14.0, +0.5]** | 0.029 (el mínimo posible con 4 y 4) |
| GSM8K: (a) − sin thinking | [+4.5, +15.75] | [+2.5, +17.75] | 0.029 |

**Consecuencia:**
- La conclusión principal ("no superó") **sale reforzada**, no debilitada: los intervalos se ensanchan y siguen cruzando el 0.
- Pero **(b) > (a)** y **(f) < (e)** dejan de ser sólidas cuando se habla de métodos y no de estos LoRA concretos. La ganancia en GSM8K sí aguanta.

**Qué habría que hacer:**
1. Decir en el paper, sin rodeos: "n = 4 grupos de capas por brazo; los IC son condicionales a esos grupos y a esos entrenamientos".
2. Reportar los puntajes por semilla de todos los brazos en la tabla principal (ya están en `p3/etapa2_por_semilla.csv`).
3. Bajar (b) − (a) y (f) − (e) a "indicio".
4. Si hay GPU: más sorteos del placebo (para conocer cómo se reparte "el azar") y repetir el entrenamiento de un mismo grupo de capas con varias semillas, para separar "capas" de "suerte del entrenamiento". Es el experimento que más valor añadiría.

---

### 3. GRAVE-MEDIO — Se omitió la edición del MIT (p50c), que el PLAN lista como referencia, y cambia la lectura de IFEval

**Qué pasa:** `PLAN.md` (tabla de referencias, línea 75) incluye "p50c del MIT, thinking". Los datos existen, recalificados con la regla del paper 2 (`resultados/calificacion/*_p50c_think_*`). ANALISIS_FINAL no lo menciona ni una vez.

**Evidencia** (`rev_por_modelo.csv`, `rev_comparaciones.csv`, `rev_holm.csv`; misma temperatura, mismo muestreo, mismos 100 problemas, 4 semillas):

| Tarea (0.6) | p50c | LoRA (rango de los 6) | Diferencia LoRA − p50c |
|---|---|---|---|
| MATH | 51.25% (29.25% al límite, 21,436 tokens) | 45.5–58.5% (2.5–10.5% al límite, 4,179–7,554 tokens) | de −5.75 a +7.25; solo (e) sobrevive a Holm (p 0.047) |
| GSM8K | 67.5% | 65.5–68.25% | de −2.0 a +0.75; nada |
| **IFEval** | **57.75%** (1% al límite) | **45.25–51.75%** | **de −6.0 a −12.5; 5 de 6 sobreviven a Holm** |
| MATH a 1.0 | 28.75% | (e) 54.25% | +25.5 [+18.75, +32.5] |

Detalle de IFEval: (a) −8.75 [−14.5, −3.0]; (b) −12.5 [−19.25, −6.0]; (c) −9.5 [−15.25, −4.0]; (d) −12.25 [−18.25, −6.5]; (e) −6.0 [−12.25, −0.25]; (f) −7.75 [−14.0, −1.5]. El original sin thinking también queda −7.75 por debajo de p50c.

**Consecuencia:**
- "En IFEval no hay daño medible" solo es cierto contra *apagar el thinking*. Contra la edición pequeña del MIT (130,188 pesos), los LoRA (2.65 millones de parámetros) siguen instrucciones claramente peor.
- En GSM8K, la ganancia de +10 a +12.75 no es mérito especial del LoRA: p50c da lo mismo. La lectura correcta es "pensar ayuda en GSM8K cuando el modelo logra terminar, se arregle como se arregle".
- A favor del LoRA, y también falta decirlo: usa 3–5 veces menos tokens que p50c en MATH y no se cae a 1.0.

**Qué habría que hacer:** añadir p50c a todas las tablas (A1, A4, A5) y una familia "contra p50c". Estas pruebas son nuevas y posteriores a los datos: marcarlas como exploratorias. Si se omitió a propósito, explicar por qué; a un revisor le parecerá una omisión conveniente.

---

### 4. MEDIO — "IFEval: no hay daño medible" es más suave de lo que permiten los datos

**Evidencia:**
- Los IC contra sin thinking llegan a **−11.5** ((b): −4.75 [−11.5, +2.0]) y −11.0 ((d)). No se puede descartar un daño de 11 puntos.
- Los LoRA llegan al límite en 3.0–11.0% de las respuestas; el original sin thinking, en 0%. Usan 1,783–4,389 tokens de media contra 261 (7 a 17 veces más). Eso **es** un efecto secundario medido.
- En los casos donde el original con thinking sí terminaba (109 de 400), acierta 67.9%; ahí (b) acierta 46.8%, (d) 53.2%, (e) 54.1%, y p50c 66.1% (`rev_ganancia_separada.csv`). Es un subgrupo pequeño y elegido a posteriori: pista, no prueba.
- Contra p50c, ver problema 3.

**Qué habría que hacer:** cambiar "no hay daño medible" por "no detectamos cambio en % de correctas contra apagar el thinking; no podemos descartar una pérdida de hasta ~11 puntos; sí medimos más respuestas truncadas y 7–17 veces más tokens; contra p50c los LoRA quedan por debajo".

---

### 5. MEDIO — Un resultado nulo, leído un poco más allá de lo que da

El documento ya dice "un empate no prueba igualdad" (bien). Aun así faltan tres cosas:

- **No hay margen de equivalencia fijado.** Con IC al 90% (los que usa TOST; `rev_comparaciones.csv`): (b) − (c) = [−5.5, +2.5] y (b) − (d) = [−1.5, +7.25]. Solo se podría declarar "equivalentes" con un margen mayor que ±5.5 y ±7.25. Lo que **sí** se puede decir: la ventaja de Opus sobre el azar, si existe, es menor que +2.5 puntos (unilateral al 5%, condicional a estos LoRA; +5.75 con el intervalo de dos vías). Sobre la regla de gradiente **no se puede descartar una ventaja de hasta +7 puntos**.
- **Qué "Opus" se probó.** Una sesión por semilla, con la pista de las capas 15 y 19 del MIT, eligiendo 4 de 24 capas para un LoRA solo de MLP. Las 4 sesiones coinciden poco entre sí: comparten en promedio 1.33 capas de 4 (por puro azar serían 0.67), y las sesiones 1 y 2 no comparten ninguna. Un método que da respuestas tan distintas cada vez difícilmente gana en promedio. El resultado habla de **este protocolo**, no de "un LLM eligiendo dónde entrenar" en general.
- **Solo 0.6 y solo "arreglar bucles".** La tarea donde el lugar podría pesar más (enseñar la empresa) se quitó (ver problema 7).

**Qué habría que hacer:** en el resumen, sustituir "Respuesta: no" por "No encontramos ventaja", y dar al lado la cota: "descartamos una ventaja sobre el azar mayor que ~+2.5 a +6 puntos; no podemos descartar hasta +7 sobre la regla de gradiente". No hacer un TOST ahora con un margen elegido después de ver datos.

---

### 6. MEDIO — Faltan métricas que el PLAN prometía, y "salió del bucle" se mide solo con el % al límite

**Qué prometía `PLAN.md` §3 (línea 65):** "precisión entre las que terminan" y "ganancia separada entre 'antes llegaba al límite' y 'ya terminaba'". La línea 59 dice que se reportan justo por el riesgo de que el LoRA aprenda a cortar el razonamiento. ANALISIS_FINAL no las trae.

**Las calculé** (`rev_por_modelo.csv`, `rev_ganancia_separada.csv`), MATH a 0.6:

| | (a) | (b) | (c) | (d) | (e) | (f) | Sin thinking | p50c |
|---|---|---|---|---|---|---|---|---|
| % correctas entre las que terminan | 46.7 | 60.3 | 59.0 | 56.6 | 62.1 | 55.6 | 58.5 | 72.4 |
| % correctas donde el original llegaba al límite (369 casos) | 41.2 | 50.7 | 52.0 | 47.7 | 55.0 | 48.2 | 48.8 | 47.2 |
| % correctas donde el original terminaba (31 casos; el original acierta 100%) | 96.8 | 93.5 | 96.8 | 93.5 | 100 | 96.8 | 87.1 | 100 |

Lectura: nada alarmante en MATH; casi toda la ganancia viene de casos que antes llegaban al límite, como era de esperar. Pero entre las que terminan, los LoRA no son mejores que apagar el thinking, y p50c es bastante más preciso cuando termina (72.4%, aunque termina menos).

**"Salió del bucle" está contado a medias.** El % al límite baja de 92.25% a 2.5–10.5%, cierto. Pero hay otro modo de fallo: varios `</think>`. Esas respuestas aciertan 22–30% contra 51–75% de las limpias (`rev_respuestas_limpias.csv`). Sumando los dos, (b) solo da una respuesta limpia el 57% de las veces. En esa medida, **(b) queda 20.75 puntos por debajo del placebo** [−26.5, −15.25] y 9.0 por debajo de (d) [−14.25, −4.0] (`rev_respuestas_limpias_comparaciones.csv`). Es una métrica que definí yo después de ver datos: exploratoria. Pero apunta en la misma dirección que la conclusión principal, y más fuerte.

**Qué habría que hacer:** añadir estas dos métricas prometidas y la de respuestas limpias a la tabla A1.

---

### 7. MEDIO — Cosas decididas después de ver resultados (o sin fecha comprobable) que aparecen como fijadas

El documento es bastante transparente; casi todo esto está confesado en algún lugar. El problema es que los **títulos** dicen "fijado" y los matices están enterrados.

| Qué | Cómo se presenta | Qué encontré | Gravedad |
|---|---|---|---|
| Familias de Holm (2 y 6) y forma de juntar semillas | Dentro de la sección A, titulada "PRUEBAS FIJADAS ANTES DE VER RESULTADOS". La línea 83 dice que se anotaron "antes de mirar las conclusiones" | `analisis_etapa2.py` aparece por primera vez en el commit `4274fd9` (11-09 11:14), **junto con sus resultados** y con todos los datos de la etapa 2 ya en disco. No hay forma de comprobar el "antes". | Media. No cambia nada (ver pregunta 2), pero no es "fijado". |
| Regla de calificación (decisión 14) | Título: "fijada antes de evaluar" | Se fijó el 11-07 **después** de ver que el LoRA de prueba (P1b) producía varios cierres en 8 de 20 problemas de control. Es anterior a la evaluación real, pero no a ver el fenómeno. | Baja: la regla alternativa da resultados idénticos (pregunta 8). |
| Alcance de GSM8K/IFEval (A5, "lo fijado") | Como pruebas fijadas | La decisión 16 (11-09 14:59) recortó el alcance **después** de ver MATH: solo 0.6, y se quitó la tarea de la empresa "porque la pregunta principal ya está respondida en MATH". Las pruebas estaban en el PLAN; **qué se corrió** se decidió mirando resultados. | Media: quitar la tarea donde la hipótesis tenía más oportunidad, tras ver un nulo, hay que decirlo en el texto principal, no en la limitación 7. |
| "Guiado gana = NO; tampoco evidencia parcial" | Como resultado de la regla | La regla definía "evidencia parcial" como ganar en una de dos temperaturas. (b) nunca se midió a 1.0. Lo correcto: "no se cumple a 0.6; a 1.0 no se evaluó". | Baja. |
| "Pre-registered criterion" (frase segura en inglés) | Pre-registro | Todo está en un git local sin subir. El primer commit del paper 2 (`cf51b47`, 11-07 07:19) llega **después** del plan, del sorteo del placebo, del diagnóstico ciego y de P1b. No hay sello de tiempo de terceros. | Media: usar "pre-specified" y publicar el historial de git. |
| Brazos (e) y (f) | Parte del diseño de 6 brazos | Se añadieron el 11-07, cuando ya se conocían las capas de las sesiones informadas, pero antes de entrenar nada. | Baja; está dicho. |
| Qué sesión de Opus va a qué semilla en (b) | Limitación 5 | Confesado. Sin resultados a la vista. | Baja. |
| 1.0 solo en el mejor brazo | Decisión 15 | Sí es anterior a los resultados (commit comprobado). Pero rompe la regla de `paper2/CLAUDE.md` ("siempre 0.6 y 1.0") y deja la regla principal sin poder evaluarse entera. | Baja; está dicho. |
| Métrica "empeora/mejora" y piso de ruido | Sección B | Bien marcadas como exploratorias. | Ninguna. |

**Qué habría que hacer:** renombrar la sección A a algo como "Pruebas escritas en el PLAN (con las elecciones de análisis hechas después, señaladas)", y poner una tabla como esta en el paper.

---

### 8. MEDIO-BAJO — El McNemar de 400 parejas es pseudo-replicación (y el emparejamiento de semillas es arbitrario)

**Qué pasa:** dos defectos. (i) Las 4 semillas del mismo problema no son independientes. (ii) Emparejar "semilla 0 de X con semilla 0 de Y" no significa nada cuando Y es el original: son muestreos sin relación, y el valor p cambia según cómo se emparejen.

**Evidencia** (`rev_comparaciones.csv`, `rev_holm.csv`):

| Comparación | p McNemar 400 | Rango de p con los 24 emparejamientos | **p permutación por problema** | Holm original → Holm corregido |
|---|---|---|---|---|
| (b) − (c) | 0.602 | 0.594–0.627 | **0.618** | 0.602 → 0.690 |
| (b) − (d) | 0.300 | 0.300–0.355 | **0.345** | 0.599 → 0.690 |
| (b) − (a) | 0.00044 | 0.0004–0.0022 | **0.0020** | sobrevive igual |
| (a) − sin thinking | 0.025 | 0.019–0.030 | **0.069** | 0.124 → 0.345 |
| (e) − sin thinking | 0.0093 | 0.006–0.011 | **0.016** | 0.056 → **0.096** |
| (f) − (e) | 0.0067 | 0.006–0.012 | **0.0074** | 0.033 → 0.037 |
| GSM8K, el más débil ((a) − sin thinking) | 0.00017 | 0.0001–0.0003 | **0.0009** | sobrevive igual |

**Consecuencia:** como predecía la limitación 10, los p originales eran algo bajos (hasta 5 veces en GSM8K). **Ninguna conclusión cambia.** Lo único que se mueve es el "por poco" de (e), que deja de ser tan "por poco" (0.056 → 0.096).

**Qué habría que hacer:** usar la permutación de signos por problema como prueba principal y dejar el McNemar de 400 como nota. Ver pregunta 1.

---

### 9. BAJO-MEDIO — El "piso de ruido" está construido de forma asimétrica

**Qué pasa:** el "exceso" se calcula como (cambios brazo-contra-original) menos (piso **del original**). Pero una pareja brazo-original tiene ruido de los dos lados. Si el brazo es más ruidoso que el original, el exceso sale inflado; si es menos ruidoso, sale desinflado. La cuenta correcta resta el **promedio de los dos pisos** (así el exceso mide solo cuánto difieren de verdad las probabilidades de acierto por problema).

**Evidencia** (`rev_ruido_simetrico.csv`):
- **IFEval:** el exceso baja de +7.83…+11.58 (documento) a **+5.3…+7.9**. Los IC siguen sin tocar el 0 (desde +1.6). Hay cambio real por problema, pero un tercio menor que el reportado.
- **p50c da el mismo exceso en IFEval (+6.4).** O sea, no es una huella especial del LoRA: comparar un modelo que piensa con uno que no piensa ya produce ese cambio.
- **MATH:** (a) pasa de "dentro del azar" a **+5.0 [+1.3, +9.25]**. Tiene sentido: (a) es el brazo que baja 6.25 puntos.
- **GSM8K:** pasa de "dentro del azar" (−2.67 a +1.58) a **+1.9…+4.5**, casi todos con el IC rozando o superando el 0. También tiene sentido: una subida neta de 12 puntos no puede ser "todo ruido".

**Qué habría que hacer:** cambiar el estimador por el simétrico, corregir la frase "en MATH y GSM8K lo que cambia cada brazo queda dentro del azar" y añadir p50c como comparación.

---

### 10. BAJO — Maldición del ganador en (e) y temperatura 1.0

Está bien confesado (limitación 1). Solo añado: como (e) se eligió por ser el máximo de 6, **toda** comparación de (e) con estos mismos datos está inflada, incluidas las que cito yo en el problema 1 ((e) − (d)). La única medida "limpia" de (e) es a 1.0: +2.75 [−3.5, +9.0] contra sin thinking. Recomiendo que el resumen cite ese número cuando hable de (e).

### 11. BAJO — La descripción de los cierres múltiples es inexacta

B6 dice "cierran, contestan y vuelven a cerrar". Miré los textos: de 615 respuestas con varios cierres en MATH, solo **3** tienen una caja `\boxed{}` antes del último tramo (2 de 247 en GSM8K). No "contestan y vuelven a cerrar": cierran, **siguen razonando** en la zona de la respuesta, y vuelven a cerrar. Es el bucle que continúa después del cierre. Por eso conviene contarlo como fallo residual (problema 6) y por eso la regla de calificación no importa (pregunta 8).

### 12. BAJO — Detalles

- Holm se aplica sobre valores p ya redondeados a 5 decimales. Sin efecto práctico.
- El resumen de ‖ΔW‖/‖W‖ no tenía CSV, contra la regla "solo números de CSV". Lo dejo en `rev_dw_resumen.csv`.
- La "diferencia detectable de 6–9 puntos" viene de dos parejas del paper 1. Con los datos reales de este paper sale parecida (medio ancho de IC ≈ 4.75–5.25, es decir unos 7 puntos para detectarla el 80% de las veces). Está bien, pero conviene citar la cifra propia.
- "Estadísticamente indistinguible de cambiar una opción de generación" (A3): "no distinguido" sería más exacto; el IC de (a) llega a −12.75 y el de (e) a +12.0.
- El incidente de memoria de la sesión 4 (que alimenta la semilla 0 de (b)) merece una línea en el paper.

---

## Respuestas a las 8 preguntas

**1. ¿Es justo el McNemar sobre 400 parejas?**
No del todo: es pseudo-replicación, y además el emparejamiento de semillas contra las referencias es arbitrario. Recomiendo la **permutación de signos por problema** (exacta, sin supuestos, usa las 4 semillas). El McNemar por mayoría de semillas es válido pero tira mucha información: con él, (b) − (a) pasa de p 0.002 a 0.012, y (e) − sin thinking a 0.064. Un modelo mixto no hace falta para 100 problemas y 4 semillas. Efecto real del cambio: ninguna conclusión se mueve (problema 8). El problema de fondo no es este, sino la unidad de análisis (problema 2).

**2. ¿Las familias de Holm son razonables?**
Sí, son defendibles, y probé otras (`rev_holm.csv`):
- Juntar las 9 pruebas fijadas de MATH en una familia: (b) − (c) y (b) − (d) siguen en p = 1.0 o cerca; (b) − (a) sobrevive (0.018); (e) − sin thinking 0.13.
- Solo los 4 brazos del PLAN original contra sin thinking: nada sobrevive.
- Las 3 tareas juntas (18 pruebas): GSM8K sobrevive entero (máximo 0.012); (e) en MATH 0.19.
- (f) − (e): sobrevive en la familia de 5 (0.037) pero **no** en la de las 9 parejas entre brazos de 4 capas (0.059).
Conclusión: lo principal no depende de la agrupación. (e) contra sin thinking no sobrevive en **ninguna** agrupación con la prueba corregida. (f) − (e) sí depende de la familia: tratarlo como indicio. Y decir que las familias se eligieron en el análisis, no en el PLAN.

**3. ¿Está bien acotada por la potencia? ¿Hace falta TOST?**
"6–9 puntos detectables" es correcto pero incompleto. No hacer TOST ahora: el margen se elegiría después de ver los datos. Lo honesto es dar los intervalos y leerlos como cotas (problema 5): ventaja de Opus sobre el azar menor que +2.5 (por problema) o +5.75 (dos vías); sobre la regla de gradiente no se descarta hasta +7.25 / +10.75. Para un futuro experimento: fijar antes un margen (por ejemplo ±5 puntos) y calcular cuántos problemas y cuántos grupos de capas hacen falta.

**4. ¿Es válido haber evaluado 1.0 solo en el "mejor brazo"?**
Como decisión de presupuesto tomada antes de ver resultados, sí (lo comprobé en git). Pero tiene tres costos que hay que escribir: (i) la regla "guiado gana" quedó evaluable solo a 0.6, y así debe reportarse; (ii) "tampoco evidencia parcial" debe ser "no evaluado a 1.0"; (iii) el dato de 1.0 de (e) sirve para corregir la maldición del ganador, no para comparar brazos. Como (b) ya falla a 0.6, la regla completa no podía cumplirse de ningún modo: eso sí es sólido.

**5. ¿(b) mide "Opus" o "Opus + pista del MIT"?**
"Opus + pista". Llamarlo así siempre ("Opus informed, with prior-work layer hints"). La capa 15 sale en 3 de 4 sesiones y la 19 en 2 de 4. Importa en las dos direcciones: si (b) hubiera ganado, no se sabría si fue Opus o la pista; como no ganó, tampoco se puede decir que "Opus sin pista" habría perdido (el diagnóstico ciego eligió 16, 17, 20, 21 y nunca se entrenó). El paper debe decir que **no hay brazo de Opus sin pista entrenado**.

**6. ¿Qué aporta (b) − (a)?**
Poco, y debe salir del texto principal. (a) cambia capas y rango a la vez, y al contar el ruido de entrenamiento la diferencia ya no es clara (IC de dos vías [−0.25, +17.75]; 4 contra 4 LoRA p = 0.11; (a) va de 40 a 53 con las mismas capas). Dejarla en una tabla suplementaria con esa advertencia. Lo único útil de (a) es como aviso: el LoRA "normal" de 24 capas es el brazo con menos aciertos en MATH y el único que queda por debajo de apagar el thinking (−6.25, p 0.069).

**7. ¿Están bien construidos "empeora/mejora" y el piso de ruido?**
La idea es buena y poco habitual; la cuenta, no. Hay que restar el promedio de los dos pisos, no solo el del original (problema 9). Con eso la objeción de la pregunta desaparece: el piso del brazo (que incluye reentrenar y cambiar capas) entra en la resta, y lo que queda mide cuánto difieren las probabilidades de acierto por problema entre "la familia de LoRA de ese brazo" y el original. Resultado corregido: IFEval +5.3 a +7.9 (real, pero menor, y p50c da lo mismo); MATH (a) +5.0; GSM8K +1.9 a +4.5.

**8. ¿Cómo tratar la regla de varios `</think>`?**
Hice el análisis de sensibilidad (`rev_regla_cierre.py`, en WSL, solo CPU). **La regla del primer cierre del paper 1 da exactamente la misma calificación en las 4,800 respuestas LoRA de MATH y GSM8K.** Ni una cambia. Motivo: casi nunca hay una caja antes del último tramo (problema 11). También probé un techo ("correcta si cualquier tramo acierta"): idéntico. La limitación 4 puede sustituirse por una frase: "la regla alternativa del primer cierre produce resultados idénticos (0 de 4,800 cambios)". El problema de los cierres múltiples no es de calificación sino de **qué cuenta como arreglado** (problema 6).

---

## Lo que está bien hecho (para ser justo)

- Los números son reproducibles: 468 de 468 cifras, y la calificación entera de MATH y GSM8K.
- El placebo se sorteó con una semilla reproducible y los 6 brazos tienen exactamente los mismos parámetros.
- La referencia "apagar el thinking" no está debilitada: en GSM8K da 55.5% aquí contra 53.2% con el muestreo no-thinking del MIT en el paper 1; en IFEval 50.0% contra 51.2%.
- La sección de limitaciones es larga y honesta; la lista de "frases prohibidas" es una buena práctica.
- La regla del "mejor brazo" y la decisión 15 sí están en git antes de los resultados.
- Se reporta un resultado nulo sin maquillarlo.

---

## ¿Aguanta la conclusión principal?

**"Opus no superó al azar ni a la regla barata": SÍ aguanta.**

| Comprobación | (b) − (c) azar | (b) − (d) gradiente |
|---|---|---|
| Diferencia e IC por problema | −1.5 [−6.25, +3.25] | +2.75 [−2.25, +8.0] |
| Permutación de signos por problema | p = 0.62 | p = 0.35 |
| McNemar por mayoría de semillas | 8 contra 9, p = 1.0 | 14 contra 6, p = 0.12 |
| IC de dos vías (problemas y LoRA) | [−8.75, +5.75] | [−5.25, +10.75] |
| 4 LoRA contra 4 LoRA | p = 0.54 | p = 0.37 |
| Regla de calificación alternativa | idéntico | idéntico |
| GSM8K / IFEval | +0.75 / −3.0 | +0.25 / −0.25 |
| Respuestas limpias (exploratorio) | −20.75 [−26.5, −15.25] | −9.0 [−14.25, −4.0] |

No hay ninguna forma razonable de mirar estos datos en la que Opus gane. En la medida más cercana al objetivo (terminar limpio), queda claramente peor que el azar.

**Con cuatro condiciones para que la frase sea honesta:**

1. Es **"no superó"**, no "es igual" ni "no aporta". No se descarta una ventaja de hasta ~+7 puntos sobre la regla de gradiente.
2. Vale para **este protocolo**: 4 sesiones de Opus con pista del MIT, 4 de 24 capas, LoRA solo en MLP, Qwen3.5-0.8B, MATH-100, temperatura 0.6, tarea de bucles. Con n = 4 grupos de capas por brazo.
3. "La regla barata" es la de gradiente (d), que era la fijada. La otra regla barata, el barrido (e), queda por encima de Opus (+4.5 [+0.5, +8.5], p = 0.038 sin corregir): dato exploratorio y con maldición del ganador, pero va en la misma dirección.
4. **Hay que soltar la segunda mitad de la frase del resumen** ("lo que importó fueron los datos de entrenamiento"). Eso no se midió, y los indicios disponibles dicen que el lugar sí importa.

**Frase que yo firmaría:**
*"En nuestro montaje, las capas elegidas por Opus (con pistas del trabajo previo) no superaron a capas al azar ni a una regla de gradiente (−1.5 y +2.75 puntos; n = 4 grupos de capas por brazo, 100 problemas). No podemos descartar ventajas menores de ~6–7 puntos. Todos los LoRA sacan al modelo del bucle, pero en MATH ninguno supera a apagar el thinking, y en IFEval todos quedan por debajo de la edición del MIT. Hay indicios exploratorios de que el lugar sí importa; Opus no lo encontró."*

---

## Qué haría antes de escribir el paper (por orden, todo sin GPU salvo lo marcado)

1. Reescribir las líneas 5 y 10 del resumen y las frases seguras afectadas (problema 1).
2. Añadir p50c a las tablas y la familia "contra p50c" (problema 3).
3. Cambiar McNemar-400 por permutación de signos por problema; añadir la tabla por semilla y la advertencia de n = 4 (problemas 2 y 8).
4. Añadir las métricas prometidas y las respuestas limpias (problema 6).
5. Corregir el piso de ruido (problema 9) y el texto de IFEval (problema 4).
6. Poner la tabla de "decidido antes / después" (problema 7) y cambiar "pre-registered" por "pre-specified".
7. (Con GPU, opcional, lo decide el autor) más sorteos del placebo y reentrenos del mismo grupo de capas; un brazo con datos falsos; (b) a 1.0.

---

## Archivos de esta revisión (`paper2/resultados/revision/`)

| Archivo | Qué contiene |
|---|---|
| `REVISION_EXTERNA.md` | Este documento |
| `rev_estadistica.py` | Script principal (Python estándar, sin GPU; ~40 s). Uso desde `paper2/`: `python resultados/revision/rev_estadistica.py` |
| `rev_regla_cierre.py` | Recalificación con reglas alternativas (WSL, math-verify, CPU; ~20 s) |
| `rev_verificacion_csv.csv` | Las 468 cifras originales contra las recalculadas |
| `rev_por_modelo.csv` | % por modelo y tarea, por semilla, al límite, precisión entre terminadas, tokens (incluye p50c) |
| `rev_comparaciones.csv` | 81 comparaciones: IC 95% y 90%, McNemar-400 y su rango con 24 emparejamientos, permutación de signos, z por problema, McNemar por mayoría, IC de dos vías |
| `rev_holm.csv` | Holm con familias originales y alternativas, con las dos pruebas |
| `rev_nivel_lora.csv` | Análisis con 4 LoRA por brazo como unidad |
| `rev_ganancia_separada.csv` | Aciertos donde el original llegaba al límite y donde terminaba |
| `rev_ruido_simetrico.csv` | Piso de ruido con el estimador simétrico, junto al original |
| `rev_regla_cierre_items.csv`, `rev_regla_cierre_resumen.csv` | Sensibilidad a la regla de calificación |
| `rev_respuestas_limpias.csv`, `rev_respuestas_limpias_comparaciones.csv` | Respuestas con un solo cierre y sin llegar al límite |
| `rev_dw_resumen.csv` | Máximo de ‖ΔW‖/‖W‖ por LoRA (el resumen que no tenía CSV) |

**Aviso de reproducibilidad:** `rev_dw_resumen.csv`, `rev_respuestas_limpias.csv` y `rev_respuestas_limpias_comparaciones.csv` los generé con comandos cortos de Python escritos en la terminal, que no quedaron guardados como script. Los demás CSV se regeneran con los dos scripts de arriba. Si esas tres tablas van al paper, hay que rehacerlas con un script guardado. **Actualización (2026-11-10, tras aceptarse la revisión):** ya las genera `rev_estadistica.py` (0 celdas distintas respecto de las hechas a mano; se añadió p50c y el IC de dos vías), y el IC de dos vías se calcula ahora para todas las comparaciones y para cada modelo.

GPU durante la revisión: 829 MiB usados y 0 procesos antes y después de la única corrida en WSL (hecha con `CUDA_VISIBLE_DEVICES` vacío).
