"""Prueba sin GPU de preparar_math_train, armar_dataset_lora y resumir_piloto, en una carpeta temporal.
Usa textos con forma real pero marcados como inventados; nada de esto se entrena. Uso: python prueba_datos.py <carpeta_temporal>"""
import csv, json, os, subprocess, sys
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from comun_lora import CIERRE, leer_jsonl

T = sys.argv[1]
D, R = f"{T}/datos", f"{T}/resultados/piloto"
os.makedirs(D, exist_ok=True); os.makedirs(R, exist_ok=True)

subprocess.run([sys.executable, f"{AQUI}/preparar_math_train.py", D], check=True)
xs = leer_jsonl(f"{D}/math_train_1200.jsonl")
ctl = leer_jsonl(f"{D}/math_control20.jsonl")
b0 = [l.strip() for l in open(f"{D}/math_train_bloque00_ids.txt")]
assert len(xs) == 1200 and len(ctl) == 20 and len(b0) == 100
assert not {x["id"] for x in xs} & {x["id"] for x in ctl}
assert all(x["answer"] and x["id"].startswith("train/") for x in xs)
print("ejemplo:", xs[0]["id"], "nivel", xs[0]["level"], "respuesta", xs[0]["answer"][:30])

# corrida simulada: 1 forzada correcta, 1 natural correcta, 1 incorrecta, 1 forzada sin marca
def corrida(nombre, ids):
    campos = ["id", "correcto", "forzado", "tokens"]
    textos = [f"Pensando. {CIERRE} Fin.\n</think>\n\n\\boxed{{1}}", "Pienso.\n</think>\n\n\\boxed{2}", "x", "sin marca"]
    meta = [("1", "1"), ("1", "0"), ("0", "1"), ("1", "1")]
    with open(nombre, "w", newline="", encoding="utf-8") as h:
        w = csv.writer(h); w.writerow(campos)
        for i, (c, f) in zip(ids, meta):
            w.writerow([i, c, f, 10])
    with open(nombre + ".jsonl", "w", encoding="utf-8") as h:
        for i, t in zip(ids, textos):
            h.write(json.dumps(dict(id=i, texto=t, corte="stop")) + "\n")

c = f"{R}/datos_b00_B_s0.csv"
corrida(c, b0[:4])
json.dump(dict(correctos=3, problemas=4, segundos=120.0), open(c + ".meta.json", "w"))
salida = f"{D}/piloto_lora.jsonl"
subprocess.run([sys.executable, f"{AQUI}/armar_dataset_lora.py", salida, "16384", c], check=True)
ej = leer_jsonl(salida)
assert [e["tipo"] for e in ej] == ["forzada", "natural"], [e["tipo"] for e in ej]
assert ej[0]["salida"].startswith(CIERRE) and ej[1]["salida"].startswith("</think>")
assert all(e["salida"].endswith("<|im_end|>\n") for e in ej)
assert ej[0]["prompt"].rstrip().endswith("<think>"), repr(ej[0]["prompt"][-30:])

# un problema de evaluación debe detener el proceso
c2 = f"{R}/mala_B_s0.csv"
corrida(c2, ["test/algebra/1082.json"] + b0[1:4])
r = subprocess.run([sys.executable, f"{AQUI}/armar_dataset_lora.py", f"{D}/malo.jsonl", "16384", c2], capture_output=True, text=True)
assert r.returncode != 0 and "evaluación" in (r.stderr + r.stdout), r.stderr[-300:]
print("rechaza problemas de evaluación: sí")

# resumen con archivos simulados
open(f"{R}/memoria.csv", "w").write("brazo,perdida,largo,resultado,vram_pico_gb,tok_por_s\n4capas_r48,salida,2048,ok,3.1,2500\n")
json.dump(dict(ejemplos=2, pasos=1, tok_por_s=2000, vram_pico_gb=5.0, perdida_inicial=2.0, perdida_final=1.5, parametros=2654208),
          open(f"{R}/entrenamiento.json", "w"))
open(f"{R}/fusion.csv", "w").write("tensor,dw_w_antes,dw_w_despues,pct_pesos_cambiados,fraccion_parche_conservada\na,0.01,0.01,50,0.9\n")
for n in ("control_original_s0.csv", "control_lora_s0.csv"):
    open(f"{R}/{n}", "w").write("correcto,llego_limite,tokens\n1,0,100\n0,1,32768\n")
subprocess.run([sys.executable, f"{AQUI}/resumir_piloto.py", R], check=True, stdout=subprocess.DEVNULL)
print("PRUEBA DATOS OK")
