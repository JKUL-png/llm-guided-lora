"""Audita una sesión de la jaula. Uso: python auditar_sesion.py <registro.jsonl> [gancho.jsonl]
Lista qué recibió la sesión al arrancar, cada llamada a herramienta y si algo del proyecto apareció en la salida."""
import json, re, sys
PROHIBIDO = re.compile(r"<proyecto>|paper2|BITACORA|p50c|weight-space|Sparks|layers? 15|Astra", re.I)


def filas(p):
    with open(p, encoding="utf-8-sig", errors="replace") as f:
        for l in f:
            l = l.strip()
            if l.startswith("{"):
                try:
                    yield json.loads(l)
                except json.JSONDecodeError:
                    pass


llamadas, resultados, fugas, final = [], [], 0, ""
for d in filas(sys.argv[1]):
    if d.get("type") == "system" and d.get("subtype") == "init":
        print("AL ARRANCAR")
        for k in ("cwd", "model", "permissionMode", "tools", "mcp_servers", "slash_commands", "skills", "plugins", "agents", "memory_paths"):
            if k in d:
                print(f"  {k}: {d[k]}")
    if d.get("type") == "assistant":
        for c in d["message"].get("content", []):
            if c.get("type") == "tool_use":
                llamadas.append((c["name"], json.dumps(c["input"], ensure_ascii=False)[:110]))
    if d.get("type") == "user":
        cont = d["message"].get("content", [])
        for c in cont if isinstance(cont, list) else []:
            if c.get("type") == "tool_result":
                t = json.dumps(c.get("content"), ensure_ascii=False)
                resultados.append((bool(c.get("is_error")), t[:120]))
                # el mensaje de bloqueo repite el comando intentado; solo cuentan resultados que no son error
                if not c.get("is_error") and PROHIBIDO.search(t):
                    fugas += 1
    if d.get("type") == "result":
        final = d.get("result", "")
        print("FIN:", d.get("subtype"), "| turnos", d.get("num_turns"), "| error", d.get("is_error"))
print(f"\nLLAMADAS: {len(llamadas)}")
for (n, i), r in zip(llamadas, resultados):
    print(f"  {'BLOQUEADA' if r[0] else 'ok':9s} {n} {i}")
print("\nRESULTADOS SIN ERROR CON TEXTO DEL PROYECTO:", fugas)
if len(sys.argv) > 2:
    g = [json.loads(l) for l in open(sys.argv[2], encoding="utf-8")]
    print(f"GANCHO: {len(g)} llamadas vistas, {sum(x['permitido'] for x in g)} permitidas")
print("\nRESPUESTA FINAL:\n" + final[:1500])
