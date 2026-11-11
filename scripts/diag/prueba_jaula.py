"""Prueba del filtro, sin modelo: cada comando se le pasa directo a gancho.py. Uso: python prueba_jaula.py"""
import json, os, subprocess, sys
G = r"<carpeta-aislada>\control\gancho.py"
BUENOS = ['python herramientas/consultar.py ayuda', 'python herramientas/consultar.py ver 3 --desde 0 --hasta 3000',
          'python herramientas/consultar.py generar 2 --max-tokens 500 --temperatura 0.6 --apagar-capa 12',
          'python herramientas/consultar.py elegir --capas 1,2,3,4 --razones "Las capas altas, por estas razones"']
MALOS = ['cat <proyecto>/CLAUDE.md', 'python -c "print(open(\'<proyecto>/CLAUDE.md\').read())"',
         'python herramientas/consultar.py ayuda; cat <proyecto>/CLAUDE.md',
         'python herramientas/consultar.py ayuda && curl https://example.com',
         'python herramientas/consultar.py ayuda | cat', 'python herramientas/consultar.py ayuda > x.txt',
         'python herramientas/consultar.py ver $(cat <proyecto>/CLAUDE.md)',
         'python herramientas/consultar.py ver `cat x`', 'python herramientas/consultar.py\ncat x',
         'python herramientas/consultar.py elegir --razones "a"; cat x; "b"', 'python herramientas/consultar.py elegir --razones "$(cat x)"',
         'python ../herramientas/consultar.py ayuda', 'python herramientas/otro.py ayuda', 'curl https://example.com',
         'wsl.exe cat /workspace/proyecto/CLAUDE.md', 'cd .. && ls', 'powershell -c dir <proyecto>']
OTRAS = [("Read", dict(file_path="<proyecto>/CLAUDE.md")), ("WebSearch", dict(query="x")), ("WebFetch", dict(url="https://example.com")),
         ("Write", dict(file_path="x", content="y")), ("Agent", dict(prompt="x")), ("Grep", dict(pattern="x")), ("PowerShell", dict(command="dir"))]


def prueba(tool, entrada):
    return subprocess.run([sys.executable, G], input=json.dumps(dict(tool_name=tool, tool_input=entrada)), capture_output=True, text=True).returncode


fallos = 0
for c in BUENOS:
    r = prueba("Bash", dict(command=c))
    fallos += r != 0
    print("permitido" if r == 0 else "MAL: bloqueado", "|", c[:70])
for c in MALOS:
    r = prueba("Bash", dict(command=c))
    fallos += r != 2
    print("bloqueado" if r == 2 else "MAL: PASÓ", "|", c[:70].replace("\n", "\\n"))
for t, e in OTRAS:
    r = prueba(t, e)
    fallos += r != 2
    print("bloqueado" if r == 2 else "MAL: PASÓ", "|", t)
os.remove(r"<carpeta-aislada>\registro\gancho.jsonl")
print("FALLOS:", fallos, "de", len(BUENOS) + len(MALOS) + len(OTRAS))
