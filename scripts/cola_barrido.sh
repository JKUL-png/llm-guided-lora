#!/bin/bash
# Cola del barrido (DISENO_BARRIDO.md). Prueba de tiempo y barrido completo. Sin reintentos. No sobrescribe.
P=/workspace/proyecto/paper2
O=$P/resultados/barrido
LOCK=$HOME/cola_p2_barrido.lock
[ -e $LOCK ] && { echo "ya hay una cola"; exit 1; }
[ -e $O/barrido.csv ] && { echo "ya existe barrido.csv; no sobrescribo"; exit 1; }
touch $LOCK; trap 'rm -f $LOCK' EXIT
source "$HOME/venv-lora/bin/activate"
cd $P/scripts
echo "===== $(date '+%F %T') prueba de tiempo (2 fragmentos x 49 condiciones)"
python barrido.py $O/prueba_tiempo.csv --max-frag 2 > $O/prueba_tiempo.log 2>&1 || { echo "FALLO prueba" > $O/ERROR.txt; exit 1; }
tail -n 1 $O/prueba_tiempo.log
H=$(python -c "
import csv;x=list(csv.DictReader(open('$O/prueba_tiempo.csv')));s=sum(float(r['segundos']) for r in x)/len(x)
print(round(s*299*49/3600,2))")
echo "estimado del barrido completo: $H h"
python -c "import sys;sys.exit(0 if $H<=4 else 1)" || { echo "PARADA: estimado $H h > 4 h" > $O/ERROR.txt; echo "PARADA"; exit 1; }
echo "===== $(date '+%F %T') barrido completo"
python barrido.py $O/barrido.csv > $O/barrido.log 2>&1 || { echo "FALLO barrido" > $O/ERROR.txt; exit 1; }
tail -n 1 $O/barrido.log
python resumir_barrido.py $O/barrido.csv $O > $O/resumen.log 2>&1 || { echo "FALLO resumen" > $O/ERROR.txt; exit 1; }
cat $O/resumen.log
echo "$(date '+%F %T') BARRIDO TERMINADO"
