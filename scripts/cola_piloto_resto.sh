#!/bin/bash
# Pasos 7 y 8 del piloto y su resumen. La primera corrida se detuvo en el paso 7 porque faltaba
# VLLM_USE_FLASHINFER_SAMPLER=0. Sin reintentos: si un paso falla, se detiene.
P=/workspace/proyecto
S=$P/paper2/scripts
D=$P/paper2/datos
R=$P/paper2/resultados/piloto
M0=$HOME/modelos/Qwen3.5-0.8B
A=$HOME/modelos/paper2/piloto
LOCK=$HOME/cola_p2_piloto.lock
export VLLM_USE_FLASHINFER_SAMPLER=0

pgrep -f "correr_vllm|correr_p2|entrenar_lora" > /dev/null && { echo "Ya hay un proceso de GPU corriendo"; exit 1; }
[ -e "$LOCK" ] && { echo "Ya existe $LOCK"; exit 1; }
touch "$LOCK"; trap 'rm -f "$LOCK"' EXIT
fallo() { echo "$(date '+%F %T') FALLÓ: $1" | tee -a "$R/ERROR.txt"; exit 1; }
paso() { echo; echo "===== $(date '+%F %T') $1"; }

source "$HOME/venv-vllm/bin/activate"
paso "7/8 modelo fusionado en vLLM, 20 problemas de control"
python $S/correr_p2.py $A/fusionado p2_think_T06 $D/math_control20_ids.txt $D/math_control20.jsonl \
  $R/control_lora 0 math || fallo "control LoRA"

paso "8/8 modelo original, los mismos 20 problemas"
python $S/correr_p2.py "$M0" p2_think_T06 $D/math_control20_ids.txt $D/math_control20.jsonl \
  $R/control_original 0 math || fallo "control original"

python $S/resumir_piloto.py $R > $R/RESUMEN_PILOTO.md || fallo "resumen"
echo "$(date '+%F %T') PILOTO TERMINADO"
