"""Resume el barrido (sin GPU). Uso: python resumir_barrido.py <barrido.csv> <carpeta_salida>
Para cada capa, variante y métrica: cambio medio frente al modelo normal en el mismo fragmento, IC 95% por bootstrap
por problema (10,000 remuestreos, semilla 20261107), % de fragmentos donde sube y la media solo en los puntos principales.
Escribe barrido_resumen.csv, tabla_opus.md (lo único que ve Opus) y capas_e.json (brazo e: las 4 capas de mayor
|cambio medio| en log P(</think>), apagado en cero, puntos principales + bucle)."""
import csv, json, os, random, sys
from collections import defaultdict

ent, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
X = list(csv.DictReader(open(ent, encoding="utf-8")))
base = {int(x["frag"]): x for x in X if x["variante"] == "normal"}
METRICAS = [("lp_think", "log P(</think>)"), ("lp_frase", "log P(frase de cierre)"), ("lp_cont", "log P(seguir el bucle)")]
R, B = random.Random(20261107), 10000

d = defaultdict(lambda: defaultdict(list))     # (capa, variante, métrica, tipo) -> problema -> [cambios]
for x in X:
    if x["variante"] == "normal":
        continue
    b = base[int(x["frag"])]
    for met, _ in METRICAS:
        if x[met] != "":
            d[(int(x["capa"]), x["variante"], met, x["tipo"])][int(x["problema"])].append(float(x[met]) - float(b[met]))


def resumen(por_prob):
    vals = [v for vs in por_prob.values() for v in vs]
    probs = list(por_prob)
    S, N = [sum(por_prob[p]) for p in probs], [len(por_prob[p]) for p in probs]
    boots = []
    for _ in range(B):
        idx = [R.randrange(len(probs)) for _ in probs]
        boots.append(sum(S[i] for i in idx) / sum(N[i] for i in idx))
    boots.sort()
    return sum(vals) / len(vals), boots[int(0.025 * B)], boots[int(0.975 * B) - 1], sum(v > 0 for v in vals) / len(vals), len(vals), len(probs)


filas = []
for capa in sorted({k[0] for k in d}):
    for var in ("cero", "media"):
        for met, _ in METRICAS:
            todos = defaultdict(list)
            for tipo in ("principal", "bucle"):
                for p, v in d.get((capa, var, met, tipo), {}).items():
                    todos[p] += v
            if not todos:
                continue
            media, lo, hi, sube, n, np_ = resumen(todos)
            pr = [v for vs in d.get((capa, var, met, "principal"), {}).values() for v in vs]
            nat = [v for vs in d.get((capa, var, met, "cierre_natural"), {}).values() for v in vs]
            filas.append(dict(capa=capa, variante=var, metrica=met, cambio_medio=round(media, 4), ic_bajo=round(lo, 4),
                              ic_alto=round(hi, 4), pct_sube=round(100 * sube, 1), n_fragmentos=n, n_problemas=np_,
                              cambio_principal=round(sum(pr) / len(pr), 4) if pr else "",
                              cambio_cierre_natural=round(sum(nat) / len(nat), 4) if nat else "", n_cierre_natural=len(nat)))
with open(f"{out}/barrido_resumen.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=filas[0].keys()); w.writeheader(); w.writerows(filas)

clave = [x for x in filas if x["variante"] == "cero" and x["metrica"] == "lp_think"]
e = sorted(sorted(clave, key=lambda x: -abs(x["cambio_medio"]))[:4], key=lambda x: x["capa"])
json.dump(dict(capas=[x["capa"] for x in e], regla="4 capas de mayor |cambio medio| en log P(</think>), MLP en cero",
               valores={x["capa"]: x["cambio_medio"] for x in e}), open(f"{out}/capas_e.json", "w"), indent=1)

nb = {x["tipo"] for x in X}
with open(f"{out}/tabla_opus.md", "w", encoding="utf-8") as f:
    f.write("# Barrido: efecto de apagar el MLP de cada capa\n\n")
    f.write(f"Fragmentos dentro de bucles de las respuestas guardadas al límite: {len({int(x['frag']) for x in X if x['tipo'] != 'cierre_natural'})}, "
            f"de {len({int(x['problema']) for x in X if x['tipo'] != 'cierre_natural'})} problemas. Cada valor es el cambio medio frente al "
            "modelo normal en el mismo fragmento (en log de probabilidad; positivo = más probable al apagar). IC 95% por bootstrap por problema. "
            "\"Cero\": salida del MLP en cero. \"Media\": reemplazada por su promedio. \"Principal\": solo el punto donde el bucle "
            "empieza a repetirse. \"Cierre natural\": respuestas que sí cerraron, medidas en su </think>.\n\n")
    for met, nombre in METRICAS:
        f.write(f"## {nombre}\n\n| Capa | Cero: cambio [IC 95%] | % sube | Principal | Media: cambio [IC 95%] |"
                + (" Cierre natural (cero) |" if met == "lp_think" else "") + "\n|---|---|---|---|---|" + ("---|" if met == "lp_think" else "") + "\n")
        for capa in sorted({x["capa"] for x in filas}):
            c = next((x for x in filas if x["capa"] == capa and x["variante"] == "cero" and x["metrica"] == met), None)
            mm = next((x for x in filas if x["capa"] == capa and x["variante"] == "media" and x["metrica"] == met), None)
            if not c:
                continue
            f.write(f"| {capa} | {c['cambio_medio']:+.3f} [{c['ic_bajo']:+.3f}, {c['ic_alto']:+.3f}] | {c['pct_sube']} | {c['cambio_principal']:+.3f} | "
                    + (f"{mm['cambio_medio']:+.3f} [{mm['ic_bajo']:+.3f}, {mm['ic_alto']:+.3f}]" if mm else "") + " |"
                    + (f" {c['cambio_cierre_natural']} |" if met == "lp_think" else "") + "\n")
        f.write("\n")
print("listo:", len(filas), "filas | brazo e:", [x["capa"] for x in e])
