#!/bin/bash
mkdir -p /workspace/proyecto/paper2/resultados/barrido
nohup bash /workspace/proyecto/paper2/scripts/cola_barrido.sh > /workspace/proyecto/paper2/resultados/barrido/cola.log 2>&1
