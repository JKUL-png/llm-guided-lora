"""EXPLORATORIO (no estaba en PLAN.md §6). Generaliza cierres_por_problema.py a los 6 brazos (sin GPU).
Uso (desde paper2/): python scripts/cierres_por_problema_todos.py
Por brazo: en los problemas donde unas semillas cerraron una vez y otras varias, acierto con un cierre menos acierto con
varios (mismo problema, así la dificultad queda fija); IC 95% bootstrap por problema (10,000, random.Random(20261107)),
y cuántos problemas gana cada lado. Misma lógica exacta que cierres_por_problema.py (para (a) da el mismo resultado).
Fila extra 'todos': junta los 6 brazos (cada problema x brazo es una unidad; EXPLORATORIO también).
Escribe resultados/p3/cierres_por_problema_todos.csv (detalle) y cierres_por_problema_todos_resumen.csv."""
import csv, glob, random
from collections import defaultdict


def resumen(nombre, d):
    R = random.Random(20261107)
    bs = sorted(sum(R.choice(d) for _ in d) / len(d) for _ in range(10000))
    gu, gm = sum(x > 0 for x in d), sum(x < 0 for x in d)
    return dict(estado="EXPLORATORIO", brazo=nombre, problemas_mixtos=len(d), dif_media_un_cierre_menos_varios=round(sum(d) / len(d), 3),
                ic95_bajo=round(bs[250], 3), ic95_alto=round(bs[9749], 3), gana_un_cierre=gu, gana_varios=gm, empates=len(d) - gu - gm)


det, res, todos = [], [], []
for b in "abcdef":
    por = defaultdict(list)
    for f in sorted(glob.glob(f"resultados/p3/eval/{b}?_T06_s?.csv")):
        for x in csv.DictReader(open(f, encoding="utf-8")):
            por[x["id"]].append((int(x["cierres"]), int(x["correcto"])))
    assert len(por) == 100 and all(len(v) == 4 for v in por.values())
    d = []
    for i, v in sorted(por.items()):
        u = [c for k, c in v if k == 1]; m = [c for k, c in v if k > 1]
        if u and m:
            fila = dict(brazo=b, id=i, semillas_un_cierre=len(u), semillas_varios=len(m), acierto_un_cierre=round(sum(u) / len(u), 3), acierto_varios=round(sum(m) / len(m), 3))
            det.append(fila); d.append(fila["acierto_un_cierre"] - fila["acierto_varios"])
    todos += d
    res.append(resumen(b, d))
res.append(resumen("todos", todos))
for nom, F in (("cierres_por_problema_todos.csv", det), ("cierres_por_problema_todos_resumen.csv", res)):
    with open(f"resultados/p3/{nom}", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(F[0].keys())); w.writeheader(); w.writerows(F)
for r in res: print(r)
