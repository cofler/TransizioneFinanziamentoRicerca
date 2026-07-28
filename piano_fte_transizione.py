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
Leva PAGHE (W = media europea a PPP, x1,16) scala il personale, non le attrezzature.

- LEVA PREPENSIONAMENTO (vedi il blocco PREPENS_* più sotto): finestra di uscite
anticipate collocata PRIMA dell'anno di picco dell'organico, per smorzare l'onda
di accumulo senza toccare lo stato stazionario. ACCESA di default, sulla
configurazione consigliata (anticipo 4 anni, adesione 50%, sigma 4, centro 2053):
porta la gobba da +13,5% a +5,1% senza scavare buchi. --prepens-ades 0 la spegne
e riporta il modello esattamente com'era prima che la leva esistesse.
================================================================================
"""
from __future__ import annotations

import argparse
import os

import numpy as np
import pandas as pd

import config as C
from regime import (_contrib, _epr_in_tgt, _ta_epr, _ta_uni, densita_iso_herd,
                    eta_ruolo_in, perm_dur, regime_shares, teste_per_fte)
from motore import (_anno_picco, _centro_finestra, _epr_in0, _fte, _fte_didattico,
                    _fte_epr, _fte_ric_uni, _fte_uni_oggi, _init_stato, _p1_hist,
                    _pd_in0, _precari_per_chiudere, _prepens_on, _spesa, _spesa_epr,
                    _teste_tot, _uni_in0, _voci, simula, simula_senza_prepens)
from irpef import Voce, _quadratura, retroflusso, scomponi
from calibrazione import (_calibra_lambda_he, _calibra_overhead_epr,
                          _calibra_supporto, _goverd_base, _herd_assoluto,
                          _herd_base, _tabella_stabilizzazione, _tempo_a_regime)
from tabelle import RIGHE_TAB, tabella_scenario
from grafici import (grafici_singolo, grafico_ffo, grafico_spesa_stack,
                     grafico_stack, grafico_target, grafico_trend)


def main() -> None:
    ap = argparse.ArgumentParser(description="Transizione FTE verso il regime cattedre.")
    ap.add_argument("--out", type=str, default=C.OUT,
                    help="cartella di output per png/csv (default: cartella dello script)")
    ap.add_argument("--uplift-ppp", type=float, default=C.UPLIFT_PPP,
                    help=f"moltiplicatore paghe (default {C.UPLIFT_PPP_EU:.3f} = MEDIA EUROPEA "
                         f"{C.REDDITO_PHD_EU:,} / Italia {C.REDDITO_PHD_IT:,} sul reddito dei "
                         f"dottori di ricerca a PPP, ReICO EC+OCSE). Alternative: "
                         f"{C.UPLIFT_PPP_TOP5:.4f} = media dei 5 paesi che pagano meglio "
                         f"(scenario molto ottimista, paniere NON solo-UE); "
                         f"{C.UPLIFT_PPP_CARSA06_UE25:.3f} = media UE25 CARSA 2006 (conferma "
                         f"del default); {C.UPLIFT_PPP_CARSA06:.3f} = top-5 UE CARSA 2006")
    ap.add_argument("--quota-ric-uni", type=float, default=C.QUOTA_RIC_UNI,
                    help="quota del ruolo universitario con profilo ricercatore "
                         "(alpha 0.75, stipendio EPR) invece che docente PO/PA")
    ap.add_argument("--rtt-anni", type=int, default=C.D_RTT,
                    help=f"durata del contratto RTT in anni (default {C.D_RTT}, L.79/2022; "
                         "usa 3 per l'ex RTD-B = tenure più rapida possibile)")
    ap.add_argument("--p2-tgt", type=float, default=C.P2_TGT,
                    help="postdoc->RTT a regime (default 1.0 = nessun imbuto interno; "
                         "P1 viene ricavato di conseguenza dal vincolo di stabilizzazione)")
    ap.add_argument("--stab-phd", type=float, default=C.STAB_PHD,
                    help="quota di dottori stabilizzati al ruolo = P1*P2 (default 0.50)")
    ap.add_argument("--borsa-tgt", type=float, default=C.BORSA_TGT,
                    help=f"borsa PhD target, netto mensile (default {C.BORSA_TGT:.0f}; oggi {C.BORSA_OGGI:.0f})")
    ap.add_argument("--costo-phd", type=float, default=C.COSTO["dottorando"],
                    help="costo lordo ente di un dottorando oggi (default 22000)")
    ap.add_argument("--epr-precari", type=int, default=C.EPR_PRECARI_OGGI,
                    help=f"precari EPR oggi (default {C.EPR_PRECARI_OGGI:,})")
    ap.add_argument("--epr-ruolo", type=int, default=C.EPR_RUOLO_OGGI,
                    help=f"ricercatori EPR di ruolo oggi (default {C.EPR_RUOLO_OGGI:,})")
    ap.add_argument("--costo-epr-ruolo", type=float, default=C.COSTO_EPR_RUOLO,
                    help=f"costo ente ricercatore EPR di ruolo (default {C.COSTO_EPR_RUOLO:,})")
    ap.add_argument("--ta-elast", type=float, default=C.TA_ELAST,
                    help=f"elasticità del TA ai ricercatori (default {C.TA_ELAST}: "
                         "ricercatori x2 -> TA x1,5). 0 = overhead fisso, "
                         "1 = proporzionale. Il dato storico italiano è 0.33, ma "
                         "misura il blocco del turnover, non il fabbisogno")
    ap.add_argument("--costo-ta", type=float, default=C.COSTO_TA,
                    help=f"costo lordo ente per testa-anno di TA (default {C.COSTO_TA:,})")
    ap.add_argument("--ta-segue-w", action=argparse.BooleanOptionalAction,
                    default=C.TA_SEGUE_W,
                    help="gli stipendi TA seguono la leva paghe W (default: sì, come "
                         "il vecchio SUPPORTO). Il gap ReICO è però misurato sui "
                         "dottori di ricerca, non sugli amministrativi")
    ap.add_argument("--lambda-he", type=float, default=None,
                    help="quota-lavoro dell'HERD (default: RICAVATA dai costi del "
                         "personale, TA compreso; usa 0.70 per l'assunzione vecchia, "
                         "che però non è compatibile con i TA misurati)")
    ap.add_argument("--supporto", type=float, default=None,
                    help="overhead tecnici/amministrativi sul costo-ricerca del personale "
                         f"(default: auto-calibrato per riprodurre HERD {C.HERD_OGGI}%% PIL; "
                         "usa 0 per disattivarlo)")
    ap.add_argument("--phd-in-fte", action=argparse.BooleanOptionalAction, default=C.PHD_IN_FTE,
                    help="i dottorandi contano negli FTE-ricerca (default: si', convenzione Frascati). "
                         "Il loro COSTO entra in HERD/budget in entrambi i casi.")
    ap.add_argument("--quota-esente-postdoc", type=float, default=C.QUOTA_ESENTE_PREC_UNI,
                    help=f"quota di postdoc universitari sotto un regime ESENTE IRPEF "
                         f"(assegni, borse e incarichi di ricerca) nel {C.ANNO0} "
                         f"(default {C.QUOTA_ESENTE_PREC_UNI:.3f} = mix osservabile MUR; "
                         "sensitività: 0.366 se esenti i soli assegni certi, 0.787 se "
                         "tutte le figure non separate fossero borse). Scende a "
                         f"{C.QUOTA_ESENTE_PREC_UNI_TGT:.2f} lungo la rampa")
    ap.add_argument("--p2-hist", type=float, default=C.P2_HIST,
                    help="stabilizzazione storica (default 0.10)")
    ap.add_argument("--p2-min", type=float, default=C.P2_MIN,
                    help="pavimento su P2: la stabilizzazione non scende sotto questo "
                         f"valore già dal {C.ANNO0}, scavalcando la rampa (default "
                         f"{C.P2_MIN} = piano straordinario da ~15.000 stabilizzati nel "
                         "primo triennio; usa 0 per la sola rampa)")
    ap.add_argument("--perm-oggi", type=int, default=C.PERM_OGGI,
                    help=f"professori di ruolo PO+PA oggi (default {C.PERM_OGGI:,}, "
                         "MUR open data 2023)")
    ap.add_argument("--precari-oggi", type=int, default=None,
                    help="stock di postdoc precari oggi (default: RICAVATO per chiudere "
                         "il gap fra l'FTE del modello e il dato Eurostat; usa 35000 "
                         "per la stima PNRR e lasciare il gap dichiarato)")
    ap.add_argument("--ric-uni-ruolo-oggi", type=int, default=C.RIC_UNI_RUOLO_OGGI,
                    help=f"ricercatori a tempo indeterminato oggi (default "
                         f"{C.RIC_UNI_RUOLO_OGGI:,}, ruolo a esaurimento)")
    ap.add_argument("--precari-anni", type=float, default=C.PRECARI_ANNI,
                    help="permanenza media nel precariato, anni (default 3)")
    ap.add_argument("--ramp", type=int, default=C.RAMP,
                    help=f"anni di rampa delle leve, tutte (default {C.RAMP} -> a regime dal {C.ANNO0 + C.RAMP})")
    ap.add_argument("--prepens-anni", type=int, default=C.PREPENS_ANNI,
                    help=f"prepensionamento: anni di anticipo sull'età di pensione "
                         f"({C.ETA_PENS}). Default {C.PREPENS_ANNI}: eleggibili i "
                         f"{C.ETA_PENS-C.PREPENS_ANNI}-{C.ETA_PENS-1}enni")
    ap.add_argument("--prepens-ades", type=float, default=C.PREPENS_ADES,
                    help="prepensionamento: adesione annua degli aventi diritto al CENTRO "
                         f"della finestra (default {C.PREPENS_ADES}). Con 0 la leva è "
                         "spenta e il modello torna quello senza prepensionamento.")
    ap.add_argument("--prepens-centro", type=int, default=C.PREPENS_CENTRO,
                    help=f"prepensionamento: anno centrale della finestra (default "
                         f"{C.PREPENS_CENTRO}). Centrarla sul picco dell'organico invece "
                         "che prima lascia un buco e un rimbalzo: vedi --prepens-centro-auto")
    ap.add_argument("--prepens-centro-auto", action="store_true",
                    help="prepensionamento: ricava il centro dai dati invece di usare "
                         f"il {C.PREPENS_CENTRO} fisso (= picco dell'organico a leva spenta "
                         "meno --prepens-anni). Serve quando altre leve spostano il picco.")
    ap.add_argument("--prepens-sigma", type=float, default=C.PREPENS_SIGMA,
                    help=f"prepensionamento: semi-ampiezza gaussiana della finestra in anni "
                         f"(default {C.PREPENS_SIGMA}; la leva è spenta oltre 3 sigma dal centro)")
    ap.add_argument("--prepens-coda", type=float, default=C.PREPENS_CODA,
                    help="prepensionamento: anni in cui l'anticipo concesso scende da "
                         "--prepens-anni a 1 dopo il centro, per non lasciare assenze "
                         f"strascicate oltre la gobba (default {C.PREPENS_CODA} = anticipo "
                         "costante)")
    ap.add_argument("--prepens-asimm", type=float, default=C.PREPENS_ASIMM,
                    help="prepensionamento: sigma della metà destra della finestra in "
                         f"multipli di --prepens-sigma (default {C.PREPENS_ASIMM} = "
                         "simmetrica; <1 chiude prima di quanto ha aperto)")
    a = ap.parse_args()
    C.PREPENS_ANNI, C.PREPENS_ADES, C.PREPENS_SIGMA = (a.prepens_anni, a.prepens_ades,
                                                 a.prepens_sigma)
    C.PREPENS_CODA, C.PREPENS_ASIMM = a.prepens_coda, a.prepens_asimm
    # None fa scattare la regola di _centro_finestra dentro simula()
    C.PREPENS_CENTRO = None if a.prepens_centro_auto else a.prepens_centro
    C.P2_HIST, C.PERM_OGGI, C.PRECARI_ANNI, C.RAMP = a.p2_hist, a.perm_oggi, a.precari_anni, a.ramp
    C.RIC_UNI_RUOLO_OGGI = a.ric_uni_ruolo_oggi
    C.P2_MIN = a.p2_min
    C.STAB_PHD, C.PHD_IN_FTE, C.D_RTT = a.stab_phd, a.phd_in_fte, a.rtt_anni
    C.EPR_PRECARI_OGGI, C.EPR_RUOLO_OGGI = a.epr_precari, a.epr_ruolo
    C.EPR_RICERC_OGGI = C.EPR_PRECARI_OGGI + C.EPR_RUOLO_OGGI
    C.COSTO_EPR_RUOLO, C.P2_TGT = a.costo_epr_ruolo, a.p2_tgt
    C.QUOTA_RIC_UNI, C.UPLIFT_PPP = a.quota_ric_uni, a.uplift_ppp
    # Vincolo di stabilizzazione. Con P2_univ = P2_EPR = 1 (nessun imbuto interno)
    # si riduce a P1 = STAB_PHD: tutta la selezione è all'uscita dal dottorato.
    # (Con P2_univ < 1 l'EPR, che stabilizza al 100%, alza di poco la media: è un
    # flusso di rimpiazzo piccolo, quindi si approssima col solo ramo universitario.)
    C.P1 = min(1.0, C.STAB_PHD / C.P2_TGT)
    C.BORSA_TGT = a.borsa_tgt
    C.W_PHD = C.BORSA_TGT / C.BORSA_OGGI
    C.COSTO["dottorando"] = a.costo_phd
    C.OUT = a.out
    os.makedirs(C.OUT, exist_ok=True)
    C.TA_ELAST, C.COSTO_TA, C.TA_SEGUE_W = a.ta_elast, a.costo_ta, a.ta_segue_w
    C.QUOTA_ESENTE_PREC_UNI = a.quota_esente_postdoc
    # Densità iniziale RICAVATA dagli stock, non imposta. Va fatto prima di ogni
    # calibrazione: FTE_OGGI è la base del TA e l'ancora del ramo universitario.
    # I precari chiudono il gap: dipendono da PERM_OGGI, P2_HIST, D_RTT e PRECARI_ANNI,
    # quindi vanno risolti DOPO che tutti quelli sono stati letti dalla CLI.
    C.PRECARI_OGGI = _precari_per_chiudere() if a.precari_oggi is None else a.precari_oggi
    C.FTE_OGGI = _fte_uni_oggi()
    C.DENS_OGGI = C.FTE_OGGI / C.POP_100K
    # livelli di TA dal rapporto misurato: così il TA segue il perimetro del modello
    C.TA_UNI_OGGI = C.TA_UNI_RATIO * C.FTE_OGGI
    C.TA_EPR_OGGI = C.TA_EPR_RATIO * C.EPR_RICERC_OGGI * C.ALPHA_EPR
    # studenti impliciti nel rapporto di partenza, sul denominatore in FTE didattici
    C.STUDENTI_OGGI = C.STUD_DOC_OGGI * _fte_didattico(_init_stato(0.0))
    # ORDINE OBBLIGATO: lambda dipende dal TA (esplicito), il supporto residuo dipende
    # da lambda, l'overhead EPR dal supporto. Invertirli dà una calibrazione incoerente.
    C.LAMBDA_HE = _calibra_lambda_he() if a.lambda_he is None else a.lambda_he
    C.SUPPORTO = _calibra_supporto() if a.supporto is None else a.supporto
    C.OVH_EPR_SUPP, C.OVH_EPR_ATTR = _calibra_overhead_epr()

    base_herd = _herd_base()
    quota_reg = regime_shares(C.PRECARI_ANNI)["docente"]
    phd_oggi = _pd_in0() * C.D_PHD

    # la quota-ricercatori è una leva solo del terzo scenario: FLC ed ERA restano
    # i baseline tutto-cattedre, così il confronto isola l'effetto della riforma.
    _q = C.QUOTA_RIC_UNI
    C.QUOTA_RIC_UNI = 0.0
    d_era = densita_iso_herd(C.HERD_TGT, 1.0, C.PRECARI_ANNI, C.W_PHD)
    C.QUOTA_RIC_UNI = _q
    d_ppp = densita_iso_herd(C.HERD_TGT, C.UPLIFT_PPP, C.PRECARI_ANNI, C.W_PHD)
    C.QUOTA_RIC_UNI = 0.0
    scen = {
        "FLC":          (140.0, 1.0, 0.0),
        "ERA":          (d_era, 1.0, 0.0),
        "ERA_PPP_ric":  (d_ppp, C.UPLIFT_PPP, _q),
    }
    dfs = {nome: simula(t, W, q) for nome, (t, W, q) in scen.items()}

    print("#" * 82)
    print("# TRANSIZIONE DINAMICA - stato stazionario da imbuto")
    print(f"# param: P2_hist={C.P2_HIST} | ruolo_oggi={C.PERM_OGGI:,} | precari_anni={C.PRECARI_ANNI} "
          f"| ramp={C.RAMP}a")
    print(f"# leve (P2, flusso PhD, paghe W, borsa W_phd) rampate dal {C.ANNO0} e a REGIME dal {C.ANNO0 + C.RAMP}; "
          f"ingresso in ruolo a {eta_ruolo_in(C.PRECARI_ANNI)} anni, durata ruolo {perm_dur(C.PRECARI_ANNI)}a")
    print(f"# IMBUTO a regime: PhD -(P1={C.P1:.2f})-> [univ -(P2={C.P2_TGT:.2f})-> ruolo | "
          f"EPR -(Madia,P2={C.P2_EPR:.2f})-> ruolo] => {C.STAB_PHD*100:.0f}% stabilizzato")
    print(f"# UNICO FILTRO all'uscita dal dottorato: P1 scende da {_p1_hist():.2f} (oggi) "
          f"a {C.P1:.2f}; chi passa ha la carriera garantita")
    if _p1_hist() > 1.0:
        print(f"#   /!\\ P1 storico > 1: il precariato del 2026 è più GRANDE di quanto il "
              f"flusso di dottori possa rimpiazzare ({_uni_in0()+_epr_in0():,.0f} ingressi "
              f"servono, {C.PHD_OGGI_REALE/C.D_PHD:,.0f} dottori escono).")
        print(f"#       Non è un errore di calibrazione: è la bolla PNRR: uno stock "
              f"gonfiato da un finanziamento straordinario e non sostenibile a regime. "
              f"Il motore lo gestisce")
        print(f"#       (prosegue = min(serve, escono)), quindi il precariato inizia a "
              f"sgonfiarsi già dall'anno 0 invece di restare al livello di partenza.")
    print(f"# EPR: {C.EPR_RICERC_OGGI:,} ricercatori COSTANTI ({C.EPR_RUOLO_OGGI:,} ruolo + "
          f"{C.EPR_PRECARI_OGGI:,} precari oggi -> {_epr_in_tgt()*C.PERM_DUR_EPR:,.0f} + "
          f"{_epr_in_tgt()*C.D_PREC_EPR:,.0f} a regime); flusso di rimpiazzo "
          f"{_epr_in0():,.0f} -> {_epr_in_tgt():,.0f}/anno")
    print(f"# GOVERD 'oggi' del modello: {_goverd_base():.2f}% PIL (obiettivo {C.GOVERD_TGT}%) | "
          f"overhead FISSO: residuo {C.OVH_EPR_SUPP/1e6:,.0f} mln + infrastruttura "
          f"{C.OVH_EPR_ATTR/1e6:,.0f} mln [auto-calibrato, al netto del TA esplicito]")
    print(f"# BORSA PhD: {C.BORSA_OGGI:.0f} -> {C.BORSA_TGT:.0f} EUR/mese netti (x{C.W_PHD:.2f}), "
          f"costo lordo ente {C.COSTO['dottorando']:,.0f} -> {C.COSTO['dottorando']*C.W_PHD:,.0f} EUR/anno")
    print(f"# DOTTORANDI oggi nel modello: {phd_oggi:,.0f} teste "
          f"(reale ~{C.PHD_OGGI_REALE:,}: scarto {phd_oggi/C.PHD_OGGI_REALE-1:+.0%}) | "
          f"PhD contati negli FTE: {'SI' if C.PHD_IN_FTE else 'NO'}")
    _s0 = _init_stato(0.0)
    _f0 = _fte(_s0)
    print(f"# STATO INIZIALE da stock OSSERVATI (MUR 2023 + precari PNRR), non da un "
          f"target di densità:")
    print(f"#   PO+PA {C.PERM_OGGI:,} x{C.ALPHA['docente']:.2f} = {_f0['docente']:,.0f} | "
          f"ric.indet {C.RIC_UNI_RUOLO_OGGI:,} x{C.ALPHA['ric_uni']:.2f} = {_f0['ric_uni']:,.0f} | "
          f"precari {C.PRECARI_OGGI:,.0f} x{C.ALPHA['precari']:.2f} = {_f0['precari']:,.0f} | "
          f"RTT {sum(_s0.rtt):,.0f} x{C.ALPHA['RTT']:.2f} = {_f0['RTT']:,.0f}")
    print(f"#   => {C.FTE_OGGI:,.0f} FTE ricostruiti contro {C.RIC_UNI_EUROSTAT:,.0f} Eurostat "
          f"(HES, ricercatori, 2023): scarto {C.FTE_OGGI-C.RIC_UNI_EUROSTAT:+,.0f} FTE "
          f"({C.FTE_OGGI/C.RIC_UNI_EUROSTAT-1:+.1%})")
    _chiuso = a.precari_oggi is None
    if _chiuso:
        print(f"#   gap CHIUSO sui precari: {C.PRECARI_OGGI:,.0f} contro i 25.113 osservabili "
              f"dal MUR (RTD-A + assegni) e i ~35.000 stimati con l'onda PNRR "
              f"({C.PRECARI_OGGI/35_000-1:+.0%}).")
        print(f"#       SCELTA di attribuzione: tutto lo scarto di perimetro finisce "
              f"nel precariato. Le alternative erano i dottorandi in parte fra i "
              f"ricercatori,")
        print(f"#       o alpha_docente sopra 0,50. Usa --precari-oggi 35000 per tornare "
              f"alla stima e vedere il gap dichiarato.")
    elif abs(C.FTE_OGGI / C.RIC_UNI_EUROSTAT - 1) > 0.03:
        print(f"#   /!\\ NON TORNA. Le spiegazioni candidate, in ordine di plausibilità:")
        print(f"#       (a) il perimetro HES di Frascati è più largo del personale MUR "
              f"(docenti a contratto, ricerca dei policlinici universitari, enti non-MUR);")
        print(f"#       (b) i dottorandi sono in parte contati fra i ricercatori: ne "
              f"basterebbe il {(C.RIC_UNI_EUROSTAT-C.FTE_OGGI)/C.ALPHA['dottorando']/C.PHD_OGGI_REALE:.0%} "
              f"a alpha {C.ALPHA['dottorando']:.2f} per chiudere;")
        print(f"#       (c) alpha_docente {C.ALPHA['docente']:.2f} è troppo basso: servirebbe "
              f"{(C.RIC_UNI_EUROSTAT-_f0['precari']-_f0['RTT']-_f0['ric_uni'])/C.PERM_OGGI:.3f}.")
    # Test indipendente: l'RTT NON è usato per calibrare niente, quindi il confronto
    # è informativo. Chiudere il gap sui precari lo peggiora per costruzione.
    _rtt_oss = 6_915        # RTD-B + L.79/2022, MUR 2023
    _p2_coerente = _rtt_oss / (_uni_in0() * C.D_RTT) if _uni_in0() > 0 else 0.0
    print(f"#   RTT ricostruito {sum(_s0.rtt):,.0f} contro {_rtt_oss:,} osservati "
          f"(RTD-B + L.79/2022, MUR 2023): scarto {sum(_s0.rtt)/_rtt_oss-1:+.1%}")
    if abs(sum(_s0.rtt) / _rtt_oss - 1) > 0.05:
        print(f"#       <- il PREZZO della chiusura: con {C.PRECARI_OGGI:,.0f} precari e "
              f"P2_HIST={C.P2_HIST:.2f} il modello genera troppi RTT. Per tenerli sul dato "
              f"servirebbe P2_HIST={_p2_coerente:.3f},")
        print(f"#       cioè una stabilizzazione storica più bassa: un bacino di precari "
              f"più grande a parità di posti di tenure track. Coerente, ma P2_HIST "
              f"smette di essere un dato e diventa un residuo.")
    print(f"# oggi {C.DENS_OGGI:.1f} FTE/100k | flusso PhD ~{_pd_in0():,.0f}/anno | "
          f"quota-docente a regime {quota_reg*100:.0f}% "
          f"({'cattedre' if quota_reg >= 0.65 else 'più precari-heavy'})")
    _s0 = _init_stato(_pd_in0())
    _ta_u, _ta_e = _ta_uni(_fte_ric_uni(_s0)), _ta_epr(_fte_epr(_s0))
    print(f"# TA ESPLICITO (Eurostat 2023, FTE): università {C.TA_UNI_OGGI:,.0f} + enti "
          f"{C.TA_EPR_OGGI:,.0f} = {C.TA_UNI_OGGI+C.TA_EPR_OGGI:,.0f} FTE "
          f"({(C.TA_UNI_OGGI+C.TA_EPR_OGGI)/C.ALPHA_TA:,.0f} teste a alpha {C.ALPHA_TA:.3f}), "
          f"{C.COSTO_TA:,.0f} EUR/testa-anno")
    print(f"#   elasticità TA_ELAST={C.TA_ELAST:.2f}: ricercatori x2 -> TA x{1+C.TA_ELAST:.2f}"
          f" | quota TA oggi {(_ta_u+_ta_e)/(_fte_ric_uni(_s0)+_fte_epr(_s0)+_ta_u+_ta_e)*100:.1f}%"
          f" -> asintoto {C.TA_ELAST*(C.TA_UNI_OGGI+C.TA_EPR_OGGI)/(C.FTE_OGGI+C.RIC_EPR_OGGI+C.TA_ELAST*(C.TA_UNI_OGGI+C.TA_EPR_OGGI))*100:.1f}%"
          f" | stipendi TA {'seguono' if C.TA_SEGUE_W else 'NON seguono'} W")
    print(f"# LAMBDA_HE (quota-lavoro dell'HERD) = {C.LAMBDA_HE:.3f} "
          f"{'[RICAVATA dai costi del personale]' if a.lambda_he is None else '[imposta]'}"
          f" -> attrezzature {(1-C.LAMBDA_HE)*100:.0f}% dell'HERD")
    if C.LAMBDA_HE > 0.90:
        print(f"#   /!\\ sopra 0,90: l'università non comprerebbe quasi strumenti. "
              f"Sospetta i costi unitari o HERD_OGGI, non accettare il valore.")
    print(f"# SUPPORTO (residuo non nominato): +{C.SUPPORTO*100:.1f}% sul costo-ricerca del "
          f"personale strutturato {'[auto-calibrato]' if a.supporto is None else '[imposto]'}"
          f"{'  <- a zero: il TA esplicito spiega tutto il supporto' if C.SUPPORTO < 1e-9 else ''}")
    dq = densita_iso_herd(C.HERD_TGT, C.UPLIFT_PPP, C.PRECARI_ANNI, C.W_PHD)
    d0 = densita_iso_herd(C.HERD_TGT, 1.0, C.PRECARI_ANNI, C.W_PHD)
    print(f"# COMPROMESSO: {C.QUOTA_RIC_UNI*100:.0f}% del ruolo a profilo ricercatore "
          f"(alpha {C.ALPHA['ric_uni']}, {C.COSTO['ric_uni']:,.0f} EUR) => a HERD {C.HERD_TGT}% "
          f"e parità PPP la densità è {dq:.0f} FTE/100k (senza: {d0:.0f} a paghe odierne)")
    _eu = abs(C.UPLIFT_PPP - C.UPLIFT_PPP_EU) < 1e-9
    print(f"# UPLIFT PPP x{C.UPLIFT_PPP:.3f} = "
          + (f"MEDIA EUROPEA {C.REDDITO_PHD_EU:,} / Italia {C.REDDITO_PHD_IT:,}"
             if _eu else f"paniere selezionato / Italia {C.REDDITO_PHD_IT:,}")
          + f", reddito dei dottori di ricerca a PPP [ReICO, Commissione UE + OCSE].")
    if _eu:
        print(f"#     CONFERMA a vent'anni di distanza: la media UE25 della tabella CARSA "
              f"2006 dà x{C.UPLIFT_PPP_CARSA06_UE25:.3f}, cioè "
              f"{C.UPLIFT_PPP/C.UPLIFT_PPP_CARSA06_UE25-1:+.1%}. Due fonti indipendenti, "
              f"stesso traguardo.")
        print(f"#     NON in uso: il paniere dei 5 paesi che pagano meglio darebbe "
              f"x{C.UPLIFT_PPP_TOP5:.3f} (CARSA sui 5 UE migliori: x{C.UPLIFT_PPP_CARSA06:.3f}). "
              f"È lo scenario molto ottimista, --uplift-ppp {C.UPLIFT_PPP_TOP5:.4f}.")
    else:
        print(f"#     /!\\ NON è il default: il modello usa la media europea "
              f"(x{C.UPLIFT_PPP_EU:.3f}). Se questo è il paniere top-5, vale l'avvertenza "
              f"(a): NON è solo-UE (i due valori di testa\n"
              f"#     sono verosimilmente extra-UE; sui 3 dietro gli outlier sarebbe x1.47).")
    print(f"# /!\\ Avvertenza che vale in ogni caso: la popolazione ReICO sono i dottori di "
          f"ricerca di TUTTI i settori, non i ricercatori accademici, mentre il modello "
          f"applica W\n"
          f"#     a docenti, RTT, postdoc e borse. Vedi il commento su UPLIFT_PPP nel sorgente.")
    print(f"# HERD 'oggi' del modello: {base_herd:.2f}% PIL (ISTAT {C.HERD_OGGI}%: "
          f"scarto {base_herd - C.HERD_OGGI:+.2f}pp)")
    print("#" * 82)

    # ---- stabilizzazione EPR a organico costante ----
    print(f"\n[STABILIZZAZIONE EPR] organico costante {C.EPR_RICERC_OGGI:,} ricercatori: "
          f"quanto costa togliere il precariato, senza espandere")
    ts = _tabella_stabilizzazione()
    print(ts.to_string(index=False))
    g = ts["GOVERD_%PIL"].iloc[-1]
    print(f"  -> a regime GOVERD {C.GOVERD_OGGI}% -> {g:.3f}% "
          f"(+{(g-C.GOVERD_OGGI)/100*C.PIL_MLN:,.0f} mln/anno di spesa R&S; "
          f"+{ts['d_budget_mln'].iloc[-1]:,.0f} mln di monte stipendi) | obiettivo "
          f"{C.GOVERD_TGT}%: {'DENTRO' if g <= C.GOVERD_TGT else f'SFORATO di {g-C.GOVERD_TGT:.3f}pp'}")

    # ---- frontiera iso-HERD ----
    print(f"\n[FRONTIERA ISO-HERD {C.HERD_TGT}%] alzare le paghe => ridurre il personale a HERD fisso")
    fr = []
    C.QUOTA_RIC_UNI = 0.0
    # le due varianti restano affiancate in tabella: fra loro ci sono ~17 FTE/100k,
    # cioè l'età dei dati vale più di molte leve del modello
    for W in sorted({1.00, C.UPLIFT_PPP_EU, C.UPLIFT_PPP_CARSA06_UE25, C.UPLIFT_PPP_PLI24,
                     1.45, C.UPLIFT_PPP_TOP5, C.UPLIFT_PPP_CARSA06, C.UPLIFT_PPP}):
        d = densita_iso_herd(C.HERD_TGT, W, C.PRECARI_ANNI, C.W_PHD)
        teste_tot = d * C.POP_100K * teste_per_fte(C.PRECARI_ANNI)
        quota_phd = _contrib(C.P2_TGT, C.PRECARI_ANNI)[0]["dottorando"] / sum(_contrib(C.P2_TGT, C.PRECARI_ANNI)[0].values())
        fr.append({"W_paghe": round(W, 3), "densita_FTE/100k": round(d),
                   "teste_totali": round(teste_tot),
                   "di_cui_PhD": round(teste_tot * quota_phd),
                   "HERD_%PIL": C.HERD_TGT,
                   "nota": ("ReICO media UE [IN USO]" if W == C.UPLIFT_PPP_EU else
                            "ReICO top-5 (molto ottimista)" if W == C.UPLIFT_PPP_TOP5 else
                            "CARSA 2006 media UE25 (conferma)" if W == C.UPLIFT_PPP_CARSA06_UE25 else
                            "CARSA 2006 top-5 UE" if W == C.UPLIFT_PPP_CARSA06 else
                            "CARSA, deflatore PLI 2024" if W == C.UPLIFT_PPP_PLI24 else "")})
    print(pd.DataFrame(fr).to_string(index=False))
    d1 = densita_iso_herd(C.HERD_TGT, 1.0, C.PRECARI_ANNI, C.W_PHD)
    d2 = densita_iso_herd(C.HERD_TGT, C.UPLIFT_PPP, C.PRECARI_ANNI, C.W_PHD)
    print(f"  -> a HERD {C.HERD_TGT}% fisso, parità PPP (x{C.UPLIFT_PPP:.2f}): "
          f"{d1:.0f} -> {d2:.0f} FTE/100k = -{(1-d2/d1)*100:.0f}% personale.")

    # ---- prepensionamento: quanto è servito, e quanto costa ----
    if _prepens_on():
        print(f"\n[PREPENSIONAMENTO] finestra gaussiana sigma={C.PREPENS_SIGMA:g}a, "
              f"anticipo fino a {C.PREPENS_ANNI}a (eleggibili i {C.ETA_PENS-C.PREPENS_ANNI}"
              f"-{C.ETA_PENS-1}enni), adesione {C.PREPENS_ADES:.0%} al centro")
        pre, coda = [], False
        for nome, (t, W, q) in scen.items():
            df, df0 = dfs[nome], simula_senza_prepens(t, W, q)
            reg = _teste_tot(df0).iloc[-1]
            picco0 = _anno_picco(t, W, q)
            r = {"scenario": nome, "picco": picco0,
                 "centro": (C.PREPENS_CENTRO if C.PREPENS_CENTRO is not None
                            else _centro_finestra(t, W, q))}
            # l'oscillazione ha PIÙ fasi e vanno misurate tutte, altrimenti si scambia
            # per successo una sovracorrezione: la CONCA (2036-2048, la campana di
            # partenza è già uscita e le nuove leve non sono arrivate), la GOBBA
            # (2050-2065, eccesso di organico) e il BUCO che la leva può scavare DOPO
            # il picco. Solo il terzo è colpa della leva; la conca non la tocca nessuna
            # configurazione, perchè è una carenza e si riempie assumendo prima.
            for tag, d in (("base", df0), ("con", df)):
                dev = (_teste_tot(d) / reg - 1) * 100
                r[f"conca_{tag}_%"] = round(dev[d["anno"].between(2030, 2050)].min(), 1)
                r[f"gobba_{tag}_%"] = round(dev[d["anno"].between(2045, 2080)].max(), 1)
                r[f"buco_{tag}_%"] = round(dev[d["anno"] > picco0].min(), 1)
            r["teste_uscite"] = round(df["prepensionati"].sum())
            r["pens_mld_picco"] = round(df["pensioni_anticipate_mln"].max() / 1000, 2)
            # se non è ~0 la finestra sta ancora agendo a fine orizzonte: lo stato
            # stazionario non è più quello senza leva e il confronto salta
            r["scarto_2080_%"] = round(
                (_teste_tot(df).iloc[-1] / _teste_tot(df0).iloc[-1] - 1) * 100, 2)
            coda = coda or abs(r["scarto_2080_%"]) > 0.1
            pre.append(r)
        print(pd.DataFrame(pre).to_string(index=False))
        print("  -> conca/gobba/buco = massimo scostamento dallo stato stazionario in "
              "difetto PRIMA della gobba,\n     in eccesso, e in difetto DOPO il picco. "
              "La leva agisce sulla gobba; il buco dev'essere ~0.")
        print("  -> la leva ANTICIPA uscite, non taglia organico: a orizzonte lo stato "
              "stazionario resta quello\n     senza prepensionamento (scarto_2080 ~ 0). "
              "Alzare adesione o anticipo oltre il default non liscia\n     di più: "
              "converte la gobba in un buco subito dopo la finestra.")
        print("  -> /!\\ le pensioni anticipate NON sono in HERD/GOVERD (un pensionato non "
              "è personale di R&S) nè\n     nel budget: sul solo bilancio della ricerca "
              "la leva sembra un risparmio, ma è una partita di giro\n     verso la "
              f"previdenza, stimata a {C.TASSO_SOST:.0%} dell'ultimo lordo.")
        if coda:
            print(f"  -> /!\\ con sigma={C.PREPENS_SIGMA:g} la finestra (+/-3 sigma) è ancora "
                  f"aperta nel {C.ANNO0+C.ORIZZONTE}: lo stato stazionario\n     è alterato e "
                  "NON è più confrontabile. Riduci sigma o anticipa il centro.")

    # ---- retroflusso fiscale ----
    # Domanda: la spesa del piano sono stipendi, e uno stipendio pubblico e' in parte
    # una partita di giro. Quanto ne torna? Il conto e' meccanico (nessun
    # moltiplicatore, nessun indotto), ma va fatto pro capite perche' l'IRPEF e'
    # progressiva: vedi irpef.py per il perche' le masse non bastano.
    _s0 = _init_stato(_pd_in0())
    _sp0, _spe0 = _spesa(_s0, 1.0, 1.0), _spesa_epr(_s0, 1.0, C.COSTO_EPR_PREC_OGGI)
    _v0 = _voci(_s0, 1.0, 1.0, C.COSTO_EPR_PREC_OGGI, _sp0["ta_fte"], _spe0["ta_fte"],
                C.QUOTA_ESENTE_PREC_UNI)
    print(f"\n[RETROFLUSSO FISCALE] la spesa sono stipendi: quanto ne rientra come IRPEF")
    print(f"  scomposizione del costo lordo ente (gross-up {C.GROSS_UP_DIP:.4f} = oneri "
          f"{C.ALIQ_ONERI_ENTE:.2%} + IRAP {C.ALIQ_IRAP:.2%}), fisco vigente tenuto fermo "
          f"al {C.ANNO0 + C.ORIZZONTE}:")
    print(f"  {'figura':<24}{'teste':>9}{'costo ente':>12}{'lordo':>10}{'imponibile':>12}"
          f"{'IRPEF':>10}{'aliq.':>8}")
    for v in sorted(_v0, key=lambda x: -x.costo):
        sc = scomponi(v)
        print(f"  {v.nome:<24}{v.teste:>9,.0f}{v.costo:>12,.0f}"
              f"{sc['ral']/v.teste:>10,.0f}{sc['imponibile']/v.teste:>12,.0f}"
              f"{sc['irpef']/v.teste:>10,.0f}"
              + (f"{sc['irpef']/sc['imponibile']:>8.1%}" if sc["irpef"] else
                 f"{'esente':>8}"))
    if _quadratura(_v0) > 1e-9:
        print(f"  /!\\ la scomposizione NON quadra col costo lordo ente "
              f"(scarto {_quadratura(_v0):.2e}): il retroflusso perde o inventa denaro.")
    # test di coerenza col resto del modello: il monte stipendi ricostruito qui deve
    # essere il budget del modello MENO le attrezzature, che non sono stipendi
    _r0 = retroflusso(_v0)
    _bud0 = (_sp0["budget_mln"] + _spe0["budget_epr_mln"]) * 1e6
    print(f"  monte stipendi {C.ANNO0} = {_r0['costo']/1e9:.2f} mld su {_bud0/1e9:.2f} mld di "
          f"budget ({_r0['costo']/_bud0:.0%}); il resto sono attrezzature, che non pagano "
          f"IRPEF e restano fuori.")
    rf = []
    for nome, (t, W, q) in scen.items():
        df = dfs[nome]
        f0, f1 = df.iloc[0], df.iloc[-1]
        rf.append({
            "scenario": nome,
            f"IRPEF_{C.ANNO0}_mld": round(f0["irpef_mln"] / 1000, 2),
            "IRPEF_2080_mld": round(f1["irpef_mln"] / 1000, 2),
            "aliq_media_2080": round(f1["aliq_irpef_media"], 3),
            "IRPEF_su_stipendi_2080": round(f1["irpef_quota_stip"], 3),
            "cum_spesa_mld": round((df["budget_univ_mld"] + df["budget_epr_mld"]).sum()),
            "cum_stipendi_mld": round(df["monte_stip_mln"].sum() / 1000),
            "cum_IRPEF_mld": round(df["irpef_mln"].sum() / 1000),
            "cum_retro_mld": round(df["retro_mln"].sum() / 1000),
        })
    print(f"\n  TOTALI CUMULATI {C.ANNO0}-{C.ANNO0+C.ORIZZONTE}: SOMMA di "
          f"{C.ORIZZONTE+1} annualita', EUR{C.ANNO0} costanti, NON attualizzata.")
    print(f"  NON sono importi annui: il piano vale ~13 mld/anno a regime, e sono i 55 "
          f"anni a fare le centinaia di miliardi.")
    print(pd.DataFrame(rf).to_string(index=False))
    print(f"\n  COSTO DEL PIANO al netto del rientro fiscale (maggior costo rispetto al "
          f"{C.ANNO0}), prima a REGIME e poi cumulato:")
    for nome in scen:
        df = dfs[nome]
        d = df["dStato_univ_mld"] + df["dStato_epr_mld"]
        lordo, irp, retro = d.sum(), df["dIRPEF_mld"].sum(), df["dRetro_mld"].sum()
        f = df.iloc[-1]
        print(f"  {nome:<12} a regime {d.iloc[-1]:>5.1f} mld/anno lordi -> "
              f"{d.iloc[-1]-f['dIRPEF_mld']:>5.1f} netto IRPEF -> "
              f"{d.iloc[-1]-f['dRetro_mld']:>5.1f} netto di tutti i prelievi   ||   "
              f"cumulati su {C.ORIZZONTE+1} anni: {lordo:>4,.0f} -> "
              f"{lordo-irp:>4,.0f} ({irp/lordo:.0%} rientra) -> {lordo-retro:>4,.0f} "
              f"({retro/lordo:.0%})")
    _q = dfs["ERA_PPP_ric"]
    print(f"  -> a regime l'IRPEF vale {_q['irpef_quota_stip'].iloc[-1]:.0%} del monte "
          f"stipendi e {_q['irpef_mln'].iloc[-1]/(_q['budget_univ_mld'].iloc[-1]+_q['budget_epr_mld'].iloc[-1])/1000:.0%} "
          f"della spesa totale; con addizionali, contributi e IRAP si arriva al "
          f"{_q['retro_quota_stip'].iloc[-1]:.0%} degli stipendi.")
    print(f"  -> l'aliquota media sale dal {dfs['ERA_PPP_ric']['aliq_irpef_media'].iloc[0]:.1%} "
          f"al {_q['aliq_irpef_media'].iloc[-1]:.1%}: il piano non aggiunge solo teste, "
          f"le sposta verso il ruolo e alza le paghe, e l'IRPEF e' progressiva.\n"
          f"     Il ritorno fiscale cresce quindi PIU' CHE PROPORZIONALMENTE alla spesa.")
    # sensitivita' sulla quota esente dei postdoc: e' l'incertezza piu' grande del
    # retroflusso dei primi anni, perche' il MUR non separa 18.282 delle 43.395
    # posizioni e non si sa quante siano borse o incarichi di ricerca (esenti)
    # IRPEF di UN postdoc tassato: e' il moltiplicatore che spiega l'ampiezza della
    # forchetta, e va detto perche' altrimenti la si attribuisce alla platea
    _v0_pd = scomponi(Voce("postdoc", 1.0, C.COSTO["precari"]))["irpef"]
    _sens = []
    for _q_es, _et in ((15_891 / 43_395, "solo assegni certi"),
                       (C.QUOTA_ESENTE_PREC_UNI, "mix osservabile MUR [IN USO]"),
                       ((15_891 + 18_282) / 43_395, "tutti i non separati esenti")):
        _salva, C.QUOTA_ESENTE_PREC_UNI = C.QUOTA_ESENTE_PREC_UNI, _q_es
        _d = simula(*scen["ERA_PPP_ric"])
        C.QUOTA_ESENTE_PREC_UNI = _salva
        _sens.append({"quota_esente_2026": round(_q_es, 3),
                      "teste_esenti": round(_q_es * C.PRECARI_OGGI),
                      f"IRPEF_{C.ANNO0}_mld": round(_d["irpef_mln"].iloc[0] / 1000, 2),
                      "IRPEF_2080_mld": round(_d["irpef_mln"].iloc[-1] / 1000, 2),
                      # una cifra decimale, non zero: a interi le tre righe sembrano
                      # identiche e si perde proprio l'informazione che serve
                      "cum_IRPEF_mld": round(_d["irpef_mln"].sum() / 1000, 1),
                      "ipotesi": _et})
    print(f"\n  SENSITIVITA' sui postdoc esenti (assegni + borse + incarichi di ricerca, "
          f"art. 6 c.6 L.398/1989 e art. 4 c.3 L.210/1998), scenario ERA_PPP_ric:")
    print(pd.DataFrame(_sens).to_string(index=False))
    print(f"  -> la forchetta e' STRETTA, e non perche' la platea sia piccola: i postdoc "
          f"pagano poca IRPEF comunque ({_v0_pd:,.0f} EUR a testa, aliquota effettiva "
          f"bassa),\n     quindi esentarne 18.000 in piu' sposta il {C.ANNO0} di "
          f"~{_sens[0][f'IRPEF_{C.ANNO0}_mld']-_sens[-1][f'IRPEF_{C.ANNO0}_mld']:.2f} mld. "
          f"Sul cumulato sparisce del tutto: la quota esente scende a "
          f"{C.QUOTA_ESENTE_PREC_UNI_TGT:.0%} lungo la rampa e pesa su {C.RAMP} anni "
          f"su {C.ORIZZONTE+1}.")
    print(f"     Tornerebbe a contare solo se borse e incarichi SOPRAVVIVESSERO alla "
          f"riforma: e' l'ipotesi che sta in QUOTA_ESENTE_PREC_UNI_TGT, oggi a "
          f"{C.QUOTA_ESENTE_PREC_UNI_TGT:.0%}.")
    print(f"  -> /!\\ agli esenti il modello attribuisce il costo pieno del postdoc "
          f"({C.COSTO['precari']:,.0f}), perche' COSTO['precari'] e' un valore unico: la "
          f"quota corregge il REGIME FISCALE,\n     non il prezzo. Un assegno ne costava "
          f"{C.COSTO_EPR_ASSEGNO:,.0f}, quindi il monte stipendi {C.ANNO0} del ramo "
          f"universitario resta sovrastimato - ma e' una questione del ramo costi, "
          f"non del fisco.")
    _phd = _q["phd_teste"].iloc[-1] * C.COSTO["dottorando"] * C.W_PHD / 1e9
    print(f"  -> /!\\ le BORSE di dottorato sono esenti IRPEF (art. 4 L. 476/1984): "
          f"{_phd:.1f} mld/anno a regime che tornano solo come Gestione separata.\n"
          f"     Alzare una borsa costa allo Stato quasi il doppio, in termini netti, "
          f"di alzare uno stipendio dello stesso importo lordo.")
    print(f"  -> /!\\ NON e' un moltiplicatore: nessun indotto, nessuna IVA, nessun "
          f"effetto di comportamento. Solo il prelievo su buste paga che lo Stato "
          f"sta gia' pagando.\n"
          f"     E' un LIMITE INFERIORE del ritorno, non una stima del suo valore.")
    print(f"  -> /!\\ addizionali ({C.ADD_REGIONALE+C.ADD_COMUNALE:.2%}) e IRAP vanno a "
          f"Regioni e Comuni, non all'erario: chi guarda il solo bilancio dello Stato "
          f"legga la colonna IRPEF.")

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
        onda = df[df["anno"] <= C.ANNO0 + 20]
        picco = int(onda.loc[onda["pensionamenti"].idxmax(), "anno"])
        if anno90 < 0:
            quota = (df["densita"].iloc[-1] - df["densita"].iloc[0]) / (t - df["densita"].iloc[0])
            traguardo = f"90% del gap NON colmato entro il {C.ANNO0 + C.ORIZZONTE} (solo {quota*100:.0f}%)"
        else:
            traguardo = f"90% del gap colmato entro il {anno90} ({anno90 - C.ANNO0} anni)"
        print(f"  -> {traguardo}; onda pensionamenti picco ~{picco}.")

    # ---- grafico ----
    # le etichette portano il TARGET, che è cio' che definisce lo scenario; la densità
    # effettiva 2080 è più alta perchè la popolazione SSP2 scende, ed è annotata
    # direttamente sui grafici
    etich = {"FLC": f"FLC (target {scen['FLC'][0]:.0f})",
             "ERA": f"ERA paghe oggi (target {scen['ERA'][0]:.0f})",
             "ERA_PPP_ric": f"ERA PPP + ric.univ. (target {scen['ERA_PPP_ric'][0]:.0f})"}
    grafico_target(dfs, {n: v[0] for n, v in scen.items()}, etich,
                   f"{C.OUT}/transizione_fte.png")
    for nome, df in dfs.items():
        df.to_csv(f"{C.OUT}/transizione_{nome}.csv", index=False)

    # ---- report 2026-2050 ----
    # le righe del prepensionamento compaiono solo se la leva è accesa: a leva spenta
    # sarebbero tre righe di zeri in una tabella già fitta
    if _prepens_on():
        i = [e for e, _, _ in RIGHE_TAB].index("Pensionamenti/anno") + 1
        RIGHE_TAB[i:i] = [("Prepensionati/anno", "prepensionati", 0),
                          ("Pensioni anticipate in carico (teste)", "prepens_in_carico", 0),
                          ("Costo pensioni anticipate (mln EUR)", "pensioni_anticipate_mln", 0)]
    anni = [2026, 2030, 2035, 2040, 2050, 2060, 2070, 2080]
    for nome in ("FLC", "ERA_PPP_ric"):
        print(f"\n{'='*100}\nTABELLA {nome} - traiettoria {anni[0]}-{anni[-1]} "
              f"(target {scen[nome][0]:.0f} FTE/100k, paghe x{scen[nome][1]:.2f})\n{'='*100}")
        print(tabella_scenario(dfs[nome], anni).to_string())
    # i grafici si fermano a FINE_GRAFICI, le tabelle e i CSV no: gli ultimi anni sono
    # una linea piatta che ruba spazio alla transizione (vedi il commento in config)
    fg = C.FINE_GRAFICI
    grafico_trend(dfs, fg, f"{C.OUT}/trend_{C.ANNO0}_{fg}.png")
    grafico_ffo(dfs, fg, f"{C.OUT}/ffo_aggiuntivo.png")
    grafico_stack(dfs, fg, f"{C.OUT}/organico_stack.png", etich)
    grafico_spesa_stack(dfs, fg, f"{C.OUT}/spesa_stack.png", etich)
    print(f"\n[grafici] fino al {fg} (la simulazione arriva al {C.ANNO0+C.ORIZZONTE}: "
          f"tabelle e CSV restano a orizzonte pieno)")
    print(f"          {C.OUT}/trend_{C.ANNO0}_{fg}.png (14 pannelli: ricerca, TA, didattica) "
          f"+ {C.OUT}/ffo_aggiuntivo.png (mld/anno) "
          f"+ {C.OUT}/organico_stack.png (organico univ.+EPR) "
          f"+ {C.OUT}/spesa_stack.png (spesa per ramo, con la fascia IRPEF che rientra)")
    singoli = grafici_singolo("ERA_PPP_ric", dfs, fg, C.OUT, etich)
    print(f"[grafici] solo scenario ERA_PPP_ric, su file separati:\n           "
          + "\n           ".join(singoli))
    print("  NB: 'proxy FFO' = maggior costo del personale di ricerca a carico dello"
          " Stato.\n      L'FFO come voce di bilancio NON è modellato.")

    print("\n=== LETTURA ===")
    print(f"  densità 2080: 'SSP2' = a popolazione proiettata ({C.pop_100k(2080)/10:.1f} mln), "
          f"'pop.2026' = a demografia ferma ({C.pop_100k(C.ANNO0)/10:.1f} mln). Il target di "
          f"scenario è su quest'ultima.")
    for nome, (tg, W, q) in scen.items():
        f = dfs[nome].iloc[-1]
        print(f"  {nome:<12} densità SSP2 {f['densita']:.0f} (pop.2026 {f['densita_pop2026']:.0f}, "
              f"target {tg:.0f}) | HERD {f['HERD_%PIL']:.3f}% + GOVERD "
              f"{f['GOVERD_%PIL']:.3f}% | paghe x{W:.2f} | ric.univ. {q*100:.0f}% | "
              f"+{f['dStato_univ_mld']+f['dStato_epr_mld']:.1f} mld/anno")
    _fd0 = _fte_didattico(_init_stato(0.0))
    print(f"\n  [CARICO DIDATTICO] studenti per docente in FTE didattici (peso = 1-alpha: "
          f"prof {1-C.ALPHA['docente']:.2f}, ric.univ/RTT/postdoc {1-C.ALPHA['RTT']:.2f}; "
          f"dottorandi esclusi)")
    print(f"  denominatore {C.ANNO0} = {_fd0:,.0f} FTE-docente -> studenti impliciti "
          f"{C.STUDENTI_OGGI:,.0f}")
    for nome, df in dfs.items():
        sotto = df[df["stud_per_doc"] <= C.STUD_DOC_TGT]
        anno = int(sotto["anno"].iloc[0]) if len(sotto) else -1
        f30 = df[df["anno"] == C.ANNO0 + 30].iloc[0]
        fin = df.iloc[-1]
        print(f"  {nome:<12} {C.ANNO0}: {df['stud_per_doc'].iloc[0]:.2f} | "
              f"{C.ANNO0+30}: {f30['stud_per_doc']:.2f} | {C.ANNO0+C.ORIZZONTE}: "
              f"{fin['stud_per_doc']:.2f} (a studenti fermi) / {fin['stud_per_doc_pop']:.2f} "
              f"(studenti ~ pop.) | media UE {C.STUD_DOC_TGT} raggiunta nel "
              + (f"{anno}" if anno > 0 else "MAI"))
    print(f"  /!\\ In FTE didattici il rapporto si muove MOLTO meno che in teste PO/PA: la "
          f"transizione sposta persone dal precariato (peso {1-C.ALPHA['precari']:.2f}) al "
          f"ruolo (peso {1-C.ALPHA['docente']:.2f}),")
    print(f"      quindi ogni stabilizzazione vale {(1-C.ALPHA['docente'])/(1-C.ALPHA['RTT']):.0f}x "
          f"in capacità didattica. è l'effetto che conta, ed è invisibile se si contano "
          f"le teste.")
    print(f"      NB: il {C.STUD_DOC_OGGI} di partenza e il traguardo {C.STUD_DOC_TGT} devono "
          f"venire dallo stesso indicatore, altrimenti il confronto non è omogeneo.")
    print()
    print(f"  Il terzo scenario tiene INSIEME densità {scen['ERA_PPP_ric'][0]:.0f}, HERD "
          f"{C.HERD_TGT}% e parità PPP: i ricercatori universitari rendono 2x FTE per euro")
    print("  dei docenti, quindi servono MENO teste, non più.")
    if C.PRECARI_ANNI > 3:
        print(f"  Con precari_anni={C.PRECARI_ANNI}: flusso d'ingresso realistico (~{_pd_in0():,.0f}), "
              f"ma il regime NON è più cattedre (quota-docente {quota_reg*100:.0f}%): il")
        print(f"  precariato prolungato è esso stesso uno stock strutturale permanente.")
    print(f"\nFile: transizione_fte.png + transizione_*.csv (in {C.OUT})")


if __name__ == "__main__":
    main()
