"""Análisis de la etapa 2 de P3 (6 brazos x 4 semillas, MATH-100 fijo, temperatura 0.6). Sin GPU, solo Python estándar.
Uso (desde paper2/): python scripts/analisis_etapa2.py
Pruebas fijadas en PLAN.md §6 antes de ver resultados: bootstrap por problema con las 4 semillas, McNemar pareado y Holm.
Cómo se agregan las 4 semillas (convención del proyecto, igual que scripts/analisis_ronda3.py del paper 1):
  - % del brazo = media de las 400 respuestas (100 problemas x 4 semillas).
  - IC 95% del brazo y de las diferencias: bootstrap por problema (se remuestrean los 100 problemas con sus 4 semillas;
    10,000 remuestras, random.Random(20261107), percentiles 2.5 y 97.5). Diferencias pareadas por problema.
  - IC por semilla (una corrida de 100): Wilson 95%.
  - McNemar exacto bilateral sobre parejas (problema, semilla): semilla s de X con semilla s de Y (400 parejas).
  - Holm dentro de cada familia (columna 'familia'). Lo que el PLAN no fijó va con estado = EXPLORATORIO.
Escribe en resultados/p3/: etapa2_por_semilla.csv, etapa2_por_brazo.csv, etapa2_comparaciones.csv."""
import csv, math, random
from collections import defaultdict

P3 = "resultados/p3"
IDS = [l.strip() for l in open("../datos/math500_subset100_ids.txt", encoding="utf-8") if l.strip() and not l.startswith("#")]
NOMBRE = {"a": "(a) normal 24 capas", "b": "(b) Opus informado", "c": "(c) placebo al azar", "d": "(d) automatico gradiente",
          "e": "(e) automatico barrido", "f": "(f) Opus + barrido", "T": "original con thinking (ref.)", "N": "original sin thinking (ref.)"}
CAPAS = defaultdict(dict)
for r in csv.DictReader(open("resultados/p3_lista_lora.csv", encoding="utf-8")):
    CAPAS[r["brazo"]][int(r["semilla"])] = r["capas"].replace(";", " ")


def cargar(b, s):
    if b == "T": f = f"resultados/calificacion/math_orig_think_T06_s{s}.csv"
    elif b == "N": f = f"resultados/calificacion/math_orig_nothink_T06_s{s}.csv"
    else: f = f"{P3}/eval/{b}{s}_T06_s{s}.csv"
    X = {r["id"]: r for r in csv.DictReader(open(f, encoding="utf-8"))}
    assert sorted(X) == sorted(IDS), f"{f}: ids distintos del subconjunto fijo"
    assert all(r.get("error_calificacion", "0") in ("0", "") for r in X.values()), f"{f}: error de calificación"
    return X


BR = "abcdefTN"
D = {b: {s: cargar(b, s) for s in range(4)} for b in BR}
M = {"correctas": "correcto", "al_limite": "llego_limite"}


def mat(b, m):  # 100 x 4 (0/1)
    return [[int(D[b][s][i][M[m]]) for s in range(4)] for i in IDS]


def wilson(k, n, z=1.959964):
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return round(100 * (c - h), 2), round(100 * (c + h), 2)


def boot(v):  # v: valor por problema; IC de la media
    R = random.Random(20261107); n = len(v)
    bs = sorted(sum(v[R.randrange(n)] for _ in range(n)) / n for _ in range(10000))
    return round(100 * bs[249], 2), round(100 * bs[9749], 2)


def mcnemar(x, y):
    b = sum(1 for i in range(100) for s in range(4) if x[i][s] == 1 and y[i][s] == 0)
    c = sum(1 for i in range(100) for s in range(4) if x[i][s] == 0 and y[i][s] == 1)
    n = b + c
    if n == 0: return b, c, 1.0
    p = 2 * sum(math.comb(n, k) for k in range(min(b, c) + 1)) / 2 ** n
    return b, c, min(1.0, p)


# 1) por semilla
f1 = []
for b in BR:
    for s in range(4):
        X = list(D[b][s].values()); n = len(X)
        k = sum(int(r["correcto"]) for r in X); L = sum(int(r["llego_limite"]) for r in X)
        f1.append(dict(brazo=b, nombre=NOMBRE[b], semilla=s, capas=CAPAS[b].get(s, "-") if b in "abcdef" else "-", n=n,
                       correctas=k, pct_correctas=round(100 * k / n, 2), ic95_corr_bajo=wilson(k, n)[0], ic95_corr_alto=wilson(k, n)[1],
                       pct_al_limite=round(100 * L / n, 2), ic95_lim_bajo=wilson(L, n)[0], ic95_lim_alto=wilson(L, n)[1],
                       tokens_medios=round(sum(int(r["tokens"]) for r in X) / n, 1),
                       pct_varios_cierres=round(100 * sum(int(r["cierres"]) > 1 for r in X) / n, 2)))

