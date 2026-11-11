"""Macros y tablas de RESULTADOS del paper 2, generadas desde los CSV. SIN GPU, solo Python estandar.
Lo llama make_macros.py al final (no hace falta correrlo aparte).
Salida: paper2/paper/latex/generated/resultados.tex (claves \\R{...}) y generated/tab_*.tex.
Uso en LaTeX: \\R{mod:math:06:b:acc} -> 54.0. Si una clave no existe, LaTeX imprime ??clave?? en negrita
y check_keys() de este script ya habra fallado antes, porque revisa todas las claves que usa main.tex.
Formato: porcentajes y diferencias con 1 decimal, redondeo de mitades al par (como el paper 1)."""
import csv, json, os, re, glob, collections
from decimal import Decimal, ROUND_HALF_EVEN

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))   # raiz del repositorio
P2 = RAIZ; RES = os.path.join(P2, "resultados"); REV = os.path.join(RES, "revision")
OUT = os.path.join(RAIZ, "paper", "latex", "generated")
K = collections.OrderedDict()   # clave -> texto LaTeX
SRC = {}                        # clave -> archivo fuente


def put(key, val, src):
    assert key not in K, key
    K[key] = str(val); SRC[key] = src


def rows(*p): return list(csv.DictReader(open(os.path.join(*p), encoding="utf-8")))


MINUS = "$-$"


def f1(v):
    d = Decimal(str(round(float(v), 6))).quantize(Decimal("0.1"), rounding=ROUND_HALF_EVEN)
    if d == 0: d = abs(d)
    s = str(d)
    return s.replace("-", MINUS)


def sg(v):   # con signo
    s = f1(v)
    return s if s.startswith(MINUS) or s == "0.0" else "+" + s


def miles(n): return f"{int(round(float(n))):,}".replace(",", "{,}")


def fp(p):
    p = float(p)
    if p < 0.001: return "$<$0.001"
    if p >= 0.1: return f"{p:.2f}"
    return f"{float(f'{p:.2g}'):g}" if p >= 0.01 else f"{p:.2g}".replace("e-0", "e-")


def ci(lo, hi, signed=True):
    g = sg if signed else f1
    return f"[{g(lo)}, {g(hi)}]"


T = {"T06": "06", "T10": "10"}
ARMS = "abcdef"

# ---------------- 1. Por modelo ----------------
F = "resultados/revision/rev_por_modelo.csv"
MOD = {}
for r in rows(REV, "rev_por_modelo.csv"):
    k = f"mod:{r['tarea']}:{T[r['temp']]}:{r['modelo']}"; MOD[(r['tarea'], T[r['temp']], r['modelo'])] = r
    put(k + ":acc", f1(r["pct_correctas"]), F); put(k + ":lo", f1(r["ic95_dosvias_bajo"]), F); put(k + ":hi", f1(r["ic95_dosvias_alto"]), F)
    put(k + ":ci", ci(r["ic95_dosvias_bajo"], r["ic95_dosvias_alto"], False), F)
    put(k + ":plo", f1(r["ic95_bajo"]), F); put(k + ":phi", f1(r["ic95_alto"]), F)
    put(k + ":seeds", r["por_semilla"].replace(" / ", "\\,/\\,"), F)
    put(k + ":lim", f1(r["pct_al_limite"]), F); put(k + ":tok", miles(r["tokens_medios"]), F)
    put(k + ":multi", f1(r["pct_varios_cierres"]), F); put(k + ":accfin", f1(r["pct_correctas_entre_terminadas"]), F)
    put(k + ":nfin", r["terminaron"], F)
    sem = [int(x) for x in r["por_semilla"].split(" / ")]; put(k + ":seedmin", min(sem), F); put(k + ":seedmax", max(sem), F)

# rangos sobre los 6 brazos
for (t, tp) in sorted({(a, b) for a, b, _ in MOD}):
    if not all((t, tp, a) in MOD for a in ARMS): continue
    for campo, nom in (("pct_correctas", "acc"), ("pct_al_limite", "lim"), ("tokens_medios", "tok"), ("pct_varios_cierres", "multi"), ("pct_correctas_entre_terminadas", "accfin")):
        v = [float(MOD[(t, tp, a)][campo]) for a in ARMS]
        g = miles if nom == "tok" else f1
        put(f"rng:mod:{t}:{tp}:{nom}:min", g(min(v)), F); put(f"rng:mod:{t}:{tp}:{nom}:max", g(max(v)), F)
    four = [float(MOD[(t, tp, a)]["pct_al_limite"]) for a in "bcdef"]
