"""Cola de P3/P4 por etapas, que se puede parar y seguir sin perder nada. Corre en WSL con el python del sistema (solo biblioteca estándar);
cada paso llama al python del entorno que necesita. Uso:
  python3 cola_p3.py <etapa> [--hasta HH:MM] [--simulacro] [--lista]
Etapas:
  1  brazo (a), 4 semillas: entrenar, fusionar y evaluar MATH-100 a 0.6 (+ 20 de control de (a) s0 para compararlo con P1b), luego parada 2.
  2  los otros 20 LoRA (b a f): entrenar, fusionar y evaluar MATH-100 a 0.6. Exige parada2.csv = PASA y el archivo OK_USUARIO_etapa2.
  3  temperatura 1.0: el mejor brazo según 0.6 (regla en mejor_brazo.py) y la referencia sin thinking (P4b). Exige OK_USUARIO_etapa3.
  4  (decisión 16) GSM8K e IFEval a 0.6, en este orden: P6b (original sin thinking, 4 semillas), P5a (los 24 LoRA, thinking) y P6 (original con thinking,
     semillas 1-3; la 0 ya existe del paper 1). Exige OK_USUARIO_etapa4.
Cómo para y sigue (todo sin perder nada):
- Un paso es la unidad: entrenar 1 LoRA (~26 min), fusionar (segundos) o evaluar 1 celda (hasta ~1 h). Un paso terminado deja estado/<paso>.ok.
- Parada ordenada: crear resultados/p3/PARAR, o dar --hasta HH:MM (no empieza un paso que, con su duración máxima, pasaría de esa hora).
  La cola termina el paso en curso y se detiene. Para seguir, se vuelve a lanzar el mismo comando: salta lo que tiene .ok.
- Si la cola muere en medio de un paso (corte de luz, memoria), lo hecho a medias se MUEVE a parcial/<paso>_<fecha> (no se borra) y el paso se repite entero.
- Sin reintentos: si un paso falla, deja ERROR.txt y se detiene. No sobrescribe nada que tenga .ok.
- Antes de cada paso con GPU anota nvidia-smi y se niega a empezar si hay otro proceso de GPU o más de 3,000 MiB en uso (el escritorio de Windows solo ya usa ~2,000)."""
import csv, datetime as dt, json, os, shutil, signal, subprocess, sys, time

HOME = os.path.expanduser("~")
P = "/workspace/proyecto"
S, D = f"{P}/paper2/scripts", f"{P}/paper2/datos"
SIM = "--simulacro" in sys.argv
RAIZ_R = os.environ.get("P3_RESULTADOS", f"{P}/paper2/resultados/p3")
RAIZ_A = os.environ.get("P3_MODELOS", f"{HOME}/modelos/paper2/p3")
PY_LORA, PY_VLLM = f"{HOME}/venv-lora/bin/python", f"{HOME}/venv-vllm/bin/python"
DUR_MAX = {"ent": 40, "fus": 3, "ev": 65, "ctrl": 12, "p6b_gsm8k": 60, "p6b_ifeval": 25, "p5_gsm8k": 30, "p5_ifeval": 15, "p6_gsm8k": 60, "p6_ifeval": 50}      # minutos; ev06 medido hasta 0.93 h en promedio de la celda del paper 1
LISTA = f"{P}/paper2/resultados/p3_lista_lora.csv"
MATH_IDS, MATH_JSONL = f"{P}/datos/math500_subset100_ids.txt", f"{P}/datos/math500_subset100.jsonl"
TAREAS = {"gsm8k": (f"{P}/datos/gsm8k_subset100_ids.txt", f"{P}/datos/gsm8k_subset100.jsonl"),
          "ifeval": (f"{P}/datos/ifeval_subset100_ids.txt", f"{P}/datos/ifeval_subset100.jsonl")}
ORIGINAL = f"{HOME}/modelos/Qwen3.5-0.8B"
CTRL_IDS, CTRL_JSONL = f"{D}/math_control20_ids.txt", f"{D}/math_control20.jsonl"


def ahora():
    return dt.datetime.now()


def gpu_estado():
    if SIM:
        return "simulacro", 0
    q = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"], capture_output=True, text=True).stdout.strip()
    p = subprocess.run(["nvidia-smi", "--query-compute-apps=pid", "--format=csv,noheader"], capture_output=True, text=True).stdout.split()
    return f"{q} MiB, {len(p)} procesos", (int(q) if q.isdigit() else 99999) + (100000 if p else 0)


