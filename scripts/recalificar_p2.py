"""Recalifica con la regla del paper 2 (calificacion.py) una corrida ya guardada, sin GPU. Correr en ~/venv-vllm (WSL).
No toca la entrada: escribe un CSV nuevo con las columnas de la entrada más
  correcto_primer_cierre (la nota original), correcto (regla del paper 2), cierres, varios_cierres.
Uso: python recalificar_p2.py <entrada.csv> <salida.csv> <math|gsm8k|ifeval> <ids_file> <problemas.jsonl>
(ids_file y problemas.jsonl: nombre dentro de datos/ de la raíz o ruta absoluta)"""
import csv, json, os, sys
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import calificacion as C
from comun_math import cargar_problemas

entrada, salida, tarea, ids_file, jsonl = sys.argv[1:6]
assert os.path.abspath(entrada) != os.path.abspath(salida)
assert not os.path.exists(salida), "la salida ya existe; no se sobrescribe"
probs = {p["id"]: p for p in cargar_problemas(ids_file, jsonl)}
textos = {j["id"]: j["texto"] for j in map(json.loads, open(entrada + ".jsonl", encoding="utf-8"))}
filas = list(csv.DictReader(open(entrada, encoding="utf-8")))
cambios = 0
for r in filas:
    t, pensando = textos[r["id"]], r["modo"] == "thinking"
    r["correcto_primer_cierre"] = r["correcto"]
    try:
        r["correcto"] = int(C.calificar(probs[r["id"]], t, pensando, tarea))
    except Exception:
        r["correcto"] = 0; r["error_calificacion"] = 1
    r["cierres"] = C.cierres(t); r["varios_cierres"] = int(r["cierres"] > 1)
    cambios += int(r["correcto"]) != int(r["correcto_primer_cierre"])
os.makedirs(os.path.dirname(os.path.abspath(salida)), exist_ok=True)
with open(salida, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(filas[0].keys())); w.writeheader(); w.writerows(filas)
print(json.dumps(dict(entrada=os.path.basename(entrada), n=len(filas), correctos_antes=sum(int(r["correcto_primer_cierre"]) for r in filas),
                      correctos_regla_p2=sum(int(r["correcto"]) for r in filas), cambios=cambios,
                      varios_cierres=sum(r["varios_cierres"] for r in filas))), flush=True)
