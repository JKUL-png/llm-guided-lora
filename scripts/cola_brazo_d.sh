#!/bin/bash
# Prueba C: capas del brazo (d), 256 ejemplos por semilla, semillas 0 a 3. Sin reintentos. No sobrescribe.
P=/workspace/proyecto/paper2
O=$P/resultados/brazo_d
LOCK=$HOME/cola_p2_brazo_d.lock
[ -e $LOCK ] && { echo "ya hay una cola"; exit 1; }
touch $LOCK; trap 'rm -f $LOCK' EXIT
source "$HOME/venv-lora/bin/activate"
for s in 0 1 2 3; do
  echo "===== $(date '+%F %T') semilla $s"
  python $P/scripts/capas_gradiente.py $P/datos/lora_bucles.jsonl $s $O/capas_gradiente_s$s.csv 256 > $O/capas_s$s.log 2>&1 \
    || { echo "FALLO semilla $s" > $O/ERROR.txt; exit 1; }
  tail -n 1 $O/capas_s$s.log
done
echo "$(date '+%F %T') BRAZO_D TERMINADO"