def lora_ids(filtro):
    """(id, brazo, semilla, capas) de la lista fija p3_lista_lora.csv."""
    filas = list(csv.DictReader(open(LISTA, encoding="utf-8")))
    return [(f"{f['brazo']}{f['semilla']}", f["brazo"], int(f["semilla"]), "todas" if f["n_capas"] == "24" else f["capas"].replace(";", ","))
            for f in filas if filtro(f)]


def pasos_lora(i, b, s, capas, temps=("06",)):
    A, R = f"{RAIZ_A}/{i}", RAIZ_R
    ev = lambda t: dict(
        id=f"ev{t}_{i}", dur=DUR_MAX["ev"], gpu=True, productos=[f"{R}/eval/{i}_T{t}_s{s}{x}" for x in (".csv", ".csv.jsonl", ".csv.meta.json")],
        cmd=[PY_VLLM, f"{S}/correr_p2.py", f"{A}/fusionado", f"p2_think_T{t}", MATH_IDS, MATH_JSONL, f"{R}/eval/{i}_T{t}", str(s), "math"])
    out = [dict(id=f"ent_{i}", dur=DUR_MAX["ent"], gpu=True, productos=[f"{A}/adaptador"],
                cmd=[PY_LORA, f"{S}/entrenar_lora.py", "--datos", f"{D}/lora_bucles.jsonl", "--capas", capas, "--semilla", str(s),
                     "--max-tokens", "22000", "--salida", f"{A}/adaptador"], tras=lambda: shutil.copy(f"{A}/adaptador/entrenamiento.json", f"{R}/entrenamiento/{i}.json")),
           dict(id=f"fus_{i}", dur=DUR_MAX["fus"], gpu=False, productos=[f"{A}/fusionado"],
                cmd=[PY_LORA, f"{S}/fusionar_lora.py", f"{A}/adaptador", f"{A}/fusionado"], tras=lambda: shutil.copy(f"{A}/fusionado/fusion.csv", f"{R}/fusion/{i}.csv"))]
    return out + [ev(t) for t in temps]


def plan(etapa):
    R = RAIZ_R
    if etapa == 1:
        pasos = []
        for i, b, s, c in lora_ids(lambda f: f["brazo"] == "a"):
            pasos += pasos_lora(i, b, s, c)
            if s == 0:      # prueba de reproducibilidad: los mismos 20 de control que P1b
                pasos.append(dict(id="ctrl20_a0", dur=DUR_MAX["ctrl"], gpu=True,
                                  productos=[f"{R}/eval/a0_control20_s0{x}" for x in (".csv", ".csv.jsonl", ".csv.meta.json")],
                                  cmd=[PY_VLLM, f"{S}/correr_p2.py", f"{RAIZ_A}/a0/fusionado", "p2_think_T06", CTRL_IDS, CTRL_JSONL, f"{R}/eval/a0_control20", "0", "math"]))
        pasos.append(dict(id="parada2", dur=1, gpu=False, productos=[f"{R}/parada2.csv", f"{R}/repro_a0.csv"],
                          cmd=[sys.executable, f"{S}/parada2_a.py", R]))
        return pasos
    if etapa == 2:
        pasos = []
        for i, b, s, c in lora_ids(lambda f: f["brazo"] != "a"):
            pasos += pasos_lora(i, b, s, c)
        return pasos
    if etapa == 3:
        pasos = [dict(id="mejor_brazo", dur=1, gpu=False, productos=[f"{R}/mejor_brazo.csv"], cmd=[sys.executable, f"{S}/mejor_brazo.py", R])]
        mejor = f"{R}/mejor_brazo.csv"
        if os.path.exists(mejor):
            b = list(csv.DictReader(open(mejor, encoding="utf-8")))[0]["brazo"]
            for i, bb, s, c in lora_ids(lambda f: f["brazo"] == b):
                pasos.append(pasos_lora(i, bb, s, c, temps=("10",))[2])
        pasos.append(dict(id="ref_sin_thinking_T10", dur=100, gpu=True,
                          productos=[f"{R}/eval/ref_nothink_T10_s{s}{x}" for s in range(4) for x in (".csv", ".csv.jsonl", ".csv.meta.json")],
                          cmd=[PY_VLLM, f"{S}/correr_p2.py", f"{HOME}/modelos/Qwen3.5-0.8B", "p2_nothink_T10", MATH_IDS, MATH_JSONL, f"{R}/eval/ref_nothink_T10", "0,1,2,3", "math"]))
        return pasos
    if etapa == 4:
        R = RAIZ_R
        def paso(id_, dur, modelo, config, tarea, pref, sem):
            ids, jl = TAREAS[tarea]
            return dict(id=id_, dur=dur, gpu=True, productos=[f"{R}/eval/{pref}_s{s}{x}" for s in sem.split(",") for x in (".csv", ".csv.jsonl", ".csv.meta.json")],
                        cmd=[PY_VLLM, f"{S}/correr_p2.py", modelo, config, ids, jl, f"{R}/eval/{pref}", sem, tarea])
        pasos = [paso(f"p6b_{t}", DUR_MAX[f"p6b_{t}"], ORIGINAL, "p2_nothink_T06", t, f"p6b_{t}_orig_nothink_T06", "0,1,2,3") for t in TAREAS]
        for i, b, s, c in lora_ids(lambda f: True):
            for t in TAREAS:
                pasos.append(paso(f"p5_{t}_{i}", DUR_MAX[f"p5_{t}"], f"{RAIZ_A}/{i}/fusionado", "p2_think_T06", t, f"p5_{t}_{i}_T06", str(s)))
        for t in TAREAS:
            for s in (1, 2, 3):
                pasos.append(paso(f"p6_{t}_s{s}", DUR_MAX[f"p6_{t}"], ORIGINAL, "p2_think_T06", t, f"p6_{t}_orig_think_T06", str(s)))
        return pasos
    raise SystemExit("etapa 1, 2, 3 o 4")


