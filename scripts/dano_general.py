"""¿Apagar una capa daña todo el modelo? (análisis pedido por el usuario sobre la capa 0 del brazo e; no cambia la regla).
Corre en WSL (~/venv-lora). Solo pasadas hacia adelante. Uso: python dano_general.py <salida.csv> [--cpu] [--max-prob N]
Para las 37 respuestas de diagnóstico al límite y dos ventanas:
- "bucle": el contexto del punto principal del barrido (prompt + últimos 8,192 tokens); se miden sus últimas 256 posiciones.
- "antes": el prompt + los primeros 1,024 tokens de la respuesta (razonamiento normal); se miden las posiciones 256 a 1,024.
En cada posición, con el MLP de cada capa en cero o por la media (la misma media que el barrido):
  KL(normal || apagado) de la distribución completa del siguiente token, si coincide el token más probable,
  y el cambio en log P del token real. Escribe una fila por problema, ventana, capa y variante."""
import csv, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
CPU = "--cpu" in sys.argv
if CPU:
    os.environ["CUDA_VISIBLE_DEVICES"] = ""; sys.modules["fla"] = None
import barrido as BR

ULT_BUCLE, ANTES_INI, ANTES_FIN, TROZO = 256, 256, 1024, 128


def main():
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    salida = sys.argv[1]
    assert not os.path.exists(salida), "no sobrescribo"
    tok = AutoTokenizer.from_pretrained(BR.MODELO)
    frags = [f for f in BR.fragmentos(tok)[0] if f["tipo"] == "principal"]
    frags = frags[:int(BR.opcion("--max-prob", len(frags)))]
    disp = "cpu" if CPU else "cuda"
    m = AutoModelForCausalLM.from_pretrained(BR.MODELO, dtype=torch.float32 if CPU else torch.bfloat16).to(disp).eval()
    capas = m.model.layers

    def prompt(f):
        p = tok.apply_chat_template([{"role": "user", "content": f["enunciado"] + "\n" + BR.INSTRUCCION}], tokenize=False,
                                    add_generation_prompt=True, enable_thinking=True)
        return tok(p, add_special_tokens=False)["input_ids"]

    ventanas = []
    for f in frags:
        p = prompt(f)
        ventanas.append((f, "bucle", p + f["ids"][max(0, f["k"] - 8192):f["k"]], ULT_BUCLE))
        ventanas.append((f, "antes", p + f["ids"][:ANTES_FIN], ANTES_FIN - ANTES_INI))

    # media de cada MLP, igual que el barrido (contextos de los puntos principales, modelo normal)
    suma, cuenta = {}, {}
    def captar(i):
        def h(_m, _x, y):
            suma[i] = suma.get(i, 0) + y[0].float().sum(0); cuenta[i] = cuenta.get(i, 0) + y.shape[1]
        return h
    gs = [capas[i].mlp.register_forward_hook(captar(i)) for i in range(BR.CAPAS)]
    with torch.no_grad():
        for f, v, ids, n in ventanas:
            if v == "bucle":
                m(input_ids=torch.tensor([ids], device=disp), logits_to_keep=1)
    for g in gs:
        g.remove()
    media = {i: (suma[i] / cuenta[i]).to(m.dtype) for i in range(BR.CAPAS)}

    @torch.no_grad()
    def logits(ids, n):        # logits de las últimas n+1 posiciones (la última no tiene token real después)
        return m(input_ids=torch.tensor([ids], device=disp), logits_to_keep=n + 1).logits[0, :-1]

    with open(salida, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["problema", "ventana", "capa", "variante", "kl_medio", "top1_igual", "cambio_lp_real", "posiciones"])
        w.writeheader()
        t0 = time.time()
        for j, (f, v, ids, n) in enumerate(ventanas):
            real = torch.tensor(ids[-n:], device=disp)
            base = logits(ids, n)
            for capa in range(BR.CAPAS):
                for var in ("cero", "media"):
                    fn = (lambda _m, _x, y: y * 0) if var == "cero" else (lambda _m, _x, y, q=media[capa]: q.expand_as(y))
                    g = capas[capa].mlp.register_forward_hook(fn)
                    try:
                        ab = logits(ids, n)
                    finally:
                        g.remove()
                    kl = top = dlp = 0.0
                    for a in range(0, n, TROZO):           # por trozos, para no llenar la memoria
                        lb = torch.log_softmax(base[a:a + TROZO].float(), -1)
                        la = torch.log_softmax(ab[a:a + TROZO].float(), -1)
                        kl += (lb.exp() * (lb - la)).sum().item()
                        top += (lb.argmax(-1) == la.argmax(-1)).sum().item()
                        r = real[a:a + TROZO, None]
                        dlp += (la.gather(-1, r) - lb.gather(-1, r)).sum().item()
                    w.writerow(dict(problema=f["problema"], ventana=v, capa=capa, variante=var, kl_medio=round(kl / n, 5),
                                    top1_igual=round(top / n, 4), cambio_lp_real=round(dlp / n, 5), posiciones=n))
            fh.flush()
            print(f"ventana {j + 1}/{len(ventanas)} | {time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
