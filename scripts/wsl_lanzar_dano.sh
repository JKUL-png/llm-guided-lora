#!/bin/bash
O=/workspace/proyecto/paper2/resultados/barrido
source "$HOME/venv-lora/bin/activate"
cd /workspace/proyecto/paper2/scripts
nvidia-smi --query-gpu=memory.used --format=csv,noheader > $O/dano_general.log
nohup python dano_general.py $O/dano_general.csv >> $O/dano_general.log 2>&1
echo "$(date '+%F %T') DANO TERMINADO" >> $O/dano_general.log
nvidia-smi --query-gpu=memory.used --format=csv,noheader >> $O/dano_general.log
