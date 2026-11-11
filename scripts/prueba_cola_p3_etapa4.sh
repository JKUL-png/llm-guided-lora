#!/bin/bash
# Prueba de la etapa 4 SIN GPU (modo simulacro): lista, orden, gate de OK, reanudación.
S=/workspace/proyecto/paper2/scripts; T=$(mktemp -d); export P3_RESULTADOS=$T P3_MODELOS=$T/modelos P3_SIM_SEG=0
echo "--- sin OK_USUARIO_etapa4 (debe negarse)"; python3 $S/cola_p3.py 4 --simulacro 2>&1 | tail -1
touch $T/OK_USUARIO_etapa4
echo "--- orden"; python3 $S/cola_p3.py 4 --lista | awk '{print $2}' | sed -E 's/_(a|b|c|d|e|f)[0-3]$/_<lora>/' | uniq -c
echo "--- total"; python3 $S/cola_p3.py 4 --lista | wc -l
echo "--- simulacro completo"; python3 $S/cola_p3.py 4 --simulacro | tail -2
echo "--- productos y .ok"; ls $T/estado/*.ok | wc -l; ls $T/eval | grep -c csv$
echo "--- relanzar (no debe repetir nada)"; python3 $S/cola_p3.py 4 --simulacro | grep -E "ya hechos|TERMINADA|INICIO" | head -3
rm -rf $T
