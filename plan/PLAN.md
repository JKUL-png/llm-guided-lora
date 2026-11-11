# Plan del paper 2 (aprobado el 2026-11-06)

**Pregunta:** si un LLM diagnostica un problema y elige dónde entrenar, ¿el resultado es mejor que elegir al azar o con una regla automática barata?

**Estado:** plan aprobado, con las decisiones de la sección 9. Entorno y scripts del piloto listos; piloto terminado y parada 1 superada el 2026-11-06. Lo marcado **supuesto** no está medido. Las medidas salen de `paper2/scripts/estimar_plan.py` y están en `paper2/resultados/plan_*.csv`.

## 1. Términos
- **LoRA:** en vez de cambiar los pesos del modelo, se entrena un parche pequeño que se suma a ellos.
- **Rango:** el tamaño de ese parche. Más rango significa más parámetros.
- **Capa:** Qwen3.5-0.8B tiene 24 bloques en fila. Cada uno tiene una parte MLP, que procesa cada token por separado.
- **Norma de gradiente:** cuánto "quiere" cambiar una capa para reducir el error.
- **Semilla:** el número que fija el azar de una corrida.
- **Sesión ciega:** una sesión de Opus que no conoce la respuesta de antemano.

## 2. Los cuatro brazos

| Brazo | Capas | Rango | Parámetros LoRA |
|---|---|---|---|
| (a) Normal | Las 24 | 8 | 2,654,208 |
| (b) Opus informado | 4 que elige Opus con contexto y mediciones | 48 | 2,654,208 |
| (c) Placebo | 4 al azar | 48 | 2,654,208 |
| (d) Automático | Las 4 con mayor norma de gradiente | 48 | 2,654,208 |

**Por qué solo la parte MLP.** Medí las formas reales: si LoRA toca todos los módulos, una capa de atención lineal cuesta 29,216 parámetros por rango y una de atención completa 25,088 (`plan_modulos_por_capa.csv`). Entonces dos grupos de capas no darían el mismo total. En la parte MLP todas cuestan 13,824 por rango, y la igualdad es exacta (`plan_igualar_parametros.csv`).

**Referencia en todas las comparaciones de bucles: apagar el thinking.** No es un brazo de LoRA: es el modelo original sin entrenar y sin thinking. Aparece en cada tabla, tarea y temperatura (sección 3).

**Lo que esto no aísla.** (a) difiere de los demás en capas y en rango a la vez. La comparación limpia es entre (b), (c) y (d); (a) queda como referencia.

**Igual en todos los brazos:** datos, orden de los datos por semilla, pasos, tasa de aprendizaje y alfa/rango. La tasa de aprendizaje se fija antes (2e-4, **supuesto**). El piloto solo comprueba que no diverja; no se ajusta mirando la evaluación.

**Semillas.** Cada semilla s (0–3) fija el entrenamiento y el muestreo de la evaluación:
- (c): sorteo fijado por adelantado con `random.Random(20261106 + s).sample(range(24), 4)`, guardado antes del diagnóstico. Son 4 grupos distintos.
- (d): 256 ejemplos de entrenamiento sorteados con la semilla. Se calcula en el modelo sin entrenar, sumando ‖∂L/∂W‖ de las 3 matrices MLP de cada capa. Se usa la norma cruda; la relativa a ‖W‖ solo se anota.
- (b): ver sección 4.

## 3. Tarea 1: bucles

### Datos de entrenamiento (decisión 1)
Este es el mayor riesgo del plan. Hay que enseñar a terminar, y el modelo casi nunca termina por sí solo:

| Fuente | Rendimiento medido | Problema |
|---|---|---|
| Respuestas correctas y terminadas, thinking a 0.6 | 7.75% (5.25% con ≤8,192 tokens) | Pocas, y casi nada de nivel 5 (0.0%) |
| Igual a temperatura 1.0 | 17.75% (4.75% con ≤8,192) | Mediana de 14,283 tokens |
| **Cortar y cerrar** (variante B del paper 1) | 34 de 100: 25 forzadas + 9 naturales | 1 sola corrida; mediana de 9,733 tokens |