# razones de tokens
for t in ("math", "gsm8k", "ifeval"):
    arms = [float(MOD[(t, "06", a)]["tokens_medios"]) for a in ARMS]
    for ref in "PN":
        rt = float(MOD[(t, "06", ref)]["tokens_medios"])
        q = [rt / x for x in arms] if ref == "P" else [x / rt for x in arms]
        put(f"ratio:{t}:{ref}:min", f"{min(q):.1f}", F + " (cociente de tokens medios)"); put(f"ratio:{t}:{ref}:max", f"{max(q):.1f}", F + " (cociente de tokens medios)")

# ---------------- 2. Comparaciones ----------------
F = "resultados/revision/rev_comparaciones.csv"
CMP = {}
for r in rows(REV, "rev_comparaciones.csv"):
    key = (r["tarea"], T[r["temp"]], r["X"], r["Y"]); CMP[key] = r
    k = "cmp:" + ":".join(key)
    put(k + ":dif", sg(r["dif_puntos"]), F); put(k + ":lo", sg(r["ic95_dosvias_bajo"]), F); put(k + ":hi", sg(r["ic95_dosvias_alto"]), F)
    put(k + ":ci", ci(r["ic95_dosvias_bajo"], r["ic95_dosvias_alto"]), F); put(k + ":pci", ci(r["ic95_bajo"], r["ic95_alto"]), F)
    put(k + ":nci", ci(r["ic90_bajo"], r["ic90_alto"]), F)
    put(k + ":p", fp(r["p_signos_exacta"]), F); put(k + ":mc", fp(r["p_mcnemar400"]), F)
    put(k + ":mcmin", fp(r["p_mcnemar400_min_24_emparejamientos"]), F); put(k + ":mcmax", fp(r["p_mcnemar400_max_24_emparejamientos"]), F)
    put(k + ":majx", r["mayoria_solo_X"], F); put(k + ":majy", r["mayoria_solo_Y"], F); put(k + ":pmaj", fp(r["p_mcnemar_mayoria"]), F)
    put(k + ":absdif", f1(abs(float(r["dif_puntos"]))), F)
for (t, tp, Y) in sorted({(a, b, d) for a, b, c, d in CMP}):
    xs = [CMP[(t, tp, x, Y)] for x in ARMS if (t, tp, x, Y) in CMP]
    if len(xs) != 6: continue
    d = [float(r["dif_puntos"]) for r in xs]; lo = [float(r["ic95_dosvias_bajo"]) for r in xs]; hi = [float(r["ic95_dosvias_alto"]) for r in xs]
    put(f"rng:cmp:{t}:{tp}:{Y}:min", sg(min(d)), F); put(f"rng:cmp:{t}:{tp}:{Y}:max", sg(max(d)), F)
    put(f"rng:cmp:{t}:{tp}:{Y}:minlo", sg(min(lo)), F); put(f"rng:cmp:{t}:{tp}:{Y}:maxhi", sg(max(hi)), F)
    put(f"rng:cmp:{t}:{tp}:{Y}:absmin", f1(min(abs(x) for x in d)), F); put(f"rng:cmp:{t}:{tp}:{Y}:absmax", f1(max(abs(x) for x in d)), F)
    put(f"rng:cmp:{t}:{tp}:{Y}:pmin", fp(min(float(r["p_signos_exacta"]) for r in xs)), F)
    put(f"rng:cmp:{t}:{tp}:{Y}:pmax", fp(max(float(r["p_signos_exacta"]) for r in xs)), F)

# ---------------- 3. Holm ----------------
F = "resultados/revision/rev_holm.csv"
FAM = [("math_principal_2", "main"), ("math_vs_sin_thinking_solo", "vsNabcd"), ("math_vs_sin_thinking_6", "vsN"), ("math_todas_las_fijadas", "all"),
       ("math_4capas_vs_a", "vsa"), ("math_centrales", "central"), ("math_parejas_entre", "pairs"), ("gsm8k_vs_sin_thinking", "vsN"),
       ("ifeval_vs_sin_thinking", "vsN"), ("vs_sin_thinking_las_3", "vsNall"), ("math_vs_p50c", "vsP"), ("gsm8k_vs_p50c", "vsP"), ("ifeval_vs_p50c", "vsP")]
HOLM = {}
for r in rows(REV, "rev_holm.csv"):
    fam = next(s for pre, s in FAM if r["familia"].startswith(pre))
    key = (fam, r["tarea"], r["X"], r["Y"]); HOLM[key] = r
    k = "holm:" + ":".join(key)
    put(k + ":hs", fp(r["holm_signos"]), F); put(k + ":hm", fp(r["holm_mcnemar400"]), F)
    put(f"fam:{fam}:{r['tarea']}:size", r["tamano"], F) if f"fam:{fam}:{r['tarea']}:size" not in K else None
