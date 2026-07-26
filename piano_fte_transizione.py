"""
================================================================================
TRANSIZIONE DINAMICA VERSO LO STATO STAZIONARIO "CATTEDRE" (FLC e ERA)
================================================================================
Modello stock-flow per coorte/età. Lo STATO STAZIONARIO è la composizione
prodotta dall'imbuto di carriera (a precari_anni=3 -> "cattedre", docenti ~71%
degli FTE). Il PERCORSO dipende da: stock di partenza in disequilibrio, DURATE
degli stadi, onda pensionamenti, leve di policy (stabilizzazione P2, flusso).

- RICIRCOLO DEI PRECARI: lo stadio "precari" (postdoc/assegni) è un compartimento
con PERMANENZA MEDIA `precari_anni` (default 3). Ogni anno una quota avanza a
RTT (tasso P2/precari_anni). 
A precari_anni=3 riproduce la v1; alzandolo, il flusso d'ingresso scende a
valori realistici e la coda della transizione si allunga.
NB: alzare precari_anni SPOSTA anche lo stato stazionario via dai "cattedre"
(più precari strutturalmente) -> la quota-docente a regime cala.
- Parametri da CLI: --p2-hist, --perm-oggi, --precari-anni, --ramp, --out.

- DURATA DEL RUOLO ENDOGENA: l'età d'ingresso in ruolo è ETA_FINE_PHD +
precari_anni + D_RTT. Allungare il precariato accorcia
la carriera di ruolo (PERM_DUR = 68 - eta_ingresso) invece di lasciarla a 28.
A precari_anni=3 riproduce la v2 (ingresso 40, durata 28).
- LEVA PAGHE RAMPATA come le altre leve: W sale da 1 a W_target su `ramp` anni,
invece di saltare al valore pieno già nell'anno 0.

Unità densità = somma(teste_i*alpha_i)/(pop/100k). Spesa in due misure distinte:
  HERD (R&S)  = somma(FTE_i*COSTO_i)/lambda      [quota-ricerca degli stipendi]
  BUDGET pubb = somma(teste_i*COSTO_i) + attrezz  [stipendi PIENI, incl. didattica]
Leva PAGHE (W = parità PPP x1,66) scala il personale, non le attrezzature.
================================================================================
"""
from __future__ import annotations

import argparse
import os
from dataclasses import dataclass

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt

OUT = os.path.dirname(os.path.abspath(__file__)) or "."   # override con --out

# ============================ COSTANTI ======================================
# Popolazione italiana, scenario SSP2 ("middle of the road"), proiezioni IIASA WIC2023, valori in MIGLIAIA di persone, nodi quinquennali.
# Estratti dal database ufficiale (indicatore 'pop', scenario 2, country_code 380,
# age='All', sex='Both'): https://iiasa.ac.at/models-tools-data/wcde
# Il nodo 2025 (58.934,5) coincide con la popolazione che il modello usava già come
# costante, quindi la baseline non si muove. L'orizzonte del modello è il 2080 e la
# serie arriva al 2085: nessuna estrapolazione oltre i dati.
POP_SSP2 = {2025: 58_934.5, 2030: 58_198.5, 2035: 57_549.9, 2040: 56_987.7,
            2045: 56_465.8, 2050: 55_949.2, 2055: 55_223.2, 2060: 54_319.9,
            2065: 53_295.2, 2070: 52_314.4, 2075: 51_487.8, 2080: 50_823.4,
            2085: 50_229.7}


def pop_100k(anno: int) -> float:
    """Popolazione dell'anno in centinaia di migliaia, interpolata linearmente fra i
    nodi quinquennali SSP2, è il DENOMINATORE della densità: l'Italia perde il 13,8%
    di popolazione fra il 2026 e il 2080, quindi lo stesso organico vale una densità
    più alta col passare del tempo (+16% circa al 2080)."""
    a = min(max(anno, min(POP_SSP2)), max(POP_SSP2))
    nodi = sorted(POP_SSP2)
    lo = max(y for y in nodi if y <= a)
    hi = min(y for y in nodi if y >= a)
    p = POP_SSP2[lo] if lo == hi else (POP_SSP2[lo] + (POP_SSP2[hi] - POP_SSP2[lo])
                                       * (a - lo) / (hi - lo))
    return p / 100.0          # migliaia -> centinaia di migliaia


# Popolazione di RIFERIMENTO, = nodo 2025. Su questa sono ancorati i TARGET di densità
# e la frontiera iso-HERD, che sono grandezze di stato stazionario e non hanno un anno.
# La densità riportata anno per anno usa invece pop_100k(anno), quindi a regime supera
# il target: la differenza fra le colonne 'densità e 'densita_pop2026' è demografia.
POP_100K = 589.34
PIL_MLN = 2_192_182
LAMBDA_HE = 0.70

# "ric_uni" = ruolo universitario con profilo da ricercatore EPR: meno didattica
# (alpha 0,75 invece di 0,50) e stipendio da III->II livello invece che da PO/PA.
# Rende ESATTAMENTE il doppio di FTE per euro rispetto a un docente.
ALPHA = {"dottorando": 0.75, "docente": 0.50, "ric_uni": 0.75,
         "RTT": 0.75, "precari": 0.75}
COSTO = {"docente": 0.39 * 130_000 + 0.61 * 78_000,   # ~98.280
         "ric_uni": 73_500,                            # = COSTO_EPR_RUOLO
         "RTT": 55_000, "precari": 45_000,
         "dottorando": 22_000}                         # borsa + contributi, lordo ente
QUOTA_RIC_UNI = 0.25       # quota del ruolo universitario con profilo ricercatore.
                           # è la leva del COMPROMESSO: alza la densità raggiungibile
                           # a HERD fisso senza aumentare le teste (anzi riducendole),
                           # perchè un ricercatore rende 2x FTE per euro di un docente.
                           # --quota-ric-uni 0 torna al modello tutto-cattedre.

# ---------------------------------------------------------------------------
# UPLIFT PPP: quanto vanno alzate le paghe italiane per la parità di potere
# d'acquisto coi 5 paesi che pagano meglio i dottori di ricerca.
#
# FONTE PRIMARIA: ReICO - Research and Innovation Careers Observatory, iniziativa
# congiunta Commissione europea + OCSE (dal 2024, ERA Policy Agenda Action 4),
# indicatore di reddito dei doctorate holders a parità di potere d'acquisto.
#   https://www.oecd.org/en/data/dashboards/research-and-innovation-careers-observatory-reico.html
# Il rapporto è adimensionale: vale purchè tutti e sei i valori stiano nella
# STESSA unità e siano aggiustati per il potere d'acquisto, come da indicatore.
#
# CONFERMA INDIPENDENTE (importante: due fonti, due decenni, stesso numero).
# Lo stesso rapporto calcolato sullo studio CARSA "Remuneration of Researchers in
# the Public and Private Sectors" (Service Contract REM01, Commissione europea,
# DG Research Direzione D, aprile 2007, ISBN 92-79-05602-4), Tabella 10 p. 46,
# colonna PPS, dati 2006 N=6110, sui 5 paesi UE migliori:
#   (60.530 AT + 56.721 NL + 56.268 LU + 55.998 BE + 53.358 DE) / 5 / 34.120 IT
#   = 1,658, cioè -0,6% dal valore ReICO.
#   https://euraxess.ec.europa.eu/sites/default/files/policy_library/final_report.pdf
# Che due rilevazioni indipendenti a vent'anni di distanza diano lo stesso gap è
# il fatto più robusto di tutto il ramo paghe. (Il vecchio commento attribuiva
# quello studio alle indagini MORE: errore, sono studi diversi e successivi.)
#
# TRE AVVERTENZE, da riportare ovunque il numero compaia:
#
# (a) Il paniere ReICO NON è ristretto all'UE. I due valori di testa (153.819 e
#     148.806) staccano il terzo di oltre 25 punti percentuali e sono
#     verosimilmente extra-UE (Stati Uniti, Svizzera). Il numero va quindi letto
#     come "i 5 paesi che pagano meglio", non "i 5 paesi UE". Sui soli tre paesi
#     dietro gli outlier il rapporto sarebbe 1,467; sul solo primo paese, 1,953.
#
# (b) La popolazione ReICO sono i DOCTORATE HOLDERS di tutti i settori, non i
#     ricercatori accademici. Il modello applica W a docenti, RTT, postdoc e borse:
#     è un trasferimento fra popolazioni diverse. CARSA misurava i ricercatori,
#     ed è la ragione per cui la coincidenza dei due numeri è rassicurante ma
#     non dimostrativa.
#
# (c) è un obiettivo ambizioso per costruzione: la media dei CINQUE paesi che
#     pagano meglio, non la media UE. Nella tabella CARSA la media UE25 (40.126
#     PPS) dava un moltiplicatore di 1,18, circa un terzo del costo aggiuntivo del
#     ramo paghe. Chi legge "parità PPP" deve sapere che la parità è coi migliori.
#
# Il prossimo affinamento utile è un uplift PER FIGURA invece di uno scalare
# unico: oggi W moltiplica allo stesso modo la borsa del dottorando e lo stipendio
# dell'ordinario, e non c'è motivo perchè il gap sia lo stesso.
UPLIFT_PPP = (sum([153_819,    # i 5 paesi con reddito più alto dei dottori di
                   148_806,    # ricerca nel dataset ReICO, a parità di potere
                   119_119,    # d'acquisto. Vedi avvertenza (a): i primi due
                   113_706,    # staccano molto e sono verosimilmente extra-UE.
                   113_695])
              / 5) / 78_758    # Italia -> 1,6485
UPLIFT_PPP_CARSA06 = (sum([60_530, 56_721, 56_268, 55_998, 53_358]) / 5) / 34_120
UPLIFT_PPP_PLI24 = 1.349       # CARSA 2006 col solo deflatore riportato al PLI 2024:
                               # sensitività storica, NON una stima alternativa
# ---------------------------------------------------------------------------
HERD_TGT = 0.69                                        # % PIL (ancora di spesa ERA)
HERD_OGGI = 0.36                                       # % PIL, ISTAT 2023 (ancora di calibrazione)

D_RTT = 6     # durata dell'RTT come da L.79/2022 (conv. DL 36/2022), che ha sostituito
              # RTD-A e RTD-B con un'unica figura tenure-track. Il valore 3 delle
              # versioni precedenti era la durata dell'EX RTD-B (L.240/2010 art.24
              # c.3 lett.b), cioè la tenure più rapida possibile e non quella di
              # legge. Usa --rtt-anni 3 per tornare all'ipotesi ottimistica.
D_PHD = 3                              # durata del dottorato
ETA_FINE_PHD, ETA_PENS = 34, 68        # 34 + 3 (precari) + 6 (RTT) = ingresso a 43
ETA_INIZIO_PHD = ETA_FINE_PHD - D_PHD  # 31
S_RTT_PERM = 1.0

# --- obiettivo: metà dei dottori arriva al ruolo, con UN SOLO filtro --------
# A regime non c'è imbuto interno: chi entra come postdoc arriva all'RTT (P2=1) e
# chi entra come contratto di ricerca EPR si struttura via Madia (P2_EPR=1). Tutta
# la selezione avviene all'uscita dal dottorato, cioè su P1. Ne segue P1 = STAB_PHD.
STAB_PHD = 0.50                        # quota PhD che arriva al ruolo
P2_TGT = 1.0                           # postdoc -> RTT a regime: nessuna perdita
P1 = STAB_PHD                          # ricalcolato in main dai due rami

