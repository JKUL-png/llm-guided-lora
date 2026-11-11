"""EXPLORATORIO (no está en el PLAN §6; pedido por el usuario el 2026-11-10): PISO DE RUIDO de 'empeora/mejora'.
Para cada modelo (original con/sin thinking; brazos a-f) y tarea (math, gsm8k, ifeval), por problema: cuánto cambia el resultado (correcto/incorrecto)
entre semillas distintas del MISMO modelo. Parejas ordenadas de semillas (s,t), s != t: 12 por problema, 1,200 por modelo.
  - pct_cambia = % de parejas con resultados distintos (ruido de muestreo; en los brazos incluye ADEMÁS la variación del LoRA entre semillas,
    que cambia de semilla: b y c cambian capas, y todos reentrenan).
  - pct_1a0 = % de parejas con (s correcto, t incorrecto) = el 'empeora' esperado por azar; pct_0a1 el 'mejora'.
Luego, para cada brazo contra cada referencia (misma semilla, como cambios_vs_original.py): % que cambia (empeora+mejora) MENOS el piso de ruido del
original en ese modo. IC 95% por bootstrap de problemas (10,000, random.Random(20261107)). Sin Holm: leer el IC.
Uso (desde paper2/): python scripts/ruido_semillas.py     Salida: resultados/p3/ruido_semillas_por_modelo.csv y ruido_vs_cambios.csv
Omite lo que aún no existe (p. ej. el original con thinking de IFEval hasta que termine P6)."""
import csv, os, random
P3 = "resultados/p3"
def ids(t): return [l.strip() for l in open(f"../datos/{ {'math': 'math500', 'gsm8k': 'gsm8k', 'ifeval': 'ifeval'}[t] }_subset100_ids.txt", encoding="utf-8") if l.strip() and not l.startswith("#")]
def ruta(t, m, s):
    if m == "think":
        if t == "math": return f"resultados/calificacion/math_orig_think_T06_s{s}.csv"
        return f"resultados/calificacion/{t}_orig_think_T06_s0.csv" if s == 0 else f"{P3}/eval/p6_{t}_orig_think_T06_s{s}.csv"
    if m == "nothink": return f"resultados/calificacion/math_orig_nothink_T06_s{s}.csv" if t == "math" else f"{P3}/eval/p6b_{t}_orig_nothink_T06_s{s}.csv"
    return f"{P3}/eval/{m}{s}_T06_s{s}.csv" if t == "math" else f"{P3}/eval/p5_{t}_{m}{s}_T06_s{s}.csv"
def cargar(t, m, I):
    fs = [ruta(t, m, s) for s in range(4)]
    if not all(os.path.exists(f) for f in fs): return None
    C = []
    for f in fs:
        X = {r["id"]: r for r in csv.DictReader(open(f, encoding="utf-8"))}
        assert sorted(X) == sorted(I) and all(r.get("error_calificacion", "0") in ("0", "") for r in X.values()), f
        C.append([int(X[i]["correcto"]) for i in I])
    return [[C[s][i] for s in range(4)] for i in range(100)]      # [problema][semilla]
def boot(vec_fn):
    R = random.Random(20261107); q = sorted(vec_fn([R.randrange(100) for _ in range(100)]) for _ in range(10000)); return round(q[249], 2), round(q[9749], 2)
PARES = [(s, u) for s in range(4) for u in range(4) if s != u]
por, vs = [], []
for t in ("math", "gsm8k", "ifeval"):
    I = ids(t); D = {m: cargar(t, m, I) for m in ("think", "nothink", "a", "b", "c", "d", "e", "f")}
    piso = {}
    for m, C in D.items():
        if C is None: continue
        dis = [sum(C[i][s] != C[i][u] for s, u in PARES) for i in range(100)]
        a10 = [sum(C[i][s] == 1 and C[i][u] == 0 for s, u in PARES) for i in range(100)]
        ok = [sum(C[i][s] == 1 for s, u in PARES) for i in range(100)]
        f = lambda v, idx: 100 * sum(v[i] for i in idx) / (12 * len(idx))
        lo, hi = boot(lambda idx: f(dis, idx)); piso[m] = (dis, f(dis, range(100)))
        lo2, hi2 = boot(lambda idx: 100 * sum(a10[i] for i in idx) / max(sum(ok[i] for i in idx), 1))
        por.append(dict(tarea=t, modelo=m, parejas=1200, pct_cambia=round(f(dis, range(100)), 2), ic95_bajo=lo, ic95_alto=hi, pct_1a0=round(f(a10, range(100)), 2),
                        pct_0a1=round(f(dis, range(100)) - f(a10, range(100)), 2), pct_1a0_dado_correcto=round(100 * sum(a10) / max(sum(ok), 1), 2),
                        ic95_1a0_dado_correcto_bajo=lo2, ic95_1a0_dado_correcto_alto=hi2, pct_correctas=round(100 * sum(sum(r) for r in C) / 400, 2),
                        solo_muestreo="si" if m in ("think", "nothink") else "no (incluye reentrenar el LoRA)", estado="EXPLORATORIO"))
    for ref in ("think", "nothink"):
        if D[ref] is None: continue
        O = D[ref]; dref, pref = piso[ref]
        for b in "abcdef":
            C = D[b]; d4 = [sum(C[i][s] != O[i][s] for s in range(4)) for i in range(100)]; dbrazo = piso[b][1]
            g = lambda idx: 100 * sum(d4[i] for i in idx) / (4 * len(idx))
            x = lambda idx: g(idx) - 100 * sum(dref[i] for i in idx) / (12 * len(idx))
            lo, hi = boot(x)
            vs.append(dict(tarea=t, referencia=f"original_{ref}", brazo=b, pct_cambia_brazo_vs_original=round(g(range(100)), 2), piso_original_vs_original=round(pref, 2),
                           piso_brazo_vs_brazo=round(dbrazo, 2), exceso_sobre_piso=round(x(range(100)), 2), ic95_exceso_bajo=lo, ic95_exceso_alto=hi,
                           lectura="mas que azar" if lo > 0 else "dentro del azar" if hi >= 0 else "menos que el azar", estado="EXPLORATORIO"))
for nom, F in [("ruido_semillas_por_modelo", por), ("ruido_vs_cambios", vs)]:
    with open(f"{P3}/{nom}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(F[0].keys())); w.writeheader(); w.writerows(F)
for r in por: print(r["tarea"], r["modelo"], "cambia", r["pct_cambia"], (r["ic95_bajo"], r["ic95_alto"]), "1a0", r["pct_1a0"], "cond", r["pct_1a0_dado_correcto"], "corr", r["pct_correctas"])
for r in vs: print(r["tarea"], r["referencia"], r["brazo"], "cambia", r["pct_cambia_brazo_vs_original"], "piso", r["piso_original_vs_original"], "exceso", r["exceso_sobre_piso"], (r["ic95_exceso_bajo"], r["ic95_exceso_alto"]), r["lectura"])
