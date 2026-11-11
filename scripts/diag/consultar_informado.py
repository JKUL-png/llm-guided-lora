"""Herramienta de consulta (sesión informada). Uso: python herramientas/consultar.py ayuda"""
import base64
import json
import re
import subprocess
import sys

MOTOR = "<carpeta-aislada>/motor/motor.py"
PYTHON = "~/venv-lora/bin/python"
SEGURO = re.compile(r"^[^\x00-\x1f`$\\]*$")


def main():
    args = sys.argv[1:] or ["ayuda"]
    for a in args:
        malos = sorted({c for c in a if not SEGURO.match(c)})
        if malos or len(a) > 6000:
            print("error: argumento no válido: " + ("caracteres no permitidos " + " ".join(repr(c) for c in malos) if malos
                                                     else f"demasiado largo ({len(a)} caracteres; máximo 6000)"))
            return
    try:
        r = subprocess.run(["wsl.exe", "-d", "Ubuntu-24.04", "--", PYTHON, MOTOR, "--b64",
                            base64.b64encode(json.dumps(args).encode("utf-8")).decode("ascii")],
                           capture_output=True, timeout=3300, encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        print("error: la consulta tardó demasiado")
        return
    sys.stdout.reconfigure(encoding="utf-8")
    print(r.stdout[-12000:] if r.stdout else "error: la consulta no devolvió nada")


if __name__ == "__main__":
    main()
