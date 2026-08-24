"""Giuntura fra il MODELLO e chi lo chiama - la CLI di piano_transizione o la webapp.

Qui non si stampa e non si scrive su disco: entrano parametri, escono DataFrame. E'
l'unico posto in cui il blocco "applica i parametri e calibra" esiste, cosi' CLI e web
non possono divergere.

PERCHE' SERVE. config.py e' un singleton globale mutabile, e la convenzione del progetto
- ripetuta in motore, irpef, grafici, calibrazione - e' che i valori si leggano SEMPRE
come C.NOME perche' solo l'accesso per attributo vede il rebinding. Finche' il modello
girava una volta sola per processo la cosa era innocua. Una webapp lo rieseguE decine di
volte nello stesso processo, e da piu' thread: servono percio' due garanzie che la CLI
non aveva mai dovuto dare.

  IDEMPOTENZA - due run con parametri diversi non devono contaminarsi. Non basta
  riscrivere le globali che la CLI riscrive: ce ne sono di CONDIZIONATE (--ta-cap solo
  se non None, GOVERD_MIN solo con --no-goverd-pavimento) che lasciate stare
  erediterebbero il valore della run precedente. Invece di enumerarle a mano - elenco
  che si sfalderebbe al primo parametro nuovo - si riparte ogni volta dallo stato
  PRISTINO di config, fotografato all'import.

  MUTUA ESCLUSIONE - _LOCK serializza l'intera sezione "scrivi le globali, calibra,
  simula". Un run dura ~1s e i DataFrame che escono sono valori, non riferimenti a C:
  dopo il rilascio del lock sono al sicuro.
"""
from __future__ import annotations

import copy
import threading
import types
from dataclasses import dataclass, field

import pandas as pd

import config as C
from calibrazione import (_calibra_anni_da_associato, _calibra_lambda_he,
                          _calibra_overhead_epr, _calibra_supporto, _herd_base)
from motore import (_fte_didattico, _fte_uni_oggi, _init_stato, _p1_hist, _pd_in0,
                    _precari_per_chiudere, piano_attrezzature, simula,
                    simula_senza_blocco, simula_senza_prepens)
from regime import densita_iso_herd, regime_shares

# Fotografia dello stato di config PRIMA che chiunque lo tocchi. Vale perche' questo
# modulo viene importato in cima a piano_transizione (e ad app.py), quindi molto prima
# che main() o la UI applichino alcunche'. Si escludono funzioni e moduli: si ripristina
# solo il DATO. La deepcopy serve per COSTO e per le scale, che sono mutabili.
_PRISTINO: dict[str, object] = {
    k: copy.deepcopy(v) for k, v in vars(C).items()
    if not k.startswith("__") and not callable(v)
    and not isinstance(v, types.ModuleType)
}

_LOCK = threading.RLock()

NOMI_SCENARI = ("FLC", "ERA", "ADI_Manifesto_ric")


