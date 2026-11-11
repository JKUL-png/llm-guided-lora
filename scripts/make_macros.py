"""Genera las macros y tablas LaTeX del paper 2 a partir de los CSV/JSON del proyecto. SIN GPU, solo Python estandar.
Uso (desde la raiz del repositorio):  python -I paper2/paper/scripts/make_macros.py
Salida: paper2/paper/latex/generated/numeros.tex, tabla_brazos.tex, tabla_config.tex
Regla del proyecto: ningun numero del paper se escribe a mano; si falta uno, se agrega aqui con su fuente.
Cada macro lleva en un comentario el archivo del que sale."""
import ast, csv, json, os, re, itertools, collections

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))   # raiz del repositorio
P2 = RAIZ
RES = os.path.join(P2, "resultados")
OUT = os.path.join(RAIZ, "paper", "latex", "generated")
os.makedirs(OUT, exist_ok=True)
macros = []   # (nombre, valor LaTeX, fuente)


def M(nombre, valor, fuente):
    assert re.fullmatch(r"[A-Za-z]+", nombre), nombre
    macros.append((nombre, str(valor), fuente))


def miles(n): return f"{int(n):,}".replace(",", "{,}")   # 2654208 -> 2{,}654{,}208


def csvf(*p): return list(csv.DictReader(open(os.path.join(*p), encoding="utf-8")))


# ---- 1. Lista de los 24 LoRA ----
L = csvf(RES, "p3_lista_lora.csv"); F = "resultados/p3_lista_lora.csv"
M("NLora", len(L), F)
brazos = sorted({r["brazo"] for r in L}); M("NArms", len(brazos), F)
M("NSeeds", len({r["semilla"] for r in L}), F)
for campo, nom in (("parametros_contados_peft", "ParamsLora"), ("max_tokens", "MaxTrainTokens"), ("ejemplos", "NExamples"), ("tokens_datos", "NTrainTokens")):
    v = {r[campo] for r in L}; assert len(v) == 1, campo; M(nom, miles(v.pop()), F)
for campo, nom in (("epocas", "Epochs"), ("acumular", "Accum")):
    v = {r[campo] for r in L}; assert len(v) == 1; M(nom, v.pop(), F)
lr = {r["lr"] for r in L}; assert len(lr) == 1
mant, exp = f"{float(lr.pop()):.0e}".split("e"); M("LearningRate", f"{int(mant)}\\times10^{{{int(exp)}}}", F)
assert {r["perdida"] for r in L} == {"salida"}
for b, nom in (("a", "Full"), ("b", "Four")):
    rr = {(r["rango"], r["alfa"], r["n_capas"]) for r in L if r["brazo"] == b}; assert len(rr) == 1
    rg, al, nc = rr.pop(); M("Rank" + nom, rg, F); M("Alpha" + nom, al, F); M("NLayers" + nom, nc, F)
assert all(len({(r["rango"]) for r in L if r["brazo"] == b}) == 1 for b in "bcdef")
M("NModelLayers", 24, "Qwen3.5-0.8B tiene 24 bloques (PLAN.md s.1)")
# pasos de entrenamiento (un JSON por LoRA)
pasos = set()
for r in L:
    j = json.load(open(os.path.join(RES, "p3", "entrenamiento", f"{r['brazo']}{r['semilla']}.json"), encoding="utf-8")); pasos.add(j["pasos"])
assert len(pasos) == 1; M("TrainSteps", pasos.pop(), "resultados/p3/entrenamiento/*.json")
# datos de entrenamiento
D = json.load(open(os.path.join(RAIZ, "datos", "lora_bucles.jsonl.resumen.json"), encoding="utf-8")); F = "datos/lora_bucles.jsonl.resumen.json"
M("NTrainProblems", miles(D["respuestas_vistas"]), F); M("NForced", D["forzadas"], F); M("NNatural", D["naturales"], F)
M("NDroppedLong", D["descartadas_por_largo"], F); assert D["ejemplos"] == int(L[0]["ejemplos"])
M("PctForced", f"{100 * D['forzadas'] / D['ejemplos']:.0f}", F + " (forzadas/ejemplos)")

