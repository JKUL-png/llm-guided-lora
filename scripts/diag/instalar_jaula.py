"""Copia el kit a <carpeta-aislada>. No toca nada del proyecto y no sobrescribe la carpeta de datos.
Uso: python instalar_jaula.py"""
import os, shutil
SRC = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.join(SRC, "..", "..", "..")
D = r"<carpeta-aislada>"
for c in ("herramientas", "motor", "motor/datos", "control", "registro", "salida"):
    os.makedirs(os.path.join(D, c), exist_ok=True)
shutil.copy(f"{SRC}/consultar.py", f"{D}/herramientas/consultar.py")
shutil.copy(f"{SRC}/motor.py", f"{D}/motor/motor.py")
for f in ("gancho.py", "ajustes.json", "prompt.txt"):
    shutil.copy(f"{SRC}/{f}", f"{D}/control/{f}")
if not os.path.exists(f"{D}/control/claude.exe"):
    shutil.copy(os.path.join(RAIZ, "claude.exe"), f"{D}/control/claude.exe")
print("listo:", sorted(os.listdir(D)))
