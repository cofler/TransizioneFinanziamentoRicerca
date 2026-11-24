"""Mini modello stock-flow dei precari degli EPR (2023 -> fine 2026) e rischio 2027.

Modulo richiamato da stock_flow_precari.py (pipeline completa: universita' + EPR).
Eseguito da solo stampa i risultati EPR.

Stessa identita' contabile del modello universitario:
  usciti = P_2023 + ingressi - P_2026 - passati_in_ruolo

Dati (unita' annue, Conto annuale RGS, dai grafici "Assegnisti di ricerca negli EPR" e
"Ricercatori e tecnologi a tempo determinato negli EPR"; NON includono i borsisti):
  assegnisti  2023 2.505, 2024 2.825, 2027 scenario 1.149 (809-1.637)
              cali 2024->2027: fine PNRR -405, tetto 30 mesi -1.271
  TD ric/tecn 2023 880, 2024 1.685, 2027 scenario 341 (161-663)
              cali 2024->2027: fine PNRR -1.090, tetto 30 mesi -254
  (valori trascritti a mano dal grafico)
Ingressi in ruolo: input/AssuntiCessati2024.xlsx (Conto annuale 2024, EPR):
  ricercatore III livello 140 + tecnologo III livello 118 = 258 assunti/anno.

Il modello di simulazione (config.EPR_PRECARI_OGGI) usa 6.000 precari EPR in TESTE,
borsisti inclusi: qui si ricostruisce a quale anno e quota di borsisti corrispondono.
"""
from pathlib import Path

import numpy as np
import openpyxl

ROOT = Path(__file__).parent

# ------------------------------------------------- dati dal grafico (unita' annue)
ASS = {2023: 2505, 2024: 2825, 2027: 1149}
TD = {2023: 880, 2024: 1685, 2027: 341}
CALO_PNRR = {"ass": 405, "td": 1090}
CALO_TETTO = {"ass": 1271, "td": 254}
RANGE_2027 = {"ass": (809, 1637), "td": (161, 663)}
EPR_PRECARI_MODELLO = 6000      # config.EPR_PRECARI_OGGI (teste, borsisti inclusi)


def assunti_ingresso_epr():
    """Ricercatori e tecnologi di III livello assunti negli EPR, Conto annuale 2024."""
    ws = openpyxl.load_workbook(ROOT / "input" / "AssuntiCessati2024.xlsx", data_only=True).active
    tot = 0
    for r in ws.iter_rows(values_only=True):
        if r[5] in ("6 - RICERCATORE", "12 - TECNOLOGO") and r[6] == "Totale":
            tot += r[7] + r[8]
    return tot


# (basso, centrale, alto, descrizione)
PARAM = {
    "k_teste":  (1.00, 1.15, 1.30, "persone per unita' annua (contratti infra-annuali)"),
    "D":        (2.0, 3.0, 5.0,    "anni di permanenza della persona nel pool (uscite 2024)"),
    "E_2526":   (0, 300, 600,      "nuovi ingressi 2025-26 (unita' annue)"),
    "pnrr_ok":  (0.80, 1.00, 1.00, "quota del calo 'fine PNRR' gia' avvenuta a fine 2026"),
    "tetto_ok": (0.00, 0.25, 0.50, "quota del calo 'tetto 30 mesi' gia' avvenuta a fine 2026"),
    "s_prec":   (0.60, 0.75, 0.90, "quota assunti III livello che erano precari EPR"),
}
CENTRALE = {k: v[1] for k, v in PARAM.items()}


def modello(p, hires):
    """Stock e flussi EPR. Valori in unita' annue (UA) e, col suffisso _teste, in persone."""
    k = p["k_teste"]
    f = {}
    f["P23"] = ASS[2023] + TD[2023]
    f["P24"] = ASS[2024] + TD[2024]
    f["P27"] = ASS[2027] + TD[2027]
    f["ass26"] = ASS[2024] - p["pnrr_ok"] * CALO_PNRR["ass"] - p["tetto_ok"] * CALO_TETTO["ass"]
    f["td26"] = TD[2024] - p["pnrr_ok"] * CALO_PNRR["td"] - p["tetto_ok"] * CALO_TETTO["td"]
    f["P26"] = f["ass26"] + f["td26"]
    f["ingressi"] = (f["P24"] - f["P23"]) + f["P23"] / p["D"] + p["E_2526"]
    # gli assunti in ruolo (Conto annuale) sono gia' persone
    f["in_ruolo"] = hires * 3 * p["s_prec"]                  # 2024, 2025, 2026
    for v in ("P23", "P24", "P26", "P27", "ass26", "td26", "ingressi"):
        f[v + "_teste"] = f[v] * k
    f["ass27_teste"] = ASS[2027] * k
    f["usciti_teste"] = (f["P23"] + f["ingressi"] - f["P26"]) * k - f["in_ruolo"]
    f["a_rischio_2027_teste"] = (f["P26"] - f["P27"]) * k
    f["usciti_min_dal_picco_teste"] = (f["P24"] - f["P26"]) * k - hires * 2 * p["s_prec"]
    f["passati_teste"] = (f["P23"] + f["ingressi"]) * k      # = usciti + in ruolo + rimasti
    f["quota_usciti_su_chi_lascia"] = f["usciti_teste"] / (f["usciti_teste"] + f["in_ruolo"])
    f["borsisti_impliciti_se_2024"] = EPR_PRECARI_MODELLO - f["P24_teste"]
    f["borsisti_impliciti_se_2026"] = EPR_PRECARI_MODELLO - f["P26_teste"]
    assert np.allclose(f["passati_teste"], f["usciti_teste"] + f["in_ruolo"] + f["P26_teste"])
    return f


def monte_carlo(hires, n=50_000, seed=7):
    rng = np.random.default_rng(seed)
    draw = {k: (rng.triangular(lo, mo, hi, n) if lo < hi else np.full(n, float(lo)))
            for k, (lo, mo, hi, _) in PARAM.items()}
    return modello(draw, hires)


if __name__ == "__main__":
    h = assunti_ingresso_epr()
    c, mc = modello(CENTRALE, h), monte_carlo(h)
    print(f"Assunti III livello EPR (Conto annuale 2024): {h}/anno")
    for k, v in c.items():
        arr = np.broadcast_to(np.asarray(mc[k], dtype=float), (50_000,))
        print(f"{k:32s} {v:10.1f}  p10 {np.percentile(arr, 10):9.1f}  p90 {np.percentile(arr, 90):9.1f}")