# ---- 2. Capas por brazo y semilla; coincidencia entre sesiones de Opus ----
capas = collections.defaultdict(dict)
for r in L: capas[r["brazo"]][int(r["semilla"])] = sorted(int(x) for x in r["capas"].split(";"))
sets_b = [set(capas["b"][s]) for s in range(4)]
par = [len(x & y) for x, y in itertools.combinations(sets_b, 2)]
M("OpusSharedMean", f"{sum(par) / len(par):.2f}", "resultados/p3_lista_lora.csv (capas del brazo b, 6 pares de sesiones)")
M("OpusSharedChance", f"{4 * 4 / 24:.2f}", "valor esperado por azar = 4*4/24")
cont = collections.Counter(c for s in sets_b for c in s)
M("OpusLayerFifteen", cont[15], "capas elegidas por Opus (b), de 4 sesiones"); M("OpusLayerNineteen", cont[19], "idem")
placebo = json.load(open(os.path.join(RAIZ, "datos", "capas_placebo.json"), encoding="utf-8"))
M("PlaceboRule", "\\texttt{random.Random(20261106+s).sample(range(24), 4)}", "datos/capas_placebo.json")
assert placebo["regla"].replace(" ", "") == "random.Random(20261106+semilla).sample(range(24),4)".replace("semilla", "semilla")
for s in range(4): assert capas["c"][s] == sorted(placebo["capas"][str(s)]), s   # el sorteo guardado coincide con el entrenado

