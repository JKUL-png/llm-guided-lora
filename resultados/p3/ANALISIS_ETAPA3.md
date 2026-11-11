# Análisis de la etapa 3 (temperatura 1.0, MATH-100 fijo, 4 semillas)
Pruebas del PLAN §6 (bootstrap por problema, McNemar pareado, Holm). Script: `scripts/analisis_etapa3.py`. Datos: `etapa3_por_semilla.csv`, `etapa3_por_brazo.csv`, `etapa3_comparaciones.csv`.

| Qué | Correctas % [IC95] | Al límite % [IC95] | Varios `</think>` % |
|---|---|---|---|
| (e) automático por barrido, a 1.0 | 54.25 [46.5, 61.75] | 0.25 [0.0, 0.75] | 30.0 |
| Original sin thinking, a 1.0 | 51.5 [44.25, 58.75] | 1.0 [0.25, 2.0] | 0.0 |
| Original con thinking, a 1.0 | 17.75 [12.25, 24.0] | 82.25 [76.0, 87.75] | 0.25 |

| Comparación | Estado | Dif. (puntos) [IC95] | Solo X / solo Y | p McNemar | ¿Sobrevive Holm? |
|---|---|---|---|---|---|
| (e) − sin thinking, correctas | **FIJADA EN PLAN** (§6, "cada brazo contra el original sin thinking") | +2.75 [−3.5, +9.0] | 69 / 58 | 0.375 | no |
| (e) − sin thinking, al límite | EXPLORATORIO | −0.75 [−2.0, +0.25] | 1 / 4 | 0.375 | no |
| (e) − con thinking, correctas | EXPLORATORIO (pedida por el usuario tras ver la etapa 2) | +36.5 [+29.75, +43.5] | 153 / 7 | <0.000001 | sí |
| (e) − con thinking, al límite | EXPLORATORIO | −82.0 [−87.75, −75.75] | 0 / 328 | <0.000001 | sí |

Notas: (1) la familia de Holm de cada fila tiene 1 comparación (solo se evaluó (e) a 1.0), así que p corregido = p. (2) (e) a 1.0 no supera a apagar el thinking: la diferencia (+2.75) cae dentro del ruido. (3) Contra el original con thinking a 1.0 la mejora es enorme, porque ese original llega al límite en el 82% de las respuestas. (4) A 0.6 la diferencia de (e) con apagar el thinking fue +6.75 (IC [+1.5, +12.0]) con p corregido 0.056 (etapa 2). (5) Con 100 problemas hacen falta unos 6–9 puntos para detectar una diferencia; que no aparezca no prueba que sean iguales. (6) (e) incluye la capa 0, que pudo entrar por dañar todo el modelo (BITACORA). (7) En (e) a 1.0 el 30% de las respuestas tiene varios `</think>`, y en el original sin thinking no existen.
