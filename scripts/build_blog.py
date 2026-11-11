"""Builds the paper 2 blog: docs/src/index.template.html -> docs/index.html, plus paper2/blog/data/data.js.
SIN GPU, solo Python estandar.

Uso, desde la raiz del proyecto:  python -I scripts/build_blog.py
- Primero corre make_macros.py (que llama a make_results.py), asi los numeros son los mismos que los del paper.
- {{M:Nombre}} se llena con una macro de generated/numeros.tex; {{R:clave}} con una clave de generated/resultados.tex.
- data/data.js (window.BLOG) lleva los datos de los graficos interactivos, leidos de los CSV, y los ejemplos del reproductor.
- Ejemplos del reproductor: respuestas reales de la semilla 0 (original con thinking, capas de Opus, capas al azar), elegidos
  con una regla fija (ver elegir_ejemplos). Se guardan recortados en resultados/blog_ejemplos.json; si las respuestas completas
  no estan (repositorio publico), se usa ese archivo.
- Se detiene si falta una clave, si queda LaTeX sin traducir, si aparece una frase prohibida o si falta una frase obligatoria.
"""
import csv, json, os, re, runpy

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))   # raiz del repositorio
P2 = RAIZ; GEN = os.path.join(RAIZ, "paper", "latex", "generated"); BLOG = os.path.join(RAIZ, "docs")
RES = os.path.join(P2, "resultados"); REV = os.path.join(RES, "revision")
ORIG = os.path.join(RAIZ, "resultados", "linea_base_vllm.csv")   # original con thinking, semilla 0 (paper 1); no esta en el repo publico

runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "make_macros.py"), run_name="__main__")

M = {}
for l in open(os.path.join(GEN, "numeros.tex"), encoding="utf-8"):
    m = re.match(r"\\newcommand\*?\{\\(\w+)\}\{(.*)\} % ", l)
    if m: M[m.group(1)] = m.group(2)
R = {}
for l in open(os.path.join(GEN, "resultados.tex"), encoding="utf-8"):
    m = re.match(r"\\expandafter\\def\\csname R@(.+?)\\endcsname\{(.*)\}% ", l)
    if m: R[m.group(1)] = m.group(2)


def html(v, math=False):
    """LaTeX de las macros -> texto HTML. En modo math (dentro de KaTeX) se deja tal cual salvo las comas de miles."""
    v = v.replace("{,}", ",")
    if math: return v
    v = v.replace("$-$", "\u2212").replace("$<$", "<").replace("\\,/\\,", " / ")
    v = re.sub(r"\\texttt\{([^}]*)\}", r"<code>\1</code>", v)
    assert "\\" not in v and "$" not in v, f"LaTeX sin traducir: {v}"
    return v


def rows(*p): return list(csv.DictReader(open(os.path.join(*p), encoding="utf-8")))


ARMS = "abcdef"
NAME = {"a": "(a) all 24 layers", "b": "(b) Opus", "c": "(c) random", "d": "(d) gradient rule", "e": "(e) sweep rule", "f": "(f) Opus + sweep",
        "N": "Original, thinking off", "T": "Original, thinking on", "P": "p50c (MIT edit)"}
NAME["a"] = f"(a) all {M['NLayersFull']} layers"

# ======================= datos de los graficos =======================
LISTA = rows(RES, "p3_lista_lora.csv")
MOD = {(r["tarea"], r["temp"], r["modelo"]): r for r in rows(REV, "rev_por_modelo.csv")}
CL = {(r["tarea"], r["brazo"]): r for r in rows(REV, "rev_respuestas_limpias.csv")}
CMP = {(r["tarea"], r["temp"], r["X"], r["Y"]): r for r in rows(REV, "rev_comparaciones.csv")}
seeds = lambda s: [int(x) for x in s.replace("/", " ").split()]

design = []
for r in sorted(LISTA, key=lambda r: (r["brazo"], int(r["semilla"]))):
    b, s = r["brazo"], int(r["semilla"])
    design.append(dict(arm=b, seed=s, layers=[int(x) for x in r["capas"].split(";")],
                       correct=seeds(MOD[("math", "T06", b)]["por_semilla"])[s], clean=seeds(CL[("math", b)]["limpias_por_semilla"])[s]))

