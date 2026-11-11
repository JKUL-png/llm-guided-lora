# Análisis final del paper 2: ¿ayuda que un LLM elija dónde entrenar?

**Versión 2 (2026-11-10).** Reescrito después de la revisión externa (`revision/REVISION_EXTERNA.md`), cuyas
correcciones se aceptaron todas. Sin GPU y sin experimentos nuevos: solo cambian los análisis y la redacción.
La versión 1 (la que se revisó) queda en el historial de git. Fuentes: `PLAN.md`, `BITACORA.md`, `RELACIONADO.md`
y los CSV de `paper2/resultados/`. Cada cifra importante lleva su CSV (rutas relativas a `paper2/resultados/`).
Los análisis corregidos salen de `revision/rev_estadistica.py` y están en `revision/rev_*.csv`.
Si la bitácora y un CSV no coinciden, manda el CSV. Lo que cambió respecto de la versión 1 está al final.

---

## Resumen en 10 líneas

1. Pregunta: si Opus diagnostica los bucles de Qwen3.5-0.8B y elige 4 capas para un LoRA, ¿gana a elegirlas al azar o con una regla automática?
2. **Respuesta: no encontramos ventaja.** El brazo guiado por Opus (b) no superó al azar (c) ni a la regla de gradiente (d) en MATH a 0.6.
3. (b) − (c) = −1.5 puntos [−8.75, +5.75], p 0.62; (b) − (d) = +2.75 [−5.25, +10.75], p 0.35; p Holm 0.69 en las dos (`revision/rev_comparaciones.csv`, `revision/rev_holm.csv`).
4. La regla escrita antes ("guiado gana" solo si (b) supera a (c) y a (d) tras Holm, en las dos temperaturas) **no se cumple a 0.6**; a 1.0 el brazo (b) no se evaluó.
5. Todos los LoRA sacan al modelo del bucle (de 92.25% de respuestas al límite a 2.5–10.5%). **No medimos cuánto se debe a los datos de entrenamiento:** ningún brazo cambia los datos.
6. **El lugar parece importar** (exploratorio): el barrido (e) queda +7.25 puntos sobre la regla de gradiente (d) [0.0, +14.5], y las "respuestas limpias" van de 57% (Opus) a 81% según el brazo; ahí Opus queda 20.75 puntos por debajo del azar [−38.25, −1.75].
7. **Ningún brazo supera a simplemente apagar el thinking** en MATH (51.75%); el más cerca, (e): +6.75 [−0.5, +14.25], p Holm 0.096.
8. En GSM8K los 6 LoRA superan al original sin thinking por +10 a +12.75 puntos (sólido), pero **empatan con la edición del MIT (p50c)**. En IFEval ninguno se distingue de apagar el thinking y **todos quedan de 6 a 12.5 puntos por debajo de p50c** (sólido en (b), (c) y (d)).
9. Hay solo 4 LoRA por brazo y 100 problemas: no se puede descartar una ventaja de Opus de hasta unos +6 puntos sobre el azar ni de +11 sobre la regla de gradiente. **Un empate no prueba igualdad.**
10. La frase honesta: *el lugar parece importar, pero Opus no encontró uno mejor que el azar.*

---

## La historia paso a paso

### Términos (se usan en todo el documento)
- **LoRA:** en vez de cambiar todos los pesos del modelo, se entrena un "parche" pequeño que se suma a ellos.
- **Rango:** el tamaño de ese parche. Más rango = más parámetros (números que se entrenan).
- **Capa:** Qwen3.5-0.8B tiene 24 bloques en fila (0 a 23). Cada uno tiene una parte **MLP**, que procesa cada token por separado. Aquí el LoRA toca solo la MLP.
- **Thinking:** modo en que el modelo "piensa en voz alta" antes de responder y cierra ese pensamiento con la etiqueta `</think>`. El 0.8B en thinking se queda dando vueltas (**bucle**) hasta agotar el tope de 32,768 tokens (**"al límite"**).
- **Semilla:** número que fija el azar de una corrida. Aquí cada semilla (0–3) fija el entrenamiento del LoRA y el muestreo de la evaluación.
- **Temperatura:** cuánto azar hay al elegir cada palabra. 0.6 = poco; 1.0 = más.
- **IC (intervalo de confianza al 95%):** el rango donde probablemente está el valor real. Si el IC de una diferencia cruza el 0, no se puede decir quién gana.
- **Bootstrap por problema:** se sortean los 100 problemas con reemplazo 10,000 veces y se mira cuánto se mueve el resultado. Así sale el IC.
- **Valor p:** qué tan raro sería ver una diferencia así si los dos modelos fueran iguales (p < 0.05 = "raro").
- **Permutación por problema (prueba principal desde la versión 2):** para cada problema se suma "aciertos de X menos aciertos de Y" en sus 4 semillas. Si X e Y fueran iguales, ese número podría tener el signo al revés; la prueba calcula, exacta, qué tan seguido saldría una suma tan grande. Respeta que las 4 semillas del mismo problema se parecen.
- **McNemar de 400 parejas:** la prueba de la versión 1. Trata las 400 parejas (problema, semilla) como independientes, y no lo son (**pseudo-replicación**), así que sus valores p salen algo bajos. Queda solo como comprobación de robustez.
- **IC de dos vías (intervalo principal desde la versión 2):** bootstrap que sortea los problemas **y también las 4 semillas** (es decir, los 4 LoRA de cada brazo). Sale más ancho que el IC por problema porque cuenta que otro entrenamiento u otro grupo de capas daría otro número. Con solo 4 LoRA es tosco y probablemente algo estrecho.
- **Holm:** si se hacen varias pruebas, alguna sale "rara" por suerte. Holm sube los valores p para corregirlo. "Sobrevive a Holm" = p corregido < 0.05.
- **Escrito antes (pre-specified) vs. exploratorio:** "escrito antes" = la prueba estaba en `PLAN.md` §6 antes de ver resultados. No es un pre-registro: todo vive en un git local, sin sello de tiempo de terceros. "Exploratorio" = se decidió mirar después de ver datos; vale como pista, no como prueba.
- **Sólido / indicio (regla de lectura de la versión 2, puesta después de ver los datos):** "sólido" = sobrevive a Holm con la permutación **y** su IC de dos vías no toca el 0. Si solo cumple una de las dos, es "indicio".
- **p50c:** el modelo editado por el MIT (130,188 pesos cambiados en las capas 15 y 19), evaluado con thinking. El PLAN lo lista como referencia; son datos del paper 1 recalificados con la regla de este paper (`calificacion/*_p50c_think_*`).
- **Respuesta limpia (exploratorio):** la que cierra el pensamiento una sola vez y no llega al límite.

### Diseño: 6 brazos con el mismo tamaño
Todos los LoRA tienen **2,654,208 parámetros** (verificado con fórmula y contando con PEFT, `p3_lista_lora.csv`). Una capa MLP cuesta 13,824 parámetros por unidad de rango, así que 24 capas × rango 8 = 4 capas × rango 48. Iguales en todo lo demás: datos, orden, 49 pasos, tasa de aprendizaje 2e-4, alfa = 2 × rango, 1 época (`p3_lista_lora.csv`).

