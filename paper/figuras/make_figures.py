"""Regenerates every figure of paper 2 from the CSVs in paper2/resultados/.

Usage (from the project root):  python paper/figuras/make_figures.py
No plotted value is typed here: this file holds only labels, styles and offsets.
Output: paper2/paper/latex/figures/fig{1,2,3}.pdf (+ .png for checking) and paper2/blog/figures/fig{1,2,3}.svg. Same visual style as paper 1.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "resultados"
REV = RES / "revision"
OUT = Path(__file__).resolve().parents[1] / "latex" / "figures"
OUT.mkdir(parents=True, exist_ok=True)
BLOG = ROOT / "docs" / "figures"   # same figures, as SVG, for the blog
BLOG.mkdir(parents=True, exist_ok=True)

# ---- One style for all figures (Okabe-Ito palette, as in paper 1) ----
C_ORIG, C_P50C = "#0072B2", "#D55E00"
C_OPUS, C_AUTO, C_FULL = "#CC79A7", "#009E73", "#555555"
INK, MUTED, GRID = "#222222", "#666666", "#E4E4E4"
WIDE = 7.0
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 8, "axes.labelsize": 8,
    "xtick.labelsize": 7, "ytick.labelsize": 7.5, "legend.fontsize": 7.5,
    "axes.edgecolor": MUTED, "axes.linewidth": 0.6, "axes.labelcolor": INK,
    "xtick.color": MUTED, "ytick.color": MUTED, "xtick.labelcolor": INK, "ytick.labelcolor": INK,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.axisbelow": True, "legend.frameon": False,
    "pdf.fonttype": 42, "svg.fonttype": "none",
})

ORDER = ["a", "b", "c", "d", "e", "f", "N", "T", "P"]
LABEL = {"a": "(a)", "b": "(b)", "c": "(c)", "d": "(d)", "e": "(e)", "f": "(f)", "N": "N", "T": "T", "P": "P"}
COLOR = {"a": C_FULL, "b": C_OPUS, "f": C_OPUS, "c": C_AUTO, "d": C_AUTO, "e": C_AUTO, "N": C_ORIG, "T": C_ORIG, "P": C_P50C}
MARK = {"N": "v", "T": "o", "P": "o"}
TASK = {"math": "MATH-500 (100 problems)", "gsm8k": "GSM8K (100 problems)", "ifeval": "IFEval (100 prompts)"}


def seeds(text, sep=" / "):
    return [float(x) for x in str(text).replace(" / ", " ").split()]


def save(fig, name):
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight", pad_inches=0.03)
    fig.savefig(OUT / f"{name}.png", dpi=300, bbox_inches="tight", pad_inches=0.03)
    fig.savefig(BLOG / f"{name}.svg", bbox_inches="tight", pad_inches=0.03, metadata={"Date": None})
    plt.close(fig)


def ci_point(ax, x, y, lo, hi, color, marker="o", filled=True, size=5.5):
    ax.plot([x, x], [lo, hi], color=color, lw=2.6, alpha=0.35, solid_capstyle="butt", zorder=2)
    ax.plot([x], [y], marker=marker, ms=size, mew=1.0, mec=color, mfc=color if filled else "white", ls="none", zorder=4)


def seed_dots(ax, x, vals, color):
    n = len(vals)
    for i, v in enumerate(vals):
        ax.plot([x + 0.22 + 0.05 * (i - (n - 1) / 2)], [v], marker="o", ms=2.2, mec="none", mfc=color, alpha=0.8, ls="none", zorder=3)


# ---- Figure 1: accuracy per model, three tasks, T = 0.6 ----
def fig1():
    m = pd.read_csv(REV / "rev_por_modelo.csv")
    m = m[m.temp == "T06"]
    fig, axes = plt.subplots(1, 3, figsize=(WIDE, 2.7), sharey=True)
    for ax, task in zip(axes, ["math", "gsm8k", "ifeval"]):
        t = m[m.tarea == task].set_index("modelo")
        ax.axhline(t.loc["N", "pct_correctas"], color=C_ORIG, lw=0.8, ls=(0, (4, 3)), zorder=1)
        for i, arm in enumerate(ORDER):
            r = t.loc[arm]
            ci_point(ax, i, r.pct_correctas, r.ic95_dosvias_bajo, r.ic95_dosvias_alto, COLOR[arm], MARK.get(arm, "o"), filled=arm != "T")
            seed_dots(ax, i, [100 * v / 100 for v in seeds(r.por_semilla)], COLOR[arm])
        ax.axvline(5.5, color=GRID, lw=0.8)
        ax.set_xticks(range(len(ORDER)), [LABEL[a] for a in ORDER], fontsize=7)
        ax.set_xlim(-0.6, len(ORDER) - 0.3)
        ax.set_title(TASK[task], fontsize=8, color=INK)
    axes[0].set_ylabel("Correct (%)")
    axes[0].set_ylim(0, 80)
    handles = [Line2D([], [], color=C_FULL, marker="o", ls="none", label="LoRA, 24 layers"),
               Line2D([], [], color=C_OPUS, marker="o", ls="none", label="LoRA, layers chosen by Opus"),
               Line2D([], [], color=C_AUTO, marker="o", ls="none", label="LoRA, layers chosen at random or by a rule"),
               Line2D([], [], color=C_ORIG, marker="v", ls="none", label="Original model (N: no-thinking; T: thinking, hollow)"),
               Line2D([], [], color=C_P50C, marker="o", ls="none", label="P: p50c (MIT edit), thinking"),
               Line2D([], [], color=C_ORIG, lw=0.8, ls=(0, (4, 3)), label="Original, no-thinking (level)")]
    fig.legend(handles=handles, ncol=3, loc="lower center", bbox_to_anchor=(0.5, -0.16), fontsize=7)
    save(fig, "fig1")


# ---- Figure 2: forest plot of differences, MATH, T = 0.6 ----
def fig2():
    c = pd.read_csv(REV / "rev_comparaciones.csv")
    c = c[(c.tarea == "math") & (c.temp == "T06")].set_index(["X", "Y"])
    groups = [("Primary (pre-specified)", [("b", "c"), ("b", "d")]),
              ("Secondary (pre-specified)", [("b", "a")]),
              ("Against no-thinking (pre-specified)", [(a, "N") for a in "abcdef"]),
              ("Against p50c (exploratory)", [(a, "P") for a in "abcdef"]),
              ("Among 4-layer arms (exploratory)", [("e", "d"), ("f", "e"), ("e", "b")])]
    rows, y = [], 0
    for title, pairs in groups:
        rows.append(("title", title, y)); y += 1
        for p in pairs:
            rows.append(("pair", p, y)); y += 1
        y += 0.4
    fig, ax = plt.subplots(figsize=(WIDE * 0.62, 4.6))
    names = {"a": "(a)", "b": "(b)", "c": "(c)", "d": "(d)", "e": "(e)", "f": "(f)", "N": "no-thinking", "P": "p50c"}
    for kind, item, yy in rows:
        if kind == "title":
            ax.text(-39, yy, item, fontsize=7, fontweight="bold", color=INK, va="center", ha="left")
            continue
        X, Y = item; r = c.loc[(X, Y)]
        col = C_OPUS if X in "bf" else (C_AUTO if X in "cde" else C_FULL)
        ax.plot([r.ic95_dosvias_bajo, r.ic95_dosvias_alto], [yy, yy], color=col, lw=3.0, alpha=0.35, solid_capstyle="butt")
        ax.plot([r.ic95_bajo, r.ic95_alto], [yy, yy], color=col, lw=0.9)
        ax.plot([r.dif_puntos], [yy], marker="o", ms=4.5, mec=col, mfc=col, ls="none", zorder=4)
        ax.text(-38, yy, f"{names[X]} − {names[Y]}", fontsize=7, va="center", ha="left", color=INK)
    ax.axvline(0, color=MUTED, lw=0.8)
    ax.set_ylim(y, -1); ax.set_yticks([])
    ax.set_xlim(-39, 24)
    ax.grid(axis="x", color=GRID, lw=0.6); ax.grid(axis="y", visible=False)
    ax.spines["left"].set_visible(False)
    ax.set_xlabel("Difference in correct answers (percentage points)")
    ax.set_xticks(range(-20, 25, 5))
    handles = [Line2D([], [], color=MUTED, lw=3.0, alpha=0.35, label="95% CI, problems and LoRAs (primary)"),
               Line2D([], [], color=MUTED, lw=0.9, label="95% CI, problems only (robustness)")]
    ax.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, -0.24), ncol=1, fontsize=7)
    save(fig, "fig2")


# ---- Figure 3: clean responses on MATH ----
def fig3():
    cl = pd.read_csv(REV / "rev_respuestas_limpias.csv")
    cl = cl[cl.tarea == "math"].set_index("brazo")
    lista = pd.read_csv(RES / "p3_lista_lora.csv")
    order = ["a", "b", "c", "d", "e", "f", "P"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(WIDE, 2.6), gridspec_kw={"width_ratios": [1.35, 1]})
    for i, arm in enumerate(order):
        r = cl.loc[arm]
        ci_point(ax1, i, r.pct_respuesta_limpia_1_cierre_sin_limite, r.ic95_dosvias_bajo, r.ic95_dosvias_alto, COLOR[arm])
        seed_dots(ax1, i, seeds(r.limpias_por_semilla), COLOR[arm])
    pl = lista[lista.brazo == "c"].sort_values("semilla")
    vals = seeds(cl.loc["c"].limpias_por_semilla)
    for (s, capas), v in zip(zip(pl.semilla, pl.capas), vals):
        ax1.annotate("layers " + capas.replace(";", " "), (2.0, v), xytext=(-8, {2: 7, 3: -7}.get(int(s), 0)), textcoords="offset points",
                     fontsize=5.5, color=MUTED, va="center", ha="right")
    ax1.set_xticks(range(len(order)), [LABEL[a] for a in order], fontsize=6)
    ax1.set_ylabel("Clean responses (%)")
    ax1.set_ylim(30, 100)
    ax1.set_title("One close of thinking, not at the limit", fontsize=8, color=INK)
    w = 0.38
    for i, arm in enumerate(order):
        r = cl.loc[arm]
        ax2.bar(i - w / 2, r.pct_correctas_entre_limpias, w * 0.92, color=COLOR[arm])
        ax2.bar(i + w / 2, r.pct_correctas_entre_varios_cierres, w * 0.92, facecolor="white", edgecolor=COLOR[arm], hatch="////", lw=0.8)
    ax2.set_xticks(range(len(order)), [LABEL[a] for a in order], fontsize=6)
    ax2.set_ylabel("Correct (%)")
    ax2.set_title("Accuracy by response type", fontsize=8, color=INK)
    handles = [plt.Rectangle((0, 0), 1, 1, color=MUTED, label="clean"),
               plt.Rectangle((0, 0), 1, 1, facecolor="white", edgecolor=MUTED, hatch="////", label="more than one close")]
    ax2.set_ylim(0, 100)
    ax2.legend(handles=handles, loc="upper left", ncol=2, fontsize=6.5)
    save(fig, "fig3")


if __name__ == "__main__":
    fig1(); fig2(); fig3()
    print("figures written to", OUT)
