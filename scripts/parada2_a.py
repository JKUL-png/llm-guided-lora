"""Parada 2 sobre el brazo (a) a 0.6 (decidido por el usuario el 2026-11-07, antes de ver P3) y prueba de reproducibilidad (a) s0 vs P1b.
Uso: python parada2_a.py <resultados/p3>
Criterio (PLAN.md, parada 2): el % de respuestas al límite de (a) a 0.6, media de las 4 semillas, debe bajar al menos 20 puntos
desde 92.25% (original sin entrenar, mismos 100 problemas): PASA si la media <= 72.25. Escribe parada2.csv y repro_a0.csv. Sin GPU."""
import csv, json, os, sys
R = sys.argv[1]
REF, BAJA = 92.25, 20.0
filas, lim, ok_ = [], [], []
for s in range(4):
    x = list(csv.DictReader(open(f"{R}/eval/a{s}_T06_s{s}.csv", encoding="utf-8")))
    n = len(x)
    al = 100 * sum(int(r["llego_limite"]) for r in x) / n
    co = 100 * sum(int(r["correcto"]) for r in x) / n
    lim.append(al); ok_.append(co)
    filas.append(dict(semilla=s, n=n, pct_al_limite=round(al, 2), pct_correctas=round(co, 2), tokens_medios=round(sum(int(r["tokens"]) for r in x) / n),
                      varios_cierres=sum(int(r["varios_cierres"]) for r in x)))
media = sum(lim) / 4
decision = "PASA" if media <= REF - BAJA else "NO_PASA"
with open(f"{R}/parada2.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["decision", "media_pct_al_limite", "referencia_pct", "baja_exigida_puntos", "baja_observada_puntos",
                                      "semilla", "n", "pct_al_limite", "pct_correctas", "tokens_medios", "varios_cierres"])
    w.writeheader()
    for r in filas:
        w.writerow(dict(r, decision=decision, media_pct_al_limite=round(media, 2), referencia_pct=REF, baja_exigida_puntos=BAJA,
                        baja_observada_puntos=round(REF - media, 2)))
print(f"parada 2: media {media:.2f}% al límite (referencia {REF}%), baja {REF - media:.2f} puntos -> {decision}")

# reproducibilidad (a) s0 vs P1b
P1 = os.path.join(os.path.dirname(os.path.abspath(R)), "p1")
a, b = json.load(open(f"{R}/entrenamiento/a0.json")), json.load(open(f"{P1}/p1b_entrenamiento.json"))
fa = {r["tensor"] if "tensor" in r else list(r.values())[0]: r for r in csv.DictReader(open(f"{R}/fusion/a0.csv", encoding="utf-8"))}
fb = {r["tensor"] if "tensor" in r else list(r.values())[0]: r for r in csv.DictReader(open(f"{P1}/p1b_fusion.csv", encoding="utf-8"))}
col = [c for c in next(iter(fa.values())).keys() if "despues" in c.lower() or "after" in c.lower()] or [list(next(iter(fa.values())).keys())[1]]
dif = [abs(float(fa[k][col[0]]) - float(fb[k][col[0]])) / max(float(fb[k][col[0]]), 1e-12) for k in fa if k in fb]
ra, rb = a["registro"], b["registro"]
n = min(len(ra), len(rb))
c = list(csv.DictReader(open(f"{R}/eval/a0_control20_s0.csv", encoding="utf-8")))
pb = [r for r in csv.DictReader(open(f"{P1}/control_resumen.csv", encoding="utf-8")) if r["modelo"] == "LoRA P1b" and r["temperatura"] == "0.6"][0]
filas = [("pasos", a["pasos"], b["pasos"]), ("tokens_entrenados", a["tokens"], b["tokens"]),
         ("perdida_inicial", a["perdida_inicial"], b["perdida_inicial"]), ("perdida_final", a["perdida_final"], b["perdida_final"]),
         ("max_abs_dif_registro_perdida", round(max(abs(x - y) for x, y in zip(ra[:n], rb[:n])), 4), 0),
         ("dif_relativa_max_normaDW_por_tensor", round(max(dif), 5), 0),
         ("control20_correctas", sum(int(r["correcto"]) for r in c), pb["correctas"].split()[0] if " " in pb["correctas"] else pb["correctas"]),
         ("control20_al_limite", sum(int(r["llego_limite"]) for r in c), pb["al_limite"]),
         ("control20_tokens_medios", round(sum(int(r["tokens"]) for r in c) / len(c)), pb["tokens_medios"])]
with open(f"{R}/repro_a0.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["medida", "a_semilla0_nueva", "P1b"]); w.writerows(filas)
for r in filas:
    print(r)
