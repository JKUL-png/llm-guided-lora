#!/bin/bash
# Prueba corta de calificación: 2 problemas de GSM8K y 2 de IFEval en el LoRA e0 (usa GPU unos minutos; la GPU debe estar libre).
P=/workspace/proyecto; O=$P/paper2/resultados/p3/prueba_p5; mkdir -p $O
echo "GPU antes: $(nvidia-smi --query-gpu=memory.used --format=csv,noheader) | procesos de cómputo: $(nvidia-smi --query-compute-apps=pid --format=csv,noheader | wc -l)" | tee $O/gpu.txt
head -2 $P/datos/gsm8k_subset100_ids.txt > $O/ids_gsm8k_2.txt
head -2 $P/datos/ifeval_subset100_ids.txt > $O/ids_ifeval_2.txt
export VLLM_USE_FLASHINFER_SAMPLER=0 HF_HUB_OFFLINE=1
M=$HOME/modelos/paper2/p3/e0/fusionado
PY=$HOME/venv-vllm/bin/python; S=$P/paper2/scripts
$PY $S/correr_p2.py $M p2_think_T06 $O/ids_gsm8k_2.txt $P/datos/gsm8k_subset100.jsonl $O/e0_gsm8k 0 gsm8k > $O/gsm8k.log 2>&1; echo "gsm8k salida: $?"
$PY $S/correr_p2.py $M p2_think_T06 $O/ids_ifeval_2.txt $P/datos/ifeval_subset100.jsonl $O/e0_ifeval 0 ifeval > $O/ifeval.log 2>&1; echo "ifeval salida: $?"
echo "GPU después: $(nvidia-smi --query-gpu=memory.used --format=csv,noheader) | procesos de cómputo: $(nvidia-smi --query-compute-apps=pid --format=csv,noheader | wc -l)" | tee -a $O/gpu.txt
