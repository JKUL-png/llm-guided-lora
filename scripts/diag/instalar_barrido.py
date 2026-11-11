"""Instala en <carpeta-aislada> la jaula "Opus + barrido" para una sesión. No toca el proyecto.
Uso: python instalar_barrido.py <sesion 1-4, o 0 para pruebas>
- Revisa que el contexto esté limpio (revisar_contexto.py) y que la tabla del barrido no nombre nada del proyecto.
- Archiva en registro/archivo_<fecha>/ el registro y la salida anteriores (ya copiados al proyecto).
- Exige que el saldo de esa sesión (~/qm_estado/barrido_<sesion>) no exista.
- Quita del motor lo de la jaula informada (generar, motor base): aquí no se mide nada."""
import json, os, re, shutil, subprocess, sys, time
SRC = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.join(SRC, "..", "..", "..")
TABLA = os.path.join(SRC, "..", "..", "resultados", "barrido", "tabla_opus.md")
D = r"<carpeta-aislada>"
sesion = int(sys.argv[1])
assert 0 <= sesion <= 4   # 0 = prueba

r = subprocess.run([sys.executable, f"{SRC}/revisar_contexto.py"], capture_output=True, text=True, encoding="utf-8",
                   env=dict(os.environ, PYTHONIOENCODING="utf-8"))
assert "RESULTADO: LIMPIO" in r.stdout, "el contexto no está limpio:\n" + r.stdout
t = open(TABLA, encoding="utf-8").read()
assert not re.search(r"<proyecto>|paper2|BITACORA|p50c|weight-space|Sparks|Astra|doubleAI|brazo|test/", t, re.I) and not re.search(r"\bMIT\b", t), "la tabla nombra algo del proyecto"
q = subprocess.run(["wsl.exe", "-d", "Ubuntu-24.04", "--", "test", "-e", f"~/qm_estado/barrido_{sesion}"])
assert q.returncode == 1, f"ya existe el saldo de la sesión {sesion}; no se reutiliza"

viejos = [f for c in ("registro", "salida") for f in os.listdir(f"{D}/{c}") if not f.startswith("archivo_")]
if viejos:
    arch = f"{D}/registro/archivo_{time.strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(arch)
    for c in ("registro", "salida"):
        for f in os.listdir(f"{D}/{c}"):
            if not f.startswith("archivo_"):
                shutil.move(f"{D}/{c}/{f}", f"{arch}/{c}_{f}")
for f in ("base.py", "generar_vllm.py"):
    if os.path.exists(f"{D}/motor/{f}"):
        os.remove(f"{D}/motor/{f}")
shutil.rmtree(f"{D}/motor/__pycache__", ignore_errors=True)
copias = {"consultar_informado.py": "herramientas/consultar.py", "motor_barrido.py": "motor/motor.py",
          "contexto_informado.md": "motor/contexto.md", "gancho_informado.py": "control/gancho.py",
          "ajustes_informado.json": "control/ajustes.json", "prompt_barrido.txt": "control/prompt.txt"}
for a, b in copias.items():
    shutil.copy(f"{SRC}/{a}", f"{D}/{b}")
shutil.copy(TABLA, f"{D}/motor/barrido.md")
json.dump(dict(sesion=sesion, brazo="barrido", instalado=time.strftime("%F %T")), open(f"{D}/motor/sesion.json", "w"))
print("listo: barrido, sesión", sesion, "|", {c: sorted(os.listdir(f"{D}/{c}")) for c in ("herramientas", "motor", "control")})