# --- leva borsa PhD: dal minimo attuale al livello IdR ------------------------
BORSA_OGGI, BORSA_TGT = 1195.0, 1600.0                 # netto mensile, EUR
W_PHD = BORSA_TGT / BORSA_OGGI                         # ~1,34

DENS_OGGI = 99
FTE_OGGI = DENS_OGGI * POP_100K                        # ~58.345

# ============================ RAMO EPR ======================================
# Negli EPR tutti fanno ricerca (alpha unico) e ci si struttura via Madia dopo
# 3 anni di contratto di ricerca: nessun imbuto interno, P2_EPR = 1.
ALPHA_EPR = 0.75
D_PREC_EPR = 3                         # contratto di ricerca prima della Madia
P2_EPR = 1.0                           # chi completa i 3 anni entra in ruolo
ETA_RUOLO_EPR = ETA_FINE_PHD + D_PREC_EPR      # 37
PERM_DUR_EPR = ETA_PENS - ETA_RUOLO_EPR        # 31

EPR_RICERC_OGGI = 25_000               # ricercatori EPR totali
EPR_PRECARI_OGGI = 6_000               # di cui precari (~50% assegnisti)
EPR_RUOLO_OGGI = EPR_RICERC_OGGI - EPR_PRECARI_OGGI

# Costi lordo ente. Il precario oggi è un mix 50/50 assegno (esente IRPEF,
# ~22.700) e contratto di ricerca (~37.600); la L.79/2022 abolisce gli assegni,
# quindi il costo converge al contratto di ricerca ANCHE senza stabilizzare.
COSTO_EPR_PREC_OGGI = 30_000
COSTO_EPR_PREC_TGT = 37_600
COSTO_EPR_RUOLO = 73_500               # carriera III (15a) -> II (16a), CCNL 2022-24 tab. C4
COSTO_EPR_INGRESSO = 48_200            # III livello 0-2 anni: costo di chi si stabilizza OGGI

GOVERD_OGGI, GOVERD_TGT = 0.21, 0.22   # % PIL

# ============================ GERD (3%) =====================================
# BERD (ricerca delle imprese) NON è modellato endogenamente: è ~2/3 del GERD
# italiano e non dipende da nessuna leva qui dentro. Ipotesi dichiarata: quando la
# componente pubblica raggiunge HERD_RIF + GOVERD_RIF, il privato ha tenuto il passo
# e il 3% è raggiunto. BERD è quindi interpolato sullo stesso avanzamento.
GERD_OGGI, GERD_TGT = 1.38, 3.00       # % PIL (GERD 2024 ISTAT; usato anche per il 2026)
HERD_RIF, GOVERD_RIF = 0.69, 0.21      # componente pubblica al punto "3% raggiunto"
                                       # (= HERD_TGT ERA + GOVERD odierno = 0,90%)
LAMBDA_GOV = 0.70
# Overhead EPR (tecnici + infrastruttura) in valore ASSOLUTO, non proporzionale:
# stabilizzare un precario non richiede più acceleratori nè più tecnici. Calibrati
# in main sul GOVERD osservato. Il supporto è stipendi (segue W), le attrezzature no.
OVH_EPR_SUPP = 0.0
OVH_EPR_ATTR = 0.0
PHD_OGGI_REALE = 45_000        # dottorandi in corso, ordine di grandezza MUR
                               # (DA VERIFICARE): serve come test di calibrazione
ANNO0, ORIZZONTE = 2026, 54   # orizzonte fino al 2080

# --- parametri OVERRIDABILI da CLI (default = comportamento v1) --------------
P2_HIST = 0.10
PERM_OGGI = 60_000
PRECARI_ANNI = 3.0
RAMP = 5            # anni di rampa: le leve sono a regime dall'anno ANNO0+RAMP (2030)
PHD_IN_FTE = False  # i dottorandi contano negli FTE-ricerca del dato Eurostat?
                    # Default NO: con NO il modello riproduce ~45k dottorandi e HERD
                    # 0,33% (vs 0,36 ISTAT); con SI dà 20,7k e 0,25%. Il loro COSTO
                    # entra sempre in HERD/budget, a prescindere dal conteggio.
SUPPORTO = None     # overhead tecnici/amministrativi di ricerca sul costo-ricerca
                    # del personale strutturato. None = auto-calibrato su HERD_OGGI.


# ============================ COMPOSIZIONE A REGIME ==========================
def eta_ruolo_in(precari_anni: float) -> int:
    """Età d'ingresso in ruolo: fine PhD + precariato + RTT. Un precariato più
    lungo NON allunga la vita lavorativa, la sposta in avanti."""
    return int(round(ETA_FINE_PHD + precari_anni + D_RTT))


def perm_dur(precari_anni: float) -> int:
    """Anni di ruolo effettivi (slot della coorte). A precari_anni=3 vale 28."""
    return max(1, ETA_PENS - eta_ruolo_in(precari_anni))


def _contrib(P2: float, precari_anni: float) -> tuple[dict[str, float], dict[str, float]]:
    """Per unità di flusso PhD in ingresso, a regime: (teste-anno, FTE) per stadio.
    L'imbuto è PhD -(P1)-> precari -(P2)-> RTT -> ruolo."""
    # per unità di flusso POSTDOC universitario in ingresso (non di flusso PhD:
    # il bacino dei dottorandi serve entrambi i rami, e l'EPR ha fabbisogno fisso)
    ruolo = P2 * perm_dur(precari_anni)
    teste = {"dottorando": D_PHD / P1,      # dottorandi necessari a produrre 1 postdoc
             "precari": precari_anni,
             "RTT": P2 * D_RTT,
             "docente": ruolo * (1 - QUOTA_RIC_UNI),
             "ric_uni": ruolo * QUOTA_RIC_UNI}
    fte = {k: v * ALPHA[k] for k, v in teste.items()}
    if not PHD_IN_FTE:
        fte["dottorando"] = 0.0        # esclusi dal CONTEGGIO, non dal costo
    return teste, fte


def kappa(P2: float, precari_anni: float) -> float:
    """FTE-ricerca universitari per unità di flusso POSTDOC in ingresso, a regime."""
    return sum(_contrib(P2, precari_anni)[1].values())


def _epr_in_tgt() -> float:
    """Fabbisogno EPR a regime: puro RIMPIAZZO a organico costante. Il GOVERD è già
    saturato dalla stabilizzazione, quindi gli EPR non crescono in teste."""
    return EPR_RICERC_OGGI / (D_PREC_EPR + PERM_DUR_EPR)


def regime_shares(precari_anni: float) -> dict[str, float]:
    fte = _contrib(P2_TGT, precari_anni)[1]
    tot = sum(fte.values())
    return {k: v / tot for k, v in fte.items()}


def avg_costo_split(precari_anni: float) -> tuple[float, float]:
    """Quota-ricerca degli stipendi per FTE CONTATO, separando le due leve salariali:
    (personale strutturato/precario -> leva W, borse PhD -> leva W_PHD).
    Il numeratore include i dottorandi anche quando non contano negli FTE."""
    teste, fte = _contrib(P2_TGT, precari_anni)
    tot = sum(fte.values())
    costo = {k: t * ALPHA[k] * COSTO[k] / tot for k, t in teste.items()}
    return sum(v for k, v in costo.items() if k != "dottorando"), costo["dottorando"]


def avg_costo(precari_anni: float) -> float:
    return sum(avg_costo_split(precari_anni))


def teste_per_fte(precari_anni: float) -> float:
    teste, fte = _contrib(P2_TGT, precari_anni)
    return sum(teste.values()) / sum(fte.values())


def densita_iso_herd(herd_pct: float, W: float, precari_anni: float,
                     W_phd: float = 1.0) -> float:
    """Frontiera prezzo<->quantità a HERD costante, con le due leve salariali."""
    c_pers, c_phd = avg_costo_split(precari_anni)
    c_supp = (SUPPORTO or 0.0) * c_pers
    denom = (c_pers * W + c_phd * W_phd + c_supp * W
             + (c_pers + c_phd + c_supp) * (1 - LAMBDA_HE) / LAMBDA_HE)
    fte = (herd_pct / 100 * PIL_MLN) * 1e6 / denom
    return fte / POP_100K


# ============================ MOTORE DI SIMULAZIONE =========================
@dataclass
class Stato:
    phd: list[float]      # dottorandi per anno-di-corso (vintage, D_PHD slot)
    precari: float        # postdoc universitari (compartimento)
    rtt: list[float]      # RTT per anno-di-stadio (vintage)
    perm: list[float]     # ruolo universitario - docenti (PO/PA), per età
    perm_ric: list[float] # ruolo universitario - ricercatori (profilo EPR), per età
    epr_prec: list[float] # contratti di ricerca EPR (vintage, D_PREC_EPR slot)
    epr_ruolo: list[float]# ruolo EPR per età 37..67


def _p1_hist() -> float:
    """P1 di OGGI, ricavato dallo stock osservato di dottorandi: quota di dottori che
    tenta la carriera. Oggi è alta (il filtro sta a valle, P2_HIST=0,10); a regime
    scende a STAB_PHD perchè il filtro si sposta all'uscita dal dottorato."""
    return (_uni_in0() + _epr_in0()) / (PHD_OGGI_REALE / D_PHD)


def _uni_in0() -> float:
    """Flusso di postdoc UNIVERSITARI oggi tale che la densità iniziale = 99."""
    resto = FTE_OGGI - ALPHA["docente"] * PERM_OGGI
    # alpha espliciti per stadio: NON assumere alpha_RTT == alpha_precari
    return resto / (ALPHA["precari"] * PRECARI_ANNI
                    + ALPHA["RTT"] * D_RTT * P2_HIST)


def _epr_in0() -> float:
    """Flusso di contratti di ricerca EPR oggi, dallo stock osservato."""
    return EPR_PRECARI_OGGI / D_PREC_EPR


def _pd_in0() -> float:
    """Flusso PhD in ingresso oggi: alimenta ENTRAMBI i rami, quindi è la somma
    dei due fabbisogni a valle divisa per la sopravvivenza P1 odierna."""
    return (_uni_in0() + _epr_in0()) / _p1_hist()


def _quota_epr0() -> float:
    """Quota EPR implicita nello stato di partenza (vs QUOTA_EPR a regime)."""
    return _epr_in0() / (_uni_in0() + _epr_in0())


def _coorte(teste: float, eta_in: int) -> list[float]:
    """Distribuisce uno stock su classi d'età con la campana empirica (56, sd 7)."""
    eta = np.arange(eta_in, ETA_PENS)
    peso = np.exp(-0.5 * ((eta - 56) / 7) ** 2)
    return list(peso / peso.sum() * teste)


def _init_stato(pd_in0: float) -> Stato:
    perm = _coorte(PERM_OGGI, eta_ruolo_in(PRECARI_ANNI))
    phd = [pd_in0] * D_PHD
    precari = _uni_in0() * PRECARI_ANNI
    rtt = [P2_HIST * _uni_in0()] * D_RTT
    epr_prec = [_epr_in0()] * D_PREC_EPR
    epr_ruolo = _coorte(EPR_RUOLO_OGGI, ETA_RUOLO_EPR)
    perm_ric = [0.0] * len(perm)      # oggi la figura non esiste: q parte da 0
    return Stato(phd, precari, rtt, perm, perm_ric, epr_prec, epr_ruolo)