**Propuesta: cortar y cerrar.** Se detecta el bucle, se recorta en la primera copia, se cierra `</think>`, el modelo contesta y solo se conservan las respuestas correctas según math-verify. Esto enseña a salir de la repetición usando texto del propio modelo.

- **Problemas:** 1,200 del conjunto de entrenamiento de MATH (7,500), que no se solapa con MATH-500. Hay que descargarlo y comprobarlo.
- **Rendimiento esperado:** unos 400 ejemplos (**supuesto**, si se repite el 34%).
- **Por qué no p50c:** usar el modelo editado por el MIT como maestro metería su edición en todos los brazos.
- **GSM8K e IFEval no se usan para entrenar:** sirven para medir transferencia y olvido.
- **Un solo conjunto de datos fijo** para los 4 brazos y las 4 semillas. 1 época.
- **Dónde cuenta la pérdida (detalle nuevo):** solo en la salida, es decir, la frase de cierre y la respuesta. El texto previo se lee, pero no se entrena. Así no se refuerza el camino que llevó al bucle y baja mucho la memoria. El piloto mide también la opción de entrenar con todo el texto.

**Riesgo de memoria.** El vocabulario tiene 248,320 tokens. Con 8,192 tokens, las predicciones en float32 ocupan unos 8 GB, tanto como toda la GPU. Por eso la pérdida se calcula por pedazos y solo donde cuenta. El piloto decide el largo máximo. Si solo cabe un largo corto, se pierde buena parte de los ejemplos: solo 10 de las 25 forzadas tienen ≤8,192 tokens y 1 tiene ≤4,096.

**Riesgo de interpretación.** El modelo podría aprender a cortar su razonamiento en general, no solo a salir de bucles. Por eso se reportan tokens y precisión entre las que terminan.

### Evaluación
- **Motor:** vLLM en WSL, con LoRA fusionado al modelo y `BASE_MIT`, cambiando solo la temperatura (0.6 y 1.0), 32,768 tokens.
- **Conjuntos:** los fijos del paper 1: MATH-500 (100), GSM8K (subconjunto 1), IFEval (100).
- **Calificación (decisión 14):** la respuesta final es lo que va tras el **último** `</think>`; ver abajo.
- **Métricas:** precisión, % al límite, % de respuestas con más de un `</think>`, precisión entre las que terminan, tokens medios, ganancia separada entre "antes llegaba al límite" y "ya terminaba", ‖ΔW‖/‖W‖ tras fusionar.
- **Fusión:** el piloto comprueba que redondear a bf16 no borre el parche.

### Referencias

Todas con 4 semillas y `BASE_MIT`. Precisión en MATH:

| Modelo | Temp. 0.6 | Temp. 1.0 |
|---|---|---|
| Original, thinking | 7.75% | 17.75% |
| p50c del MIT, thinking | 51.25% | 28.75% |
| **Original, sin thinking** | 51.5% | Falta medir |

**Apagar el thinking es la vara principal.** Da 51.5% a 0.6 sin entrenar nada, así que cada brazo se compara también contra eso. Qué existe y qué hay que correr:

| Tarea | Temp. 0.6 | Temp. 1.0 |
|---|---|---|
| MATH | Existe (`cero_edicion_no_thinking`) | Falta |
| GSM8K | Falta | Falta |
| IFEval | Falta | Falta |

Los datos sin thinking de GSM8K e IFEval del paper 1 no sirven: usan temperatura 0.7, top_p 0.8 y tope de 8,192 tokens. La temperatura 1.0 sin thinking se agrega en `paper2/scripts/correr_p2.py`, sin tocar el paper 1. Son 20 corridas nuevas y unas 1.5–2.9 h (**supuesto**, a partir de 11.87 min por corrida de MATH a 0.6).

