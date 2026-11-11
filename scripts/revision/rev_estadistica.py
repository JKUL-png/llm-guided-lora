"""REVISION EXTERNA (2026-11-10). Analisis nuevo, SIN GPU, solo Python estandar. NO es parte del analisis original.
Uso (desde paper2/): python resultados/revision/rev_estadistica.py
Lee los CSV por problema (resultados/p3/eval y resultados/calificacion) y NO modifica nada existente.
Escribe solo en resultados/revision/ (archivos rev_*.csv).

Que hace:
 1. Recalcula desde cero % por brazo, diferencias, IC bootstrap por problema y McNemar de 400 parejas (para verificar los CSV originales).
 2. Pruebas que respetan que las 4 semillas del mismo problema NO son independientes:
    - p_signos_exacta: permutacion exacta de signos por problema sobre d_i = (aciertos de X - aciertos de Y) en las 4 semillas (d_i entre -4 y 4).
    - p_z_cluster: z = media(d)/error estandar por problema (aprox. normal).
    - McNemar por problema con mayoria estricta (>=3 de 4 semillas).
 3. Sensibilidad del McNemar de 400 parejas al emparejamiento de semillas (las 24 formas de emparejar semillas de X con semillas de Y).
 4. IC bootstrap de dos vias (remuestrea problemas Y semillas) e IC 90% (para una lectura de equivalencia tipo TOST).
 5. Holm con las familias originales y con familias alternativas, usando p_signos_exacta.
 6. Comparacion con p50c (edicion del MIT), que el PLAN lista como referencia y ANALISIS_FINAL no usa.
 7. Metricas que el PLAN (seccion 3) prometia y ANALISIS_FINAL no reporta: precision entre las que terminan y ganancia separada (antes al limite / ya terminaba).
 8. Piso de ruido con un estimador simetrico: cruce(brazo, original) - promedio de los dos pisos.
 9. Analisis a nivel de LoRA (n = 4 por brazo): permutacion exacta de etiquetas entre brazos."""
import csv, math, random, itertools
R = "resultados"; P3 = f"{R}/p3"; CAL = f"{R}/calificacion"; OUT = f"{R}/revision"
IDF = {"math": "math500", "gsm8k": "gsm8k", "ifeval": "ifeval"}
NOM = {"a": "(a) 24 capas", "b": "(b) Opus informado", "c": "(c) placebo", "d": "(d) gradiente", "e": "(e) barrido", "f": "(f) Opus+barrido",
       "T": "original con thinking", "N": "original sin thinking", "P": "p50c MIT con thinking"}


def ids(t): return [l.strip() for l in open(f"datos/{IDF[t]}_subset100_ids.txt", encoding="utf-8") if l.strip() and not l.startswith("#")]


def ruta(t, temp, m, s):
    if temp == "T10":
        return {"e": f"{P3}/eval/e{s}_T10_s{s}.csv", "N": f"{P3}/eval/ref_nothink_T10_s{s}.csv", "T": f"{CAL}/math_orig_think_T10_s{s}.csv", "P": f"{CAL}/math_p50c_think_T10_s{s}.csv"}[m]
    if m == "P": return f"{CAL}/{t}_p50c_think_T06_s{s}.csv"
    if m == "T": return f"{CAL}/{t}_orig_think_T06_s{s}.csv" if (t == "math" or s == 0) else f"{P3}/eval/p6_{t}_orig_think_T06_s{s}.csv"
    if m == "N": return f"{CAL}/math_orig_nothink_T06_s{s}.csv" if t == "math" else f"{P3}/eval/p6b_{t}_orig_nothink_T06_s{s}.csv"
    return f"{P3}/eval/{m}{s}_T06_s{s}.csv" if t == "math" else f"{P3}/eval/p5_{t}_{m}{s}_T06_s{s}.csv"


