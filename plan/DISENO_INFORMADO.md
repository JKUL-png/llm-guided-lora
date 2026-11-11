# Diseño del brazo "Opus informado" (aprobado el 2026-11-06, sin lanzar)

**Decisión del usuario (2026-11-06):** el diagnóstico ciego número 1 queda como resultado ("encuentra los bucles sin pista") y no se repiten los ciegos 2 a 4. El brazo (b) pasa a ser "Opus informado". Sus capas 16, 17, 20 y 21 no se entrenan.

**Qué pregunta responde ahora (b):** si un modelo fuerte conoce el problema y la evidencia previa, y además puede medir, ¿elige mejores capas que el azar y que la regla de gradientes? Ya no prueba si descubre el problema solo.

## 1. Contexto
Texto completo en `scripts/diag/contexto_informado.md`, unas 650 palabras. Se entrega con la orden gratis `contexto`.

**Incluye:** la receta fija, cómo se medirá y resúmenes del blog del MIT, del paper 1 y del blog de doubleAI. De doubleAI, solo lo visible en el blog.

**No incluye:**
- Ningún problema, respuesta oficial o respuesta del modelo de los conjuntos de evaluación; solo números agregados. `revisar_contexto.py` lo comprueba.
- Las capas del diagnóstico ciego ni las del brazo automático.
- Los sorteos del placebo ni el resultado de P1b.
- Los resultados de las otras sesiones informadas.

## 2. Herramientas
Las mismas del ciego, con estos cambios:

| Orden | Cambio |
|---|---|
| `contexto` | Nueva, gratis |
| `generar` | Hasta 32,768 tokens, varias muestras y varios problemas por llamada: `generar --problemas 1,10,35 --muestras 4 [--temperatura 0.6/1.0] [--apagar-capa L]` |
| `ver-muestra ID --desde C --hasta D` | Nueva, gratis: lee una muestra generada |

- `generar` devuelve por muestra: tokens, si cerró `</think>`, si terminó y si acertó.
- Corre en vLLM. Apagar una capa se hace en una copia temporal con `down_proj` en cero, que equivale a apagar la salida de su MLP.
- Solo usa los 40 problemas del diagnóstico, nunca evaluación.
- Hasta 16 muestras por llamada.

**Por construir y probar antes de lanzar:** tiempo máximo de la herramienta (cada llamada larga dura unos 11 min, y el Bash de la sesión corta a los 10 por defecto); `elegir` con aviso de caracteres permitidos y razones más largas; saldo y semilla propios por sesión. Se repiten las pruebas de la jaula.

## 3. Presupuesto, igual en todas las sesiones
- **50 consultas cortas:** activaciones, gradientes, apagar, lente.
- **160 muestras largas:** cada muestra de `generar` gasta 1.
- **150 llamadas** como máximo, igual que en el ciego.
- Mismo contexto y mismo prompt. Solo cambia la semilla de `generar`. Sesiones independientes, sin memoria.

Con 160 muestras caben unas 10 pruebas de 16. Cada una da una estimación gruesa: con 16 muestras, una tasa de 50% tiene un margen de unos ±24 puntos. Sirve para ver efectos grandes, no finos.

## 4. Prompt (borrador)
> Lee el contexto con `python herramientas/consultar.py contexto` y las órdenes con `python herramientas/consultar.py ayuda`. Investiga con esas herramientas. Después elige exactamente 4 de las 24 capas de este modelo para entrenar el LoRA descrito en el contexto, de modo que corrija los bucles y mejore la nota a temperaturas 0.6 y 1.0, sin dañar lo demás. Tienes 50 consultas cortas y 160 muestras largas. Registra tu elección y tus razones con la orden `elegir`.

## 5. Cuántos diagnósticos
**Propuesta: 2, y 2 más solo si no coinciden.** Regla fijada antes de ver resultados:
- Si las 2 primeras sesiones comparten al menos 3 de 4 capas: se termina. La sesión 1 va a las semillas 0 y 1, y la 2 a las semillas 2 y 3.
- Si comparten 2 o menos: se corren las sesiones 3 y 4, y cada semilla usa una sesión.

| Sesiones | Uso del plan (equivalente en dólares, supuesto) | GPU (supuesto) |
|---|---|---|
| 2 | Unos 5 | Unas 4 h |
| 4 | Unos 10 | Unas 8 h |

La base es lo medido en el ciego: 82 turnos, 1,190 s, 23,019 tokens de salida y 1.19 dólares equivalentes. Supongo el doble por sesión, por el contexto y las lecturas largas. Ese valor es lo que costaría por API; el plan Pro no cobra así y no sé cuánto de su límite representa. Tras la sesión 1 reviso el uso real antes de seguir.

## 6. Lo que hay que reportar
- **Anclaje:** el contexto nombra las capas 15 y 19. Si Opus las elige, puede ser por haberlas leído. Se reporta cuántas coinciden y si lo justificó con mediciones propias.
- **Ventaja de información y de cómputo:** (b) recibe contexto y unas 2 h de GPU por sesión; (c) y (d) no. Se reporta, porque es parte del costo real de "guiado".
- **Coincidencia con (d):** se reporta. El gradiente también está disponible como herramienta.
- **Diagnóstico ciego:** va al paper como resultado aparte, con el matiz de que la tabla de tokens muestra el síntoma.

## 7. Orden
1. Revisar P1b (parada 1b). Si la receta no funciona, no vale la pena gastar en los diagnósticos.
2. Construir y probar la versión informada de la jaula.
3. Calcular las capas de (d) con 256 ejemplos, antes de las sesiones informadas.
4. Sesión 1, revisar uso real, sesión 2, aplicar la regla.
