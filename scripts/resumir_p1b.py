"""Resume P1 y P1b para la parada 1b. Sin GPU. Compara el LoRA con el original del piloto en los mismos 20 de control."""
import csv, json, os
AQUI = os.path.dirname(os.path.abspath(__file__))
P2 = os.path.dirname(AQUI)
R = f"{P2}/resultados/p1"
PIL = f"{P2}/resultados/piloto"
CIERRE = "Okay, I have thought about this enough."
W, K, L = 300, 3, 6000


def filas(p):
    return list(csv.DictReader(open(p, encoding="utf-8")))


def textos(p):
    return [json.loads(l)["texto"] for l in open(p + ".jsonl", encoding="utf-8")]


def bucle(t):
    c = t[-L:]
    return len(c) >= W and c.count(c[-W:]) >= K


d = json.load(open(f"{P2}/datos/lora_bucles.jsonl.resumen.json"))
e = json.load(open(f"{R}/p1b_entrenamiento.json"))
f = filas(f"{R}/p1b_fusion.csv")
print("# P1 y P1b\n\n## Datos\n")
print(f"- Ejemplos: {d['ejemplos']} ({d['forzadas']} forzadas, {d['naturales']} naturales), de {d['respuestas_vistas']} respuestas.")
print(f"- Fuera por largo: {d['descartadas_por_largo']}. Tokens totales: {d['tokens_totales']:,}.")
print("\n## Entrenamiento\n")
print(f"- {e['pasos']} pasos, {e['segundos'] / 60:.1f} min, {e['tok_por_s']} tok/s, VRAM pico {e['vram_pico_gb']} GB.")
print(f"- Pérdida {e['perdida_inicial']} → {e['perdida_final']}. Parámetros {e['parametros']:,}.")
print(f"- Parche conservado tras bf16: mínimo {min(float(x['fraccion_parche_conservada']) for x in f):.3f}. "
      f"‖ΔW‖/‖W‖ máximo {max(float(x['dw_w_despues']) for x in f):.4g}.")
print("\n## 20 de control (no son evaluación)\n")
print("| Modelo | Correctas | Al límite | Tokens medios | Con cierre | Con </think> | Bucle exacto al final |\n|---|---|---|---|---|---|---|")
for nombre, base in (("Original", f"{PIL}/control_original_s0.csv"), ("LoRA P1b", f"{R}/p1b_control_s0.csv")):
    x, t = filas(base), textos(base)
    print(f"| {nombre} | {sum(int(r['correcto']) for r in x)} de {len(x)} | {sum(int(r['llego_limite']) for r in x)} | "
          f"{sum(int(r['tokens']) for r in x) / len(x):.0f} | {sum(CIERRE in s for s in t)} | {sum('</think>' in s for s in t)} | {sum(bucle(s) for s in t)} |")