def cargar(t, temp, m):
    I = ids(t); cols = {"correcto": [], "llego_limite": [], "tokens": [], "cierres": []}
    for s in range(4):
        X = {r["id"]: r for r in csv.DictReader(open(ruta(t, temp, m, s), encoding="utf-8"))}
        assert sorted(X) == sorted(I), ruta(t, temp, m, s)
        assert all(r.get("error_calificacion", "0") in ("0", "") for r in X.values()), ruta(t, temp, m, s)
        for k in cols: cols[k].append([int(float(X[i].get(k) or 0)) for i in I])
    return {k: [[cols[k][s][i] for s in range(4)] for i in range(100)] for k in cols}   # [problema][semilla]


def boot(v, q=(249, 9749)):   # identico al original: IC percentil de la media, 10,000 remuestras, misma semilla
    Rg = random.Random(20261107); n = len(v)
    bs = sorted(sum(v[Rg.randrange(n)] for _ in range(n)) / n for _ in range(10000))
    return tuple(round(100 * bs[k], 2) for k in q)


def mcn_p(b, c):
    n = b + c
    return 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, k) for k in range(min(b, c) + 1)) / 2 ** n)


def mcn400(x, y, perm=(0, 1, 2, 3)):
    b = sum(x[i][s] == 1 and y[i][perm[s]] == 0 for i in range(100) for s in range(4))
    c = sum(x[i][s] == 0 and y[i][perm[s]] == 1 for i in range(100) for s in range(4))
    return b, c, mcn_p(b, c)


def signos_exacta(D):   # D: enteros d_i. p bilateral exacta de |suma| bajo cambio de signo independiente por problema
    obs = abs(sum(D)); dist = {0: 1.0}
    for d in D:
        if d == 0: continue
        nd = {}
        for k, p in dist.items():
            nd[k + d] = nd.get(k + d, 0) + p / 2; nd[k - d] = nd.get(k - d, 0) + p / 2
        dist = nd
    return min(1.0, sum(p for k, p in dist.items() if abs(k) >= obs))


def z_cluster(D):
    n = len(D); m = sum(D) / n; v = sum((d - m) ** 2 for d in D) / (n - 1)
    if v == 0: return 1.0
    return math.erfc(abs(m / math.sqrt(v / n)) / math.sqrt(2))


def dosvias(x, y, reps=4000):   # remuestrea problemas y, por separado, las semillas de X y de Y
    Rg = random.Random(20261110); out = []
    for _ in range(reps):
        sx = [Rg.randrange(4) for _ in range(4)]; sy = [Rg.randrange(4) for _ in range(4)]
        v = [(sum(x[i][s] for s in sx) - sum(y[i][s] for s in sy)) / 4 for i in range(100)]
        out.append(sum(v[Rg.randrange(100)] for _ in range(100)) / 100)
    out.sort(); return round(100 * out[int(.025 * reps)], 2), round(100 * out[int(.975 * reps) - 1], 2)


def holm(ps):
    o = sorted(range(len(ps)), key=lambda i: ps[i]); out = [0] * len(ps); m = 0
    for r, i in enumerate(o): m = max(m, (len(ps) - r) * ps[i]); out[i] = min(1.0, m)
    return out


def guardar(nom, F):
    with open(f"{OUT}/{nom}", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(F[0].keys())); w.writeheader(); w.writerows(F)


CERO = [[0] * 4 for _ in range(100)]   # para el IC de dos vias de un solo modelo
DATA = {}
for t in ("math", "gsm8k", "ifeval"):
    DATA[(t, "T06")] = {m: cargar(t, "T06", m) for m in "abcdefTNP"}
DATA[("math", "T10")] = {m: cargar("math", "T10", m) for m in "eNTP"}
DOSVIAS = {("math", "T06"): [("b", "c"), ("b", "d"), ("b", "a"), ("e", "N"), ("c", "N"), ("a", "N"), ("f", "e")], ("math", "T10"): [("e", "N")],
           ("gsm8k", "T06"): [("a", "N"), ("b", "N"), ("b", "c")], ("ifeval", "T06"): [("b", "N"), ("d", "N"), ("b", "c")]}
