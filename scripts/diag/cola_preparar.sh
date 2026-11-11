#!/bin/bash
# Genera las respuestas guardadas para la jaula: 40 problemas de MATH train, config de la línea base (MIT).
# Usa GPU unos 25 minutos (supuesto): requiere el OK del usuario. Se detiene al primer error, sin reintentos.
P=/workspace/proyecto
D=$P/paper2/datos
R=$P/paper2/resultados/diag
LOCK=$HOME/cola_p2_diag.lock
export VLLM_USE_FLASHINFER_SAMPLER=0
pgrep -f "correr_vllm|correr_p2|entrenar_lora" > /dev/null && { echo "Ya hay un proceso de GPU corriendo"; exit 1; }
[ -e "$HOME/cola_p2_piloto.lock" ] && { echo "Hay otra cola activa"; exit 1; }
[ -e "$LOCK" ] && { echo "Ya existe $LOCK"; exit 1; }
touch "$LOCK"; trap 'rm -f "$LOCK"' EXIT
mkdir -p "$R"
fallo() { echo "$(date '+%F %T') FALLÓ: $1" | tee -a "$R/ERROR.txt"; exit 1; }

source "$HOME/venv-lora/bin/activate"
python $P/paper2/scripts/diag/preparar_respuestas.py elegir $D || fallo "elegir"
source "$HOME/venv-vllm/bin/activate"
python $P/paper2/scripts/correr_p2.py "$HOME/modelos/Qwen3.5-0.8B" p2_think_T06 $D/diag40_ids.txt $D/diag40.jsonl \
  $R/respuestas 0 math || fallo "generar"
source "$HOME/venv-lora/bin/activate"
python $P/paper2/scripts/diag/preparar_respuestas.py empaquetar $D $R/respuestas_s0.csv <carpeta-aislada>/motor/datos/respuestas.jsonl || fallo "empaquetar"
echo "$(date '+%F %T') DATOS DE LA JAULA LISTOS"
