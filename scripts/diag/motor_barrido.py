"""Motor de la sesión "Opus + barrido" (DISENO_BARRIDO.md). Corre en WSL (~/venv-lora). Se instala como motor/motor.py.
Sin GPU ni herramientas de medición: Opus solo lee el contexto (el mismo del informado) y la tabla del barrido, y elige.
Saldo por sesión en ~/qm_estado/barrido_<k> (motor/sesion.json lo escribe el instalador). Los errores no muestran rutas."""
import base64, json, os, sys, time

BASE = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(f"{BASE}/sesion.json"))
SESION = int(S["sesion"])
ESTADO = os.path.expanduser(f"~/qm_estado/barrido_{SESION}")
CAPAS, RAZONES_MAX = 24, 4000

AYUDA = f"""Órdenes (todas gratis):
  ayuda
  contexto                   la tarea, la receta del LoRA y lo que se sabe de antes (léelo primero)
  modelo                     datos básicos del modelo
  barrido                    la tabla del barrido: efecto de apagar el MLP de cada capa en fragmentos dentro de bucles
Para terminar (una sola vez):
  elegir --capas a,b,c,d --razones "texto"
      las 4 capas (0 a 23) y tus razones: una sola línea entre comillas dobles, hasta {RAZONES_MAX} caracteres,
      sin estos caracteres: comillas dobles internas, acento grave, $, barra invertida, ; & | < >"""


class Aviso(Exception):
    pass


def estado():
    os.makedirs(ESTADO, exist_ok=True)
    p = f"{ESTADO}/saldo.json"
    return json.load(open(p)) if os.path.exists(p) else dict(lecturas=0, terminado=False)


def guardar(e):
    json.dump(e, open(f"{ESTADO}/saldo.json", "w"))


def elegir(a, e):
    if "--capas" not in a or a.index("--capas") + 1 >= len(a):
        raise Aviso("falta --capas")
    try:
        capas = sorted(int(c) for c in a[a.index("--capas") + 1].split(","))
    except ValueError:
        raise Aviso("capas no válidas")
    if len(capas) != 4 or len(set(capas)) != 4 or not all(0 <= c < CAPAS for c in capas):
        raise Aviso("elige exactamente 4 capas distintas, de 0 a 23")
    razones = " ".join(a[a.index("--razones") + 1:]) if "--razones" in a else ""
    if len(razones) < 20:
        raise Aviso("faltan las razones")
    if len(razones) > RAZONES_MAX:
        raise Aviso(f"las razones tienen {len(razones)} caracteres; el máximo es {RAZONES_MAX}")
    os.makedirs(f"{BASE}/../salida", exist_ok=True)
    json.dump(dict(sesion=SESION, capas=capas, razones=razones, lecturas=e["lecturas"], fecha=time.strftime("%F %T")),
              open(f"{BASE}/../salida/capas_barrido_{SESION}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    e["terminado"] = True
    guardar(e)
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
        print(open(f"{BASE}/contexto.md", encoding="utf-8").read())
    elif orden == "modelo":
        print("Qwen3.5-0.8B, 24 capas (0 a 23). Cada capa tiene un MLP (gate, up, down).\n"
              "Evaluación: thinking, temperaturas 0.6 y 1.0, top_p 0.95, top_k 20, presence_penalty 1.5, hasta 32,768 tokens.")
    elif orden == "barrido":
        print(open(f"{BASE}/barrido.md", encoding="utf-8").read())
    elif orden == "elegir":
        elegir(a, e)
        return
    else:
        raise Aviso("orden desconocida; usa ayuda")
    e["lecturas"] += 1
    guardar(e)


if __name__ == "__main__":
    try:
        main()
    except Aviso as x:
        print("aviso:", x)
    except Exception as x:
        print("error en la consulta:", type(x).__name__)
