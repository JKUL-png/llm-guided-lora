"""Comprueba si LoRA y original generaron cosas distintas en los 20 de control, y si el LoRA usa lo aprendido.
Sin GPU. Escribe paper2/resultados/piloto/revision_control.csv."""
import csv, json, os, sys
AQUI = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(AQUI, "..", "resultados", "piloto")
CIERRE = "Okay, I have thought about this enough."
W, K, L = 300, 3, 6000


def cargar(n):
    return {d["id"]: d["texto"] for d in map(json.loads, open(f"{R}/{n}.csv.jsonl", encoding="utf-8"))}


def bucle(t):
    cola = t[-L:]
    return len(cola) >= W and cola.count(cola[-W:]) >= K


def comun(a, b):
    i = 0
    for x, y in zip(a, b):
        if x != y:
            break
        i += 1
    return i


lo, og = cargar("control_lora_s0"), cargar("control_original_s0")
filas = []
for i in og:
    a, b = lo[i], og[i]
    filas.append(dict(id=i, identicos=int(a == b), prefijo_comun_chars=comun(a, b), chars_lora=len(a), chars_orig=len(b),
                      bucle_exacto_lora=int(bucle(a)), bucle_exacto_orig=int(bucle(b)),
                      cierre_lora=a.count(CIERRE), cierre_orig=b.count(CIERRE),
                      think_lora=a.count("</think>"), think_orig=b.count("</think>")))
with open(f"{R}/revision_control.csv", "w", newline="", encoding="utf-8") as h:
    w = csv.DictWriter(h, fieldnames=list(filas[0])); w.writeheader(); w.writerows(filas)
n = len(filas)
s = lambda k: sum(f[k] for f in filas)
print("idénticos", s("identicos"), "de", n)
print("prefijo común mediano", sorted(f["prefijo_comun_chars"] for f in filas)[n // 2])
print("bucle exacto al final: LoRA", s("bucle_exacto_lora"), "| original", s("bucle_exacto_orig"))
print("frase de cierre: LoRA", s("cierre_lora"), "| original", s("cierre_orig"))
print("</think>: LoRA", s("think_lora"), "| original", s("think_orig"))
