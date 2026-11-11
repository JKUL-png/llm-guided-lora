# Análisis de la etapa 2 de P3: 6 brazos de LoRA a temperatura 0.6 (2026-11-09)

Datos: 24 LoRA (6 brazos × 4 semillas) evaluados en los 100 problemas fijos de MATH
(`datos/math500_subset100_ids.txt`), modo thinking, temperatura 0.6, tope 32,768 tokens.
Scripts: `scripts/analisis_etapa2.py`, `scripts/cierres_por_problema_todos.py`, `scripts/metrica_cierres.py`,
`scripts/mejor_brazo.py` (sin modificar). Todo es cálculo en CPU; no se usó la GPU.
CSV: `etapa2_por_semilla.csv`, `etapa2_por_brazo.csv`, `etapa2_comparaciones.csv`, `cierres_por_brazo.csv`,
`cierres_por_problema_todos.csv`, `cierres_por_problema_todos_resumen.csv`, `mejor_brazo.csv`.

## Palabras que se usan aquí
- **IC 95% (intervalo de confianza):** el rango donde probablemente está el valor real. Si es ancho, sabemos poco.
- **Bootstrap por problema:** se sortean 100 problemas con reemplazo (10,000 veces, semilla 20261107) y se mira cuánto
  cambia el resultado. Da el IC. Se sortea el problema entero con sus 4 semillas, porque las 4 respuestas al
  mismo problema se parecen entre sí.
- **McNemar pareado:** compara dos brazos solo en los casos donde uno acierta y el otro falla, en el mismo problema
  y la misma semilla (400 parejas). Da un **valor p**: qué tan raro sería ver esa diferencia si los dos brazos fueran iguales.
- **Holm:** si hago varias pruebas a la vez, alguna sale "significativa" por suerte. Holm sube los valores p para
  corregir eso. "Sobrevive a Holm" = p corregido < 0.05.
- **EXPLORATORIO:** cálculo que el PLAN no fijó antes de ver resultados. Sirve para generar ideas, no para concluir.

## Qué estaba fijado en el PLAN (§6 y decisión 15) y qué no
- **Fijado:** comparación principal (b) vs (c) y (b) vs (d) en % de correctas (familia de Holm de 2); secundaria
  (b) vs (a); obligatoria: cada brazo vs el original sin thinking (familia de 6). Estadística: bootstrap por
  problema con las 4 semillas, McNemar pareado, Holm. Regla: "guiado gana" solo si (b) supera a (c) **y** a (d)
  tras Holm en las dos temperaturas. Mejor brazo para 1.0: `mejor_brazo.py`.
- **Cómo se juntan las 4 semillas** (el PLAN no lo detalla; uso la convención del paper 1, `scripts/analisis_ronda3.py`):
  % del brazo = media de las 400 respuestas; McNemar sobre parejas (problema, semilla s de X con semilla s de Y).
- **Las familias de Holm** son mi lectura del PLAN (que solo dice "Holm"): la principal (2) y "vs sin thinking" (6).
- **EXPLORATORIO:** todo lo demás: (c)–(f) vs (a), todo el % al límite entre brazos, (f) vs (c), (d) vs (c),
  (e) vs (c), (f) vs (d), (f) vs (e), y el análisis de cierres por problema. ((f) vs (e) lo motiva
  `DISENO_BARRIDO.md` §3, pero sin prueba ni familia fijadas.)