PARES = {("math", "T06"): [("b", "c"), ("b", "d"), ("b", "a")] + [(x, "N") for x in "abcdef"] + [(x, "a") for x in "cdef"] +
         [("f", "c"), ("d", "c"), ("e", "c"), ("f", "d"), ("f", "e"), ("e", "b"), ("e", "d")] + [(x, "P") for x in "abcdefN"] + [(x, "T") for x in "abcdef"],
         ("math", "T10"): [("e", "N"), ("e", "T"), ("e", "P"), ("N", "P")]}
for t in ("gsm8k", "ifeval"):
    PARES[(t, "T06")] = [(x, "N") for x in "abcdef"] + [("b", "a"), ("b", "c"), ("b", "d")] + [(x, "P") for x in "abcdefN"] + [(x, "T") for x in "abcdef"]

comp, porb = [], []
for (t, temp), D in DATA.items():
    for m, d in D.items():
        x = d["correcto"]; v = [sum(r) / 4 for r in x]; lo, hi = boot(v); dv = dosvias(x, CERO)
        fin = [(d["correcto"][i][s], d["llego_limite"][i][s]) for i in range(100) for s in range(4)]
        nfin = sum(1 for c, l in fin if not l)
        porb.append(dict(tarea=t, temp=temp, modelo=m, nombre=NOM[m], pct_correctas=round(sum(v), 2), ic95_bajo=lo, ic95_alto=hi, ic95_dosvias_bajo=dv[0], ic95_dosvias_alto=dv[1],
                         por_semilla=" / ".join(str(sum(x[i][s] for i in range(100))) for s in range(4)),
                         pct_al_limite=round(sum(l for c, l in fin) / 4, 2), terminaron=nfin,
                         pct_correctas_entre_terminadas=round(100 * sum(c for c, l in fin if not l) / max(1, nfin), 2),
                         tokens_medios=round(sum(map(sum, d["tokens"])) / 400, 1), pct_varios_cierres=round(sum(c > 1 for r in d["cierres"] for c in r) / 4, 2)))
    for X, Y in PARES[(t, temp)]:
        x, y = D[X]["correcto"], D[Y]["correcto"]
        di = [sum(x[i]) - sum(y[i]) for i in range(100)]; d = [k / 4 for k in di]
        lo, hi = boot(d); lo90, hi90 = boot(d, (499, 9499)); b, c, p = mcn400(x, y)
        pp = [mcn400(x, y, pm)[2] for pm in itertools.permutations(range(4))]
        mx = [int(sum(r) >= 3) for r in x]; my = [int(sum(r) >= 3) for r in y]
        mb = sum(a == 1 and bb == 0 for a, bb in zip(mx, my)); mc = sum(a == 0 and bb == 1 for a, bb in zip(mx, my))
        fila = dict(tarea=t, temp=temp, X=X, Y=Y, comparacion=f"{NOM[X]} - {NOM[Y]}", pct_X=round(sum(map(sum, x)) / 4, 2), pct_Y=round(sum(map(sum, y)) / 4, 2),
                    dif_puntos=round(sum(d), 2), ic95_bajo=lo, ic95_alto=hi, ic90_bajo=lo90, ic90_alto=hi90, solo_X=b, solo_Y=c, p_mcnemar400=round(p, 6),
                    p_mcnemar400_min_24_emparejamientos=round(min(pp), 6), p_mcnemar400_max_24_emparejamientos=round(max(pp), 6),
                    p_signos_exacta=round(signos_exacta(di), 6), p_z_cluster=round(z_cluster(di), 6),
                    mayoria_solo_X=mb, mayoria_solo_Y=mc, p_mcnemar_mayoria=round(mcn_p(mb, mc), 6), problemas_con_d_distinto_de_0=sum(k != 0 for k in di),
                    ic95_dosvias_bajo="", ic95_dosvias_alto="")
        fila["ic95_dosvias_bajo"], fila["ic95_dosvias_alto"] = dosvias(x, y)
        comp.append(fila)
