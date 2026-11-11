#!/bin/bash
# Prueba SIN GPU: la cola anota SIGTERM, y avisa tras un kill -9. Uso: bash prueba_sigterm_cola.sh
S=/workspace/proyecto/paper2/scripts; T=$(mktemp -d); export P3_CANDADO=$T/candado P3_RESULTADOS=$T P3_MODELOS=$T/modelos P3_SIM_SEG=20
touch $T/OK_USUARIO_etapa4
python3 $S/cola_p3.py 4 --simulacro >/dev/null 2>&1 & Q=$!; sleep 4; kill -TERM $Q; sleep 2
echo "--- tras SIGTERM"; tail -3 $T/cola_etapa4.log; cat $T/ERROR.txt; ls $T/candado 2>&1 | tail -1
rm -f $T/ERROR.txt
python3 $S/cola_p3.py 4 --simulacro >/dev/null 2>&1 & Q=$!; sleep 4; pkill -9 -P $Q; kill -9 $Q; sleep 1
echo "--- tras kill -9 y relanzar"; python3 $S/cola_p3.py 4 --simulacro >/dev/null 2>&1 & Q=$!; sleep 4; kill -TERM $Q; sleep 1; grep -E "AVISO|SEÑAL" $T/cola_etapa4.log
rm -rf $T
