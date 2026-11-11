#!/bin/bash
# Prueba de la cola de P3 en simulacro (sin GPU, sin modelos): parar, seguir, morir en medio de un paso y el límite de hora.
T=/tmp/p3test; rm -rf $T; mkdir -p $T
export P3_RESULTADOS=$T/r P3_MODELOS=$T/m P3_SIM_SEG=2
C="python3 /workspace/proyecto/paper2/scripts/cola_p3.py"
echo "--- lista etapa 1 (primeras 8)"; $C 1 --simulacro --lista | head -8
echo "--- A: pedir PARAR a los 5 s"; ($C 1 --simulacro > $T/a.out 2>&1 &); sleep 5; touch $T/r/PARAR; sleep 6
tail -3 $T/a.out; echo "pasos hechos: $(ls $T/r/estado | wc -l)"
echo "--- B: seguir y matar con kill -9 en medio de un paso"; rm $T/r/PARAR; export P3_SIM_SEG=6
($C 1 --simulacro > $T/b.out 2>&1 &); sleep 4; pkill -9 -f "cola_p3.py 1"; pkill -9 -f "time.sleep"; sleep 1
echo "pasos hechos: $(ls $T/r/estado | wc -l) | candado viejo: $(ls ~/cola_p2_p3.lock 2>&1 | tail -1)"
echo "--- C: reanudar"; export P3_SIM_SEG=1; $C 1 --simulacro > $T/c.out 2>&1
grep -a "restos\|candado\|TERMINADA\|FALL\|INICIO" $T/c.out | head -8; echo "carpeta parcial: $(ls $T/r/parcial)"; echo "pasos hechos: $(ls $T/r/estado | wc -l)"
echo "--- D: --hasta que no cabe"; rm -f $T/r/estado/ev06_a3.ok $T/r/eval/a3_T06_s3*
H=$(date -d "+10 minutes" +%H:%M); $C 1 --simulacro --hasta $H | tail -2
echo "--- E: etapa 2 sin parada2 PASA ni OK"; $C 2 --simulacro 2>&1 | tail -1
echo "--- F: restos de un paso a medias (producto sin .ok)"; rm -f $T/r/estado/ent_a3.ok; ls $T/m/a3/adaptador | head -2; export P3_SIM_SEG=1
$C 1 --simulacro 2>&1 | grep -a "restos\|FIN ent_a3\|TERMINADA"; echo "parcial: $(ls $T/r/parcial)"; ls $T/r/parcial/* | head -3
