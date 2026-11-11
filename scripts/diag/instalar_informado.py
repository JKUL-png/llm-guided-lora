"""Instala en <carpeta-aislada> la versión informada de la jaula para una sesión. No toca el proyecto.
Uso: python instalar_informado.py <sesion 1-4, o 0 para pruebas> <semilla>
- Revisa antes que el contexto esté limpio (revisar_contexto.py).
- Archiva en registro/archivo_<fecha>/ el registro y la salida anteriores (ya copiados en paper2/resultados/diag).
- Exige que el saldo de esa sesión (~/qm_estado/informado_<sesion>) no exista: cada sesión empieza de cero.
- Conserva motor/datos (las 40 respuestas guardadas)."""
import json, os, shutil, subprocess, sys, time
SRC = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.join(SRC, "..", "..", "..")
D = r"<carpeta-aislada>"
sesion, semilla = int(sys.argv[1]), int(sys.argv[2])
assert 0 <= sesion <= 4   # 0 = prueba

r = subprocess.run([sys.executable, f"{SRC}/revisar_contexto.py"], capture_output=True, text=True, encoding="utf-8",
                   env=dict(os.environ, PYTHONIOENCODING="utf-8"))
assert "RESULTADO: LIMPIO" in r.stdout, "el contexto no está limpio:\n" + r.stdout
assert os.path.exists(f"{D}/motor/datos/respuestas.jsonl"), "faltan las 40 respuestas guardadas"
q = subprocess.run(["wsl.exe", "-d", "Ubuntu-24.04", "--", "test", "-e", f"~/qm_estado/informado_{sesion}"])
assert q.returncode == 1, f"ya existe el saldo de la sesión {sesion}; no se reutiliza"

viejos = [f for c in ("registro", "salida") for f in os.listdir(f"{D}/{c}") if not f.startswith("archivo_")]
if viejos:
    arch = f"{D}/registro/archivo_{time.strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(arch)
    for c in ("registro", "salida"):
        for f in os.listdir(f"{D}/{c}"):
            if not f.startswith("archivo_"):
                shutil.move(f"{D}/{c}/{f}", f"{arch}/{c}_{f}")

copias = {"consultar_informado.py": "herramientas/consultar.py", "motor.py": "motor/base.py",
          "motor_informado.py": "motor/motor.py", "generar_vllm.py": "motor/generar_vllm.py",
          "contexto_informado.md": "motor/contexto.md", "gancho_informado.py": "control/gancho.py",
          "ajustes_informado.json": "control/ajustes.json", "prompt_informado.txt": "control/prompt.txt"}
for a, b in copias.items():
    shutil.copy(f"{SRC}/{a}", f"{D}/{b}")
json.dump(dict(sesion=sesion, semilla=semilla, instalado=time.strftime("%F %T")), open(f"{D}/motor/sesion.json", "w"))
if not os.path.exists(f"{D}/control/claude.exe"):
    shutil.copy(os.path.join(RAIZ, "claude.exe"), f"{D}/control/claude.exe")
print("listo: sesión", sesion, "semilla", semilla, "|", {c: sorted(os.listdir(f"{D}/{c}")) for c in ("herramientas", "motor", "control")})
