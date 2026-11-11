"""Brazo (d): elige las 4 capas con mayor norma de gradiente, en el modelo sin entrenar. Usa GPU. Corre en ~/venv-lora.
Regla (PLAN.md): con la misma pérdida del entrenamiento, se promedia el gradiente de los pesos MLP sobre hasta 256 ejemplos
sorteados con la semilla; por capa se suman las normas ‖∂L/∂W‖ de gate, up y down. Se usa la norma cruda; la relativa a ‖W‖
solo se anota. Uso: python capas_gradiente.py <datos.jsonl> <semilla> <salida.csv> [max_ejemplos=256]. No sobrescribe."""
import csv, json, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comun_lora import *
from entrenar_lora import perdida_por_pedazos, tokenizar


def main():
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    datos, semilla, salida = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    n_max = int(sys.argv[4]) if len(sys.argv) > 4 else 256
    if os.path.exists(salida):
        print("Ya existe; no sobrescribo:", salida); sys.exit(1)
    tok = AutoTokenizer.from_pretrained(MODELO_BASE)
    xs = leer_jsonl(datos)
    random.Random(semilla).shuffle(xs)
    xs = xs[:n_max]
    m = AutoModelForCausalLM.from_pretrained(MODELO_BASE, dtype=torch.bfloat16).to("cuda")
    m.config.use_cache = False
    for q in m.parameters():
        q.requires_grad_(False)
    pesos = {k: [getattr(c.mlp, f"{n}").weight for n in MODULOS] for k, c in enumerate(m.model.layers)}
    for ws in pesos.values():
        for w in ws:
            w.requires_grad_(True)
    m.gradient_checkpointing_enable(gradient_checkpointing_kwargs=dict(use_reentrant=False))
    m.enable_input_require_grads()
    m.train()
    acum = {id(w): torch.zeros_like(w, dtype=torch.float32) for ws in pesos.values() for w in ws}
    usados = 0
    for x in xs:
        t = tokenizar(tok, x, "salida", 22000)
        if t is None:
            continue
        ids, desde = t
        v = torch.tensor([ids], device="cuda")
        with torch.autocast("cuda", dtype=torch.bfloat16):
            h = m.model(input_ids=v).last_hidden_state[0]
            p = perdida_por_pedazos(h[desde - 1:-1], m.lm_head, v[0, desde:])
        p.backward()
        for ws in pesos.values():
            for w in ws:
                acum[id(w)] += w.grad.float()
                w.grad = None
        usados += 1
    filas = []
    for k, ws in pesos.items():
        cruda = sum((acum[id(w)] / usados).norm().item() for w in ws)
        rel = sum((acum[id(w)] / usados).norm().item() / w.float().norm().item() for w in ws)
        filas.append(dict(capa=k, norma_gradiente=round(cruda, 6), norma_relativa=round(rel, 8)))
    orden = sorted(filas, key=lambda f: -f["norma_gradiente"])
    with open(salida, "w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=list(filas[0]) + ["puesto"]); w.writeheader()
        for i, f in enumerate(orden, 1):
            w.writerow(dict(f, puesto=i))
    print(json.dumps(dict(semilla=semilla, ejemplos=usados, capas=sorted(f["capa"] for f in orden[:K_CAPAS]))))


if __name__ == "__main__":
    main()
