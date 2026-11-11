#!/bin/bash
# P1: cortar y cerrar en los bloques 01 a 11 (el 00 ya salió en el piloto). P1b: 1 LoRA con todos los ejemplos,
# brazo normal (24 capas, rango 8, semilla 0), fusionado y probado en los 20 de control.
# Sin reintentos: si un paso falla, la cola se detiene y deja ERROR.txt. No sobrescribe salidas.
P=/workspace/proyecto
S=$P/paper2/scripts
D=$P/paper2/datos
R=$P/paper2/resultados/p1
M0=$HOME/modelos/Qwen3.5-0.8B
A=$HOME/modelos/paper2/p1b
LOCK=$HOME/cola_p2_p1.lock
export VLLM_USE_FLASHINFER_SAMPLER=0

for l in cola_p2_piloto cola_p2_diag; do
  [ -e "$HOME/$l.lock" ] && { echo "Hay otra cola activa: $l"; exit 1; }
done
pgrep -f "correr_vllm|correr_p2|entrenar_lora|capas_gradiente" > /dev/null && { echo "Ya hay un proceso de GPU corriendo"; exit 1; }
[ -e "$LOCK" ] && { echo "Ya existe $LOCK"; exit 1; }
touch "$LOCK"; trap 'rm -f "$LOCK"' EXIT
mkdir -p "$R" "$A"
fallo() { echo "$(date '+%F %T') FALLÓ: $1" | tee -a "$R/ERROR.txt"; exit 1; }
paso() { echo; echo "===== $(date '+%F %T') $1"; }

source "$HOME/venv-vllm/bin/activate"
CORRIDAS="$P/paper2/resultados/piloto/datos_b00_B_s0.csv"
for b in 01 02 03 04 05 06 07 08 09 10 11; do
  paso "P1 bloque $b"
  python $P/scripts/correr_vllm_reintento.py "$M0" $D/math_train_bloque${b}_ids.txt $D/math_train_1200.jsonl \
    $R/datos_b$b 0 > $R/bloque_$b.log 2>&1 || fallo "bloque $b"
  CORRIDAS="$CORRIDAS $R/datos_b${b}_B_s0.csv"
done

paso "P1 armar dataset"
source "$HOME/venv-lora/bin/activate"
python $S/armar_dataset_lora.py $D/lora_bucles.jsonl 22000 $CORRIDAS || fallo "armar dataset"

paso "P1b entrenar (24 capas, rango 8, semilla 0)"
python $S/entrenar_lora.py --datos $D/lora_bucles.jsonl --capas todas --semilla 0 --max-tokens 22000 --salida $A/adaptador \
  > $R/p1b_entrenamiento.log 2>&1 || fallo "entrenar"
cp $A/adaptador/entrenamiento.json $R/p1b_entrenamiento.json

paso "P1b fusionar"
python $S/fusionar_lora.py $A/adaptador $A/fusionado > $R/p1b_fusion.log || fallo "fusionar"
cp $A/fusionado/fusion.csv $R/p1b_fusion.csv

paso "P1b 20 problemas de control"
source "$HOME/venv-vllm/bin/activate"
python $S/correr_p2.py $A/fusionado p2_think_T06 $D/math_control20_ids.txt $D/math_control20.jsonl \
  $R/p1b_control 0 math > $R/p1b_control.log 2>&1 || fallo "control"

python $S/resumir_p1b.py > $R/RESUMEN_P1.md || fallo "resumen"
echo "$(date '+%F %T') P1 Y P1B TERMINADOS"
