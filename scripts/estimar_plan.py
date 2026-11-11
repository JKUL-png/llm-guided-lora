"""Medidas para PLAN.md. Sin GPU: solo lee cabeceras de pesos y resultados guardados del paper 1.
Escribe paper2/resultados/plan_*.csv. Uso: python paper2/scripts/estimar_plan.py"""
import csv, json, os, random, re, struct, glob
from collections import defaultdict
RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R = os.path.join(RAIZ, "resultados"); S = os.path.join(RAIZ, "paper2", "resultados")

# 1) formas reales de los tensores -> parámetros LoRA por módulo y capa
f = os.path.join(RAIZ, "modelos/Qwen3.5-0.8B/model.safetensors-00001-of-00001.safetensors")
with open(f, "rb") as h:
    n = struct.unpack("<Q", h.read(8))[0]; cab = json.loads(h.read(n))
filas = []
for k, v in cab.items():
    m = re.match(r".*language_model\.layers\.(\d+)\.(.+)\.weight$", k)
    if m and len(v["shape"]) == 2:
        o, i = v["shape"]; filas.append((int(m[1]), m[2], o, i, o + i))
filas.sort()
with open(f"{S}/plan_modulos_por_capa.csv", "w", newline="") as h:
    w = csv.writer(h); w.writerow(["capa", "modulo", "salida", "entrada", "lora_params_por_rango"]); w.writerows(filas)
por_capa = defaultdict(int); mlp = defaultdict(int)
for c, mod, o, i, s in filas:
    por_capa[c] += s
    if mod.startswith("mlp."): mlp[c] += s
print("capas", len(por_capa), "| params/rango todos los módulos por capa:", sorted(set(por_capa.values())), "| solo MLP:", sorted(set(mlp.values())))
per = sorted(set(mlp.values()))[0]
with open(f"{S}/plan_igualar_parametros.csv", "w", newline="") as h:
    w = csv.writer(h); w.writerow(["capas_k", "rango", "parametros_lora", "igual_a_24_capas_rango8"])
    obj = 24 * 8 * per
    for k in (24, 12, 8, 6, 4, 3, 2):
        r = 8 * 24 // k; w.writerow([k, r, k * r * per, k * r * per == obj])
print("objetivo", obj)

# 2) largo de las respuestas que terminan (original, thinking)
def filas_jsonl(p):
    return [json.loads(l) for l in open(p, encoding="utf8")]
ej = filas_jsonl(f"{R}/linea_base_vllm.csv.jsonl")[0]
print("campos jsonl:", {k: (str(v)[:30]) for k, v in ej.items() if k != "texto"})

# 2b) respuestas correctas y terminadas del original en thinking, por temperatura y tope de tokens
def leer(p):
    return list(csv.DictReader(open(p, encoding="utf8")))
def corrida(pref, s):
    p = f"{R}/{pref}.csv" if (pref == "linea_base_vllm" and s == 0) else f"{R}/{pref}_s{s}.csv"
    return leer(p)
sal = []
for nombre, pref, T in (("orig_think_T0.6", "linea_base_vllm", 0.6), ("orig_think_T1.0", "cero_edicion_ficha_qwen", 1.0)):
    tok = []; niveles = defaultdict(int); total = 0; tot_niv = defaultdict(int)
    for s in range(4):
        for f_ in corrida(pref, s):
            total += 1; tot_niv[f_["nivel"]] += 1
            if f_["correcto"] == "1" and f_["llego_limite"] == "0":
                tok.append(int(f_["tokens"])); niveles[f_["nivel"]] += 1
    tok.sort(); q = lambda p: tok[int(p * (len(tok) - 1))]
    fila = dict(config=nombre, muestras=total, correctas_terminadas=len(tok), pct=round(100 * len(tok) / total, 2),
                tokens_mediana=q(.5), tokens_p90=q(.9), tokens_max=tok[-1])
    for c in (2048, 4096, 8192, 16384):
        fila[f"le_{c}"] = sum(t <= c for t in tok); fila[f"pct_muestras_le_{c}"] = round(100 * fila[f"le_{c}"] / total, 2)
    for n_ in sorted(tot_niv): fila[f"pct_nivel{n_}"] = round(100 * niveles[n_] / tot_niv[n_], 1)
    sal.append(fila)
with open(f"{S}/plan_rendimiento_datos.csv", "w", newline="") as h:
    w = csv.DictWriter(h, fieldnames=list(sal[0])); w.writeheader(); w.writerows(sal)
for x in sal: print(x)

# 3) diferencia detectable: bootstrap por problema de la diferencia pareada (4 semillas)
def por_problema(pref):
    d = defaultdict(list)
    for s in range(4):
        for f_ in corrida(pref, s): d[f_["id"]].append(int(f_["correcto"]))
    return {k: sum(v) / len(v) for k, v in d.items()}