# ---- 3. Barrido (brazos e y f) ----
fr = json.load(open(os.path.join(RES, "barrido", "barrido.csv.fragmentos.json"), encoding="utf-8")); F = "resultados/barrido/barrido.csv.fragmentos.json"
tipos = collections.Counter(x["tipo"] for x in fr)
M("SweepResponses", len({x["id"] for x in fr if x["tipo"] != "cierre_natural"}), F)
M("SweepFragments", tipos["principal"] + tipos["bucle"], F); M("SweepControl", tipos["cierre_natural"], F)
M("SweepFragPerResp", (tipos["principal"] + tipos["bucle"]) // tipos["principal"], F + " (fragmentos por respuesta)")
B = csvf(RES, "barrido", "barrido.csv")
M("SweepConditions", len({(r["capa"], r["variante"]) for r in B}), "resultados/barrido/barrido.csv (1 normal + 24 capas x 2 variantes)")
M("SweepDiagProblems", 40, "datos/diag40_ids.txt (40 problemas del diagnostico)")
assert sum(1 for l in open(os.path.join(RAIZ, "datos", "diag40_ids.txt"), encoding="utf-8") if l.strip() and not l.startswith("#")) == 40
capas_e = json.load(open(os.path.join(RES, "barrido", "capas_e.json"), encoding="utf-8"))["capas"]
assert capas_e == capas["e"][0], "las capas del barrido (e) no coinciden con las entrenadas"

# ---- 4. Conjuntos de evaluacion fijos ----
def n_ids(f): return sum(1 for l in open(os.path.join(RAIZ, "datos", f), encoding="utf-8") if l.strip() and not l.startswith("#"))
for nom, f in (("NMath", "math500_subset100_ids.txt"), ("NGsm", "gsm8k_subset100_ids.txt"), ("NIfeval", "ifeval_subset100_ids.txt")):
    M(nom, n_ids(f), "datos/" + f)
M("NPairs", n_ids("math500_subset100_ids.txt") * 4, "problemas x 4 semillas")
niv = collections.Counter(json.loads(l)["level"] for l in open(os.path.join(RAIZ, "datos", "math500_subset100.jsonl"), encoding="utf-8"))
M("MathLevels", ", ".join(str(niv[k]) for k in range(1, 6)), "datos/math500_subset100.jsonl (problemas por nivel 1 a 5)")
sem = re.search(r"semilla=(\d+)", open(os.path.join(RAIZ, "datos", "math500_subset100_ids.txt"), encoding="utf-8").read()); M("MathSubsetSeed", sem.group(1), "datos/math500_subset100_ids.txt")

# ---- 5. Configuraciones de generacion (leidas de scripts/comun_math.py) ----
src = ast.parse(open(os.path.join(RAIZ, "scripts", "comun_math.py"), encoding="utf-8").read())
def dict_de(nombre):
    for n in src.body:
        if isinstance(n, ast.Assign) and n.targets[0].id == nombre and isinstance(n.value, ast.Call):
            return {k.arg: ast.literal_eval(k.value) for k in n.value.keywords}
BASE = dict_de("BASE_MIT"); NOTH = dict_de("NOTHINK_MIT")
assert BASE and NOTH
def fila(nombre, think, c):
    return f"{nombre} & {think} & {c['temperature']} & {c['top_p']} & {c['top_k']} & {c['presence_penalty']} & {c['repetition_penalty']} & {miles(c['max_tokens'])} \\\\"
filas = [fila("Thinking (original MIT; all LoRA arms)", "on", BASE), fila("No-thinking, same sampling (reference N)", "off", dict(BASE)),
         fila("No-thinking, MIT sampling (paper 1 only)", "off", NOTH)]
open(os.path.join(OUT, "tabla_config.tex"), "w", encoding="utf-8", newline="\n").write(
    "% Generado por make_macros.py desde scripts/comun_math.py (BASE_MIT, NOTHINK_MIT). No editar a mano.\n"
    "\\begin{tabular}{lcccccccc}\n\\toprule\n\\textbf{Configuration} & \\textbf{Thinking} & $T$ & top-$p$ & top-$k$ & presence & repetition & max tokens \\\\\n\\midrule\n"
    + "\n".join(filas) + "\n\\bottomrule\n\\end{tabular}\n")
M("TempMain", BASE["temperature"], "scripts/comun_math.py BASE_MIT"); M("MaxTokensEval", miles(BASE["max_tokens"]), "scripts/comun_math.py BASE_MIT")
M("PresencePenalty", BASE["presence_penalty"], "scripts/comun_math.py BASE_MIT")

# ---- 6. Estadistica (parametros leidos del script de analisis) ----
S = open(os.path.join(RAIZ, "scripts", "revision", "rev_estadistica.py"), encoding="utf-8").read(); F = "scripts/revision/rev_estadistica.py"
M("BootProblemReps", miles(re.search(r"\) / n for _ in range\((\d+)\)\)", S).group(1)), F)
M("BootProblemSeed", re.search(r"def boot.*\n\s*Rg = random.Random\((\d+)\)", S).group(1), F)
M("BootTwoWayReps", miles(re.search(r"def dosvias\(x, y, reps=(\d+)\)", S).group(1)), F)
M("BootTwoWaySeed", re.search(r"def dosvias.*\n\s*Rg = random.Random\((\d+)\)", S).group(1), F)
M("HolmAlpha", "0.05", "convencion; columnas sobrevive_holm_0.05 de los CSV")

# ---- 7. Tamano de la edicion fusionada (descriptivo) ----
W = csvf(RES, "revision", "rev_dw_resumen.csv"); F = "resultados/revision/rev_dw_resumen.csv"
for b in "abcdef":
    v = [float(r["max_dw_w_despues"]) for r in W if r["brazo"] == b]
    M("DW" + b + "Lo", f"{min(v):.4f}", F); M("DW" + b + "Hi", f"{max(v):.4f}", F)
M("MinKept", f"{min(float(r['min_fraccion_conservada']) for r in W):.4f}", F + " (minima fraccion del parche conservada tras bf16)")

# ---- 8. Tabla de brazos ----
desc = {"a": "all 24 layers (rank 8)", "b": "Opus, informed session", "c": "random placebo", "d": "gradient-norm rule", "e": "automatic sweep rule", "f": "Opus reading the sweep table"}
out = ["% Generado por make_macros.py desde resultados/p3_lista_lora.csv. No editar a mano.",
       "\\begin{tabular}{llp{.5\\linewidth}}", "\\toprule", "\\textbf{Arm} & \\textbf{How layers are chosen} & \\textbf{Layers trained, seeds 0 / 1 / 2 / 3} \\\\", "\\midrule"]
for b in brazos:
    if b == "a": cel = "all 24 in every seed"
    else:
        ss = [capas[b][s] for s in range(4)]
        cel = "same in every seed: " + ", ".join(map(str, ss[0])) if all(x == ss[0] for x in ss) else " / ".join(", ".join(map(str, x)) for x in ss)
    out.append(f"({b}) & {desc[b]} & {cel} \\\\")
out += ["\\bottomrule", "\\end{tabular}"]
open(os.path.join(OUT, "tabla_brazos.tex"), "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")

# ---- 9. La edicion p50c del MIT (referencia; datos del paper 1) ----
mf = json.load(open(os.path.join(RAIZ, "datos", "mit_exp8", "edits", "p50c", "manifest.json"), encoding="utf-8")); F = "datos/mit_exp8/edits/p50c/manifest.json"
M("MitEntries", miles(mf["changed_entries_total"]), F); M("MitTensors", mf["changed_tensors"], F)
ly = sorted(int(re.search(r"layers\.(\d+)\.", x["name"]).group(1)) for x in mf["tensors"]); M("MitLayerA", ly[0], F); M("MitLayerB", ly[1], F)
assert {x["changed_columns"] for x in mf["tensors"]} == {64}; M("MitColumns", 64, F)

# ---- 10. Calificacion: regla del ultimo cierre vs. regla del primer cierre ----
it = csvf(RES, "revision", "rev_regla_cierre_items.csv"); F = "resultados/revision/rev_regla_cierre_items.csv"
M("RuleItems", miles(len(it)), F); M("RuleSame", miles(sum(1 for r in it if r["L"] == r["P1"])), F + " (columnas L y P1 iguales)")
M("ParamsPerRankLayer", miles(int(L[0]["parametros_contados_peft"]) // (24 * 8)), "parametros / (24 capas x rango 8)")
assert int(L[0]["parametros_contados_peft"]) == 24 * 8 * (int(L[0]["parametros_contados_peft"]) // (24 * 8)) == 4 * 48 * (int(L[0]["parametros_contados_peft"]) // (24 * 8))

# ---- 11. Fechas de los commits que fijan decisiones (git local, sin sello de tiempo externo) ----
FECHAS = {r["commit"]: r["fecha"] for r in csvf(RES, "fechas_decisiones.csv")}
FECHAS_OUT = []
for nom, h in (("DateFirstCommit", "cf51b47"), ("DateBestArmRule", "7483729"), ("DateHolmFamilies", "4274fd9"), ("DateScopeCut", "5a7f102")):
    d = FECHAS[h]   # el historial del proyecto original no es publico: fechas guardadas en resultados/fechas_decisiones.csv
    M(nom, d, f"git log, commit {h}")
    FECHAS_OUT.append(dict(commit=h, macro=nom, fecha=d))

# ---- 12. Constantes de diseno que aparecen en el texto (cada una se verifica contra el documento de diseno que la fija) ----
import math
def buscar(archivo, patron, grupo=1):
    m = re.search(patron, open(os.path.join(RAIZ, "plan", archivo), encoding="utf-8").read()); assert m, (archivo, patron); return m.group(grupo)
DI = "DISENO_INFORMADO.md"
M("OpusShortQueries", buscar(DI, r"\*\*(\d+) consultas cortas:\*\*"), DI); M("OpusLongSamples", buscar(DI, r"\*\*(\d+) muestras largas:\*\*"), DI)
M("OpusMaxCalls", buscar(DI, r"\*\*(\d+) llamadas\*\* como m"), DI); M("OpusContextWords", buscar(DI, r"unas (\d+) palabras"), DI)
M("GradExamples", buscar("PLAN.md", r"(\d+) ejemplos de entrenamiento sorteados"), "PLAN.md")
M("VocabSize", miles(buscar("PLAN.md", r"vocabulario tiene ([\d,]+) tokens").replace(",", "")), "PLAN.md")
M("SweepContTokens", buscar("DISENO_BARRIDO.md", r"de los (\d+) tokens reales"), "DISENO_BARRIDO.md")
M("SweepExtraPoints", buscar("DISENO_BARRIDO.md", r"Más (\d+) puntos al final"), "DISENO_BARRIDO.md")
cm = open(os.path.join(RAIZ, "scripts", "comun_math.py"), encoding="utf-8").read()
M("TempHigh", re.search(r'"ficha_qwen":\s*dict\(BASE_MIT, temperature=([\d.]+)\)', cm).group(1), "scripts/comun_math.py (ficha_qwen)")
M("NSeedPairings", math.factorial(4), "4! formas de emparejar las 4 semillas de dos brazos")
M("LoraMinP",f"{2 / math.comb(8, 4):.3f}", "2 / C(8,4): menor p posible comparando 4 LoRA contra 4 LoRA (permutacion de etiquetas)")
M("WilsonHalf", f"{1.96 * math.sqrt(0.25 / 100) * 100:.0f}", "semi-ancho aproximado del IC al 95% con n=100 y p=0.5")
fs = [set(capas["f"][s]) for s in range(4)]; M("FSharedFirstTwo", len(fs[0] & fs[2]), "p3_lista_lora.csv: capas compartidas entre las sesiones 1 y 2 del brazo (f)")
M("BSharedFirstTwoMax", max(par), "p3_lista_lora.csv: maximo de capas compartidas entre dos sesiones de (b)")
M("DWfourLo", f"{min(float(m[1]) for m in macros if re.fullmatch(r'DW[bcdef]Lo', m[0])):.4f}", "resultados/revision/rev_dw_resumen.csv (brazos b-f)")
M("DWfourHi", f"{max(float(m[1]) for m in macros if re.fullmatch(r'DW[bcdef]Hi', m[0])):.4f}", "resultados/revision/rev_dw_resumen.csv (brazos b-f)")

# fechas de los commits que fijan decisiones (el repositorio publico no tiene este historial: las lee de aqui)
with open(os.path.join(RES, "fechas_decisiones.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=["commit", "macro", "fecha"]); w.writeheader(); w.writerows(FECHAS_OUT)

# ---- 13. Marca de borrador: mientras main.tex tenga algun \\todo{...}, paper y blog dicen "Draft v0.9" ----
_tex = open(os.path.join(OUT, "..", "main.tex"), encoding="utf-8").read()
_n_todo = _tex.count("\\todo{")   # la linea que define \todo no contiene "\todo{", asi que no hay que restarla
M("DraftMark", "Draft v0.9" if _n_todo > 0 else "", f"main.tex: {_n_todo} todo pendientes")

# ---- salida de macros ----
with open(os.path.join(OUT, "numeros.tex"), "w", encoding="utf-8", newline="\n") as fh:
    fh.write("% Generado por paper2/paper/scripts/make_macros.py. NO EDITAR A MANO. Cada macro indica su fuente.\n")
    # DraftMark va con \newcommand* (no "long"), para que \ifx\DraftMark\empty sea verdadero cuando esta vacia
    for n, v, f in macros: fh.write(f"\\newcommand{'*' if n == 'DraftMark' else ''}{{\\{n}}}{{{v}}} % {f}\n")
print(len(macros), "macros escritas en", os.path.relpath(OUT, RAIZ))

# ---- resultados: macros \R{...} y tablas (otro script, mismo paso) ----
import runpy
runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "make_results.py"), run_name="__main__")
