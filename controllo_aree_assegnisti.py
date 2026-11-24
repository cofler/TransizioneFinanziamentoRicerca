"""Controllo della discrepanza sugli assegnisti tra Excel e monitoraggio.

Il problema: nell'Excel "La grande espulsione_2.xlsx" gli assegnisti di oggi erano ricavati come
  somma per area CUN (01-14) di TUTTE le qualifiche - contratti - incarichi postdoc - incarichi di ricerca
mentre i contratti e gli incarichi sottratti erano i totali "tutte le aree". Se una parte dei
nuovi contratti/incarichi non ha un'area CUN (sono inquadrati solo sui nuovi SSD/GSD 2024),
la sottrazione toglie persone che nella somma per area non c'erano, e gli assegnisti escono sottostimati.

Questo script interroga cercauniversita.mur.gov.it (tutti gli atenei, area per area) e confronta:
  - somma per area, tutte le qualifiche
  - somma per area, solo assegni di ricerca
  - totali nazionali per qualifica (contratti, incarichi postdoc, incarichi di ricerca)
La query "tutte le aree + tutti gli atenei" per assegni e "tutte le qualifiche" restituisce 0
(troppi risultati): per quei totali fa fede il monitoraggio, che somma ateneo per ateneo.

Uso:  python controllo_aree_assegnisti.py   -> output/controllo_aree_assegnisti.csv
Usa le funzioni di NumeroRicercatoriEmail/mur_helpers.py (stessa sessione e token del monitoraggio).
Fa ~35 richieste in sequenza, con pause.
"""
import sys
import time
import warnings
from datetime import date
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

ROOT = Path(__file__).parent
MONITORAGGIO_DIR = ROOT.parent / "NumeroRicercatoriEmail"
sys.path.insert(0, str(MONITORAGGIO_DIR))
import mur_helpers as M  # noqa: E402

warnings.filterwarnings("ignore")
F = "filtri_ricerca_assegnisti_form"
URL = f"{M.MUR_BASE}/ricerca-assegnisti"
QUALIFICHE = {"0": "Tutte le qualifiche", "1": "Assegni di ricerca", "2": "Contratti di ricerca",
              "3": "Incarichi post-doc", "4": "Incarichi di ricerca"}


def conta(qualifica, area="0000", ssd="0000"):
    for _ in range(3):
        try:
            s = M._session()
            soup = BeautifulSoup(s.get(URL, timeout=30).text, "html.parser")
            data = {f"{F}[qualifica]": qualifica, f"{F}[ateneo]": "ALL", f"{F}[area]": area,
                    f"{F}[ssd]": ssd, f"{F}[ssd24]": "ALL", f"{F}[argomentoDellaRicerca]": "",
                    f"{F}[cognome]": "", f"{F}[nome]": "", f"{F}[_token]": M._csrf_token(soup, F)}
            r = s.post(URL, data=data, timeout=90)
            return M._extract_count(BeautifulSoup(r.text, "html.parser"))
        except Exception as e:  # il sito chiude connessioni sotto carico: riprova
            print("  riprovo:", e, flush=True)
            time.sleep(5)
    return None


def main():
    oggi = date.today().isoformat()
    righe = []
    for q in ("2", "3", "4"):
        righe.append(dict(data=oggi, qualifica=QUALIFICHE[q], area="tutte", n=conta(q)))
        time.sleep(1.5)
    for q in ("0", "1"):
        for a in [f"{i:02d}" for i in range(1, 15)]:
            righe.append(dict(data=oggi, qualifica=QUALIFICHE[q], area=a, n=conta(q, a)))
            time.sleep(1.5)
    df = pd.DataFrame(righe)
    (ROOT / "output").mkdir(exist_ok=True)
    df.to_csv(ROOT / "output" / "controllo_aree_assegnisti.csv", index=False, encoding="utf-8-sig")

    per_area = df[df.area != "tutte"].groupby("qualifica").n.sum()
    nuovi = df[df.area == "tutte"].n.sum()
    tot, ar = per_area["Tutte le qualifiche"], per_area["Assegni di ricerca"]
    print(f"Somma per area, tutte le qualifiche: {tot}")
    print(f"Somma per area, assegni:             {ar}")
    print(f"  -> contratti+incarichi CON area:   {tot - ar}")
    print(f"Contratti+incarichi, tutte le aree:  {nuovi}")
    print(f"  -> contratti+incarichi SENZA area: {nuovi - (tot - ar)}")
    print(f"Assegni 'per differenza' (metodo Excel): {tot - nuovi}  vs assegni per area: {ar}")


if __name__ == "__main__":
    main()
