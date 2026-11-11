"""Filtro externo: corre ANTES de cada herramienta de la sesión ciega. El modelo no puede verlo ni apagarlo.
Solo deja pasar la orden exacta de consultar.py, con argumentos simples y hasta MAX_LLAMADAS. Registra todo."""
import json, os, re, sys, time

CONTROL = os.path.dirname(os.path.abspath(__file__))
REGISTRO = os.path.join(CONTROL, "..", "registro", "gancho.jsonl")
MAX_LLAMADAS = 150
TEXTO = r'"[^"`$\\;&|<>\r\n]*"'
ORDEN = re.compile(r'^python herramientas/consultar\.py( [a-z]+)( (--[a-z-]+|-?[0-9][0-9.,]*|' + TEXTO + r'))*$')


def main():
    e = json.load(sys.stdin)
    herramienta = e.get("tool_name", "")
    comando = (e.get("tool_input") or {}).get("command", "")
    os.makedirs(os.path.dirname(REGISTRO), exist_ok=True)
    previas = sum(1 for _ in open(REGISTRO, encoding="utf-8")) if os.path.exists(REGISTRO) else 0
    ok = herramienta == "Bash" and bool(ORDEN.match(comando)) and previas < MAX_LLAMADAS
    with open(REGISTRO, "a", encoding="utf-8") as f:
        f.write(json.dumps(dict(hora=time.strftime("%F %T"), herramienta=herramienta, permitido=ok,
                                entrada=e.get("tool_input")), ensure_ascii=False) + "\n")
    if not ok:
        print("Bloqueado: solo se permite python herramientas/consultar.py", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
