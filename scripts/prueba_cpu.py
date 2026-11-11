"""Prueba de la tubería SIN GPU (CUDA_VISIBLE_DEVICES vacío), con el modelo real y texto inventado.
Comprueba: número de parámetros en los dos tipos de brazo, módulos tocados, entrenamiento, fusión e igualdad
entre el modelo fusionado y el adaptador. Todo va a una carpeta temporal. Uso: python prueba_cpu.py <carpeta_temporal>"""
import json, os, subprocess, sys
os.environ["CUDA_VISIBLE_DEVICES"] = ""
sys.modules["fla"] = None   # sus nucleos solo corren en GPU
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from comun_lora import *
import torch
from importlib.metadata import version
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
from safetensors.torch import load_file

T = sys.argv[1]
os.makedirs(T, exist_ok=True)
assert not torch.cuda.is_available(), "La GPU debería estar oculta"
print({p: version(p) for p in ("torch", "transformers", "peft", "flash-linear-attention")})

from entrenar_lora import cargar_modelo
for nombre, capas in (("todas", list(range(CAPAS_TOTAL))), ("placebo s0", capas_placebo(0))):
    m = cargar_modelo(MODELO_BASE, capas, rango_para(capas), "cpu", gc=False)
    n = sum(q.numel() for q in m.parameters() if q.requires_grad)
    mods = sorted({k.split(".lora_A")[0] for k, _ in m.named_parameters() if ".lora_A" in k})
    print(nombre, type(m.get_base_model()).__name__, "| parámetros", n, "| módulos", len(mods), "| ej.", mods[0])
    assert n == PARAMS_OBJETIVO and len(mods) == 3 * len(capas)
    assert all(".mlp." in x for x in mods)
    del m

tok = AutoTokenizer.from_pretrained(MODELO_BASE)
prompt = tok.apply_chat_template([{"role": "user", "content": "What is 2 + 2?"}], tokenize=False,
                                 add_generation_prompt=True, enable_thinking=True)
ej = [dict(id=f"inventado/{i}", tipo="forzada", prompt=prompt, pensamiento="Add the numbers. " * (3 + i),
           salida=f"{CIERRE} I will stop here.\n</think>\n\nThe answer is \\boxed{{4}}<|im_end|>\n", tokens=0) for i in range(4)]
datos = f"{T}/datos.jsonl"
with open(datos, "w", encoding="utf-8") as f:
    for x in ej:
        f.write(json.dumps(x) + "\n")

capas = capas_placebo(0)
ad, fu = f"{T}/adaptador", f"{T}/fusionado"
subprocess.run([sys.executable, f"{AQUI}/entrenar_lora.py", "--datos", datos, "--capas", ",".join(map(str, capas)),
                "--semilla", "0", "--salida", ad, "--cpu", "--acumular", "2"], check=True)
e = json.load(open(f"{ad}/entrenamiento.json"))
print("pérdida", e["registro"], "| ejemplos", e["ejemplos"])
assert e["perdida_final"] < e["perdida_inicial"], "La pérdida no bajó"
subprocess.run([sys.executable, f"{AQUI}/fusionar_lora.py", ad, fu], check=True)

base, fus = load_file(f"{MODELO_BASE}/{ARCHIVO_PESOS}"), load_file(f"{fu}/{ARCHIVO_PESOS}")
assert set(base) == set(fus)
distintos = sorted(k for k in base if not torch.equal(base[k], fus[k]))
print("tensores cambiados:", len(distintos), "| ej.", distintos[0])
esperados = {f"model.language_model.layers.{c}.mlp.{m}.weight" for c in capas for m in MODULOS}
assert set(distintos) <= esperados, "La fusión tocó tensores que no debía"

ids = torch.tensor([tok(prompt + ej[0]["pensamiento"], add_special_tokens=False)["input_ids"]])
with torch.no_grad():
    b = AutoModelForCausalLM.from_pretrained(MODELO_BASE, dtype=torch.float32)
    l0 = b(ids).logits[0, -1]
    l1 = PeftModel.from_pretrained(b, ad)(ids).logits[0, -1]
    l2 = AutoModelForCausalLM.from_pretrained(fu, dtype=torch.float32)(ids).logits[0, -1]
print("cambio del adaptador", round((l1 - l0).abs().max().item(), 4), "| fusionado vs adaptador", round((l2 - l1).abs().max().item(), 4))
print("mismo token predicho:", int(l1.argmax()) == int(l2.argmax()))
print("PRUEBA OK")
