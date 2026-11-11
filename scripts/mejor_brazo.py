"""Elige el mejor brazo según 0.6 para la etapa de 1.0. Regla fijada el 2026-11-07, antes de ver cualquier resultado de P3:
el brazo con mayor % de respuestas correctas, media de las 4 semillas, a 0.6 en MATH-100 (los 6 brazos); si empatan, el de menor % al límite.
Uso: python mejor_brazo.py <resultados/p3>. Escribe mejor_brazo.csv (primera fila = el elegido). Sin GPU."""
import csv, sys
R = sys.argv[1]
res = []
for b in "abcdef":
    x = [r for s in range(4) for r in csv.DictReader(open(f"{R}/eval/{b}{s}_T06_s{s}.csv", encoding="utf-8"))]
    res.append(dict(brazo=b, n=len(x), pct_correctas=round(100 * sum(int(r["correcto"]) for r in x) / len(x), 2),
                    pct_al_limite=round(100 * sum(int(r["llego_limite"]) for r in x) / len(x), 2)))
res.sort(key=lambda r: (-r["pct_correctas"], r["pct_al_limite"]))
with open(f"{R}/mejor_brazo.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=res[0].keys()); w.writeheader(); w.writerows(res)
print("mejor brazo a 0.6:", res[0])
