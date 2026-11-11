#!/bin/bash
# Lanzador oculto de cola_preparar.sh. Usa GPU.
nohup bash /workspace/proyecto/paper2/scripts/diag/cola_preparar.sh > "$HOME/cola_p2_diag.log" 2>&1
