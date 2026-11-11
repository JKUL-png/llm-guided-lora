"""EXPLORATORIO (no está en el PLAN §6; pedido por el usuario el 2026-11-09 para el análisis de P5, sin cambiar las pruebas fijadas).
Por brazo y tarea: contra el ORIGINAL, por problema y semilla (semilla s del brazo contra semilla s del original; 100 problemas x 4 semillas = 400 parejas):
  - empeora = el original acierta y el brazo falla (correcto -> incorrecto)
  - mejora  = el original falla y el brazo acierta (incorrecto -> correcto)
  - igual   = mismo resultado.
Se reporta como % de las 400 parejas y como % condicionado (empeora / parejas donde el original acierta; mejora / parejas donde falla).
IC 95% por bootstrap de problemas (10,000, random.Random(20261107)). Luego, (a) 24 capas contra cada brazo de 4 capas (b..f): diferencia
de empeora% y de mejora% con IC por bootstrap de problemas pareado. SIN corrección de Holm (exploratorio: leer el IC, no un p).
Uso (desde paper2/): python scripts/cambios_vs_original.py <math|gsm8k|ifeval> [think|nothink]
  - 'think' = original CON thinking a 0.6 (mismo modo que los LoRA); 'nothink' = original SIN thinking a 0.6. Por omisión, ambos.
  - math se usa de ensayo del script (ya estaba analizado); gsm8k e ifeval necesitan que la etapa 4 haya terminado.
Salida: resultados/p3/cambios_<tarea>_<ref>_por_brazo.csv y _comparaciones.csv."""
import csv, random, sys
from collections import defaultdict
P3 = "resultados/p3"
tarea = sys.argv[1]; refs = [sys.argv[2]] if len(sys.argv) > 2 else ["think", "nothink"]
IDS = [l.strip() for l in open(f"../datos/{ {'math': 'math500', 'gsm8k': 'gsm8k', 'ifeval': 'ifeval'}[tarea] }_subset100_ids.txt", encoding="utf-8") if l.strip() and not l.startswith("#")]
assert len(IDS) == 100


def arch_original(ref, s):
    if tarea == "math": return f"resultados/calificacion/math_orig_{ref}_T06_s{s}.csv"
    if ref == "think": return f"resultados/calificacion/{tarea}_orig_think_T06_s0.csv" if s == 0 else f"{P3}/eval/p6_{tarea}_orig_think_T06_s{s}.csv"
    return f"{P3}/eval/p6b_{tarea}_orig_nothink_T06_s{s}.csv"


def arch_brazo(b, s):
    return f"{P3}/eval/{b}{s}_T06_s{s}.csv" if tarea == "math" else f"{P3}/eval/p5_{tarea}_{b}{s}_T06_s{s}.csv"


def cargar(f):
    X = {r["id"]: r for r in csv.DictReader(open(f, encoding="utf-8"))}
    assert sorted(X) == sorted(IDS), f"{f}: ids distintos del subconjunto fijo"
    assert all(r.get("error_calificacion", "0") in ("0", "") for r in X.values()), f"{f}: error de calificación"
    return [int(X[i]["correcto"]) for i in IDS]


def boot(f, n=100, B=10000):
    R = random.Random(20261107); v = []
    for _ in range(B):
        idx = [R.randrange(n) for _ in range(n)]; v.append(f(idx))
    v.sort(); return round(v[249], 2), round(v[9749], 2)


def conteos(C, O, idx):   # C, O: [problema][semilla]
    w = m = ok_o = ko_o = 0
    for i in idx:
        for s in range(4):
            if O[i][s]: ok_o += 1; w += (not C[i][s])
            else: ko_o += 1; m += C[i][s]
    return w, m, ok_o, ko_o


filas, comp = [], []
for ref in refs:
    O_ = [cargar(arch_original(ref, s)) for s in range(4)]
    O = [[O_[s][i] for s in range(4)] for i in range(100)]
    B = {}
    for b in "abcdef":
        C_ = [cargar(arch_brazo(b, s)) for s in range(4)]
        B[b] = [[C_[s][i] for s in range(4)] for i in range(100)]
    for b in "abcdef":
        C = B[b]; allp = range(100); w, m, ok_o, ko_o = conteos(C, O, allp)
        pe = lambda idx: 100 * conteos(C, O, idx)[0] / 400
        pm = lambda idx: 100 * conteos(C, O, idx)[1] / 400
        ce = lambda idx: (lambda c: 100 * c[0] / max(c[2], 1))(conteos(C, O, idx))
        cm = lambda idx: (lambda c: 100 * c[1] / max(c[3], 1))(conteos(C, O, idx))
        r = dict(tarea=tarea, referencia=f"original_{ref}_T06", brazo=b, parejas=400, original_acierta=ok_o, original_falla=ko_o,
                 pct_empeora=round(pe(allp), 2), pct_mejora=round(pm(allp), 2), pct_igual=round(100 - pe(allp) - pm(allp), 2),
                 pct_empeora_dado_original_acierta=round(ce(allp), 2), pct_mejora_dado_original_falla=round(cm(allp), 2),
                 neto_mejora_menos_empeora=round(pm(allp) - pe(allp), 2), estado="EXPLORATORIO")
        for nom, fn in [("pct_empeora", pe), ("pct_mejora", pm), ("neto", lambda idx: pm(idx) - pe(idx))]:
            lo, hi = boot(fn); r[f"ic95_{nom}_bajo"], r[f"ic95_{nom}_alto"] = lo, hi
        filas.append(r)
    for b in "bcdef":     # (a) 24 capas contra cada brazo de 4 capas
        for nom, fn in [("pct_empeora", lambda C, idx: 100 * conteos(C, O, idx)[0] / 400),
                        ("pct_mejora", lambda C, idx: 100 * conteos(C, O, idx)[1] / 400)]:
            d = lambda idx: fn(B[b], idx) - fn(B["a"], idx)
            lo, hi = boot(d); full = d(range(100))
            comp.append(dict(tarea=tarea, referencia=f"original_{ref}_T06", metrica=nom, comparacion=f"({b}) 4 capas - (a) 24 capas",
                             dif_puntos=round(full, 2), ic95_bajo=lo, ic95_alto=hi, cruza_cero="si" if lo <= 0 <= hi else "no", estado="EXPLORATORIO"))
for nom, F in [("por_brazo", filas), ("comparaciones", comp)]:
    for ref in refs:
        sub = [r for r in F if r["referencia"] == f"original_{ref}_T06"]
        with open(f"{P3}/cambios_{tarea}_{ref}_{nom}.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(sub[0].keys())); w.writeheader(); w.writerows(sub)
for r in filas: print(r["referencia"], r["brazo"], "empeora", r["pct_empeora"], "mejora", r["pct_mejora"], "igual", r["pct_igual"], "neto", r["neto_mejora_menos_empeora"])
for r in comp: print(r["referencia"], r["metrica"], r["comparacion"], r["dif_puntos"], (r["ic95_bajo"], r["ic95_alto"]), r["cruza_cero"])