## Tabla 1. Cada brazo, las 4 semillas juntas (n = 400)
| Brazo | Correctas % [IC95] | Rango por semilla | Al límite % [IC95] | Tokens medios | Varios cierres % |
|---|---|---|---|---|---|
| (a) normal 24 capas | 45.5 [37.8, 53.3] | 40–53 | 2.5 [1.0, 4.3] | 4,179 | 17.8 |
| (b) Opus informado | 54.0 [46.5, 61.5] | 51–58 | 10.5 [7.0, 14.3] | 7,554 | 39.3 |
| (c) placebo al azar | 55.5 [47.5, 63.5] | 53–57 | 6.0 [3.8, 8.8] | 6,266 | 18.5 |
| (d) automático gradiente | 51.3 [43.8, 58.8] | 46–54 | 9.5 [5.8, 13.8] | 7,344 | 29.5 |
| (e) automático barrido | 58.5 [50.5, 66.3] | 57–60 | 5.8 [3.3, 8.5] | 6,140 | 21.8 |
| (f) Opus + barrido | 52.0 [44.3, 59.5] | 47–55 | 6.5 [3.8, 9.5] | 6,586 | 27.0 |
| Ref.: original con thinking | 7.8 [4.0, 12.0] | 6–9 | 92.3 [88.0, 96.0] | 30,770 | 0.0 |
| Ref.: original sin thinking | 51.8 [44.0, 59.3] | 49–57 | 12.0 [7.8, 16.5] | 7,955 | 0.0 |

(El PLAN decía 51.5% para el original sin thinking; con la recalificación de la decisión 14 da 51.75%.)

## Tabla 2. Por semilla (IC Wilson en `etapa2_por_semilla.csv`)
| Brazo | Semilla | Capas | Correctas | Al límite % | Tokens medios | Varios cierres % |
|---|---|---|---|---|---|---|
| (a) | 0 / 1 / 2 / 3 | las 24 | 53 / 40 / 49 / 40 | 6 / 3 / 0 / 1 | 5,091 / 4,347 / 3,801 / 3,479 | 33 / 15 / 15 / 8 |
| (b) | 0 | 11 15 19 22 | 51 | 12 | 7,166 | 37 |
| (b) | 1 | 14 19 22 23 | 51 | 18 | 10,364 | 48 |
| (b) | 2 | 12 15 17 20 | 58 | 6 | 6,734 | 37 |
| (b) | 3 | 10 14 15 22 | 56 | 6 | 5,952 | 35 |
| **(c) placebo** | **0** | **1 2 4 20** | **55** | **7** | **6,217** | **21** |
| **(c) placebo** | **1** | **12 14 18 21** | **57** | **13** | **8,578** | **40** |
| **(c) placebo** | **2** | **7 9 10 14** | **57** | **2** | **5,752** | **6** |
| **(c) placebo** | **3** | **1 5 9 15** | **53** | **2** | **4,516** | **7** |
| (d) | 0 / 1 / 2 / 3 | 10 14 15 23 | 51 / 54 / 54 / 46 | 9 / 12 / 10 / 7 | 7,310 / 8,504 / 7,176 / 6,388 | 40 / 31 / 26 / 21 |
| (e) | 0 / 1 / 2 / 3 | 0 10 12 15 | 57 / 57 / 60 / 60 | 6 / 8 / 5 / 4 | 6,078 / 6,754 / 6,181 / 5,547 | 25 / 23 / 16 / 23 |
| (f) | 0 / 1 | 10 14 15 17 | 52 / 55 | 5 / 10 | 6,015 / 8,089 | 34 / 28 |
| (f) | 2 / 3 | 10 14 15 18 | 54 / 47 | 4 / 7 | 5,884 / 6,356 | 22 / 24 |

El placebo (c) tiene **capas distintas en cada semilla** (sorteo fijado antes, `random.Random(20261106 + s)`).
Aun así sus 4 semillas dan 53–57 correctas: cuatro grupos de capas al azar funcionaron casi igual.
En % al límite sí varía (2% a 13%; EXPLORATORIO, solo descriptivo).

