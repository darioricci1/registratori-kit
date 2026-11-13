"""E6 (10/11/2026): un modello visione-linguaggio aperto (Qwen3-VL, Apache 2.0) giudica le carte di Scorri come le
giudica Claude: cosa c'e' nel riquadro rosso. Gira nel Python della NVIDIA (~\\kr_vlm\\venv).
version: 0.3.0 (13/11/2026) - v3: prima e dopo (tre immagini), per i pezzi del secondo passaggio della prova grande.
version: 0.2.0 (11/11/2026) - la domanda in tre varianti, da confrontare sulle stesse carte:
  v1  la domanda del 10/11 (etichette italiane, una sola immagine);
  v2  la domanda nuova: cosa e' un abbandono (FUORI dai contenitori, anche sul coperchio) e cosa no (il contenitore,
      il rifiuto gia' dentro, veicolo, persona, ombra, vegetazione), etichette in inglese ripassate in italiano,
      prima «vedo» e «dove» e poi la risposta, cosi' il modello guarda prima di decidere;
  v2d come v2, ma con davanti un primo piano del riquadro rosso ingrandito (il 4B il 10/11 perdeva i sacchetti
      piccoli: nel ritaglio di Scorri il riquadro e' largo una settantina di punti su 640).
0.1.0 (10/11/2026) - prima versione (v1).
Uso: python vlm_giudica.py <cartella carte> <uscita.json> <modello> <nf4|bf16> [--prompt v1|v2|v2d]"""
import json
import os
import re
import sys
import tempfile
import time

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

# v2: le etichette che vede il modello (inglesi, senza doppi sensi: «riquadro» il 4B lo leggeva come «box» e lo dava
# a cassonetti, portiere e rami) e quelle di Scorri.
INGLESE = {"waste": "giusto", "waste_partly": "riquadro", "bin": "cassonetto", "vehicle": "veicolo",
           "person": "persona", "shadow": "ombra", "nothing": "niente", "unclear": "non_si_capisce"}
IMMAGINI_V2 = ("The image has two parts. TOP: a zoom around the red box. BOTTOM: the whole camera frame, smaller, "
               "with the same red box.")
IMMAGINI_V2D = ("Image 1 is a close-up of the red box, enlarged. Image 2 has two parts: TOP a zoom around the red box, "
                "BOTTOM the whole camera frame, smaller, with the same red box.")
PROMPT_V2 = (
    "You check alerts from a CCTV camera that watches street waste containers in Italy. A program drew a RED BOX "
    "where it thinks someone abandoned waste. Decide what the red box really contains. {immagini}\n\n"
    "ABANDONED WASTE is something left OUTSIDE the containers: a garbage bag (black, white, blue or transparent), a "
    "cardboard box, a bag of clothes, furniture, a mattress, an appliance, a tyre, rubble, a crate, bottles or "
    "litter, lying on the ground, leaning against a container, or put on top of a container lid. Even a small bag or "
    "a small light-coloured object lying on the ground next to the containers counts.\n\n"
    "NOT abandoned waste:\n"
    "- the container itself or a part of it: bin, wheelie bin, glass bell, clothing bin, lid, side, corner, wheel, "
    "pedal, sticker, red and white stripes;\n"
    "- waste that is already INSIDE a container, or only visible through its opening;\n"
    "- a vehicle or a part of it (car, van, truck: door, tailgate, hood, wheel, light, bumper);\n"
    "- a person, a bicycle, someone's legs, also when the person is carrying a bag;\n"
    "- a shadow, a patch of light, a headlight reflection, a wet spot;\n"
    "- ground, asphalt, kerb, grass, leaves, branches, bushes, reeds, wall, pole, sign, fence, the date and time "
    "text.\n"
    "Judge only what is INSIDE the red box: waste elsewhere in the picture does not count.\n\n"
    "risposta is ONE word from this list:\n"
    "waste = abandoned waste, and the red box frames it\n"
    "waste_partly = abandoned waste that the red box cuts or misses slightly (the waste touches the box)\n"
    "bin = a container or a part of it\n"
    "vehicle = a vehicle or a part of it\n"
    "person = a person or a bicycle\n"
    "shadow = shadow, light or reflection\n"
    "nothing = ground, vegetation, wall, pole, sign or text\n"
    "unclear = too dark or too blurry to tell\n\n"
    "First look, then answer. Reply ONLY with JSON, with these keys in this order:\n"
    '{{"vedo": "what is inside the red box, 3 to 8 words", '
    '"dove": "ground | on_container | inside_container | none", '
    '"risposta": "one word from the list", "sicuro": true}}\n'
    "sicuro is false when you hesitate between two words.")


