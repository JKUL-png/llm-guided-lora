"""Reconstruye una sesión de la jaula paso a paso. Uso: python analizar_sesion.py <sesion.jsonl> <salida.csv>
Escribe una fila por llamada, con la orden, si gastó consulta y el texto del modelo justo antes.
Imprime la primera mención de repetición o bucles en el texto ESCRITO por el modelo."""
import csv, json, re, sys
MENCION = re.compile(r"repet|repit|bucle|loop|cicl|degener|atasc|stuck|no termina|sin terminar|nunca termina|trunc|límite de tokens|agota", re.I)
PAGADAS = ("activaciones", "gradientes", "apagar", "lente", "generar")
eventos, pend = [], {}
with open(sys.argv[1], encoding="utf-8-sig", errors="replace") as f:
    for l in f:
        l = l.strip()
        if not l.startswith("{"):
            continue
        try:
            d = json.loads(l)
        except json.JSONDecodeError:
            continue
        if d.get("type") == "assistant":
            for c in d["message"].get("content", []):
                if c.get("type") == "text":
                    eventos.append(("texto", c["text"]))
                elif c.get("type") == "thinking":
                    eventos.append(("pensamiento", c.get("thinking", "")))
                elif c.get("type") == "tool_use":
                    eventos.append(("llamada", c["input"].get("command", json.dumps(c["input"])), c["id"]))
        elif d.get("type") == "user":
            cont = d["message"].get("content", [])
            for c in cont if isinstance(cont, list) else []:
                if c.get("type") == "tool_result":
                    x = c.get("content")
                    t = x if isinstance(x, str) else " ".join(y.get("text", "") for y in x or [])
                    pend[c["tool_use_id"]] = (bool(c.get("is_error")), t)
        elif d.get("type") == "result":
            print("FIN:", d.get("subtype"), "| turnos", d.get("num_turns"), "| segundos", round(d.get("duration_ms", 0) / 1000), "| error", d.get("is_error"))

filas, n, pagadas, primera, texto_previo = [], 0, 0, None, ""
for e in eventos:
    if e[0] in ("texto", "pensamiento"):
        texto_previo += " " + e[1]
        m = MENCION.search(e[1])
        if m and primera is None:
            primera = dict(tipo=e[0], tras_llamadas=n, tras_consultas=pagadas, palabra=m.group(0),
                           cita=e[1][max(0, m.start() - 250):m.start() + 350])
    else:
        n += 1
        cmd = e[1]
        orden = (cmd.split("consultar.py")[-1].split() or ["?"])[0]
        err, res = pend.get(e[2], (None, ""))
        gasta = orden in PAGADAS and "consultas usadas" in res
        pagadas += gasta
        filas.append(dict(llamada=n, consultas_acumuladas=pagadas, orden=orden, comando=cmd[:160], bloqueada=int(bool(err)),
                          gasta=int(gasta), texto_previo=texto_previo.strip()[:300], resultado=res[:200].replace("\n", " ")))
        texto_previo = ""
with open(sys.argv[2], "w", newline="", encoding="utf-8") as h:
    w = csv.DictWriter(h, fieldnames=list(filas[0])); w.writeheader(); w.writerows(filas)
cuenta = {}
for f in filas:
    cuenta[f["orden"]] = cuenta.get(f["orden"], 0) + 1
print("llamadas", n, "| consultas pagadas", pagadas, "| bloqueadas", sum(f["bloqueada"] for f in filas), "| por orden", cuenta)
print("tipos de texto:", {k: sum(1 for e in eventos if e[0] == k) for k in ("texto", "pensamiento")})
print("PRIMERA MENCIÓN:", json.dumps(primera, ensure_ascii=False, indent=1))
print("\nPRIMERAS 14 LLAMADAS")
for f in filas[:14]:
    print(f["llamada"], f["consultas_acumuladas"], f["comando"].replace("python herramientas/consultar.py ", "")[:80], "|", f["texto_previo"][:170])