| Brazo | Cómo se eligen las capas | Capas (semillas 0 / 1 / 2 / 3) | Rango |
|---|---|---|---|
| (a) Normal | Todas | 0–23 | 8 |
| (b) Opus informado | Una sesión de Opus por semilla, con contexto y mediciones del modelo | 11 15 19 22 / 14 19 22 23 / 12 15 17 20 / 10 14 15 22 | 48 |
| (c) Placebo | Sorteo fijado antes del diagnóstico | 1 2 4 20 / 12 14 18 21 / 7 9 10 14 / 1 5 9 15 | 48 |
| (d) Automático por gradiente | Las 4 con mayor norma de gradiente (256 ejemplos por semilla; las 4 semillas dieron lo mismo) | 10 14 15 23 (todas) | 48 |
| (e) Automático por barrido | Las 4 cuyo apagado más cambia la probabilidad de `</think>` | 0 10 12 15 (todas) | 48 |
| (f) Opus + barrido | Opus lee solo la tabla del barrido y elige | 10 14 15 17 / 10 14 15 17 / 10 14 15 18 / 10 14 15 18 | 48 |

(Fuente de las capas: `p3_lista_lora.csv`.) **Norma de gradiente** = cuánto "quiere" cambiar una capa para bajar el error. **Barrido** = apagar la MLP de cada capa, una por una, dentro de los bucles y medir el cambio.

Referencias sin entrenar (no son LoRA): **original con thinking** (el modelo roto) y **original sin thinking** (apagar el thinking, la vara barata que el PLAN obliga a mostrar siempre). Tercera referencia: **p50c**, la edición del MIT con thinking (la versión 1 la omitía).

Tamaño real de cada parche tras fusionarlo al modelo (‖ΔW‖/‖W‖ = cuánto cambia el peso respecto de su tamaño; máximo por tensor, por semilla): (a) 0.0162–0.0165; (b) 0.0367–0.0390; (c) 0.0377–0.0452; (d) 0.0364–0.0369; (e) 0.0380–0.0392; (f) 0.0370–0.0392. Más del 99.68% del parche sobrevive al redondeo a bf16 (resumen en `revision/rev_dw_resumen.csv`, generado por script desde los 24 `p3/fusion/*.csv`).

### Datos de entrenamiento
"Cortar y cerrar": 1,200 problemas de MATH *train* (no se solapan con la evaluación). Se deja al original pensar; cuando entra en bucle se recorta en la primera copia, se cierra `</think>`, el modelo contesta y solo se guardan las respuestas correctas. Salieron **388 ejemplos** (303 forzados, 85 naturales), 3,269,949 tokens (`p3_lista_lora.csv`; detalle en BITACORA 2026-11-07). La pérdida (el error que se entrena) cuenta solo en la frase de cierre y la respuesta.

### Etapas
1. **Piloto y P1b (2026-11-06/07):** la tubería funciona; un LoRA de prueba con todos los datos pasa de 0/20 a 8/20 correctas en 20 problemas de control (solo comprueba la receta, no es resultado).
2. **Diagnósticos (2026-11-06/07):** 1 sesión ciega (eligió 16, 17, 20, 21; no se entrenó), 4 sesiones "Opus informado" (→ (b)) y 2 de "Opus + barrido" (→ (f)). Costo: 7 sesiones, 4.21 USD equivalentes, 7.7 h de GPU como cota alta (`costo_diagnostico.csv`).
3. **Etapa 1 (2026-11-08):** brazo (a), 4 semillas, MATH a 0.6. **Parada 2** (regla fijada: bajar el % al límite al menos 20 puntos desde 92.25%): bajó a 2.5% → **PASA** (`p3/parada2.csv`).
4. **Etapa 2 (2026-11-08/09):** los otros 20 LoRA en MATH a 0.6. La cola se detuvo a mano una vez ("mátala") y se retomó sin perder resultados.
5. **Etapa 3 (2026-11-09):** el mejor brazo a 0.6 según una regla fijada antes (`mejor_brazo.py`: más correctas) fue **(e)** (`p3/mejor_brazo.csv`); se evaluó a 1.0, junto con el original sin thinking a 1.0.
6. **Etapa 4 (2026-11-09/10):** GSM8K e IFEval (100 problemas fijos cada uno) en los 24 LoRA a 0.6, más 3 semillas extra del original con thinking y 4 del original sin thinking (decisión 16).

### Qué se midió
En cada celda (brazo × semilla × tarea × temperatura): % de correctas, % al límite, tokens medios, % de respuestas con varios `</think>`. Motor: vLLM en WSL, LoRA fusionado, muestreo de la línea base del MIT (top_p 0.95, top_k 20, presence_penalty 1.5) cambiando solo la temperatura, tope 32,768 tokens. Conjuntos fijos del paper 1: MATH-500 (100), GSM8K (subconjunto 1, 100), IFEval (100).

### Regla de calificación (decisión 14)
- La respuesta final es el texto que va **tras el último** `</think>`. Con thinking, si no hay `</think>` = incorrecta.
- MATH y GSM8K: última `\boxed{}` de esa respuesta, comparada con **math-verify** (la librería que usa el MIT); sin caja = incorrecta.
- IFEval: el **corrector oficial** (lm-eval) sobre esa respuesta.
- Igual para todos los brazos y referencias; las del paper 1 se recalificaron (46 corridas, solo 2 cambian en ±1 problema, ambas de IFEval; BITACORA 2026-11-07).
- **Cuándo se fijó:** el 2026-11-07, antes de la evaluación real, pero **después** de ver que el LoRA de prueba (P1b) daba varios cierres en 8 de 20 problemas de control.
- **Sensibilidad (revisión):** la regla alternativa del primer cierre (la del paper 1) da exactamente la misma nota en las 4,800 respuestas LoRA de MATH y GSM8K (`revision/rev_regla_cierre_resumen.csv`). La elección de regla no cambia nada.

---

## Qué se escribió antes y qué se decidió después de ver resultados

"Escrito antes" significa aquí **pre-specified** en un git local sin subir; no hay pre-registro externo. El primer commit del paper 2 (`cf51b47`, 11-07 07:19) llegó cuando ya existían el plan, el sorteo del placebo, el diagnóstico ciego y P1b.

| Cuándo | Qué |
|---|---|
| **Antes de cualquier evaluación** | La prueba principal ((b) contra (c) y (d), con Holm) y la regla "guiado gana"; apagar el thinking como referencia obligatoria; el placebo (sorteo reproducible: `random.Random(20261106+s).sample(range(24), 4)`); mismo número de parámetros en todos los brazos; la regla del "mejor brazo" y la decisión 15 de medir 1.0 solo en él (commit `7483729`, 11-07 18:42; la etapa 1 empezó el 11-08 00:37). |
| **Antes de evaluar, pero ya habiendo visto algo** | La regla de calificación (tras ver los cierres múltiples de P1b). Los brazos (e) y (f), añadidos el 11-07 cuando ya se conocían las capas de las sesiones de Opus (antes de entrenar). Qué sesión de Opus va a qué semilla en (b). |
| **Después de ver MATH (etapa 2)** | Las familias de Holm (2 y 6 pruebas) y la forma de juntar las semillas: el script y sus resultados aparecen en el mismo commit (`4274fd9`, 11-09 11:14), con los datos ya en disco. |
| **Después de ver todo MATH (etapas 2 y 3)** | La decisión 16 (11-09 14:59): GSM8K e IFEval solo a 0.6, y **se quitó la tarea de la empresa** "porque la pregunta principal ya está respondida en MATH". Es justo la tarea donde elegir el lugar podría pesar más, y se quitó tras ver un resultado nulo. |
| **Después de ver todos los resultados (revisión, 11-10)** | La permutación por problema, el IC de dos vías, la regla "sólido / indicio", las pruebas contra p50c, las respuestas limpias, el piso de ruido simétrico y las familias de Holm alternativas. Todo esto corrige o amplía el análisis, pero se eligió mirando los datos. |

