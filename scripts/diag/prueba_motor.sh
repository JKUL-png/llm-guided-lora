#!/bin/bash
# Prueba cada orden del motor en CPU, con datos inventados, y borra todo al terminar. No usa la GPU.
source "$HOME/venv-lora/bin/activate"
export CUDA_VISIBLE_DEVICES= MOTOR_CPU=1 HF_HUB_OFFLINE=1
M=<carpeta-aislada>/motor/motor.py
F=<carpeta-aislada>/motor/datos/respuestas.jsonl
[ -e "$F" ] && { echo "Ya hay datos reales; no pruebo"; exit 1; }
rm -rf "$HOME/qm_estado"
python - "$F" <<'EOF'
import json, sys
t = "Let me add the numbers. Two plus two is four. " * 12
with open(sys.argv[1], "w", encoding="utf-8") as f:
    for n in (1, 2):
        f.write(json.dumps(dict(n=n, nivel=1, problema="What is 2 + 2?", respuesta_oficial="4", texto=t, tokens=130, correcto=0)) + "\n")
EOF
c() { echo "--- $*"; python $M "$@" 2>/dev/null | tail -n "${LINEAS:-4}" | cut -c1-120; }
c ayuda; c modelo; c resumen; c problema 1; c ver 1 --desde 0 --hasta 60; c saldo
c activaciones 1 --desde 50 --hasta 200
c gradientes 1 --desde 50 --hasta 200
c apagar 1 --desde 50 --hasta 200 --capa 3
c lente 1 --pos 100
c generar 1 --max-tokens 12 --apagar-capa 3
echo "=== casos que deben fallar sin gastar"
c ver 9 --desde 0 --hasta 10
c ver 1 --desde 0 --hasta 9000
c gradientes 1 --desde 0 --hasta 9000
c apagar 1 --desde 0 --hasta 100 --capa 99
c elegir --capas 1,2,3 --razones "muy poco texto de razones aqui hoy"
c saldo
c elegir --capas 1,2,3,4 --razones "Prueba con razones suficientes y (parentesis)"
cat <carpeta-aislada>/salida/capas.json | cut -c1-120
c ayuda
rm -f "$F" <carpeta-aislada>/salida/capas.json; rm -rf "$HOME/qm_estado"
echo FIN_PRUEBA_MOTOR