# --- parametri -------------------------------------------------------------------
# Una voce per ogni flag della CLI, con lo STESSO nome in snake_case che argparse
# produce, piu' herd_tgt/goverd_tgt che prima vivevano solo in config. I valori si
# leggono da C all'import, quando config e' ancora vergine: sono percio' esattamente i
# default che l'argparse dichiara, senza doverli ricopiare a mano.
DEFAULTS: dict[str, object] = {
    # obiettivi di spesa
    "herd_tgt": C.HERD_TGT,
    "goverd_tgt": C.GOVERD_TGT,
    # paghe e composizione
    "uplift_ppp": C.UPLIFT_PPP,
    "quota_ric_uni": C.QUOTA_RIC_UNI,
    "quota_po_tgt": C.QUOTA_PO_TGT,
    # imbuto di carriera
    "rtt_anni": C.D_RTT,
    "p2_tgt": C.P2_TGT,
    "stab_phd": C.STAB_PHD,
    "p2_hist": C.P2_HIST,
    "p2_min": C.P2_MIN,
    "precari_anni": C.PRECARI_ANNI,
    "ramp": C.RAMP,
    "ramp_phd": C.RAMP_PHD,
    "ramp_alpha_prec": C.RAMP_ALPHA_PREC,   # None = segue ramp
    # dottorato
    "borsa_tgt": C.BORSA_TGT,
    "costo_phd": C.COSTO["dottorando"],
    "phd_in_fte": C.PHD_IN_FTE,
    # enti pubblici di ricerca
    "epr_precari": C.EPR_PRECARI_OGGI,
    "epr_ruolo": C.EPR_RUOLO_OGGI,
    "costo_epr_ruolo": C.COSTO_EPR_RUOLO,
    "phd_nel_diretto": C.PHD_NEL_DIRETTO_EPR,
    "epr_non_mur": C.EPR_NON_MUR_OGGI,
    "epr_pav_gain": C.EPR_PAV_GAIN,
    "epr_anni_liv2": None,
    "epr_anni_liv1": None,
    "epr_quota_ii_tgt": C.QUOTA_EPR_II_TGT,
    "epr_quota_i_tgt": C.QUOTA_EPR_I_TGT,
    "no_goverd_pavimento": False,
    "no_attrezzature": False,
    # tecnici e amministrativi
    "ta_elast": C.TA_ELAST,
    "costo_ta": C.COSTO_TA,
    "ta_cap": None,
    "ta_uplift": C.TA_UPLIFT,
    "ta_segue_w": C.TA_SEGUE_W,
    # postdoc: incarico di ricerca
    "quota_incarico": C.QUOTA_PREC_INCARICO,
    "anni_incarico": C.ANNI_INCARICO,
    # stock di partenza
    "perm_oggi": C.PERM_OGGI,
    "precari_oggi": None,
    "ric_uni_ruolo_oggi": C.RIC_UNI_RUOLO_OGGI,
    # calibrazione: None = ricava dal dato, un valore = imponi
    "lambda_he": None,
    "supporto": None,
    # leva prepensionamento
    "prepens_anni": C.PREPENS_ANNI,
    "prepens_ades": C.PREPENS_ADES,
    "prepens_centro": C.PREPENS_CENTRO,
    "prepens_centro_auto": False,
    "prepens_sigma": C.PREPENS_SIGMA,
    "prepens_coda": C.PREPENS_CODA,
    "prepens_asimm": C.PREPENS_ASIMM,
    # leva blocco scatti
    "scatti_blocco_da": C.SCATTI_BLOCCO_DA,
    "scatti_blocco_anni": C.SCATTI_BLOCCO_ANNI,
    "scatti_blocco_recupero": C.SCATTI_BLOCCO_RECUPERO,
    "scatti_blocco2_da": C.SCATTI_BLOCCO2_DA,
    "scatti_blocco2_anni": C.SCATTI_BLOCCO2_ANNI,
    "scatti_blocco2_recupero": C.SCATTI_BLOCCO2_RECUPERO,
}


def con_default(p: dict | None = None) -> dict:
    """I DEFAULTS con sopra le sole chiavi passate. Chi chiama non deve conoscere i 52
    parametri: ne muove tre e il resto resta calibrato."""
    d = dict(DEFAULTS)
    if p:
        d.update({k: v for k, v in p.items() if k in DEFAULTS})
    return d


def _ripristina() -> None:
    """Riporta config allo stato dell'import. Chiamata all'inizio di applica(): e' cio'
    che rende una run indipendente da quella prima."""
    for k, v in _PRISTINO.items():
        setattr(C, k, copy.deepcopy(v))