guardar("rev_por_modelo.csv", porb); guardar("rev_comparaciones.csv", comp)
C = {(r["tarea"], r["temp"], r["X"], r["Y"]): r for r in comp}

# 5) Holm con p_signos_exacta y con el McNemar original, familias originales y alternativas
M6 = "abcdef"
FAMS = [("math_principal_2 (original)", [("math", "T06", "b", "c"), ("math", "T06", "b", "d")]),
        ("math_vs_sin_thinking_6 (original)", [("math", "T06", x, "N") for x in M6]),
        ("math_todas_las_fijadas_a_0.6_juntas_9 (alternativa)", [("math", "T06", "b", "c"), ("math", "T06", "b", "d"), ("math", "T06", "b", "a")] + [("math", "T06", x, "N") for x in M6]),
        ("math_vs_sin_thinking_solo_brazos_del_PLAN_original_abcd_4 (alternativa)", [("math", "T06", x, "N") for x in "abcd"]),
        ("math_4capas_vs_a_5 (exploratoria original)", [("math", "T06", x, "a") for x in "bcdef"]),
        ("math_centrales_5 (exploratoria original)", [("math", "T06", "f", "c"), ("math", "T06", "d", "c"), ("math", "T06", "e", "c"), ("math", "T06", "f", "d"), ("math", "T06", "f", "e")]),
        ("math_parejas_entre_brazos_de_4_capas_9 (alternativa)", [("math", "T06", "b", "c"), ("math", "T06", "b", "d"), ("math", "T06", "f", "c"), ("math", "T06", "d", "c"), ("math", "T06", "e", "c"), ("math", "T06", "f", "d"), ("math", "T06", "f", "e"), ("math", "T06", "e", "b"), ("math", "T06", "e", "d")]),
        ("gsm8k_vs_sin_thinking_6 (original)", [("gsm8k", "T06", x, "N") for x in M6]),
        ("ifeval_vs_sin_thinking_6 (original)", [("ifeval", "T06", x, "N") for x in M6]),
        ("vs_sin_thinking_las_3_tareas_juntas_18 (alternativa)", [(t, "T06", x, "N") for t in ("math", "gsm8k", "ifeval") for x in M6]),
        ("math_vs_p50c_6 (nueva, revision)", [("math", "T06", x, "P") for x in M6]),
        ("gsm8k_vs_p50c_6 (nueva, revision)", [("gsm8k", "T06", x, "P") for x in M6]),
        ("ifeval_vs_p50c_6 (nueva, revision)", [("ifeval", "T06", x, "P") for x in M6])]
H = []
for nom, ks in FAMS:
    h1 = holm([C[k]["p_mcnemar400"] for k in ks]); h2 = holm([C[k]["p_signos_exacta"] for k in ks])
    for k, a, b in zip(ks, h1, h2):
        r = C[k]; H.append(dict(familia=nom, tamano=len(ks), tarea=k[0], X=k[2], Y=k[3], dif_puntos=r["dif_puntos"], ic95=f"[{r['ic95_bajo']}, {r['ic95_alto']}]",
                                p_mcnemar400=r["p_mcnemar400"], holm_mcnemar400=round(a, 6), p_signos_exacta=r["p_signos_exacta"], holm_signos=round(b, 6),
                                sobrevive_mcnemar400="si" if a < .05 else "no", sobrevive_signos="si" if b < .05 else "no"))
guardar("rev_holm.csv", H)

