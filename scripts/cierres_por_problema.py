"""Separa dificultad de cierres (sin GPU). Uso: python cierres_por_problema.py <brazo> <salida.csv>
Para cada problema donde unas semillas cerraron una vez y otras varias: acierto de las semillas con un cierre vs. las de varios cierres
(mismo problema, así la dificultad queda fija). Resumen: promedio de la diferencia por problema, IC 95% bootstrap por problema
(10,000, semilla 20261107), y en cuántos problemas gana cada lado (los empates no cuentan)."""
import csv, glob, random, re, sys
from collections import defaultdict
b = sys.argv[1]
por = defaultdict(list)
for f in sorted(glob.glob(f"resultados/p3/eval/{b}?_T06_s?.csv")):
    for x in csv.DictReader(open(f, encoding="utf-8")):
        por[x["id"]].append((int(x["cierres"]), int(x["correcto"])))
filas = []
for i, v in sorted(por.items()):
    u = [c for k, c in v if k == 1]; m = [c for k, c in v if k > 1]
    if u and m:
        filas.append(dict(id=i, semillas_un_cierre=len(u), semillas_varios=len(m), acierto_un_cierre=round(sum(u) / len(u), 3), acierto_varios=round(sum(m) / len(m), 3)))
d = [f["acierto_un_cierre"] - f["acierto_varios"] for f in filas]
R = random.Random(20261107)
bs = sorted(sum(R.choice(d) for _ in d) / len(d) for _ in range(10000))
gana_u, gana_m = sum(x > 0 for x in d), sum(x < 0 for x in d)
res = dict(brazo=b, problemas_mixtos=len(d), dif_media_un_cierre_menos_varios=round(sum(d) / len(d), 3), ic95_bajo=round(bs[250], 3), ic95_alto=round(bs[9749], 3),
           gana_un_cierre=gana_u, gana_varios=gana_m, empates=len(d) - gana_u - gana_m)
with open(sys.argv[2], "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=filas[0].keys()); w.writeheader(); w.writerows(filas)
with open(sys.argv[2].replace(".csv", "_resumen.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=res.keys()); w.writeheader(); w.writerow(res)
print(res)