for fam, t, Y in sorted({(a, b, d) for a, b, c, d in HOLM}):
    xs = [HOLM[(fam, t, x, Y)] for x in ARMS if (fam, t, x, Y) in HOLM]
    if len(xs) == 6:
        put(f"rng:holm:{fam}:{t}:{Y}:max", fp(max(float(r["holm_signos"]) for r in xs)), F)
        put(f"rng:holm:{fam}:{t}:{Y}:min", fp(min(float(r["holm_signos"]) for r in xs)), F)


def lectura(fam, t, tp, X, Y):
    """Regla de lectura (adoptada tras la revision): solido = Holm(permutacion) < 0.05 y el IC de dos vias excluye 0."""
    h = float(HOLM[(fam, t, X, Y)]["holm_signos"]) < 0.05
    c = CMP[(t, tp, X, Y)]; e = float(c["ic95_dosvias_bajo"]) > 0 or float(c["ic95_dosvias_alto"]) < 0
    return "solid" if h and e else ("indication" if h or e else "no")


for (fam, t, X, Y) in HOLM:
    put(f"read:{fam}:{t}:{X}:{Y}", lectura(fam, t, "06", X, Y), "regla de lectura sobre rev_holm.csv y rev_comparaciones.csv")

# ---------------- 4. 4 LoRA contra 4 LoRA ----------------
F = "resultados/revision/rev_nivel_lora.csv"
for r in rows(REV, "rev_nivel_lora.csv"):
    put(f"lora:{r['tarea']}:{r['X']}:{r['Y']}:p", fp(r["p_permutacion_etiquetas_70"]), F)

# ---------------- 5. Respuestas limpias (exploratorio) ----------------
F = "resultados/revision/rev_respuestas_limpias.csv"
CL = {}
for r in rows(REV, "rev_respuestas_limpias.csv"):
    k = f"clean:{r['tarea']}:{r['brazo']}"; CL[(r["tarea"], r["brazo"])] = r
    put(k + ":pct", f1(r["pct_respuesta_limpia_1_cierre_sin_limite"]), F); put(k + ":ci", ci(r["ic95_dosvias_bajo"], r["ic95_dosvias_alto"], False), F)
    put(k + ":seeds", r["limpias_por_semilla"].replace(" ", "\\,/\\,"), F)
    put(k + ":acc", f1(r["pct_correctas_entre_limpias"]), F); put(k + ":accmulti", f1(r["pct_correctas_entre_varios_cierres"]), F)
for t in ("math", "gsm8k", "ifeval"):
    v = [float(CL[(t, a)]["pct_respuesta_limpia_1_cierre_sin_limite"]) for a in ARMS]
    put(f"rng:clean:{t}:min", f1(min(v)), F); put(f"rng:clean:{t}:max", f1(max(v)), F)
    for campo, nom in (("pct_correctas_entre_limpias", "acc"), ("pct_correctas_entre_varios_cierres", "accmulti")):
        v = [float(CL[(t, a)][campo]) for a in ARMS]; put(f"rng:clean:{t}:{nom}:min", f1(min(v)), F); put(f"rng:clean:{t}:{nom}:max", f1(max(v)), F)
F = "resultados/revision/rev_respuestas_limpias_comparaciones.csv"
for r in rows(REV, "rev_respuestas_limpias_comparaciones.csv"):
    k = f"cleancmp:{r['X']}:{r['Y']}"
    put(k + ":dif", sg(r["dif_puntos"]), F); put(k + ":ci", ci(r["ic95_dosvias_bajo"], r["ic95_dosvias_alto"]), F)
    put(k + ":pci", ci(r["ic95_bajo"], r["ic95_alto"]), F); put(k + ":p", fp(r["p_signos_exacta"]), F)
# grupos de capas del placebo (para el texto): capas por semilla desde la lista de LoRA
LISTA = rows(RES, "p3_lista_lora.csv")
for r in LISTA:
    if r["brazo"] == "c": put(f"layers:c:{r['semilla']}", r["capas"].replace(";", ", "), "resultados/p3_lista_lora.csv")
put("layers:e:min", min(int(x) for x in next(r for r in LISTA if r["brazo"] == "e")["capas"].split(";")), "resultados/p3_lista_lora.csv (capa mas baja del brazo e)")

# ---------------- 6. Ganancia separada (exploratorio, prometida en el PLAN) ----------------
F = "resultados/revision/rev_ganancia_separada.csv"
for r in rows(REV, "rev_ganancia_separada.csv"):
    k = f"gain:{r['tarea']}:{r['modelo']}"
    put(k + ":nlim", r["n_original_think_al_limite"], F); put(k + ":acclim", f1(r["pct_correctas_modelo_donde_original_al_limite"]), F)
    put(k + ":nfin", r["n_original_think_terminaba"], F); put(k + ":accfin", f1(r["pct_correctas_modelo_donde_original_terminaba"]), F)
    put(k + ":origfin", f1(r["pct_correctas_original_donde_terminaba"]), F)

