"""REVISION EXTERNA (2026-11-10). Sensibilidad a la regla de calificacion cuando hay varios </think>. SIN GPU (solo math-verify en CPU).
Uso (en WSL, desde paper2/): CUDA_VISIBLE_DEVICES= ~/venv-vllm/bin/python resultados/revision/rev_regla_cierre.py
Lee los textos guardados (resultados/p3/eval/*.jsonl) de los 6 brazos LoRA en MATH y GSM8K y los recalifica con 4 reglas. No modifica nada existente.
Reglas:
  L    = regla oficial del paper 2: ultima caja de lo que va tras el ULTIMO </think>. Debe reproducir la columna 'correcto' de los CSV.
  P1   = regla del paper 1: ultima caja de TODO lo que va tras el PRIMER </think>.
  SEG1 = primera respuesta que dio el modelo: ultima caja del tramo entre el primer </think> y el segundo (o el final).
  ANY  = techo: correcta si la ultima caja de CUALQUIER tramo tras un </think> es correcta (no es una regla usable; mide cuanto se pierde).
El original sin thinking (N) no tiene </think>, asi que su calificacion no cambia: se toma del CSV.
Escribe resultados/revision/rev_regla_cierre_items.csv y rev_regla_cierre_resumen.csv."""
import os, sys, csv, json, math, random
os.environ.setdefault("PROYECTO_RAIZ", "/workspace/proyecto")
sys.path.insert(0, "/workspace/proyecto/scripts")
from comun_math import ultima_caja
from math_verify import parse, verify
P3 = "resultados/p3"; OUT = "resultados/revision"; BS = "\\"; TAG = "</think>"
CACHE = {}


def ok(gold, pred):
    if pred is None: return 0
    k = (gold, pred)
    if k not in CACHE:
        try: CACHE[k] = int(bool(verify(parse(BS + "boxed{" + gold + "}"), parse(BS + "boxed{" + pred + "}"))))
        except Exception: CACHE[k] = 0
    return CACHE[k]


def reglas(texto, gold):
    if TAG not in texto: return dict(L=0, P1=0, SEG1=0, ANY=0)
    tr = texto.split(TAG)[1:]
    return dict(L=ok(gold, ultima_caja(tr[-1])), P1=ok(gold, ultima_caja(texto.split(TAG, 1)[1])), SEG1=ok(gold, ultima_caja(tr[0])),
                ANY=int(any(ok(gold, ultima_caja(x)) for x in tr)))


def boot(v):
    Rg = random.Random(20261107); n = len(v)
    bs = sorted(sum(v[Rg.randrange(n)] for _ in range(n)) / n for _ in range(10000))
    return round(100 * bs[249], 2), round(100 * bs[9749], 2)


def signos(D):
    obs = abs(sum(D)); dist = {0: 1.0}
    for d in D:
        if d == 0: continue
        nd = {}
        for k, p in dist.items():
            nd[k + d] = nd.get(k + d, 0) + p / 2; nd[k - d] = nd.get(k - d, 0) + p / 2
        dist = nd
    return min(1.0, sum(p for k, p in dist.items() if abs(k) >= obs))


items, res = [], []
for t, pref, idf, nfile in (("math", "", "math500", "resultados/calificacion/math_orig_nothink_T06_s{s}.csv"), ("gsm8k", "p5_gsm8k_", "gsm8k", P3 + "/eval/p6b_gsm8k_orig_nothink_T06_s{s}.csv")):
    I = [l.strip() for l in open(f"../datos/{idf}_subset100_ids.txt", encoding="utf-8") if l.strip() and not l.startswith("#")]
    GOLD = {}
    for l in open(f"../datos/{idf}_subset100.jsonl", encoding="utf-8"):
        p = json.loads(l); GOLD[p["id"]] = p["answer"]
    M = {}   # M[regla][brazo] = [problema][semilla]
    for b in "abcdef":
        per = {r: [[0] * 4 for _ in I] for r in ("L", "P1", "SEG1", "ANY")}
        for s in range(4):
            f = f"{P3}/eval/{pref}{b}{s}_T06_s{s}.csv"
            C = {r["id"]: r for r in csv.DictReader(open(f, encoding="utf-8"))}
            T = {}
            for l in open(f + ".jsonl", encoding="utf-8"):
                j = json.loads(l); T[j["id"]] = j["texto"]
            for i, pid in enumerate(I):
                g = reglas(T[pid], GOLD[pid]); n = T[pid].count(TAG)
                for r in per: per[r][i][s] = g[r]
                items.append(dict(tarea=t, brazo=b, semilla=s, id=pid, cierres=n, correcto_csv=C[pid]["correcto"], **g))
        for r in per: M.setdefault(r, {})[b] = per[r]
    N = [[0] * 4 for _ in I]
    for s in range(4):
        C = {r["id"]: r for r in csv.DictReader(open(nfile.format(s=s), encoding="utf-8"))}
        for i, pid in enumerate(I): N[i][s] = int(C[pid]["correcto"])
    for r in ("L", "P1", "SEG1", "ANY"):
        for b in "abcdef":
            v = [sum(x) / 4 for x in M[r][b]]; lo, hi = boot(v)
            res.append(dict(tarea=t, regla=r, tipo="brazo", X=b, Y="", valor=round(sum(v), 2), ic95_bajo=lo, ic95_alto=hi, p_signos_exacta=""))
        for X, Y in [("b", "c"), ("b", "d"), ("b", "a"), ("e", "b"), ("f", "e")] + [(b, "N") for b in "abcdef"]:
            x = M[r][X]; y = N if Y == "N" else M[r][Y]
            di = [sum(x[i]) - sum(y[i]) for i in range(100)]; lo, hi = boot([k / 4 for k in di])
            res.append(dict(tarea=t, regla=r, tipo="diferencia", X=X, Y=Y, valor=round(sum(di) / 4, 2), ic95_bajo=lo, ic95_alto=hi, p_signos_exacta=round(signos(di), 6)))
for nom, F in (("rev_regla_cierre_items.csv", items), ("rev_regla_cierre_resumen.csv", res)):
    with open(f"{OUT}/{nom}", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(F[0].keys())); w.writeheader(); w.writerows(F)
mal = sum(int(r["correcto_csv"]) != r["L"] for r in items)
print("items:", len(items), "| regla L distinta del CSV original:", mal)
mc = [r for r in items if r["cierres"] > 1]
print("con varios cierres:", len(mc), "| L correcta:", sum(r["L"] for r in mc), "| SEG1 correcta:", sum(r["SEG1"] for r in mc), "| ANY:", sum(r["ANY"] for r in mc),
      "| L=1,SEG1=0:", sum(r["L"] and not r["SEG1"] for r in mc), "| L=0,SEG1=1:", sum(r["SEG1"] and not r["L"] for r in mc))
for r in res:
    if r["tipo"] == "brazo" or (r["X"], r["Y"]) in (("b", "c"), ("b", "d"), ("b", "a"), ("e", "N")): print(r["tarea"], r["regla"], r["tipo"], r["X"], r["Y"], r["valor"], r["ic95_bajo"], r["ic95_alto"], r["p_signos_exacta"])
