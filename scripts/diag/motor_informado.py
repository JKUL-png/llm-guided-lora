"""Motor de la sesión "Opus informado". Corre en WSL (~/venv-lora). Se instala como motor/motor.py, junto al motor del
ciego copiado como motor/base.py, del que reutiliza las consultas cortas sin cambiarlas.
Cambios respecto del ciego (DISENO_INFORMADO.md): orden 'contexto', 'generar' en vLLM hasta 32,768 tokens con varias
muestras y problemas, 'ver-muestra', dos saldos (50 cortas y 160 muestras), saldo y semilla propios por sesión
(motor/sesion.json, que escribe el instalador) y 'elegir' con razones largas. Los errores nunca muestran rutas ni trazas."""
import base64, json, os, subprocess, sys, time

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import base as B

S = json.load(open(f"{BASE}/sesion.json"))
SESION, SEMILLA = int(S["sesion"]), int(S["semilla"])
ESTADO = os.path.expanduser(f"~/qm_estado/informado_{SESION}")
B.ESTADO = ESTADO
CORTAS, MUESTRAS, MAX_POR_LLAMADA, MAX_TOKENS = 50, 160, 16, 32768
TEMPERATURAS = (0.6, 1.0)
RAZONES_MAX = 4000
SIMULAR = os.environ.get("MOTOR_SIMULAR") == "1"   # solo para pruebas en CPU: generar_vllm.py inventa las muestras
PY_VLLM = sys.executable if SIMULAR else os.path.expanduser("~/venv-vllm/bin/python")
Aviso = B.Aviso

AYUDA = f"""Órdenes gratis:
  ayuda
  contexto                   la tarea, la receta del LoRA y lo que se sabe de antes (léelo primero)
  modelo                     datos básicos del modelo
  resumen                    tabla de las 40 respuestas guardadas (temperatura 0.6)
  problema N                 enunciado y respuesta oficial (N de 1 a 40)
  ver N --desde C --hasta D  fragmento de la respuesta guardada del problema N (máx. 3000 caracteres)
  ver-muestra ID --desde C --hasta D   fragmento de una muestra creada con generar (máx. 3000 caracteres)
  saldo                      lo que llevas gastado
Consultas cortas: gastan 1 cada una (tienes {CORTAS}). Trabajan sobre la respuesta guardada; C y D son caracteres:
  activaciones N --desde C --hasta D           norma media por capa, de la corriente y de la salida del MLP
  gradientes N --desde C --hasta D             norma del gradiente de los pesos MLP por capa, para esos tokens
  apagar N --desde C --hasta D --capa L        cambio en la pérdida de esos tokens al apagar el MLP de la capa L
  lente N --pos C                              top 5 de tokens que predice cada capa en esa posición
Muestras largas: cada muestra gasta 1 (tienes {MUESTRAS}). Mismo muestreo que la evaluación, hasta {MAX_TOKENS:,} tokens:
  generar --problemas a,b,c --muestras K [--temperatura 0.6 o 1.0] [--apagar-capa L]
      problemas × K muestras, máximo {MAX_POR_LLAMADA} por llamada. Con --apagar-capa, el MLP de la capa L da cero.
      Devuelve por muestra: ID, tokens, si cerró </think>, cuántos </think>, si terminó y si acertó.
      Una llamada de 16 muestras largas puede tardar unos 15 minutos. Si tu herramienta tiene tiempo máximo, dale 60 minutos.
Para terminar (una sola vez):
  elegir --capas a,b,c,d --razones "texto"
      las 4 capas (0 a 23) y tus razones: una sola línea entre comillas dobles, hasta {RAZONES_MAX} caracteres,
      sin estos caracteres: comillas dobles internas, acento grave, $, barra invertida, ; & | < >"""

CONTEXTO = f"{BASE}/contexto.md"


def estado():
    e = B.estado()
    e.setdefault("muestras", 0); e.setdefault("llamadas_generar", 0); e.setdefault("siguiente_id", 1)
    return e


def lista_problemas(a, d):
    try:
        ns = [int(x) for x in B.opcion(a, "--problemas", str).split(",")]
    except ValueError:
        raise Aviso("problemas no válidos")
    if not ns or len(set(ns)) != len(ns) or any(n not in d for n in ns):
        raise Aviso(f"los problemas van de 1 a {len(d)}, sin repetir")
    return ns


