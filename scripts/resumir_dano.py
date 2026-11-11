"""Resume dano_general.csv (sin GPU). Uso: python resumir_dano.py <dano_general.csv> <salida.csv>
Por capa, variante y ventana: KL medio (IC 95% por bootstrap de problemas, 10,000, semilla 20261107),
% de posiciones donde el token más probable no cambia, cambio medio en log P del token real, y puesto de la capa por KL."""
import csv, random, sys
from collections import defaultdict

X = list(csv.DictReader(open(sys.argv[1], encoding="utf-8")))
R, B = random.Random(20261107), 10000
g = defaultdict(list)
for x in X:
    g[(int(x["capa"]), x["variante"], x["ventana"])].append(x)


def ic(v):
    bs = sorted(sum(R.choice(v) for _ in v) / len(v) for _ in range(B))
    return bs[int(0.025 * B)], bs[int(0.975 * B) - 1]


filas = []
for (capa, var, ven), xs in sorted(g.items()):
    kl = [float(x["kl_medio"]) for x in xs]
    lo, hi = ic(kl)
    filas.append(dict(capa=capa, variante=var, ventana=ven, kl_medio=round(sum(kl) / len(kl), 4), kl_ic_bajo=round(lo, 4),
                      kl_ic_alto=round(hi, 4), top1_igual=round(sum(float(x["top1_igual"]) for x in xs) / len(xs), 4),
                      cambio_lp_real=round(sum(float(x["cambio_lp_real"]) for x in xs) / len(xs), 4), n_problemas=len(xs)))
for var in ("cero", "media"):
    for ven in ("bucle", "antes"):
        orden = sorted([f for f in filas if f["variante"] == var and f["ventana"] == ven], key=lambda f: -f["kl_medio"])
        for i, f in enumerate(orden, 1):
            f["puesto_kl"] = i
with open(sys.argv[2], "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=filas[0].keys()); w.writeheader(); w.writerows(filas)
print("| Capa | KL bucle (cero) | puesto | KL antes (cero) | puesto | top-1 igual antes | Δ log P real antes |")
print("|---|---|---|---|---|---|---|")
for c in range(24):
    b = next(f for f in filas if f["capa"] == c and f["variante"] == "cero" and f["ventana"] == "bucle")
    a = next(f for f in filas if f["capa"] == c and f["variante"] == "cero" and f["ventana"] == "antes")
    print(f"| {c} | {b['kl_medio']:.3f} [{b['kl_ic_bajo']:.3f}, {b['kl_ic_alto']:.3f}] | {b['puesto_kl']} | "
          f"{a['kl_medio']:.3f} [{a['kl_ic_bajo']:.3f}, {a['kl_ic_alto']:.3f}] | {a['puesto_kl']} | {100 * a['top1_igual']:.1f}% | {a['cambio_lp_real']:+.3f} |")