def applica(p: dict) -> None:
    """Scrive in config i 53 parametri e ricalcola i derivati, NELL'ORDINE del sorgente
    originale - che non e' cosmetico: la soglia PA->PO viene prima perche' il costo dei
    professori entra nell'HERD ricostruito, lambda dipende dal TA, il supporto da lambda
    e l'overhead EPR dal supporto. Invertirli da' una calibrazione incoerente.

    Riparte dallo stato pristino, quindi e' idempotente: applica(A); applica(B);
    applica(A) lascia config esattamente come il primo applica(A).

    Solleva ValueError se i parametri sono incoerenti fra loro."""
    _ripristina()
    C.PREPENS_ANNI, C.PREPENS_ADES, C.PREPENS_SIGMA = (p["prepens_anni"], p["prepens_ades"],
                                                 p["prepens_sigma"])
    C.PREPENS_CODA, C.PREPENS_ASIMM = p["prepens_coda"], p["prepens_asimm"]
    # None fa scattare la regola di _centro_finestra dentro simula()
    C.PREPENS_CENTRO = None if p["prepens_centro_auto"] else p["prepens_centro"]
    C.SCATTI_BLOCCO_DA, C.SCATTI_BLOCCO_ANNI = p["scatti_blocco_da"], p["scatti_blocco_anni"]
    C.SCATTI_BLOCCO_RECUPERO = p["scatti_blocco_recupero"]
    C.SCATTI_BLOCCO2_DA, C.SCATTI_BLOCCO2_ANNI = (p["scatti_blocco2_da"],
                                                  p["scatti_blocco2_anni"])
    C.SCATTI_BLOCCO2_RECUPERO = p["scatti_blocco2_recupero"]
    # le due finestre si sommano in _persi(): se si sovrappongono, gli anni in comune
    # verrebbero tolti due volte. Meglio dirlo subito che spiegarlo dopo.
    if (p["scatti_blocco_anni"] >= 1 and p["scatti_blocco2_anni"] >= 1
            and p["scatti_blocco_da"] < p["scatti_blocco2_da"] + p["scatti_blocco2_anni"]
            and p["scatti_blocco2_da"] < p["scatti_blocco_da"] + p["scatti_blocco_anni"]):
        raise ValueError(
            "le due finestre di blocco scatti si sovrappongono: gli anni in comune "
            "verrebbero contati due volte. Separa --scatti-blocco-da/--scatti-blocco2-da.")
    C.P2_HIST, C.PERM_OGGI, C.PRECARI_ANNI, C.RAMP = p["p2_hist"], p["perm_oggi"], p["precari_anni"], p["ramp"]
    C.RAMP_PHD = p["ramp_phd"]
    # None = segue RAMP. Va dopo C.RAMP, che ramp_alpha_prec() legge come ripiego.
    C.RAMP_ALPHA_PREC = p["ramp_alpha_prec"]
    C.RIC_UNI_RUOLO_OGGI = p["ric_uni_ruolo_oggi"]
    C.P2_MIN = p["p2_min"]
    C.STAB_PHD, C.PHD_IN_FTE, C.D_RTT = p["stab_phd"], p["phd_in_fte"], p["rtt_anni"]
    C.EPR_PRECARI_OGGI, C.EPR_RUOLO_OGGI = p["epr_precari"], p["epr_ruolo"]
    C.EPR_NON_MUR_OGGI, C.PHD_NEL_DIRETTO_EPR = p["epr_non_mur"], p["phd_nel_diretto"]
    C.EPR_PAV_GAIN = p["epr_pav_gain"]
    # Obiettivi di spesa. Erano costanti di config; sono la domanda piu' naturale che
    # si fa a questo modello ("quanto vogliamo spendere?"), quindi sono parametri.
    # HERD_RIF/GOVERD_RIF sono il riferimento con cui _voci() misura il 3% GERD, e
    # GOVERD_MIN e' il pavimento di spesa degli enti: entrambi seguono l'obiettivo,
    # altrimenti muovere il target lascerebbe indietro meta' della contabilita'.
    C.HERD_TGT, C.GOVERD_TGT = p["herd_tgt"], p["goverd_tgt"]
    C.HERD_RIF, C.GOVERD_RIF = C.HERD_TGT, C.GOVERD_TGT
    C.GOVERD_MIN = C.GOVERD_TGT
    if p["no_goverd_pavimento"]:
        C.GOVERD_MIN = None
        C.EPR_PAV_GAIN = 0.0
    if p["no_attrezzature"]:
        C.ATTREZZ_INVILUPPO = False
    C.EPR_RICERC_OGGI = C.EPR_PRECARI_OGGI + C.EPR_RUOLO_OGGI
    C.COSTO_EPR_RUOLO, C.P2_TGT = p["costo_epr_ruolo"], p["p2_tgt"]
    C.ANNI_DA_LIV2, C.ANNI_DA_LIV1 = p["epr_anni_liv2"], p["epr_anni_liv1"]
    C.QUOTA_EPR_II_TGT, C.QUOTA_EPR_I_TGT = p["epr_quota_ii_tgt"], p["epr_quota_i_tgt"]
    C.QUOTA_RIC_UNI, C.UPLIFT_PPP = p["quota_ric_uni"], p["uplift_ppp"]
    C.QUOTA_PO_TGT = p["quota_po_tgt"]
    # Vincolo di stabilizzazione. Con P2_univ = P2_EPR = 1 (nessun imbuto interno)
    # si riduce a P1 = STAB_PHD: tutta la selezione è all'uscita dal dottorato.
    # (Con P2_univ < 1 l'EPR, che stabilizza al 100%, alza di poco la media: è un
    # flusso di rimpiazzo piccolo, quindi si approssima col solo ramo universitario.)
    C.P1 = min(1.0, C.STAB_PHD / C.P2_TGT)
    C.BORSA_TGT = p["borsa_tgt"]
    C.W_PHD = C.BORSA_TGT / C.BORSA_OGGI
    C.COSTO["dottorando"] = p["costo_phd"]
    C.TA_ELAST, C.COSTO_TA, C.TA_UPLIFT, C.TA_SEGUE_W = p["ta_elast"], p["costo_ta"], p["ta_uplift"], p["ta_segue_w"]
    if p["ta_cap"] is not None:
        C.TA_CAP = p["ta_cap"]
    # la quota a incarico governa TRE cose insieme - platea esente, costo medio del
    # postdoc e quindi la spesa - e vanno mosse assieme, altrimenti la scomposizione
    # IRPEF non quadra piu' col monte stipendi di _spesa(). Va DOPO --precari-anni,
    # perche' la quota sullo stock e' una frazione della permanenza.
    C.QUOTA_PREC_INCARICO, C.ANNI_INCARICO = p["quota_incarico"], p["anni_incarico"]
    C.QUOTA_ESENTE_PREC_UNI = C.QUOTA_ESENTE_PREC_UNI_TGT = C.quota_incarico_stock()
    C.COSTO["precari"] = C.costo_precari()
    # Densità iniziale RICAVATA dagli stock, non imposta. Va fatto prima di ogni
    # calibrazione: FTE_OGGI è la base del TA e l'ancora del ramo universitario.
    # I precari chiudono il gap: dipendono da PERM_OGGI, P2_HIST, D_RTT e PRECARI_ANNI,
    # quindi vanno risolti DOPO che tutti quelli sono stati letti dalla CLI.
    C.PRECARI_OGGI = _precari_per_chiudere() if p["precari_oggi"] is None else p["precari_oggi"]
    C.FTE_OGGI = _fte_uni_oggi()
    C.DENS_OGGI = C.FTE_OGGI / C.POP_100K
    # livelli di TA dal rapporto misurato: così il TA segue il perimetro del modello
    C.TA_UNI_OGGI = C.TA_UNI_RATIO * C.FTE_OGGI
    C.TA_EPR_OGGI = C.TA_EPR_RATIO * C.EPR_RICERC_OGGI * C.ALPHA_EPR
    # studenti impliciti nel rapporto di partenza, sul denominatore in FTE didattici
    C.STUDENTI_OGGI = C.STUD_DOC_OGGI * _fte_didattico(_init_stato(0.0))
    # ORDINE OBBLIGATO: la soglia PA->PO viene prima di tutto il resto (il costo dei
    # professori entra nell'HERD ricostruito), lambda dipende dal TA (esplicito), il
    # supporto residuo dipende da lambda, l'overhead EPR dal supporto. Invertirli dà
    # una calibrazione incoerente.
    C.ANNI_DA_ASSOCIATO = _calibra_anni_da_associato()
    C.LAMBDA_HE = _calibra_lambda_he() if p["lambda_he"] is None else p["lambda_he"]
    C.SUPPORTO = _calibra_supporto() if p["supporto"] is None else p["supporto"]
    C.OVH_EPR_SUPP, C.OVH_EPR_ATTR = _calibra_overhead_epr()


