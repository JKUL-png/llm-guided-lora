# Does It Help When an LLM Chooses Where to Train?

Opus-chosen layers for a LoRA against random and rule-based choices.

Claude Opus diagnosed why Qwen3.5-0.8B gets stuck in reasoning loops and chose which four layers to train with a LoRA adapter. We trained the same adapter, with the same data and the same number of parameters, in random layers, in layers picked by a gradient-norm rule, and in layers picked by a sweep-based rule, four seeds each. Opus did not beat random layers or a cheap rule. The place seems to matter, but Opus did not find a better one than chance.

This is part 2 of [decomposing-the-gain](https://github.com/JKUL-png/decomposing-the-gain).

- **Blog:** https://jkul-png.github.io/llm-guided-lora/
- **Paper:** [paper/llm_guided_lora.pdf](paper/llm_guided_lora.pdf), LaTeX sources in `paper/latex/`

Authors: Juan José Giraldo Márquez and Juan José Gómez. Figures by Juan José Gómez, made with AI assistance.

## Layout

| Folder | Contents |
|---|---|
| `docs/` | The blog, served with GitHub Pages, and a copy of the paper PDF. KaTeX is hosted here, with no CDN. |
| `paper/` | PDF, LaTeX sources (`latex/`, with the generated macros and tables in `latex/generated/`) and the figures with their script (`figuras/`). |
| `resultados/` | Results: one CSV per run with one row per problem (`p3/eval/`, `calificacion/`), the training and merge records, the layer sweep, and the corrected analysis after the external review (`revision/`). `ANALISIS_FINAL.md` is the full analysis, in Spanish. |
| `datos/` | Training data, diagnostic problems, the fixed evaluation subsets and the manifest of the published edit. |
| `plan/` | The plan and the arm designs, written before the results (in Spanish). |
| `scripts/` | Training, evaluation, the isolated Opus sessions (`diag/`), the analysis, and the builds of the paper's numbers and of the blog. |

Folder, file and column names and code comments are in Spanish: `resultados` = results, `datos` = data, `semilla` = seed, `brazo` = arm, `capas` = layers, `correcto` = correct, `llego_limite` = hit the token limit, `barrido` = sweep, `revision` = review.

## Reproducing the numbers (no GPU)

From the repository root, with Python 3.11+ (standard library only, except the figures):

1. `python scripts/revision/rev_estadistica.py` recomputes the corrected statistics in `resultados/revision/` from the per-problem CSVs.
2. `python scripts/make_macros.py` writes every number, table and check used by the paper to `paper/latex/generated/`. It stops if a number used in the text is missing, or if a statement made in words no longer matches the data.
3. `python paper/figuras/make_figures.py` draws the figures (needs matplotlib and pandas).
4. `python scripts/build_blog.py` builds `docs/index.html` from `docs/src/index.template.html`, with the same numbers as the paper.
5. Compile `paper/latex/main.tex` with pdfLaTeX and BibTeX.

## The runs (GPU)

Training and evaluation ran under WSL2 on one 8 GB GPU, with vLLM for generation and math-verify 0.9.0 for grading. The run scripts are published as they were used. They expect the original project layout: a folder with the [decomposing-the-gain](https://github.com/JKUL-png/decomposing-the-gain) repository at its root (whose `scripts/` provide generation and grading) and this paper under `paper2/`, at `/workspace/proyecto`. The Opus sessions ran in an isolated folder, outside the project, with only the tools in `scripts/diag/`.

Full model responses are not included in this version.

## Notes on what is published

- Personal paths in the scripts and documents were replaced by placeholders: `<proyecto>`, `<carpeta-aislada>` and `~`.
- Some Spanish documents and scripts mention `BITACORA` (the project log) and `CLAUDE.md` (instructions for the coding assistant). Those files are private and not included. The scripts in `scripts/diag/` mention `CLAUDE.md` because they test that the isolated Opus sessions could not read it.
- The plan was kept in a private git repository with no external timestamp. We call the analyses written there "pre-specified", not pre-registered. `resultados/fechas_decisiones.csv` keeps the dates of the commits that fixed key decisions, and the paper says which analyses were decided after seeing results.

## License

Code is under the MIT license (see `LICENSE`). The paper, the blog text and the results are under CC BY 4.0 (see `LICENSES/CC-BY-4.0.txt`). Third-party material keeps its own license; see `THIRD_PARTY.md`.

## Citation

```bibtex
@misc{giraldo2026where,
  title  = {Does It Help When an LLM Chooses Where to Train? Opus-Chosen Layers for a LoRA Against Random and Rule-Based Choices},
  author = {Giraldo M{\'a}rquez, Juan Jos{\'e} and G{\'o}mez, Juan Jos{\'e}},
  year   = {2026},
  url    = {https://github.com/JKUL-png/llm-guided-lora}
}
```
