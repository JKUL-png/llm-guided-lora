"""Regla de calificación del paper 2 (fijada el 2026-11-07, antes de cualquier evaluación del paper 2).
Se aplica igual a todos los brazos y referencias, incluidas las del paper 1 recalificadas.

Regla:
- La respuesta final es el texto después del ÚLTIMO </think>.
- Con thinking: si no hay ningún </think>, no hay respuesta = incorrecta.
- Sin thinking: si no hay </think>, se usa todo el texto; si lo hay, lo que va tras el último.
- MATH y GSM8K: la última caja (\\boxed o \\fbox) de esa respuesta, con math-verify como el MIT. Sin caja = incorrecta.
- IFEval: el corrector oficial de lm-eval (estricto, por prompt) sobre esa respuesta.
Métrica extra: cierres = número de </think> en el texto generado; varios_cierres = 1 si hay más de uno.
El paper 1 usaba lo que va tras el PRIMER </think>; con un solo cierre las dos reglas dan lo mismo."""
import os, sys
os.environ.setdefault("PROYECTO_RAIZ", "/workspace/proyecto")
sys.path.insert(0, "/workspace/proyecto/scripts")
CIERRE_TAG = "</think>"
BS = "\\"


def respuesta_final(texto, pensando=True):
    if CIERRE_TAG in texto:
        return texto.rsplit(CIERRE_TAG, 1)[1]
    return "" if pensando else texto


def cierres(texto):
    return texto.count(CIERRE_TAG)


def es_correcta(texto, respuesta_oficial, thinking=True):
    from comun_math import ultima_caja
    from math_verify import parse, verify
    pred = ultima_caja(respuesta_final(texto, thinking))
    if pred is None:
        return False
    return bool(verify(parse(BS + "boxed{" + respuesta_oficial + "}"), parse(BS + "boxed{" + pred + "}")))


def calificar_ifeval(p, texto, pensando):
    from ifeval_oficial import utils as U
    doc = dict(key=p["key"], instruction_id_list=p["instruction_id_list"], prompt=p["problem"], kwargs=p["kwargs"])
    return bool(U.process_results(doc, [respuesta_final(texto, pensando)])["prompt_level_strict_acc"])


def calificar(p, texto, pensando, tarea):
    return calificar_ifeval(p, texto, pensando) if tarea == "ifeval" else es_correcta(texto, p["answer"], pensando)
