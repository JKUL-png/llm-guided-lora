"""Crea los problemas FIJOS de entrenamiento desde el train de MATH (EleutherAI/hendrycks_math, licencia MIT).
Sin GPU. Se corre en ~/venv-lora. No sobrescribe; nunca regenerar una vez creados.
Salidas en <carpeta> (por defecto paper2/datos):
  math_train_1200.jsonl     los 1,200 problemas para generar datos, en bloques de 100
  math_train_bloqueNN_ids.txt
  math_control20.jsonl / math_control20_ids.txt   20 problemas aparte, SOLO para revisar el piloto
Se detiene si algún problema coincide con MATH-500 o con los subconjuntos de evaluación.
Uso: python preparar_math_train.py [carpeta]"""
import json, os, random, re, sys
from collections import defaultdict

RAIZ = "/workspace/proyecto"
SEMILLA = 20261107
N, N_CONTROL, BLOQUE = 1200, 20, 100
TEMAS = ["algebra", "counting_and_probability", "geometry", "intermediate_algebra", "number_theory", "prealgebra", "precalculus"]


def normalizar(t):
    return re.sub(r"\s+", "", t).lower()


def caja(sol):
    """Contenido del último \\boxed{...} de la solución oficial, con llaves balanceadas."""
    i = sol.rfind("\\boxed")
    if i < 0:
        return None
    j = sol.find("{", i)
    if j < 0:
        return None
    n = 0
    for k in range(j, len(sol)):
        n += (sol[k] == "{") - (sol[k] == "}")
        if n == 0:
            return sol[j + 1:k]
    return None


def main():
    from datasets import load_dataset
    carpeta = sys.argv[1] if len(sys.argv) > 1 else f"{RAIZ}/paper2/datos"
    destino = f"{carpeta}/math_train_1200.jsonl"
    if os.path.exists(destino):
        print("Ya existe; no regenero:", destino); return
    prohibidos = set()
    for f in ("math500_full.jsonl", "gsm8k_subset100.jsonl", "gsm8k_subset100b.jsonl"):
        for l in open(f"{RAIZ}/datos/{f}", encoding="utf-8"):
            prohibidos.add(normalizar(json.loads(l)["problem"]))
    print("problemas prohibidos:", len(prohibidos))

    filas, sin_caja, sin_nivel, repetidos = [], 0, 0, 0
    for t in TEMAS:
        d = load_dataset("EleutherAI/hendrycks_math", t, split="train")
        for i, r in enumerate(d):
            ans = caja(r["solution"])
            m = re.match(r"Level (\d)", r["level"])
            if not ans or not ans.strip():
                sin_caja += 1; continue
            if not m:
                sin_nivel += 1; continue
            if normalizar(r["problem"]) in prohibidos:
                repetidos += 1; continue
            filas.append(dict(id=f"train/{t}/{i}", level=int(m[1]), subject=t, problem=r["problem"], answer=ans))
    print(f"train: {len(filas)} útiles; sin caja {sin_caja}; sin nivel {sin_nivel}; iguales a evaluación (excluidos) {repetidos}")

    # Muestra estratificada por nivel, proporcional, con semilla fija
    rng = random.Random(SEMILLA)
    por_nivel = defaultdict(list)
    for f in filas:
        por_nivel[f["level"]].append(f)
    total = N + N_CONTROL
    elegidos = []
    for n_ in sorted(por_nivel):
        g = sorted(por_nivel[n_], key=lambda x: x["id"])
        rng.shuffle(g)
        elegidos += g[:round(total * len(g) / len(filas))]
    rng.shuffle(elegidos)
    elegidos = elegidos[:total]
    assert len(elegidos) == total, len(elegidos)
    control, datos = elegidos[:N_CONTROL], elegidos[N_CONTROL:]
    assert not {x["id"] for x in control} & {x["id"] for x in datos}

    os.makedirs(carpeta, exist_ok=True)
    def escribir(ruta, xs):
        with open(ruta, "w", encoding="utf-8") as h:
            for x in xs:
                h.write(json.dumps(x, ensure_ascii=False) + "\n")
    escribir(destino, datos)
    escribir(f"{carpeta}/math_control20.jsonl", control)
    open(f"{carpeta}/math_control20_ids.txt", "w", encoding="utf-8").write("\n".join(x["id"] for x in control) + "\n")
    for b in range(N // BLOQUE):
        ids = [x["id"] for x in datos[b * BLOQUE:(b + 1) * BLOQUE]]
        open(f"{carpeta}/math_train_bloque{b:02d}_ids.txt", "w", encoding="utf-8").write("\n".join(ids) + "\n")
    niveles = defaultdict(int)
    for x in datos:
        niveles[x["level"]] += 1
    print("listo:", len(datos), "problemas +", len(control), "de control; por nivel:", dict(sorted(niveles.items())))


if __name__ == "__main__":
    main()