def _ramp(t: int, v0: float, v1: float) -> float:
    return v1 if t >= RAMP else v0 + (v1 - v0) * t / RAMP


def _teste(s: Stato) -> dict[str, float]:
    # due coorti distinte nel ruolo: la conversione avviene per RICAMBIO (i nuovi
    # entrano come ricercatori), non riclassificando i docenti già in servizio.
    return {"dottorando": sum(s.phd),
            "docente": sum(s.perm),
            "ric_uni": sum(s.perm_ric),
            "RTT": sum(s.rtt), "precari": s.precari}


def _fte(s: Stato) -> dict[str, float]:
    fte = {k: t * ALPHA[k] for k, t in _teste(s).items()}
    if not PHD_IN_FTE:
        fte["dottorando"] = 0.0
    return fte


def _fte_epr(s: Stato) -> float:
    return (sum(s.epr_ruolo) + sum(s.epr_prec)) * ALPHA_EPR


def _spesa_epr(s: Stato, W: float, costo_prec: float) -> dict[str, float]:
    """GOVERD del ramo EPR. Contabilità separata da HERD: settori Eurostat diversi.
    L'overhead è FISSO in valore assoluto (vedi OVH_EPR_*): cambiare lo status
    contrattuale di un ricercatore non moltiplica tecnici e infrastruttura."""
    pers = sum(s.epr_ruolo) * COSTO_EPR_RUOLO + sum(s.epr_prec) * costo_prec
    ric = pers * ALPHA_EPR                      # quota-ricerca (alpha unico)
    return {"goverd_mln": (W * (ric + OVH_EPR_SUPP) + OVH_EPR_ATTR) / 1e6,
            "budget_epr_mln": (W * (pers + OVH_EPR_SUPP) + OVH_EPR_ATTR) / 1e6}


def _spesa(s: Stato, W: float, W_phd: float = 1.0) -> dict[str, float]:
    teste = _teste(s)
    # il costo-ricerca usa ALPHA anche per i dottorandi esclusi dal conteggio FTE:
    # la borsa è spesa R&S comunque la si conti nel personale.
    # due leve distinte: W sul personale, W_phd sulle borse di dottorato.
    lev = {k: (W_phd if k == "dottorando" else W) for k in teste}
    herd_pers = sum(t * ALPHA[k] * COSTO[k] for k, t in teste.items())
    herd_pers_w = sum(t * ALPHA[k] * COSTO[k] * lev[k] for k, t in teste.items())
    full_pers_w = sum(t * COSTO[k] * lev[k] for k, t in teste.items())
    # tecnici / amministrativi di ricerca: overhead sul costo-ricerca del personale
    # strutturato (non sulle borse). Sono stipendi, quindi seguono la leva W.
    s = SUPPORTO or 0.0
    supp = s * sum(t * ALPHA[k] * COSTO[k] for k, t in teste.items() if k != "dottorando")
    attrezz = (herd_pers + supp) * (1 - LAMBDA_HE) / LAMBDA_HE  # non scalate dalle paghe
    return {"herd_mln": (herd_pers_w + W * supp + attrezz) / 1e6,
            "budget_mln": (full_pers_w + W * supp + attrezz) / 1e6}


def simula(dens_target: float, W: float = 1.0, q_ric: float = 0.0) -> pd.DataFrame:
    global QUOTA_RIC_UNI
    _salva_q, QUOTA_RIC_UNI = QUOTA_RIC_UNI, q_ric
    pd_in0 = _pd_in0()
    # Il flusso PhD è RICAVATO dal fabbisogno a valle dei DUE rami:
    #   - università: quanti postdoc servono per la densità target
    #   - EPR: rimpiazzo a organico costante (il GOVERD è già saturo)
    # e diviso per P1, perchè solo metà dei dottori prosegue.
    uni_in_tgt = dens_target * POP_100K / kappa(P2_TGT, PRECARI_ANNI)
    epr_in_tgt = _epr_in_tgt()
    # PAVIMENTO: il numero di dottorandi non scende mai sotto quello odierno. Se il
    # fabbisogno accademico ne richiede meno, l'eccedenza NON viene tagliata: esce
    # verso destinazioni non accademiche (imprese, PA), che il modello non simula ma
    # ora contabilizza esplicitamente.
    pd_in_tgt = max(pd_in0, (uni_in_tgt + epr_in_tgt) / P1)
    s = _init_stato(pd_in0)
    base = _spesa(s, 1.0, 1.0)
    base_e = _spesa_epr(s, 1.0, COSTO_EPR_PREC_OGGI)

    righe = []
    for k in range(ORIZZONTE + 1):
        anno = ANNO0 + k
        fte = _fte(s)
        fte_tot = sum(fte.values())
        # entrambe le leve salariali sono rampate come le altre
        Wk = _ramp(k, 1.0, W)
        sp = _spesa(s, Wk, _ramp(k, 1.0, W_PHD))
        # il costo del precario EPR sale comunque: la L.79/2022 abolisce gli assegni
        cp = _ramp(k, COSTO_EPR_PREC_OGGI, COSTO_EPR_PREC_TGT)
        spe = _spesa_epr(s, Wk, cp)
        pub = (sp["herd_mln"] + spe["goverd_mln"]) / PIL_MLN * 100   # HERD + GOVERD
        # --- flussi dell'anno (servono anche come diagnostica in tabella) ---
        P2 = _ramp(k, P2_HIST, P2_TGT)
        pd_in = _ramp(k, pd_in0, pd_in_tgt)
        uni_in_k = _ramp(k, _uni_in0(), uni_in_tgt)
        epr_in_k = _ramp(k, _epr_in0(), epr_in_tgt)
        serve, escono = uni_in_k + epr_in_k, s.phd[-1]
        prosegue = min(serve, escono)
        scala = prosegue / serve if serve > 0 else 0.0
        uni_in, epr_in = uni_in_k * scala, epr_in_k * scala
        p1_eff = prosegue / escono if escono > 0 else 0.0
        righe.append({
            "phd_prosegue": prosegue,
            "phd_fuori_accademia": max(0.0, escono - prosegue),
            "P1_effettivo": p1_eff,
            "anno": anno,
            # densità a popolazione VARIABILE (SSP2): è la grandezza che si confronta
            # con gli altri paesi nell'anno. A organico costante sale, perchè il
            # denominatore scende.
            "densita": fte_tot / pop_100k(anno),
            "pop_mln": pop_100k(anno) / 10.0,
            # ... e a popolazione FISSA 2026, per isolare l'effetto organico da quello
            # demografico: la differenza fra le due colonne è tutta demografia.
            "densita_pop2026": fte_tot / pop_100k(ANNO0),
            "quota_docente": (fte["docente"] + fte["ric_uni"]) / fte_tot,
            "ruolo_teste": sum(s.perm) + sum(s.perm_ric),
            "ric_uni_teste": sum(s.perm_ric),
            "phd_teste": sum(s.phd),
            "postdoc_teste": s.precari,
            "rtt_teste": sum(s.rtt),
            "precari_teste": s.precari + sum(s.rtt),
            "pensionamenti": s.perm[-1] + s.perm_ric[-1],
            "W_paghe": Wk,
            "borsa_mese": BORSA_OGGI * _ramp(k, 1.0, W_PHD),
            "HERD_%PIL": sp["herd_mln"] / PIL_MLN * 100,
            "GOVERD_%PIL": spe["goverd_mln"] / PIL_MLN * 100,
            "pubblico_%PIL": (sp["budget_mln"] + spe["budget_epr_mln"]) / PIL_MLN * 100,
            "RS_pubblica_%PIL": pub,
            "BERD_%PIL": _berd(pub),
            "GERD_%PIL": pub + _berd(pub),
            "spesa_RS_mln": sp["herd_mln"] + spe["goverd_mln"],
            # PROXY FFO: maggior fabbisogno annuo a carico dello Stato per il ramo
            # universitario. NON è l'FFO (che finanzia anche TA, edilizia, servizi
            # agli studenti): è l'incremento di costo del personale di ricerca.
            "dStato_univ_mld": (sp["budget_mln"] - base["budget_mln"]) / 1000,
            "dStato_epr_mld": (spe["budget_epr_mln"] - base_e["budget_epr_mln"]) / 1000,
            "epr_ruolo": sum(s.epr_ruolo),
            "epr_precari": sum(s.epr_prec),
            "densita_epr": _fte_epr(s) / POP_100K,
            "dHERD_%PIL": (sp["herd_mln"] - base["herd_mln"]) / PIL_MLN * 100,
            "dBudget_%PIL": (sp["budget_mln"] - base["budget_mln"]) / PIL_MLN * 100,
            "dGOVERD_%PIL": (spe["goverd_mln"] - base_e["goverd_mln"]) / PIL_MLN * 100,
            "dBudgetEPR_%PIL": (spe["budget_epr_mln"] - base_e["budget_epr_mln"]) / PIL_MLN * 100,
            # livelli ASSOLUTI di spesa, non incrementi: servono al grafico di spesa
            # pubblica, che parte dal valore 2026 invece che da zero.
            "budget_univ_mld": sp["budget_mln"] / 1000,
            "budget_epr_mld": spe["budget_epr_mln"] / 1000,
        })
        # --- avanzamento di un anno ---
        adv, ex = P2 / PRECARI_ANNI, (1 - P2) / PRECARI_ANNI
        stabil = adv * s.precari                     # postdoc -> RTT
        rtt_out = s.rtt[-1] * S_RTT_PERM             # RTT -> ruolo
        epr_stab = s.epr_prec[-1] * P2_EPR           # contratto di ricerca -> Madia
        s.phd = [pd_in] + s.phd[:-1]
        s.precari = s.precari + uni_in - stabil - ex * s.precari
        s.rtt = [stabil] + s.rtt[:-1]
        qr = _ramp(k, 0.0, QUOTA_RIC_UNI)            # conversione per ricambio
        s.perm = [rtt_out * (1 - qr)] + s.perm[:-1]   # età 67 -> pensione
        s.perm_ric = [rtt_out * qr] + s.perm_ric[:-1]
        s.epr_prec = [epr_in] + s.epr_prec[:-1]
        s.epr_ruolo = [epr_stab] + s.epr_ruolo[:-1]
    QUOTA_RIC_UNI = _salva_q
    return pd.DataFrame(righe)


# ============================ ANALISI =======================================
def _tempo_a_regime(df: pd.DataFrame, target: float, soglia: float = 0.90) -> int:
    # confronto col target a POPOLAZIONE FISSA: il target è un obiettivo di organico
    # espresso per 100k abitanti del 2026. Usando la densità SSP2 il traguardo
    # risulterebbe raggiunto in anticipo solo perchè cala il denominatore.
    d0 = df["densita_pop2026"].iloc[0]
    traguardo = d0 + soglia * (target - d0)
    ok = df[df["densita_pop2026"] >= traguardo]
    return int(ok["anno"].iloc[0]) if len(ok) else -1


def _herd_base() -> float:
    """HERD 'oggi' ricostruito dal modello, % PIL (test di calibrazione vs ISTAT 0,36)."""
    return _spesa(_init_stato(_pd_in0()), 1.0, 1.0)["herd_mln"] / PIL_MLN * 100


def _herd_assoluto(df: pd.DataFrame) -> float:
    return _herd_base() + df["dHERD_%PIL"].iloc[-1]


