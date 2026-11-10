"""E6 (10/11/2026): un modello visione-linguaggio aperto (Qwen3-VL, Apache 2.0) giudica le carte di Scorri come le
giudica Claude: cosa c'e' nel riquadro rosso. Gira nel Python della NVIDIA (~\\kr_vlm\\venv).
version: 0.1.0
Uso: python vlm_giudica.py <cartella carte> <uscita.json> <modello> <nf4|bf16>"""
import json
import os
import re
import sys
import time

import torch
from transformers import AutoModelForImageTextToText, AutoProcessor

RISPOSTE = ["giusto", "riquadro", "cassonetto", "veicolo", "persona", "ombra", "niente", "non_si_capisce"]
PROMPT = (
    "This image comes from a CCTV camera near street waste bins. Top: a zoom around the red box. Bottom: the whole "
    "frame with the same red box. A program says the red box contains abandoned waste (a bag, cardboard, litter left "
    "on the ground or on a bin). Look at what is inside the red box and answer ONLY with JSON like "
    '{"risposta": "...", "sicuro": true, "cosa": "two or three words"}. '
    "risposta must be one of: giusto (waste, bag, box or litter, and the red box frames it), riquadro (there is waste "
    "but the box covers only a piece of it or is shifted), cassonetto (a bin, container, clothing bin or a part of it: "
    "lid, side, corner), veicolo (car, van, truck or a part: wheel, door, hood, light), persona (person or bicycle), "
    "ombra (shadow, light, reflection), niente (ground, asphalt, grass, leaves, wall, pole, sign, date text), "
    "non_si_capisce (too dark or blurry). sicuro is false when you are not sure.")


def leggi(testo):
    m = re.search(r"\{.*\}", testo, re.S)
    try:
        d = json.loads(m.group(0)) if m else {}
    except ValueError:
        d = {}
    r = str(d.get("risposta", "")).strip().lower()
    if r not in RISPOSTE:
        r = next((x for x in RISPOSTE if x in testo.lower()), "non_si_capisce")
    return {"risposta": r, "sicuro": bool(d.get("sicuro", False)), "cosa": str(d.get("cosa", ""))[:60]}


def main():
    cart, uscita, nome, modo = sys.argv[1:5]
    t0 = time.time()
    kw = {"device_map": "cuda:0"}
    if modo == "nf4":
        from transformers import BitsAndBytesConfig
        kw["quantization_config"] = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                                                       bnb_4bit_compute_dtype=torch.bfloat16)
    else:
        kw["torch_dtype"] = torch.bfloat16
    proc = AutoProcessor.from_pretrained(nome)
    model = AutoModelForImageTextToText.from_pretrained(nome, **kw)
    carico = time.time() - t0
    carte = json.load(open(os.path.join(cart, "carte.json"), encoding="utf-8"))
    out = {"modello": nome, "modo": modo, "caricato_in_s": round(carico, 1), "memoria_gb": None, "giudizi": []}
    for c in carte:
        f = os.path.join(cart, c["file"])
        t1 = time.time()
        msg = [{"role": "user", "content": [{"type": "image", "path": f}, {"type": "text", "text": PROMPT}]}]
        try:
            inp = proc.apply_chat_template(msg, tokenize=True, add_generation_prompt=True, return_dict=True,
                                           return_tensors="pt").to(model.device)
            with torch.inference_mode():
                g = model.generate(**inp, max_new_tokens=80, do_sample=False)
            testo = proc.batch_decode(g[:, inp["input_ids"].shape[1]:], skip_special_tokens=True)[0]
            r = leggi(testo)
        except Exception as ex:   # noqa: BLE001
            testo, r = f"{type(ex).__name__}: {ex}"[:300], {"risposta": "errore", "sicuro": False, "cosa": ""}
        out["giudizi"].append({"id": c["id"], **r, "testo": testo[:300], "secondi": round(time.time() - t1, 2)})
        if len(out["giudizi"]) % 20 == 0:
            out["memoria_gb"] = round(torch.cuda.max_memory_allocated() / 1e9, 2)
            json.dump(out, open(uscita, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            print(len(out["giudizi"]), "carte", flush=True)
    out["memoria_gb"] = round(torch.cuda.max_memory_allocated() / 1e9, 2)
    out["totale_s"] = round(time.time() - t0, 1)
    json.dump(out, open(uscita, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
