"""Evaluación del paper 2 en vLLM (~/venv-vllm). Reutiliza correr_vllm_multi.py del paper 1 sin modificarlo:
le agrega las configuraciones que faltan y le cambia la calificación por la regla del paper 2 (calificacion.py).
Mismos argumentos que correr_vllm_multi.py.
Configs: p2_think_T06, p2_think_T10, p2_nothink_T06, p2_nothink_T10.
Todas son BASE_MIT (32,768 tokens); solo cambian la temperatura y el modo.
p2_nothink_T06 es idéntica a la "no_thinking" del paper 1 y p2_think_T10 a "ficha_qwen".
Cada CSV sale con las columnas extra 'cierres' y 'varios_cierres', y el .meta.json con 'regla' y 'varios_cierres'."""
import csv, json, os, sys
os.environ.setdefault("VLLM_USE_FLASHINFER_SAMPLER", "0")   # sin esto vLLM pide nvcc; igual que en el paper 1
sys.path.insert(0, "/workspace/proyecto/scripts")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import correr_vllm_multi as M
import calificacion as C
from comun_math import BASE_MIT

M.CONFIGS.update({
    "p2_think_T06":   dict(BASE_MIT, thinking=True),
    "p2_think_T10":   dict(BASE_MIT, temperature=1.0, thinking=True),
    "p2_nothink_T06": dict(BASE_MIT, thinking=False),
    "p2_nothink_T10": dict(BASE_MIT, temperature=1.0, thinking=False),
})

# Regla del paper 2: respuesta tras el ÚLTIMO </think>.
M.es_correcta = C.es_correcta
M.calificar_ifeval = C.calificar_ifeval

_original = M.correr_semilla


def correr_semilla(llm, tok, probs, P, config, semilla, salida):
    _original(llm, tok, probs, P, config, semilla, salida)
    n = {j["id"]: C.cierres(j["texto"]) for j in map(json.loads, open(salida + ".jsonl", encoding="utf-8"))}
    filas = list(csv.DictReader(open(salida, encoding="utf-8")))
    for r in filas:
        r["cierres"] = n[r["id"]]; r["varios_cierres"] = int(n[r["id"]] > 1)
    with open(salida, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=filas[0].keys()); w.writeheader(); w.writerows(filas)
    meta = json.load(open(salida + ".meta.json"))
    meta.update(regla="ultimo_cierre", varios_cierres=sum(r["varios_cierres"] for r in filas))
    json.dump(meta, open(salida + ".meta.json", "w"))


M.correr_semilla = correr_semilla

if __name__ == "__main__":
    M.main()
