#!/bin/bash
# Prueba el motor informado en CPU, con generar simulado (sin vLLM ni GPU). Usa la sesión 0 y borra su saldo al final.
source "$HOME/venv-lora/bin/activate"
export CUDA_VISIBLE_DEVICES= MOTOR_CPU=1 MOTOR_SIMULAR=1 HF_HUB_OFFLINE=1
M=<carpeta-aislada>/motor/motor.py
grep -q '"sesion": 0' <carpeta-aislada>/motor/sesion.json || { echo "instala antes la sesión 0"; exit 1; }
rm -rf "$HOME/qm_estado/informado_0"
c() { echo "--- $*"; python $M "$@" 2>&1 | tail -n "${LINEAS:-4}" | cut -c1-130; }
LINEAS=3 c ayuda; LINEAS=2 c contexto; c modelo; c saldo; LINEAS=2 c resumen; LINEAS=2 c problema 1
c ver 1 --desde 0 --hasta 80
LINEAS=12 c generar --problemas 1,2,3 --muestras 2 --temperatura 1.0
c ver-muestra 4 --desde 0 --hasta 60
c generar --problemas 5 --muestras 4 --apagar-capa 7
c saldo
LINEAS=2 c apagar 1 --desde 100 --hasta 400 --capa 3
echo "=== casos que deben fallar sin gastar"
c generar --problemas 1,2,3,4,5 --muestras 4
c generar --problemas 1 --muestras 2 --temperatura 0.8
c generar --problemas 1,1 --muestras 2
c generar --problemas 41 --muestras 1
c generar --problemas 1 --muestras 1 --apagar-capa 24
c ver-muestra 99 --desde 0 --hasta 10
c ver-muestra 1 --desde 0 --hasta 5000
c saldo
echo "=== saldo de muestras al tope"
python - <<'P'
import json, os
p = os.path.expanduser("~/qm_estado/informado_0/saldo.json"); e = json.load(open(p)); e["muestras"] = 150; json.dump(e, open(p, "w"))
P
c generar --problemas 1,2,3 --muestras 4
LINEAS=3 c generar --problemas 1,2 --muestras 5
c saldo
echo "=== elegir"
c elegir --capas 1,2,3 --razones "muy poco texto de razones aqui hoy"
c elegir --capas 1,2,3,4 --razones "$(python -c 'print("x" * 4100)')"
c elegir --capas 3,1,2,4 --razones "$(python -c 'print("Razones largas, con (parentesis), comas: y puntos. " * 60)')"
python -c "import json;d=json.load(open('<carpeta-aislada>/salida/capas_informado_0.json'));print(d['capas'],len(d['razones']),d['muestras'],d['consultas_cortas'])"
c ayuda
rm -f <carpeta-aislada>/salida/capas_informado_0.json; rm -rf "$HOME/qm_estado/informado_0"
echo FIN_PRUEBA_MOTOR_INFORMADO