# ---------------- 7. Piso de ruido simetrico (exploratorio) ----------------
F = "resultados/revision/rev_ruido_simetrico.csv"
RU = collections.defaultdict(dict)
for r in rows(REV, "rev_ruido_simetrico.csv"):
    ref = "N" if "sin" in r["referencia"] else "T"; k = f"noise:{r['tarea']}:{ref}:{r['modelo']}"
    put(k + ":exc", sg(r["exceso_simetrico"]), F); put(k + ":ci", ci(r["ic95_sim_bajo"], r["ic95_sim_alto"]), F)
    put(k + ":old", sg(r["exceso_como_el_original"]), F); put(k + ":floorref", f1(r["piso_referencia"]), F)
    RU[(r["tarea"], ref)][r["modelo"]] = r
for (t, ref), d in RU.items():
    v = [float(d[a]["exceso_simetrico"]) for a in ARMS]; lo = [float(d[a]["ic95_sim_bajo"]) for a in ARMS]
    o = [float(d[a]["exceso_como_el_original"]) for a in ARMS]
    put(f"rng:noise:{t}:{ref}:min", sg(min(v)), F); put(f"rng:noise:{t}:{ref}:max", sg(max(v)), F); put(f"rng:noise:{t}:{ref}:minlo", sg(min(lo)), F)
    put(f"rng:noise:{t}:{ref}:oldmin", sg(min(o)), F); put(f"rng:noise:{t}:{ref}:oldmax", sg(max(o)), F)
    put(f"noise:{t}:{ref}:floor", f1(d["a"]["piso_referencia"]), F)

# ---------------- 8. Cierres multiples: regla de calificacion y por problema ----------------
F = "resultados/revision/rev_regla_cierre_items.csv"
IT = rows(REV, "rev_regla_cierre_items.csv")
for t in ("math", "gsm8k"):
    mu = [r for r in IT if r["tarea"] == t and int(r["cierres"]) > 1]; un = [r for r in IT if r["tarea"] == t and int(r["cierres"]) == 1]
    put(f"rule:{t}:n", miles(sum(1 for r in IT if r["tarea"] == t)), F)
    put(f"rule:{t}:nmulti", miles(len(mu)), F); put(f"rule:{t}:Lmulti", miles(sum(int(r["L"]) for r in mu)), F)
    put(f"rule:{t}:SEGmulti", miles(sum(int(r["SEG1"]) for r in mu)), F); put(f"rule:{t}:ANYmulti", miles(sum(int(r["ANY"]) for r in mu)), F)
    put(f"rule:{t}:pctLmulti", f1(100 * sum(int(r["L"]) for r in mu) / len(mu)), F)
    put(f"rule:{t}:pctLsingle", f1(100 * sum(int(r["L"]) for r in un) / len(un)), F)
F = "resultados/p3/cierres_por_problema_todos_resumen.csv"
for r in rows(RES, "p3", "cierres_por_problema_todos_resumen.csv"):
    k = f"closeprob:{r['brazo']}"
    put(k + ":n", r["problemas_mixtos"], F); put(k + ":dif", sg(100 * float(r["dif_media_un_cierre_menos_varios"])), F + " (x100, puntos)")
    put(k + ":ci", ci(100 * float(r["ic95_bajo"]), 100 * float(r["ic95_alto"])), F + " (x100)")
    put(k + ":gx", r["gana_un_cierre"], F); put(k + ":gy", r["gana_varios"], F); put(k + ":ties", r["empates"], F)

# ---------------- 9. Mejora / empeora por problema (exploratorio) ----------------
for t, ref, f in (("math", "N", "cambios_math_nothink_por_brazo.csv"), ("gsm8k", "N", "cambios_gsm8k_nothink_por_brazo.csv"), ("ifeval", "N", "cambios_ifeval_nothink_por_brazo.csv"),
                  ("gsm8k", "T", "cambios_gsm8k_think_por_brazo.csv"), ("ifeval", "T", "cambios_ifeval_think_por_brazo.csv")):
    R = rows(RES, "p3", f); F = "resultados/p3/" + f
    for campo, nom in (("pct_empeora", "worse"), ("pct_mejora", "better"), ("neto_mejora_menos_empeora", "net")):
        v = [float(r[campo]) for r in R]; g = sg if nom == "net" else f1
        put(f"chg:{t}:{ref}:{nom}:min", g(min(v)), F); put(f"chg:{t}:{ref}:{nom}:max", g(max(v)), F)