def generar(a, e):
    d = B.datos()
    ns = lista_problemas(a, d)
    k = B.opcion(a, "--muestras")
    temp = B.opcion(a, "--temperatura", float, 0.6)
    capa = B.opcion(a, "--apagar-capa", int, -1)
    total = len(ns) * k
    if k < 1 or total > MAX_POR_LLAMADA:
        raise Aviso(f"problemas × muestras debe ir de 1 a {MAX_POR_LLAMADA}")
    if temp not in TEMPERATURAS:
        raise Aviso("la temperatura debe ser 0.6 o 1.0")
    if not -1 <= capa < B.CAPAS:
        raise Aviso("la capa va de 0 a 23")
    if e["muestras"] + total > MUESTRAS:
        raise Aviso(f"no te alcanzan las muestras: quedan {MUESTRAS - e['muestras']}")
    semilla = SEMILLA * 100000 + e["llamadas_generar"]
    os.makedirs(f"{ESTADO}/muestras", exist_ok=True)
    pedido = f"{ESTADO}/pedido.json"
    json.dump(dict(problemas=[dict(n=n, problema=d[n]["problema"], respuesta_oficial=d[n]["respuesta_oficial"]) for n in ns],
                   muestras=k, temperatura=temp, capa=capa, semilla=semilla, salida=f"{ESTADO}/respuesta.json"),
              open(pedido, "w", encoding="utf-8"), ensure_ascii=False)
    if os.path.exists(f"{ESTADO}/respuesta.json"):
        os.remove(f"{ESTADO}/respuesta.json")
    t0 = time.time()
    env = dict(os.environ, VLLM_USE_FLASHINFER_SAMPLER="0", HF_HUB_OFFLINE="1")
    r = subprocess.run([PY_VLLM, f"{BASE}/generar_vllm.py", pedido], capture_output=True, text=True, env=env, timeout=3000)
    if r.returncode != 0 or not os.path.exists(f"{ESTADO}/respuesta.json"):
        open(f"{ESTADO}/error_generar.txt", "a").write(r.stderr[-4000:])
        raise RuntimeError("generar")
    salidas = json.load(open(f"{ESTADO}/respuesta.json", encoding="utf-8"))
    filas = []
    for s in salidas:
        i = e["siguiente_id"]; e["siguiente_id"] += 1
        s.update(id=i, temperatura=temp, capa_apagada=capa, semilla=semilla)
        json.dump(s, open(f"{ESTADO}/muestras/{i}.json", "w", encoding="utf-8"), ensure_ascii=False)
        filas.append(s)
    e["muestras"] += total; e["llamadas_generar"] += 1
    B.guardar(e)
    print(f"temperatura {temp} | capa apagada: {'ninguna' if capa < 0 else capa} | {time.time() - t0:.0f} s")
    print("ID   problema  tokens  cerró  cierres  terminó  acertó")
    for s in filas:
        print(f"{s['id']:<4} {s['n']:>8}  {s['tokens']:>6}  {'sí' if s['cierres'] else 'no':>5}  {s['cierres']:>7}  "
              f"{'sí' if s['termino'] else 'no':>7}  {'sí' if s['correcto'] else 'no':>6}")
    for n in ns:
        g = [s for s in filas if s["n"] == n]
        print(f"problema {n}: {sum(s['correcto'] for s in g)} de {len(g)} correctas, {sum(not s['termino'] for s in g)} al límite")
    print(f"[muestras usadas: {e['muestras']} de {MUESTRAS}]")


def ver_muestra(a):
    try:
        i = int(a[1])
    except (IndexError, ValueError):
        raise Aviso("falta el ID de la muestra")
    p = f"{ESTADO}/muestras/{i}.json"
    if not os.path.exists(p):
        raise Aviso("no existe esa muestra")
    s = json.load(open(p, encoding="utf-8"))
    c, f = B.opcion(a, "--desde"), B.opcion(a, "--hasta")
    if not 0 <= c < f or f - c > 3000:
        raise Aviso("máximo 3000 caracteres")
    print(f"[muestra {i}: problema {s['n']}, temperatura {s['temperatura']}, capa apagada "
          f"{'ninguna' if s['capa_apagada'] < 0 else s['capa_apagada']}, {len(s['texto'])} caracteres en total]\n" + s["texto"][c:f])


