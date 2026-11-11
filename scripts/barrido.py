"""Barrido del brazo "Opus + barrido" (DISENO_BARRIDO.md). Corre en WSL (~/venv-lora). Solo pasadas hacia adelante.
Uso: python barrido.py <salida.csv> [--cpu] [--max-frag N] [--capas 0,5,23] [--contexto 8192]
- Fragmentos: las 37 respuestas de diagnóstico al límite (resultados/diag/respuestas_s0.csv), 8 puntos cada una:
  el corte de la primera copia (detector del paper 1, revisado cada 512 tokens) y 7 finales de párrafo repartidos
  parejo después del corte. Control positivo: las respuestas que cierran solas, en su </think> real.
- Condiciones: normal, y el MLP de cada capa en cero o reemplazado por su media (media medida en los contextos
  de los puntos principales con el modelo normal).
- Métricas: log P(</think>) como siguiente token, log P de la frase de cierre de P1b tras "\\n\\n", y log P de los
  32 tokens reales que siguen. Escribe una fila por fragmento y condición, y retoma si el CSV ya existe."""
import bisect, copy, csv, json, os, sys, time

P2 = "/workspace/proyecto/paper2"
MODELO = os.path.expanduser("~/modelos/Qwen3.5-0.8B")
INSTRUCCION = "Please reason step by step, and put your final answer within " + chr(92) + "boxed{}."
W, K, L, CADA = 300, 3, 6000, 512            # detector del paper 1 (scripts/correr_vllm_reintento.py)
FRASE = "Okay, I have thought about this enough. I will stop here and give my final answer now.\n</think>"
PUNTOS_EXTRA, CONT, CAPAS = 7, 32, 24
CAMPOS = ["frag", "problema", "tipo", "capa", "variante", "lp_think", "lp_frase", "lp_cont", "tokens_ctx", "segundos"]


def opcion(nombre, defecto):
    a = sys.argv
    return a[a.index(nombre) + 1] if nombre in a else defecto


def hay_bucle(t):
    c = t[-L:]
    return len(c) >= W and c.count(c[-W:]) >= K


def recortar(t):
    c = t[-L:]
    return len(t) - len(c) + c.find(c[-W:]) + W