---

## A. PRUEBAS ESCRITAS EN EL PLAN (§6), CON EL ANÁLISIS CORREGIDO TRAS LA REVISIÓN

**Cómo leer las tablas.** "Dif. [IC95]" es el IC de dos vías. "p" es la permutación exacta por problema; "p Holm" corrige esas p dentro de su familia. La columna "Robustez" trae lo que usaba la versión 1: IC por problema y p de McNemar de 400 parejas. Todo sale de `revision/rev_comparaciones.csv`, `revision/rev_holm.csv` y `revision/rev_por_modelo.csv`. Las cifras de la versión 1 se recalcularon desde los CSV por problema: 468 de 468 coinciden (`revision/rev_verificacion_csv.csv`).

### A1. MATH-100 a 0.6 por modelo

| Modelo | Correctas % [IC95] | Por semilla | Al límite % | Tokens medios | Varios `</think>` % | Correctas entre las que terminan % |
|---|---|---|---|---|---|---|
| (a) 24 capas | 45.5 [35.5, 55.75] | 53 / 40 / 49 / 40 | 2.5 | 4,179 | 17.75 | 46.67 |
| (b) Opus informado | 54.0 [45.5, 63.0] | 51 / 51 / 58 / 56 | 10.5 | 7,554 | 39.25 | 60.34 |
| (c) Placebo | 55.5 [46.75, 64.25] | 55 / 57 / 57 / 53 | 6.0 | 6,266 | 18.5 | 59.04 |
| (d) Gradiente | 51.25 [42.5, 60.0] | 51 / 54 / 54 / 46 | 9.5 | 7,344 | 29.5 | 56.63 |
| (e) Barrido | 58.5 [50.0, 67.25] | 57 / 57 / 60 / 60 | 5.75 | 6,140 | 21.75 | 62.07 |
| (f) Opus + barrido | 52.0 [43.0, 61.0] | 52 / 55 / 54 / 47 | 6.5 | 6,586 | 27.0 | 55.61 |
| Original con thinking | 7.75 [3.75, 12.5] | (ver CSV) | 92.25 | 30,770 | 0.0 | 100.0 (31 respuestas) |
| Original sin thinking | 51.75 [43.0, 61.0] | 49 / 49 / 57 / 52 | 12.0 | 7,955 | 0.0 | 58.52 |
| p50c (MIT, thinking) | 51.25 [42.75, 60.0] | 51 / 51 / 50 / 53 | 29.25 | 21,436 | 10.5 | 72.44 |

Todos los IC se pisan. Ojo con (a): con las **mismas** 24 capas en sus 4 semillas va de 40 a 53. Reentrenar ya mueve 13 puntos; por eso el intervalo principal cuenta la variación entre LoRA. p50c acierta como los LoRA, pero se queda al límite casi 3 de cada 10 veces y gasta unas 3–5 veces más tokens.

### A2. Comparación principal y regla "guiado gana"

| Comparación (correctas) | Dif. [IC95] | p | p Holm | Robustez: IC por problema; p McNemar-400 | Lectura |
|---|---|---|---|---|---|
| (b) − (c) placebo | −1.5 [−8.75, +5.75] | 0.618 | 0.690 | [−6.25, +3.25]; 0.602 | no supera |
| (b) − (d) gradiente | +2.75 [−5.25, +10.75] | 0.345 | 0.690 | [−2.25, +8.0]; 0.300 | no supera |
| (b) − (a) 24 capas (secundaria) | +8.5 [−0.25, +17.75] | 0.0020 | 0.0020 | [+3.5, +13.75]; 0.00044 | indicio |

Más comprobaciones, todas con el mismo resultado: McNemar por mayoría de semillas (p 1.0 y 0.12), 4 LoRA contra 4 LoRA (p 0.54 y 0.37, `revision/rev_nivel_lora.csv`), los 24 emparejamientos posibles de semillas, y la regla de calificación alternativa (idéntica).

**La regla "guiado gana".** Pedía que (b) superara a (c) **y** a (d) tras Holm en las dos temperaturas (una sola = "evidencia parcial"). A 0.6 no supera a ninguno. A 1.0 **no se evaluó**: por la decisión 15 (presupuesto de GPU, escrita antes de ver resultados) la 1.0 solo se midió en el mejor brazo, que fue (e). Resultado: **no se cumple a 0.6; a 1.0 no evaluado.** Como ya falla a 0.6, la regla completa no podía cumplirse de ningún modo.

La secundaria (b) > (a) baja a **indicio**: su IC de dos vías toca el 0 y con 4 LoRA contra 4 da p 0.11. Además (a) cambia capas **y** rango, así que tampoco hablaría de Opus.

### A3. Cada brazo contra apagar el thinking y contra p50c, MATH a 0.6

| Brazo | − sin thinking: Dif. [IC95] | p | p Holm (6) | Robustez (IC; McNemar) | − p50c: Dif. [IC95] | p |
|---|---|---|---|---|---|---|
| (a) | −6.25 [−16.5, +3.75] | 0.069 | 0.345 | [−12.75, 0.0]; 0.025 | −5.75 [−14.5, +2.75] | 0.037 |
| (b) | +2.25 [−5.5, +10.25] | 0.442 | 1.0 | [−3.0, +7.25]; 0.412 | +2.75 [−4.75, +10.5] | 0.359 |
| (c) | +3.75 [−4.0, +11.25] | 0.197 | 0.789 | [−1.5, +9.0]; 0.128 | +4.25 [−2.5, +11.5] | 0.153 |
| (d) | −0.5 [−9.25, +7.5] | 0.932 | 1.0 | [−6.25, +5.25]; 0.922 | 0.0 [−7.5, +7.75] | 1.0 |
| (e) | +6.75 [−0.5, +14.25] | 0.016 | 0.096 | [+1.5, +12.0]; 0.009 | +7.25 [+0.75, +14.5] | 0.0079 |
| (f) | +0.25 [−8.0, +8.0] | 1.0 | 1.0 | [−4.75, +5.25]; 1.0 | +0.75 [−6.5, +8.0] | 0.845 |

**Ningún LoRA supera a apagar el thinking**, con ninguna prueba ni agrupación de Holm (`revision/rev_holm.csv`). Entrenar 2.65 M de parámetros con 388 ejemplos da, en MATH, algo que no distinguimos de cambiar una opción de generación. Las pruebas contra p50c son **nuevas (exploratorias)**: solo (e) queda por encima (p Holm 0.047), y (e) fue elegido "mejor brazo" con estos mismos datos. Apagar el thinking y p50c empatan: +0.5 [−7.25, +8.5].

### A4. MATH a 1.0 (solo (e) y las referencias, decisión 15)