def simular(paso):
    """Reemplaza el comando por uno que crea los productos (para probar la cola sin GPU)."""
    codigo = "import os,time,sys\ntime.sleep(float(os.environ.get('P3_SIM_SEG','1')))\n" + "\n".join(
        f"p={p!r}\nos.makedirs(os.path.dirname(p),exist_ok=True)\nif p.endswith(('adaptador','fusionado')):\n os.makedirs(p,exist_ok=True)\n open(p+'/entrenamiento.json','w').write('{{}}'); open(p+'/fusion.csv','w').write('x')\nelse:\n open(p,'w').write('x')"
        for p in paso["productos"])
    return [sys.executable, "-c", codigo]


def main():
    etapa = int(sys.argv[1])
    hasta = None
    if "--hasta" in sys.argv:
        h, m = map(int, sys.argv[sys.argv.index("--hasta") + 1].split(":"))
        hasta = ahora().replace(hour=h, minute=m, second=0, microsecond=0)
        if hasta <= ahora():
            hasta += dt.timedelta(days=1)
    R = RAIZ_R
    for d in ("estado", "logs", "eval", "entrenamiento", "fusion", "parcial"):
        os.makedirs(f"{R}/{d}", exist_ok=True)
    pasos = plan(etapa)
    if "--lista" in sys.argv:
        for p in pasos:
            print(("HECHO " if os.path.exists(f"{R}/estado/{p['id']}.ok") else "falta ") + p["id"], f"(máx. {p['dur']} min)")
        return
    if etapa == 2:
        f = f"{R}/parada2.csv"
        filas = list(csv.DictReader(open(f, encoding="utf-8"))) if os.path.exists(f) else []
        ok = bool(filas) and filas[0].get("decision") == "PASA"
        assert ok, "la parada 2 no dice PASA; la etapa 2 no se lanza"
    if etapa in (2, 3, 4):
        assert os.path.exists(f"{R}/OK_USUARIO_etapa{etapa}"), f"falta {R}/OK_USUARIO_etapa{etapa} (se crea solo tras el OK del usuario)"
    lock = os.environ.get("P3_CANDADO", f"{HOME}/cola_p2_p3.lock")
    if os.path.exists(lock):       # candado: si el proceso que lo puso ya no existe (corte, memoria), se retoma
        try:
            os.kill(int(open(lock).read().strip() or 0), 0)
            raise SystemExit("ya hay una cola de P3 corriendo: " + lock)
        except (ProcessLookupError, ValueError):
            print("candado viejo de un proceso que ya no existe: lo retomo")
    open(lock, "w").write(str(os.getpid()))
    try:
        log = open(f"{R}/cola_etapa{etapa}.log", "a", encoding="utf-8")
        w = lambda t: (print(t, flush=True), log.write(t + "\n"), log.flush())
        w(f"===== {ahora():%F %T} etapa {etapa} | {sum(os.path.exists(R + '/estado/' + p['id'] + '.ok') for p in pasos)} de {len(pasos)} pasos ya hechos | hasta {hasta or 'sin límite'}{' | SIMULACRO' if SIM else ''}")
        # si la corrida anterior terminó sin FIN/ETAPA (cierre brusco de WSL, apagón), se anota ahora
        previas = [l for l in open(f"{R}/cola_etapa{etapa}.log", encoding="utf-8").read().splitlines() if l.strip() and not l.startswith("=====")]
        ult = [l for l in previas if " INICIO " in l or " FIN " in l or "TERMINADA" in l or "FALLÓ" in l or "me detengo" in l or "SEÑAL" in l]
        if ult and " INICIO " in ult[-1]:
            w(f"{ahora():%F %T} AVISO: la corrida anterior quedó sin cerrar tras '{ult[-1].strip()}' (la cola murió sin aviso: cierre brusco de WSL, apagón o kill -9)")
        actual = {"id": None}

        def al_recibir(signum, frame):      # SIGTERM/SIGHUP/SIGINT: se anota y se sale ordenadamente (el hijo recibe lo mismo del sistema)
            nom = signal.Signals(signum).name
            w(f"{ahora():%F %T} SEÑAL {nom} recibida durante {actual['id']}: la cola se interrumpió DESDE FUERA (no es un fallo del paso). Sin .ok; lo a medias irá a parcial/ al relanzar")
            open(f"{R}/ERROR.txt", "a").write(f"{ahora():%F %T} SEÑAL {nom} durante {actual['id']} (interrupción externa)\n")
            raise SystemExit(128 + signum)
        for sg in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
            signal.signal(sg, al_recibir)
        for p in pasos:
            marca = f"{R}/estado/{p['id']}.ok"
            if os.path.exists(marca):
                continue
            if os.path.exists(f"{R}/PARAR"):
                w(f"{ahora():%F %T} PARAR pedido: me detengo antes de {p['id']}"); return
            if hasta and ahora() + dt.timedelta(minutes=p["dur"]) > hasta:
                w(f"{ahora():%F %T} {p['id']} (máx. {p['dur']} min) no cabe antes de las {hasta:%H:%M}: me detengo"); return
            sobras = [x for x in p["productos"] if os.path.exists(x)]
            if sobras:      # quedó algo a medias: se aparta, no se borra
                dest = f"{R}/parcial/{p['id']}_{ahora():%Y%m%d_%H%M%S}"
                os.makedirs(dest)
                for x in sobras:
                    shutil.move(x, f"{dest}/{os.path.basename(x)}")
                w(f"{ahora():%F %T} restos de {p['id']} movidos a {dest}")
            if p["gpu"]:
                txt, uso = gpu_estado()
                w(f"{ahora():%F %T} nvidia-smi antes de {p['id']}: {txt}")
                if uso > 3000:
                    open(f"{R}/ERROR.txt", "a").write(f"{ahora():%F %T} GPU ocupada antes de {p['id']}: {txt}\n"); w("GPU ocupada: me detengo"); return
            actual["id"] = p["id"]
            w(f"{ahora():%F %T} INICIO {p['id']}")
            t0 = time.time()
            env = dict(os.environ, VLLM_USE_FLASHINFER_SAMPLER="0", HF_HUB_OFFLINE="1")
            r = subprocess.run(simular(p) if SIM else p["cmd"], stdout=open(f"{R}/logs/{p['id']}.log", "a"), stderr=subprocess.STDOUT, env=env)
            faltan = [x for x in p["productos"] if not os.path.exists(x)]
            if r.returncode != 0 or faltan:
                open(f"{R}/ERROR.txt", "a").write(f"{ahora():%F %T} FALLÓ {p['id']} (código {r.returncode}; faltan {len(faltan)} productos)\n")
                w(f"{ahora():%F %T} FALLÓ {p['id']}: me detengo (sin reintentos)"); return
            if p.get("tras"):
                p["tras"]()
            json.dump(dict(paso=p["id"], fin=f"{ahora():%F %T}", segundos=round(time.time() - t0, 1), gpu_despues=gpu_estado()[0]), open(marca, "w"))
            w(f"{ahora():%F %T} FIN {p['id']} ({time.time() - t0:.0f} s)")
        w(f"{ahora():%F %T} ETAPA {etapa} TERMINADA")
    finally:
        os.remove(lock)


if __name__ == "__main__":
    main()
