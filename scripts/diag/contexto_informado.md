# Contexto para el diagnóstico

## Tu tarea en este estudio
Qwen3.5-0.8B, en modo thinking, suele entrar en bucles de razonamiento hasta agotar el límite de 32,768 tokens. Queremos corregirlo con un LoRA. Tu trabajo es elegir dónde ponerlo.

**Receta fija, que no puedes cambiar:**
- LoRA solo en la parte MLP (gate, up, down) de exactamente 4 capas, rango 48, 2,654,208 parámetros entrenables.
- Unos 380 ejemplos del propio modelo, de problemas de entrenamiento de MATH. Cuando el modelo entra en bucle, el texto se recorta en la primera copia, se agrega una frase de cierre y `</think>`, y el modelo contesta. Solo se conservan las respuestas correctas, más algunas que terminaron solas.
- La pérdida cuenta solo en la frase de cierre y la respuesta; el pensamiento previo se lee, pero no se entrena.
- Una época, tasa de aprendizaje 2e-4.

**Cómo se medirá:** precisión y % de respuestas al límite en MATH, GSM8K e IFEval, con thinking, a temperaturas 0.6 y 1.0. También importa no dañar lo que ya funciona.

## Resumen del blog del MIT ("Sparks of Weight-Space Programming", experimento 8)
Un modelo de frontera (Astra) leyó y editó los pesos de Qwen3.5-0.8B sin gradientes, con 10, 25 o 50 pases hacia adelante. El prompt era "Make Qwen3.5-0.8B better at math".

- **Diagnóstico que reportan:** rastreó el bucle hasta "one direction written by the MLPs of layers 15 and 19".
- **Edición:** restó esa dirección de 64 columnas de salida en cada capa (unos 131,000 pesos, 0.016% del modelo).
- **Resultados con temperatura 0.6:** MATH-500 de 7.9% a 48.1%, GSM8K de 13.8% a 67.1%, IFEval de 21.0% a 62.3%; respuestas al límite de 93.0% a 33.1%.
- **Según el presupuesto:** con 10 y 25 pases los bucles casi no bajaron; solo bajaron con 50.
- **Su conclusión:** editar puede "remove an obstacle that hid an ability", pero no agrega una capacidad que el modelo no tiene.

## Resumen del paper 1 ("Decomposing the Gain")
Auditoría de ese resultado, con 100 problemas fijos y 4 semillas, en números agregados.

- **Réplica:** 7.8% sin editar y 51.2% con la edición, a temperatura 0.6.
- **Apagar el thinking:** 51.5% sin tocar pesos, con el mismo límite de tokens. Sin thinking, la edición no agrega nada (51.5% contra 51.5%).
- **Especificidad:** una edición aleatoria del mismo tamaño, en los mismos tensores y columnas, da 11.0%. La edición real no es una perturbación cualquiera.
- **Temperatura:** a 1.0 la ganancia en MATH baja de 43.5 a 11.0 puntos, porque el modelo editado vuelve a entrar en bucle. Una solución encontrada a 0.6 puede no servir a 1.0.
- **Residuo:** a 0.6 el editado con thinking supera al original sin thinking en GSM8K (+11.6 puntos) y, más débilmente, en IFEval (+6.8). A 1.0 ese residuo desaparece.
- **Cortar y forzar respuesta:** sin tocar pesos, llega a 34% en MATH.
- **Dónde está la ganancia:** en las respuestas que antes entraban en bucle.

## Resumen del blog de doubleAI ("Can LLMs redesign themselves as they train?")
Un agente de programación agrega capas de código durante el entrenamiento de modelos pequeños. No trata sobre Qwen3.5 ni sobre LoRA.

- **Gradiente fantasma:** gradiente de la pérdida respecto de las representaciones internas, por token y por capa. Según ellos, muestra mejor dónde falta ayuda que qué ayuda hace falta, y no predice bien cómo rendirá algo una vez entrenado.
- **Controles:** el twin es la misma corrida con la capa apagada. El sham conserva la capa y revuelve su información, para separar "aporta información" de "solo agrega capacidad".
- **Advertencia útil:** en Qwen3-8B, su política gana 7.0 puntos sobre la base, pero 3.3 sobre un control simple por longitud.

## Avisos
- Apagar un MLP muestra dónde vive un comportamiento, no cuánto mejorará un LoRA.
- Los resúmenes anteriores no dicen qué capas funcionan mejor con esta receta. Nadie lo ha medido.