| Modelo | Correctas % [IC95] | Al límite % |
|---|---|---|
| (e) Barrido | 54.25 [46.0, 63.0] | 0.25 |
| Original sin thinking | 51.5 [43.5, 60.25] | 1.0 |
| Original con thinking | 17.75 [11.0, 25.5] | 82.25 |
| p50c | 28.75 [20.75, 37.0] | 64.25 |

**(e) − sin thinking = +2.75 [−5.5, +10.75], p 0.43: no lo supera** (robustez: [−3.5, +9.0]; McNemar 0.375). Es la única medida de (e) que no está inflada por haberlo elegido como el mejor. Exploratorio: (e) − p50c = +25.5 [+17.75, +33.5]; p50c se cae a 1.0 y el LoRA no.

### A5. GSM8K e IFEval a 0.6

Escrito antes: cada brazo contra el original sin thinking (familia de 6 por tarea) y la secundaria (b) − (a). **Decidido después de ver MATH (decisión 16):** medir solo a 0.6. Las pruebas contra p50c son nuevas (exploratorias).

| Modelo | GSM8K correctas % [IC95] | GSM8K al límite % | GSM8K tokens | IFEval correctas % [IC95] | IFEval al límite % | IFEval tokens |
|---|---|---|---|---|---|---|
| (a) | 65.5 [57.0, 73.25] | 1.75 | 2,327 | 49.0 [39.5, 57.75] | 6.25 | 2,745 |
| (b) | 68.25 [59.75, 76.0] | 4.5 | 3,420 | 45.25 [36.75, 53.5] | 8.25 | 3,468 |
| (c) | 67.5 [58.0, 76.5] | 2.0 | 2,728 | 48.25 [40.0, 56.25] | 7.75 | 3,416 |
| (d) | 68.0 [59.0, 76.25] | 4.25 | 3,491 | 45.5 [36.25, 54.5] | 11.0 | 4,389 |
| (e) | 67.5 [59.0, 75.0] | 1.25 | 2,367 | 51.75 [42.5, 60.0] | 4.0 | 2,191 |
| (f) | 66.75 [58.5, 74.75] | 1.75 | 2,514 | 50.0 [41.25, 58.75] | 3.0 | 1,783 |
| Original sin thinking | 55.5 [47.0, 63.75] | 1.25 | 1,926 | 50.0 [40.0, 59.5] | 0.0 | 261 |
| Original con thinking | 11.75 [6.75, 17.75] | 87.75 | 29,304 | 18.75 [12.0, 26.25] | 72.75 | 24,886 |
| p50c | 67.5 [58.5, 75.5] | 6.0 | 11,627 | 57.75 [48.25, 66.5] | 1.0 | 3,659 |

| Brazo | GSM8K − sin thinking | p Holm | GSM8K − p50c | IFEval − sin thinking | IFEval − p50c | p Holm | Lectura (IFEval − p50c) |
|---|---|---|---|---|---|---|---|
| (a) | +10.0 [+2.5, +17.75] | 0.0009 | −2.0 [−8.5, +4.75] | −1.0 [−11.0, +9.25] | −8.75 [−18.0, +0.75] | 0.014 | indicio |
| (b) | +12.75 [+5.0, +21.0] | 0.0001 | +0.75 [−5.75, +8.0] | −4.75 [−14.25, +5.0] | −12.5 [−21.75, −3.25] | 0.0028 | sólido |
| (c) | +12.0 [+3.75, +20.5] | 0.0001 | 0.0 [−8.0, +7.5] | −1.75 [−11.5, +8.0] | −9.5 [−17.75, −1.5] | 0.0049 | sólido |
| (d) | +12.5 [+5.0, +20.5] | 0.00001 | +0.5 [−7.25, +8.0] | −4.5 [−14.75, +5.75] | −12.25 [−22.0, −3.0] | 0.0009 | sólido |
| (e) | +12.0 [+5.0, +19.5] | 0.0001 | 0.0 [−6.25, +6.75] | +1.75 [−8.0, +11.75] | −6.0 [−15.0, +2.75] | 0.068 | no |
| (f) | +11.25 [+4.0, +19.0] | 0.0002 | −0.75 [−7.0, +5.5] | 0.0 [−9.0, +9.5] | −7.75 [−16.75, +1.0] | 0.043 | indicio |

- **GSM8K:** los 6 brazos superan al original sin thinking (sólido; aguanta también juntando las 18 pruebas de las 3 tareas). **Pero empatan con p50c** (todas las p ≥ 0.47), y el original sin thinking queda −12.0 [−19.75, −4.0] bajo p50c. Lectura: en GSM8K pensar ayuda cuando el modelo logra terminar, se arregle como se arregle. No es un mérito especial del LoRA.
- **IFEval contra apagar el thinking:** no detectamos cambio en % de correctas (todas p Holm = 1.0), pero **no es "sin daño"**: no se puede descartar una pérdida de hasta unos 14 puntos, los LoRA llegan al límite en 3–11% (el original, 0%) y gastan de 7 a 17 veces más tokens.
- **IFEval contra p50c:** los 6 LoRA quedan por debajo (−6.0 a −12.5). Una edición de 130,188 pesos sigue instrucciones mejor que un LoRA de 2.65 M de parámetros. El original sin thinking también queda −7.75 [−18.0, +2.25] bajo p50c.
- **A favor del LoRA:** en MATH usa 3–5 veces menos tokens que p50c y no se cae a 1.0 (A4).
- **(b) − (a):** GSM8K +2.75 [−3.5, +9.25], p 0.24; IFEval −3.75 [−12.5, +4.75], p 0.19. Nada.

---

## B. LO EXPLORATORIO

> **Advertencia que vale para toda esta sección:** nada de esto estaba en `PLAN.md` §6. Se decidió mirarlo **después de ver datos**. Con muchas comparaciones, alguna sale "significativa" por suerte. Sirve para plantear hipótesis, no para afirmarlas.

**B1. EXPLORATORIO — brazos de 4 capas contra (a)** (`revision/rev_comparaciones.csv`, Holm dentro de 5). En MATH a 0.6: (c) − (a) = +10.0 [+1.25, +18.75] y (e) − (a) = +13.0 [+4.75, +21.5] son sólidas; (b) − (a) +8.5 [−0.25, +17.75], (d) − (a) +5.75 [−3.5, +14.75] y (f) − (a) +6.5 [−2.75, +16.0] son indicios (las dos últimas, p Holm 0.060). Los brazos de 4 capas **también llegan más al límite** que (a) (+3.25 a +8.0 puntos; prueba de la versión 1, `p3/etapa2_comparaciones.csv`). Como (a) cambia capas y rango a la vez, no se sabe cuál de las dos cosas lo explica.