acc = {}
for t in ("math", "gsm8k", "ifeval"):
    acc[t] = [dict(key=m, acc=float(r["pct_correctas"]), lo=float(r["ic95_dosvias_bajo"]), hi=float(r["ic95_dosvias_alto"]),
                   limit=float(r["pct_al_limite"]), tokens=float(r["tokens_medios"]), seeds=seeds(r["por_semilla"]),
                   accfin=float(r["pct_correctas_entre_terminadas"]))
              for m in "abcdefNTP" for r in [MOD[(t, "T06", m)]]]


def cmp_row(t, X, Y, fam, status):
    c = CMP[(t, "T06", X, Y)]
    return dict(x=X, y=Y, dif=float(c["dif_puntos"]), lo=float(c["ic95_dosvias_bajo"]), hi=float(c["ic95_dosvias_alto"]),
                plo=float(c["ic95_bajo"]), phi=float(c["ic95_alto"]), p=html(R[f"cmp:{t}:06:{X}:{Y}:p"]),
                holm=html(R[f"holm:{fam}:{t}:{X}:{Y}:hs"]), famsize=R[f"fam:{fam}:{t}:size"], read=R[f"read:{fam}:{t}:{X}:{Y}"], status=status)


diff = {
    "main": [cmp_row("math", "b", "c", "main", "pre-specified"), cmp_row("math", "b", "d", "main", "pre-specified"),
             cmp_row("math", "b", "a", "all", "pre-specified")],
    "nothink": [cmp_row("math", a, "N", "vsN", "pre-specified") for a in ARMS],
    "p50c": [cmp_row("math", a, "P", "vsP", "exploratory") for a in ARMS],
    "gsm8k": [cmp_row("gsm8k", a, "N", "vsN", "pre-specified") for a in ARMS] + [cmp_row("gsm8k", a, "P", "vsP", "exploratory") for a in ARMS],
    "ifeval": [cmp_row("ifeval", a, "N", "vsN", "pre-specified") for a in ARMS] + [cmp_row("ifeval", a, "P", "vsP", "exploratory") for a in ARMS],
    "explore": [cmp_row("math", "e", "d", "pairs", "exploratory"), cmp_row("math", "f", "e", "pairs", "exploratory"),
                cmp_row("math", "e", "b", "pairs", "exploratory"), cmp_row("math", "c", "a", "vsa", "exploratory"),
                cmp_row("math", "e", "a", "vsa", "exploratory")],
}
clean = [dict(key=m, pct=float(r["pct_respuesta_limpia_1_cierre_sin_limite"]), lo=float(r["ic95_dosvias_bajo"]), hi=float(r["ic95_dosvias_alto"]),
              seeds=seeds(r["limpias_por_semilla"]), accclean=float(r["pct_correctas_entre_limpias"]), accmulti=float(r["pct_correctas_entre_varios_cierres"]))
         for m in "abcdefP" for r in [CL[("math", m)]]]
placebo_layers = {int(r["semilla"]): [int(x) for x in r["capas"].split(";")] for r in LISTA if r["brazo"] == "c"}

# ======================= ejemplos del reproductor =======================
HEAD, PRE, TAIL, CORTO, MIN_CICLO = 900, 300, 1500, 2400, 300
EJ_JSON = os.path.join(RES, "blog_ejemplos.json"); EJ_CSV = os.path.join(RES, "blog_ejemplos_semilla0.csv")


def textos(csvf):
    f = {r["id"]: r for r in csv.DictReader(open(csvf, encoding="utf-8"))}
    t = {}
    for l in open(csvf + ".jsonl", encoding="utf-8"):
        d = json.loads(l); t[d["id"]] = d["texto"]
    assert set(f) == set(t) and len(f) == 100, csvf
    return f, t


