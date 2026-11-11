"""Generación para la orden 'generar' de la sesión informada. Corre en ~/venv-vllm (WSL). Uso: python generar_vllm.py <pedido.json>
Mismo muestreo que BASE_MIT (top_p 0.95, top_k 20, presence_penalty 1.5, hasta 32,768 tokens), thinking, prompt del MIT.
Con capa >= 0 usa una copia temporal del modelo con mlp.down_proj de esa capa en cero (= la salida de su MLP da cero),
y la borra al terminar. Califica con la regla del paper 2 (paper2/scripts/calificacion.py).
Con MOTOR_SIMULAR=1 no usa vLLM: inventa muestras, para probar la contabilidad en CPU."""
import glob, json, os, shutil, sys

MODELO = os.path.expanduser("~/modelos/Qwen3.5-0.8B")
TMP = os.path.expanduser("~/qm_tmp/apagada")
INSTRUCCION = "Please reason step by step, and put your final answer within " + chr(92) + "boxed{}."
MAX_TOKENS = 32768
sys.path.insert(0, "/workspace/proyecto/paper2/scripts")


def copia_apagada(capa):
    from safetensors.torch import load_file, save_file
    shutil.rmtree(TMP, ignore_errors=True)
    os.makedirs(TMP)
    for f in os.listdir(MODELO):
        if not f.startswith(".") and not f.endswith(".safetensors"):
            shutil.copy(os.path.join(MODELO, f), TMP)
    clave, hecho = f"model.language_model.layers.{capa}.mlp.down_proj.weight", False
    for f in glob.glob(f"{MODELO}/*.safetensors"):
        w = load_file(f)
        if clave in w:
            w[clave] = w[clave] * 0; hecho = True
        save_file(w, os.path.join(TMP, os.path.basename(f)), metadata={"format": "pt"})
    assert hecho, "no encontré el tensor"
    return TMP


def main():
    p = json.load(open(sys.argv[1], encoding="utf-8"))
    probs, k = p["problemas"], p["muestras"]
    if os.environ.get("MOTOR_SIMULAR") == "1":
        out = []
        for x in probs:
            for j in range(k):
                t = f"simulada {j} del problema {x['n']}. " * 40 + ("</think>\n\nThe answer is \\boxed{4}." if j % 2 == 0 else "")
                out.append(dict(n=x["n"], texto=t, tokens=len(t) // 4, termino=j % 2 == 0, cierres=t.count("</think>"),
                                correcto=int(j % 2 == 0 and x["respuesta_oficial"] == "4")))
        json.dump(out, open(p["salida"], "w", encoding="utf-8"), ensure_ascii=False)
        return
    import calificacion as C
    from vllm import LLM, SamplingParams
    modelo = copia_apagada(p["capa"]) if p["capa"] >= 0 else MODELO
    try:
        llm = LLM(modelo, dtype="bfloat16", max_model_len=MAX_TOKENS + 1024, gpu_memory_utilization=0.80, seed=0)
        tok = llm.get_tokenizer()
        prompts = [tok.apply_chat_template([{"role": "user", "content": x["problema"] + "\n" + INSTRUCCION}], tokenize=False,
                                           add_generation_prompt=True, enable_thinking=True) for x in probs]
        sp = SamplingParams(n=k, temperature=p["temperatura"], top_p=0.95, top_k=20, presence_penalty=1.5,
                            repetition_penalty=1.0, max_tokens=MAX_TOKENS, seed=p["semilla"])
        out = []
        for x, o in zip(probs, llm.generate(prompts, sp)):
            for c in o.outputs:
                out.append(dict(n=x["n"], texto=c.text, tokens=len(c.token_ids), termino=c.finish_reason != "length",
                                cierres=C.cierres(c.text), correcto=int(C.es_correcta(c.text, x["respuesta_oficial"], True))))
        json.dump(out, open(p["salida"], "w", encoding="utf-8"), ensure_ascii=False)
    finally:
        if modelo == TMP:
            shutil.rmtree(TMP, ignore_errors=True)


if __name__ == "__main__":
    main()