def elegir(a, e):
    try:
        capas = sorted(int(c) for c in B.opcion(a, "--capas", str).split(","))
    except ValueError:
        raise Aviso("capas no válidas")
    if len(set(capas)) != 4 or not all(0 <= c < B.CAPAS for c in capas):
        raise Aviso("elige exactamente 4 capas distintas, de 0 a 23")
    razones = " ".join(a[a.index("--razones") + 1:]) if "--razones" in a else ""
    if len(razones) < 20:
        raise Aviso("faltan las razones")
    if len(razones) > RAZONES_MAX:
        raise Aviso(f"las razones tienen {len(razones)} caracteres; el máximo es {RAZONES_MAX}")
    os.makedirs(f"{BASE}/../salida", exist_ok=True)
    json.dump(dict(sesion=SESION, capas=capas, razones=razones, consultas_cortas=e["usadas"], muestras=e["muestras"],
                   llamadas_generar=e["llamadas_generar"], fecha=time.strftime("%F %T")),
              open(f"{BASE}/../salida/capas_informado_{SESION}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    e["terminado"] = True
    B.guardar(e)
    print("elección guardada; ya terminaste")


def main():
    a = sys.argv[1:]
    if a[:1] == ["--b64"]:
        a = json.loads(base64.b64decode(a[1]).decode("utf-8"))
    orden = a[0] if a else "ayuda"
    e = estado()
    if e["terminado"]:
        raise Aviso("la sesión ya terminó")
    if orden == "ayuda":
        print(AYUDA)
    elif orden == "contexto":
        print(open(CONTEXTO, encoding="utf-8").read())
    elif orden == "modelo":
        print("Qwen3.5-0.8B, 24 capas. Cada capa tiene un MLP (gate, up, down).\n"
              "Evaluación: thinking, temperaturas 0.6 y 1.0, top_p 0.95, top_k 20, presence_penalty 1.5, hasta 32,768 tokens.\n"
              "Las 40 respuestas guardadas son de problemas de entrenamiento de MATH, a temperatura 0.6.")
    elif orden == "saldo":
        print(f"consultas cortas: {e['usadas']} de {CORTAS} | muestras: {e['muestras']} de {MUESTRAS}")
    elif orden == "ver-muestra":
        ver_muestra(a)
    elif orden == "generar":
        generar(a, e)
    elif orden in ("resumen", "problema", "ver"):
        libre(a)
    elif orden in B.PAGADAS and orden != "generar":
        if e["usadas"] >= CORTAS:
            raise Aviso("no te quedan consultas cortas")
        x = B.buscar(B.datos(), a)
        B.PAGADAS[orden](a, x)
        e["usadas"] += 1
        B.guardar(e)
        print(f"[consultas cortas usadas: {e['usadas']} de {CORTAS}]")
    elif orden == "elegir":
        elegir(a, e)
    else:
        raise Aviso("orden desconocida; usa ayuda")


def libre(a):
    """resumen, problema y ver: iguales al ciego."""
    d = B.datos()
    if a[0] == "resumen":
        print(f"nota: {sum(x['correcto'] for x in d.values())} de {len(d)} correctas\nN  nivel  correcta  tokens  caracteres")
        for n, x in sorted(d.items()):
            print(f"{n:2d}  {x['nivel']}  {'sí' if x['correcto'] else 'no'}  {x['tokens']}  {len(x['texto'])}")
    elif a[0] == "problema":
        x = B.buscar(d, a)
        print(x["problema"], "\nRespuesta oficial:", x["respuesta_oficial"])
    else:
        x = B.buscar(d, a)
        c, f = B.opcion(a, "--desde"), B.opcion(a, "--hasta")
        if not 0 <= c < f or f - c > 3000:
            raise Aviso("máximo 3000 caracteres")
        print(f"[{len(x['texto'])} caracteres en total]\n" + x["texto"][c:f])


if __name__ == "__main__":
    try:
        main()
    except Aviso as x:
        print("aviso:", x)
    except Exception as x:
        print("error en la consulta:", type(x).__name__, "(no se gastó la consulta)")
