# Diseño: brazo "Opus + barrido" (propuesta del 2026-11-07, sin lanzar)

**Qué pregunta responde:** si a Opus se le quita el trabajo de medir y se le da una medición
completa y con intervalos, ¿elige capas mejores (o más estables) que cuando mide él solo?
Separa dos cosas que hoy van juntas en el brazo (b): **medir** e **interpretar**.

Motivo: las sesiones informadas 1 y 2 no compartieron ninguna capa. Cada una midió poco
(6 a 16 muestras por condición) y leyó señales ruidosas a su manera.

## 1. El barrido (lo hace el sistema; Opus no lo controla)
- **Datos:** las 37 respuestas de diagnóstico que llegan al límite (`motor/datos/respuestas.jsonl`,
  las mismas 40 del ciego y del informado). Ningún problema de evaluación.
- **Fragmentos (fijados antes de medir):** en cada respuesta, el detector del paper 1 (ventana final de
  300 caracteres repetida 3 o más veces en los últimos 6,000) marca dónde empieza el bucle.
  - Punto principal: **el corte de la primera copia**, el mismo punto donde la receta P1b corta y agrega la frase de cierre.
  - Más 7 puntos al final de un párrafo (`\n\n`), repartidos parejo dentro de la zona del bucle. Si no hay 7 párrafos, al final de una línea (`\n`). (Corregido en la prueba en CPU: dentro de los bucles casi no hay párrafos.)
  - Total: 37 × 8 = **296 fragmentos**. Contexto de cada uno: el prompt y los últimos 8,192 tokens antes del punto.
- **Condiciones:** el modelo normal y el modelo con el MLP de cada una de las 24 capas apagado, de dos maneras:
  - **en cero**, igual que en las sesiones;
  - **por la media**, donde la salida del MLP se reemplaza por su promedio. Esto comprueba que el resultado no sea solo por el golpe de dejarla en cero.
  - Son 1 + 24 × 2 = 49 condiciones.
- **Qué se mide en cada fragmento y condición** (solo pasadas hacia adelante, sin generar):
  1. **Principal:** cambio en log P(`</think>`) como siguiente token.
  2. Cambio en log P de la frase de cierre completa de P1b ("Okay, I have thought about this enough." + `</think>`). Es justo lo que entrena el LoRA.
  3. Cambio en log P de los 32 tokens reales que siguen. Mide cuánto sostiene cada capa la repetición.
- **Intervalos:** media por capa con un IC del 95% por bootstrap (10,000 remuestreos) **por problema**, porque los 8 fragmentos de una misma respuesta no son independientes. Se agrega el % de fragmentos donde sube y las cuentas separadas para el punto principal.
- **Control positivo:** las 3 respuestas que sí cierran solas, medidas en su `</think>` real. Sirve para ver qué capas sostienen un cierre natural (3 problemas: solo descriptivo).
- **Salida:** `resultados/barrido/barrido.csv` (una fila por capa, variante y métrica) y una tabla corta para Opus.

## 2. La sesión de Opus (solo interpreta)
- Recibe el **mismo contexto** que el informado, para que lo único que cambie sea de dónde viene la evidencia, y además la tabla del barrido.
- **Sin herramientas de medición ni GPU.** Lee la tabla y elige 4 capas con razones. Sigue en `<carpeta-aislada>`, aislada y con el gancho; la única orden permitida es `elegir`.
- Riesgo de anclaje: el contexto sigue nombrando las capas 15 y 19. Se reporta, igual que en (b).

## 3. Control nuevo que hace falta: (e) "barrido automático"
- Las 4 capas con mayor |cambio medio| en la métrica principal, con apagado en cero. Regla fijada ahora.
- **Sin este control no se puede saber si Opus aporta algo:** si Opus elige las mismas 4, su interpretación no agrega nada sobre la tabla.
- Elegir no cuesta nada. Si las capas difieren de las de Opus, es un LoRA más por semilla en P3.

## 4. Cuántas sesiones
- La misma regla 2 + 2, fijada antes de ver nada: 2 sesiones; si comparten 3 o más de 4 capas, se para (la 1 va a las semillas 0 y 1, la 2 a las 2 y 3). Si no, 4 sesiones, una por semilla.
- Como la evidencia es la misma para todas, la diferencia entre sesiones mide solo cuánto varía la interpretación. Ese dato se compara con el de (b).

## 5. Costo (supuestos, sin medir)
| Parte | GPU | Plan |
|---|---|---|
| Barrido (una vez, sirve para todas las sesiones) | 296 × 49 ≈ 14,500 pasadas de unos 8,300 tokens; con caché para las dos continuaciones, unas **2 h** (rango 1.5 a 4 h) | 0 |
| Sesión de Opus (cada una) | 0 | Unos 0.2 a 0.4 USD equivalentes: lee unos 30k tokens y escribe unos 5k, en pocos turnos |
| 2 sesiones / 4 sesiones | 0 | Unos 0.5 / 1.5 USD |
| LoRA extra de (e) y de este brazo en P3 | 2 brazos × 4 semillas × (entrenar + evaluar) | 0 |

- Comparado con (b): una sesión informada gastó unos 75 a 90 min de GPU y 0.65 a 0.83 USD. Aquí la GPU se gasta una sola vez y cada sesión es barata.
- El tiempo por pasada es una suposición: un modelo de 0.8B con unos 8k tokens tardaría unos 0.3 a 0.5 s en la 5060 Ti. Antes de la cola habría que medirlo con una prueba corta de 1 fragmento y 2 condiciones (segundos de GPU, con OK).

## 6. Orden (todo antes de entrenar cualquier LoRA)
1. Escribir el código y probarlo en CPU con un modelo de juguete (sin GPU).
2. Prueba de tiempo (OK del usuario).
3. Cola del barrido (OK del usuario; proceso oculto, sin reintentos).
4. Fijar (e) con la regla de la sección 3.
5. 2 sesiones de Opus y luego la regla 2 + 2 (OK del usuario).
6. Recién entonces, P3 con todos los brazos: a, b, c, d, e y "Opus + barrido".

## 7. Límites
- Apagar una capa muestra dónde vive una conducta, no cuánto ayudará un LoRA ahí.
- Un cambio en log P(`</think>`) dentro de un bucle puede ser muy chico en valor absoluto (P ≈ 0). Por eso se dan también la frase completa y la continuación.
- 37 problemas: los IC por problema van a ser anchos para capas con efectos chicos.