def scenari() -> dict[str, tuple[float, float, float]]:
    """(densita' obiettivo, moltiplicatore paghe W, quota ricercatori) per scenario.

    Va chiamata DOPO applica(): le due frontiere iso-HERD leggono PRECARI_ANNI, W_PHD e
    UPLIFT_PPP appena impostati. La quota-ricercatori e' una leva del solo terzo
    scenario - FLC ed ERA restano i baseline tutto-cattedre - quindi si azzera e si
    ripristina attorno alle chiamate, come faceva main()."""
    q = C.QUOTA_RIC_UNI
    C.QUOTA_RIC_UNI = 0.0
    d_era = densita_iso_herd(C.HERD_TGT, 1.0, C.PRECARI_ANNI, C.W_PHD)
    C.QUOTA_RIC_UNI = q
    d_ppp = densita_iso_herd(C.HERD_TGT, C.UPLIFT_PPP, C.PRECARI_ANNI, C.W_PHD)
    C.QUOTA_RIC_UNI = 0.0
    return {"FLC": (140.0, 1.0, 0.0),
            "ERA": (d_era, 1.0, 0.0),
            "ADI_Manifesto_ric": (d_ppp, C.UPLIFT_PPP, q)}


@dataclass
class Risultato:
    """Cio' che una run produce. Solo valori: nessun riferimento a config, quindi si
    puo' tenere in cache e leggere fuori dal lock."""
    dfs: dict[str, pd.DataFrame]
    target: dict[str, tuple[float, float, float]]
    cal: dict[str, float]
    controlli: dict[str, pd.DataFrame] = field(default_factory=dict)