**B2. EXPLORATORIO — el lugar parece importar** (`revision/rev_comparaciones.csv`, `revision/rev_holm.csv`).
- **(e) − (d) = +7.25 [0.0, +14.5]**, p 0.0020, p Holm 0.018 dentro de las 9 parejas entre brazos de 4 capas. Los dos brazos usan las mismas capas en sus 4 semillas: (e) 57 / 57 / 60 / 60 contra (d) 51 / 54 / 54 / 46. El IC de dos vías toca el 0: indicio fuerte, no prueba. La versión 1 no reportaba esta pareja.
- **(f) − (e) = −6.5 [−14.0, +0.5]**, p 0.0074; p Holm 0.037 en la familia de 5 de la versión 1 y 0.059 en la de 9. Indicio de que la regla automática del barrido superó a Opus leyendo esa misma tabla.
- (e) − (b) = +4.5 [−2.25, +11.0], p 0.038 sin corregir (Holm 0.27): no.
- Las demás ((f)−(c), (d)−(c), (e)−(c), (f)−(d)) no se distinguen.
- **Cuidado:** (e) fue elegido "mejor brazo" con estos mismos datos, así que toda comparación con (e) está inflada (**maldición del ganador**), e incluye la capa 0 (limitación 1). Ver también B9, donde el lugar pesa mucho más.

**B3. EXPLORATORIO — (e) contra el original con thinking a 1.0** (pedida tras ver la etapa 2): +36.5 [+27.5, +45.5] con el IC de dos vías (`revision/rev_comparaciones.csv`; IC por problema [+29.75, +43.5] y McNemar p < 1e-6 en `p3/etapa3_comparaciones.csv`). En % al límite: −82.0 puntos [−87.75, −75.75] (IC por problema, `p3/etapa3_comparaciones.csv`). Que un LoRA le gane al modelo roto es esperable; la vara relevante es sin thinking (A4).

**B4. EXPLORATORIO — contra el original con thinking en MATH a 0.6.** Los 6 brazos lo superan por +37.75 a +50.75 puntos (IC de dos vías desde +28.0; `revision/rev_comparaciones.csv`). En GSM8K e IFEval sí hay: todos los brazos superan al original con thinking por +53.75 a +56.5 (GSM8K) y +26.5 a +33.0 (IFEval), todos con McNemar p < 1e-6 (`p3/p5_*_comparaciones.csv`) y con el IC de dos vías muy lejos de 0 (`revision/rev_comparaciones.csv`).

**B5. EXPLORATORIO — (b) − (c) y (b) − (d) en GSM8K e IFEval** (`revision/rev_comparaciones.csv`). GSM8K: +0.75 [−6.75, +8.75] y +0.25 [−7.25, +8.0]. IFEval: −3.0 [−10.5, +4.25] y −0.25 [−8.75, +8.5]. Tampoco fuera de MATH aparece ventaja de Opus.

**B6. EXPLORATORIO — cierres múltiples (varios `</think>`).** Los LoRA a veces cierran, **siguen razonando** en la zona de la respuesta y vuelven a cerrar: es el bucle que continúa tras el cierre. (La versión 1 decía "cierran, contestan y vuelven a cerrar"; no es así: solo 3 de 615 respuestas con varios cierres en MATH y 2 de 247 en GSM8K tienen una caja `\boxed{}` antes del último tramo, `revision/rev_regla_cierre_items.csv`.) Por semilla, las respuestas con varios cierres aciertan mucho menos (por ejemplo (a) s0: 65.7% con un cierre contra 27.3% con varios; `p3/cierres_por_brazo.csv`). Pero dentro del **mismo problema** (problemas donde unas semillas cerraron una vez y otras varias) la diferencia casi desaparece: juntando los 6 brazos, un cierre − varios = +0.031 [−0.017, +0.082], 71 problemas ganan cada lado y 160 empatan (`p3/cierres_por_problema_todos_resumen.csv`). (Estos IC son por problema, no de dos vías.) Lectura tentativa: los varios cierres aparecen sobre todo en problemas difíciles, así que la diferencia entre semillas mezcla dificultad con efecto del cierre; esta comparación no prueba que los varios cierres no cuesten nada. Solo (b) da un IC apenas sobre cero (+0.145 [+0.012, +0.285]), esperable por azar entre 6 brazos.

**B7. EXPLORATORIO — "empeora / mejora" por problema** (`p3/cambios_*_por_brazo.csv`, `p3/cambios_*_comparaciones.csv`). Por pareja (problema, semilla), contra el original: "empeora" = el original acertaba y el brazo falla; "mejora" = al revés.
- Contra el original **con** thinking casi nada empeora (GSM8K 0.25–0.75%; IFEval 3.25–6.75%) y mucho mejora (GSM8K 54.0–57.25%; IFEval 31.75–38.0%).
- Contra el original **sin** thinking (el neto, mejora − empeora, va de −6.25 a +6.75 en MATH, +10.0 a +12.75 en GSM8K y −4.75 a +1.75 en IFEval): MATH empeora 8.75–17.5%, mejora 11.25–16.0%; GSM8K empeora 5.75–8.75%, mejora 18.25–20.5%; IFEval empeora 14.25–17.75%, mejora 12.75–16.75%.
- (a) contra los de 4 capas: en MATH (contra sin thinking) los 5 brazos de 4 capas empeoran menos que (a) (IC que no cruzan 0) y solo (e) mejora más que (a) (+4.75 [+1.75, +8.0]). En GSM8K/IFEval casi todo cruza 0; excepciones sueltas: (d) empeora 3.0 menos que (a) en GSM8K sin thinking [−6.0, −0.25] y (b) empeora 2.5 más que (a) en IFEval con thinking [+0.5, +4.5]. Sin Holm. **Ver B8 antes de creer nada de esto.**

**B8. EXPLORATORIO — piso de ruido, corregido** (`revision/rev_ruido_simetrico.csv`; pisos en `p3/ruido_semillas_por_modelo.csv`). **Piso de ruido** = cuánto cambia el resultado de un mismo problema entre dos semillas del **mismo** modelo. Original sin thinking: 24.83% (MATH), 26.67% (GSM8K), 20.67% (IFEval). La versión 1 restaba solo el piso del original; lo correcto es restar el **promedio de los dos pisos** (el del brazo y el del original), porque el ruido entra por los dos lados. Exceso corregido contra el original sin thinking:
- **MATH:** solo (a) cambia más que el azar: +5.0 [+1.33, +9.25] (es el brazo que baja 6.25 puntos). Los demás, de +0.21 a +2.04, cruzan 0.
- **GSM8K:** +1.92 a +4.46, con varios IC justo sobre 0 (por ejemplo (b): +4.46 [+1.0, +8.5]). La versión 1 decía "dentro del azar"; no del todo, y tiene sentido: una subida neta de 12 puntos no puede ser todo ruido.
- **IFEval:** +5.33 a +7.92 (IC desde +1.63). Hay cambio real por problema, pero un tercio menor que el +7.83 a +11.58 de la versión 1. **p50c da el mismo exceso (+6.42 [+2.17, +11.25])**: no es una huella del LoRA, es lo que pasa al comparar un modelo que piensa con uno que no.
- Contra el original con thinking el exceso es grande en las tres tareas (versión 1: +15.83 a +42.58, con el estimador antiguo; no recalculado).

**B9. EXPLORATORIO — respuestas limpias** (`revision/rev_respuestas_limpias.csv`, `revision/rev_respuestas_limpias_comparaciones.csv`). Limpia = un solo `</think>` y sin llegar al límite: lo que se quería arreglar. Métrica definida en la revisión, después de ver los datos.