# ---------------- 10. Mejor brazo y costo ----------------
mb = rows(RES, "p3", "mejor_brazo.csv"); put("best:arm", mb[0]["brazo"], "resultados/p3/mejor_brazo.csv")
F = "resultados/costo_diagnostico.csv"; C = rows(RES, "costo_diagnostico.csv")
inf = [r for r in C if r["etapa"].startswith("Informado")]; ob = [r for r in C if r["etapa"].startswith("Opus + barrido")]
put("cost:inf:gpu", f1(sum(float(r["gpu_min"]) for r in inf)), F); put("cost:inf:usd", f"{sum(float(r['usd_equivalente_reportado']) for r in inf):.2f}", F)
put("cost:inf:n", len(inf), F)
put("cost:inf:hang", f1(re.search(r"incluye ([\d.]+) min", next(r["gpu_origen"] for r in inf if "colgada" in r["gpu_origen"])).group(1)), F)
put("cost:ob:usd", f"{sum(float(r['usd_equivalente_reportado']) for r in ob):.2f}", F); put("cost:ob:n", len(ob), F)
put("cost:sweep:gpu", f1(next(float(r["gpu_min"]) for r in C if r["etapa"].startswith("Barrido"))), F)
put("cost:grad:gpu", f1(next(float(r["gpu_min"]) for r in C if r["etapa"].startswith("Brazo d"))), F)
put("cost:saved:gpu", f1(next(float(r["gpu_min"]) for r in C if r["etapa"].startswith("Respuestas guardadas"))), F)
ent = collections.defaultdict(list)
for f in glob.glob(os.path.join(RES, "p3", "entrenamiento", "*.json")):
    j = json.load(open(f, encoding="utf-8")); ent[os.path.basename(f)[0]].append(j["segundos"])
assert all(len(v) == 4 for v in ent.values()) and len(ent) == 6
allt = [x for v in ent.values() for x in v]
put("cost:train:min", f1(min(allt) / 60), "resultados/p3/entrenamiento/*.json"); put("cost:train:max", f1(max(allt) / 60), "resultados/p3/entrenamiento/*.json")
ev = collections.defaultdict(float)
for f in glob.glob(os.path.join(RES, "p3", "eval", "*_T06_s*.csv.meta.json")):
    b = re.match(r"(?:p\d_(?:gsm8k|ifeval)_)?([a-f])\d_T06", os.path.basename(f))
    if b: ev[b.group(1)] += json.load(open(f, encoding="utf-8"))["segundos"]
assert len(ev) == 6
put("cost:eval:min", f1(min(ev.values()) / 60 / 4), "resultados/p3/eval/*meta.json (minutos por LoRA, 3 tareas a 0.6)")
put("cost:eval:max", f1(max(ev.values()) / 60 / 4), "resultados/p3/eval/*meta.json (minutos por LoRA, 3 tareas a 0.6)")

# ---------------- 11. Extras para el texto ----------------
for (t, tp, m), r in MOD.items():
    sem = [int(x) for x in r["por_semilla"].split(" / ")]
    put(f"mod:{t}:{tp}:{m}:seedspan", max(sem) - min(sem), "resultados/revision/rev_por_modelo.csv (max - min por semilla)")
F = "resultados/barrido/dano_general_resumen.csv"
d0 = next(r for r in rows(RES, "barrido", "dano_general_resumen.csv") if r["capa"] == "0" and r["variante"] == "cero" and r["ventana"] == "antes")
put("damage:0:rank", d0["puesto_kl"], F); put("damage:0:kl", d0["kl_medio"], F); put("damage:0:ci", f"[{d0['kl_ic_bajo']}, {d0['kl_ic_alto']}]", F)

# Las lecturas (solid / indication / no) que el TEXTO afirma con palabras. Si los datos cambian, esto falla y obliga a reescribir.
EXPECT = {("main", "math", "b", "c"): "no", ("main", "math", "b", "d"): "no", ("all", "math", "b", "a"): "indication",
          **{("vsN", "math", a, "N"): "no" for a in ARMS}, **{("vsN", "gsm8k", a, "N"): "solid" for a in ARMS},
          **{("vsN", "ifeval", a, "N"): "no" for a in ARMS}, **{("vsP", "gsm8k", a, "P"): "no" for a in ARMS},
          ("vsP", "math", "e", "P"): "solid", **{("vsP", "math", a, "P"): "no" for a in "abcdf"},
          **{("vsP", "ifeval", a, "P"): "solid" for a in "bcd"}, **{("vsP", "ifeval", a, "P"): "indication" for a in "af"}, ("vsP", "ifeval", "e", "P"): "no",
          ("vsa", "math", "c", "a"): "solid", ("vsa", "math", "e", "a"): "solid", ("vsa", "math", "b", "a"): "indication",
          ("vsa", "math", "d", "a"): "no", ("vsa", "math", "f", "a"): "no",
          ("pairs", "math", "e", "d"): "indication", ("pairs", "math", "f", "e"): "no", ("pairs", "math", "e", "b"): "no",
          ("central", "math", "f", "e"): "indication"}
