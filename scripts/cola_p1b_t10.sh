#!/bin/bash
# P1b a temperatura 1.0: original y LoRA P1b en los 20 de control, semilla 0. Sin reintentos. No sobrescribe.
P=/workspace/proyecto
S=$P/paper2/scripts
D=$P/paper2/datos
R=$P/paper2/resultados/p1
LOCK=$HOME/cola_p2_t10.lock
export VLLM_USE_FLASHINFER_SAMPLER=0
[ -e $LOCK ] && { echo "ya hay una cola"; exit 1; }
touch $LOCK; trap 'rm -f $LOCK' EXIT
source "$HOME/venv-vllm/bin/activate"
for par in "LoRA:$HOME/modelos/paper2/p1b/fusionado:p1b_control_T10" "Original:$HOME/modelos/Qwen3.5-0.8B:orig_control_T10"; do
  IFS=: read n m pre <<< "$par"
  echo "===== $(date '+%F %T') $n T1.0"
  python $S/correr_p2.py $m p2_think_T10 $D/math_control20_ids.txt $D/math_control20.jsonl $R/$pre 0 math \
    > $R/$pre.log 2>&1 || { echo "FALLO $n" > $R/ERROR_T10.txt; exit 1; }
done
echo "$(date '+%F %T') T10 TERMINADO"
