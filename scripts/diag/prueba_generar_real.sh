#!/bin/bash
# Prueba A: 'generar' real con vLLM en la sesión 0 (prueba), sin Claude. Borra el saldo de la sesión 0 al final.
source "$HOME/venv-lora/bin/activate"
M=<carpeta-aislada>/motor/motor.py
O=/workspace/proyecto/paper2/resultados/jaula_informada
grep -q '"sesion": 0' <carpeta-aislada>/motor/sesion.json || { echo "instala antes la sesión 0"; exit 1; }
rm -rf "$HOME/qm_estado/informado_0"
c() { echo "--- $(date +%T) $*"; /usr/bin/time -f "[%e s]" python $M "$@" 2>&1 | grep -v -i warn; }
c generar --problemas 1,2 --muestras 2 --temperatura 1.0
c generar --problemas 3 --muestras 2 --apagar-capa 12
echo "copia temporal borrada: $([ -e $HOME/qm_tmp/apagada ] && echo NO || echo sí)"
c ver-muestra 5 --desde 0 --hasta 300
c saldo
cp $HOME/qm_estado/informado_0/muestras/*.json $O/ 2>/dev/null; mkdir -p $O/muestras_A; mv $O/[0-9]*.json $O/muestras_A/ 2>/dev/null
[ -f $HOME/qm_estado/informado_0/error_generar.txt ] && tail -c 2000 $HOME/qm_estado/informado_0/error_generar.txt
rm -rf "$HOME/qm_estado/informado_0"
echo FIN_PRUEBA_A
