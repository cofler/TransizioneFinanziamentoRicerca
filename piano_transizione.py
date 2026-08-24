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
import scenario
from regime import (_blocco_on, _contrib, _epr_in_tgt, _finestre, _ta_epr, _ta_uni,
                    costi_regime, densita_iso_herd, epr_in_diretto, epr_in_phd,
                    epr_in_rimpiazzo, epr_stock_regime, eta_ruolo_in, perm_dur,
                    regime_shares, teste_per_fte)
from motore import (_anno_picco, _centro_finestra, _epr_in0, _epr_in0_tot, _fte,
                    _fte_didattico,
                    _fte_epr, _fte_ric_uni, _fte_uni_oggi, _init_stato, _p1_hist,
                    _pd_in0, _precari_per_chiudere, _prepens_on, _spesa, _spesa_epr,
                    _teste_tot, _uni_in0, _voci, piano_attrezzature, simula,
                    simula_senza_blocco, simula_senza_prepens)
from irpef import Voce, _quadratura, retroflusso, scomponi
from calibrazione import (_calibra_anni_da_associato, _calibra_lambda_he,
                          _calibra_overhead_epr, _calibra_supporto, _goverd_base,
                          _herd_assoluto, _herd_base, _tabella_stabilizzazione,
                          _tempo_a_regime)
from tabelle import RIGHE_TAB, righe_con_prepens, tabella_scenario
from grafici import (grafici_singolo, grafico_ffo, grafico_spesa_stack,
                     grafico_stack, grafico_target, grafico_trend)


