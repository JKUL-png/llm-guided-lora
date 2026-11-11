"""Prueba del barrido en CPU (sin GPU). Uso: python prueba_barrido.py
1) Cuenta los fragmentos de las 40 respuestas de diagnóstico y revisa que estén dentro de la respuesta.
2) Comprueba que el atajo con caché (contexto una vez + dos continuaciones) da lo mismo que pasar
   la secuencia completa, con el modelo normal y con un MLP apagado."""
import os, sys
os.environ["CUDA_VISIBLE_DEVICES"] = ""; sys.modules["fla"] = None
sys.argv = [sys.argv[0], "/dev/null", "--cpu"]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import barrido as BR
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

tok = AutoTokenizer.from_pretrained(BR.MODELO)
fr, sin = BR.fragmentos(tok)
tipos = {t: sum(f["tipo"] == t for f in fr) for t in ("principal", "bucle", "cierre_natural")}
print("fragmentos", len(fr), tipos, "| sin bucle:", sin)
assert all(0 < f["k"] <= len(f["ids"]) for f in fr)
assert all(f["k"] + BR.CONT <= len(f["ids"]) for f in fr if f["tipo"] != "cierre_natural")
for f in fr[:3]:
    print(f["tipo"], "problema", f["problema"], "token", f["k"], "| antes del punto:", repr(tok.decode(f["ids"][f["k"] - 12:f["k"]])))

m = AutoModelForCausalLM.from_pretrained(BR.MODELO, dtype=torch.float32).eval()
think = tok.convert_tokens_to_ids("</think>")
nl, frase = tok("\n\n", add_special_tokens=False)["input_ids"], tok(BR.FRASE, add_special_tokens=False)["input_ids"]
f = fr[0]
ctx = f["ids"][f["k"] - 200:f["k"]]
real = f["ids"][f["k"]:f["k"] + BR.CONT]


def lp(lg, obj):
    return torch.log_softmax(lg.float(), -1).gather(-1, torch.tensor(obj)[:, None]).sum().item()


@torch.no_grad()
def completo():
    a = m(input_ids=torch.tensor([ctx + real])).logits[0]
    b = m(input_ids=torch.tensor([ctx + nl + frase])).logits[0]
    n = len(ctx)
    return lp(a[n - 1:n], [think]), lp(a[n - 1:n - 1 + len(real)], real), lp(b[n + len(nl) - 1:-1], frase)


@torch.no_grad()
def con_cache():
    import copy
    o = m(input_ids=torch.tensor([ctx]), use_cache=True, logits_to_keep=1)
    ult = o.logits[0, -1]
    c2 = copy.deepcopy(o.past_key_values)
    o2 = m(input_ids=torch.tensor([real]), past_key_values=o.past_key_values, use_cache=True)
    o3 = m(input_ids=torch.tensor([nl + frase]), past_key_values=c2, use_cache=True)
    return lp(ult[None], [think]), lp(torch.cat([ult[None], o2.logits[0, :-1]]), real), lp(o3.logits[0, len(nl) - 1:-1], frase)


for nombre, capa in (("normal", None), ("capa 10 en cero", 10)):
    g = m.model.layers[capa].mlp.register_forward_hook(lambda _m, _x, y: y * 0) if capa is not None else None
    a, b = completo(), con_cache()
    if g: g.remove()
    dif = max(abs(x - y) for x, y in zip(a, b))
    print(nombre, "| completo", [round(x, 4) for x in a], "| caché", [round(x, 4) for x in b], "| dif. máx.", round(dif, 5))
    assert dif < 1e-2, "el atajo con caché no coincide"
print("PRUEBA OK")