También falta otra referencia: el original con thinking a 0.6 en GSM8K e IFEval tiene 1 semilla. Se completan 3 (4.6 h).

## 4. Diagnóstico ciego
**Cambio (2026-11-06):** el diagnóstico ciego número 1 queda como resultado y no se repiten los ciegos 2 a 4. El brazo (b) pasa a ser "Opus informado": ver `DISENO_INFORMADO.md`. Esta sección describe el ciego número 1.

Esta sesión no puede hacer el diagnóstico. `CLAUDE.md`, la bitácora, el paper y el blog público cuentan el problema, y las capas del MIT (15 y 19). Un subagente también los leería. Tampoco sirve `weight-surgeon`, porque sus instrucciones le piden leer esos archivos.

- **Carpeta aparte:** `<carpeta-aislada>\`, fuera del repositorio. Kit fuente en `paper2/scripts/diag/`.
- **Sesión nueva** con Opus 5.5, modo `--restricted`, sin conectores, sin memoria y sin sesión guardada.
- **Una sola herramienta:** `python herramientas/consultar.py`, con órdenes fijas. No tiene lectura ni escritura de archivos, ni shell libre, ni web. Un filtro externo (`gancho.py`) revisa cada llamada, registra todo y corta a las 150 llamadas.
- **Órdenes:** ver respuestas guardadas, medir activaciones y gradientes, apagar el MLP de una capa, mirar qué predice cada capa y generar hasta 2,048 tokens.
- **Presupuesto:** 50 consultas al modelo, contadas por el motor. Leer respuestas guardadas no gasta consultas.
- **Datos:** 40 problemas de MATH train, fuera de los 1,200, de los 20 de control y de toda evaluación, con la respuesta del original en la config de la línea base.
- **Salida:** `salida/capas.json`, con exactamente 4 capas y sus razones.
- **Auditoría:** `auditar_sesion.py` lista cada llamada y busca texto del proyecto en lo que recibió la sesión.
- **Prompt (se congela antes de correr):**

> Este modelo saca una nota baja en problemas de matemáticas. Investiga por qué con la herramienta `python herramientas/consultar.py` (empieza con `python herramientas/consultar.py ayuda`). Después elige exactamente 4 de sus 24 capas para entrenar un adaptador LoRA en su parte MLP, de modo que mejore esa nota. Tienes 50 consultas al modelo. Registra tu elección y tus razones con la orden `elegir`.

- **Después se reporta** si por sí sola nombró el problema, y si sus capas coinciden con (d) o con las 15 y 19 del MIT.

**Cuántos diagnósticos (decisión 3).** Propongo 4 independientes, uno por semilla. Con uno solo, (b) tendría una única elección de capas frente a 4 sorteos de (c), y no se podría separar "Opus elige bien" de "esa elección tuvo suerte".

## 5. Tarea 2: empresa ficticia

> **Decisión 16 (2026-11-09): esta tarea pasa a trabajo futuro, fuera del paper 2.** Lo que sigue queda como diseño de referencia, sin ejecutarse.
Solo empieza cuando termine la tarea 1. La empresa es la contaduría ficticia del proyecto; la parte legal queda fuera de este plan.

- **Generador:** `paper2/scripts/generar_empresa.py` con semilla fija, sin LLM. Crea socios, oficinas, clientes ficticios, tarifas, plazos y políticas. Antes de fijarlo se comprueba que los nombres no sean de una empresa real.
- **Datos:** unos 120 hechos con 8 plantillas por hecho (**supuesto**, unos 1,000 ejemplos), en inglés para comparar con los otros conjuntos.
- **Evaluación, unas 300 preguntas:**
  - Plantillas nunca vistas de hechos entrenados.
  - Preguntas que combinan dos hechos.
  - Preguntas sobre datos que no existen, donde lo correcto es decir que no se sabe. Mide cuánto inventa.
- **Calificación:** por script, con coincidencia exacta normalizada.
- **Olvido:** MATH, GSM8K e IFEval, comparados con el modelo sin entrenar.
- **Modo:** no-thinking (decisión 4). En thinking, el original entra en bucles y cada celda costaría unos 43 minutos.
- **Brazos:** los mismos 4, con los mismos parámetros, 4 semillas, 2 temperaturas. (d) y (b) se calculan otra vez sobre estos datos.

## 6. Análisis (fijado antes de ver resultados)
- **Comparación principal:** (b) contra (c) y (b) contra (d), en precisión de MATH, por temperatura.
- **Comparación obligatoria con apagar el thinking:** cada brazo contra el original sin thinking, en cada tarea y temperatura. Aparece en todas las tablas y figuras de bucles.
- **Secundaria:** (b) contra (a).
- **Estadística:** bootstrap por problema con las 4 semillas, McNemar pareado y corrección de Holm.
- **Regla:** "guiado gana" solo si (b) supera a (c) y a (d), tras Holm, en las dos temperaturas. Si gana en una sola, se reporta como evidencia parcial. Aunque gane, si no supera a apagar el thinking hay que decirlo con la misma claridad.
- **Lo que se puede detectar:** con datos reales del paper 1, una diferencia pareada tiene un IC de ±4 a ±6 puntos, y hace falta una diferencia de unos **6 a 9 puntos** para detectarla el 80% de las veces (`plan_diferencia_detectable.csv`). Si la diferencia real es menor, el estudio no la distinguirá, y un empate no probará que sean iguales.
- **Un resultado probable:** que todas las capas funcionen parecido, porque los datos pesan más que el lugar. Sería un hallazgo válido.

## 7. Orden y puntos de parada

| Fase | Qué se hace | Horas de GPU | Origen |
|---|---|---|---|
| P0 | Entorno `venv-lora` y piloto: VRAM, velocidad, fusión, 20 problemas | 2–4 | supuesto |
| P2a | Diagnóstico ciego número 1 | Parte de P2 | supuesto |
| P1 | Generar datos | 5.3 | tiempo medido; rendimiento supuesto |
| P1b | Prueba barata: 1 LoRA con todos los datos, en los 20 de control | 0.5–0.7 | supuesto |
| **Parada 1b** | | | |
| P2b | Diagnósticos ciegos 2 a 4 y gradientes | 1–2 (con P2a) | supuesto |
| P3 | Entrenar 16 LoRA | 5.1–11.9 | supuesto (velocidad sin medir) |
| P4 | Evaluar MATH, 32 celdas | 20.7–28.6 | medido |
| P4b | Apagar el thinking: MATH a 1.0 | 0.8–1.6 | supuesto |
| **Parada 2** | | | |
| P5 | Evaluar GSM8K e IFEval | 15.8–44.0 | medido |
| P6 | 3 semillas extra del original | 4.6 | medido |
| P6b | Apagar el thinking: GSM8K e IFEval, 2 temperaturas | 0.7–1.3 | supuesto |
| E | Empresa: entrenar, evaluar, referencia | 5.5–8.3 | supuesto |
| | **Total** | **62–112 h** | |

- **Parada 1 (tras P0 y los primeros 100 problemas de P1):** si no cabe en memoria o el rendimiento es muy bajo, recalculo y te consulto.
- **Orden tras la parada 1 (decidido por el usuario):** primero el diagnóstico ciego número 1, para saber pronto si Opus encuentra los bucles sin pista; después la generación de datos. La empresa sigue después de la tarea 1.
- **Parada 1b (tras P1b):** antes de entrenar los 16 LoRA se revisa si este LoRA reduce las respuestas al límite o usa el cierre. Si no cambia nada, se rediseña la receta contigo.
- **Parada 2 (cambiada el 2026-11-07, decisión 15: tras (a) a 0.6 con las 4 semillas, no tras P4b):** si (a) no baja el % al límite al menos 20 puntos a 0.6 (de 92.25%), la receta falló. No se gasta más en P5 y se rediseña.
- **Rango de evaluación:** el extremo bajo supone que los LoRA terminan como p50c; el alto, que siguen en bucle como el original.

**En calendario:** hasta la parada 2 son 35–53 h. Con unas 10 h por noche (**supuesto**), todo son unas 6 a 11 noches.

**Disco:** 32 modelos fusionados de 1.7 GB son unos 54 GB; hay 1.5 TB libres.

## 8. Uso del plan de Claude
No tengo un medidor del plan, así que esto es un **supuesto**, no una medición.

| Trabajo | Modelo | Uso aproximado |
|---|---|---|
| Scripts, colas, análisis | Sonnet | 6–10 sesiones medianas |
| Diagnósticos ciegos (4 + 4) | Opus | 8 sesiones con tope de turnos; es lo más caro |
| Lectura de resultados | Opus, solo si es difícil | 1–2 sesiones |
| Paper, blog e hilo | Sonnet | 4–6 sesiones |

En total, unas 19–26 sesiones, repartidas en 2 a 3 semanas para no chocar con los límites del plan Pro. Mientras corre la GPU no se gasta plan. Tras el primer diagnóstico vuelvo a estimar con el uso real. Con 1 diagnóstico por tarea en vez de 4 se ahorran 6 sesiones de Opus.

## 9. Decisiones del usuario (2026-11-06)
1. **Datos de bucles:** cortar y cerrar sobre MATH de entrenamiento.
2. **Capas y parámetros:** 4 capas con rango 48, solo MLP, frente a 24 capas con rango 8.
3. **Diagnósticos:** 4 independientes por tarea.
4. **Empresa:** evaluación solo en no-thinking.
5. **Referencia:** se agregan las 3 semillas del original a 0.6.
6. **Gasto de GPU:** aceptado, con parada tras P4b. El OK fue a 60–109 h; con la referencia nueva son 62–112 h.
7. **Apagar el thinking:** referencia en todas las comparaciones de bucles.
8. **Citas de doubleAI:** el paper cita solo lo visible en el blog, no los comentarios del HTML.
9. **Presupuesto:** aceptado el aumento a 62–112 h.
10. **Pérdida:** solo en la frase de cierre y la respuesta.
11. **Orden:** tras la parada 1 va el diagnóstico ciego número 1 y luego P1.
12. **Prueba barata:** tras P1, 1 LoRA con todos los ejemplos, probado en los 20 de control antes de los 16.
13. **Opción A:** el ciego 1 queda como resultado; (b) pasa a "Opus informado". Sustituye a la decisión 3; su número de sesiones se decide en `DISENO_INFORMADO.md`.
14. **Regla de calificación (2026-11-07, antes de cualquier evaluación del paper 2):** la respuesta final es el texto tras el **último** `</think>`. Con thinking, sin `</think>` = incorrecta. Sin thinking, todo el texto si no hay `</think>`. MATH y GSM8K: última caja, con math-verify como el MIT; sin caja = incorrecta. IFEval: corrector oficial sobre esa respuesta. Igual para todos los brazos y referencias: las del paper 1 se recalificaron con `scripts/recalificar_referencias.sh` en `resultados/calificacion/` (46 corridas; solo 2 cambian, ±1 problema, ambas de IFEval). Código: `scripts/calificacion.py`, usado por `correr_p2.py`. Métrica nueva en cada CSV: `cierres` y `varios_cierres` (más de un `</think>`).
15. **Cambios de diseño de P3/P4 por presupuesto de GPU (2026-11-07, antes de ver cualquier resultado de P3):** (i) la temperatura principal es 0.6; la 1.0 pasa a secundaria y solo se evalúa en la referencia (original sin thinking, P4b) y en el mejor brazo según 0.6 (regla en `scripts/mejor_brazo.py`: mayor % de correctas, media de las 4 semillas, entre los 6 brazos; empate: menor % al límite). Las 4 semillas no cambian. (ii) Orden: primero el brazo (a), 4 semillas, entrenar y evaluar a 0.6; ahí se aplica la parada 2 (bajar al menos 20 puntos el % al límite desde 92.25%, media de las 4 semillas: PASA si es ≤ 72.25%); solo si pasa se siguen los otros 20 LoRA. La parada 2 deja de ir "tras P4b". (iii) La cola se puede parar y seguir por pedazos sin perder nada (`scripts/cola_p3.py`). (iv) (a) semilla 0 se entrena de nuevo (no se reutiliza P1b) y se compara con P1b como prueba de reproducibilidad. (v) El brazo MIT de 2 capas queda fuera. (vi) Asignación de las sesiones informadas a las semillas del brazo (b): semilla 0 ← sesión 4, 1 ← sesión 1, 2 ← sesión 2, 3 ← sesión 3. Salvedad: el diseño solo decía "cada semilla usa una sesión"; la correspondencia la elegí yo al lanzar las sesiones (`serie.log`: 13:14 y 13:34 del 2026-11-07, antes de sus resultados) y no estaba escrita como regla hasta este commit; al elegirla conocía las capas de las sesiones 1 y 2. No depende de ningún resultado de entrenamiento ni de evaluación. (vii) Referencias confirmadas con la regla de la decisión 14 sobre los mismos 100 problemas fijos: original con thinking, 92.25% de respuestas al límite a 0.6 y 17.75% de correctas a 1.0 (`resultados/calificacion/math_orig_think_T06_s0-3.csv` y `T10_s0-3.csv`).
16. **Alcance de P5, P6 y la empresa (2026-11-09, tras la etapa 3 y antes de lanzar P5/P6):** (i) Entra **P5a**: GSM8K (subconjunto 1) e IFEval (100) en los 24 LoRA a 0.6, thinking, 32,768 tokens, semilla de muestreo = semilla del LoRA, para medir transferencia y olvido. (ii) Entra **P6**: 3 semillas extra (1, 2 y 3) del original CON thinking a 0.6 en GSM8K e IFEval (la semilla 0 ya existe). (iii) Entra **P6b solo a 0.6**: original SIN thinking (`p2_nothink_T06`, 32,768 tokens) en GSM8K e IFEval, semillas 0–3. (iv) **Sale P5b** (GSM8K e IFEval a 1.0 en el mejor brazo), por la decisión 15 (la 1.0 solo se evaluó en MATH). (v) **La empresa (E1–E5, §5) pasa a trabajo futuro, fuera del paper 2**, por presupuesto de GPU y porque la pregunta principal ya está respondida en MATH; `generar_empresa.py` no se escribe en este paper. (vi) Orden de la cola (etapa 4 de `scripts/cola_p3.py`): P6b, P5a, P6. (vii) Antes de la cola, prueba corta con 2 problemas de GSM8K y 2 de IFEval en un LoRA, para confirmar que `correr_p2.py` califica bien (regla de la decisión 14). Estimado en `resultados/plan_etapa4.csv`.

## 10. Piloto (listo, sin lanzar)
`paper2/scripts/cola_piloto.sh`, unas 2–4 h (**supuesto**). Se detiene al primer error, sin reintentos:

1. Fijar los problemas de MATH train (1,200 y 20 de control), sin solaparse con evaluación.
2. Medir memoria y velocidad con tokens al azar.
3. Cortar y cerrar en el bloque 00 (100 problemas).
4. Armar el dataset.
5. Entrenar un LoRA de prueba.
6. Fusionarlo y medir cuánto del parche sobrevive a bf16.
7. Probarlo en vLLM con los 20 de control.
8. Correr el original en esos mismos 20.

No usa ningún problema de evaluación. El adaptador de prueba se descarta, y sus 20 problemas solo comprueban que todo funcione: no miden el efecto. Al terminar llega la **parada 1**.