# 7) metricas prometidas en el PLAN: ganancia separada segun el estado del original con thinking (misma semilla)
G = []
for t in ("math", "gsm8k", "ifeval"):
    D = DATA[(t, "T06")]
    lim = [(i, s) for i in range(100) for s in range(4) if D["T"]["llego_limite"][i][s]]
    ter = [(i, s) for i in range(100) for s in range(4) if not D["T"]["llego_limite"][i][s]]
    acc = lambda mm, K: round(100 * sum(D[mm]["correcto"][i][s] for i, s in K) / max(1, len(K)), 2)
    for m in "abcdefNP":
        G.append(dict(tarea=t, modelo=m, nombre=NOM[m], n_original_think_al_limite=len(lim), pct_correctas_modelo_donde_original_al_limite=acc(m, lim),
                      pct_correctas_original_ahi=acc("T", lim), n_original_think_terminaba=len(ter), pct_correctas_modelo_donde_original_terminaba=acc(m, ter),
                      pct_correctas_original_donde_terminaba=acc("T", ter)))
guardar("rev_ganancia_separada.csv", G)

# 8) piso de ruido simetrico
PO = [(s, u) for s in range(4) for u in range(4) if s != u]; PT = [(s, u) for s in range(4) for u in range(4)]
RU = []
for t in ("math", "gsm8k", "ifeval"):
    D = DATA[(t, "T06")]
    for ref in ("N", "T"):
        y = D[ref]["correcto"]
        for m in "abcdefP":
            x = D[m]["correcto"]
            cr = [sum(x[i][s] != y[i][u] for s, u in PT) / 16 for i in range(100)]          # cruce con las 16 parejas de semillas
            cs = [sum(x[i][s] != y[i][s] for s in range(4)) / 4 for i in range(100)]          # cruce misma semilla (como el original)
            wa = [sum(x[i][s] != x[i][u] for s, u in PO) / 12 for i in range(100)]; wr = [sum(y[i][s] != y[i][u] for s, u in PO) / 12 for i in range(100)]
            e_or = [a - b for a, b in zip(cs, wr)]; e_si = [a - (b + c) / 2 for a, b, c in zip(cr, wa, wr)]
            l1, h1 = boot(e_or); l2, h2 = boot(e_si)
            RU.append(dict(tarea=t, referencia=NOM[ref], modelo=m, cruce_misma_semilla=round(sum(cs), 2), cruce_16_parejas=round(sum(cr), 2), piso_modelo=round(sum(wa), 2),
                           piso_referencia=round(sum(wr), 2), exceso_como_el_original=round(sum(e_or), 2), ic95_orig_bajo=l1, ic95_orig_alto=h1,
                           exceso_simetrico=round(sum(e_si), 2), ic95_sim_bajo=l2, ic95_sim_alto=h2))
guardar("rev_ruido_simetrico.csv", RU)

# 9) nivel LoRA (n = 4 por brazo): permutacion exacta de etiquetas sobre los 8 puntajes
S = []
for t in ("math", "gsm8k", "ifeval"):
    D = DATA[(t, "T06")]; sc = {m: [sum(D[m]["correcto"][i][s] for i in range(100)) for s in range(4)] for m in "abcdefN"}
    for X, Y in [("b", "c"), ("b", "d"), ("b", "a"), ("e", "f"), ("e", "N"), ("c", "N"), ("a", "N"), ("b", "N")]:
        allv = sc[X] + sc[Y]; obs = abs(sum(sc[X]) - sum(sc[Y])) / 4; n = 0; k = 0
        for cb in itertools.combinations(range(8), 4):
            n += 1; a = sum(allv[i] for i in cb); k += abs(a - (sum(allv) - a)) / 4 >= obs - 1e-9
        dif = [a - b for a, b in zip(sc[X], sc[Y])]; md = sum(dif) / 4; sd = math.sqrt(sum((d - md) ** 2 for d in dif) / 3)
        S.append(dict(tarea=t, X=X, Y=Y, puntajes_X=" ".join(map(str, sc[X])), puntajes_Y=" ".join(map(str, sc[Y])), dif_media=md,
                      p_permutacion_etiquetas_70=round(k / n, 4), ic95_t_pareado_gl3_bajo=round(md - 3.182 * sd / 2, 2), ic95_t_pareado_gl3_alto=round(md + 3.182 * sd / 2, 2),
                      desv_entre_semillas_X=round(math.sqrt(sum((v - sum(sc[X]) / 4) ** 2 for v in sc[X]) / 3), 2),
                      desv_entre_semillas_Y=round(math.sqrt(sum((v - sum(sc[Y]) / 4) ** 2 for v in sc[Y]) / 3), 2)))
