"""Entrena UN LoRA en la parte MLP de las capas pedidas. Corre en ~/venv-lora. Usa GPU salvo con --cpu.
Uso: python entrenar_lora.py --datos X.jsonl --capas 3,7,11,19|todas --semilla 0 --salida carpeta
                             [--perdida salida|todo] [--max-tokens N] [--max-pasos N] [--modelo ruta] [--cpu]
--perdida salida (por defecto): la pérdida solo cuenta en la parte de salida (cierre + respuesta).
--perdida todo: cuenta también en el pensamiento.
Las predicciones del vocabulario (248,320 tokens) se calculan solo donde cuenta la pérdida y por pedazos,
porque calcularlas de una vez no cabe en 8 GB. El orden de los datos depende solo de la semilla, no del brazo.
No sobrescribe. Escribe el adaptador y entrenamiento.json (pérdida, velocidad, memoria)."""
import argparse, json, math, os, random, sys, time
if "--cpu" in sys.argv:
    sys.modules["fla"] = None   # sus nucleos solo corren en GPU; en CPU se usa la version de PyTorch
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comun_lora import *

PEDAZO = 1024


def perdida_por_pedazos(oculto, cabeza, etiquetas):
    """Entropía cruzada sobre posiciones ya elegidas. Recalcula cada pedazo en el paso de vuelta."""
    import torch
    from torch.utils.checkpoint import checkpoint
    def trozo(h, y):
        return torch.nn.functional.cross_entropy(cabeza(h).float(), y, reduction="sum")
    total = oculto.new_zeros((), dtype=torch.float32)
    for i in range(0, oculto.shape[0], PEDAZO):
        total = total + checkpoint(trozo, oculto[i:i + PEDAZO], etiquetas[i:i + PEDAZO], use_reentrant=False)
    return total / etiquetas.numel()


def tokenizar(tok, x, perdida, max_tokens):
    ids_p = tok(x["prompt"], add_special_tokens=False)["input_ids"]
    ids_t = tok(x["pensamiento"], add_special_tokens=False)["input_ids"]
    ids_s = tok(x["salida"], add_special_tokens=False)["input_ids"]
    ids = ids_p + ids_t + ids_s
    if len(ids) > max_tokens:
        return None
    desde = len(ids_p) + (len(ids_t) if perdida == "salida" else 0)
    return ids, desde


def cargar_modelo(ruta, capas, rango, dispositivo, gc=True):
    import torch
    from transformers import AutoModelForCausalLM
    from peft import LoraConfig, get_peft_model
    m = AutoModelForCausalLM.from_pretrained(ruta, dtype=torch.float32 if dispositivo == "cpu" else torch.bfloat16).to(dispositivo)
    m.config.use_cache = False
    if gc:
        m.gradient_checkpointing_enable(gradient_checkpointing_kwargs=dict(use_reentrant=False))
        m.enable_input_require_grads()
    cfg = LoraConfig(r=rango, lora_alpha=ALFA_SOBRE_RANGO * rango, lora_dropout=0.0, bias="none",
                     target_modules=regex_modulos(capas))
    return get_peft_model(m, cfg)


def paso_perdida(modelo, ids, desde, dispositivo):
    """Pasa la secuencia por el cuerpo del modelo y calcula la pérdida solo desde la posición indicada."""
    import torch
    base = modelo.get_base_model()
    x = torch.tensor([ids], device=dispositivo)
    with torch.autocast(dispositivo, dtype=torch.bfloat16, enabled=dispositivo != "cpu"):
        h = base.model(input_ids=x).last_hidden_state[0]
        # la posición i predice el token i+1
        return perdida_por_pedazos(h[desde - 1:-1], base.lm_head, x[0, desde:])