| MATH a 0.6 | Limpias % [IC95] | Por semilla | Correctas entre limpias % | Correctas entre las de varios cierres % |
|---|---|---|---|---|
| (a) | 81.25 [69.5, 91.0] | 65 / 84 / 85 / 91 | 51.08 | 22.54 |
| (b) Opus | 57.0 [46.5, 67.25] | 60 / 45 / 61 / 62 | 75.44 | 28.03 |
| (c) Placebo | 77.75 [59.75, 92.5] | 75 / 53 / 92 / 91 | 64.31 | 29.73 |
| (d) | 66.0 [56.25, 76.0] | 58 / 61 / 69 / 76 | 67.05 | 23.73 |
| (e) | 74.25 [66.75, 81.75] | 71 / 72 / 80 / 74 | 70.03 | 29.89 |
| (f) | 69.0 [60.5, 77.25] | 64 / 65 / 75 / 72 | 65.58 | 25.0 |
| p50c | 61.0 [53.0, 69.0] | 57 / 62 / 62 / 63 | 76.64 | 42.86 |

- **Opus queda por debajo del azar:** (b) − (c) = −20.75 [−38.25, −1.75]; (b) − (e) = −17.25 [−27.75, −7.0]; (b) − (a) = −24.25 [−38.25, −9.0]. Contra (d): −9.0 [−20.75, +2.75] (indicio). (f) − (e) = −5.25 [−14.25, +3.5]. (b) − p50c = −4.0 [−14.5, +5.75].
- **El lugar pesa mucho aquí.** Dentro del placebo: el grupo de capas tardías (12 14 18 21) da 53 limpias; los de capas tempranas (7 9 10 14 y 1 5 9 15) dan 92 y 91. Por eso el IC de (c) es tan ancho.
- Las respuestas con varios cierres aciertan 22–30%, contra 51–75% de las limpias. El % al límite solo cuenta la mitad del problema residual.
- GSM8K, limpias: (a) 87.0, (b) 82.5, (c) 89.75, (d) 83.5, (e) 95.25, (f) 87.75, p50c 84.75. IFEval: 88.75–96.75; p50c 99.0.

**B10. EXPLORATORIO en su cálculo, prometido en el PLAN §3 — ganancia separada** (`revision/rev_ganancia_separada.csv`). La versión 1 no traía estas métricas. MATH a 0.6, % de correctas:

| | (a) | (b) | (c) | (d) | (e) | (f) | Sin thinking | p50c |
|---|---|---|---|---|---|---|---|---|
| Donde el original con thinking llegaba al límite (369 casos) | 41.2 | 50.7 | 52.0 | 47.7 | 55.0 | 48.2 | 48.8 | 47.2 |
| Donde el original terminaba (31 casos; acertaba 100%) | 96.8 | 93.5 | 96.8 | 93.5 | 100 | 96.8 | 87.1 | 100 |

Casi toda la ganancia viene de casos que antes llegaban al límite, como se esperaba. La precisión entre las que terminan está en la tabla A1: los LoRA (46.7–62.1%) no son mejores ahí que apagar el thinking (58.5%), y p50c es más preciso cuando termina (72.4%), aunque termina menos.

**B11. EXPLORATORIO — 4 LoRA contra 4 LoRA** (`revision/rev_nivel_lora.csv`). Tratando cada LoRA como una sola observación (permutación de etiquetas; con 4 y 4 el p mínimo posible es 0.029): (b)−(c) 0.54; (b)−(d) 0.37; (b)−(a) 0.11; (e)−sin thinking 0.086; (f)−(e) 0.029; GSM8K, cada brazo − sin thinking 0.029.

---

## C. LIMITACIONES

1. **Capa 0 en el brazo (e).** Apagar la capa 0 daña el modelo entero más que casi todas: es la 2.ª de 24 en daño general (KL 0.1205 [0.1074, 0.1344]) en razonamiento normal (`barrido/dano_general_resumen.csv`). **KL** = cuánto cambia la distribución de la siguiente palabra. Su efecto en `</think>` puede venir de "romper todo" y no de ser "la capa del cierre". Efecto: aunque (e) fue el mejor brazo en MATH, no se puede leer como "el barrido encontró el lugar correcto". La regla no se cambió (decisión del usuario). Además, (e) fue elegido "mejor" con los mismos datos con que se compara: a 1.0 su ventaja bajó de +6.75 a +2.75, compatible con regresión a la media.
2. **Solo 100 problemas por celda.** Con datos reales, una diferencia pareada necesita unos **6–9 puntos** para detectarse el 80% de las veces (`plan_diferencia_detectable.csv`: 8.57 y 5.89 puntos en dos pares del paper 1). Efecto: las diferencias reales entre brazos menores que eso pasan desapercibidas. **Un empate no prueba igualdad.** "Opus no ganó" no es lo mismo que "Opus es igual al azar". Con el IC de dos vías, lo que sí se puede acotar: la ventaja de Opus sobre el azar, si existe, no pasa de unos +5.75 puntos; sobre la regla de gradiente no se descarta hasta +10.75. No se fijó antes un margen de equivalencia, así que no se hace una prueba de equivalencia (TOST) a posteriori.
3. **Piso de ruido y reentrenamiento.** Gran parte del "empeora/mejora" por problema es azar de muestreo (B8). En los brazos, cada semilla es además otro LoRA entrenado y, en (b), (c) y (f), otro grupo de capas. Efecto: la variación entre semillas mezcla tres fuentes (muestreo, entrenamiento, elección de capas) y no se pueden separar con 4 semillas. La comparación (a) semilla 0 contra P1b, que son el mismo entrenamiento, ya mostró diferencias en 20 problemas de control (7 contra 8 correctas, 4 contra 1 al límite) con pérdida casi igual (0.1534 contra 0.153) (`p3/repro_a0.csv`).
4. **Cierres múltiples.** La regla de calificación ya no es una preocupación: la regla del primer cierre da notas idénticas en las 4,800 respuestas (`revision/rev_regla_cierre_resumen.csv`). Lo que sí importa es que una respuesta con varios cierres es un fallo residual que el % al límite no cuenta (B9). Aparte: Opus + barrido descartó las capas 0 y 12 usando la columna de "cierre natural" del barrido, que sale de **solo 3 respuestas** (BITACORA 2026-11-07). Señal frágil.
5. **Asignación de sesiones a semillas en (b).** El diseño solo decía "cada semilla usa una sesión". La correspondencia (semilla 0 ← sesión 4, 1 ← 1, 2 ← 2, 3 ← 3) la elegí yo al lanzar, antes de cualquier resultado de entrenamiento o evaluación, pero ya conociendo las capas de las sesiones 1 y 2, y quedó escrita como regla después (decisión 15 vi). Efecto: pequeño, porque no hubo resultados que mirar; pero es un grado de libertad no fijado por escrito de antemano. Para (f) la asignación sí estaba escrita antes (`DISENO_BARRIDO.md` §4).
6. **Alcance estrecho.** Un solo modelo (Qwen3.5-0.8B), solo LoRA en la MLP, solo MATH-100 para la pregunta principal, solo 0.6 y 1.0 en MATH (y 1.0 solo para (e)), solo 0.6 en GSM8K e IFEval, y un solo tipo de problema (bucles). Efecto: no se puede generalizar a otros modelos, tamaños, métodos (LoRA completo, edición de pesos) ni tareas.
7. **La empresa contable (tarea "enseñar") quedó fuera** (decisión 16). Efecto: no sabemos si elegir capas importa más cuando hay que meter conocimiento nuevo, que es justo donde el "lugar" podría pesar más que en un problema de formato.
8. **(d) y (f) comparten 3 de 4 capas** (10, 14, 15; `p3_lista_lora.csv`), y (e) comparte 2 con ambos. Efecto: no son brazos independientes; su empate ((f) − (d) = +0.75, `p3/etapa2_comparaciones.csv`) dice poco sobre si Opus aporta sobre la regla de gradiente.
9. **Anclaje en los brazos de Opus.** El contexto de las sesiones informadas nombraba las capas 15 y 19 del MIT; la 15 aparece en 3 de 4 sesiones (BITACORA 2026-11-07). Efecto: (b) no mide "Opus solo", sino "Opus con una pista del trabajo previo". No hay ningún brazo de Opus sin pista entrenado (el diagnóstico ciego eligió 16, 17, 20, 21 y no se entrenó). Además las 4 sesiones coinciden poco: comparten en promedio 1.33 capas de 4 (por puro azar serían 0.67). El resultado habla de **este protocolo**, no de "un LLM eligiendo dónde entrenar" en general.
10. **Estadística.** Solo hay **4 LoRA por brazo** (4 sesiones de Opus, 4 sorteos), y cada grupo de capas se entrenó una sola vez. La semilla fija tres cosas a la vez (entrenamiento, muestreo y, en (b), (c), (f), las capas), que no se pueden separar. El IC de dos vías intenta contarlo, pero con 4 unidades es tosco. La permutación por problema es exacta, pero condicional a estos 24 LoRA. Las familias de Holm, la forma de juntar semillas y la regla "sólido / indicio" se eligieron después de ver datos; `revision/rev_holm.csv` muestra que con otras familias la conclusión principal no cambia y que (e) contra sin thinking no sobrevive en ninguna. El McNemar de 400 parejas de la versión 1 daba valores p hasta 5 veces más bajos, sin cambiar ninguna conclusión.
11. **(a) no es comparable limpiamente.** Cambia capas y rango a la vez. El PLAN ya lo decía: la comparación limpia es entre (b), (c), (d) (y (e), (f)).
12. **Corte de WSL por Windows Update.** El 2026-11-10 a las 00:01:57 una actualización reinició WSL y mató `p6_ifeval_s1` a 74 de 100. Se relanzó y `p6_ifeval_s1..s3` terminaron completos a las 09:16 (BITACORA 2026-11-10). Lo verifiqué en el CSV: el original con thinking en IFEval tiene 400 respuestas y 4 semillas (21/24/16/14, `p3/p5_ifeval_por_brazo.csv`). Efecto sobre resultados: ninguno.
13. **Motor y referencias.** Todo se evaluó en vLLM (WSL). Las referencias del original con thinking vienen del paper 1, recalificadas con la misma regla. En la sesión 4 hubo un cuelgue de vLLM por falta de memoria (no se cobró; la sesión se dio por válida). Efecto: pequeño, pero un revisor podría pedir verificarlo.
14. **Datos generados por el propio modelo y filtrados por acierto.** Los 388 ejemplos son respuestas correctas del original tras forzar el cierre. Efecto: el LoRA aprende a cerrar, y quizá a cortar el razonamiento en general. Los tokens medios bajan mucho (de 30,770 a 4,179–7,554 en MATH; `p3/etapa2_por_brazo.csv`); no se midió si pierde razonamiento útil en problemas largos.
15. **No hay control de datos.** Los 24 LoRA usan los mismos 388 ejemplos. No existe un brazo con las mismas capas y datos distintos, así que no se puede decir cuánto de la salida del bucle se debe a la receta de datos.
16. **p50c viene del paper 1.** Mismos 100 problemas, mismo muestreo y 4 semillas, recalificado con la regla de este paper; pero las pruebas contra p50c se añadieron después de ver los datos (la versión 1 lo omitía aunque el PLAN lo listaba).