guardar("rev_nivel_lora.csv", S)

# 1) verificacion contra los CSV originales
V = []
def chk(que, orig, nuevo): V.append(dict(que=que, valor_csv_original=orig, valor_recalculado=nuevo, coincide="si" if abs(float(orig) - float(nuevo)) < 0.006 else "NO"))
CAMPOS = [("dif_puntos", "dif_puntos"), ("ic95_bajo", "ic95_bajo"), ("ic95_alto", "ic95_alto"), ("solo_X", "solo_X"), ("solo_Y", "solo_Y"), ("p_mcnemar", "p_mcnemar400")]
for etapa, temp in (("etapa2", "T06"), ("etapa3", "T10")):
    for r in csv.DictReader(open(f"{P3}/{etapa}_comparaciones.csv", encoding="utf-8")):
        k = ("math", temp, r["X"], r["Y"])
        if r["metrica"] == "correctas" and k in C:
            for a, b in CAMPOS: chk(f"{etapa} {r['familia']} {r['X']}-{r['Y']} {a}", r[a], C[k][b])
INV = {v: k for k, v in NOM.items()}; sin_pareja = 0
for t in ("gsm8k", "ifeval"):
    for r in csv.DictReader(open(f"{P3}/p5_{t}_comparaciones.csv", encoding="utf-8")):
        if r["metrica"] != "correctas": continue
        pr = r["comparacion"].split(" - ")
        if len(pr) != 2 or pr[0] not in INV or pr[1] not in INV: sin_pareja += 1; continue
        k = (t, "T06", INV[pr[0]], INV[pr[1]])
        if k in C:
            for a, b in CAMPOS: chk(f"p5 {t} {r['familia']} {k[2]}-{k[3]} {a}", r[a], C[k][b])
        else: sin_pareja += 1
PB = {(r["tarea"], r["temp"], r["modelo"]): r for r in porb}
for f, t, temp in [(f"{P3}/etapa2_por_brazo.csv", "math", "T06"), (f"{P3}/etapa3_por_brazo.csv", "math", "T10"), (f"{P3}/p5_gsm8k_por_brazo.csv", "gsm8k", "T06"), (f"{P3}/p5_ifeval_por_brazo.csv", "ifeval", "T06")]:
    for r in csv.DictReader(open(f, encoding="utf-8")):
        k = (t, temp, r["brazo"])
        if k in PB:
            for a, b in [("pct_correctas", "pct_correctas"), ("ic95_correctas_bajo", "ic95_bajo"), ("ic95_correctas_alto", "ic95_alto"), ("pct_al_limite", "pct_al_limite"),
                         ("tokens_medios", "tokens_medios"), ("pct_varios_cierres", "pct_varios_cierres")]:
                chk(f"{t} {temp} brazo {r['brazo']} {a}", r[a], PB[k][b] if a != "tokens_medios" else round(float(PB[k][b]), 1))
guardar("rev_verificacion_csv.csv", V)
print("verificacion:", len(V), "cifras;", sum(v["coincide"] == "NO" for v in V), "no coinciden; filas p5 sin pareja:", sin_pareja)
for v in V:
    if v["coincide"] == "NO": print("  ", v)


# ===== ANADIDO 2026-11-10, despues de la revision (pedido del usuario al aceptarla) =====
# (1) El IC de dos vias (problemas y semillas/LoRA) se calcula ahora para TODAS las comparaciones y para cada modelo.
# (2) Las 3 tablas que en la revision se hicieron con comandos sueltos se generan aqui. Son EXPLORATORIAS (definidas despues de ver datos).
def limpia(d): return [[int(d["cierres"][i][s] == 1 and not d["llego_limite"][i][s]) for s in range(4)] for i in range(100)]


