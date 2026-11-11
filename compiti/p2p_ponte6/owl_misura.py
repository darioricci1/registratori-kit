"""owl_misura.py: la misura di OWLv2 in ONNX (misura_owl del ponte) in un processo suo.
Nel compito 25 (ponte 0.10.0) la misura girava in un filo del ponte e onnxruntime non si caricava («DLL load failed
while importing onnxruntime_pybind11_state: Routine di inizializzazione della libreria (DLL) non riuscita»): nello
stesso processo c'era gia' la libreria Focus, con la sua cartella FocusNetSDK (msvcp140, vcruntime140 suoi) messa
davanti nel PATH e fra le cartelle delle DLL. Qui gira lanciato dal ponte come un compito a parte
(exe --compito <cartella>, ambiente pulito, senza FocusNetSDK nel PATH): nella cartella ci sono ponte.py (il compito.py
del ponte, da cui si prendono le definizioni fino al ciclo, senza farlo partire) e owl.json ({"owl": cfg, "lavori": [...]}).
Scrive uscita/owl_tempi.json; il ponte lo copia nella sua uscita.
version: 0.1.0 (11/11/2026)
"""
import json
import os
import sys

C = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
FINE = "\nt_fine = time.time() + DURATA"   # da qui in giu' il ponte ascolta: non si esegue
src = open(os.path.join(C, "ponte.py"), encoding="utf-8").read()
g = {"__name__": "ponte", "__file__": os.path.join(C, "ponte.py")}
exec(compile(src[:src.index(FINE)], os.path.join(C, "ponte.py"), "exec"), g)   # noqa: S102 - il nostro codice
cfg = json.load(open(os.path.join(C, "owl.json"), encoding="utf-8"))
g["av"]("owl_misura 0.1.0: parte in un processo suo (pid %d)" % os.getpid())
g["misura_owl"](cfg["owl"], cfg.get("lavori") or [])
g["av"]("owl_misura: fatto")
