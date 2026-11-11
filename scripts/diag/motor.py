"""Motor de consultas. Corre en WSL. Los errores nunca muestran rutas ni trazas."""
import base64, json, os, sys, time

BASE = os.path.dirname(os.path.abspath(__file__))
ESTADO = os.path.expanduser("~/qm_estado")
MODELO = os.path.expanduser("~/modelos/Qwen3.5-0.8B")
PRESUPUESTO = 50
VENTANA_MAX, CONTEXTO_MAX, CAPAS = 6000, 12000, 24
INSTRUCCION = "Please reason step by step, and put your final answer within " + chr(92) + "boxed{}."
CPU = os.environ.get("MOTOR_CPU") == "1"
if CPU:
    sys.modules["fla"] = None

AYUDA = f"""Órdenes gratis:
  ayuda
  modelo                     datos básicos del modelo
  resumen                    tabla de las respuestas guardadas
  problema N                 enunciado y respuesta oficial
  ver N --desde C --hasta D  fragmento de la respuesta guardada del problema N (máx. 3000 caracteres)
  saldo                      consultas usadas
Órdenes que gastan 1 consulta (tienes {PRESUPUESTO}). Trabajan sobre la respuesta guardada; C y D son caracteres:
  activaciones N --desde C --hasta D           norma media por capa, de la corriente y de la salida del MLP
  gradientes N --desde C --hasta D             norma del gradiente de los pesos MLP por capa, para esos tokens
  apagar N --desde C --hasta D --capa L        cambio en la pérdida de esos tokens al apagar el MLP de la capa L
  lente N --pos C                              top 5 de tokens que predice cada capa en esa posición
  generar N --max-tokens T [--temperatura X] [--apagar-capa L]   respuesta nueva (T hasta 2048)
Para terminar (una sola vez):
  elegir --capas a,b,c,d --razones "texto"     las 4 capas (0 a 23) y tus razones"""


class Aviso(Exception):
    pass


def opcion(a, nombre, tipo=int, defecto=None):
    if nombre in a:
        i = a.index(nombre)
        if i + 1 >= len(a):
            raise Aviso(f"falta el valor de {nombre}")
        try:
            return tipo(a[i + 1])
        except ValueError:
            raise Aviso(f"valor no válido en {nombre}")
    if defecto is None:
        raise Aviso(f"falta {nombre}")
    return defecto


def datos():
    with open(f"{BASE}/datos/respuestas.jsonl", encoding="utf-8") as f:
        return {d["n"]: d for d in map(json.loads, f)}


def estado():
    os.makedirs(ESTADO, exist_ok=True)
    p = f"{ESTADO}/saldo.json"
    return json.load(open(p)) if os.path.exists(p) else dict(usadas=0, terminado=False)


def guardar(e):
    json.dump(e, open(f"{ESTADO}/saldo.json", "w"))


def buscar(d, a):
    try:
        n = int(a[1])
    except (IndexError, ValueError):
        raise Aviso("falta el número de problema")
    if n not in d:
        raise Aviso(f"el problema va de 1 a {len(d)}")
    return d[n]


def cargar():
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(MODELO)
    disp = "cpu" if CPU else "cuda"
    m = AutoModelForCausalLM.from_pretrained(MODELO, dtype=torch.float32 if CPU else torch.bfloat16).to(disp).eval()
    m.config.use_cache = False
    return torch, tok, m, disp


def prompt_de(tok, x):
    return tok.apply_chat_template([{"role": "user", "content": x["problema"] + "\n" + INSTRUCCION}], tokenize=False,
                                   add_generation_prompt=True, enable_thinking=True)


def tokens_ventana(tok, x, desde, hasta):
    if not 0 <= desde < hasta or hasta - desde > VENTANA_MAX:
        raise Aviso(f"ventana no válida (máx. {VENTANA_MAX} caracteres)")
    if desde >= len(x["texto"]):
        raise Aviso(f"esa respuesta tiene {len(x['texto'])} caracteres")
    p = tok(prompt_de(tok, x), add_special_tokens=False)["input_ids"]
    t = tok(x["texto"][:hasta], add_special_tokens=False, return_offsets_mapping=True)
    ini = next((i for i, o in enumerate(t["offset_mapping"]) if o[0] >= desde), len(t["input_ids"]) - 1)
    ids = p + t["input_ids"]
    if len(ids) > CONTEXTO_MAX:
        recorte = len(ids) - CONTEXTO_MAX
        return ids[recorte:], max(1, len(p) + ini - recorte)
    return ids, max(1, len(p) + ini)