for (fam, t, X, Y), v in EXPECT.items():
    got = lectura(fam, t, "06", X, Y)
    assert got == v, f"el texto dice '{v}' para {fam}:{t}:{X}-{Y}, los datos dan '{got}'"
# Otras afirmaciones del texto que dependen de los datos
assert float(CMP[("math", "06", "e", "d")]["ic95_dosvias_bajo"]) == 0.0
assert all(float(HOLM[("vsNall", "gsm8k", a, "N")]["holm_signos"]) < 0.05 for a in ARMS)
assert all(float(RU[("math", "N")][a]["ic95_sim_bajo"]) <= 0 for a in "bcdef") and float(RU[("math", "N")]["a"]["ic95_sim_bajo"]) > 0
assert all(float(RU[("ifeval", "N")][a]["ic95_sim_bajo"]) > 0 for a in ARMS + "P")
assert max(float(MOD[("math", "06", a)]["pct_correctas"]) for a in ARMS) == float(MOD[("math", "06", "e")]["pct_correctas"])
assert all(float(CL[("math", a)]["pct_respuesta_limpia_1_cierre_sin_limite"]) > float(CL[("math", "b")]["pct_respuesta_limpia_1_cierre_sin_limite"]) for a in "acdefP")
G = {r["modelo"]: float(r["pct_correctas_modelo_donde_original_al_limite"]) for r in rows(REV, "rev_ganancia_separada.csv") if r["tarea"] == "math"}
assert min(G[a] for a in ARMS) == G["a"] and max(G[a] for a in ARMS) == G["e"]          # "the arms score (a)--(e)"
assert all(float(MOD[("math", "06", a)]["pct_al_limite"]) > float(MOD[("math", "06", "a")]["pct_al_limite"]) for a in "bcdef")
assert float(MOD[("math", "06", "P")]["pct_correctas_entre_terminadas"]) > max(float(MOD[("math", "06", a)]["pct_correctas_entre_terminadas"]) for a in ARMS)
assert HOLM[("main", "math", "b", "c")]["holm_signos"] == HOLM[("main", "math", "b", "d")]["holm_signos"]   # "Holm ... for both"
assert all(float(CMP[("ifeval", "06", a, "P")]["dif_puntos"]) < 0 for a in ARMS)                       # "all six arms are lower"
assert all(float(CMP[("math", "06", a, "N")]["dif_puntos"]) < float(CMP[("math", "06", "e", "N")]["dif_puntos"]) for a in "abcdf")  # "the closest is (e)"
assert float(CMP[("math", "06", "f", "e")]["dif_puntos"]) < 0                                            # "the rule did at least as well"

# ======================= TABLAS =======================
NAME = {"a": "(a) 24 layers", "b": "(b) Opus, informed", "c": "(c) Random placebo", "d": "(d) Gradient rule", "e": "(e) Sweep rule",
        "f": "(f) Opus + sweep", "N": "Original, no-thinking", "T": "Original, thinking", "P": "\\texttt{p50c} (MIT edit), thinking"}
RD = {"solid": "solid", "indication": "indication", "no": "--"}


def tabla(nombre, cols, cuerpo, nota=None):
    txt = [f"% Generado por make_results.py. No editar a mano.", f"\\begin{{tabular}}{{{cols}}}", "\\toprule"] + cuerpo + ["\\bottomrule", "\\end{tabular}"]
    open(os.path.join(OUT, nombre), "w", encoding="utf-8", newline="\n").write("\n".join(txt) + "\n")


def R(k): return K[k]


# T1: MATH a 0.6 por modelo
c = ["\\textbf{Model} & \\textbf{Accuracy \\% [95\\% CI]} & \\textbf{Per seed} & \\textbf{At limit \\%} & \\textbf{Tokens} & \\textbf{$>$1 close \\%} & \\textbf{Acc. if finished \\%} \\\\", "\\midrule"]
for m in "abcdefNTP":
    k = f"mod:math:06:{m}"
    if m == "N": c.append("\\midrule")
    c.append(f"{NAME[m]} & {R(k+':acc')} {R(k+':ci')} & {R(k+':seeds')} & {R(k+':lim')} & {R(k+':tok')} & {R(k+':multi')} & {R(k+':accfin')} \\\\")
tabla("tab_models_math.tex", "lrcrrrr", c)