def _berd(pubblico: float) -> float:
    """BERD implicito. IPOTESI, non risultato: il privato avanza verso la sua quota
    del 3% in proporzione all'avanzamento della componente pubblica verso il suo
    punto di riferimento. A pubblico = HERD_RIF+GOVERD_RIF, il 3% è raggiunto."""
    pub0 = HERD_OGGI + GOVERD_OGGI
    pub_rif = HERD_RIF + GOVERD_RIF
    berd0 = GERD_OGGI - pub0
    berd_tgt = GERD_TGT - pub_rif
    if pub_rif <= pub0:
        return berd0
    # SATURA a 1: oltre il punto di ancoraggio l'interpolazione non ha significato,
    # e con una leva di ~4:1 farebbe esplodere il GERD ben oltre il 3%.
    avanz = min(1.0, (pubblico - pub0) / (pub_rif - pub0))
    berd = berd0 + avanz * (berd_tgt - berd0)
    # TETTO: il GERD non supera mai il 3%. Se il pubblico sfora l'ancora, è il
    # privato a non doversi più muovere, non il totale a gonfiarsi.
    return max(0.0, min(berd, GERD_TGT - pubblico))


def _goverd_base() -> float:
    """GOVERD 'oggi' ricostruito dal modello, % PIL."""
    s = _init_stato(_pd_in0())
    return _spesa_epr(s, 1.0, COSTO_EPR_PREC_OGGI)["goverd_mln"] / PIL_MLN * 100


def _ric_epr_oggi() -> float:
    """Costo-ricerca (alpha-pesato) dei ricercatori EPR oggi, in euro."""
    s = _init_stato(_pd_in0())
    return (sum(s.epr_ruolo) * COSTO_EPR_RUOLO
            + sum(s.epr_prec) * COSTO_EPR_PREC_OGGI) * ALPHA_EPR


def _calibra_overhead_epr() -> tuple[float, float]:
    """Scompone il GOVERD osservato in (supporto, attrezzature) come RESIDUI ASSOLUTI
    rispetto al costo-ricerca dei ricercatori. Grande, perchè gli EPR sono
    infrastruttura-intensivi (acceleratori, spazio, grandi impianti)."""
    tot = GOVERD_OGGI / 100 * PIL_MLN * 1e6
    lavoro = tot * LAMBDA_GOV
    return max(0.0, lavoro - _ric_epr_oggi()), tot * (1 - LAMBDA_GOV)


def _goverd_di(ruolo: float, prec: float, c_ruolo: float, c_prec: float) -> float:
    """GOVERD (% PIL) di un organico EPR arbitrario, a overhead fisso."""
    ric = (ruolo * c_ruolo + prec * c_prec) * ALPHA_EPR
    return (ric + OVH_EPR_SUPP + OVH_EPR_ATTR) / 1e6 / PIL_MLN * 100


def _tabella_stabilizzazione() -> pd.DataFrame:
    """Costo della stabilizzazione EPR a organico costante (25.000 ricercatori),
    isolando l'effetto-stabilizzazione da quello-espansione."""
    tot = EPR_RUOLO_OGGI + EPR_PRECARI_OGGI
    intake = tot / (D_PREC_EPR + PERM_DUR_EPR)      # regime a organico invariato
    righe = [
        ("oggi (mix 50% assegni)", EPR_RUOLO_OGGI, EPR_PRECARI_OGGI,
         COSTO_EPR_RUOLO, COSTO_EPR_PREC_OGGI),
        ("assegni -> contratti di ricerca (L.79/2022, senza stabilizzare)",
         EPR_RUOLO_OGGI, EPR_PRECARI_OGGI, COSTO_EPR_RUOLO, COSTO_EPR_PREC_TGT),
        ("stabilizzazione oggi (i 6.000 entrano al III, 0-2 anni)",
         EPR_RUOLO_OGGI + EPR_PRECARI_OGGI, 0.0,
         (EPR_RUOLO_OGGI * COSTO_EPR_RUOLO + EPR_PRECARI_OGGI * COSTO_EPR_INGRESSO) / tot, 0.0),
        (f"a regime: {D_PREC_EPR}a contratto -> Madia -> carriera fino al II",
         intake * PERM_DUR_EPR, intake * D_PREC_EPR, COSTO_EPR_RUOLO, COSTO_EPR_PREC_TGT),
    ]
    out = []
    for nome, r, p, cr, cp in righe:
        g = _goverd_di(r, p, cr, cp)
        out.append({"scenario": nome, "ruolo": round(r), "precari": round(p),
                    "GOVERD_%PIL": round(g, 3),
                    "d_mln": round((g - GOVERD_OGGI) / 100 * PIL_MLN),
                    "d_budget_mln": round((r * cr + p * cp
                                           - EPR_RUOLO_OGGI * COSTO_EPR_RUOLO
                                           - EPR_PRECARI_OGGI * COSTO_EPR_PREC_OGGI) / 1e6)})
    return pd.DataFrame(out)


def _calibra_supporto() -> float:
    """Overhead di personale di supporto che porta l'HERD 'oggi' del modello sul dato
    ISTAT. è un RESIDUO: assorbe tutto cio' che il modello non conta esplicitamente
    (tecnici, amministrativi di ricerca), non solo lo stipendio di un tecnico."""
    global SUPPORTO
    salva, SUPPORTO = SUPPORTO, 0.0
    b0 = _herd_base()
    SUPPORTO = 1.0
    b1 = _herd_base()
    SUPPORTO = salva
    if b1 <= b0:
        return 0.0
    return max(0.0, (HERD_OGGI - b0) / (b1 - b0))


# ============================ REPORT 2026-2050 ==============================
# Palette: primi tre slot della palette di riferimento (validati all-pairs).
PAL = {"ERA_PPP_ric": "#2a78d6", "ERA": "#eb6834", "FLC": "#1baf7a"}
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#898781", "#e1e0d9"

# Rampa dello stack di composizione. Le fasce NON sono categorie indipendenti ma
# STADI ORDINATI di carriera: una sola tinta a luminosità decrescente verso
# l'alto, non tinte diverse. Volutamente estranea a PAL: i colori degli scenari
# restano riservati alla linea di totale in cima allo stack.
# DUE rampe, non una da sette passi: università e EPR sono settori contabili
# distinti (HERD vs GOVERD). La TINTA dice il settore, la LUMINOSITà lo stadio di
# carriera dentro il settore. Le due famiglie sono INTERLACCIATE, perchè lo stack
# è ordinato per stadio: postdoc EPR accanto ai postdoc universitari, ricercatori
# EPR accanto ai ricercatori universitari. Un'unica rampa a 7 passi non starebbe nei
# vincoli (servirebbero 0,36 di escursione in L tenendo l'estremo chiaro leggibile).
# Verificato con validate_palette.py sulle coppie ADIACENTI nell'ordine di impilamento,
# le sole che si toccano nel disegno: CVD peggiore 9.7 (Ricercatori EPR / RTT), sopra la
# soglia di 8. A vista normale le due coppie più debolli sono Professori / Ricercatori
# univ. a 10.9 e Ricercatori EPR / RTT a 12.4, sotto la soglia categoriale di 15 - che
# una rampa a una tinta non puo' rispettare per costruzione. Per questo ogni fascia
# porta l'etichetta scritta dentro: l'identità non è mai solo-colore.
STACK = [("phd_teste",       "Dottorandi",          "#3f2560"),   # viola = università
         ("postdoc_teste",   "Postdoc univ.",       "#623f88"),
         ("epr_precari",     "Postdoc EPR",         "#720a3b"),   # cremisi = EPR
         ("rtt_teste",       "RTT",                 "#825ba9"),
         ("epr_ruolo",       "Ricercatori EPR",     "#ae3970"),
         ("ric_uni_teste",   "Ricercatori univ.",   "#a17ec6"),
         ("prof_teste",      "Professori (PO/PA)",  "#c0a3da")]

# Grafico di spesa: DUE ENTITà CATEGORIALI (rami di bilancio), non stadi ordinati,
# quindi due tinte e non una rampa. Palette distinta da STACK perchè l'oggetto è
# diverso: li' sono persone, qui sono euro.
# Verificato sulle coppie che si TOCCANO nel disegno: i due riempimenti fra loro stanno
# a ΔE 17.1 a vista normale e 14.5 in CVD; la linea di totale (colore dello scenario)
# contro la fascia EPR che le sta sotto, 21.8 col verde, 27.0 col blu, 27.9 con
# l'arancio. Il test all-pairs segnala il verde di PAL contro il verde università
# (8.5), ma quelle due marche non sono mai adiacenti: l'università è la fascia in
# basso, la linea di totale sta in cima, separate dall'intera banda EPR.
# Quarto campo: la stessa dizione per esteso, ma mandata a capo, per la scrittura
# DENTRO la fascia. Su una riga non entrerebbe nella finestra piatta disponibile.
SPESA = [("dStato_univ_mld", "Università", "#249F2F", "Università"),
         ("dStato_epr_mld",  "Enti pubblici di ricerca", "#4f6410",
          "Enti pubblici\ndi ricerca")]

RIGHE_TAB = [
    ("Densità università (FTE/100k)",      "densita",        1),
    ("Personale di ruolo PO/PA+ric. (teste)", "ruolo_teste", 0),
    ("RTT (teste)",                       "rtt_teste",      0),
    ("Postdoc università (teste)",        "postdoc_teste",  0),
    ("Dottorandi (teste)",                "phd_teste",      0),
    ("Dottori che proseguono/anno",       "phd_prosegue",   0),
    ("Dottori fuori accademia/anno",      "phd_fuori_accademia", 0),
    ("P1 effettivo (prosegue/dottori)",   "P1_effettivo",   2),
    ("Pensionamenti/anno",                "pensionamenti",  0),
    ("EPR di ruolo (teste)",              "epr_ruolo",      0),
    ("EPR precari (teste)",               "epr_precari",    0),
    ("Densità EPR (FTE/100k)",             "densita_epr",    1),
    ("Moltiplicatore paghe W",            "W_paghe",        2),
    ("Borsa PhD (EUR/mese netti)",        "borsa_mese",     0),
    ("HERD (% PIL)",                      "HERD_%PIL",      3),
    ("GOVERD (% PIL)",                    "GOVERD_%PIL",    3),
    ("R&S pubblica HERD+GOVERD (% PIL)",  "RS_pubblica_%PIL", 3),
    ("BERD imprese - IPOTESI (% PIL)",    "BERD_%PIL",      3),
    ("GERD totale (% PIL)",               "GERD_%PIL",      3),
    ("Spesa R&S pubblica (mln EUR)",      "spesa_RS_mln",   0),
    ("Budget pubblico tot. (% PIL)",      "pubblico_%PIL",  3),
]


def tabella_scenario(df: pd.DataFrame, anni: list[int]) -> pd.DataFrame:
    """Trasposta: una riga per variabile, una colonna per anno."""
    v = df[df["anno"].isin(anni)].set_index("anno")
    out = {}
    for etichetta, col, dec in RIGHE_TAB:
        out[etichetta] = [f"{v.loc[a, col]:,.{dec}f}" for a in anni]
    return pd.DataFrame(out, index=anni).T


