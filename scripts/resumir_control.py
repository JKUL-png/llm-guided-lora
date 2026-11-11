"""Resume los 20 de control a 0.6 y 1.0, original y LoRA P1b, con la regla del paper 2. Sin GPU.
Escribe resultados/p1/control_resumen.csv e imprime la tabla en markdown."""
import csv, json, os
P2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R, Q = f"{P2}/resultados/p1", f"{P2}/resultados/calificacion"
CIERRE = "Okay, I have thought about this enough."
CASOS = [("Original", "0.6", f"{Q}/control_orig_think_T06_s0.csv", f"{P2}/resultados/piloto/control_original_s0.csv"),
         ("LoRA P1b", "0.6", f"{Q}/control_p1b_think_T06_s0.csv", f"{R}/p1b_control_s0.csv"),
         ("Original", "1.0", f"{R}/orig_control_T10_s0.csv", None),
         ("LoRA P1b", "1.0", f"{R}/p1b_control_T10_s0.csv", None)]
out = []
for nombre, temp, csvf, txt in CASOS:
    if not os.path.exists(csvf):
        continue
    x = list(csv.DictReader(open(csvf, encoding="utf-8")))
    t = {j["id"]: j["texto"] for j in map(json.loads, open((txt or csvf) + ".jsonl", encoding="utf-8"))}
    fin = [r for r in x if r["llego_limite"] == "0"]
    out.append(dict(modelo=nombre, temperatura=temp, n=len(x), correctas=sum(int(r["correcto"]) for r in x),
                    al_limite=sum(int(r["llego_limite"]) for r in x),
                    tokens_medios=round(sum(int(r["tokens"]) for r in x) / len(x)),
                    con_frase_cierre=sum(CIERRE in t[r["id"]] for r in x),
                    con_think=sum("</think>" in t[r["id"]] for r in x),
                    varios_cierres=sum(int(r["varios_cierres"]) for r in x),
                    correctas_entre_terminadas=f"{sum(int(r['correcto']) for r in fin)}/{len(fin)}"))
with open(f"{R}/control_resumen.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=out[0].keys()); w.writeheader(); w.writerows(out)
print("| Modelo | Temp. | Correctas | Al límite | Tokens medios | Con frase de cierre | Con </think> | Más de un </think> | Correctas entre las que terminan |")
print("|---|---|---|---|---|---|---|---|---|")
for o in out:
    print(f"| {o['modelo']} | {o['temperatura']} | {o['correctas']} de {o['n']} | {o['al_limite']} | {o['tokens_medios']:,} | "
          f"{o['con_frase_cierre']} | {o['con_think']} | {o['varios_cierres']} | {o['correctas_entre_terminadas']} |")
