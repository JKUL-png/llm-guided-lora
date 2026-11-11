#!/bin/bash
# Lanzador del piloto del paper 2. En primer plano dentro de un wsl.exe oculto (así WSL no se apaga).
# Usa la GPU: requiere el OK del usuario.
nohup bash /workspace/proyecto/paper2/scripts/cola_piloto.sh > "$HOME/cola_p2_piloto.log" 2>&1
