"""Datos de la jaula. Corre en ~/venv-lora. Sin GPU.
  elegir <carpeta>       40 problemas de MATH train, fuera de los 1,200, de los 20 de control y de toda evaluación
  empaquetar <carpeta> <corrida.csv> <salida.jsonl>   une problemas y respuestas para el motor
No sobrescribe."""
import csv, json, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from preparar_math_train import TEMAS, caja, normalizar

RAIZ = "/workspace/proyecto"
SEMILLA, N = 20261108, 40


def elegir(carpeta):
    from datasets import load_dataset
    destino = f"{carpeta}/diag40.jsonl"
    if os.path.exists(destino):
        print("Ya existe:", destino); return
    fuera = set()
    for f in ("math500_full.jsonl", "gsm8k_subset100.jsonl", "gsm8k_subset100b.jsonl"):
        fuera |= {normalizar(json.loads(l)["problem"]) for l in open(f"{RAIZ}/datos/{f}", encoding="utf-8")}
    for f in ("math_train_1200.jsonl", "math_control20.jsonl"):
        fuera |= {normalizar(json.loads(l)["problem"]) for l in open(f"{RAIZ}/paper2/datos/{f}", encoding="utf-8")}
    filas = []
    for t in TEMAS:
        for i, r in enumerate(load_dataset("EleutherAI/hendrycks_math", t, split="train")):
            a = caja(r["solution"])
            if a and a.strip() and r["level"][-1:].isdigit() and normalizar(r["problem"]) not in fuera:
                filas.append(dict(id=f"train/{t}/{i}", level=int(r["level"][-1]), subject=t, problem=r["problem"], answer=a))
    filas.sort(key=lambda x: x["id"])
    random.Random(SEMILLA).shuffle(filas)
    xs = filas[:N]
    os.makedirs(carpeta, exist_ok=True)
    with open(destino, "w", encoding="utf-8") as h:
        for x in xs:
            h.write(json.dumps(x, ensure_ascii=False) + "\n")
    open(f"{carpeta}/diag40_ids.txt", "w").write("\n".join(x["id"] for x in xs) + "\n")
    print("listo:", len(xs), "de", len(filas), "disponibles")


def empaquetar(carpeta, corrida, salida):
    if os.path.exists(salida):
        print("Ya existe:", salida); return
    probs = {x["id"]: x for x in map(json.loads, open(f"{carpeta}/diag40.jsonl", encoding="utf-8"))}
    meta = {r["id"]: r for r in csv.DictReader(open(corrida, encoding="utf-8"))}
    textos = {d["id"]: d["texto"] for d in map(json.loads, open(corrida + ".jsonl", encoding="utf-8"))}
    with open(salida, "w", encoding="utf-8") as h:
        for n, i in enumerate(sorted(probs, key=lambda k: list(probs).index(k)), 1):
            p, r = probs[i], meta[i]
            h.write(json.dumps(dict(n=n, nivel=p["level"], problema=p["problem"], respuesta_oficial=p["answer"], texto=textos[i],
                                    tokens=int(r["tokens"]), correcto=int(r["correcto"])), ensure_ascii=False) + "\n")
    print("empaquetado:", len(probs))


if __name__ == "__main__":
    if sys.argv[1] == "elegir":
        elegir(sys.argv[2])
    else:
        empaquetar(*sys.argv[2:5])
