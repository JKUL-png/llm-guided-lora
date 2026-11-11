"""Comprueba que el contexto no contenga nada de evaluación ni datos reservados. Sin GPU.
Busca: trozos de 30 caracteres de enunciados y respuestas guardadas de evaluación, ids, y las capas reservadas.
Uso: python revisar_contexto.py"""
import glob, json, os, re, sys
A = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.join(A, "..", "..", "..")
t = open(f"{A}/contexto_informado.md", encoding="utf-8").read()
norm = lambda s: re.sub(r"\s+", " ", s).lower()
T = norm(t)
trozos, fuentes = set(), 0
for f in ("math500_subset100.jsonl", "math500_full.jsonl", "gsm8k_subset100.jsonl", "gsm8k_subset100b.jsonl", "ifeval_subset100.jsonl"):
    for l in open(f"{RAIZ}/datos/{f}", encoding="utf-8"):
        p = norm(json.loads(l)["problem"])
        fuentes += 1
        trozos.update(p[i:i + 30] for i in range(0, max(1, len(p) - 30), 10))
hits = [x for x in trozos if len(x) == 30 and x in T]
print("enunciados revisados:", fuentes, "| trozos:", len(trozos), "| coincidencias:", len(hits))
gen = 0
for r in glob.glob(f"{RAIZ}/resultados/linea_base_vllm*.jsonl")[:2] + glob.glob(f"{RAIZ}/resultados/r2_ed_think_s0*.jsonl"):
    for l in open(r, encoding="utf-8"):
        x = norm(json.loads(l)["texto"])
        gen += sum(x[i:i + 40] in T for i in range(0, min(len(x), 6000), 200))
print("trozos de respuestas guardadas encontrados:", gen)
reservados = {"ids de evaluación": r"test/[a-z_]+/\d+|gsm8k_test", "capas del ciego": r"\b16, 17|\b(capas?) 16\b|\b(capas?) 20\b|\b(capas?) 21\b",
              "automático": r"\b10, 14\b|\b(capas?) 23\b", "placebo": r"\b1, 2, 4\b", "p1b": r"\bP1b\b|parada", "html doubleai": r"mean of 4 runs|25 problems per length|300 documents|illustrative"}
malos = 0
for k, e in reservados.items():
    m = re.findall(e, t, flags=re.I)
    malos += bool(m)
    print(k, "=>", "NINGUNO" if not m else m[:3])
print("palabras:", len(t.split()))
print("RESULTADO:", "LIMPIO" if not hits and not gen and not malos else "REVISAR")
