"""Lista exacta de los LoRA de P3 (sin GPU: fuerza CPU). Uso: python armar_lista_p3.py <salida.csv>
Escribe una fila por LoRA (6 brazos x 4 semillas) y verifica los parámetros de dos maneras:
1) con la fórmula (capas x rango x 13,824), y 2) construyendo el modelo con PEFT en CPU y contando los entrenables.
Además verifica el brazo MIT (capas 15 y 19, rango 96), que NO está entre los 24: solo calcula si daría lo mismo."""
import hashlib, json, os, sys
os.environ["CUDA_VISIBLE_DEVICES"] = ""
sys.modules["fla"] = None
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comun_lora import *

P2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS = f"{P2}/datos/lora_bucles.jsonl"
placebo = json.load(open(f"{P2}/datos/capas_placebo.json"))["capas"]
assert all(placebo[str(s)] == capas_placebo(s) for s in SEMILLAS), "el placebo no coincide con la regla fijada"
INFORMADO = {0: ("4", [11, 15, 19, 22]), 1: ("1", [14, 19, 22, 23]), 2: ("2", [12, 15, 17, 20]), 3: ("3", [10, 14, 15, 22])}
BARRIDO = {0: ("1", [10, 14, 15, 17]), 1: ("1", [10, 14, 15, 17]), 2: ("2", [10, 14, 15, 18]), 3: ("2", [10, 14, 15, 18])}
D, E = [10, 14, 15, 23], [0, 10, 12, 15]
BRAZOS = [("a", "normal: 24 capas", lambda s: ("-", list(range(24)))),
          ("b", "Opus informado", lambda s: INFORMADO[s]),
          ("c", "placebo al azar", lambda s: ("-", placebo[str(s)])),
          ("d", "automático por gradiente", lambda s: ("-", D)),
          ("e", "barrido automático", lambda s: ("-", E)),
          ("f", "Opus + barrido", lambda s: BARRIDO[s])]
MET = json.load(open(f"{P2}/datos/lora_bucles.jsonl.resumen.json"))
sha = hashlib.sha256(open(DATOS, "rb").read()).hexdigest()


def contar(capas, rango):
    from entrenar_lora import cargar_modelo
    m = cargar_modelo(MODELO_BASE, capas, rango, "cpu", gc=False)
    n = sum(q.numel() for q in m.parameters() if q.requires_grad)
    del m
    return n


filas, memo = [], {}
for brazo, nombre, f in BRAZOS:
    for s in SEMILLAS:
        sesion, capas = f(s)
        capas = sorted(capas)
        r = rango_para(capas)
        formula = len(capas) * r * PARAMS_POR_RANGO_CAPA
        clave = (tuple(capas), r)
        if clave not in memo:
            memo[clave] = contar(capas, r)
        assert formula == memo[clave] == PARAMS_OBJETIVO, (brazo, s, formula, memo[clave])
        filas.append(dict(n=len(filas) + 1, brazo=brazo, nombre=nombre, semilla=s, sesion_diagnostico=sesion,
                          capas=";".join(map(str, capas)), n_capas=len(capas), rango=r, alfa=ALFA_SOBRE_RANGO * r,
                          parametros_formula=formula, parametros_contados_peft=memo[clave], lr=LR, epocas=1,
                          acumular=8, perdida="salida", max_tokens=22000, ejemplos=MET["ejemplos"],
                          tokens_datos=MET["tokens_totales"], datos="datos/lora_bucles.jsonl", sha256_datos=sha[:16]))
import csv
with open(sys.argv[1], "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=filas[0].keys()); w.writeheader(); w.writerows(filas)
print("LoRA:", len(filas), "| configuraciones distintas contadas con PEFT:", len(memo), "| todos =", PARAMS_OBJETIVO)

# brazo MIT (no incluido): la fórmula y, si da igual, PEFT
mit = [15, 19]
f_mit = len(mit) * 96 * PARAMS_POR_RANGO_CAPA
print("MIT 2 capas rango 96: fórmula", f_mit, "| PEFT", contar(mit, 96), "| igual al objetivo:", f_mit == PARAMS_OBJETIVO)
try:
    rango_para(mit)
except ValueError as e:
    print("rango_para(MIT) hoy:", e)