def _fotografia_calibrazione() -> dict[str, float]:
    """I residui che la calibrazione ha ricavato, piu' gli stock e le diagnostiche che ne
    dipendono. Sono la parte del modello che NON e' un'ipotesi ma un residuo, e vanno
    potuti mostrare.

    VA CHIAMATA PRIMA DI scenari(), che azzera QUOTA_RIC_UNI per costruire i baseline
    tutto-cattedre e non lo ripristina: quota_reg letta dopo direbbe la composizione di
    un regime SENZA ricercatori universitari, cioe' di uno scenario che l'utente non ha
    chiesto."""
    return {"base_herd": _herd_base(),
            "quota_reg": regime_shares(C.PRECARI_ANNI)["docente"],
            "phd_oggi": _pd_in0() * C.D_PHD,
            "anni_da_associato": C.ANNI_DA_ASSOCIATO, "lambda_he": C.LAMBDA_HE,
            "supporto": C.SUPPORTO, "ovh_epr_supp": C.OVH_EPR_SUPP,
            "ovh_epr_attr": C.OVH_EPR_ATTR, "precari_oggi": C.PRECARI_OGGI,
            "fte_oggi": C.FTE_OGGI, "dens_oggi": C.DENS_OGGI,
            "p1": C.P1, "p1_hist": _p1_hist(), "w_phd": C.W_PHD}


def esegui(p: dict, quali: tuple[str, ...] = ("ADI_Manifesto_ric",),
           controlli: bool = False) -> Risultato:
    """Applica i parametri, calibra e simula gli scenari richiesti.

    `quali` e' la leva che rende la webapp reattiva: una simula() costa ~1s, e la UI ne
    vuole normalmente UNA sola (lo scenario di arrivo), non tre. La CLI le chiede tutte.

    `controlli` aggiunge le due simulazioni CONTROFATTUALI - senza prepensionamento e
    senza blocco scatti - che servono solo ai blocchi diagnostici della CLI: sono altre
    due simula() per scenario, cioe' il doppio del tempo, e la UI non le usa."""
    with _LOCK:
        applica(p)
        # PRIMA di scenari(), che lascia QUOTA_RIC_UNI a 0: vedi il docstring.
        cal = _fotografia_calibrazione()
        scen = scenari()
        ignoti = [n for n in quali if n not in scen]
        if ignoti:
            raise ValueError(f"scenari sconosciuti: {ignoti}; attesi {list(scen)}")
        # l'inviluppo di spesa si posa QUI, una volta sola, subito dopo la simulazione:
        # da questo punto in poi CSV, tabelle e grafici vedono tutti le stesse colonne.
        dfs = {n: piano_attrezzature(simula(*scen[n])) for n in quali}
        ctrl: dict[str, pd.DataFrame] = {}
        if controlli:
            # Le due di controllo NON passano da piano_attrezzature: confrontano teste e
            # costo per testa, non spesa di piano.
            for n in quali:
                ctrl[f"{n}/senza_prepens"] = simula_senza_prepens(*scen[n])
                ctrl[f"{n}/senza_blocco"] = simula_senza_blocco(*scen[n])
    return Risultato(dfs=dfs, target=scen, cal=cal, controlli=ctrl)