pares = [("p50c_think_vs_p50c_nothink32k", "r2_ed_think", "r2_ed_nothink32k"),
         ("p50c_T1_vs_orig_T1", "r2_ed_ficha_qwen", "cero_edicion_ficha_qwen")]
rng = random.Random(20261106); res = []
for nom, a, b in pares:
    try: A, B = por_problema(a), por_problema(b)
    except FileNotFoundError as e: print("falta", e); continue
    ids = sorted(set(A) & set(B)); dif = [A[i] - B[i] for i in ids]
    bs = sorted(sum(rng.choice(dif) for _ in ids) / len(ids) for _ in range(5000))
    lo, hi = bs[125], bs[4874]; media = sum(dif) / len(dif); media_ = 100 * media
    medio = 100 * (hi - lo) / 2
    res.append(dict(par=nom, problemas=len(ids), diferencia_pts=round(media_, 2), ic95_lo=round(100 * lo, 2), ic95_hi=round(100 * hi, 2),
                    semiancho_ic95=round(medio, 2), detectable_80pct_potencia=round(medio * 2.8 / 1.96, 2)))
with open(f"{S}/plan_diferencia_detectable.csv", "w", newline="") as h:
    w = csv.DictWriter(h, fieldnames=list(res[0])); w.writeheader(); w.writerows(res)
for x in res: print(x)

# 4) datos de "cortar y cerrar" (variante B del paper 1, MATH, semilla 0): rendimiento y largo
b = leer(f"{R}/r3_reint_math_B_s0.csv")
fz = [f_ for f_ in b if f_["forzado"] == "1"]; ok = sorted(int(f_["tokens"]) for f_ in fz if f_["correcto"] == "1")
nat = [f_ for f_ in b if f_["forzado"] == "0" and f_["correcto"] == "1"]
q = lambda p: ok[int(p * (len(ok) - 1))]
fila = dict(problemas=len(b), correctas=sum(f_["correcto"] == "1" for f_ in b), forzadas=len(fz), forzadas_correctas=len(ok), naturales_correctas=len(nat),
            tokens_mediana=q(.5), tokens_p90=q(.9), tokens_max=ok[-1], le_4096=sum(t <= 4096 for t in ok), le_8192=sum(t <= 8192 for t in ok))
with open(f"{S}/plan_rendimiento_cortar_cerrar.csv", "w", newline="") as h:
    w = csv.DictWriter(h, fieldnames=list(fila)); w.writeheader(); w.writerow(fila)
print(fila)

# 5) costo de evaluación desde minutos medidos en el paper 1 (rango: como p50c .. como el original)
T = {r["prefijo"]: float(r["minutos_medios"]) for r in leer(f"{R}/tabla_tiempos_por_prefijo.csv") if r["minutos_medios"]}
celdas = [("MATH", 0.6, "r2_ed_think", "linea_base_vllm"), ("MATH", 1.0, "r2_ed_ficha_qwen", "cero_edicion_ficha_qwen"),
          ("GSM8K", 0.6, "r2_gsm8k_ed_think", "r2_gsm8k_orig_think"), ("GSM8K", 1.0, "r2_gsm8k_ed_ficha", "r2_gsm8k_orig_ficha"),
          ("IFEval", 0.6, "r2_ifeval_ed_think", "r2_ifeval_orig_think"), ("IFEval", 1.0, "r2_ifeval_ed_ficha", "r2_ifeval_orig_ficha")]
with open(f"{S}/plan_costo_evaluacion.csv", "w", newline="") as h:
    w = csv.writer(h); w.writerow(["tarea", "temperatura", "min_como_p50c", "min_como_original", "horas_16_modelos_lo", "horas_16_modelos_hi"])
    lo = hi = ml = mh = 0
    for t, tp, a, o in celdas:
        w.writerow([t, tp, round(T[a], 2), round(T[o], 2), round(16 * T[a] / 60, 1), round(16 * T[o] / 60, 1)])
        lo += T[a]; hi += T[o]
        if t == "MATH": ml += T[a]; mh += T[o]
    w.writerow(["TOTAL", "", round(lo, 2), round(hi, 2), round(16 * lo / 60, 1), round(16 * hi / 60, 1)])
print("MATH h", round(16 * ml / 60, 1), round(16 * mh / 60, 1), "todo h", round(16 * lo / 60, 1), round(16 * hi / 60, 1))
print("ref orig T0.6 GSM8K+IFEval 3 semillas h", round(3 * (T["r2_gsm8k_orig_think"] + T["r2_ifeval_orig_think"]) / 60, 1))
print("cortar y cerrar min/100 problemas", T["r3_reint_math_B"])
