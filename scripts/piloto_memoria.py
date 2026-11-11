"""Piloto de memoria y velocidad (GPU, ~/venv-lora). Usa tokens al azar: no toca ningún problema.
Prueba cada combinación de capas, modo de pérdida y largo con 3 pasos, y guarda VRAM pico y tokens por segundo.
Cada combinación corre en un proceso aparte, para que quedarse sin memoria no arruine las siguientes.
Uso: python piloto_memoria.py <salida.csv>   (no sobrescribe)"""
import csv, json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comun_lora import *

LARGOS = (2048, 4096, 8192, 12288, 16384, 22000)
BRAZOS = (("todas_r8", list(range(CAPAS_TOTAL))), ("4capas_r48", capas_placebo(0)))
SALIDA_TOKENS = 512     # en modo "salida", la pérdida cuenta en los últimos 512 tokens


def una(capas, largo, modo):
    import torch, time
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from entrenar_lora import cargar_modelo, paso_perdida
    m = cargar_modelo(MODELO_BASE, capas, rango_para(capas), "cuda")
    params = [q for q in m.parameters() if q.requires_grad]
    opt = torch.optim.AdamW(params, lr=LR)
    m.train(); torch.cuda.reset_peak_memory_stats()
    g = torch.Generator().manual_seed(0)
    desde = largo - SALIDA_TOKENS if modo == "salida" else 1
    tiempos = []
    for _ in range(3):
        ids = torch.randint(1000, 200000, (largo,), generator=g).tolist()
        torch.cuda.synchronize(); t = time.time()
        paso_perdida(m, ids, desde, "cuda").backward()
        opt.step(); opt.zero_grad(set_to_none=True)
        torch.cuda.synchronize(); tiempos.append(time.time() - t)
    # el primer paso compila núcleos: no cuenta para la velocidad
    print("RES" + json.dumps(dict(vram_pico_gb=round(torch.cuda.max_memory_allocated() / 2**30, 2),
                                  tok_por_s=round(largo / (sum(tiempos[1:]) / 2), 1))))


def main():
    if sys.argv[1] == "--una":
        una(json.loads(sys.argv[2]), int(sys.argv[3]), sys.argv[4]); return
    salida = sys.argv[1]
    if os.path.exists(salida):
        print("Ya existe; no sobrescribo:", salida); sys.exit(1)
    with open(salida, "w", newline="", encoding="utf-8") as h:
        w = csv.writer(h); w.writerow(["brazo", "perdida", "largo", "resultado", "vram_pico_gb", "tok_por_s"])
        for nombre, capas in BRAZOS:
            for modo in ("salida", "todo"):
                for largo in LARGOS:
                    r = subprocess.run([sys.executable, __file__, "--una", json.dumps(capas), str(largo), modo],
                                       capture_output=True, text=True)
                    res = [l for l in r.stdout.splitlines() if l.startswith("RES")]
                    if res:
                        d = json.loads(res[0][3:]); fila = [nombre, modo, largo, "ok", d["vram_pico_gb"], d["tok_por_s"]]
                    else:
                        memoria = "out of memory" in r.stderr.lower()
                        fila = [nombre, modo, largo, "sin_memoria" if memoria else "error", "", ""]
                        if not memoria:
                            print(r.stderr[-1500:], flush=True)
                    w.writerow(fila); h.flush(); print(fila, flush=True)
                    if fila[3] != "ok":
                        break   # si un largo no cabe, los mayores tampoco


if __name__ == "__main__":
    main()
