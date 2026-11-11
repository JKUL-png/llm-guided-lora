# Figuras del paper 2

Autoría: **Juan José Gómez** (hechas con ayuda de IA, Claude Code, a partir de los datos registrados).

- Script: `make_figures.py`. Lee los CSV de `paper2/resultados/` y escribe `paper2/paper/latex/figures/fig{1,2,3}.pdf` (y `.png` para revisar).
- Uso, desde la raíz del proyecto: `.venv/Scripts/python.exe paper2/paper/figuras/make_figures.py` (el `.venv` de la raíz tiene matplotlib y pandas; el Python del sistema no).
- Ningún valor dibujado está escrito a mano: el script solo tiene etiquetas, colores y posiciones. Mismo estilo que las figuras del paper 1 (paleta Okabe-Ito).

| Figura | Qué muestra | Fuente |
|---|---|---|
| 1 | % de correctas por modelo en MATH, GSM8K e IFEval a T = 0.6, con el IC de dos vías y las 4 semillas | `revision/rev_por_modelo.csv` |
| 2 | Diferencias en MATH a T = 0.6 (principales, contra no-thinking, contra p50c y entre brazos de 4 capas), con el IC de dos vías y el IC por problema | `revision/rev_comparaciones.csv` |
| 3 | Respuestas limpias en MATH por brazo (con los 4 grupos de capas del placebo) y precisión según el tipo de respuesta | `revision/rev_respuestas_limpias.csv`, `p3_lista_lora.csv` |
