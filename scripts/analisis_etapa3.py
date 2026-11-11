"""Análisis de la etapa 3 de P3 (temperatura 1.0, MATH-100 fijo, 4 semillas). Sin GPU, Python estándar. Uso (desde paper2/): python scripts/analisis_etapa3.py
Mismas pruebas y convenciones que scripts/analisis_etapa2.py (PLAN §6): bootstrap por problema (10,000, random.Random(20261107), percentiles 2.5/97.5),
McNemar exacto bilateral sobre parejas (problema, semilla), Wilson por semilla, Holm dentro de cada familia.
Familias:
  - vs_sin_thinking_T10 (FIJADA_EN_PLAN, §6 'cada brazo contra el original sin thinking, en cada tarea y temperatura'): (e) - original sin thinking.
    Solo se evaluó (e) a 1.0 (decisión 15), así que la familia tiene 1 comparación y Holm no cambia el p.
  - vs_con_thinking_T10 (EXPLORATORIO: pedida por el usuario después de ver la etapa 2, no estaba en el PLAN): (e) - original con thinking.
Escribe en resultados/p3/: etapa3_por_semilla.csv, etapa3_por_brazo.csv, etapa3_comparaciones.csv."""
import csv, math, random
P3 = "resultados/p3"
IDS = [l.strip() for l in open("../datos/math500_subset100_ids.txt", encoding="utf-8") if l.strip() and not l.startswith("#")]
NOMBRE = {"e": "(e) automatico barrido a 1.0", "N": "original sin thinking a 1.0 (ref.)", "T": "original con thinking a 1.0 (ref.)"}
RUTA = {"e": lambda s: f"{P3}/eval/e{s}_T10_s{s}.csv", "N": lambda s: f"{P3}/eval/ref_nothink_T10_s{s}.csv",
        "T": lambda s: f"resultados/calificacion/math_orig_think_T10_s{s}.csv"}


def cargar(b, s):
    X = {r["id"]: r for r in csv.DictReader(open(RUTA[b](s), encoding="utf-8"))}
    assert sorted(X) == sorted(IDS), f"{RUTA[b](s)}: ids distintos del subconjunto fijo"
    assert all(r.get("error_calificacion", "0") in ("0", "") for r in X.values())
    return X


D = {b: {s: cargar(b, s) for s in range(4)} for b in "eNT"}
M = {"correctas": "correcto", "al_limite": "llego_limite"}
mat = lambda b, m: [[int(D[b][s][i][M[m]]) for s in range(4)] for i in IDS]


def wilson(k, n, z=1.959964):
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return round(100 * (c - h), 2), round(100 * (c + h), 2)


def boot(v):
    R = random.Random(20261107); n = len(v)
    bs = sorted(sum(v[R.randrange(n)] for _ in range(n)) / n for _ in range(10000))
    return round(100 * bs[249], 2), round(100 * bs[9749], 2)


def mcnemar(x, y):
    b = sum(1 for i in range(100) for s in range(4) if x[i][s] == 1 and y[i][s] == 0)
    c = sum(1 for i in range(100) for s in range(4) if x[i][s] == 0 and y[i][s] == 1)
    n = b + c
    return b, c, (1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, k) for k in range(min(b, c) + 1)) / 2 ** n))


f1, f2, f3 = [], [], []
for b in "eNT":
    for s in range(4):
        X = list(D[b][s].values()); n = len(X); k = sum(int(r["correcto"]) for r in X); L = sum(int(r["llego_limite"]) for r in X)
        f1.append(dict(brazo=b, nombre=NOMBRE[b], semilla=s, n=n, correctas=k, pct_correctas=round(100 * k / n, 2), ic95_corr_bajo=wilson(k, n)[0], ic95_corr_alto=wilson(k, n)[1],
                       pct_al_limite=round(100 * L / n, 2), ic95_lim_bajo=wilson(L, n)[0], ic95_lim_alto=wilson(L, n)[1],
                       tokens_medios=round(sum(int(r["tokens"]) for r in X) / n, 1), pct_varios_cierres=round(100 * sum(int(r["cierres"]) > 1 for r in X) / n, 2)))
    fila = dict(brazo=b, nombre=NOMBRE[b], n=400)
    for m in M:
        x = mat(b, m); v = [sum(r) / 4 for r in x]; lo, hi = boot(v)
        fila.update({f"pct_{m}": round(100 * sum(v) / 100, 2), f"ic95_{m}_bajo": lo, f"ic95_{m}_alto": hi})
    Xs = [r for s in range(4) for r in D[b][s].values()]
    fila["tokens_medios"] = round(sum(int(r["tokens"]) for r in Xs) / 400, 1)
    fila["pct_varios_cierres"] = round(100 * sum(int(r["cierres"]) > 1 for r in Xs) / 400, 2)
    f2.append(fila)
for fam, est, Y in [("vs_sin_thinking_T10", "FIJADA_EN_PLAN", "N"), ("vs_con_thinking_T10", "EXPLORATORIO", "T")]:
    for m in M:
        x, y = mat("e", m), mat(Y, m); d = [(sum(x[i]) - sum(y[i])) / 4 for i in range(100)]
        lo, hi = boot(d); b_, c_, p = mcnemar(x, y)
        f3.append(dict(familia=fam, estado=est if m == "correctas" else "EXPLORATORIO", metrica=m, X="e", Y=Y, comparacion=f"{NOMBRE['e']} - {NOMBRE[Y]}",
                       pct_X=round(100 * sum(map(sum, x)) / 400, 2), pct_Y=round(100 * sum(map(sum, y)) / 400, 2), dif_puntos=round(100 * sum(d) / 100, 2),
                       ic95_bajo=lo, ic95_alto=hi, solo_X=b_, solo_Y=c_, p_mcnemar=round(p, 6), p_holm=round(p, 6), tamano_familia=1,
                       **{"sobrevive_holm_0.05": "si" if p < 0.05 else "no"}))
for nom, F in [("etapa3_por_semilla.csv", f1), ("etapa3_por_brazo.csv", f2), ("etapa3_comparaciones.csv", f3)]:
    with open(f"{P3}/{nom}", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(F[0].keys())); w.writeheader(); w.writerows(F)
for r in f2: print(r)
for r in f3: print(r["familia"], r["estado"], r["metrica"], r["pct_X"], r["pct_Y"], r["dif_puntos"], (r["ic95_bajo"], r["ic95_alto"]), r["solo_X"], r["solo_Y"], r["p_mcnemar"], r["sobrevive_holm_0.05"])
