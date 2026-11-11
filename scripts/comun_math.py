"""Utilidades compartidas por todos los brazos: problemas, prompt, parámetros y calificación (como el MIT)."""
import json, os

BS = chr(92)  # barra invertida; se arma así para que ningún editor/shell la degrade
RAIZ = os.environ.get("PROYECTO_RAIZ", r"<proyecto>")
# Prompt del MIT (exp8_math/code/mathqa.py build_prompt): problema + UN salto de línea + instrucción.
INSTRUCCION = "Please reason step by step, and put your final answer within " + BS + "boxed{}."

def construir_prompt(problema):
    return problema + "\n" + INSTRUCCION

# ---- Configuraciones de muestreo (todas: thinking ON, max_tokens 32768, seed 0, repetition_penalty 1.0 salvo que se diga)
# LÍNEA BASE OFICIAL = exacta del MIT (protocolo think35, exp8_math/code/profiles.py): permite replicar su 7.9% en MATH-500.
BASE_MIT = dict(temperature=0.6, top_p=0.95, top_k=20, presence_penalty=1.5, repetition_penalty=1.0, max_tokens=32768)
# PILOTO (decidido 2026-11-03): presence 0 en AMBOS motores; sirve solo para comparar motores, NO es la línea base.
PILOTO_PRESENCE0 = dict(BASE_MIT, presence_penalty=0.0)
# Brazo "cero edición": se prueban por separado (cada uno cambia SOLO lo indicado respecto de BASE_MIT).
# Los valores concretos de repetition_penalty y presence más alto se fijan antes de correrlos (ver BITACORA).
# Valores fijados por el usuario (2026-11-03). Cada variante cambia SOLO un parámetro respecto de BASE_MIT.
# "thinking" no es parámetro de muestreo: es el modo (enable_thinking del chat template).
# OJO no-thinking: el MIT usó para no-thinking temp 0.7/top_p 0.8/max 8192; aquí NO se copia, porque el usuario pidió
# cambiar solo un parámetro y mantener 32,768 tokens. Se deja el muestreo de BASE_MIT y solo se apaga el thinking.
CERO_EDICION = {
    "no_thinking":  dict(BASE_MIT, thinking=False),
    "presence0":    dict(BASE_MIT, presence_penalty=0.0),
    "presence2":    dict(BASE_MIT, presence_penalty=2.0),
    "rep105":       dict(BASE_MIT, repetition_penalty=1.05),
    "rep110":       dict(BASE_MIT, repetition_penalty=1.1),
    # Config de thinking de la ficha de Qwen3.5-0.8B (texto): temp 1.0, top_p 0.95, top_k 20, presence 1.5, rep 1.0.
    # Frente a BASE_MIT solo cambia la temperatura (0.6 -> 1.0). Decidido por el usuario 2026-11-05 (1 semilla, 100 MATH).
    "ficha_qwen":   dict(BASE_MIT, temperature=1.0),
}
for _v in CERO_EDICION.values():
    _v.setdefault("thinking", True)
# Muestreo no-thinking del MIT (exp8_math/code/evaluate.py SAMPLING_NOTHINK35): temp 0.7, top_p 0.8, top_k 20,
# presence 1.5, max_tokens 8192 (este es el perfil que el MIT descartó a favor de thinking; se usa aquí para comparar).
NOTHINK_MIT = dict(temperature=0.7, top_p=0.8, top_k=20, presence_penalty=1.5, repetition_penalty=1.0,
                   max_tokens=8192, thinking=False)
ORDEN_NOCHE =["no_thinking", "presence0", "presence2", "rep105", "rep110"]

def cargar_problemas(ids_file, jsonl="math500_subset100.jsonl"):
    ids = [l.strip() for l in open(os.path.join(RAIZ, "datos", ids_file), encoding="utf-8")
           if l.strip() and not l.startswith("#")]
    todos = {}
    for l in open(os.path.join(RAIZ, "datos", jsonl), encoding="utf-8"):
        r = json.loads(l); todos[r["id"]] = r
    return [todos[i] for i in ids]

# ---- Calificación como el MIT: último caja-de-respuesta (hendrycks last_boxed_only_string), y math-verify 0.9.0
# verify(parse(caja(gold)), parse(caja(pred))). Sin caja cerrada = sin respuesta = incorrecto.
def ultima_caja(texto):
    idx = texto.rfind(BS + "boxed")
    if idx < 0:
        idx = texto.rfind(BS + "fbox")
        if idx < 0: return None
    abiertas, fin = 0, None
    for i in range(idx, len(texto)):
        if texto[i] == "{": abiertas += 1
        elif texto[i] == "}":
            abiertas -= 1
            if abiertas == 0: fin = i; break
    if fin is None: return None
    caja = texto[idx:fin + 1]
    for izq in (BS + "boxed{", BS + "fbox{"):
        if caja.startswith(izq): return caja[len(izq):-1]
    return None

def quitar_pensamiento(texto):
    """Quita el bloque de razonamiento: lo que va después de </think>. Si no hay </think> (respuesta cortada
    en el límite), no hay respuesta final. SUPUESTO nuestro: el MIT dice 'a stray reasoning block is cut off first'."""
    return texto.split("</think>", 1)[1] if "</think>" in texto else ""

def es_correcta(texto_generado, respuesta_oficial, thinking=True):
    """thinking=False (modo no-thinking): no hay </think>, se califica el texto completo."""
    from math_verify import parse, verify
    pred = ultima_caja(quitar_pensamiento(texto_generado) if thinking else texto_generado)
    if pred is None: return False
    return bool(verify(parse(BS + "boxed{" + respuesta_oficial + "}"), parse(BS + "boxed{" + pred + "}")))
