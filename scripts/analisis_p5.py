"""Análisis de P5a (GSM8K e IFEval, 24 LoRA a 0.6 thinking). Sin GPU, Python estándar. Uso (desde paper2/): python scripts/analisis_p5.py <gsm8k|ifeval> <N|T|NT>
Mismas pruebas que analisis_etapa2.py (PLAN §6): bootstrap por problema (10,000, random.Random(20261107), pct 2.5/97.5), McNemar exacto bilateral sobre
parejas (problema, semilla) y Holm dentro de cada familia. Referencias: N = original SIN thinking a 0.6 (P6b); T = original CON thinking a 0.6 (s0 paper 1, s1-3 P6).
Familias:
  - vs_sin_thinking (FIJADA_EN_PLAN §6, 'cada brazo contra el original sin thinking, en cada tarea'): 6 brazos, Holm de 6, metrica correctas.
  - vs_con_thinking (EXPLORATORIO: olvido = brazo vs original en el mismo modo; Holm de 6).
  - secundaria (b)-(a) (FIJADA); (b)-(c) y (b)-(d) en GSM8K/IFEval = EXPLORATORIO (el PLAN las fija para MATH).
Salida: resultados/p3/p5_<tarea>_por_brazo.csv y p5_<tarea>_comparaciones.csv"""
import csv, math, random, sys
P3 = "resultados/p3"; t = sys.argv[1]; refs = sys.argv[2]
IDS = [l.strip() for l in open(f"../datos/{t}_subset100_ids.txt", encoding="utf-8") if l.strip() and not l.startswith("#")]
NOM = {"a": "(a) 24 capas", "b": "(b) Opus informado", "c": "(c) placebo", "d": "(d) gradiente", "e": "(e) barrido", "f": "(f) Opus+barrido", "T": "original con thinking", "N": "original sin thinking"}
RUTA = {"N": lambda s: f"{P3}/eval/p6b_{t}_orig_nothink_T06_s{s}.csv",
        "T": lambda s: f"resultados/calificacion/{t}_orig_think_T06_s0.csv" if s == 0 else f"{P3}/eval/p6_{t}_orig_think_T06_s{s}.csv"}
for b in "abcdef": RUTA[b] = (lambda b: lambda s: f"{P3}/eval/p5_{t}_{b}{s}_T06_s{s}.csv")(b)
def cargar(b, s):
    X = {r["id"]: r for r in csv.DictReader(open(RUTA[b](s), encoding="utf-8"))}
    assert sorted(X) == sorted(IDS) and all(r.get("error_calificacion", "0") in ("0", "") for r in X.values()), RUTA[b](s)
    return X
bs_ = "abcdef" + refs
D = {b: {s: cargar(b, s) for s in range(4)} for b in bs_}
M = {"correctas": "correcto", "al_limite": "llego_limite"}
mat = lambda b, m: [[int(D[b][s][i][M[m]]) for s in range(4)] for i in IDS]
def boot(v):
    R = random.Random(20261107); n = len(v)
    q = sorted(sum(v[R.randrange(n)] for _ in range(n)) / n for _ in range(10000)); return round(100 * q[249], 2), round(100 * q[9749], 2)
def mcn(x, y):
    b = sum(x[i][s] == 1 and y[i][s] == 0 for i in range(100) for s in range(4)); c = sum(x[i][s] == 0 and y[i][s] == 1 for i in range(100) for s in range(4)); n = b + c
    return b, c, (1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, k) for k in range(min(b, c) + 1)) / 2 ** n))
def holm(ps):
    o = sorted(range(len(ps)), key=lambda i: ps[i]); out = [0] * len(ps); m = 0
    for r, i in enumerate(o): m = max(m, (len(ps) - r) * ps[i]); out[i] = min(1.0, m)
    return out
por = []
for b in bs_:
    f = dict(tarea=t, brazo=b, nombre=NOM[b], n=400)
    for m in M:
        v = [sum(r) / 4 for r in mat(b, m)]; lo, hi = boot(v); f.update({f"pct_{m}": round(sum(v), 2), f"ic95_{m}_bajo": lo, f"ic95_{m}_alto": hi})
    f["tokens_medios"] = round(sum(int(D[b][s][i]["tokens"]) for s in range(4) for i in IDS) / 400, 1)
    f["pct_varios_cierres"] = round(100 * sum(int(D[b][s][i]["cierres"]) > 1 for s in range(4) for i in IDS) / 400, 2)
    f["pct_por_semilla"] = " / ".join(str(sum(int(D[b][s][i]["correcto"]) for i in IDS)) for s in range(4)); por.append(f)
comp = []
def fam(nombre, estado, pares):
    rows = []
    for m in M:
        for X, Y in pares:
            x, y = mat(X, m), mat(Y, m); d = [(sum(x[i]) - sum(y[i])) / 4 for i in range(100)]; lo, hi = boot(d); b_, c_, p = mcn(x, y)
            rows.append(dict(tarea=t, familia=nombre, estado=estado if m == "correctas" else "EXPLORATORIO", metrica=m, comparacion=f"{NOM[X]} - {NOM[Y]}",
                             pct_X=round(sum(map(sum, x)) / 4, 2), pct_Y=round(sum(map(sum, y)) / 4, 2), dif_puntos=round(sum(d), 2), ic95_bajo=lo, ic95_alto=hi, solo_X=b_, solo_Y=c_, p_mcnemar=round(p, 6)))
    for m in M:
        sub = [r for r in rows if r["metrica"] == m]; h = holm([r["p_mcnemar"] for r in sub])
        for r, hp in zip(sub, h): r["p_holm"] = round(hp, 6); r["tamano_familia"] = len(sub); r["sobrevive_holm_0.05"] = "si" if hp < 0.05 else "no"
    comp.extend(rows)
if "N" in refs: fam("vs_sin_thinking", "FIJADA_EN_PLAN", [(b, "N") for b in "abcdef"])
if "T" in refs: fam("vs_con_thinking", "EXPLORATORIO", [(b, "T") for b in "abcdef"])
fam("secundaria_b_vs_a", "FIJADA_EN_PLAN", [("b", "a")]); fam("exploratoria_b_vs_c_d", "EXPLORATORIO", [("b", "c"), ("b", "d")])
for nom, F in [("por_brazo", por), ("comparaciones", comp)]:
    with open(f"{P3}/p5_{t}_{nom}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(F[0].keys())); w.writeheader(); w.writerows(F)
for r in por: print(r["brazo"], r["pct_correctas"], (r["ic95_correctas_bajo"], r["ic95_correctas_alto"]), "lim", r["pct_al_limite"], "tok", r["tokens_medios"], "vc", r["pct_varios_cierres"], r["pct_por_semilla"])
for r in comp:
    if r["metrica"] == "correctas": print(r["familia"], r["comparacion"], r["pct_X"], r["pct_Y"], r["dif_puntos"], (r["ic95_bajo"], r["ic95_alto"]), r["solo_X"], r["solo_Y"], "p", r["p_mcnemar"], "holm", r["p_holm"], r["sobrevive_holm_0.05"])
