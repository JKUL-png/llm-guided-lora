"""Builds the paper 2 blog: docs/src/index.template.html -> docs/index.html. SIN GPU, solo Python estandar.

Uso, desde la raiz del proyecto:  python -I scripts/build_blog.py
- Primero corre make_macros.py (que llama a make_results.py), asi los numeros son los mismos que los del paper.
- {{M:Nombre}} se llena con una macro de generated/numeros.tex; {{R:clave}} con una clave de generated/resultados.tex.
- {{DESIGN}} es la figura del diseno (un SVG generado aqui desde resultados/p3_lista_lora.csv).
- Se detiene si falta una clave, si queda algo de LaTeX sin traducir, si aparece una frase prohibida
  o si falta una de las frases que el blog debe decir.
Las figuras 1-3 (figures/*.svg) las escribe paper2/paper/figuras/make_figures.py (mismas que el paper).
"""
import csv, os, re, runpy

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))   # raiz del repositorio
P2 = RAIZ; GEN = os.path.join(RAIZ, "paper", "latex", "generated"); BLOG = os.path.join(RAIZ, "docs")

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


def design_svg():
    L = list(csv.DictReader(open(os.path.join(P2, "resultados", "p3_lista_lora.csv"), encoding="utf-8")))
    n = int(M["NModelLayers"]); mit = {int(M["MitLayerA"]), int(M["MitLayerB"])}
    cls = {"a": "on-full", "b": "on-opus", "f": "on-opus", "c": "on-auto", "d": "on-auto", "e": "on-auto"}
    name = {"a": "(a) 24 layers", "b": "(b) Opus", "c": "(c) random", "d": "(d) gradient", "e": "(e) sweep", "f": "(f) Opus + sweep"}
    name["a"] = f"(a) all {M['NLayersFull']}"
    X0, CW, RH, GAP, Y0 = 108, 12, 9, 7, 16
    out, y = [], Y0
    for k in range(n):
        if k % 5 == 0 or k == n - 1:
            out.append(f'<text class="num" x="{X0 + k * CW + CW / 2}" y="10" text-anchor="middle">{k}</text>')
    filas = []
    for b in "abcdef":
        rs = sorted((r for r in L if r["brazo"] == b), key=lambda r: int(r["semilla"]))
        out.append(f'<text class="lbl" x="0" y="{y + 2 * RH}" dominant-baseline="middle">{name[b]}</text>')
        for r in rs:
            capas = {int(x) for x in r["capas"].split(";")}
            for k in range(n):
                c = cls[b] if k in capas else "off"
                out.append(f'<rect class="{c}" x="{X0 + k * CW + 1}" y="{y + 1}" width="{CW - 2}" height="{RH - 2}" rx="1.5"><title>{name[b]}, seed {r["semilla"]}, layer {k}</title></rect>')
            y += RH
        filas.append(y); y += GAP
    for k in sorted(mit):
        out.append(f'<rect class="mit" x="{X0 + k * CW + 0.5}" y="{Y0 - 1}" width="{CW - 1}" height="{y - GAP - Y0 + 2}"/>')
    h = y - GAP + 4; w = X0 + n * CW + 2
    return (f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="Grid of 24 adapters by 24 layers showing which layers each adapter trains">'
            + "".join(out) + "</svg>")


t = open(os.path.join(BLOG, "src", "index.template.html"), encoding="utf-8").read()
faltan = []


def sub_math(m):   # dentro de <span class="math"> las macros van sin traducir a HTML
    return m.group(1) + re.sub(r"\{\{M:(\w+)\}\}", lambda x: html(M[x.group(1)], math=True), m.group(2)) + m.group(3)


t = re.sub(r'(<span class="math">)(.*?)(</span>)', sub_math, t)


def rep(m):
    kind, key = m.group(1), m.group(2)
    src = M if kind == "M" else R
    if key not in src: faltan.append(m.group(0)); return m.group(0)
    return html(src[key])


t = re.sub(r"\{\{([MR]):([^}|]+)\}\}", rep, t)
assert not faltan, "claves que no existen: " + ", ".join(faltan)
t = t.replace("{{DESIGN}}", design_svg())
t = t.replace("{{DRAFT}}", f' · <span class="draft">{M["DraftMark"]}</span>' if M["DraftMark"] else "")
assert "{{" not in t, "quedo un marcador sin llenar"

# ---- frases: prohibidas y obligatorias (sobre el texto visible) ----
texto = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<svg.*?</svg>", " ", t, flags=re.S))).lower()
PROHIBIDAS = ["pre-registered", "preregistered", "pre-registration", "it was the data", "the data mattered", "regardless of which layers",
              "layer choice does not matter", "the place does not matter", "no harm", "opus is equal", "as good as random",
              "the sweep found the right layers", "beats standard lora"]
OBLIGATORIAS = ["opus did not beat random layers or a cheap rule", "the place seems to matter, but opus did not find a better one than chance",
                "exploratory", "pre-specified", "p50c"]
malas = [p for p in PROHIBIDAS if p in texto]; faltan = [p for p in OBLIGATORIAS if p not in texto]
assert not malas, f"frases prohibidas en el blog: {malas}"
assert not faltan, f"frases obligatorias que faltan: {faltan}"
for f in ("figures/fig1.svg", "figures/fig2.svg", "figures/fig3.svg", "paper.pdf", "style.css", "js/math.js", "vendor/katex/katex.min.js", "vendor/katex/katex.min.css"):
    assert os.path.exists(os.path.join(BLOG, f)), f"falta {f}"

open(os.path.join(BLOG, "index.html"), "w", encoding="utf-8", newline="\n").write(t)
n_num = len(re.findall(r"\{\{[MR]:", open(os.path.join(BLOG, "src", "index.template.html"), encoding="utf-8").read()))
print(f"blog escrito: paper2/blog/index.html ({n_num} numeros desde macros; frases revisadas)")