def grafici(dfs: dict[str, pd.DataFrame], fine: int, path: str,
            titolo: str | None = None) -> None:
    pann = [("densita", "Densità università (FTE/100k)"),
            # 'ruolo' = PO/PA + ricercatori univ.: negli scenari con la quota-ricercatori
            # non sono tutti docenti, quindi l'etichetta non dice "docenti"
            ("ruolo_teste", "Personale di ruolo, PO/PA + ric. (teste)"),
            ("postdoc_teste", "Postdoc università (teste)"),
            ("rtt_teste", "RTT (teste)"),
            ("phd_fuori_accademia", "Dottori/anno fuori accademia (eccedenza)"),
            ("epr_ruolo", "EPR di ruolo (teste)"),
            ("W_paghe", "Moltiplicatore paghe W"),
            ("HERD_%PIL", "HERD (% PIL)"),
            ("GOVERD_%PIL", "GOVERD (% PIL)")]
    fig, axes = plt.subplots(3, 3, figsize=(13.5, 10.5), facecolor="#fcfcfb")
    for ax, (col, tit) in zip(axes.ravel(), pann):
        # spessore decrescente: dove le serie COINCIDONO (EPR, W) restano tutte
        # visibili come bande concentriche invece di nascondersi a vicenda
        for sp, (nome, df) in zip((3.4, 2.2, 1.3), dfs.items()):
            d = df[df["anno"] <= fine]
            ax.plot(d["anno"], d[col], lw=sp, color=PAL[nome],
                    label=nome.replace("_", " "), solid_capstyle="round")
        # la nota "identico" ha senso solo se ci sono più scenari da confrontare
        coincide = len(dfs) > 1 and all(
            np.allclose(df[df["anno"] <= fine][col],
                        list(dfs.values())[0][lambda x: x["anno"] <= fine][col])
            for df in dfs.values())
        ax.set_title(tit + (f"  (identico nei {len(dfs)} scenari)" if coincide else ""),
                     fontsize=10, color=INK, loc="left", pad=8)
        ax.yaxis.set_major_formatter(
            plt.FuncFormatter(lambda v, _: f"{v:,.0f}" if abs(v) >= 1000 else f"{v:g}"))
        if col == "GOVERD_%PIL":                    # riferimento: obiettivo dichiarato
            ax.axhline(GOVERD_TGT, lw=1.2, ls=(0, (4, 3)), color=MUTED)
            ax.annotate(f"obiettivo {GOVERD_TGT:g}%", (ANNO0 + 1, GOVERD_TGT),
                        textcoords="offset points", xytext=(0, -11),
                        fontsize=8, color=INK2)
        if col == "HERD_%PIL":
            ax.axhline(HERD_TGT, lw=1.2, ls=(0, (4, 3)), color=MUTED)
            ax.annotate(f"obiettivo ERA {HERD_TGT:g}%", (ANNO0 + 1, HERD_TGT),
                        textcoords="offset points", xytext=(0, -11),
                        fontsize=8, color=INK2)
        ax.grid(True, lw=0.6, color=GRID)
        ax.set_axisbelow(True)
        ax.tick_params(labelsize=8, colors=MUTED, length=0)
        for lato in ("top", "right"):
            ax.spines[lato].set_visible(False)
        for lato in ("left", "bottom"):
            ax.spines[lato].set_color("#c3c2b7")
        if col in ("densita", "ruolo_teste", "postdoc_teste", "rtt_teste",
                   "phd_fuori_accademia", "epr_ruolo", "phd_teste"):
            ax.set_ylim(bottom=0)      # conteggi di persone: baseline sempre a zero
        ax.set_facecolor("#fcfcfb")
    # una sola legenda per l'intera figura: l'identità non è mai solo-colore.
    # Con una serie sola la legenda non serve: è il titolo a nominarla.
    if len(dfs) > 1:
        axes[0][0].legend(fontsize=8.5, frameon=False, labelcolor=INK2, loc="upper left")
    fig.suptitle(titolo or f"Transizione {ANNO0}-{fine}: università ed EPR a confronto",
                 fontsize=12.5, color=INK, x=0.008, ha="left", y=0.995)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(path, dpi=140, facecolor="#fcfcfb")
    plt.close(fig)


def grafico_ffo(dfs: dict[str, pd.DataFrame], fine: int, path: str,
                titolo: str | None = None) -> None:
    """Maggior fabbisogno annuo a carico dello Stato, in miliardi. PROXY dell'FFO
    aggiuntivo: il modello non ha l'FFO come voce di bilancio (vedi README)."""
    pann = [("dStato_univ_mld", "Università (mld EUR/anno)"),
            ("dStato_epr_mld", "EPR - dotazione aggiuntiva (mld EUR/anno)"),
            (None, "Totale ricerca pubblica (mld EUR/anno)")]
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.4), facecolor="#fcfcfb")
    for ax, (col, tit) in zip(axes, pann):
        for sp, (nome, df) in zip((3.4, 2.2, 1.3), dfs.items()):
            d = df[df["anno"] <= fine]
            y = (d["dStato_univ_mld"] + d["dStato_epr_mld"]) if col is None else d[col]
            ax.plot(d["anno"], y, lw=sp, color=PAL[nome],
                    label=nome.replace("_", " "), solid_capstyle="round")
            ax.annotate(f"{y.iloc[-1]:.1f}", (d["anno"].iloc[-1], y.iloc[-1]),
                        textcoords="offset points", xytext=(4, 0), fontsize=8.5,
                        color=INK2, va="center")
        ax.axhline(0, lw=1.0, color="#c3c2b7")
        ax.set_title(tit, fontsize=10, color=INK, loc="left", pad=8)
        ax.grid(True, lw=0.6, color=GRID)
        ax.set_axisbelow(True)
        ax.tick_params(labelsize=8, colors=MUTED, length=0)
        for lato in ("top", "right"):
            ax.spines[lato].set_visible(False)
        for lato in ("left", "bottom"):
            ax.spines[lato].set_color("#c3c2b7")
        ax.set_facecolor("#fcfcfb")
        ax.margins(x=0.10)
    if len(dfs) > 1:      # con una serie sola è il titolo a nominarla
        axes[0].legend(fontsize=8.5, frameon=False, labelcolor=INK2, loc="upper left")
    fig.suptitle(titolo or "Maggior fabbisogno annuo rispetto a oggi (EUR2026 costanti)",
                 fontsize=12.5, color=INK, x=0.006, ha="left", y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(path, dpi=140, facecolor="#fcfcfb")
    plt.close(fig)


def _ink_su(hex_fondo: str) -> str:
    """Inchiostro per un'etichetta scritta DENTRO una fascia colorata: chiaro sui
    riempimenti scuri, scuro su quelli chiari. Deciso dalla luminanza relativa della
    fascia, non dalla sua posizione nello stack: con due rampe la posizione non dice
    più quanto è scura. Soglia 0,35 = punto in cui i due contrasti si pareggiano."""
    r, g, b = (int(hex_fondo[i:i + 2], 16) / 255 for i in (1, 3, 5))
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in (r, g, b)]
    lum = 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]
    return "#fcfcfb" if lum < 0.35 else INK


def _posa_etichetta(anni: np.ndarray, basso: np.ndarray, alto: np.ndarray,
                    ytop: float, nchar: int, soglia: float) -> tuple[float, float] | None:
    """Dove scrivere un'etichetta DENTRO una fascia di uno stackplot, oppure None se
    non ci sta da nessuna parte.

    Non basta il punto più SPESSO: il testo si estende in orizzontale, e dove la
    fascia sale o scende le sue estremità escono - sopra la linea di totale il fondo
    è pagina, e l'inchiostro chiaro diventa invisibile. Quindi si massimizza lo
    spessore UTILE: l'intersezione della fascia su una finestra larga quanto il testo.
    Restituisce (anno, y) del centro."""
    n = len(anni)
    # mezza larghezza del testo in anni: ~0,46 anni per carattere a fontsize 8.5 su
    # un pannello tipico di questa figura, con un minimo di 3 per le etichette corte.
    # Il margine è volutamente generoso: serve anche a tenere il testo staccato dai
    # bordi del pannello, non solo dentro la fascia.
    w = max(3, int(nchar * 0.46))
    if n <= 2 * w + 1:
        return None
    # i centri candidati stanno a distanza >= w dai bordi: la finestra è sempre piena
    # (altrimenti ai bordi si accorcia, l'intersezione risulta più larga e vince
    # sempre l'estremità, mandando il testo fuori dal pannello)
    best = (-1.0, w, 0.0)
    for i in range(w, n - w):
        y_lo, y_hi = basso[i - w:i + w + 1].max(), alto[i - w:i + w + 1].min()
        if y_hi - y_lo > best[0]:
            best = (y_hi - y_lo, i, (y_lo + y_hi) / 2)
    if best[0] < soglia * ytop:
        return None
    return anni[best[1]], best[2]


def _posa_ripiego(anni: np.ndarray, basso: np.ndarray, alto: np.ndarray,
                  nchar: int) -> tuple[float, float]:
    """Posizione per una fascia TROPPO SOTTILE per contenere il suo testo: il punto più
    spesso, e il testo sborderà sulle fasce vicine. Serve quando la legenda non c'è e
    ogni fascia deve comunque essere nominata; la leggibilità la garantisce l'alone,
    non lo spessore (vedi _scrivi_in_fascia)."""
    # stesso margine dai bordi di _posa_etichetta, cosi' il testo non tocca le cornici;
    # cambia solo il criterio: spessore grezzo invece dell'intersezione su finestra,
    # perchè qui l'intersezione è comunque troppo piccola per contenere il testo
    w = max(3, int(nchar * 0.46)) + 1
    n = len(anni)
    a = min(w, n - 1)
    b = max(n - w, a + 1)
    spess = alto - basso
    i = a + int(np.argmax(spess[a:b]))
    return anni[i], (basso[i] + alto[i]) / 2


def _scrivi_in_fascia(ax, testo: str, posa: tuple[float, float], col: str,
                      sborda: bool) -> None:
    """Etichetta dentro una fascia. Se sborda sulle vicine le si mette un alone del
    colore della fascia stessa: il testo resta leggibile e si legge come appartenente
    alla striscia, non a quelle che invade."""
    eff = ([pe.withStroke(linewidth=2.6, foreground=col)] if sborda else None)
    ax.annotate(testo, posa, fontsize=8.5, ha="center", va="center",
                linespacing=1.35, color=_ink_su(col), path_effects=eff, zorder=7)