def perdida(torch, m, ids, ini, disp):
    x = torch.tensor([ids], device=disp)
    h = m.model(input_ids=x).last_hidden_state[0, ini - 1:-1]
    return torch.nn.functional.cross_entropy(m.lm_head(h).float(), x[0, ini:])


def activaciones(a, x):
    torch, tok, m, disp = cargar()
    ids, ini = tokens_ventana(tok, x, opcion(a, "--desde"), opcion(a, "--hasta"))
    salidas = {}
    ganchos = [c.mlp.register_forward_hook(lambda _m, _i, o, k=k: salidas.__setitem__(k, o[0, ini:].float().norm(dim=-1).mean().item()))
               for k, c in enumerate(m.model.layers)]
    with torch.no_grad():
        hs = m.model(input_ids=torch.tensor([ids], device=disp), output_hidden_states=True).hidden_states
    for g in ganchos:
        g.remove()
    print("capa  norma_corriente  norma_salida_mlp")
    for k in range(CAPAS):
        print(f"{k:4d}  {hs[k + 1][0, ini:].float().norm(dim=-1).mean().item():15.2f}  {salidas[k]:16.2f}")


def gradientes(a, x):
    torch, tok, m, disp = cargar()
    ids, ini = tokens_ventana(tok, x, opcion(a, "--desde"), opcion(a, "--hasta"))
    for q in m.parameters():
        q.requires_grad_(False)
    for c in m.model.layers:
        for q in c.mlp.parameters():
            q.requires_grad_(True)
    if not CPU:
        m.gradient_checkpointing_enable(gradient_checkpointing_kwargs=dict(use_reentrant=False))
        m.train()
    p = perdida(torch, m, ids, ini, disp)
    p.backward()
    print(f"pérdida media {p.item():.4f}\ncapa  norma_gradiente_mlp")
    for k, c in enumerate(m.model.layers):
        print(f"{k:4d}  {sum(q.grad.float().pow(2).sum().item() for q in c.mlp.parameters()) ** .5:.4f}")


def apagar_mlp(capa):
    return lambda _m, _i, o: o * 0


def apagar(a, x):
    torch, tok, m, disp = cargar()
    capa = opcion(a, "--capa")
    if not 0 <= capa < CAPAS:
        raise Aviso("la capa va de 0 a 23")
    ids, ini = tokens_ventana(tok, x, opcion(a, "--desde"), opcion(a, "--hasta"))
    with torch.no_grad():
        b = perdida(torch, m, ids, ini, disp).item()
        g = m.model.layers[capa].mlp.register_forward_hook(apagar_mlp(capa))
        c = perdida(torch, m, ids, ini, disp).item()
        g.remove()
    print(f"pérdida normal {b:.4f} | con el MLP de la capa {capa} apagado {c:.4f} | cambio {c - b:+.4f}")


def lente(a, x):
    torch, tok, m, disp = cargar()
    pos = opcion(a, "--pos")
    ids, ini = tokens_ventana(tok, x, max(0, pos - 1), pos + 1)
    with torch.no_grad():
        hs = m.model(input_ids=torch.tensor([ids], device=disp), output_hidden_states=True).hidden_states
        print("capa  top 5")
        for k in range(CAPAS):
            h = hs[k + 1][0, -1]
            top = m.lm_head(m.model.norm(h) if k < CAPAS - 1 else h).float().topk(5).indices.tolist()
            print(f"{k:4d}  " + " | ".join(repr(tok.decode([t])) for t in top))