## Tabla 3. Comparaciones FIJADAS en el PLAN (% de correctas, diferencia en puntos)
| Comparación | Diferencia [IC95] | Gana X / gana Y | p | p Holm | ¿Sobrevive? |
|---|---|---|---|---|---|
| (b) − (c) — principal | −1.5 [−6.3, +3.3] | 43 / 49 | 0.60 | 0.60 | no |
| (b) − (d) — principal | +2.8 [−2.3, +8.0] | 52 / 41 | 0.30 | 0.60 | no |
| (b) − (a) — secundaria | +8.5 [+3.5, +13.8] | 62 / 28 | 0.0004 | 0.0004 | **sí** |
| (a) − sin thinking | −6.3 [−12.8, 0.0] | 45 / 70 | 0.025 | 0.12 | no |
| (b) − sin thinking | +2.3 [−3.0, +7.3] | 52 / 43 | 0.41 | 1.00 | no |
| (c) − sin thinking | +3.8 [−1.5, +9.0] | 50 / 35 | 0.13 | 0.51 | no |
| (d) − sin thinking | −0.5 [−6.3, +5.3] | 51 / 53 | 0.92 | 1.00 | no |
| (e) − sin thinking | +6.8 [+1.5, +12.0] | 64 / 37 | 0.009 | 0.056 | no (por poco) |
| (f) − sin thinking | +0.3 [−4.8, +5.3] | 49 / 48 | 1.00 | 1.00 | no |

**Regla del PLAN: "guiado gana" NO se cumple.** Opus informado (b) no supera al placebo (c) (incluso queda 1.5 puntos
abajo) ni a la regla de gradiente (d). Además, la temperatura 1.0 solo se evaluará en el mejor brazo, así que la
parte "en las dos temperaturas" de la regla no se podrá comprobar para (b) vs (c) y (d).
**Ningún brazo supera a apagar el thinking tras Holm.** El que más se acerca es (e).

## Tabla 4. Brazos de 4 capas contra (a) — pedida por el usuario, EXPLORATORIO (Holm dentro de las 5 de cada métrica)
| Brazo − (a) | Correctas: dif. [IC95] | p Holm | Al límite: dif. [IC95] | p Holm |
|---|---|---|---|---|
| (b) | +8.5 [+3.5, +13.8] | 0.001 | +8.0 [+4.5, +11.8] | <0.0001 |
| (c) | +10.0 [+5.0, +15.5] | 0.0004 | +3.5 [+1.0, +6.0] | 0.021 |
| (d) | +5.8 [+1.0, +10.5] | 0.038 | +7.0 [+3.3, +11.3] | 0.0001 |
| (e) | +13.0 [+8.3, +17.8] | <0.0001 | +3.3 [+0.8, +6.0] | 0.024 |
| (f) | +6.5 [+1.0, +12.0] | 0.038 | +4.0 [+1.3, +7.0] | 0.021 |

Todas sobreviven a Holm: los brazos de 4 capas (rango 48) aciertan más que (a) (24 capas, rango 8), **pero también
llegan más al límite**. Recordar que (a) difiere en capas y en rango a la vez (PLAN §2), así que esto no aísla "dónde".

## Tabla 5. Otras comparaciones centrales — EXPLORATORIO (Holm dentro de cada bloque)
| Comparación | Correctas: dif. [IC95] | p Holm (5) | Al límite: dif. [IC95] | p Holm (7) |
|---|---|---|---|---|
| (b) − (c) | (ver tabla 3) | – | +4.5 [+1.0, +8.3] | 0.12 |
| (b) − (d) | (ver tabla 3) | – | +1.0 [−2.8, +4.8] | 1.00 |
| (f) − (c) | −3.5 [−8.5, +1.3] | 0.52 | +0.5 [−2.8, +3.8] | 1.00 |
| (d) − (c) | −4.3 [−9.8, +1.3] | 0.43 | +3.5 [−0.3, +7.5] | 0.32 |
| (e) − (c) | +3.0 [−1.8, +7.8] | 0.52 | −0.3 [−3.3, +2.5] | 1.00 |
| (f) − (d) | +0.8 [−3.8, +5.3] | 0.83 | −3.0 [−7.3, +1.3] | 0.74 |
| (f) − (e) | **−6.5 [−11.0, −2.3]** | **0.033** | +0.8 [−2.3, +4.0] | 1.00 |

Lo único que sobrevive: **(e) barrido automático acierta más que (f) Opus + barrido** (+6.5 puntos). Es decir, con la
misma tabla de mediciones, la regla automática eligió capas que funcionaron mejor que las que eligió Opus al leerla.
Es EXPLORATORIO (comparación no fijada) y (e) incluye la capa 0 (ver advertencias).