def grafico_stack(dfs: dict[str, pd.DataFrame], fine: int, path: str,
                  etich: dict[str, str] | None = None) -> None:
    """Composizione dell'organico della RICERCA PUBBLICA in teste, un pannello per
    scenario. Le fasce sono ordinate per STADIO DI CARRIERA e le due famiglie di colore
    si interlacciano: viola = università (dottorandi -> professori), cremisi = EPR
    (postdoc e ruolo). La tinta dice quindi il settore contabile - HERD contro GOVERD -
    e la luminosità lo stadio dentro il settore.
    La linea di totale in cima allo stack porta il colore che lo scenario ha in tutti
    gli altri grafici; la tratteggiata grafite è la densità FTE/100k sull'asse
    destro."""
    etich = etich or {n: n.replace("_", " ") for n in dfs}
    # con un solo pannello la larghezza minima è dettata dalla legenda, non dal grafico
    fig, axes = plt.subplots(1, len(dfs), figsize=(max(9.0, 5.2 * len(dfs)), 5.4),
                             facecolor="#fcfcfb", sharey=True)
    # asse y comune e IMPOSTO sul massimo degli scenari passati: con sharey
    # l'autoscale dell'ultimo pannello troncherebbe i totali più alti (ERA).
    def _tot(df: pd.DataFrame) -> pd.Series:
        d = df[df["anno"] <= fine]
        return (d["ruolo_teste"] + d["phd_teste"] + d["postdoc_teste"] + d["rtt_teste"]
                + d["epr_precari"] + d["epr_ruolo"])
    ytop = max(_tot(df).max() for df in dfs.values()) * 1.06
    for ax, (nome, df) in zip(np.atleast_1d(axes), dfs.items()):
        d = df[df["anno"] <= fine].copy()
        # 'docentè nel modello è la coorte PO/PA; i ricercatori universitari sono
        # una coorte distinta di ruolo, quindi vanno scorporati per non contarli due volte.
        d["prof_teste"] = d["ruolo_teste"] - d["ric_uni_teste"]
        # la fascia ricercatori compare SOLO negli scenari che prevedono la figura
        voci = [(c, lab, col) for c, lab, col in STACK if d[c].max() > 1.0]
        y = np.vstack([d[c].to_numpy() for c, _, _ in voci])
        cum = np.cumsum(y, axis=0)
        # linewidth su fondo pagina = il distacco di 2px fra le fasce contigue
        ax.stackplot(d["anno"], y, colors=[col for _, _, col in voci],
                     labels=[lab for _, lab, _ in voci],
                     edgecolor="#fcfcfb", linewidth=0.9)
        ax.plot(d["anno"], cum[-1], lw=2.4, color=PAL[nome],
                solid_capstyle="round", zorder=5)
        # Etichette dirette su OGNI fascia. Qui non è una scelta di stile: la legenda
        # delle fasce non c'è, quindi se una striscia resta senza nome non è
        # identificabile in nessun modo. Le fasce sottili prendono la posizione di
        # ripiego e l'alone, e il testo sborderà sulle vicine.
        basso = np.vstack([np.zeros(len(d)), cum[:-1]])
        anni = d["anno"].to_numpy()
        for k, (_, lab, col) in enumerate(voci):
            posa = _posa_etichetta(anni, basso[k], cum[k], ytop, len(lab), 0.042)
            _scrivi_in_fascia(ax, lab,
                              posa or _posa_ripiego(anni, basso[k], cum[k], len(lab)),
                              col, sborda=posa is None)
        ax.set_title(etich[nome], fontsize=10, color=INK, loc="left", pad=8)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:,.0f}"))
        ax.grid(True, axis="y", lw=0.6, color=GRID)
        ax.set_axisbelow(True)
        ax.tick_params(labelsize=8, colors=MUTED, length=0)
        for lato in ("top", "right"):
            ax.spines[lato].set_visible(False)
        for lato in ("left", "bottom"):
            ax.spines[lato].set_color("#c3c2b7")
        ax.set_facecolor("#fcfcfb")
        ax.set_xlim(d["anno"].iloc[0], d["anno"].iloc[-1])
        ax.set_ylim(0, ytop)
        # --- densita FTE/100k su asse DESTRO ---
        # Secondo asse y: normalmente da evitare, ma qui le due grandezze sono la
        # stessa cosa contata in due modi (posizioni vs FTE su popolazione SSP2), e il
        # confronto internazionale si fa in FTE/100k. Per non farlo passare per una
        # serie dello stack: grafite tratteggiata, nessuna tinta della palette, e
        # tacche e titolo dell'asse dello stesso inchiostro della linea.
        axr = ax.twinx()
        axr.plot(d["anno"], d["densita"], lw=1.8, ls=(0, (5, 2.5)), color=INK,
                 zorder=6, label="Densità FTE/100k (asse destro)")
        axr.set_ylim(0, max(df[df["anno"] <= fine]["densita"].max()
                            for df in dfs.values()) * 1.10)
        axr.tick_params(labelsize=8, colors=INK, length=0)
        axr.set_facecolor("none")
        for lato in ("top", "left", "bottom"):
            axr.spines[lato].set_visible(False)
        axr.spines["right"].set_color("#c3c2b7")
        # la scala destra è la stessa in tutti i pannelli: tacche e titolo solo
        # sull'ultimo, come fa sharey per l'asse sinistro
        if ax is np.atleast_1d(axes)[-1]:
            axr.set_ylabel("Densità FTE per 100k abitanti (pop. SSP2)", fontsize=8.5,
                           color=INK)
        else:
            axr.set_yticklabels([])
    ass = np.atleast_1d(axes)
    ass[0].set_ylabel("Numero Posizioni", fontsize=8.5, color=INK2)
    # In legenda SOLO la linea dell'asse destro: le fasce sono tutte nominate dentro il
    # grafico, quindi ripeterle in legenda sarebbe ridondante. La tratteggiata invece va
    # dichiarata, perchè è l'unica marca che legge su un'altra scala.
    h_fte = plt.Line2D([], [], lw=1.8, ls=(0, (5, 2.5)), color=INK)
    fig.legend([h_fte], ["Densità FTE per 100k abitanti (asse destro)"], fontsize=8.5,
               frameon=False, labelcolor=INK2, loc="lower center",
               bbox_to_anchor=(0.5, -0.005))
    fig.suptitle(f"Composizione dell'organico della ricerca pubblica, {ANNO0}-{fine} "
                 "(posizioni)", fontsize=12.5, color=INK, x=0.006, ha="left", y=0.995)
    # su una figura strettta (un pannello solo) il sottotitolo va su due righe, altrimenti
    # esce dal bordo destro
    stretta = fig.get_figwidth() < 12
    fig.text(0.006, 0.95, "Viola = università (spesa HERD), cremisi = enti pubblici di "
             "ricerca (spesa GOVERD);"
             + ("\n" if stretta else " ")
             + "le fasce sono ordinate per stadio di carriera. La linea in cima allo "
               "stack è il totale.",
             fontsize=8.5, color=INK2, ha="left", va="top", linespacing=1.4)
    fig.tight_layout(rect=(0, 0.055, 1, 0.90 if stretta else 0.92))
    fig.savefig(path, dpi=140, facecolor="#fcfcfb")
    plt.close(fig)


def grafico_spesa_stack(dfs: dict[str, pd.DataFrame], fine: int, path: str,
                        etich: dict[str, str] | None = None) -> None:
    """VARIAZIONE della spesa pubblica per la ricerca rispetto al 2026, con i due rami
    di bilancio impilati: università e EPR. Parte da zero per costruzione - il livello
    assoluto della baseline 2026 resta fuori dal grafico.
    (I livelli assoluti sono comunque nei CSV, colonne budget_univ_mld e
    budget_epr_mld, se serve rimetterli.)"""
    etich = etich or {n: n.replace("_", " ") for n in dfs}
    fig, axes = plt.subplots(1, len(dfs), figsize=(max(8.6, 5.0 * len(dfs)), 5.0),
                             facecolor="#fcfcfb", sharey=True)
    ytop = max((df[df["anno"] <= fine][[c for c, _, _, _ in SPESA]].sum(axis=1)).max()
               for df in dfs.values()) * 1.10
    for ax, (nome, df) in zip(np.atleast_1d(axes), dfs.items()):
        d = df[df["anno"] <= fine]
        y = np.vstack([d[c].to_numpy() for c, _, _, _ in SPESA])
        cum = np.cumsum(y, axis=0)
        ax.stackplot(d["anno"], y, colors=[col for _, _, col, _ in SPESA],
                     labels=[lab for _, lab, _, _ in SPESA],
                     edgecolor="#fcfcfb", linewidth=0.9)
        ax.plot(d["anno"], cum[-1], lw=2.4, color=PAL[nome],
                solid_capstyle="round", zorder=5)
        ax.axhline(0, lw=1.0, color="#c3c2b7", zorder=4)
        # il totale in nero: è un valore, e i valori portano inchiostro di testo, non
        # il colore della serie
        ax.annotate(f"+{cum[-1][-1]:.1f} mld", (d["anno"].iloc[-1], cum[-1][-1]),
                    textcoords="offset points", xytext=(-2, 8), fontsize=9.5,
                    color=INK, ha="right")
        # il picco non coincide col valore a regime: l'onda dei pensionamenti lo alza
        # per una ventina d'anni, ed è il numero che conta per la programmazione
        kp = int(np.argmax(cum[-1]))
        # if cum[-1][kp] > cum[-1][-1] * 1.03:
        #    ax.annotate(f"Picco +{cum[-1][kp]:.1f} ({d['anno'].iloc[kp]})",
        #                (d["anno"].iloc[kp], cum[-1][kp]), textcoords="offset points",
        #                xytext=(0, 9), fontsize=8.5, color=INK2, ha="center")
        # etichette dirette dentro le fasce, come nello stack dell'organico
        basso = np.vstack([np.zeros(len(d)), cum[:-1]])
        anni = d["anno"].to_numpy()
        for k, (_, _, col, dentro) in enumerate(SPESA):
            # la larghezza che conta è quella della riga più lunga, non del testo
            nch = max(len(r) for r in dentro.splitlines())
            posa = _posa_etichetta(anni, basso[k], cum[k], ytop, nch, 0.055)
            if posa is None:
                continue
            ax.annotate(dentro, posa, fontsize=8.5, ha="center", va="center",
                        linespacing=1.35, color=_ink_su(col))
        ax.set_title(etich[nome], fontsize=10, color=INK, loc="left", pad=8)
        ax.grid(True, axis="y", lw=0.6, color=GRID)
        ax.set_axisbelow(True)
        ax.tick_params(labelsize=8, colors=MUTED, length=0)
        for lato in ("top", "right"):
            ax.spines[lato].set_visible(False)
        for lato in ("left", "bottom"):
            ax.spines[lato].set_color("#c3c2b7")
        ax.set_facecolor("#fcfcfb")
        ax.set_xlim(d["anno"].iloc[0], d["anno"].iloc[-1])
        ax.set_ylim(0, ytop)
    ass = np.atleast_1d(axes)
    ass[0].set_ylabel("Mld EUR/anno in più rispetto ad oggi (EUR2026)",
                      fontsize=8.5, color=INK2)
    h, l = ass[0].get_legend_handles_labels()
    fig.legend(h[::-1], l[::-1], fontsize=8.5, frameon=False, labelcolor=INK2,
               loc="lower center", ncol=len(l), bbox_to_anchor=(0.5, -0.005))
    # titolo su due righe: una riga sola sfora la figura strettta a un pannello
    fig.suptitle(f"Fondi per la ricerca pubblica: variazione annua rispetto al {ANNO0}, "
                 "per ramo di bilancio",
                 fontsize=12.5, color=INK, x=0.006, ha="left", y=0.995)
    fig.text(0.006, 0.945, f"Parte da zero per costruzione: il livello della baseline "
             f"{ANNO0} resta fuori dal grafico. La linea in cima allo stack è il totale.",
             fontsize=8.5, color=INK2, ha="left", va="top")
    fig.tight_layout(rect=(0, 0.06, 1, 0.915))
    fig.savefig(path, dpi=140, facecolor="#fcfcfb")
    plt.close(fig)


