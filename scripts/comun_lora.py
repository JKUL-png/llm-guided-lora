"""Constantes compartidas del paper 2. Si algo de aquí cambia, cambia para TODOS los brazos."""
import json, os, random

RAIZ_WSL = "/workspace/proyecto"
P2 = os.path.join(RAIZ_WSL, "paper2")
MODELO_BASE = os.path.expanduser("~/modelos/Qwen3.5-0.8B")
ARCHIVO_PESOS = "model.safetensors-00001-of-00001.safetensors"

CAPAS_TOTAL = 24
K_CAPAS = 4                 # capas de los brazos (b), (c) y (d)
RANGO_TODAS = 8             # brazo (a): 24 capas
RANGO_K = 48                # brazos (b), (c), (d): 4 capas
ALFA_SOBRE_RANGO = 2        # alfa = 2 * rango en todos los brazos
PARAMS_POR_RANGO_CAPA = 13824   # gate + up + down, medido en plan_modulos_por_capa.csv
PARAMS_OBJETIVO = 2654208
SEMILLA_PLACEBO = 20261106
SEMILLAS = (0, 1, 2, 3)
MODULOS = ("gate_proj", "up_proj", "down_proj")
LR = 2e-4

CIERRE = "Okay, I have thought about this enough."   # frase de cierre de correr_vllm_reintento.py (variante B)


def capas_placebo(semilla):
    """Sorteo del brazo (c). Depende solo de la semilla, así que no puede ajustarse después."""
    return sorted(random.Random(SEMILLA_PLACEBO + semilla).sample(range(CAPAS_TOTAL), K_CAPAS))


def rango_para(capas):
    """Devuelve el rango que deja el número de parámetros exacto, o se detiene."""
    capas = sorted(set(capas))
    if len(capas) == CAPAS_TOTAL:
        r = RANGO_TODAS
    elif len(capas) == K_CAPAS:
        r = RANGO_K
    else:
        raise ValueError(f"Se esperaban {K_CAPAS} o {CAPAS_TOTAL} capas, llegaron {len(capas)}")
    if not all(0 <= c < CAPAS_TOTAL for c in capas):
        raise ValueError(f"Capa fuera de rango: {capas}")
    if len(capas) * r * PARAMS_POR_RANGO_CAPA != PARAMS_OBJETIVO:
        raise ValueError("El número de parámetros no coincide con el objetivo")
    return r


def regex_modulos(capas):
    """Expresión para PEFT: solo la parte MLP de las capas pedidas.
    AutoModelForCausalLM carga solo el modelo de texto, donde las capas se llaman model.layers.N."""
    lista = "|".join(str(c) for c in sorted(set(capas)))
    return rf".*model\.layers\.({lista})\.mlp\.({'|'.join(MODULOS)})"


def nombre_en_archivo(clave_adaptador):
    """Traduce una clave lora_A del adaptador al nombre del tensor en el archivo de pesos del modelo."""
    n = clave_adaptador.replace("base_model.model.", "", 1).replace(".lora_A.weight", ".weight")
    return n.replace("model.layers.", "model.language_model.layers.", 1)


def leer_jsonl(ruta):
    with open(ruta, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]