def fragmentos(tok):
    filas = list(csv.DictReader(open(f"{P2}/resultados/diag/respuestas_s0.csv", encoding="utf-8")))
    textos = {j["id"]: j["texto"] for j in map(json.loads, open(f"{P2}/resultados/diag/respuestas_s0.csv.jsonl", encoding="utf-8"))}
    probs = {j["id"]: j["problem"] for j in map(json.loads, open(f"{P2}/datos/diag40.jsonl", encoding="utf-8"))}
    assert set(textos) == set(probs) and len(probs) == 40, "no son los 40 de diagnóstico"
    out, sin_bucle = [], []
    for n, r in enumerate(filas, 1):
        t = textos[r["id"]]
        e = tok(t, add_special_tokens=False, return_offsets_mapping=True)
        ids, fin = e["input_ids"], [o[1] for o in e["offset_mapping"]]
        def corte(c):                          # número de tokens que caben enteros antes del carácter c
            return bisect.bisect_right(fin, c)
        base = dict(problema=n, id=r["id"], enunciado=probs[r["id"]], ids=ids)
        if r["llego_limite"] != "1":
            if "</think>" in t:
                k = corte(t.index("</think>"))
                out.append(dict(base, tipo="cierre_natural", k=k))
            continue
        k0 = next((corte(recortar(t[:fin[k - 1]])) for k in range(CADA, len(ids) + 1, CADA) if hay_bucle(t[:fin[k - 1]])), None)
        if k0 is None or k0 + CONT > len(ids):
            sin_bucle.append(n); continue
        out.append(dict(base, tipo="principal", k=k0))
        for sep in ("\n\n", "\n"):             # finales de párrafo; si no alcanzan, finales de línea
            cand = [corte(i + len(sep)) for i in range(fin[k0 - 1], len(t) - len(sep)) if t[i:i + len(sep)] == sep]
            cand = sorted({c for c in cand if k0 < c <= len(ids) - CONT})
            if len(cand) >= PUNTOS_EXTRA:
                break
        if len(cand) < PUNTOS_EXTRA:           # tampoco hay líneas suficientes: posiciones parejas de tokens
            cand = [k0 + (len(ids) - CONT - k0) * (j + 1) // (PUNTOS_EXTRA + 1) for j in range(PUNTOS_EXTRA)]
        else:
            cand = [cand[round(j * (len(cand) - 1) / (PUNTOS_EXTRA - 1))] for j in range(PUNTOS_EXTRA)]
        out += [dict(base, tipo="bucle", k=c) for c in cand]
    for i, f in enumerate(out):
        f["frag"] = i
    return out, sin_bucle


def main():
    cpu = "--cpu" in sys.argv
    if cpu:
        os.environ["CUDA_VISIBLE_DEVICES"] = ""; sys.modules["fla"] = None
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    salida, ctx_max = sys.argv[1], int(opcion("--contexto", 8192))
    capas = [int(c) for c in opcion("--capas", ",".join(map(str, range(CAPAS)))).split(",")]
    tok = AutoTokenizer.from_pretrained(MODELO)
    frags, sin_bucle = fragmentos(tok)
    frags = frags[:int(opcion("--max-frag", len(frags)))]
    print(f"fragmentos {len(frags)} | por tipo", {t: sum(f['tipo'] == t for f in frags) for t in ("principal", "bucle", "cierre_natural")},
          "| sin bucle detectado:", sin_bucle, flush=True)
    json.dump([{k: f[k] for k in ("frag", "problema", "id", "tipo", "k")} for f in frags],
              open(salida + ".fragmentos.json", "w"), indent=0)
    disp = "cpu" if cpu else "cuda"
    m = AutoModelForCausalLM.from_pretrained(MODELO, dtype=torch.float32 if cpu else torch.bfloat16).to(disp).eval()
    capas_m = m.model.layers
    think = tok.convert_tokens_to_ids("</think>")
    nl, frase = tok("\n\n", add_special_tokens=False)["input_ids"], tok(FRASE, add_special_tokens=False)["input_ids"]
    prompts = {}

    def contexto(f):
        if f["problema"] not in prompts:
            p = tok.apply_chat_template([{"role": "user", "content": f["enunciado"] + "\n" + INSTRUCCION}], tokenize=False,
                                        add_generation_prompt=True, enable_thinking=True)
            prompts[f["problema"]] = tok(p, add_special_tokens=False)["input_ids"]
        return prompts[f["problema"]] + f["ids"][max(0, f["k"] - ctx_max):f["k"]]

    def lp(logits, objetivo):                  # suma de log P de los tokens objetivo
        return torch.log_softmax(logits.float(), -1).gather(-1, torch.tensor(objetivo, device=disp)[:, None]).sum().item()

    @torch.no_grad()
    def medir(f):
        ctx = contexto(f)
        o = m(input_ids=torch.tensor([ctx], device=disp), use_cache=True, logits_to_keep=1)
        ult = o.logits[0, -1]
        r = dict(lp_think=lp(ult[None], [think]), tokens_ctx=len(ctx))
        if f["tipo"] == "cierre_natural":
            return dict(r, lp_frase="", lp_cont="")
        c2 = copy.deepcopy(o.past_key_values)
        real = f["ids"][f["k"]:f["k"] + CONT]
        o2 = m(input_ids=torch.tensor([real], device=disp), past_key_values=o.past_key_values, use_cache=True)
        r["lp_cont"] = lp(torch.cat([ult[None], o2.logits[0, :-1]]), real)
        o3 = m(input_ids=torch.tensor([nl + frase], device=disp), past_key_values=c2, use_cache=True)
        r["lp_frase"] = lp(o3.logits[0, len(nl) - 1:-1], frase)
        return r

    # media de la salida de cada MLP (modelo normal, contextos de los puntos principales)
    suma, cuenta = {}, {}
    def captar(i):
        def h(_m, _x, y):
            suma[i] = suma.get(i, 0) + y[0].float().sum(0); cuenta[i] = cuenta.get(i, 0) + y.shape[1]
        return h
    gs = [capas_m[i].mlp.register_forward_hook(captar(i)) for i in capas]
    with torch.no_grad():
        for f in [f for f in frags if f["tipo"] == "principal"]:
            m(input_ids=torch.tensor([contexto(f)], device=disp), logits_to_keep=1)
    for g in gs:
        g.remove()
    media = {i: (suma[i] / cuenta[i]).to(m.dtype) for i in capas}

    hechos = set()
    if os.path.exists(salida):
        hechos = {(int(x["frag"]), int(x["capa"]), x["variante"]) for x in csv.DictReader(open(salida, encoding="utf-8"))}
    nuevo = not os.path.exists(salida)
    with open(salida, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=CAMPOS)
        if nuevo:
            w.writeheader()
        conds = [(-1, "normal")] + [(c, v) for c in capas for v in ("cero", "media")]
        t0, hechas = time.time(), 0
        for f in frags:
            for capa, var in conds:
                if (f["frag"], capa, var) in hechos:
                    continue
                g = None
                if capa >= 0:
                    fn = (lambda _m, _x, y: y * 0) if var == "cero" else (lambda _m, _x, y, v=media[capa]: v.expand_as(y))
                    g = capas_m[capa].mlp.register_forward_hook(fn)
                s = time.time()
                try:
                    r = medir(f)
                finally:
                    if g: g.remove()
                w.writerow(dict(r, frag=f["frag"], problema=f["problema"], tipo=f["tipo"], capa=capa, variante=var,
                                segundos=round(time.time() - s, 3)))
                hechas += 1
            fh.flush()
            print(f"frag {f['frag'] + 1}/{len(frags)} | {hechas} mediciones | {(time.time() - t0) / max(hechas, 1):.2f} s cada una", flush=True)


if __name__ == "__main__":
    main()