# 2) por brazo (4 semillas juntas)
f2 = []
for b in BR:
    fila = dict(brazo=b, nombre=NOMBRE[b], n=400)
    for m in M:
        x = mat(b, m); v = [sum(r) / 4 for r in x]
        lo, hi = boot(v); por_sem = [100 * sum(x[i][s] for i in range(100)) / 100 for s in range(4)]
        fila.update({f"pct_{m}": round(100 * sum(v) / 100, 2), f"ic95_{m}_bajo": lo, f"ic95_{m}_alto": hi,
                     f"{m}_min_semilla": min(por_sem), f"{m}_max_semilla": max(por_sem)})
    X = [r for s in range(4) for r in D[b][s].values()]
    fila["tokens_medios"] = round(sum(int(r["tokens"]) for r in X) / 400, 1)
    fila["pct_varios_cierres"] = round(100 * sum(int(r["cierres"]) > 1 for r in X) / 400, 2)
    f2.append(fila)

# 3) comparaciones por familias
FIJ, EXP = "FIJADA_EN_PLAN", "EXPLORATORIO"
FAM = [
    ("principal_PLAN6", FIJ, "correctas", [("b", "c"), ("b", "d")]),
    ("secundaria_PLAN6", FIJ, "correctas", [("b", "a")]),
    ("vs_sin_thinking_PLAN6", FIJ, "correctas", [(b, "N") for b in "abcdef"]),
    ("vs_a_pedida_usuario", EXP, "correctas", [(b, "a") for b in "bcdef"]),
    ("vs_a_pedida_usuario", EXP, "al_limite", [(b, "a") for b in "bcdef"]),
    ("centrales_no_fijadas", EXP, "correctas", [("f", "c"), ("d", "c"), ("e", "c"), ("f", "d"), ("f", "e")]),
    ("al_limite_4capas", EXP, "al_limite", [("b", "c"), ("b", "d"), ("f", "c"), ("d", "c"), ("e", "c"), ("f", "d"), ("f", "e")]),
]
f3 = []
for fam, est, m, pares in FAM:
    filas = []
    for X, Y in pares:
        x, y = mat(X, m), mat(Y, m)
        d = [(sum(x[i]) - sum(y[i])) / 4 for i in range(100)]
        lo, hi = boot(d); b_, c_, p = mcnemar(x, y)
        filas.append(dict(familia=fam, estado=est, metrica=m, X=X, Y=Y, comparacion=f"{NOMBRE[X]} - {NOMBRE[Y]}",
                          pct_X=round(100 * sum(map(sum, x)) / 400, 2), pct_Y=round(100 * sum(map(sum, y)) / 400, 2),
                          dif_puntos=round(100 * sum(d) / 100, 2), ic95_bajo=lo, ic95_alto=hi,
                          solo_X=b_, solo_Y=c_, p_mcnemar=round(p, 5)))
    # Holm
    orden = sorted(range(len(filas)), key=lambda k: filas[k]["p_mcnemar"]); prev = 0
    for r, k in enumerate(orden):
        prev = max(prev, min(1.0, (len(filas) - r) * filas[k]["p_mcnemar"])); filas[k]["p_holm"] = round(prev, 5)
    for fl in filas:
        fl["tamano_familia"] = len(filas); fl["sobrevive_holm_0.05"] = "si" if fl["p_holm"] < 0.05 else "no"
    f3 += filas


def guardar(nom, F):
    with open(f"{P3}/{nom}", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(F[0].keys())); w.writeheader(); w.writerows(F)


guardar("etapa2_por_semilla.csv", f1); guardar("etapa2_por_brazo.csv", f2); guardar("etapa2_comparaciones.csv", f3)
for r in f2: print(r)
for r in f3: print(r["familia"], r["estado"], r["metrica"], r["X"], r["Y"], r["dif_puntos"], (r["ic95_bajo"], r["ic95_alto"]), r["solo_X"], r["solo_Y"], r["p_mcnemar"], r["p_holm"], r["sobrevive_holm_0.05"])
