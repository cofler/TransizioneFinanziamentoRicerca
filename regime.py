"""Composizione di STATO STAZIONARIO e frontiera prezzo/quantita'.

Nessuna dinamica qui: solo la composizione che l'imbuto di carriera produce a
regime, i costi medi che ne derivano e la frontiera iso-HERD. E' la parte del
modello che si puo' risolvere in forma chiusa.

CONVENZIONE: i valori di configurazione si leggono SEMPRE come C.NOME, mai importati
per nome. main() li riassegna a runtime (calibrazioni, argomenti da CLI) e solo
l'accesso per attributo vede il rebinding; un `from config import X` catturerebbe una
copia congelata all'import. Le funzioni invece non vengono mai riassegnate e si
importano per nome.
"""
from __future__ import annotations

import config as C

# ============================ COMPOSIZIONE A REGIME ==========================
def eta_ruolo_in(precari_anni: float) -> int:
    """Età d'ingresso in ruolo: fine PhD + precariato + RTT. Un precariato più
    lungo NON allunga la vita lavorativa, la sposta in avanti."""
    return int(round(C.ETA_FINE_PHD + precari_anni + C.D_RTT))


def perm_dur(precari_anni: float) -> int:
    """Anni di ruolo effettivi (slot della coorte). A precari_anni=3 vale 28."""
    return max(1, C.ETA_PENS - eta_ruolo_in(precari_anni))


def _contrib(P2: float, precari_anni: float) -> tuple[dict[str, float], dict[str, float]]:
    """Per unità di flusso PhD in ingresso, a regime: (teste-anno, FTE) per stadio.
    L'imbuto è PhD -(P1)-> precari -(P2)-> RTT -> ruolo."""
    # per unità di flusso POSTDOC universitario in ingresso (non di flusso PhD:
    # il bacino dei dottorandi serve entrambi i rami, e l'EPR ha fabbisogno fisso)
    ruolo = P2 * perm_dur(precari_anni)
    teste = {"dottorando": C.D_PHD / C.P1,      # dottorandi necessari a produrre 1 postdoc
             "precari": precari_anni,
             "RTT": P2 * C.D_RTT,
             "docente": ruolo * (1 - C.QUOTA_RIC_UNI),
             "ric_uni": ruolo * C.QUOTA_RIC_UNI}
    fte = {k: v * C.ALPHA[k] for k, v in teste.items()}
    if not C.PHD_IN_FTE:
        fte["dottorando"] = 0.0        # esclusi dal CONTEGGIO, non dal costo
    return teste, fte


def kappa(P2: float, precari_anni: float) -> float:
    """FTE-ricerca universitari per unità di flusso POSTDOC in ingresso, a regime."""
    return sum(_contrib(P2, precari_anni)[1].values())


def _epr_in_tgt() -> float:
    """Fabbisogno EPR a regime: puro RIMPIAZZO a organico costante. Il GOVERD è già
    saturato dalla stabilizzazione, quindi gli EPR non crescono in teste."""
    return C.EPR_RICERC_OGGI / (C.D_PREC_EPR + C.PERM_DUR_EPR)


def regime_shares(precari_anni: float) -> dict[str, float]:
    fte = _contrib(C.P2_TGT, precari_anni)[1]
    tot = sum(fte.values())
    return {k: v / tot for k, v in fte.items()}


def avg_costo_split(precari_anni: float) -> tuple[float, float]:
    """Quota-ricerca degli stipendi per FTE CONTATO, separando le due leve salariali:
    (personale strutturato/precario -> leva W, borse PhD -> leva W_PHD).
    Il numeratore include i dottorandi anche quando non contano negli FTE."""
    teste, fte = _contrib(C.P2_TGT, precari_anni)
    tot = sum(fte.values())
    costo = {k: t * C.ALPHA[k] * C.COSTO[k] / tot for k, t in teste.items()}
    return sum(v for k, v in costo.items() if k != "dottorando"), costo["dottorando"]


def avg_costo(precari_anni: float) -> float:
    return sum(avg_costo_split(precari_anni))


def teste_per_fte(precari_anni: float) -> float:
    teste, fte = _contrib(C.P2_TGT, precari_anni)
    return sum(teste.values()) / sum(fte.values())


def ta_di(fte_ric: float, ta0: float, ric0: float) -> float:
    """FTE di personale TA associati a uno stock di FTE-ricercatori.

    Regola a DUE componenti: una quota (1-TA_ELAST) che NON dipende dai ricercatori e
    una che scala col loro rapporto rispetto all'anno 0. Vedi il blocco PERSONALE TA
    per il perche' l'elasticita' sta fra 0 e 1 e per l'asintoto che ne consegue."""
    if ric0 <= 0:
        return ta0
    return ta0 * (1 - C.TA_ELAST + C.TA_ELAST * fte_ric / ric0)


def _ta_uni(fte_ric: float) -> float:
    return ta_di(fte_ric, C.TA_UNI_OGGI, C.FTE_OGGI)


def _ta_epr(fte_ric: float) -> float:
    return ta_di(fte_ric, C.TA_EPR_OGGI, C.EPR_RICERC_OGGI * C.ALPHA_EPR)


def densita_iso_herd(herd_pct: float, W: float, precari_anni: float,
                     W_phd: float = 1.0) -> float:
    """Frontiera prezzo<->quantità a HERD costante, con le due leve salariali.

    Col TA esplicito la frontiera NON è più una semplice divisione: il TA è affine nei
    ricercatori (una parte fissa più una proporzionale), non proporzionale, quindi il
    costo totale ha un'intercetta. Resta risolvibile in forma chiusa - qui sotto - ma
    la parte fissa del TA va sottratta dal budget PRIMA di dividere, altrimenti la
    densità raggiungibile risulta sovrastimata."""
    c_pers, c_phd = avg_costo_split(precari_anni)
    c_supp = (C.SUPPORTO or 0.0) * c_pers
    k_attr = (1 - C.LAMBDA_HE) / C.LAMBDA_HE       # attrezzature per euro di lavoro
    # costo per FTE-ricercatore: stipendi levati + attrezzature sul costo NON levato
    # (le attrezzature non seguono le paghe)
    c_ric = (c_pers * W + c_phd * W_phd + c_supp * W
             + (c_pers + c_phd + c_supp) * k_attr)
    # costo di un FTE di TA, stipendio + attrezzature che si porta dietro
    c_ta = C.COSTO_TA * ((W if C.TA_SEGUE_W else 1.0) + k_attr)
    # TA(R) = fisso + marg*R  ->  budget = R*c_ric + (fisso + marg*R)*c_ta
    fisso, marg = C.TA_UNI_OGGI * (1 - C.TA_ELAST), C.TA_UNI_OGGI * C.TA_ELAST / C.FTE_OGGI
    budget = (herd_pct / 100 * C.PIL_MLN) * 1e6
    fte = max(0.0, (budget - fisso * c_ta) / (c_ric + marg * c_ta))
    return fte / C.POP_100K
