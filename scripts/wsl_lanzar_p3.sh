#!/bin/bash
# Lanza la cola de P3 en proceso oculto. Uso: wsl_lanzar_p3.sh <etapa> [--hasta HH:MM]. Volver a lanzar el mismo comando sigue donde quedó.
E=$1; shift
mkdir -p /workspace/proyecto/paper2/resultados/p3
nohup python3 /workspace/proyecto/paper2/scripts/cola_p3.py $E "$@" >> /workspace/proyecto/paper2/resultados/p3/nohup_etapa$E.log 2>&1