def main() -> None:
    ap = argparse.ArgumentParser(description="Transizione FTE verso il regime cattedre.")
    ap.add_argument("--out", type=str, default=C.OUT,
                    help="cartella di output per png/csv (default: cartella dello script)")
    ap.add_argument("--herd-tgt", type=float, default=C.HERD_TGT,
                    help=f"obiettivo di spesa HERD in %% PIL (default {C.HERD_TGT}); "
                         "si porta dietro HERD_RIF, il riferimento con cui si misura "
                         "il 3%% GERD")
    ap.add_argument("--goverd-tgt", type=float, default=C.GOVERD_TGT,
                    help=f"obiettivo di spesa GOVERD in %% PIL (default {C.GOVERD_TGT}); "
                         "e' anche il pavimento di spesa degli enti, salvo "
                         "--no-goverd-pavimento")
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
    ap.add_argument("--quota-po-tgt", type=float, default=C.QUOTA_PO_TGT,
                    help=f"quota di ordinari sui professori a REGIME (default "
                         f"{C.QUOTA_PO_TGT:.2f}; {C.QUOTA_PO:.2f} = composizione di "
                         "oggi portata avanti). Non e' un dato: e' la forma della "
                         "piramide accademica che si vuole a fine transizione, e il "
                         "modello la realizza spostando la soglia di anzianita' PA->PO")
    ap.add_argument("--rtt-anni", type=int, default=C.D_RTT,
                    help=f"durata del contratto RTT in anni (default {C.D_RTT}, L.79/2022; "
                         "usa 3 per l'ex RTD-B = tenure più rapida possibile)")
    ap.add_argument("--p2-tgt", type=float, default=C.P2_TGT,
                    help=f"postdoc->RTT a fine postdoc (default {C.P2_TGT} = passa metà "
                         "dei postdoc; 1.0 = nessun imbuto interno, tutta la selezione "
                         "all'uscita dal dottorato). P1 viene ricavato di conseguenza "
                         "dal vincolo di stabilizzazione")
    ap.add_argument("--stab-phd", type=float, default=C.STAB_PHD,
                    help=f"quota di dottori stabilizzati al ruolo = P1*P2 (default "
                         f"{C.STAB_PHD} = 0.50 x 0.50, due filtri in serie)")
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
    ap.add_argument("--phd-nel-diretto", type=float, default=C.PHD_NEL_DIRETTO_EPR,
                    help=f"quota del canale diretto EPR che richiede comunque il "
                         f"dottorato (default {C.PHD_NEL_DIRETTO_EPR}). L'altra parte è "
                         f"reclutata per concorso da laurea e NON pesa sul bacino dei "
                         f"dottorandi. 1.0 = il dottorato serve sempre")
    ap.add_argument("--no-goverd-pavimento", action="store_true",
                     help=f"spegne il pavimento sul GOVERD (default: la spesa del ramo "
                          f"enti non scende mai sotto il {C.GOVERD_MIN}%% del 2026, "
                         f"assumendo in ruolo quando serve)")
    ap.add_argument("--no-attrezzature", action="store_true",
                    help="spegne l'inviluppo di spesa (default: acceso). Le attrezzature "
                         "tornano a essere il solo residuo di calibrazione, la spesa "
                         "totale segue l'organico anche quando cala, il grafico di spesa "
                         "torna a due fasce e il trend perde il pannello di quota")
    ap.add_argument("--epr-pav-gain", type=float, default=C.EPR_PAV_GAIN,
                    help=f"frazione del gap colmata ogni anno dal pavimento (default "
                         f"{C.EPR_PAV_GAIN}; 1 = chiusura in un anno = lump, "
                         f"0 = mai = nessun pavimento)")
    ap.add_argument("--epr-non-mur", type=int, default=C.EPR_NON_MUR_OGGI,
                    help=f"ricercatori del settore GOV FUORI dagli enti MUR (default "
                         f"{C.EPR_NON_MUR_OGGI:,}: ISS, ISPRA, CREA, INAIL, IZS, ARPA, "
                         f"regioni, ministeri). Entrano in ruolo per concorso e il "
                         f"modello li rimpiazza e basta: 0 = tutte le assunzioni del "
                         f"ramo passano dall'imbuto MUR")
    ap.add_argument("--epr-anni-liv2", type=float, default=None,
                    help=f"anzianità di ruolo prima della promozione a Livello II (default "
                         f"= calibrato dalla quota attuale distribuita sulla coorte)")
    ap.add_argument("--epr-anni-liv1", type=float, default=None,
                    help=f"anzianità di ruolo prima della promozione a Livello I (default "
                         f"= calibrato dalla quota attuale distribuita sulla coorte)")
    ap.add_argument("--epr-quota-ii-tgt", type=float, default=C.QUOTA_EPR_II_TGT,
                    help=f"quota di riferimento II/I a REGIME (default {C.QUOTA_EPR_II_TGT})")
    ap.add_argument("--epr-quota-i-tgt", type=float, default=C.QUOTA_EPR_I_TGT,
                    help=f"quota di riferimento I sul totale a REGIME (default {C.QUOTA_EPR_I_TGT})")
    ap.add_argument("--ta-elast", type=float, default=C.TA_ELAST,
                    help=f"elasticità del TA ai ricercatori (default {C.TA_ELAST}: "
                         "ricercatori x2 -> TA x1,5). 0 = overhead fisso, "
                         "1 = proporzionale. Il dato storico italiano è 0.33, ma "
                         "misura il blocco del turnover, non il fabbisogno")
    ap.add_argument("--costo-ta", type=float, default=C.COSTO_TA,
                    help=f"costo lordo ente per testa-anno di TA (default {C.COSTO_TA:,})")
    ap.add_argument("--ta-cap", type=float, default=None,
                     help="cap FTE totali TA (uni + enti); None = nessun cap (default: None, "
                          f"in config.py vale {C.TA_CAP:,})")
    ap.add_argument("--ta-uplift", type=float, default=C.TA_UPLIFT,
                     help=f"moltiplicatore costante per gli stipendi TA (default {C.TA_UPLIFT})")
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
    ap.add_argument("--quota-incarico", type=float, default=C.QUOTA_PREC_INCARICO,
                    help=f"quota di postdoc universitari su INCARICO DI RICERCA "
                         f"({C.COSTO_PREC_INCARICO:,} lordo amministrazione, ESENTE "
                         f"IRPEF) invece che su contratto di ricerca "
                         f"({C.COSTO_PREC_CONTRATTO:,}, tassato). Default "
                         f"{C.QUOTA_PREC_INCARICO:.2f} = stima della quota che inizia il "
                         f"postdoc entro {C.ANNI_FINESTRA_IDR} anni dalla laurea "
                         "magistrale, da AlmaLaurea (vedi il blocco POSTDOC in config). "
                         "Sensitività sull'età alla magistrale: 0.445 a 26,5 anni, 0.582 "
                         "a 28,0. È la quota di PERSONE: sullo stock conta solo per "
                         f"--anni-incarico su {C.PRECARI_ANNI:.0f} anni di postdoc")
    ap.add_argument("--anni-incarico", type=float, default=C.ANNI_INCARICO,
                    help=f"anni di postdoc copribili con incarico di ricerca (default "
                         f"{C.ANNI_INCARICO}): la finestra dei {C.ANNI_FINESTRA_IDR} anni "
                         "dalla magistrale si chiude durante il postdoc, quindi chi ha "
                         "l'opzione la usa solo per una parte della permanenza. Sullo "
                         "stock la quota a incarico vale --quota-incarico x "
                         "(--anni-incarico / --precari-anni)")
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
                     help=f"anni di rampa delle leve (default {C.RAMP} -> a regime dal {C.ANNO0 + C.RAMP})")
    ap.add_argument("--ramp-phd", type=int, default=C.RAMP_PHD,
                     help=f"anni di rampa per la sola borsa PhD (default {C.RAMP_PHD})")
    ap.add_argument("--ramp-alpha-prec", type=float, default=C.RAMP_ALPHA_PREC,
                    help="anni su cui il postdoc smette di fare didattica (alpha da "
                         f"{C.ALPHA_PREC_OGGI} a {C.ALPHA_PREC_TGT}; default "
                         f"{C.RAMP_ALPHA_PREC}). 0 = segue --ramp. E' la leva che "
                         "governa da sola la gobba del rapporto studenti/docente: a "
                         "rampa breve il rapporto peggiora prima di migliorare")
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
    ap.add_argument("--scatti-blocco-da", type=int, default=C.SCATTI_BLOCCO_DA,
                    help=f"blocco scatti: primo anno del blocco (default {C.SCATTI_BLOCCO_DA})")
    ap.add_argument("--scatti-blocco-anni", type=int, default=C.SCATTI_BLOCCO_ANNI,
                    help=f"blocco scatti: anni di blocco (default {C.SCATTI_BLOCCO_ANNI}, "
                         "cioe' ACCESO; usa 0 per spegnerlo)")
    ap.add_argument("--scatti-blocco-recupero", type=float, default=C.SCATTI_BLOCCO_RECUPERO,
                    help=f"blocco scatti: quota di anni restituita (default {C.SCATTI_BLOCCO_RECUPERO})")
    ap.add_argument("--scatti-blocco2-da", type=int, default=C.SCATTI_BLOCCO2_DA,
                    help=f"SECONDA finestra di blocco scatti, quella piccola sul gradino "
                         f"di fine rampa: primo anno (default {C.SCATTI_BLOCCO2_DA}). "
                         "Non deve sovrapporsi alla prima")
    ap.add_argument("--scatti-blocco2-anni", type=int, default=C.SCATTI_BLOCCO2_ANNI,
                    help=f"seconda finestra: anni di blocco (default "
                         f"{C.SCATTI_BLOCCO2_ANNI}; usa 0 per spegnerla)")
    ap.add_argument("--scatti-blocco2-recupero", type=float,
                    default=C.SCATTI_BLOCCO2_RECUPERO,
                    help=f"seconda finestra: quota di anni restituita (default "
                         f"{C.SCATTI_BLOCCO2_RECUPERO} = meta', piu' mite della prima)")
    a = ap.parse_args()
    p = {**scenario.DEFAULTS, **vars(a)}
    try:
        # la CLI vuole tutti e tre gli scenari; i controfattuali se li calcola da se'
        # piu' sotto, dove servono, quindi controlli=False.
        res = scenario.esegui(p, quali=scenario.NOMI_SCENARI, controlli=False)
    except ValueError as e:
        ap.error(str(e))
    dfs, scen = res.dfs, res.target
    # la destinazione dei file e' l'unica cosa che resta alla CLI: importare o eseguire
    # il modello non deve scrivere sul disco.
    C.OUT = a.out
    os.makedirs(C.OUT, exist_ok=True)

    # calcolate dentro esegui() prima che scenari() azzeri QUOTA_RIC_UNI
    base_herd, quota_reg = res.cal["base_herd"], res.cal["quota_reg"]
    phd_oggi = res.cal["phd_oggi"]

    print("#" * 82)
    print("# TRANSIZIONE DINAMICA - stato stazionario da imbuto")
    print(f"# param: P2_hist={C.P2_HIST} | ruolo_oggi={C.PERM_OGGI:,} | precari_anni={C.PRECARI_ANNI} "
          f"| ramp={C.RAMP}a | ramp_phd={C.RAMP_PHD}a")
    print(f"# leve (P2, flusso PhD, paghe W) rampate dal {C.ANNO0} e a REGIME dal {C.ANNO0 + C.RAMP}; "
          f"borsa PhD rampa {C.RAMP_PHD}a; "
          f"ingresso in ruolo a {eta_ruolo_in(C.PRECARI_ANNI)} anni, durata ruolo {perm_dur(C.PRECARI_ANNI)}a")
    print(f"# IMBUTO a regime: PhD -(P1={C.P1:.2f})-> [univ -(P2={C.P2_TGT:.2f})-> ruolo | "
          f"EPR -(Madia {C.P2_EPR:.2f}, + concorso diretto {epr_in_diretto():,.0f}/a)-> "
          f"ruolo] => {C.STAB_PHD*100:.0f}% stabilizzato nel ramo univ.")
    if C.P2_TGT >= 1.0:
        print(f"# UNICO FILTRO all'uscita dal dottorato: P1 scende da {_p1_hist():.2f} (oggi) "
              f"a {C.P1:.2f}; chi passa ha la carriera garantita")
    else:
        print(f"# DUE FILTRI IN SERIE: P1 scende da {_p1_hist():.2f} (oggi) a {C.P1:.2f} "
              f"all'uscita dal dottorato, poi P2={C.P2_TGT:.2f} a fine dei "
              f"{C.PRECARI_ANNI:.0f} anni di postdoc;")
        print(f"#       la carriera è garantita solo da RTT in poi. Il postdoc resta un "
              f"passaggio SELETTIVO: {(1-C.P2_TGT)*100:.0f}% esce dall'accademia dopo "
              f"{C.D_PHD + C.PRECARI_ANNI:.0f} anni fra dottorato e precariato.")
    if _p1_hist() > 1.0:
        print(f"#   /!\\ P1 storico > 1: il precariato del 2026 è più GRANDE di quanto il "
              f"flusso di dottori possa rimpiazzare ({_uni_in0()+_epr_in0_tot():,.0f} ingressi "
              f"servono, {C.PHD_OGGI_REALE/C.D_PHD:,.0f} dottori escono).")
        print(f"#       Non è un errore di calibrazione: è la bolla PNRR: uno stock "
              f"gonfiato da un finanziamento straordinario e non sostenibile a regime. "
              f"Il motore lo gestisce")
        print(f"#       (prosegue = min(serve, escono)), quindi il precariato inizia a "
              f"sgonfiarsi già dall'anno 0 invece di restare al livello di partenza.")
    _dir, _fix = epr_in_diretto(), epr_stock_regime(0.0)[0]
    print(f"# EPR: organico ANCORATO ALLA SPESA (GOVERD_TGT {C.GOVERD_TGT}% PIL), non più "
          f"costante. DUE CANALI, di cui uno solo si espande:")
    print(f"#      [diretto, FISSO] {C.EPR_NON_MUR_OGGI:,} ricercatori del settore GOV "
          f"fuori dagli enti MUR (ISS, ISPRA, CREA, ARPA, regioni): entrano in ruolo per "
          f"concorso e il modello li RIMPIAZZA e basta, {_dir:,.0f}/anno.")
    print(f"#      [filiera MUR] {C.D_PREC_EPR}a di contratto di ricerca, Madia per il "
          f"{C.P2_EPR:.0%}: è qui che passa TUTTA l'espansione che il GOVERD finanzia, "
          f"quindi anche tutto il precariato.")
    print(f"#      Sul BACINO DEI DOTTORANDI pesa il canale postdoc per intero più il "
          f"{C.PHD_NEL_DIRETTO_EPR:.0%} del diretto ({_dir*C.PHD_NEL_DIRETTO_EPR:,.0f}/a): "
          f"il resto sono concorsi da laurea, su un mercato che il modello non simula.")
    # una riga per LIVELLO DI PAGHE, non per scenario: l'organico EPR di regime dipende
    # dallo scenario solo attraverso W (a GOVERD fisso, paghe più alte = meno teste).
    for W in sorted({v[1] for v in scen.values()}):
        etichetta = " + ".join(n for n, v in scen.items() if v[1] == W)
        x = _epr_in_tgt(W)
        ruolo, prec = epr_stock_regime(x)
        mur = ruolo - _fix + prec          # la sola filiera MUR, per il confronto col 31%
        print(f"#      [{etichetta}] paghe x{W:.2f}: contratti di ricerca "
              f"{_epr_in0():,.0f} -> {x:,.0f}/anno (rimpiazzo a organico fermo: "
              f"{epr_in_rimpiazzo():,.0f}) => a regime {ruolo:,.0f} ruolo + {prec:,.0f} "
              f"precari = {ruolo+prec:,.0f} teste "
              f"({(ruolo+prec)/C.EPR_RICERC_OGGI-1:+.0%} vs oggi)")
        print(f"#            quota precaria: {prec/(ruolo+prec):.1%} sul ramo intero "
              f"(oggi 16-21%), {prec/mur:.1%} sulla sola filiera MUR (oggi ~31%) - "
              f"il resto è diluizione del blocco a concorso, non de-precarizzazione.")
        if x <= 0:
            print(f"#            /!\\ flusso postdoc a ZERO: il solo canale diretto "
                  f"sfora già il GOVERD obiettivo. L'organico non-MUR non sta dentro "
                  f"{C.GOVERD_TGT}% PIL a queste paghe.")
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
           f" | stipendi TA ×{C.TA_UPLIFT} costante")
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
          f"(alpha {C.ALPHA['ric_uni']}, {costi_regime()['ric_uni']:,.0f} EUR a regime su scala EPR) => "
          f"a HERD {C.HERD_TGT}% e parità PPP la densità è {dq:.0f} FTE/100k "
          f"(senza: {d0:.0f} a paghe odierne)")
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

    # ---- stabilizzazione EPR: dal precariato all'espansione, un passo alla volta ----
    print(f"\n[STABILIZZAZIONE EPR] dai {C.EPR_RICERC_OGGI:,} ricercatori di oggi al regime, "
          f"separando riforma del precariato ed espansione (paghe ferme)")
    ts = _tabella_stabilizzazione()
    print(ts.to_string(index=False))
    g_fermo, g = ts["GOVERD_%PIL"].iloc[-2], ts["GOVERD_%PIL"].iloc[-1]
    print(f"  -> a organico FERMO il GOVERD si ferma a {g_fermo:.3f}% (obiettivo "
          f"{C.GOVERD_TGT}%): la Madia al {C.P2_EPR:.0%} non satura la spesa, "
          f"restano {(C.GOVERD_TGT-g_fermo)/100*C.PIL_MLN:,.0f} mln/anno da spendere.")
    print(f"  -> con l'ESPANSIONE GOVERD {C.GOVERD_OGGI}% -> {g:.3f}% "
          f"(+{(g-C.GOVERD_OGGI)/100*C.PIL_MLN:,.0f} mln/anno di spesa R&S; "
          f"+{ts['d_budget_mln'].iloc[-1]:,.0f} mln di monte stipendi) | obiettivo "
          f"{C.GOVERD_TGT}%: {'CENTRATO' if abs(g-C.GOVERD_TGT) < 5e-4 else f'scarto {g-C.GOVERD_TGT:+.3f}pp'}")

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

    # ---- blocco scatti stipendiali ----
    # DUE finestre, con due bersagli diversi: la grande sulla gobba demografica del 2057,
    # la piccola sul gradino di fine rampa. Ognuna va misurata nel SUO anno, altrimenti
    # la seconda non si vede: nel 2055 e' gia' tutta riassorbita.
    if _fin := _finestre():
        _et = [(int(da), int(a1) - 1, rec) for da, a1, rec in _fin]
        print("\n[BLOCCO SCATTI] " + " + ".join(
            f"{a-d+1} anni dal {d} al {a} (recupero {r:.0%})" for d, a, r in _et))
        # anno di misura per finestra: due anni dopo la sua chiusura, quando l'effetto
        # sul costo per testa e' pieno ma non ancora eroso dal ricambio della coorte
        _anni_mis = sorted({min(a + 2, C.ANNO0 + C.ORIZZONTE) for _, a, _ in _et})
        blk = []
        for nome, (t, W, q) in scen.items():
            df, df0 = dfs[nome], simula_senza_blocco(t, W, q)
            r = {"scenario": nome}
            for y in _anni_mis:
                h_no = df0.loc[df0["anno"] == y, "HERD_%PIL"].iloc[0]
                h_si = df.loc[df["anno"] == y, "HERD_%PIL"].iloc[0]
                b_no = df0.loc[df0["anno"] == y, "budget_univ_mld"].iloc[0]
                b_si = df.loc[df["anno"] == y, "budget_univ_mld"].iloc[0]
                r[f"costo_doc_{y}"] = round(df.loc[df["anno"] == y, "costo_docente"].iloc[0] / 1e3, 1)
                r[f"dHERD_{y}_pp"] = round(h_si - h_no, 3)
                r[f"dBudget_{y}_mld"] = round(b_si - b_no, 2)
            dev_2080 = (_teste_tot(df).iloc[-1] / _teste_tot(df0).iloc[-1] - 1) * 100
            r["scarto_2080_%"] = round(dev_2080, 2)
            blk.append(r)
        print(pd.DataFrame(blk).to_string(index=False))
        print(f"  -> costo_docente in kEUR/testa; dHERD e dBudget sono CON meno SENZA "
              f"blocco, ramo universitario. Anni di misura {_anni_mis}: uno per finestra,")
        print(f"     due anni dopo la sua chiusura. La finestra piccola non si vedrebbe "
              f"nel {_anni_mis[-1]}, dove e' gia' tutta riassorbita.")
        ok = all(abs(x["scarto_2080_%"]) < 0.1 for x in blk)
        if ok:
            print("  -> la leva è TRANSITORIA: stato stazionario identico (scarto_2080 ~ 0).")
        else:
            print("  -> /!\\ la leva altera ancora lo stato stazionario nel 2080: "
                  "riduci la finestra.")

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
    _q = dfs["ADI_Manifesto_ric"]
    print(f"  -> a regime l'IRPEF vale {_q['irpef_quota_stip'].iloc[-1]:.0%} del monte "
          f"stipendi e {_q['irpef_mln'].iloc[-1]/(_q['budget_univ_mld'].iloc[-1]+_q['budget_epr_mld'].iloc[-1])/1000:.0%} "
          f"della spesa totale; con addizionali, contributi e IRAP si arriva al "
          f"{_q['retro_quota_stip'].iloc[-1]:.0%} degli stipendi.")
    print(f"  -> l'aliquota media sale dal {dfs['ADI_Manifesto_ric']['aliq_irpef_media'].iloc[0]:.1%} "
          f"al {_q['aliq_irpef_media'].iloc[-1]:.1%}: il piano non aggiunge solo teste, "
          f"le sposta verso il ruolo e alza le paghe, e l'IRPEF e' progressiva.\n"
          f"     Il ritorno fiscale cresce quindi PIU' CHE PROPORZIONALMENTE alla spesa.")
    # SENSITIVITA' sulla quota a INCARICO DI RICERCA. Non e' piu' una sensitivita' solo
    # fiscale: la quota muove ANCHE il costo medio del postdoc, quindi la spesa, la
    # calibrazione e la densita' raggiungibile. Il parametro incerto e' l'eta' alla
    # laurea magistrale, che decide chi sta dentro la finestra. A finestra corta (4 anni)
    # la soglia cade dentro la classe di eta' piu' densa, quindi la sensitivita' e' PIU'
    # ampia di quanto fosse a 6 anni: 44,5%-58,2% contro 61,3%-70,7%.
    _v0_pd = scomponi(Voce("postdoc", 1.0, C.COSTO_PREC_CONTRATTO))["irpef"]
    _sens, _base_q = [], C.QUOTA_PREC_INCARICO
    for _q_in, _et in ((0.445, "laurea magistrale a 26,5 anni"),
                       (_base_q, "laurea magistrale a 27,2 anni [IN USO]"),
                       (0.582, "laurea magistrale a 28,0 anni")):
        C.QUOTA_PREC_INCARICO = _q_in
        _q_st = C.quota_incarico_stock()
        C.QUOTA_ESENTE_PREC_UNI = C.QUOTA_ESENTE_PREC_UNI_TGT = _q_st
        _salva_c, C.COSTO["precari"] = C.COSTO["precari"], C.costo_precari()
        _d = simula(*scen["ADI_Manifesto_ric"])
        C.COSTO["precari"] = _salva_c
        _sens.append({"quota_persone": round(_q_in, 3),
                      "quota_stock": round(_q_st, 3),
                      f"teste_incarico_{C.ANNO0}": round(_q_st * C.PRECARI_OGGI),
                      "costo_medio_postdoc": round(C.costo_precari()),
                      f"IRPEF_{C.ANNO0}_mld": round(_d["irpef_mln"].iloc[0] / 1000, 2),
                      "IRPEF_2080_mld": round(_d["irpef_mln"].iloc[-1] / 1000, 2),
                      "cum_IRPEF_mld": round(_d["irpef_mln"].sum() / 1000, 1),
                      "ipotesi": _et})
    C.QUOTA_PREC_INCARICO = _base_q
    C.QUOTA_ESENTE_PREC_UNI = C.QUOTA_ESENTE_PREC_UNI_TGT = C.quota_incarico_stock()
    print(f"\n  SENSITIVITA' sulla quota a INCARICO DI RICERCA ({C.COSTO_PREC_INCARICO:,} "
          f"lordo amm., esente IRPEF art. 6 c.6 L.398/1989). 'quota_persone' = chi ha "
          f"l'opzione (entro {C.ANNI_FINESTRA_IDR} anni dalla magistrale);\n  'quota_stock' "
          f"= gli anni-persona che ci stanno davvero, perche' l'incarico copre "
          f"{C.ANNI_INCARICO:g} dei {C.PRECARI_ANNI:.0f} anni di postdoc. "
          f"Scenario ADI_Manifesto_ric:")
    print(pd.DataFrame(_sens).to_string(index=False))
    print(f"  -> la stima incrocia la distribuzione dell'eta' al DOTTORATO (AlmaLaurea "
          f"2022: media 32,6a, mediana ~31,0a) con l'eta' alla LAUREA MAGISTRALE "
          f"(27,2a): chi si dottora prima dei {27.2+C.ANNI_FINESTRA_IDR:.1f} anni\n     "
          f"e' dentro la finestra. La soglia cade appena sopra la MEDIANA, quindi la "
          f"platea e' poco piu' della meta' - a 6 anni era il 65,7%.")
    print(f"  -> la FINESTRA A {C.ANNI_FINESTRA_IDR} ANNI e' una scelta di proposta, non "
          f"un dato: l'incarico esente resta un ponte d'INGRESSO e non diventa un canale "
          f"di sottoinquadramento.\n     Sullo stock ne resta il "
          f"{C.quota_incarico_stock():.1%} degli anni-persona, cioe' una figura "
          f"RESIDUALE: il postdoc del modello e' ormai il contratto di ricerca pieno.")
    print(f"  -> /!\\ la quota muove DUE cose insieme: la platea esente IRPEF e il COSTO "
          f"MEDIO del postdoc ({C.COSTO['precari']:,.0f} EUR contro i "
          f"{C.COSTO_PREC_CONTRATTO:,} di un contratto di ricerca pieno).\n"
          f"     E' quindi una leva di SPESA prima ancora che di fisco: un postdoc "
          f"tassato paga {_v0_pd:,.0f} EUR di IRPEF, ma ne costa "
          f"{C.COSTO_PREC_CONTRATTO-C.COSTO_PREC_INCARICO:,} in piu'.")
    print(f"  -> /!\\ SEMPLIFICAZIONE: la chiusura della finestra e' contabilizzata in "
          f"MEDIA, non per coorte. Il modello tiene {C.quota_incarico_stock():.1%} dei "
          f"postdoc su incarico per tutto il\n     periodo, invece dei "
          f"{C.QUOTA_PREC_INCARICO:.0%} che ci stanno per {C.ANNI_INCARICO:g} anni e poi "
          f"passano a contratto: stessi anni-persona, stesse masse, profilo individuale "
          f"diverso.")
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
             "ADI_Manifesto_ric": f"ADI Manifesto + ric.univ. (target {scen['ADI_Manifesto_ric'][0]:.0f})"}
    grafico_target(dfs, {n: v[0] for n, v in scen.items()}, etich,
                   f"{C.OUT}/transizione_fte.png")
    for nome, df in dfs.items():
        df.to_csv(f"{C.OUT}/transizione_{nome}.csv", index=False)

    # ---- report 2026-2050 ----
    # le righe del prepensionamento compaiono solo se la leva è accesa: a leva spenta
    # sarebbero tre righe di zeri in una tabella già fitta
    righe = righe_con_prepens() if _prepens_on() else RIGHE_TAB
    anni = [2026, 2030, 2035, 2040, 2050, 2060, 2070, 2080]
    for nome in ("FLC", "ADI_Manifesto_ric"):
        print(f"\n{'='*100}\nTABELLA {nome} - traiettoria {anni[0]}-{anni[-1]} "
              f"(target {scen[nome][0]:.0f} FTE/100k, paghe x{scen[nome][1]:.2f})\n{'='*100}")
        print(tabella_scenario(dfs[nome], anni, righe).to_string())
    # i grafici si fermano a FINE_GRAFICI, le tabelle e i CSV no: gli ultimi anni sono
    # una linea piatta che ruba spazio alla transizione (vedi il commento in config)
    fg = C.FINE_GRAFICI
    grafico_trend(dfs, fg, f"{C.OUT}/trend_{C.ANNO0}_{fg}.png")
    grafico_ffo(dfs, fg, f"{C.OUT}/ffo_aggiuntivo.png")
    grafico_stack(dfs, fg, f"{C.OUT}/organico_stack.png", etich)
    grafico_spesa_stack(dfs, fg, f"{C.OUT}/spesa_stack.png", etich)
    print(f"\n[grafici] fino al {fg} (la simulazione arriva al {C.ANNO0+C.ORIZZONTE}: "
          f"tabelle e CSV restano a orizzonte pieno)")
    print(f"          {C.OUT}/trend_{C.ANNO0}_{fg}.png "
          f"({16 if C.ATTREZZ_INVILUPPO else 15} pannelli: ricerca, TA, didattica"
          f"{', attrezzature' if C.ATTREZZ_INVILUPPO else ''}) "
          f"+ {C.OUT}/ffo_aggiuntivo.png (mld/anno) "
          f"+ {C.OUT}/organico_stack.png (organico univ.+EPR) "
          f"+ {C.OUT}/spesa_stack.png (spesa per "
          f"{'voce' if C.ATTREZZ_INVILUPPO else 'ramo'}, con la fascia IRPEF che rientra)")
    # l'inviluppo è una DECISIONE, non un risultato del modello: se resta solo dentro
    # ai PNG chi legge il riepilogo non sa da dove viene la differenza
    if C.ATTREZZ_INVILUPPO:
        print(f"  [ATTREZZATURE] la spesa liberata dalle due discese dell'organico resta alla "
              f"ricerca: piatta dal {C.ATTREZZ_PICCO_2}, in salita costante fra "
              f"{C.ATTREZZ_PICCO_1} e {C.ATTREZZ_PICCO_2}.")
        print(f"          il supplemento è spesa R&S: entra in HERD e GOVERD, ripartito fra "
              f"i due rami a mix invariato. Le curve di obiettivo nei pannelli")
        print(f"          di trend vanno quindi lette come SOGLIE, non come traguardi: "
              f"l'inviluppo le supera per costruzione.  (--no-attrezzature per spegnerlo)")
        for nome, df in dfs.items():
            q = df.set_index("anno")["quota_attrezz"]
            print(f"  {nome:<12} quota attrezzature {q.loc[C.ANNO0]:.1%} ({C.ANNO0}) -> "
                  f"max {q[q.index <= C.ATTREZZ_QUOTA_FINE].max():.1%} -> "
                  f"{q.loc[C.ATTREZZ_QUOTA_FINE]:.1%} ({C.ATTREZZ_QUOTA_FINE}) | "
                  f"supplemento max {df['attrezz_extra_mld'].max():.1f} mld/anno")
    else:
        print("  [ATTREZZATURE] inviluppo SPENTO: la spesa totale segue l'organico anche "
              "dove cala, e le attrezzature restano")
        print("          il solo residuo di calibrazione (LAMBDA_HE per l'università, "
              "OVH_EPR_ATTR per gli enti).")
    singoli = grafici_singolo("ADI_Manifesto_ric", dfs, fg, C.OUT, etich)
    print(f"[grafici] solo scenario ADI_Manifesto_ric, su file separati:\n           "
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
              f"+{f['dStato_univ_mld']+f['dStato_epr_mld']:.1f} mld/anno"
              + (f" (di cui {f['attrezz_extra_mld']:.1f} di attrezzature da inviluppo)"
                 if C.ATTREZZ_INVILUPPO else ""))
    _fd0 = _fte_didattico(_init_stato(0.0))
    print(f"\n  [CARICO DIDATTICO] studenti per docente in FTE didattici (peso = 1-alpha: "
          f"prof {1-C.ALPHA['docente']:.2f}, ric.univ/RTT {1-C.ALPHA['RTT']:.2f}; "
          f"dottorandi esclusi)")
    print(f"      il POSTDOC e' l'unico peso che si MUOVE: {1-C.alpha_precari(0):.2f} nel "
          f"{C.ANNO0} come oggi, {1-C.alpha_precari(C.RAMP):.2f} dal {C.ANNO0+C.RAMP} "
          f"(sola ricerca), rampato su {C.RAMP} anni come le altre leve.")
    print(f"  denominatore {C.ANNO0} = {_fd0:,.0f} FTE-docente -> studenti impliciti "
          f"{C.STUDENTI_OGGI:,.0f}")
    for nome, df in dfs.items():
        # NON basta il primo anno sotto il traguardo: con la didattica del postdoc che
        # si spegne lungo la rampa il rapporto puo' scendere sotto 14,3 durante la gobba
        # demografica e poi RISALIRE sopra. Dire "raggiunta nel 2057" e fermarsi li'
        # sarebbe falso, quindi si dichiara anche se ci si resta.
        sotto = df[df["stud_per_doc"] <= C.STUD_DOC_TGT]
        anno = int(sotto["anno"].iloc[0]) if len(sotto) else -1
        resta = len(sotto) and df["stud_per_doc"].iloc[-1] <= C.STUD_DOC_TGT
        f30 = df[df["anno"] == C.ANNO0 + 30].iloc[0]
        fin = df.iloc[-1]
        esito = ("MAI" if anno < 0 else
                 f"{anno}" if resta else
                 f"{anno} ma RIPERSA (fine a {fin['stud_per_doc']:.2f})")
        print(f"  {nome:<12} {C.ANNO0}: {df['stud_per_doc'].iloc[0]:.2f} | "
              f"{C.ANNO0+30}: {f30['stud_per_doc']:.2f} | {C.ANNO0+C.ORIZZONTE}: "
              f"{fin['stud_per_doc']:.2f} (a studenti fermi) / {fin['stud_per_doc_pop']:.2f} "
              f"(studenti ~ pop.) | media UE {C.STUD_DOC_TGT}: " + esito)
    _pk = max(dfs["ADI_Manifesto_ric"]["stud_per_doc"])
    print(f"  /!\\ ATTENZIONE: il rapporto PEGGIORA prima di migliorare - tocca "
          f"{_pk:.2f} a fine rampa, sopra il {C.STUD_DOC_OGGI} di partenza. Togliere la "
          f"didattica al postdoc")
    print(f"      toglie ~{C.PRECARI_OGGI*(1-C.alpha_precari(0)):,.0f} FTE-docente dal "
          f"denominatore in {C.RAMP} anni, e il ruolo non cresce cosi' in fretta: la "
          f"didattica del postdoc va RIMPIAZZATA, non solo tolta.")
    print(f"  /!\\ DUE effetti sovrapposti, e vanno letti insieme. (1) La transizione "
          f"sposta persone dal precariato al ruolo (peso {1-C.ALPHA['RTT']:.2f} -> "
          f"{1-C.ALPHA['docente']:.2f}, cioè "
          f"{(1-C.ALPHA['docente'])/(1-C.ALPHA['RTT']):.0f}x).")
    print(f"      (2) Il postdoc esce dalla didattica lungo la rampa (peso "
          f"{1-C.alpha_precari(0):.2f} -> {1-C.alpha_precari(C.RAMP):.2f}), il che TOGLIE "
          f"denominatore nei primi {C.RAMP} anni: il rapporto migliora più lentamente "
          f"all'inizio")
    print(f"      di quanto farebbero le sole assunzioni. È l'effetto che conta, ed è "
          f"invisibile se si contano le teste.")
    print(f"      NB: il {C.STUD_DOC_OGGI} di partenza e il traguardo {C.STUD_DOC_TGT} devono "
          f"venire dallo stesso indicatore, altrimenti il confronto non è omogeneo.")
    print()
    print(f"  Il terzo scenario tiene INSIEME densità {scen['ADI_Manifesto_ric'][0]:.0f}, HERD "
          f"{C.HERD_TGT}% e parità PPP: i ricercatori universitari rendono 2x FTE per euro")
    print("  dei docenti, quindi servono MENO teste, non più.")
    if C.PRECARI_ANNI > 3:
        print(f"  Con precari_anni={C.PRECARI_ANNI}: flusso d'ingresso realistico (~{_pd_in0():,.0f}), "
              f"ma il regime NON è più cattedre (quota-docente {quota_reg*100:.0f}%): il")
        print(f"  precariato prolungato è esso stesso uno stock strutturale permanente.")
    print(f"\nFile: transizione_fte.png + transizione_*.csv (in {C.OUT})")


if __name__ == "__main__":
    main()