def bucle(t):
    """Ciclo exacto al final del texto (misma funcion que el blog del paper 1)."""
    for p in range(1, min(6000, len(t) // 3)):
        if t[-p:] == t[-2 * p:-p] == t[-3 * p:-2 * p]:
            i = len(t) - p - 1
            while i >= 0 and t[i] == t[i + p]: i -= 1
            inicio = i + 1
            if len(t) - inicio < MIN_CICLO: continue
            salto = t.find("\n", inicio, inicio + p)
            if salto != -1: inicio = salto + 1
            return dict(start=inicio, period=p, copies=(len(t) - inicio) // p, unit=t[inicio:inicio + p])
    return None


def caja(t):
    t = t.split("</think>")[-1]; i = t.rfind("\\boxed{")
    if i < 0: return None
    j, nivel = i + 7, 1
    while j < len(t) and nivel:
        nivel += {"{": 1, "}": -1}.get(t[j], 0); j += 1
    return t[i + 7:j - 1] if nivel == 0 else None


si = lambda v: str(v) in ("1", "True", "true")


def brazo(fila, texto):
    b = dict(tokens=int(fila["tokens"]), limit=si(fila["llego_limite"]), correct=si(fila["correcto"]), chars=len(texto),
             closes=texto.count("</think>"), answer=None if si(fila["llego_limite"]) else caja(texto), loop=None)
    lp = bucle(texto) if b["limit"] else None
    if lp and lp["copies"] >= 3:
        b["loop"] = lp; b["head"] = texto[:min(HEAD, lp["start"])]
        b["pre"] = texto[max(len(b["head"]), lp["start"] - PRE):lp["start"]]; b["tail"] = ""
    elif len(texto) <= CORTO:
        b.update(head=texto, pre="", tail="")
    else:
        fc = texto.find("</think>")
        ini = max(HEAD, fc - 300) if b["closes"] > 1 and 0 <= fc and len(texto) - fc <= CORTO else len(texto) - TAIL
        b.update(head=texto[:HEAD], pre="", tail=texto[max(HEAD, ini):])
    return b


def limpia(f): return not si(f["llego_limite"]) and int(f["cierres"]) == 1


def elegir_ejemplos():
    """Regla: semilla 0, el original con thinking llega al limite. Tres grupos:
    both_clean  = Opus (b) y azar (c) cierran una vez y aciertan;
    opus_multi  = (b) cierra mas de una vez sin llegar al limite y (c) es limpia y acierta;
    random_multi = al reves. En cada grupo: el de menor nivel de dificultad y, a igualdad, el mas corto (b + c)."""
    o = textos(ORIG); b = textos(os.path.join(RES, "p3", "eval", "b0_T06_s0.csv")); c = textos(os.path.join(RES, "p3", "eval", "c0_T06_s0.csv"))
    prob = {json.loads(l)["id"]: json.loads(l) for l in open(os.path.join(RAIZ, "datos", "math500_subset100.jsonl"), encoding="utf-8")}
    tabla, grupos = [], {"both_clean": [], "opus_multi": [], "random_multi": []}
    for i, p in prob.items():
        fo, fb, fc = o[0][i], b[0][i], c[0][i]
        cat = "other"
        if si(fo["llego_limite"]):
            bm = not si(fb["llego_limite"]) and int(fb["cierres"]) > 1; cm = not si(fc["llego_limite"]) and int(fc["cierres"]) > 1
            if limpia(fb) and si(fb["correcto"]) and limpia(fc) and si(fc["correcto"]): cat = "both_clean"
            elif bm and limpia(fc) and si(fc["correcto"]): cat = "opus_multi"
            elif cm and limpia(fb) and si(fb["correcto"]): cat = "random_multi"
        tabla.append(dict(id=i, nivel=p["level"], categoria=cat, orig_limite=fo["llego_limite"], b_cierres=fb["cierres"], b_limite=fb["llego_limite"],
                          b_correcto=fb["correcto"], c_cierres=fc["cierres"], c_limite=fc["llego_limite"], c_correcto=fc["correcto"]))
        if cat in grupos: grupos[cat].append((p["level"], len(b[1][i]) + len(c[1][i]), i))
    with open(EJ_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(tabla[0])); w.writeheader(); w.writerows(tabla)
    ej = []
    for cat in ("both_clean", "opus_multi", "random_multi"):
        if not grupos[cat]: continue
        _, _, i = min(grupos[cat]); p = prob[i]
        ej.append(dict(id=i, category=cat, level=p["level"], subject=p["subject"], problem=p["problem"], gold=p["answer"],
                       arms=dict(original=brazo(o[0][i], o[1][i]), opus=brazo(b[0][i], b[1][i]), random=brazo(c[0][i], c[1][i]))))
    counts = {k: len(v) for k, v in grupos.items()}
    json.dump(dict(examples=ej, counts=counts), open(EJ_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if os.path.exists(ORIG + ".jsonl") and os.path.exists(os.path.join(RES, "p3", "eval", "b0_T06_s0.csv.jsonl")):
    elegir_ejemplos()
EJ = json.load(open(EJ_JSON, encoding="utf-8"))

BLOGDATA = dict(nProblems=int(M["NMath"]), names=NAME, mitLayers=[int(M["MitLayerA"]), int(M["MitLayerB"])], nLayers=int(M["NModelLayers"]),
                design=design, acc=acc, diff=diff, clean=clean, placeboLayers=placebo_layers,
                examples=EJ["examples"], counts=EJ["counts"], maxTokens=int(M["MaxTokensEval"].replace("{,}", "")))
os.makedirs(os.path.join(BLOG, "data"), exist_ok=True)
with open(os.path.join(BLOG, "data", "data.js"), "w", encoding="utf-8", newline="\n") as fh:
    fh.write("window.BLOG=" + json.dumps(BLOGDATA, ensure_ascii=False, separators=(",", ":")) + ";\n")

# ======================= pagina =======================
t = open(os.path.join(BLOG, "src", "index.template.html"), encoding="utf-8").read()
faltan = []


def sub_math(m):
    return m.group(1) + re.sub(r"\{\{M:(\w+)\}\}", lambda x: html(M[x.group(1)], math=True), m.group(2)) + m.group(3)


t = re.sub(r'(<span class="math">)(.*?)(</span>)', sub_math, t)


def rep(m):
    kind, key = m.group(1), m.group(2)
    src = M if kind == "M" else R
    if key not in src: faltan.append(m.group(0)); return m.group(0)
    return html(src[key])


t = re.sub(r"\{\{([MR]):([^}|]+)\}\}", rep, t)
t = t.replace("{{EJ:both_clean}}", str(EJ["counts"]["both_clean"])).replace("{{EJ:opus_multi}}", str(EJ["counts"]["opus_multi"])).replace("{{EJ:random_multi}}", str(EJ["counts"]["random_multi"]))
assert not faltan, "claves que no existen: " + ", ".join(faltan)
t = t.replace("{{DRAFT}}", f' · <span class="draft">{M["DraftMark"]}</span>' if M["DraftMark"] else "")
assert "{{" not in t, "quedo un marcador sin llenar"

# ---- frases: prohibidas y obligatorias (sobre el texto visible) ----
texto = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>", " ", t, flags=re.S))).lower()
PROHIBIDAS = ["pre-registered", "preregistered", "pre-registration", "it was the data", "the data mattered", "regardless of which layers",
              "layer choice does not matter", "the place does not matter", "no harm", "opus is equal", "as good as random",
              "the sweep found the right layers", "beats standard lora"]
OBLIGATORIAS = ["opus did not beat random layers or a cheap rule", "the place seems to matter, but opus did not find a better one than chance",
                "exploratory", "pre-specified", "p50c"]
malas = [p for p in PROHIBIDAS if p in texto]; faltan = [p for p in OBLIGATORIAS if p not in texto]
assert not malas, f"frases prohibidas en el blog: {malas}"
assert not faltan, f"frases obligatorias que faltan: {faltan}"
for f in ("paper.pdf", "style.css", "js/math.js", "js/charts.js", "js/player.js", "data/data.js", "vendor/katex/katex.min.js", "vendor/katex/katex.min.css"):
    assert os.path.exists(os.path.join(BLOG, f)), f"falta {f}"

open(os.path.join(BLOG, "index.html"), "w", encoding="utf-8", newline="\n").write(t)
n_num = len(re.findall(r"\{\{[MR]:", open(os.path.join(BLOG, "src", "index.template.html"), encoding="utf-8").read()))
print(f"blog escrito: paper2/blog/index.html ({n_num} numeros desde macros), data/data.js ({len(EJ['examples'])} ejemplos: {EJ['counts']}); frases revisadas")
