#!/bin/bash
# Recalifica con la regla del paper 2 (respuesta tras el ÚLTIMO </think>) las referencias del paper 1 y los
# 20 de control. Sin GPU. No toca resultados/ de la raíz: escribe en paper2/resultados/calificacion/.
# Si una salida ya existe, se salta.
P=/workspace/proyecto
S=$P/paper2/scripts
R0=$P/resultados
O=$P/paper2/resultados/calificacion
D=$P/paper2/datos
mkdir -p $O
source "$HOME/venv-vllm/bin/activate"
M="math math500_subset100_ids.txt math500_subset100.jsonl"
G="gsm8k gsm8k_subset100_ids.txt gsm8k_subset100.jsonl"
I="ifeval ifeval_subset100_ids.txt ifeval_subset100.jsonl"
CTRL="math $D/math_control20_ids.txt $D/math_control20.jsonl"
uno() {  # entrada salida tarea ids jsonl
  [ -f "$2" ] && { echo "ya existe: $2"; return; }
  python $S/recalificar_p2.py "$@" || echo "FALLO: $1"
}
cuatro() {  # prefijo_raiz nombre_salida s0_sin_sufijo(0/1) tarea...
  local pre=$1 nom=$2 sin=$3; shift 3
  for s in 0 1 2 3; do
    e=$R0/${pre}_s$s.csv; [ $s = 0 ] && [ $sin = 1 ] && e=$R0/$pre.csv
    [ -f "$e" ] && uno "$e" "$O/${nom}_s$s.csv" "$@"
  done
}
cuatro linea_base_vllm           math_orig_think_T06    1 $M
cuatro cero_edicion_ficha_qwen   math_orig_think_T10    0 $M
cuatro cero_edicion_no_thinking  math_orig_nothink_T06  1 $M
cuatro r2_ed_think               math_p50c_think_T06    0 $M
cuatro r2_ed_ficha_qwen          math_p50c_think_T10    0 $M
cuatro r2_gsm8k_orig_think       gsm8k_orig_think_T06   0 $G
cuatro r2_gsm8k_orig_ficha       gsm8k_orig_think_T10   0 $G
cuatro r2_gsm8k_ed_think         gsm8k_p50c_think_T06   0 $G
cuatro r2_gsm8k_ed_ficha         gsm8k_p50c_think_T10   0 $G
cuatro r2_ifeval_orig_think      ifeval_orig_think_T06  0 $I
cuatro r2_ifeval_orig_ficha      ifeval_orig_think_T10  0 $I
cuatro r2_ifeval_ed_think        ifeval_p50c_think_T06  0 $I
cuatro r2_ifeval_ed_ficha        ifeval_p50c_think_T10  0 $I
uno $P/paper2/resultados/piloto/control_original_s0.csv $O/control_orig_think_T06_s0.csv $CTRL
uno $P/paper2/resultados/p1/p1b_control_s0.csv          $O/control_p1b_think_T06_s0.csv $CTRL
echo TERMINADO