## Mejor brazo (`mejor_brazo.py`, sin modificar)
Orden por % de correctas: **(e) 58.5%**, (c) 55.5, (b) 54.0, (f) 52.0, (d) 51.25, (a) 45.5. **Elegido: (e).**
La regla elige al de mayor media aunque la diferencia con el segundo, (c), esté dentro del ruido (+3.0 [−1.8, +7.8]).
No se creó `OK_USUARIO_etapa3` ni se lanzó nada.

## Cierres por problema — EXPLORATORIO
"Varios cierres" = la respuesta escribe `</think>` más de una vez. Para separarlo de la dificultad, en cada
problema donde unas semillas cerraron una vez y otras varias se compara su acierto (`cierres_por_problema_todos_resumen.csv`):

| Brazo | Problemas mixtos | Un cierre − varios [IC95] | Gana un cierre / varios / empates |
|---|---|---|---|
| (a) | 43 | −0.047 [−0.155, +0.066] | 5 / 9 / 29 |
| (b) | 55 | **+0.145 [+0.012, +0.285]** | 20 / 12 / 23 |
| (c) | 48 | −0.024 [−0.142, +0.090] | 9 / 11 / 28 |
| (d) | 61 | +0.052 [−0.052, +0.159] | 16 / 15 / 30 |
| (e) | 48 | +0.045 [−0.090, +0.184] | 13 / 12 / 23 |
| (f) | 47 | −0.014 [−0.117, +0.092] | 8 / 12 / 27 |
| los 6 juntos | 302 | +0.031 [−0.017, +0.082] | 71 / 71 / 160 |

En general, **dentro del mismo problema cerrar varias veces no acierta menos** (juntos: +0.03, IC incluye 0;
71 contra 71). La brecha grande de la tabla por semilla se explica sobre todo por dificultad. Solo en (b) el IC
queda apenas por encima de 0; con 6 brazos mirados sin corrección, es esperable que uno salga así por azar.
(b) es además el brazo con más respuestas de varios cierres (39%).

## Advertencias ya registradas en BITACORA
- **(d) y (f) comparten 3 de 4 capas** (10, 14, 15). No se distinguen (+0.8 [−3.8, +5.3]); no se puede decir que
  Opus + barrido aporte algo sobre la regla de gradiente.
- **La capa 0 en (e) puede haber entrado por dañar todo el modelo**, no por algo propio del cierre. (e) es el mejor
  brazo y el que gana a (f): eso puede deberse a la capa 0 o a la 12, y no lo podemos separar con estos datos.
- **El "cierre natural"** con que Opus descartó la capa 0 en (f) salió de solo **3 respuestas**: una señal frágil.
- La asignación de sesiones de (b) a semillas la eligió el investigador al lanzar (decisión 15, punto vi).

## Qué NO se puede concluir
- **100 problemas por celda y diferencias pequeñas: el IC manda.** Con este tamaño hace falta una diferencia de
  unos 6 a 9 puntos para verla (PLAN §6). (b) vs (c) y (b) vs (d) son de −1.5 y +2.8: el estudio **no las puede
  distinguir**, y eso **no prueba que sean iguales**; solo que, si hay diferencia, es pequeña.
- No se puede decir que Opus elija mejores capas que el azar: el placebo (c) quedó igual o un poco arriba.
- No se puede decir que algún brazo de LoRA supere a simplemente apagar el thinking (51.75%), que no cuesta nada.
  (e) se acerca (+6.8) pero no sobrevive a Holm.
- "4 capas > 24 capas" no se puede atribuir a la elección de capas: también cambia el rango (48 vs 8).
- Que (e) gane a (f) es exploratorio y está mezclado con la duda de la capa 0.
- Solo temperatura 0.6, solo MATH; GSM8K, IFEval y la temperatura 1.0 aún no se miden en estos brazos.
- El análisis de cierres por problema es descriptivo; no dice que los cierres causen aciertos o fallos.
- Lo visto es **compatible** con el "resultado probable" que anticipó el PLAN (las capas pesan poco; los datos pesan más), pero un empate no lo prueba.
