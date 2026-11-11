"""Carica owlv2_fp32.onnx (344 MB) su Drive, cartella «Analisi video», accanto a compito.zip: il compito p2p_ponte 0.10.0
lo scarica sul COMPUTERONE per misurare OWLv2 sulla scheda grafica (troppo grande per stare nel compito.zip).
version: 0.1.0 (11/11/2026)

Come gli altri segnaposto: l'account di servizio di Alma non ha spazio suo su Drive e non puo' creare file nuovi, quindi
nella cartella «Analisi video» deve esserci gia' un file chiamato owlv2_fp32.onnx (anche vuoto, messo da Dario) e qui se
ne sostituisce il contenuto. Sul file si scrivono le proprieta' byte e sha256 (le prime 16 cifre), per controllo.

Uso:  python3 carica_owl.py <cartella con la chiave dell'account di servizio> [owlv2_fp32.onnx]
La chiave si copia nella cartella solo per il tempo della chiamata e poi si cancella (mai nel repository).
"""
import hashlib
import os
import sys

sys.path.insert(0, "/home/user/kit-rifiuti-programma/scripts")
import drive_alma  # noqa: E402

NOME = "owlv2_fp32.onnx"
PREDEFINITO = "/tmp/claude-0/-home-user/9f050eb2-6227-5d3b-8dcb-7ce079802227/scratchpad/owlonnx/owlv2_fp32.onnx"


def impronta(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(16 << 20), b""):
            h.update(b)
    return h.hexdigest()[:16]


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    chiave = [sys.argv[1]]
    locale = sys.argv[2] if len(sys.argv) > 2 else PREDEFINITO
    if not drive_alma.file_chiave(chiave):
        sys.exit(f"nella cartella {sys.argv[1]} non c'e' la chiave dell'account di servizio di Alma")
    byte = os.path.getsize(locale)
    sha = impronta(locale)
    f = drive_alma.trova(NOME, chiave)
    if not f:
        sys.exit(f"su Drive, nella cartella «Analisi video», manca il segnaposto «{NOME}»: va creato a mano (anche vuoto)")
    pr = f.get("appProperties") or {}
    if pr.get("sha256") == sha and pr.get("byte") == str(byte):
        print(f"{NOME} e' gia' su Drive ({byte} byte, sha256 {sha}): niente da caricare")
        return
    ok, msg = drive_alma.carica(locale, NOME, chiave, proprieta={"byte": str(byte), "sha256": sha})
    print(msg)
    if not ok:
        sys.exit(1)
    f = drive_alma.servizio(chiave).files().get(fileId=f["id"], fields="size,appProperties").execute()
    print(f"su Drive: {f.get('size')} byte (atteso {byte}), proprieta' {f.get('appProperties')}")
    if str(f.get("size")) != str(byte):
        sys.exit("la grandezza su Drive non torna")


if __name__ == "__main__":
    main()
