#!/bin/bash
# Instala el entorno de ENTRENAMIENTO del paper 2 en WSL (~/venv-lora), separado de ~/venv-vllm.
# Mismas versiones de torch y transformers que venv-vllm. No usa la GPU. Log: ~/instalar_lora.log
export PATH="$HOME/.local/bin:$PATH"
cd "$HOME" || exit 1
[ -d venv-lora ] || uv venv --python 3.12 venv-lora || exit 1
source venv-lora/bin/activate
{
  uv pip install "torch==2.14.0" --torch-backend=auto &&
  uv pip install "transformers==5.20.2" peft accelerate safetensors datasets numpy flash-linear-attention
} > "$HOME/instalar_lora.log" 2>&1
echo "EXIT=$?" >> "$HOME/instalar_lora.log"
tail -n 1 "$HOME/instalar_lora.log"