# 0.3.0: v3, prima e dopo (compito 34, secondo passaggio della prova grande): e' comparso un rifiuto abbandonato?
PROMPT_V3 = (
    "You check alerts from a CCTV camera that watches street waste containers in Italy. Image 1 shows an area BEFORE, "
    "image 2 the SAME area about one or two minutes LATER (AFTER); the red box marks the same place in both. Image 3 "
    "is the whole camera frame AFTER, with the red box. A program noticed that something changed in the red box and "
    "stayed. Decide whether someone ABANDONED WASTE there: a new garbage bag, cardboard, box, bag of clothes, "
    "furniture, appliance, rubble, crate or litter that is in the AFTER image and was NOT in the BEFORE image, lying "
    "on the ground, leaning against a container or put on a container lid.\n"
    "It is NOT abandoned waste when the change is: a parked or moving vehicle, a person, a shadow or change of light, "
    "a reflection, a container moved or opened, waste already there BEFORE, leaves or vegetation, rain.\n\n"
    "risposta is ONE word: waste (new abandoned waste in the red box), vehicle, person, shadow (shadow, light, "
    "reflection), bin (a container moved, opened or closed), already (the object was already there before), "
    "nothing (no visible change), unclear.\n"
    "First look, then answer. Reply ONLY with JSON: "
    '{"prima": "what is in the box before, 3 to 8 words", "dopo": "what is in the box after, 3 to 8 words", '
    '"risposta": "one word", "sicuro": true}')


def leggi(testo):
    m = re.search(r"\{.*\}", testo, re.S)
    try:
        d = json.loads(m.group(0)) if m else {}
    except ValueError:
        d = {}
    r = str(d.get("risposta", "")).strip().lower()
    r = INGLESE.get(r, r)
    if r not in RISPOSTE:
        basso = testo.lower()
        trovate = [INGLESE[x] for x in sorted(INGLESE, key=len, reverse=True)
                   if re.search(r"\b" + x + r"\b", basso)]
        r = trovate[0] if trovate else next((x for x in RISPOSTE if x in basso), "non_si_capisce")
    return {"risposta": r, "sicuro": bool(d.get("sicuro", False)),
            "cosa": str(d.get("vedo", d.get("cosa", "")))[:60], "dove": str(d.get("dove", ""))[:20]}


def riquadro_rosso(im):
    """(x0, y0, x1, y1) del riquadro rosso nello zoom in alto della carta (alto 3/4 della larghezza), o None.
    Cerca righe e colonne con un tratto rosso continuo lungo almeno 20 punti: un cassonetto rosso pieno non fa
    linee sottili, ma se il riquadro trovato e' troppo grande o troppo piccolo si rinuncia (v2d diventa v2)."""
    import numpy as np
    a = np.asarray(im.convert("RGB")).astype(int)
    alto = round(a.shape[1] * 0.75)
    t = a[:alto]
    rosso = (t[..., 0] > 150) & (t[..., 1] < 100) & (t[..., 2] < 100) & (t[..., 0] - t[..., 1] > 80)

    def corse(m):
        out = np.zeros(m.shape[0], int)
        for i, riga in enumerate(m):
            n = b = 0
            for v in riga:
                n = n + 1 if v else 0
                b = max(b, n)
            out[i] = b
        return out

    rr = np.where(corse(rosso) >= 20)[0]
    cc = np.where(corse(rosso.T) >= 20)[0]
    if len(rr) < 2 or len(cc) < 2:
        return None
    x0, y0, x1, y1 = int(cc.min()), int(rr.min()), int(cc.max()), int(rr.max())
    area = (x1 - x0) * (y1 - y0) / (a.shape[1] * alto)
    if x1 - x0 < 15 or y1 - y0 < 15 or area > 0.4:
        return None
    return x0, y0, x1, y1


