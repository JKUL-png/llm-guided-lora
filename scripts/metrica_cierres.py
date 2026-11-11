"""Métrica de cierres por brazo y semilla (sin GPU). Uso: python metrica_cierres.py <carpeta eval> <salida.csv>
Por cada CSV <brazo><semilla>_T<temp>_s<semilla>.csv: % de respuestas con varios </think>, y % de correctas
separando las que cierran 0 veces, 1 vez, o varias veces (regla de la decisión 14: vale lo que sigue al ÚLTIMO </think>)."""
import csv, glob, os, re, sys
filas = []
for f in sorted(glob.glob(os.path.join(sys.argv[1], "*_T??_s?.csv"))):
    m = re.match(r"([a-z])(\d)_T(\d+)_s(\d)\.csv$", os.path.basename(f))
    if not m or "control" in f: continue
    X = list(csv.DictReader(open(f, encoding="utf-8")))
    g = {"0": [x for x in X if int(x["cierres"]) == 0], "1": [x for x in X if int(x["cierres"]) == 1], "varios": [x for x in X if int(x["cierres"]) > 1]}
    n = len(X)
    pc = lambda L: round(100 * sum(int(x["correcto"]) for x in L) / len(L), 1) if L else ""
    filas.append(dict(brazo=m[1], semilla=m[4], temperatura=m[3], n=n, pct_varios_cierres=round(100 * len(g["varios"]) / n, 1),
                      n_sin_cierre=len(g["0"]), n_un_cierre=len(g["1"]), n_varios_cierres=len(g["varios"]),
                      pct_correctas_total=pc(X), pct_correctas_sin_cierre=pc(g["0"]), pct_correctas_un_cierre=pc(g["1"]),
                      pct_correctas_varios_cierres=pc(g["varios"]), pct_al_limite=round(100 * sum(int(x["llego_limite"]) for x in X) / n, 1)))
with open(sys.argv[2], "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=filas[0].keys()); w.writeheader(); w.writerows(filas)
for r in filas: print(r)