# T2: comparacion principal
c = ["\\textbf{Comparison} & \\textbf{Diff. [95\\% CI]} & \\textbf{p} & \\textbf{p Holm} & \\textbf{Per-problem CI} & \\textbf{p McNemar} & \\textbf{Reading} \\\\", "\\midrule"]
for X, Y, fam, lab in (("b", "c", "main", "(b) $-$ (c) random"), ("b", "d", "main", "(b) $-$ (d) gradient"), ("b", "a", "all", "(b) $-$ (a) 24 layers")):
    k = f"cmp:math:06:{X}:{Y}"
    c.append(f"{lab} & {R(k+':dif')} {R(k+':ci')} & {R(k+':p')} & {R(f'holm:{fam}:math:{X}:{Y}:hs')} & {R(k+':pci')} & {R(k+':mc')} & {RD[R(f'read:{fam}:math:{X}:{Y}')]} \\\\")
tabla("tab_main.tex", "lrrrrrl", c)

# T3: cada brazo contra sin thinking y contra p50c (MATH 0.6)
c = ["& \\multicolumn{4}{c}{\\textbf{Arm $-$ original, no-thinking} (pre-specified)} & \\multicolumn{4}{c}{\\textbf{Arm $-$ \\texttt{p50c}} (exploratory)} \\\\",
     "\\cmidrule(lr){2-5}\\cmidrule(lr){6-9}",
     "\\textbf{Arm} & \\textbf{Diff. [95\\% CI]} & \\textbf{p} & \\textbf{p Holm} & \\textbf{Reading} & \\textbf{Diff. [95\\% CI]} & \\textbf{p} & \\textbf{p Holm} & \\textbf{Reading} \\\\", "\\midrule"]
for a in ARMS:
    kn = f"cmp:math:06:{a}:N"; kp = f"cmp:math:06:{a}:P"
    c.append(f"({a}) & {R(kn+':dif')} {R(kn+':ci')} & {R(kn+':p')} & {R(f'holm:vsN:math:{a}:N:hs')} & {RD[R(f'read:vsN:math:{a}:N')]} & {R(kp+':dif')} {R(kp+':ci')} & {R(kp+':p')} & {R(f'holm:vsP:math:{a}:P:hs')} & {RD[R(f'read:vsP:math:{a}:P')]} \\\\")
tabla("tab_vsref_math.tex", "lrrrlrrrl", c)

# T4: MATH a 1.0
c = ["\\textbf{Model} & \\textbf{Accuracy \\% [95\\% CI]} & \\textbf{At limit \\%} & \\textbf{Tokens} \\\\", "\\midrule"]
for m in "eNTP":
    k = f"mod:math:10:{m}"; c.append(f"{NAME[m]} & {R(k+':acc')} {R(k+':ci')} & {R(k+':lim')} & {R(k+':tok')} \\\\")
tabla("tab_math_t10.tex", "lrrr", c)

# T5: GSM8K e IFEval por modelo
c = ["& \\multicolumn{3}{c}{\\textbf{GSM8K}} & \\multicolumn{3}{c}{\\textbf{IFEval}} \\\\", "\\cmidrule(lr){2-4}\\cmidrule(lr){5-7}",
     "\\textbf{Model} & \\textbf{Accuracy \\% [95\\% CI]} & \\textbf{At limit \\%} & \\textbf{Tokens} & \\textbf{Accuracy \\% [95\\% CI]} & \\textbf{At limit \\%} & \\textbf{Tokens} \\\\", "\\midrule"]
for m in "abcdefNTP":
    g = f"mod:gsm8k:06:{m}"; i = f"mod:ifeval:06:{m}"
    if m == "N": c.append("\\midrule")
    c.append(f"{NAME[m]} & {R(g+':acc')} {R(g+':ci')} & {R(g+':lim')} & {R(g+':tok')} & {R(i+':acc')} {R(i+':ci')} & {R(i+':lim')} & {R(i+':tok')} \\\\")
tabla("tab_models_transfer.tex", "lrrrrrr", c)

# T6: GSM8K e IFEval, comparaciones
c = ["& \\multicolumn{4}{c}{\\textbf{GSM8K}} & \\multicolumn{4}{c}{\\textbf{IFEval}} \\\\", "\\cmidrule(lr){2-5}\\cmidrule(lr){6-9}",
     "\\textbf{Arm} & \\textbf{$-$ no-thinking} & \\textbf{p Holm} & \\textbf{$-$ \\texttt{p50c}} & \\textbf{p Holm} & \\textbf{$-$ no-thinking} & \\textbf{p Holm} & \\textbf{$-$ \\texttt{p50c}} & \\textbf{p Holm} \\\\", "\\midrule"]
