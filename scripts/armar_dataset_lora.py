"""Convierte las corridas "cortar y cerrar" en el dataset de entrenamiento. Sin GPU. Corre en ~/venv-lora.
Se conservan SOLO respuestas correctas. Dos tipos:
  forzada: el modelo cayó en bucle, se recortó y se cerró. La parte de salida empieza en la frase de cierre.
  natural: terminó solo. La parte de salida empieza en </think>.
Uso: python armar_dataset_lora.py <salida.jsonl> <max_tokens> <prefijo_corrida_B.csv> [más corridas...]
Ej.: ... datos/lora_bucles.jsonl 16384 resultados/p2_datos_b00_B_s0.csv
Escribe también <salida>.resumen.json con cuántos entraron y cuántos se descartaron por largo. No sobrescribe."""
import csv, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comun_lora import CIERRE, MODELO_BASE

sys.path.insert(0, "/workspace/proyecto/scripts")
os.environ.setdefault("PROYECTO_RAIZ", "/workspace/proyecto")
from comun_math import construir_prompt

PROHIBIDO_PREFIJO = "test/"   # los problemas de evaluación usan ids test/...; aquí no puede entrar ninguno


def problemas(rutas):
    d = {}
    for r in rutas:
        for l in open(r, encoding="utf-8"):
            x = json.loads(l); d[x["id"]] = x
    return d


def main():
    from transformers import AutoTokenizer
    salida, max_tokens, corridas = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
    if os.path.exists(salida):
        print("Ya existe; no sobrescribo:", salida); sys.exit(1)
    base = os.path.dirname(salida)
    probs = problemas([f"{base}/math_train_1200.jsonl"])
    tok = AutoTokenizer.from_pretrained(MODELO_BASE)
    filas, largo, sin_marca = [], 0, 0
    vistos = 0
    for c in corridas:
        meta = {r["id"]: r for r in csv.DictReader(open(c, encoding="utf-8"))}
        for l in open(c + ".jsonl", encoding="utf-8"):
            d = json.loads(l); r = meta[d["id"]]; vistos += 1
            if d["id"].startswith(PROHIBIDO_PREFIJO):
                raise SystemExit(f"Problema de evaluación en los datos: {d['id']}")
            if r["correcto"] != "1":
                continue
            t = d["texto"]
            forzada = r["forzado"] == "1"
            inicio = t.find(CIERRE) if forzada else t.find("</think>")
            if inicio < 0 or t.count("</think>") != 1:
                sin_marca += 1; continue
            prompt = tok.apply_chat_template([{"role": "user", "content": construir_prompt(probs[d["id"]]["problem"])}],
                                             tokenize=False, add_generation_prompt=True, enable_thinking=True)
            antes, despues = t[:inicio], t[inicio:] + "<|im_end|>\n"
            n = sum(len(tok(x, add_special_tokens=False)["input_ids"]) for x in (prompt, antes, despues))
            if n > max_tokens:
                largo += 1; continue
            filas.append(dict(id=d["id"], tipo="forzada" if forzada else "natural", prompt=prompt,
                              pensamiento=antes, salida=despues, tokens=n))
    with open(salida, "w", encoding="utf-8") as f:
        for x in filas:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    resumen = dict(respuestas_vistas=vistos, ejemplos=len(filas), forzadas=sum(x["tipo"] == "forzada" for x in filas),
                   naturales=sum(x["tipo"] == "natural" for x in filas), descartadas_por_largo=largo,
                   descartadas_sin_marca=sin_marca, max_tokens=max_tokens,
                   tokens_totales=sum(x["tokens"] for x in filas))
    json.dump(resumen, open(salida + ".resumen.json", "w"), indent=1)
    print(resumen)


if __name__ == "__main__":
    main()