---

## Trabajo relacionado

**doubleAI, "Can LLMs redesign themselves as they train?"** (blog, 2026-11-06; `RELACIONADO.md`). Un agente mira el entrenamiento y agrega **capas de código** exactas detrás de una compuerta en cero; usa el "gradiente fantasma" (gradiente respecto de las representaciones internas) para decidir *dónde* ayudar. Tienen controles "twin" (misma corrida con la capa apagada) y "sham" (misma forma, información revuelta). Según lo visible en el texto, no indican semillas, intervalos, temperatura, hiperparámetros ni código (solo se cita lo visible; los comentarios del HTML no se citan).
- **Parecido:** la pregunta de fondo, "¿aporta algo que un agente diagnostique dónde intervenir?".
- **Diferencia:** ellos agregan código nuevo; nosotros elegimos capas de un LoRA. Nuestro placebo no es su sham: el nuestro mantiene los datos y sortea el lugar (mide si importa *dónde*), el suyo mantiene el lugar y daña la información (mide si importa *qué*). No es una réplica. Nuestro brazo (d) usa gradientes de pesos, un pariente simple de su gradiente fantasma.

**kevinpl07, "weight-patching"** (kevinpl07.github.io/weight-patching). **Se conoce solo por una imagen que envió el usuario** (`referencias/weight-patching_kevinpl07_figura.png`); **no se leyó la página ni su código**. Según la figura: compara una edición de pesos contra "LoRA, same data" en 4 bugs, con decodificación greedy; su conclusión textual es *"LoRA ties or wins on the bug in 3 of 4. The edit wins on side effects. A random edit of the same size does nothing."*
- **Parecido:** la misma sospecha (¿un baseline barato iguala al método sofisticado?) y la idea de medir efectos secundarios ("other outputs unchanged" se parece a nuestro P5 y a la métrica empeora/mejora).
- **Diferencia:** ellos comparan edición contra LoRA; nosotros, formas de elegir capas del LoRA. Su "random edit" no es nuestro placebo. Greedy contra muestreo con 4 semillas. Sin intervalos ni tamaños de muestra visibles. Miden salidas sin cambio (probablemente texto); nosotros acierto por problema. **No se usa como evidencia de nuestro resultado.**

---

## Qué se puede y qué NO se puede decir en el paper

**Frases seguras (con su número y CSV al lado):**
- "In our setting, layers chosen by an informed Opus session (given layer hints from prior work) did not outperform random layers or a gradient-norm rule (MATH-100, T = 0.6, n = 4 LoRAs per arm; differences −1.5 [−8.75, +5.75] and +2.75 [−5.25, +10.75] points; Holm-adjusted permutation p = 0.69)."
- "Our pre-specified criterion for 'guided wins' was not met at T = 0.6; the guided arm was not evaluated at T = 1.0."
- "All LoRA arms escaped the reasoning loop (truncation fell from 92.25% to 2.5–10.5%). We did not vary the training data, so we cannot say how much of this is due to the data recipe."
- "Exploratory evidence suggests that layer choice matters (sweep rule vs. gradient rule: +7.25 points [0.0, +14.5]; clean-stop rate ranges from 57% to 81% across arms), but Opus did not find a better place than chance."
- "No arm beat simply disabling thinking on MATH after Holm correction. On GSM8K all six arms did (+10 to +12.75 points), matching the MIT weight edit (p50c). On IFEval no arm differed from no-thinking, and all six scored 6 to 12.5 points below p50c (robust for three arms)."
- "With 100 problems and 4 LoRAs per arm, we cannot rule out an Opus advantage of up to about +6 points over random layers or +11 over the gradient rule."
- "Exploratory: the automatic sweep rule (e) scored 6.5 points above Opus reading the same sweep table (f) ([−14.0, +0.5]); suggestive only, and (e) includes layer 0, which shows broad damage when ablated."