def psem(M): return " ".join(str(sum(M[i][s] for i in range(100))) for s in range(4))


def comparar(nom, F, clave):   # avisa si la tabla regenerada difiere de la que ya estaba en disco
    try: old = {clave(r): r for r in csv.DictReader(open(f"{OUT}/{nom}", encoding="utf-8"))}
    except FileNotFoundError: return
    mal = n = 0
    for r in F:
        o = old.get(clave({k: str(v) for k, v in r.items()}))
        if o is None: continue
        for k in o:
            if k in r:
                n += 1
                try: mal += abs(float(o[k]) - float(r[k])) > 1e-9
                except ValueError: mal += str(o[k]) != str(r[k])
    print("comparada con la version anterior:", nom, "| celdas comunes:", n, "| distintas:", mal)


rl, rlc, dw = [], [], []
for t in ("math", "gsm8k", "ifeval"):
    for m in "abcdefP":
        d = DATA[(t, "T06")][m]; L = limpia(d); lo, hi = dosvias(L, CERO)
        cel = [(d["correcto"][i][s], L[i][s], d["cierres"][i][s] > 1, d["llego_limite"][i][s]) for i in range(100) for s in range(4)]
        nl = sum(c[1] for c in cel); nv = sum(c[2] for c in cel)
        rl.append(dict(tipo="EXPLORATORIO", tarea=t, brazo=m, pct_al_limite=round(sum(c[3] for c in cel) / 4, 2), pct_varios_cierres=round(nv / 4, 2),
                       pct_respuesta_limpia_1_cierre_sin_limite=round(nl / 4, 2), ic95_dosvias_bajo=lo, ic95_dosvias_alto=hi, limpias_por_semilla=psem(L),
                       pct_correctas_entre_limpias=round(100 * sum(c[0] for c in cel if c[1]) / max(1, nl), 2),
                       pct_correctas_entre_varios_cierres=round(100 * sum(c[0] for c in cel if c[2]) / max(1, nv), 2)))
for X, Y in [("b", "c"), ("b", "d"), ("b", "e"), ("b", "a"), ("f", "e"), ("b", "P")]:
    x, y = limpia(DATA[("math", "T06")][X]), limpia(DATA[("math", "T06")][Y])
    di = [sum(x[i]) - sum(y[i]) for i in range(100)]; lo, hi = boot([k / 4 for k in di]); l2, h2 = dosvias(x, y)
    rlc.append(dict(tipo="EXPLORATORIO", tarea="math", metrica="respuesta_limpia (1 cierre y sin llegar al limite)", X=X, Y=Y, dif_puntos=round(sum(di) / 4, 2),
                    ic95_dosvias_bajo=l2, ic95_dosvias_alto=h2, ic95_bajo=lo, ic95_alto=hi, p_signos_exacta=round(signos_exacta(di), 6), por_semilla_X=psem(x), por_semilla_Y=psem(y)))
for b in "abcdef":
    for s in range(4):
        F = list(csv.DictReader(open(f"{P3}/fusion/{b}{s}.csv", encoding="utf-8")))
        dw.append(dict(tipo="DESCRIPTIVO", brazo=b, semilla=s, tensores=len(F), max_dw_w_despues=round(max(float(r["dw_w_despues"]) for r in F), 5),
                       min_fraccion_conservada=round(min(float(r["fraccion_parche_conservada"]) for r in F), 4)))
comparar("rev_respuestas_limpias.csv", rl, lambda r: (r["tarea"], r["brazo"]))
comparar("rev_respuestas_limpias_comparaciones.csv", rlc, lambda r: (r["X"], r["Y"]))
comparar("rev_dw_resumen.csv", dw, lambda r: (r["brazo"], r["semilla"]))
guardar("rev_respuestas_limpias.csv", rl); guardar("rev_respuestas_limpias_comparaciones.csv", rlc); guardar("rev_dw_resumen.csv", dw)