def primo_piano(f, cartella):
    """Il riquadro rosso con mezzo riquadro di margine per parte (almeno 100 punti), ingrandito a 448 sul lato lungo.
    Il percorso del file, o None se il riquadro non si trova."""
    from PIL import Image
    im = Image.open(f).convert("RGB")
    b = riquadro_rosso(im)
    if not b:
        return None
    x0, y0, x1, y1 = b
    alto = round(im.width * 0.75)
    mx, my = max(50, (x1 - x0) // 2), max(50, (y1 - y0) // 2)
    pezzo = im.crop((max(0, x0 - mx), max(0, y0 - my), min(im.width, x1 + mx), min(alto, y1 + my)))
    k = 448 / max(pezzo.size)
    pezzo = pezzo.resize((round(pezzo.width * k), round(pezzo.height * k)), Image.LANCZOS)
    p = os.path.join(cartella, "pp_" + os.path.basename(f))
    pezzo.save(p, quality=92)
    return p


def domanda(f, variante, cartella):
    """Il contenuto del messaggio per una carta e la variante davvero usata (v2d senza riquadro diventa v2)."""
    if variante == "v1":
        return [{"type": "image", "path": f}, {"type": "text", "text": PROMPT}], "v1"
    if variante == "v3":
        b = f[:-4]
        return [{"type": "image", "path": b + "_prima.jpg"}, {"type": "image", "path": b + "_dopo.jpg"},
                {"type": "image", "path": f}, {"type": "text", "text": PROMPT_V3}], "v3"
    if variante == "v2d":
        pp = primo_piano(f, cartella)
        if pp:
            return [{"type": "image", "path": pp}, {"type": "image", "path": f},
                    {"type": "text", "text": PROMPT_V2.format(immagini=IMMAGINI_V2D)}], "v2d"
    return [{"type": "image", "path": f}, {"type": "text", "text": PROMPT_V2.format(immagini=IMMAGINI_V2)}], "v2"


def main():
    import torch
    from transformers import AutoModelForImageTextToText, AutoProcessor
    cart, uscita, nome, modo = sys.argv[1:5]
    variante = sys.argv[sys.argv.index("--prompt") + 1] if "--prompt" in sys.argv else "v1"
    if variante not in ("v1", "v2", "v2d", "v3"):
        sys.exit(f"--prompt {variante}: sono v1, v2, v2d")
    tmp = tempfile.mkdtemp(prefix="vlm_pp_")
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
    out = {"modello": nome, "modo": modo, "prompt": variante, "versione": "0.2.0", "caricato_in_s": round(carico, 1),
           "memoria_gb": None, "giudizi": []}
    for c in carte:
        f = os.path.join(cart, c["file"])
        t1 = time.time()
        usata = variante
        try:
            contenuto, usata = domanda(f, variante, tmp)
            msg = [{"role": "user", "content": contenuto}]
            inp = proc.apply_chat_template(msg, tokenize=True, add_generation_prompt=True, return_dict=True,
                                           return_tensors="pt").to(model.device)
            with torch.inference_mode():
                g = model.generate(**inp, max_new_tokens=80 if variante == "v1" else 160, do_sample=False)
            testo = proc.batch_decode(g[:, inp["input_ids"].shape[1]:], skip_special_tokens=True)[0]
            r = leggi(testo)
        except Exception as ex:   # noqa: BLE001
            testo, r = f"{type(ex).__name__}: {ex}"[:300], {"risposta": "errore", "sicuro": False, "cosa": "",
                                                           "dove": ""}
        out["giudizi"].append({"id": c["id"], **r, "prompt": usata, "testo": testo[:300],
                               "secondi": round(time.time() - t1, 2)})
        if len(out["giudizi"]) % 20 == 0:
            out["memoria_gb"] = round(torch.cuda.max_memory_allocated() / 1e9, 2)
            json.dump(out, open(uscita, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            print(len(out["giudizi"]), "carte", flush=True)
    out["memoria_gb"] = round(torch.cuda.max_memory_allocated() / 1e9, 2)
    out["totale_s"] = round(time.time() - t0, 1)
    json.dump(out, open(uscita, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