def main():
    import torch
    from transformers import AutoTokenizer, get_cosine_schedule_with_warmup
    a = argparse.ArgumentParser()
    a.add_argument("--datos", required=True); a.add_argument("--capas", required=True)
    a.add_argument("--semilla", type=int, required=True); a.add_argument("--salida", required=True)
    a.add_argument("--perdida", default="salida", choices=["salida", "todo"])
    a.add_argument("--max-tokens", type=int, default=16384); a.add_argument("--max-pasos", type=int, default=0)
    a.add_argument("--acumular", type=int, default=8); a.add_argument("--epocas", type=int, default=1)
    a.add_argument("--modelo", default=MODELO_BASE); a.add_argument("--cpu", action="store_true")
    a.add_argument("--sin-comprobar-parametros", action="store_true", help="solo para pruebas con modelos diminutos")
    p = a.parse_args()
    if os.path.exists(f"{p.salida}/entrenamiento.json"):
        print("Ya existe; no sobrescribo:", p.salida); sys.exit(1)
    capas = list(range(CAPAS_TOTAL)) if p.capas == "todas" else [int(c) for c in p.capas.split(",")]
    rango = rango_para(capas)
    disp = "cpu" if p.cpu else "cuda"
    random.seed(p.semilla); torch.manual_seed(p.semilla)

    tok = AutoTokenizer.from_pretrained(MODELO_BASE)
    ej, fuera = [], 0
    for x in leer_jsonl(p.datos):
        t = tokenizar(tok, x, p.perdida, p.max_tokens)
        if t is None:
            fuera += 1
        else:
            ej.append(t)
    if not ej:
        raise SystemExit("No quedó ningún ejemplo")
    modelo = cargar_modelo(p.modelo, capas, rango, disp, gc=not p.cpu)
    entrenables = sum(q.numel() for q in modelo.parameters() if q.requires_grad)
    if not p.sin_comprobar_parametros and entrenables != PARAMS_OBJETIVO:
        raise SystemExit(f"Parámetros {entrenables} != {PARAMS_OBJETIVO}")
    params = [q for q in modelo.parameters() if q.requires_grad]
    opt = torch.optim.AdamW(params, lr=LR, weight_decay=0.0)

    orden = []
    for e in range(p.epocas):
        o = list(range(len(ej))); random.Random(p.semilla * 1000 + e).shuffle(o); orden += o
    pasos = math.ceil(len(orden) / p.acumular)
    if p.max_pasos:
        pasos = min(pasos, p.max_pasos); orden = orden[:pasos * p.acumular]
    sched = get_cosine_schedule_with_warmup(opt, max(1, pasos // 20), pasos)

    if not p.cpu:
        torch.cuda.reset_peak_memory_stats()
    modelo.train(); t0 = time.time(); tokens = 0; registro = []; acumulada = 0.0; n = 0
    for i, j in enumerate(orden):
        ids, desde = ej[j]
        loss = paso_perdida(modelo, ids, desde, disp)
        if not torch.isfinite(loss):
            raise SystemExit(f"Pérdida no finita en el ejemplo {i}")
        (loss / p.acumular).backward()
        acumulada += loss.item(); n += 1; tokens += len(ids)
        if n == p.acumular or i == len(orden) - 1:
            torch.nn.utils.clip_grad_norm_(params, 1.0)
            opt.step(); sched.step(); opt.zero_grad(set_to_none=True)
            registro.append(round(acumulada / n, 4))
            print(f"paso {len(registro)}/{pasos} pérdida {registro[-1]} tok/s {tokens / (time.time() - t0):.0f}", flush=True)
            acumulada, n = 0.0, 0

    os.makedirs(p.salida, exist_ok=True)
    modelo.save_pretrained(p.salida)
    json.dump(dict(capas=sorted(capas), rango=rango, alfa=ALFA_SOBRE_RANGO * rango, parametros=entrenables, semilla=p.semilla,
                   lr=LR, perdida=p.perdida, ejemplos=len(ej), ejemplos_fuera_por_largo=fuera, max_tokens=p.max_tokens,
                   pasos=len(registro), acumular=p.acumular, epocas=p.epocas, tokens=tokens,
                   segundos=round(time.time() - t0, 1), tok_por_s=round(tokens / (time.time() - t0), 1),
                   vram_pico_gb=None if p.cpu else round(torch.cuda.max_memory_allocated() / 2**30, 2),
                   perdida_inicial=registro[0], perdida_final=registro[-1], registro=registro),
              open(f"{p.salida}/entrenamiento.json", "w"), indent=1)
    print("listo:", p.salida)


if __name__ == "__main__":
    main()
