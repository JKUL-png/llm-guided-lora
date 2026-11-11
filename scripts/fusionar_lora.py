"""Fusiona un adaptador LoRA al modelo para evaluarlo en vLLM. Solo CPU. Corre en ~/venv-lora.
W' = redondeo_bf16(W + (alfa/rango) * B @ A), calculado en float32. Los demás tensores se copian tal cual.
Uso: python fusionar_lora.py <adaptador> <carpeta_salida> [modelo_base]
Escribe <carpeta_salida>/fusion.csv: por tensor, ‖ΔW‖/‖W‖ antes y después del redondeo, y el % de pesos que cambió.
Si el redondeo a bf16 borra más del 50% del parche en algún tensor, avisa con ALERTA. No sobrescribe."""
import csv, json, os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comun_lora import ARCHIVO_PESOS, MODELO_BASE, nombre_en_archivo


def main():
    import torch
    from safetensors.torch import load_file, save_file
    adaptador, salida = sys.argv[1], sys.argv[2]
    base_dir = sys.argv[3] if len(sys.argv) > 3 else MODELO_BASE
    destino = f"{salida}/{ARCHIVO_PESOS}"
    if os.path.exists(destino):
        print("Ya existe; no sobrescribo:", destino); sys.exit(1)
    cfg = json.load(open(f"{adaptador}/adapter_config.json"))
    escala = cfg["lora_alpha"] / cfg["r"]
    lora = load_file(f"{adaptador}/adapter_model.safetensors")
    pesos = load_file(f"{base_dir}/{ARCHIVO_PESOS}")

    filas, alerta = [], False
    claves_a = [k for k in lora if ".lora_A." in k]
    assert claves_a, "El adaptador no tiene tensores lora_A"
    for ka in sorted(claves_a):
        kb = ka.replace(".lora_A.", ".lora_B.")
        nombre = nombre_en_archivo(ka)
        if nombre not in pesos:
            raise SystemExit(f"No encuentro {nombre} en el modelo base")
        W = pesos[nombre].float()
        delta = escala * (lora[kb].float() @ lora[ka].float())
        assert delta.shape == W.shape, (nombre, delta.shape, W.shape)
        nuevo = (W + delta).to(torch.bfloat16)
        real = nuevo.float() - W
        nw = W.norm().item()
        antes, despues = delta.norm().item() / nw, real.norm().item() / nw
        cambiados = 100 * (real != 0).float().mean().item()
        # cuánto del parche sobrevive: proyección del cambio real sobre el parche pedido
        sobrevive = (real * delta).sum().item() / max(delta.pow(2).sum().item(), 1e-30)
        if sobrevive < 0.5:
            alerta = True
        filas.append(dict(tensor=nombre, dw_w_antes=f"{antes:.6g}", dw_w_despues=f"{despues:.6g}",
                          pct_pesos_cambiados=round(cambiados, 2), fraccion_parche_conservada=round(sobrevive, 4)))
        pesos[nombre] = nuevo

    os.makedirs(salida, exist_ok=True)
    for f in os.listdir(base_dir):
        if f != ARCHIVO_PESOS and os.path.isfile(f"{base_dir}/{f}"):
            shutil.copyfile(f"{base_dir}/{f}", f"{salida}/{f}")
    save_file(pesos, destino, metadata={"format": "pt"})
    with open(f"{salida}/fusion.csv", "w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=list(filas[0])); w.writeheader(); w.writerows(filas)
    media = sum(float(x["fraccion_parche_conservada"]) for x in filas) / len(filas)
    print(f"fusionados {len(filas)} tensores; fracción del parche conservada, media {media:.3f}")
    if alerta:
        print("ALERTA: el redondeo a bf16 borró más de la mitad del parche en algún tensor; ver fusion.csv")


if __name__ == "__main__":
    main()