for a in ARMS:
    cel = []
    for t in ("gsm8k", "ifeval"):
        for Y, fam in (("N", "vsN"), ("P", "vsP")):
            k = f"cmp:{t}:06:{a}:{Y}"; rd = R(f"read:{fam}:{t}:{a}:{Y}")
            mark = "$^{\\dagger}$" if rd == "solid" else ("$^{\\ast}$" if rd == "indication" else "")
            cel.append(f"{R(k+':dif')} {R(k+':ci')}{mark} & {R(f'holm:{fam}:{t}:{a}:{Y}:hs')}")
    c.append(f"({a}) & " + " & ".join(cel) + " \\\\")
tabla("tab_cmp_transfer.tex", "lrrrrrrrr", c)

# T7: exploratorio, parejas entre brazos de 4 capas y contra (a)
c = ["\\textbf{Comparison} & \\textbf{Diff. [95\\% CI]} & \\textbf{p} & \\textbf{p Holm} & \\textbf{Holm family} & \\textbf{Reading} \\\\", "\\midrule"]
for X, Y, fam, famlab in (("e", "d", "pairs", "pairs of 4-layer arms (9)"), ("f", "e", "pairs", "pairs of 4-layer arms (9)"), ("e", "b", "pairs", "pairs of 4-layer arms (9)"),
                          ("f", "c", "pairs", "pairs of 4-layer arms (9)"), ("d", "c", "pairs", "pairs of 4-layer arms (9)"), ("e", "c", "pairs", "pairs of 4-layer arms (9)"),
                          ("f", "d", "pairs", "pairs of 4-layer arms (9)"),
                          ("c", "a", "vsa", "4-layer arm vs.\\ (a) (5)"), ("e", "a", "vsa", "4-layer arm vs.\\ (a) (5)"), ("d", "a", "vsa", "4-layer arm vs.\\ (a) (5)"),
                          ("f", "a", "vsa", "4-layer arm vs.\\ (a) (5)"), ("b", "a", "vsa", "4-layer arm vs.\\ (a) (5)")):
    k = f"cmp:math:06:{X}:{Y}"
    c.append(f"({X}) $-$ ({Y}) & {R(k+':dif')} {R(k+':ci')} & {R(k+':p')} & {R(f'holm:{fam}:math:{X}:{Y}:hs')} & {famlab} & {RD[R(f'read:{fam}:math:{X}:{Y}')]} \\\\")
tabla("tab_explore.tex", "lrrrll", c)

# T8: respuestas limpias en MATH
c = ["\\textbf{Model} & \\textbf{Clean \\% [95\\% CI]} & \\textbf{Per seed} & \\textbf{Acc. among clean \\%} & \\textbf{Acc. among $>$1 close \\%} \\\\", "\\midrule"]
for m in "abcdefP":
    k = f"clean:math:{m}"
    if m == "P": c.append("\\midrule")
    c.append(f"{NAME[m]} & {R(k+':pct')} {R(k+':ci')} & {R(k+':seeds')} & {R(k+':acc')} & {R(k+':accmulti')} \\\\")
tabla("tab_clean.tex", "lrcrr", c)

# T9: ganancia separada (MATH)
c = ["\\textbf{Model} & \\textbf{Where the original looped} & \\textbf{Where the original finished} \\\\", "\\midrule"]
for m in "abcdefNP":
    k = f"gain:math:{m}"; c.append(f"{NAME[m]} & {R(k+':acclim')} & {R(k+':accfin')} \\\\")
tabla("tab_gain.tex", "lrr", c)

# ======================= SALIDA Y CONTROL =======================
with open(os.path.join(OUT, "resultados.tex"), "w", encoding="utf-8", newline="\n") as fh:
    fh.write("% Generado por paper2/paper/scripts/make_results.py. NO EDITAR A MANO.\n")
    fh.write("\\makeatletter\n\\newcommand{\\R}[1]{\\ifcsname R@#1\\endcsname\\csname R@#1\\endcsname\\else\\textbf{??#1??}\\fi}\n")
    for k, v in K.items():
        fh.write(f"\\expandafter\\def\\csname R@{k}\\endcsname{{{v}}}% {SRC[k]}\n")
    fh.write("\\makeatother\n")


def check_keys():
    tex = open(os.path.join(RAIZ, "paper", "latex", "main.tex"), encoding="utf-8").read()
    usadas = set(re.findall(r"\\R\{([^}]+)\}", tex))
    faltan = sorted(u for u in usadas if u not in K)
    assert not faltan, "claves usadas en main.tex que no existen: " + ", ".join(faltan)
    return len(usadas)


print(len(K), "claves de resultados;", check_keys(), "usadas en main.tex; 9 tablas")