def generar(a, x):
    torch, tok, m, disp = cargar()
    t = opcion(a, "--max-tokens")
    temp = opcion(a, "--temperatura", float, 0.6)
    capa = opcion(a, "--apagar-capa", int, -1)
    if not 1 <= t <= 2048 or not 0.1 <= temp <= 1.5 or not -1 <= capa < CAPAS:
        raise Aviso("valores fuera de rango")
    torch.manual_seed(0)
    g = m.model.layers[capa].mlp.register_forward_hook(apagar_mlp(capa)) if capa >= 0 else None
    m.config.use_cache = True
    ids = tok(prompt_de(tok, x), add_special_tokens=False, return_tensors="pt").to(disp)
    with torch.no_grad():
        o = m.generate(**ids, max_new_tokens=t, do_sample=True, temperature=temp, top_p=0.95, top_k=20)
    if g:
        g.remove()
    nuevos = o[0, ids["input_ids"].shape[1]:]
    texto = tok.decode(nuevos, skip_special_tokens=True)
    print(f"tokens {len(nuevos)} | terminó {'sí' if int(nuevos[-1]) == tok.eos_token_id or len(nuevos) < t else 'no'}")
    print(texto if len(texto) <= 3000 else texto[:1200] + "\n[...]\n" + texto[-1800:])


def elegir(a, e):
    try:
        capas = sorted(int(c) for c in opcion(a, "--capas", str).split(","))
    except ValueError:
        raise Aviso("capas no válidas")
    if len(set(capas)) != 4 or not all(0 <= c < CAPAS for c in capas):
        raise Aviso("elige exactamente 4 capas distintas, de 0 a 23")
    razones = " ".join(a[a.index("--razones") + 1:]) if "--razones" in a else ""
    if len(razones) < 20:
        raise Aviso("faltan las razones")
    os.makedirs(f"{BASE}/../salida", exist_ok=True)
    json.dump(dict(capas=capas, razones=razones, consultas_usadas=e["usadas"], fecha=time.strftime("%F %T")),
              open(f"{BASE}/../salida/capas.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    e["terminado"] = True
    guardar(e)
    print("elección guardada; ya terminaste")


PAGADAS = dict(activaciones=activaciones, gradientes=gradientes, apagar=apagar, lente=lente, generar=generar)


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
    elif orden == "modelo":
        print("Modelo de lenguaje pequeño, 24 capas. Cada capa tiene un MLP (gate, up, down).\n"
              "Evaluación: respuestas con razonamiento, temperatura 0.6, top_p 0.95, top_k 20, hasta 32,768 tokens.")
    elif orden == "saldo":
        print(f"usadas {e['usadas']} de {PRESUPUESTO}")
    elif orden == "resumen":
        d = datos()
        print(f"nota: {sum(x['correcto'] for x in d.values())} de {len(d)} correctas\nN  nivel  correcta  tokens  caracteres")
        for n, x in sorted(d.items()):
            print(f"{n:2d}  {x['nivel']}  {'sí' if x['correcto'] else 'no'}  {x['tokens']}  {len(x['texto'])}")
    elif orden == "problema":
        x = buscar(datos(), a)
        print(x["problema"], "\nRespuesta oficial:", x["respuesta_oficial"])
    elif orden == "ver":
        x = buscar(datos(), a)
        c, f = opcion(a, "--desde"), opcion(a, "--hasta")
        if not 0 <= c < f or f - c > 3000:
            raise Aviso("máximo 3000 caracteres")
        print(f"[{len(x['texto'])} caracteres en total]\n" + x["texto"][c:f])
    elif orden in PAGADAS:
        if e["usadas"] >= PRESUPUESTO:
            raise Aviso("no te quedan consultas")
        x = buscar(datos(), a)
        PAGADAS[orden](a, x)
        e["usadas"] += 1
        guardar(e)
        print(f"[consultas usadas: {e['usadas']} de {PRESUPUESTO}]")
    elif orden == "elegir":
        elegir(a, e)
    else:
        raise Aviso("orden desconocida; usa ayuda")


if __name__ == "__main__":
    try:
        main()
    except Aviso as x:
        print("aviso:", x)
    except Exception as x:
        print("error en la consulta:", type(x).__name__, "(no se gastó la consulta)")