def grafici_singolo(nome: str, dfs: dict[str, pd.DataFrame], fine: int, out: str,
                    etich: dict[str, str]) -> list[str]:
    """Gli stessi grafici, ma per UN SOLO scenario, su file separati. Utile per
    metterlo in una slide o in un documento senza il confronto a fianco: le serie
    degli altri due scenari, li', sono rumore."""
    solo = {nome: dfs[nome]}
    lab = etich.get(nome, nome.replace("_", " "))
    file = {"trend":  f"{out}/{nome}_trend.png",
            "ffo":    f"{out}/{nome}_ffo.png",
            "stack":  f"{out}/{nome}_organico.png",
            "spesa":  f"{out}/{nome}_spesa.png"}
    grafici(solo, fine, file["trend"],
            titolo=f"Scenario {lab}: transizione {ANNO0}-{fine}")
    grafico_ffo(solo, fine, file["ffo"],
                titolo=f"Scenario {lab}: maggior fabbisogno annuo rispetto a oggi "
                       "(EUR2026 costanti)")
    grafico_stack(solo, fine, file["stack"], etich)
    grafico_spesa_stack(solo, fine, file["spesa"], etich)
    return list(file.values())


def main() -> None:
    global P2_HIST, PERM_OGGI, PRECARI_ANNI, RAMP, OUT
    global P1, P2_TGT, STAB_PHD, PHD_IN_FTE, W_PHD, BORSA_TGT, SUPPORTO, D_RTT
    global QUOTA_RIC_UNI, UPLIFT_PPP
    global OVH_EPR_SUPP, OVH_EPR_ATTR, EPR_PRECARI_OGGI, EPR_RUOLO_OGGI, EPR_RICERC_OGGI, COSTO_EPR_RUOLO
    ap = argparse.ArgumentParser(description="Transizione FTE verso il regime cattedre.")
    ap.add_argument("--out", type=str, default=OUT,
                    help="cartella di output per png/csv (default: cartella dello script)")
    ap.add_argument("--uplift-ppp", type=float, default=UPLIFT_PPP,
                    help=f"moltiplicatore paghe della parità PPP (default {UPLIFT_PPP:.3f} = "
                         "media top-5 / Italia sul reddito dei dottori di ricerca a parità "
                         f"di potere d'acquisto, dati ReICO (EC+OCSE); {UPLIFT_PPP_CARSA06:.3f} "
                         f"per lo stesso rapporto sullo studio CARSA 2006, {UPLIFT_PPP_PLI24} "
                         "per quest'ultimo col solo deflatore riportato al PLI 2024)")
    ap.add_argument("--quota-ric-uni", type=float, default=QUOTA_RIC_UNI,
                    help="quota del ruolo universitario con profilo ricercatore "
                         "(alpha 0.75, stipendio EPR) invece che docente PO/PA")
    ap.add_argument("--rtt-anni", type=int, default=D_RTT,
                    help=f"durata del contratto RTT in anni (default {D_RTT}, L.79/2022; "
                         "usa 3 per l'ex RTD-B = tenure più rapida possibile)")
    ap.add_argument("--p2-tgt", type=float, default=P2_TGT,
                    help="postdoc->RTT a regime (default 1.0 = nessun imbuto interno; "
                         "P1 viene ricavato di conseguenza dal vincolo di stabilizzazione)")
    ap.add_argument("--stab-phd", type=float, default=STAB_PHD,
                    help="quota di dottori stabilizzati al ruolo = P1*P2 (default 0.50)")
    ap.add_argument("--borsa-tgt", type=float, default=BORSA_TGT,
                    help=f"borsa PhD target, netto mensile (default {BORSA_TGT:.0f}; oggi {BORSA_OGGI:.0f})")
    ap.add_argument("--costo-phd", type=float, default=COSTO["dottorando"],
                    help="costo lordo ente di un dottorando oggi (default 22000)")
    ap.add_argument("--epr-precari", type=int, default=EPR_PRECARI_OGGI,
                    help=f"precari EPR oggi (default {EPR_PRECARI_OGGI:,})")
    ap.add_argument("--epr-ruolo", type=int, default=EPR_RUOLO_OGGI,
                    help=f"ricercatori EPR di ruolo oggi (default {EPR_RUOLO_OGGI:,})")
    ap.add_argument("--costo-epr-ruolo", type=float, default=COSTO_EPR_RUOLO,
                    help=f"costo ente ricercatore EPR di ruolo (default {COSTO_EPR_RUOLO:,})")
    ap.add_argument("--supporto", type=float, default=None,
                    help="overhead tecnici/amministrativi sul costo-ricerca del personale "
                         f"(default: auto-calibrato per riprodurre HERD {HERD_OGGI}%% PIL; "
                         "usa 0 per disattivarlo)")
    ap.add_argument("--phd-in-fte", action=argparse.BooleanOptionalAction, default=PHD_IN_FTE,
                    help="i dottorandi contano negli FTE-ricerca (default: si', convenzione Frascati). "
                         "Il loro COSTO entra in HERD/budget in entrambi i casi.")
    ap.add_argument("--p2-hist", type=float, default=P2_HIST,
                    help="stabilizzazione storica (default 0.10)")
    ap.add_argument("--perm-oggi", type=int, default=PERM_OGGI,
                    help="teste di ruolo oggi (default 60000)")
    ap.add_argument("--precari-anni", type=float, default=PRECARI_ANNI,
                    help="permanenza media nel precariato, anni (default 3)")
    ap.add_argument("--ramp", type=int, default=RAMP,
                    help=f"anni di rampa delle leve, tutte (default {RAMP} -> a regime dal {ANNO0 + RAMP})")
    a = ap.parse_args()
    P2_HIST, PERM_OGGI, PRECARI_ANNI, RAMP = a.p2_hist, a.perm_oggi, a.precari_anni, a.ramp
    STAB_PHD, PHD_IN_FTE, D_RTT = a.stab_phd, a.phd_in_fte, a.rtt_anni
    EPR_PRECARI_OGGI, EPR_RUOLO_OGGI = a.epr_precari, a.epr_ruolo
    EPR_RICERC_OGGI = EPR_PRECARI_OGGI + EPR_RUOLO_OGGI
    COSTO_EPR_RUOLO, P2_TGT = a.costo_epr_ruolo, a.p2_tgt
    QUOTA_RIC_UNI, UPLIFT_PPP = a.quota_ric_uni, a.uplift_ppp
    # Vincolo di stabilizzazione. Con P2_univ = P2_EPR = 1 (nessun imbuto interno)
    # si riduce a P1 = STAB_PHD: tutta la selezione è all'uscita dal dottorato.
    # (Con P2_univ < 1 l'EPR, che stabilizza al 100%, alza di poco la media: è un
    # flusso di rimpiazzo piccolo, quindi si approssima col solo ramo universitario.)
    P1 = min(1.0, STAB_PHD / P2_TGT)
    BORSA_TGT = a.borsa_tgt
    W_PHD = BORSA_TGT / BORSA_OGGI
    COSTO["dottorando"] = a.costo_phd
    OUT = a.out
    os.makedirs(OUT, exist_ok=True)
    SUPPORTO = _calibra_supporto() if a.supporto is None else a.supporto
    OVH_EPR_SUPP, OVH_EPR_ATTR = _calibra_overhead_epr()

    base_herd = _herd_base()
    quota_reg = regime_shares(PRECARI_ANNI)["docente"]
    phd_oggi = _pd_in0() * D_PHD

    # la quota-ricercatori è una leva solo del terzo scenario: FLC ed ERA restano
    # i baseline tutto-cattedre, così il confronto isola l'effetto della riforma.
    _q = QUOTA_RIC_UNI
    QUOTA_RIC_UNI = 0.0
    d_era = densita_iso_herd(HERD_TGT, 1.0, PRECARI_ANNI, W_PHD)
    QUOTA_RIC_UNI = _q
    d_ppp = densita_iso_herd(HERD_TGT, UPLIFT_PPP, PRECARI_ANNI, W_PHD)
    QUOTA_RIC_UNI = 0.0
    scen = {
        "FLC":          (140.0, 1.0, 0.0),
        "ERA":          (d_era, 1.0, 0.0),
        "ERA_PPP_ric":  (d_ppp, UPLIFT_PPP, _q),
    }
    dfs = {nome: simula(t, W, q) for nome, (t, W, q) in scen.items()}

    print("#" * 82)
    print("# TRANSIZIONE DINAMICA - stato stazionario da imbuto")
    print(f"# param: P2_hist={P2_HIST} | ruolo_oggi={PERM_OGGI:,} | precari_anni={PRECARI_ANNI} "
          f"| ramp={RAMP}a")
    print(f"# leve (P2, flusso PhD, paghe W, borsa W_phd) rampate dal {ANNO0} e a REGIME dal {ANNO0 + RAMP}; "
          f"ingresso in ruolo a {eta_ruolo_in(PRECARI_ANNI)} anni, durata ruolo {perm_dur(PRECARI_ANNI)}a")
    print(f"# IMBUTO a regime: PhD -(P1={P1:.2f})-> [univ -(P2={P2_TGT:.2f})-> ruolo | "
          f"EPR -(Madia,P2={P2_EPR:.2f})-> ruolo] => {STAB_PHD*100:.0f}% stabilizzato")
    print(f"# UNICO FILTRO all'uscita dal dottorato: P1 scende da {_p1_hist():.2f} (oggi) "
          f"a {P1:.2f}; chi passa ha la carriera garantita")
    print(f"# EPR: {EPR_RICERC_OGGI:,} ricercatori COSTANTI ({EPR_RUOLO_OGGI:,} ruolo + "
          f"{EPR_PRECARI_OGGI:,} precari oggi -> {_epr_in_tgt()*PERM_DUR_EPR:,.0f} + "
          f"{_epr_in_tgt()*D_PREC_EPR:,.0f} a regime); flusso di rimpiazzo "
          f"{_epr_in0():,.0f} -> {_epr_in_tgt():,.0f}/anno")
    print(f"# GOVERD 'oggi' del modello: {_goverd_base():.2f}% PIL (obiettivo {GOVERD_TGT}%) | "
          f"overhead FISSO: tecnici {OVH_EPR_SUPP/1e6:,.0f} mln + infrastruttura "
          f"{OVH_EPR_ATTR/1e6:,.0f} mln [auto-calibrato]")
    print(f"# BORSA PhD: {BORSA_OGGI:.0f} -> {BORSA_TGT:.0f} EUR/mese netti (x{W_PHD:.2f}), "
          f"costo lordo ente {COSTO['dottorando']:,.0f} -> {COSTO['dottorando']*W_PHD:,.0f} EUR/anno")
    print(f"# DOTTORANDI oggi nel modello: {phd_oggi:,.0f} teste "
          f"(reale ~{PHD_OGGI_REALE:,}: scarto {phd_oggi/PHD_OGGI_REALE-1:+.0%}) | "
          f"PhD contati negli FTE: {'SI' if PHD_IN_FTE else 'NO'}")
    print(f"# oggi {DENS_OGGI} FTE/100k | flusso PhD ~{_pd_in0():,.0f}/anno | "
          f"quota-docente a regime {quota_reg*100:.0f}% "
          f"({'cattedre' if quota_reg >= 0.65 else 'più precari-heavy'})")
    print(f"# SUPPORTO (tecnici/amm.vi): +{SUPPORTO*100:.0f}% sul costo-ricerca del personale "
          f"strutturato {'[auto-calibrato]' if a.supporto is None else '[imposto]'}")
    dq = densita_iso_herd(HERD_TGT, UPLIFT_PPP, PRECARI_ANNI, W_PHD)
    d0 = densita_iso_herd(HERD_TGT, 1.0, PRECARI_ANNI, W_PHD)
    print(f"# COMPROMESSO: {QUOTA_RIC_UNI*100:.0f}% del ruolo a profilo ricercatore "
          f"(alpha {ALPHA['ric_uni']}, {COSTO['ric_uni']:,.0f} EUR) => a HERD {HERD_TGT}% "
          f"e parità PPP la densità è {dq:.0f} FTE/100k (senza: {d0:.0f} a paghe odierne)")
    print(f"# UPLIFT PPP x{UPLIFT_PPP:.3f}: reddito dei dottori di ricerca a parità di potere "
          f"d'acquisto, media dei 5 paesi migliori / Italia [ReICO, Commissione UE + OCSE].")
    print(f"#     CONFERMA a vent'anni di distanza: lo stesso rapporto sullo studio CARSA 2006 "
          f"(5 paesi UE migliori) dà x{UPLIFT_PPP_CARSA06:.3f}, cioè "
          f"{UPLIFT_PPP/UPLIFT_PPP_CARSA06-1:+.1%}.")
    print(f"# /!\\ Avvertenze: il paniere ReICO NON è solo-UE (i due valori di testa sono "
          f"verosimilmente extra-UE; sui 3 dietro gli outlier sarebbe x1.47); la popolazione "
          f"sono i\n"
          f"#     dottori di ricerca di TUTTI i settori, non i ricercatori accademici; ed è un "
          f"obiettivo ambizioso per costruzione (media dei 5 MIGLIORI, non media UE: verso\n"
          f"#     quella, nella tabella CARSA, sarebbe x1.18). Vedi il commento su UPLIFT_PPP "
          f"nel sorgente.")
    print(f"# HERD 'oggi' del modello: {base_herd:.2f}% PIL (ISTAT {HERD_OGGI}%: "
          f"scarto {base_herd - HERD_OGGI:+.2f}pp)")
    print("#" * 82)

    # ---- stabilizzazione EPR a organico costante ----
    print(f"\n[STABILIZZAZIONE EPR] organico costante {EPR_RICERC_OGGI:,} ricercatori: "
          f"quanto costa togliere il precariato, senza espandere")
    ts = _tabella_stabilizzazione()
    print(ts.to_string(index=False))
    g = ts["GOVERD_%PIL"].iloc[-1]
    print(f"  -> a regime GOVERD {GOVERD_OGGI}% -> {g:.3f}% "
          f"(+{(g-GOVERD_OGGI)/100*PIL_MLN:,.0f} mln/anno di spesa R&S; "
          f"+{ts['d_budget_mln'].iloc[-1]:,.0f} mln di monte stipendi) | obiettivo "
          f"{GOVERD_TGT}%: {'DENTRO' if g <= GOVERD_TGT else f'SFORATO di {g-GOVERD_TGT:.3f}pp'}")

    # ---- frontiera iso-HERD ----
    print(f"\n[FRONTIERA ISO-HERD {HERD_TGT}%] alzare le paghe => ridurre il personale a HERD fisso")
    fr = []
    QUOTA_RIC_UNI = 0.0
    # le due varianti restano affiancate in tabella: fra loro ci sono ~17 FTE/100k,
    # cioè l'età dei dati vale più di molte leve del modello
    for W in sorted({1.00, 1.15, UPLIFT_PPP_PLI24, 1.45, UPLIFT_PPP, UPLIFT_PPP_CARSA06}):
        d = densita_iso_herd(HERD_TGT, W, PRECARI_ANNI, W_PHD)
        teste_tot = d * POP_100K * teste_per_fte(PRECARI_ANNI)
        quota_phd = _contrib(P2_TGT, PRECARI_ANNI)[0]["dottorando"] / sum(_contrib(P2_TGT, PRECARI_ANNI)[0].values())
        fr.append({"W_paghe": round(W, 3), "densita_FTE/100k": round(d),
                   "teste_totali": round(teste_tot),
                   "di_cui_PhD": round(teste_tot * quota_phd),
                   "HERD_%PIL": HERD_TGT,
                   "nota": "ReICO EC+OCSE [in uso]" if W == UPLIFT_PPP else
                           "CARSA 2006 (conferma)" if W == UPLIFT_PPP_CARSA06 else
                           "CARSA, deflatore PLI 2024" if W == UPLIFT_PPP_PLI24 else ""})
    print(pd.DataFrame(fr).to_string(index=False))
    d1 = densita_iso_herd(HERD_TGT, 1.0, PRECARI_ANNI, W_PHD)
    d2 = densita_iso_herd(HERD_TGT, UPLIFT_PPP, PRECARI_ANNI, W_PHD)
    print(f"  -> a HERD {HERD_TGT}% fisso, parità PPP (x{UPLIFT_PPP:.2f}): "
          f"{d1:.0f} -> {d2:.0f} FTE/100k = -{(1-d2/d1)*100:.0f}% personale.")

    # ---- transizioni ----
    for nome, (t, W, q) in scen.items():
        df = dfs[nome]
        print(f"\n=== {nome} - target {t:.0f} FTE/100k, paghe x{W:.2f} "
              f"(HERD a regime {_herd_assoluto(df):.2f}% PIL) ===")
        cols = ["anno", "densita", "quota_docente", "ruolo_teste", "phd_teste",
                "precari_teste", "pensionamenti", "epr_ruolo", "epr_precari",
                "densita_epr", "dHERD_%PIL", "dBudget_%PIL", "dGOVERD_%PIL"]
        vista = df[df["anno"].isin([2026, 2035, 2045, 2055, 2080])][cols].copy()
        vista["densita"] = vista["densita"].round(0)
        vista["quota_docente"] = (vista["quota_docente"] * 100).round(0)
        for c in ("ruolo_teste", "phd_teste", "precari_teste", "pensionamenti",
                  "epr_ruolo", "epr_precari"):
            vista[c] = vista[c].round(0)
        vista["densita_epr"] = vista["densita_epr"].round(1)
        for c in ("dHERD_%PIL", "dBudget_%PIL", "dGOVERD_%PIL"):
            vista[c] = vista[c].round(3)
        print(vista.to_string(index=False))
        anno90 = _tempo_a_regime(df, t)
        onda = df[df["anno"] <= ANNO0 + 20]
        picco = int(onda.loc[onda["pensionamenti"].idxmax(), "anno"])
        if anno90 < 0:
            quota = (df["densita"].iloc[-1] - df["densita"].iloc[0]) / (t - df["densita"].iloc[0])
            traguardo = f"90% del gap NON colmato entro il {ANNO0 + ORIZZONTE} (solo {quota*100:.0f}%)"
        else:
            traguardo = f"90% del gap colmato entro il {anno90} ({anno90 - ANNO0} anni)"
        print(f"  -> {traguardo}; onda pensionamenti picco ~{picco}.")

    # ---- grafico ----
    # le etichette portano il TARGET, che è cio' che definisce lo scenario; la densità
    # effettiva 2080 è più alta perchè la popolazione SSP2 scende, ed è annotata
    # direttamente sui grafici
    etich = {"FLC": f"FLC (target {scen['FLC'][0]:.0f})",
             "ERA": f"ERA paghe oggi (target {scen['ERA'][0]:.0f})",
             "ERA_PPP_ric": f"ERA PPP + ric.univ. (target {scen['ERA_PPP_ric'][0]:.0f})"}
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.6))
    for nome, (t, W, q) in scen.items():
        df = dfs[nome]
        # qui la densità a popolazione FISSA, perchè il pannello ha le righe di target
        ax[0].plot(df["anno"], df["densita_pop2026"], label=etich[nome])
        ax[0].axhline(t, ls=":", lw=0.6, color="grey")
        ax[1].plot(df["anno"], df["dBudget_%PIL"], label=etich[nome])
    ax[0].axhline(DENS_OGGI, ls="--", lw=0.8, color="black")
    ax[0].set_title(f"Densità FTE/100k a pop. 2026 fissa (precari_anni={PRECARI_ANNI})")
    ax[0].set_xlabel("anno"); ax[0].legend(fontsize=8)
    ax[1].set_title("Budget pubblico aggiuntivo (% PIL)")
    ax[1].set_xlabel("anno"); ax[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(f"{OUT}/transizione_fte.png", dpi=130)
    for nome, df in dfs.items():
        df.to_csv(f"{OUT}/transizione_{nome}.csv", index=False)

    # ---- report 2026-2050 ----
    anni = [2026, 2030, 2035, 2040, 2050, 2060, 2070, 2080]
    for nome in ("FLC", "ERA_PPP_ric"):
        print(f"\n{'='*100}\nTABELLA {nome} - traiettoria {anni[0]}-{anni[-1]} "
              f"(target {scen[nome][0]:.0f} FTE/100k, paghe x{scen[nome][1]:.2f})\n{'='*100}")
        print(tabella_scenario(dfs[nome], anni).to_string())
    grafici(dfs, 2080, f"{OUT}/trend_2026_2080.png")
    grafico_ffo(dfs, 2080, f"{OUT}/ffo_aggiuntivo.png")
    grafico_stack(dfs, 2080, f"{OUT}/organico_stack.png", etich)
    grafico_spesa_stack(dfs, 2080, f"{OUT}/spesa_stack.png", etich)
    print(f"\n[grafici] {OUT}/trend_2026_2080.png (9 pannelli) "
          f"+ {OUT}/ffo_aggiuntivo.png (mld/anno) "
          f"+ {OUT}/organico_stack.png (organico univ.+EPR) "
          f"+ {OUT}/spesa_stack.png (variazione fondi per ramo di bilancio)")
    singoli = grafici_singolo("ERA_PPP_ric", dfs, 2080, OUT, etich)
    print(f"[grafici] solo scenario ERA_PPP_ric, su file separati:\n           "
          + "\n           ".join(singoli))
    print("  NB: 'proxy FFO' = maggior costo del personale di ricerca a carico dello"
          " Stato.\n      L'FFO come voce di bilancio NON è modellato.")

    print("\n=== LETTURA ===")
    print(f"  densità 2080: 'SSP2' = a popolazione proiettata ({pop_100k(2080)/10:.1f} mln), "
          f"'pop.2026' = a demografia ferma ({pop_100k(ANNO0)/10:.1f} mln). Il target di "
          f"scenario è su quest'ultima.")
    for nome, (tg, W, q) in scen.items():
        f = dfs[nome].iloc[-1]
        print(f"  {nome:<12} densità SSP2 {f['densità']:.0f} (pop.2026 {f['densita_pop2026']:.0f}, "
              f"target {tg:.0f}) | HERD {f['HERD_%PIL']:.3f}% + GOVERD "
              f"{f['GOVERD_%PIL']:.3f}% | paghe x{W:.2f} | ric.univ. {q*100:.0f}% | "
              f"+{f['dStato_univ_mld']+f['dStato_epr_mld']:.1f} mld/anno")
    print(f"  Il terzo scenario tiene INSIEME densità {scen['ERA_PPP_ric'][0]:.0f}, HERD "
          f"{HERD_TGT}% e parità PPP: i ricercatori universitari rendono 2x FTE per euro")
    print("  dei docenti, quindi servono MENO teste, non più.")
    if PRECARI_ANNI > 3:
        print(f"  Con precari_anni={PRECARI_ANNI}: flusso d'ingresso realistico (~{_pd_in0():,.0f}), "
              f"ma il regime NON è più cattedre (quota-docente {quota_reg*100:.0f}%): il")
        print(f"  precariato prolungato è esso stesso uno stock strutturale permanente.")
    print(f"\nFile: transizione_fte.png + transizione_*.csv (in {OUT})")


if __name__ == "__main__":
    main()
