#!/bin/bash
# Piloto del paper 2 (P0 + primeros 100 problemas de P1). NO se lanza sin el OK del usuario.
# Sin reintentos: si un paso falla, la cola se detiene y deja el error en paper2/resultados/piloto/ERROR.txt
# Lanzar con: wsl_lanzar_piloto.sh
P=/workspace/proyecto
S=$P/paper2/scripts
D=$P/paper2/datos
R=$P/paper2/resultados/piloto
M0=$HOME/modelos/Qwen3.5-0.8B
A=$HOME/modelos/paper2/piloto
LOCK=$HOME/cola_p2_piloto.lock
export VLLM_USE_FLASHINFER_SAMPLER=0

for l in cola_r3 cola_r2 cola_dia cola_noche cola_ficha cola_ficha_sem cola_ficha_otras; do
  [ -e "$HOME/$l.lock" ] && { echo "Hay otra cola activa: $l"; exit 1; }
done
pgrep -f "vllm|entrenar_lora" > /dev/null && { echo "Ya hay un proceso de GPU corriendo"; exit 1; }
[ -e "$LOCK" ] && { echo "Ya existe $LOCK"; exit 1; }
touch "$LOCK"; trap 'rm -f "$LOCK"' EXIT
mkdir -p "$R" "$A"

fallo() { echo "$(date '+%F %T') FALLÓ: $1" | tee -a "$R/ERROR.txt"; exit 1; }
paso() { echo; echo "===== $(date '+%F %T') $1"; }
lora() { source "$HOME/venv-lora/bin/activate"; }
vllm() { source "$HOME/venv-vllm/bin/activate"; }

paso "1/8 problemas fijos de MATH train (sin GPU)"
lora; python $S/preparar_math_train.py || fallo "preparar_math_train"

paso "2/8 memoria y velocidad (tokens al azar)"
python $S/piloto_memoria.py $R/memoria.csv || fallo "piloto_memoria"

paso "3/8 cortar y cerrar, bloque 00 (100 problemas de train)"
vllm; python $P/scripts/correr_vllm_reintento.py "$M0" $D/math_train_bloque00_ids.txt $D/math_train_1200.jsonl \
  $R/datos_b00 0 || fallo "cortar y cerrar"

paso "4/8 armar dataset del piloto"
lora; python $S/armar_dataset_lora.py $D/piloto_lora.jsonl 16384 $R/datos_b00_B_s0.csv || fallo "armar dataset"

CAPAS=$(python -c "import sys; sys.path.insert(0,'$S'); from comun_lora import capas_placebo; print(','.join(map(str,capas_placebo(0))))")
paso "5/8 entrenar un LoRA de prueba en capas $CAPAS"
python $S/entrenar_lora.py --datos $D/piloto_lora.jsonl --capas "$CAPAS" --semilla 0 --salida $A/adaptador \
  > $R/entrenamiento.log 2>&1 || fallo "entrenar"
cp $A/adaptador/entrenamiento.json $R/

paso "6/8 fusionar al modelo"
python $S/fusionar_lora.py $A/adaptador $A/fusionado | tee $R/fusion.log
[ "${PIPESTATUS[0]}" = "0" ] || fallo "fusionar"
cp $A/fusionado/fusion.csv $R/

paso "7/8 modelo fusionado en vLLM, 20 problemas de control"
vllm; python $S/correr_p2.py $A/fusionado p2_think_T06 $D/math_control20_ids.txt $D/math_control20.jsonl \
  $R/control_lora 0 math || fallo "control LoRA"

paso "8/8 modelo original, los mismos 20 problemas"
python $S/correr_p2.py "$M0" p2_think_T06 $D/math_control20_ids.txt $D/math_control20.jsonl \
  $R/control_original 0 math || fallo "control original"

python $S/resumir_piloto.py $R | tee $R/RESUMEN_PILOTO.md
echo "$(date '+%F %T') PILOTO TERMINADO"
