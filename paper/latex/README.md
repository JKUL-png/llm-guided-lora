# Compilar el paper 2

Todo lo necesario está en esta carpeta (texto, bibliografía, macros y tablas generadas, figuras en PDF).

    pdflatex main
    bibtex main
    pdflatex main
    pdflatex main

En Overleaf: subir el zip y compilar con pdfLaTeX (el proyecto hace solo los pasos de BibTeX).

- `generated/` lo escribe `paper2/paper/scripts/make_macros.py` (que llama a `make_results.py`). No editar a mano: correr el script.
- `figures/` lo escribe `paper2/paper/figuras/make_figures.py`.
- Si en el PDF aparece **??clave??** en negrita, falta una clave de resultados; el script ya revisa todas las que usa `main.tex`, así que no debería pasar.