**Frases prohibidas:**
- "Opus eligió mejor" / "Opus chose better layers" (falso con nuestros datos).
- "Layer choice does not matter" / "el lugar da igual" (un empate no prueba igualdad, y los indicios dicen lo contrario).
- "It was the data, not the place" / "lo que importó fueron los datos" (ningún brazo cambia los datos).
- "regardless of which layers were trained" (el % al límite y las respuestas limpias cambian según el brazo).
- "Pre-registered" (decir "pre-specified": git local, sin sello de tiempo externo).
- "No harm on IFEval" (contra p50c quedan por debajo; contra sin thinking no se descarta una pérdida de ~14 puntos).
- "(b) beats standard LoRA" sin decir que es un indicio y que (a) cambia capas y rango.
- "The sweep found the right layers" (capa 0, selección con los mismos datos, exploratorio).
- "LoRA fixes math reasoning" sin decir que apagar el thinking da lo mismo en MATH.
- "LoRA causes no forgetting" (en IFEval hay cambios por problema por encima del piso, aunque el % no cambie; solo se puede decir "no medible en % de correctas").
- "Multiple `</think>` causes errors" (dentro del mismo problema no se ve).
- Cualquier cifra de doubleAI sacada de los comentarios del HTML, o cualquier detalle de weight-patching que no esté en la imagen.
- Llamar "sham" o "twin" a nuestro placebo.

---

## Revisión externa (hecha el 2026-11-10) y qué cambió respecto de la versión 1

La versión 1 terminaba con 8 preguntas para un revisor. Están respondidas en `revision/REVISION_EXTERNA.md`. Se aceptaron todas las correcciones:

1. **Resumen y frase final:** se quitó "lo que importó fueron los datos, no el lugar" (no se midió). Ahora: "el lugar parece importar, pero Opus no encontró uno mejor que el azar".
2. **Estadística:** el intervalo principal es el IC de dos vías y la prueba principal es la permutación por problema. El IC por problema y el McNemar de 400 parejas quedan como robustez.
3. **p50c** está en todas las tablas de MATH, GSM8K e IFEval.
4. **Tablas con script guardado:** respuestas limpias y ‖ΔW‖/‖W‖ se generan ahora con `revision/rev_estadistica.py` (0 celdas distintas respecto de las que se hicieron a mano en la revisión).
5. **"Pre-specified", no "pre-registered"**, y una sección nueva que dice qué se decidió después de ver resultados.
6. **Bajan de categoría:** (b) > (a), (f) < (e) y el "por poco" de (e) contra sin thinking pasan a indicio o a "no".
7. **Corregidos:** el piso de ruido (B8), la descripción de los cierres múltiples (B6), el texto de IFEval (A5) y "tampoco evidencia parcial" (A2).
8. **Añadidos:** métricas prometidas en el PLAN (precisión entre las que terminan, ganancia separada) y las cotas del resultado nulo.

**La conclusión principal no cambió:** con todas las pruebas, Opus no superó al azar ni a la regla de gradiente.

**Lo que haría falta con GPU (no hecho; lo decide el usuario):** más sorteos del placebo y reentrenos del mismo grupo de capas, un brazo con datos falsos, y (b) a 1.0.

---

## Índice de archivos y CSV usados

Documentos: `paper2/CLAUDE.md`, `paper2/PLAN.md` (§2, §3, §6, §7, §9 decisiones 14–16), `paper2/BITACORA.md`, `paper2/RELACIONADO.md`, `paper2/resultados/p3/ANALISIS_ETAPA2.md`, `paper2/resultados/p3/ANALISIS_ETAPA3.md`.

CSV (bajo `paper2/resultados/`):
- Diseño: `p3_lista_lora.csv`, `plan_diferencia_detectable.csv`, `costo_diagnostico.csv`, `barrido/dano_general_resumen.csv`, `p3/fusion/*.csv` (24 archivos).
- MATH: `p3/etapa2_por_brazo.csv`, `p3/etapa2_por_semilla.csv`, `p3/etapa2_comparaciones.csv`, `p3/etapa3_por_brazo.csv`, `p3/etapa3_comparaciones.csv`, `p3/mejor_brazo.csv`, `p3/parada2.csv`, `p3/repro_a0.csv`.
- P5: `p3/p5_gsm8k_por_brazo.csv`, `p3/p5_gsm8k_comparaciones.csv`, `p3/p5_ifeval_por_brazo.csv`, `p3/p5_ifeval_comparaciones.csv`.
- Revisión y versión 2 (`revision/`): `rev_por_modelo.csv`, `rev_comparaciones.csv`, `rev_holm.csv`, `rev_nivel_lora.csv`, `rev_ganancia_separada.csv`, `rev_ruido_simetrico.csv`, `rev_regla_cierre_resumen.csv`, `rev_regla_cierre_items.csv`, `rev_respuestas_limpias.csv`, `rev_respuestas_limpias_comparaciones.csv`, `rev_dw_resumen.csv`, `rev_verificacion_csv.csv`. Scripts: `rev_estadistica.py` (Python estándar, ~1 min) y `rev_regla_cierre.py` (WSL, CPU). Referencia p50c: `calificacion/*_p50c_think_*`.
- Exploratorio: `p3/cierres_por_brazo.csv`, `p3/cierres_por_problema_todos_resumen.csv`, `p3/cierres_por_problema_a_resumen.csv`, `p3/cambios_{math,gsm8k,ifeval}_{nothink,think}_{por_brazo,comparaciones}.csv` (MATH solo sin thinking), `p3/ruido_semillas_por_modelo.csv`, `p3/ruido_vs_cambios.csv`.

Diferencias encontradas entre BITACORA/PLAN y los CSV (manda el CSV):
- PLAN §3 da 51.5% para el original sin thinking en MATH a 0.6; `p3/etapa2_por_brazo.csv` da 51.75% (51.5% es el valor a 1.0 en `p3/etapa3_por_brazo.csv`). Aquí se usa 51.75%.
- BITACORA redondea a 1 decimal: (b) − (d) "+2.8" (CSV +2.75), (e) − sin thinking "+6.8" (CSV +6.75), IC de (b) − (c) "[−6.3, +3.3]" (CSV [−6.25, +3.25]).
- BITACORA P5: "mejora 18–20%" en GSM8K (CSV 18.25–20.5) y "mejora 13–17%" en IFEval (CSV 12.75–16.75); piso de los brazos en IFEval "25–29%" (CSV 24.67–29.33) y exceso "+8 a +12" (CSV +7.83 a +11.58).
- `CLAUDE.md` pide reportar ‖ΔW‖/‖W‖ por brazo, pero no hay un CSV resumen: solo los 24 `p3/fusion/*.csv` por tensor. Resuelto en la versión 2: `revision/rev_dw_resumen.csv`.
- Las etiquetas FIJADA de (b) − (a) en GSM8K/IFEval (`p3/p5_*_comparaciones.csv`) son una lectura del PLAN §6, que no dice en qué tarea va la secundaria.
