"""Resume el piloto y responde las preguntas de la parada 1. Sin GPU. Uso: python resumir_piloto.py <carpeta_piloto>"""
import csv, json, os, sys

R = sys.argv[1]
leer = lambda n: list(csv.DictReader(open(f"{R}/{n}", encoding="utf-8")))
print("# Resumen del piloto\n\n## Memoria y velocidad (tokens al azar)\n")
print("| Brazo | Pérdida | Largo | Resultado | VRAM pico (GB) | tok/s |\n|---|---|---|---|---|---|")
for f in leer("memoria.csv"):
    print(f"| {f['brazo']} | {f['perdida']} | {f['largo']} | {f['resultado']} | {f['vram_pico_gb']} | {f['tok_por_s']} |")

m = json.load(open(f"{R}/datos_b00_B_s0.csv.meta.json"))
d = json.load(open(f"{os.path.dirname(os.path.dirname(R))}/datos/piloto_lora.jsonl.resumen.json"))
print("\n## Datos (bloque 00, problemas de train)\n")
print(f"- Correctas: {m['correctos']} de {m['problemas']}, en {m['segundos'] / 60:.1f} min.")
print(f"- Ejemplos útiles: {d['ejemplos']} ({d['forzadas']} forzadas, {d['naturales']} naturales); "
      f"fuera por largo: {d['descartadas_por_largo']}.")
print(f"- Proyección a 1,200 problemas: unos {12 * d['ejemplos']} ejemplos (el plan suponía unos 400).")

e = json.load(open(f"{R}/entrenamiento.json"))
print("\n## Entrenamiento de prueba\n")
print(f"- {e['ejemplos']} ejemplos, {e['pasos']} pasos, {e['tok_por_s']} tok/s, VRAM pico {e['vram_pico_gb']} GB.")
print(f"- Pérdida {e['perdida_inicial']} → {e['perdida_final']}. Parámetros {e['parametros']:,}.")
horas = 12 * d["tokens_totales"] / e["tok_por_s"] / 3600 * 16
print(f"- Proyección P3 (16 modelos, 1 época con los datos proyectados): {horas:.1f} h. El plan suponía 5.1–11.9 h.")

f = leer("fusion.csv")
print("\n## Fusión\n")
print(f"- Fracción del parche conservada tras bf16: mínima {min(float(x['fraccion_parche_conservada']) for x in f):.3f}.")
print(f"- ‖ΔW‖/‖W‖ tras fusionar: máxima {max(float(x['dw_w_despues']) for x in f):.4g}.")

print("\n## 20 problemas de control (no son de evaluación; solo revisan que todo funcione)\n")
print("| Modelo | Correctas | Al límite | Tokens medios |\n|---|---|---|---|")
for n, nombre in (("control_original_s0.csv", "Original"), ("control_lora_s0.csv", "LoRA de prueba")):
    x = leer(n)
    print(f"| {nombre} | {sum(int(r['correcto']) for r in x)} de {len(x)} | {sum(int(r['llego_limite']) for r in x)} | "
          f"{sum(int(r['tokens']) for r in x) / len(x):.0f} |")
print("\nCon 20 problemas y un adaptador entrenado con pocos ejemplos, esto no mide el efecto: solo indica si la tubería funciona.")
