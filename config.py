"""Costanti, ancore ai dati e parametri di scenario del modello FTE.

Tutto cio' che e' un NUMERO DI INPUT sta qui, con la fonte accanto. I valori che
main() ricalcola a runtime (calibrazioni e argomenti da CLI) partono da un valore
di ripiego e sono segnalati nei commenti: sono gli unici mutabili.

CONVENZIONE: i valori di configurazione si leggono SEMPRE come C.NOME, mai importati
per nome. main() li riassegna a runtime (calibrazioni, argomenti da CLI) e solo
l'accesso per attributo vede il rebinding; un `from config import X` catturerebbe una
copia congelata all'import. Le funzioni invece non vengono mai riassegnate e si
importano per nome.
"""
from __future__ import annotations

import os

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
LAMBDA_HE = 0.70   # quota-lavoro dell'HERD. NON piu' un'assunzione: da quando il TA e'
                   # esplicito (vedi blocco PERSONALE TA) il costo del personale di
                   # ricerca e' tutto misurato, quindi la ripartizione lavoro/attrezzature
                   # dell'HERD osservato diventa un RESIDUO. Ricalcolata in main da
                   # _calibra_lambda_he(); questo 0,70 resta solo come valore di ripiego e
                   # come default di --lambda-he per riprodurre il comportamento vecchio.
                   # Il vecchio 0,70 con i TA veri non sta in piedi: lascerebbe 237 mln
                   # per 31.357 FTE di tecnici, cioe' 7.568 EUR a testa-anno.

# "ric_uni" = ruolo universitario con profilo da ricercatore EPR: meno didattica
# (alpha 0,75 invece di 0,50) e stipendio da III->II livello invece che da PO/PA.
# Rende ESATTAMENTE il doppio di FTE per euro rispetto a un docente.
ALPHA = {"dottorando": 0.75, "docente": 0.50, "ric_uni": 0.75,
         "RTT": 0.75, "precari": 0.75}
# La figura 'docente' e' una MEDIA di due ruoli con stipendi molto diversi. Il modello
# la usa mediata ovunque tranne che nel calcolo IRPEF, dove non si puo': l'imposta e'
# progressiva, quindi la media delle imposte non e' l'imposta della media (applicare
# lo scaglione al costo medio sottostima il gettito). Le tre costanti stanno qui
# perche' il retroflusso fiscale ha bisogno dei due ruoli separati.
# Quota PO = 16.574 / (16.574 + 26.472) = 0,385 sui dati MUR 2023, arrotondata a 0,39
# come era gia' nella vecchia espressione.
QUOTA_PO = 0.39
COSTO_PO, COSTO_PA = 130_000, 78_000                   # costo lordo ente, per testa-anno
COSTO = {"docente": QUOTA_PO * COSTO_PO + (1 - QUOTA_PO) * COSTO_PA,   # ~98.280
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
# d'acquisto con la MEDIA EUROPEA del reddito dei dottori di ricerca.
#
# DUE PANIERI, uno in uso e uno no:
#   UPLIFT_PPP_EU   = 91.343 / 78.758 = 1,160  <- DEFAULT del modello
#       la media europea ReICO contro il valore italiano. È il traguardo "stare nella
#       media", non "stare coi migliori": raggiungibile, e con un costo che il ramo
#       paghe riesce a portare senza divorare la densità.
#   UPLIFT_PPP_TOP5 = 1,649                    <- scenario MOLTO OTTIMISTA, non in uso
#       la media dei 5 paesi che pagano meglio nel paniere ReICO. Resta nel sorgente
#       come estremo superiore e si seleziona con --uplift-ppp; vedi l'avvertenza (a)
#       sul perchè quel paniere non è europeo.
#
# CONFERMA INCROCIATA, un paniere per parte. Sulla tabella CARSA 2006 (vedi sotto) la
# media UE25 dava 40.126 PPS contro 34.120 italiani, cioè 1,176: a vent'anni di
# distanza e su una popolazione diversa, lo stesso 1,16-1,18 del default ReICO. E i 5
# paesi UE migliori davano 1,658, contro l'1,649 del top-5 ReICO. Le due fonti
# concordano su ENTRAMBI i panieri, il che è il motivo per cui il gap-paghe è la parte
# più solida del modello - qualunque traguardo si scelga.
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
# DUE AVVERTENZE, da riportare ovunque il numero compaia:
#
# (a) [riguarda il solo UPLIFT_PPP_TOP5, non il default] Il paniere ReICO NON è
#     ristretto all'UE. I due valori di testa (153.819 e 148.806) staccano il terzo
#     del 24,9% e sono verosimilmente extra-UE (Stati Uniti, Svizzera). Quel numero
#     va quindi letto come "i 5 paesi che pagano meglio", non "i 5 paesi UE": sui
#     soli tre paesi dietro gli outlier sarebbe 1,467, sul solo primo 1,953.
#     È una delle ragioni per cui il default è passato alla media europea, che non
#     dipende da quali paesi stiano in testa.
#
# (b) [riguarda ENTRAMBI i panieri] La popolazione ReICO sono i DOCTORATE HOLDERS
#     di tutti i settori, non i ricercatori accademici. Il modello applica W a
#     docenti, RTT, postdoc e borse: è un trasferimento fra popolazioni diverse.
#     CARSA misurava i ricercatori, ed è la ragione per cui la coincidenza dei
#     numeri è rassicurante ma non dimostrativa.
#
# La vecchia avvertenza (c) - "la parità è coi migliori, non con l'Europa" - non
# serve più: con il default sulla media europea la parità è, appunto, con l'Europa.
# Torna a valere se si seleziona --uplift-ppp con il valore top-5.
#
# Il prossimo affinamento utile è un uplift PER FIGURA invece di uno scalare
# unico: oggi W moltiplica allo stesso modo la borsa del dottorando e lo stipendio
# dell'ordinario, e non c'è motivo perchè il gap sia lo stesso.
REDDITO_PHD_IT = 78_758        # Italia, reddito dei dottori di ricerca a PPP [ReICO]
REDDITO_PHD_EU = 91_343        # media europea, stessa fonte e stessa unità
                               # (DA VERIFICARE sulla dashboard: è il numero su cui
                               # poggia l'intero ramo paghe del modello)
UPLIFT_PPP_EU = REDDITO_PHD_EU / REDDITO_PHD_IT        # 1,1598 <- in uso
UPLIFT_PPP_TOP5 = (sum([153_819,    # i 5 paesi con reddito più alto dei dottori di
                        148_806,    # ricerca nel dataset ReICO, a parità di potere
                        119_119,    # d'acquisto. Vedi avvertenza (a): i primi due
                        113_706,    # staccano molto e sono verosimilmente extra-UE.
                        113_695])
                   / 5) / REDDITO_PHD_IT               # 1,6485 <- scenario ottimista
UPLIFT_PPP = UPLIFT_PPP_EU     # DEFAULT: la media, non i migliori
UPLIFT_PPP_CARSA06 = (sum([60_530, 56_721, 56_268, 55_998, 53_358]) / 5) / 34_120
UPLIFT_PPP_CARSA06_UE25 = 40_126 / 34_120      # media UE25 2006 -> 1,176: la conferma
                                               # incrociata del default (1,160)
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

# --- STATO INIZIALE: STOCK OSSERVATI, densita' come RISULTATO ------------------
# Il modello partiva da un target di densita' (DENS_OGGI=99) e ricavava i precari come
# residuo. Ora fa il contrario: gli stock sono presi dai dati e la densita' e' cio' che
# ne esce. E' l'unico modo per poter VERIFICARE la calibrazione invece di imporla.
#
# Docenti: MUR open data 2023, "Personale docente di ruolo e ricercatore per area
# scientifico disciplinare" (dati-ustat.mur.gov.it, dataset personale-universitario).
#   Prof. I fascia   16.574
#   Prof. II fascia  26.472  -> PERM_OGGI = 43.046
#   Ric. a tempo indeterminato 4.831 -> vanno in perm_ric, NON in perm: sono ruolo a
#   esaurimento con profilo da ricercatore, cioe' esattamente la figura 'ric_uni'
#   (alpha 0,75). Il commento "oggi la figura non esiste" era sbagliato: esiste, si
#   sta svuotando per pensionamento (8.921 nel 2020 -> 4.271 nel 2024).
PERM_OGGI = 43_046                     # PO + PA, MUR 2023
RIC_UNI_RUOLO_OGGI = 4_831             # ricercatori a tempo indeterminato, MUR 2023

# Precari: onda lunga del PNRR. Comprende RTD-A (9.222 nel 2023), assegni (15.891) e le
# figure che il MUR non separa (co.co.co, borsisti, contratti di ricerca L.79/2022).
# NB: e' uno stock GONFIATO da un finanziamento straordinario e in esaurimento, non uno
# stato stazionario. Per la stessa ragione il P1 storico che ne esce e' distorto verso
# l'alto: il PNRR ha prodotto anche molti dottorandi.
#
# E' la VARIABILE DI CHIUSURA della calibrazione: ricavato in main da
# _precari_per_chiudere() perche' l'FTE del modello riproduca RIC_UNI_EUROSTAT. Tutto
# lo scarto di perimetro viene quindi attribuito al precariato - una SCELTA, non una
# misura: il MUR ne conta 25.113 fra RTD-A e assegni, e la stima "35.000 circa"
# comprendeva gia' le figure non separate. Il valore di chiusura sta sopra entrambi.
# Usa --precari-oggi 35000 per imporre la stima e lasciare il gap in vista.
PRECARI_OGGI = 35_000                  # ripiego; sovrascritto in main

# --- CARICO DIDATTICO --------------------------------------------------------
# Gli studenti sono ESOGENI: il modello non li simula, li porta dietro come popolazione
# di riferimento per un solo indicatore, il rapporto studenti/docenti.
#
# DENOMINATORE: docenti in FULL-TIME EQUIVALENT didattico, non teste. Il peso di
# ciascuna figura è il COMPLEMENTO della sua quota-ricerca - chi fa ricerca al 50%
# insegna al 50%, chi la fa al 75% insegna al 25% - quindi si ricava da ALPHA invece
# di essere riscritto a mano. Coi valori correnti dà: professori 0,50; ricercatori
# universitari di ruolo, RTT e postdoc 0,25. Se ALPHA cambia, il carico didattico segue.
# I DOTTORANDI restano FUORI: fanno tutorato, non sono docenti nell'indicatore.
DOCENTI_DID = ("docente", "ric_uni", "RTT", "precari")
STUD_DOC_OGGI = 19.45                  # rapporto di partenza, 2026 (FTE docenti)
STUD_DOC_TGT = 14.3                    # media europea, termine di paragone
# Lo stock di studenti resta COSTANTE per default: isola l'effetto-organico da quello
# demografico, come fa 'densita_pop2026' per la densità. La colonna alternativa lo
# scala con la popolazione SSP2 - proxy grezza, perchè la coorte 19-25 anni cala molto
# più in fretta della popolazione totale, quindi ENTRAMBE le colonne sono prudenti.
STUDENTI_OGGI = 0.0                    # ricavato in main da STUD_DOC_OGGI * PERM_OGGI

# Riferimento Eurostat per il CONFRONTO, non piu' per la calibrazione: rd_p_persocc
# 2023, settore HES, "Researchers", FTE, Italia. Il modello ci arriva? Vedi la
# diagnostica in main: NO, ci arriva sotto (vedi la nota sullo scarto).
RIC_UNI_EUROSTAT = 64_202.0
# Ricavati in main da _fte_uni_oggi(): qui solo valori di ripiego per l'import.
DENS_OGGI = 0.0
FTE_OGGI = 1.0

# ============================ RAMO EPR ======================================
# Negli EPR tutti fanno ricerca (alpha unico) e ci si struttura via Madia dopo
# 3 anni di contratto di ricerca: nessun imbuto interno, P2_EPR = 1.
ALPHA_EPR = 0.75
D_PREC_EPR = 3                         # contratto di ricerca prima della Madia
P2_EPR = 1.0                           # chi completa i 3 anni entra in ruolo
ETA_RUOLO_EPR = ETA_FINE_PHD + D_PREC_EPR      # 37
PERM_DUR_EPR = ETA_PENS - ETA_RUOLO_EPR        # 31

# Stessa ancora del ramo universitario, sull'altro settore contabile: Eurostat
# rd_p_persocc 2023, settore GOV (government), "Researchers", FTE, Italia = 27.672.
# A ALPHA_EPR=0,75 servono 36.896 teste, non 25.000. ATTENZIONE al cambio di
# PERIMETRO che questo comporta: il settore GOV di Frascati non sono i soli enti
# vigilati dal MUR, ma tutta la PA che fa ricerca (regioni, ministeri, agenzie,
# ISS, ISPRA, CREA, INAIL...). Il ramo "EPR" del modello copre ora quel perimetro.
RIC_EPR_OGGI = 27_672.0                # FTE ricercatori del settore GOV
EPR_PRECARI_OGGI = 6_000               # di cui precari (~50% assegnisti): OSSERVATO,
                                       # quindi non riscalato con il resto
EPR_RICERC_OGGI = round(RIC_EPR_OGGI / ALPHA_EPR)      # ~36.896 teste
EPR_RUOLO_OGGI = EPR_RICERC_OGGI - EPR_PRECARI_OGGI

# Costi lordo ente. Il precario oggi è un mix 50/50 assegno (esente IRPEF,
# ~22.700) e contratto di ricerca (~37.600); la L.79/2022 abolisce gli assegni,
# quindi il costo converge al contratto di ricerca ANCHE senza stabilizzare.
COSTO_EPR_PREC_OGGI = 30_000
COSTO_EPR_PREC_TGT = 37_600
COSTO_EPR_ASSEGNO = 22_700     # il capo esente del mix qui sopra. Serve SOLO al calcolo
                               # IRPEF, che deve sapere quante teste stanno sotto un
                               # regime esente e a quale reddito, non solo la spesa
                               # media: da questo e da COSTO_EPR_PREC_TGT si ricava la
                               # quota di assegnisti che riproduce ESATTAMENTE il costo
                               # medio dell'anno (vedi _voci_epr in motore).
COSTO_EPR_RUOLO = 73_500               # carriera III (15a) -> II (16a), CCNL 2022-24 tab. C4
COSTO_EPR_INGRESSO = 48_200            # III livello 0-2 anni: costo di chi si stabilizza OGGI

GOVERD_OGGI, GOVERD_TGT = 0.21, 0.22   # % PIL

# ====================== PERSONALE TECNICO-AMMINISTRATIVO ====================
# Il TA e' misurato DIRETTAMENTE in FTE-R&S, non in teste per un alpha: la fonte lo
# rileva gia' cosi'. Eurostat rd_p_persocc 2023, professional position "Total
# excluding researchers", unita' FTE, Italia:
#     universita' (HES)  31.357 FTE   = 32,8% del personale R&S universitario
#     settore GOV        17.537 FTE   = 38,8% del personale R&S degli enti
# Sotto l'ipotesi che i dottorandi non siano contati fra i ricercatori (vedi
# RIC_UNI_OGGI), tutto il non-ricercatore e' personale tecnico-amministrativo.
#
# COSA SOSTITUISCE. Prima il supporto esisteva in due forme incoerenti fra loro:
# nel ramo universitario come SUPPORTO, moltiplicatore sul costo-ricerca (elasticita'
# 1, ma calibrato come RESIDUO su HERD e quindi pari a un implausibile +12%, cioe'
# ~11.300 teste contro 55.738 reali); nel ramo EPR come OVH_EPR_SUPP, valore
# assoluto (elasticita' 0). I dati dicono che il settore GOV e' il PIU' intensivo di
# TA dei due (0,634 contro 0,488 FTE per FTE-ricercatore): l'asimmetria era rovesciata.
# Ora entrambi i rami hanno lo stesso trattamento esplicito e SUPPORTO/OVH_EPR_SUPP
# restano solo come residui di cio' che il modello ancora non nomina.
# ANCORATO AL RAPPORTO, NON AL LIVELLO. I 31.357 FTE valgono sul perimetro HES di
# Frascati, che è più largo del personale MUR che il modello ricostruisce (-11,8%,
# vedi la diagnostica di main). Prendendo il livello assoluto il rapporto TA/ricercatori
# del modello salirebbe a 0,554 contro lo 0,488 misurato: si importerebbe lo scarto di
# perimetro dentro un parametro di comportamento. Il RAPPORTO invece sopravvive al
# cambio di perimetro, purchè i ricercatori "in più" di Eurostat portino con sè il
# proprio supporto - che è esattamente l'ipotesi (a) fra quelle in lista.
TA_UNI_RATIO = 31_357.0 / 64_202.0     # 0,488 FTE di TA per FTE-ricercatore, HES
TA_EPR_RATIO = 17_537.0 / 27_672.0     # 0,634, settore GOV: più intensivo dell'università
TA_UNI_OGGI = 0.0                      # ricavati in main da FTE_OGGI e dall'organico EPR
TA_EPR_OGGI = 0.0

# REGOLA DI CRESCITA. Il TA cresce del TA_ELAST dell'aumento RELATIVO dei ricercatori:
#     TA(t) = TA(0) * (1 - TA_ELAST + TA_ELAST * R(t)/R(0))
# A TA_ELAST=0,40: ricercatori x2 -> TA x1,4. Nidifica i due comportamenti vecchi:
# 0 = overhead fisso (l'ipotesi EPR), 1 = proporzionale puro (l'ipotesi universitaria).
# Quello che il TA non consuma NON va perduto: densita_iso_herd() risolve per la densità
# che esaurisce l'HERD, quindi il risparmio si travasa da solo in professori/ricercatori.
# È però un travaso PICCOLO: fra 0,50 e 0,40, alla densità di regime, il TA scende del
# 5% e la densità raggiungibile sale di circa 1 FTE/100k su ~184. La leva è forte sulla
# QUOTA di TA (asintoto dal 21,0% al 17,6%), debole sul numero di ricercatori.
#
# Perche' meno di 1: la MEDIA non e' il MARGINE. Rettorato, bilancio, segreterie
# studenti e biblioteche non scalano col numero di ricercatori; tecnici di laboratorio,
# uffici grant, stabulari e HPC si'. Il dato empirico italiano e' anche piu' basso di
# 0,50: fra il 2018 e il 2023 i ricercatori universitari sono cresciuti del 23,5% in
# FTE e il personale di supporto del 7,2%, cioe' un'elasticita' di 0,33.
# NON usare quello 0,33 come parametro normativo: misura il blocco del turnover sul
# personale non docente (MUR: TA -3,9% in dieci anni contro docenti +13,6%), non il
# fabbisogno di supporto della ricerca. Proiettarlo significherebbe proiettare
# l'austerita'. 0,40 e' una scelta di policy, non una stima.
#
# LIMITE STRUTTURALE della regola: la quota di TA sul personale R&S non scende mai
# sotto TA_ELAST*TA0 / (R0 + TA_ELAST*TA0), qualunque sia l'espansione. Con i valori
# italiani e TA_ELAST=0,40 l'asintoto e' 17,6% (era 21,0% a 0,50): nessuna crescita dei
# ricercatori, per quanto grande, avvicina l'Italia ai rapporti di Svezia (9,5%) o
# Portogallo (9,2%). La media europea della quota TA e' 24,4% (media semplice dei 27;
# 28,8% aggregata, 23,1% mediana), quindi il traguardo realistico e' quello, non i minimi.
TA_ELAST = 0.40

# Costo lordo ente per TESTA-anno. Il costo-ricerca e' FTE*COSTO_TA (l'FTE incorpora
# gia' la quota-ricerca), il monte stipendi pieno e' (FTE/ALPHA_TA)*COSTO_TA.
# ALPHA_TA e' MISURATO, non ipotizzato: 31.357 FTE Eurostat / 55.738 teste TA del MUR
# (Focus personale 2023, Tav.1: 52.826 a tempo indeterminato + 2.912 determinato).
# Il valore di COSTO_TA non sposta la calibrazione 2026 - LAMBDA_HE lo assorbe - ma
# decide quanta parte del supporto e' esplicita (e quindi segue TA_ELAST) invece che
# residua (e quindi proporzionale): va scelto, non lasciato al caso.
ALPHA_TA = 31_357.0 / 55_738.0         # ~0,563 FTE-R&S per testa TA. Dai due dati
                                       # MISURATI (FTE Eurostat / teste MUR), non da
                                       # TA_UNI_OGGI, che ora è ricavato in main.
COSTO_TA = 40_000                      # CCNL Istruzione e Ricerca, mix cat. B/C/D/EP
                                       # (DA VERIFICARE sulle tabelle retributive)
TA_SEGUE_W = True                      # gli stipendi TA seguono la leva paghe W?
                                       # True = comportamento del vecchio SUPPORTO.
                                       # Da riconsiderare: il gap ReICO e' misurato sui
                                       # dottori di ricerca e non giustifica un uplift
                                       # x1,65 sugli amministrativi. --no-ta-segue-w.

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
PHD_OGGI_REALE = 47_000        # dottorandi iscritti, 2024. Erano poco piu' di 31.000 nel
                               # 2020: +48,5% in quattro anni, quasi tutto PNRR (18.770
                               # borse per il solo XXXIX ciclo, DM 2023; oltre 30.000 fra
                               # XXXIX e XL). Anche questo stock e' quindi un PICCO
                               # transitorio, non un regime: la stessa onda che gonfia
                               # PRECARI_OGGI a monte gonfia i dottorandi a valle.
ANNO0, ORIZZONTE = 2026, 54   # orizzonte fino al 2080
# Fine dei GRAFICI, che è cosa diversa dall'orizzonte di SIMULAZIONE: il modello
# continua a girare fino al 2080 - serve per vedere che lo stato stazionario è
# davvero raggiunto e che la finestra di prepensionamento si è richiusa - ma gli
# ultimi anni sono una linea piatta che ruba spazio alla transizione, che è la parte
# che si deve leggere. Le tabelle e i CSV restano a orizzonte pieno.
FINE_GRAFICI = 2070

# --- parametri OVERRIDABILI da CLI (default = comportamento v1) --------------
P2_HIST = 0.10
P2_MIN = 0.50       # PAVIMENTO sulla stabilizzazione: P2 non scende mai sotto questo
                    # valore, nemmeno durante la rampa. Modella un piano straordinario
                    # che agisce SUBITO invece di arrivare a regime in RAMP anni.
                    # 0,50 è tarato sull'obiettivo di 15.000 stabilizzati nel primo
                    # triennio (2026-2028): ne dà 15.584 contro gli 8.668 della sola
                    # rampa. Non tocca lo stato iniziale (gli RTT del 2026 sono stati
                    # assunti col P2_HIST del passato). --p2-min 0 torna alla rampa pura.
                    #
                    # ATTENZIONE a cosa NON fa: lo stock di postdoc è INVARIANTE al
                    # pavimento, perchè l'uscita totale dal compartimento vale
                    # adv+ex = P2/precari_anni + (1-P2)/precari_anni = 1/precari_anni
                    # qualunque sia P2. Il pavimento non svuota il precariato più in
                    # fretta: sposta 6.916 persone dall'uscita dall'accademia alla
                    # tenure track. È una redistribuzione a somma zero fra le due porte.
PRECARI_ANNI = 3.0
RAMP = 5            # anni di rampa: le leve sono a regime dall'anno ANNO0+RAMP (2030)
PHD_IN_FTE = False  # i dottorandi contano negli FTE-ricerca del dato Eurostat?
                    # Default NO: con NO il modello riproduce ~45k dottorandi e HERD
                    # 0,33% (vs 0,36 ISTAT); con SI dà 20,7k e 0,25%. Il loro COSTO
                    # entra sempre in HERD/budget, a prescindere dal conteggio.
SUPPORTO = None     # overhead tecnici/amministrativi di ricerca sul costo-ricerca
                    # del personale strutturato. None = auto-calibrato su HERD_OGGI.

# --- LEVA PREPENSIONAMENTO: lisciare l'onda dell'organico --------------------
# DA DOVE VIENE L'ONDA. Non da troppi pensionamenti: da troppo POCHI. Il ruolo di
# oggi è concentrato sui 50-62 anni (la campana empirica di _coorte, media 56) e si
# svuota entro il 2050. Poi per una decina d'anni non va in pensione quasi nessuno
# (~700-1.100 uscite/anno contro le ~3.900 di regime) mentre le assunzioni corrono
# già al ritmo di target: lo stock si accumula fino a un picco intorno al 2057,
# +13% sopra lo stato stazionario. Subito dopo arriva l'ECO della coorte assunta in
# blocco nella transizione (fino a ~7.300 uscite/anno nel 2062) e l'organico
# ridiscende. Il buco e l'eco sono la stessa onda vista due volte.
#
# COSA FA LA LEVA. Sposta uscite DALL'ECO DENTRO IL BUCO: chi ha fra ETA_PENS-n e
# ETA_PENS-1 anni può uscire in anticipo, con un'adesione che sale e ridiscende
# lungo una finestra di anni. Non è un taglio di organico, è un ANTICIPO: fuori
# dalla finestra la leva è spenta e lo stato stazionario NON cambia. È quindi una
# leva sull'ONDA e non sul LIVELLO - ed è efficace proprio perchè le classi appena
# sotto ETA_PENS negli anni giusti sono le coorti grasse dell'eco.
#
# QUANTO PUÒ FARE, misurato. L'oscillazione ha DUE fasi: una CONCA (-7,8% sotto il
# regime intorno al 2040: la campana di partenza è già andata in pensione e le nuove
# leve non sono ancora arrivate) e poi la GOBBA (+13,5% nel 2057). Il prepensionamento
# agisce SOLO sulla gobba, che coi default qui sotto scende a +5,1%. La conca resta
# -7,8% in ogni configurazione, e non può che restarci: è una CARENZA di personale,
# e una carenza si riempie assumendo prima, non mandando in pensione prima.
#
# IL BUCO DOPO, E COME NON FARLO. Chi esce nell'anno t con n anni di anticipo è
# ASSENTE da t a t+n: l'assenza non è il profilo delle uscite, è quel profilo
# RITARDATO e allargato di n anni. Una finestra centrata sul picco fa quindi cadere
# l'assenza DOPO la gobba, quando la curva base sta già scendendo da sola di ~5.000
# posizioni l'anno: le due discese si sommano, scavano un buco, e appena la finestra
# si chiude la curva RIMBALZA in una seconda gobba.
# Il rimedio principale non è dosare l'uscita, è COLLOCARLA PRIMA: il centro sta al
# picco MENO gli anni di anticipo, che allinea l'assenza alla gobba. Da solo basta:
# su tutti e tre gli scenari azzera sia il buco sia il rimbalzo, abbassa la gobba
# più di quanto faccia la finestra sul picco, e costa un terzo di uscite in meno
# (42.010 contro 62.481 su ERA_PPP_ric). Spostarla ancora più indietro peggiora e
# poi diventa dannoso: da picco-10 in poi la finestra cade sulla campana di partenza
# invece che sull'eco, non tocca più la gobba e APPROFONDISCE la conca (a picco-18
# la gobba è quella base e la conca passa da -9,6% a -14,2%: tutti i costi e zero
# benefici). Le altre due leve affinano la coda ma sono del secondo ordine:
#   PREPENS_CODA  - l'anticipo CONCESSO si riduce col passare degli anni (4 anni
#                   all'inizio, poi 3, 2, 1): chi esce per ultimo è assente per
#                   poco, e l'assenza collassa invece di trascinarsi.
#   PREPENS_ASIMM - la finestra si chiude più in fretta di come si è aperta
#                   (sigma destro = sigma * asimm), perchè la gobba stessa è
#                   asimmetrica: sale in dieci anni e scende in cinque.
#
# COSA NON FA: non è gratis, ed è la parte che il modello mostrerebbe alla rovescia
# se non la si contabilizzasse. Chi esce smette di essere personale di ricerca, e
# quindi HERD e monte stipendi SCENDONO: sulla sola carta del bilancio della ricerca
# il prepensionamento sembra un risparmio. Ma lo Stato gli paga la pensione per gli
# anni di servizio non prestati. Le colonne prepens_* rendono visibile quel costo,
# che resta FUORI da HERD/GOVERD perchè un pensionato non è personale di R&S.
#
# DEFAULT = la configurazione consigliata, leva ACCESA. Per il modello senza
# prepensionamento: --prepens-ades 0, che lo riporta esattamente com'era prima.
PREPENS_ANNI = 4        # anni di anticipo: eleggibili le età ETA_PENS-n .. ETA_PENS-1
PREPENS_ADES = 0.5      # adesione annua al CENTRO della finestra (0 = leva spenta)
PREPENS_CENTRO = 2053   # anno centrale. IMPOSTO, non calcolato: è il picco 2057 meno
                        # i 4 anni di anticipo, cioè quello che darebbe la regola di
                        # _centro_finestra sui parametri di oggi. Fissarlo lo rende
                        # però CIECO alle altre leve: se --perm-oggi, --ramp o --p2-min
                        # spostano il picco, il 2053 non lo segue. In quel caso usa
                        # --prepens-centro-auto, che riapplica la regola.
PREPENS_SIGMA = 4.0     # semi-ampiezza gaussiana della finestra, in anni
PREPENS_CODA = 0.0      # anni in cui l'anticipo concesso scende da PREPENS_ANNI a 1
                        # dopo il centro (0 = anticipo costante su tutta la finestra)
PREPENS_ASIMM = 1.0     # sigma della metà DESTRA della finestra, in multipli di
                        # PREPENS_SIGMA (1 = simmetrica, <1 = chiusura più rapida)
TASSO_SOST = 0.75       # pensione lorda / ultimo lordo. SOLO per la diagnostica di
                        # costo: la pensione non è spesa di R&S e non entra in HERD.

# ====================== RETROFLUSSO FISCALE (IRPEF) =========================
# La spesa del modello e' quasi tutta STIPENDI, e uno stipendio pubblico e' in parte
# una partita di giro: lo Stato lo paga e se ne riprende una quota come IRPEF (piu'
# addizionali, contributi e IRAP). Il costo NETTO per la finanza pubblica e' quindi
# sensibilmente piu' basso del costo LORDO che il modello mette in HERD e in budget.
# Questo blocco tiene i parametri per quantificarlo; il calcolo sta in irpef.py.
#
# COSA NON E'. Non e' un moltiplicatore keynesiano e non conta i consumi indotti,
# l'IVA sui consumi dei ricercatori o il gettito delle imprese fornitrici. E' solo la
# parte MECCANICA e certa: le imposte e i contributi che gravano sulla busta paga che
# lo Stato sta gia' pagando. Chi volesse aggiungere l'indotto lo faccia altrove: qui
# non c'e' nessuna ipotesi di comportamento, solo l'aritmetica di una busta paga.
#
# AVVERTENZA GENERALE, vale su tutto il blocco: il modello proietta al 2080 e la
# legislazione fiscale cambia ogni anno. Questi numeri sono quelli VIGENTI e restano
# fermi per 54 anni. Non e' una previsione: e' la domanda "a fisco di oggi, quanto
# torna indietro?", che e' l'unica a cui si puo' rispondere senza inventare.

# --- (1) dal COSTO LORDO ENTE alla RETRIBUZIONE LORDA ------------------------
# Tutti i COSTO_* del modello sono costo per il datore di lavoro, non buste paga: ci
# stanno dentro i contributi a carico dell'amministrazione e l'IRAP. L'IRPEF si calcola
# invece sulla retribuzione lorda del dipendente, che e' il costo diviso il gross-up.
# Aliquote convenzionali delle relazioni tecniche RGS sul costo del lavoro pubblico:
# oneri sociali a carico amministrazione 32,70% + IRAP 8,50% = fattore 1,412.
#
# VERIFICA INTERNA (e' il motivo per cui questo numero si puo' usare qui): dividendo i
# costi del modello per 1,412 escono retribuzioni lorde plausibili una per una, e
# nessuna e' stata scelta per farle tornare -
#   PO 130.000 -> 92.068 | PA 78.000 -> 55.240 | ric.uni/EPR ruolo 73.500 -> 52.055
#   RTT 55.000 -> 38.951 | postdoc 45.000 -> 31.870 | TA 40.000 -> 28.329
#   EPR ingresso 48.200 -> 34.135 | contratto di ricerca 37.600 -> 26.629
# cioe' esattamente le fasce del CCNL Istruzione e Ricerca e del trattamento dei
# docenti. La scomposizione e' quindi un CONTROLLO dei costi unitari, non solo un
# passaggio di calcolo: se il gross-up non tornasse, sarebbero sbagliati i costi.
ALIQ_ONERI_ENTE = 0.3270       # contributi previdenziali/assistenziali c/amministrazione
ALIQ_IRAP = 0.0850             # IRAP sulle retribuzioni, metodo retributivo (enti pubblici)
GROSS_UP_DIP = 1.0 + ALIQ_ONERI_ENTE + ALIQ_IRAP       # 1,4120

# Borse di dottorato e assegni di ricerca NON sono lavoro dipendente: niente IRAP e
# contribuzione alla Gestione separata INPS (33,72% nel 2025, per chi non ha altra
# copertura), ripartita 2/3 committente e 1/3 percettore.
ALIQ_GEST_SEP = 0.3372
GROSS_UP_BORSA = 1.0 + ALIQ_GEST_SEP * 2 / 3           # 1,2248
# Controprova: 22.700 / 1,2248 = 18.533 di assegno lordo e 22.000 / 1,2248 = 17.962 di
# borsa, contro i 19.367 e 16.243 dei minimi di legge. Il costo del dottorando del
# modello comprende pero' anche budget di ricerca e maggiorazioni, non solo la borsa:
# trattarlo tutto come borsa sovrastima di ~10% i suoi contributi. Sull'IRPEF non
# incide, perche' la borsa e' esente comunque.

# --- (2) contributi a carico del PERCETTORE, che abbattono l'imponibile -------
ALIQ_CONTR_DIP = 0.0880        # CTPS, aliquota a carico dell'iscritto (dipendenti
                               # pubblici). Con l'opera di previdenza e il fondo credito
                               # l'effettiva sale a ~10,8%: userebbe un imponibile piu'
                               # basso e darebbe ~3% di IRPEF in meno. E' la principale
                               # incertezza di secondo ordine di tutto il blocco.
ALIQ_CONTR_BORSA = ALIQ_GEST_SEP / 3                   # 11,24% a carico del percettore

# --- (3) IRPEF: scaglioni, detrazioni, addizionali ---------------------------
# Tre scaglioni, assetto reso strutturale dalla L. 207/2024 (bilancio 2025).
IRPEF_SCAGLIONI = ((28_000.0, 0.23), (50_000.0, 0.35), (float("inf"), 0.43))
# Detrazione per lavoro dipendente, art. 13 TUIR nella formulazione vigente. Si azzera
# a 50.000 di reddito complessivo: sopra quella soglia l'aliquota media coincide con
# quella degli scaglioni, ed e' li' che sta quasi tutto il personale di ruolo.
DETR_LD_SOGLIE = (15_000.0, 28_000.0, 50_000.0)
DETR_LD_BASSA = 1_955.0        # fino alla prima soglia, importo fisso
DETR_LD_FISSA, DETR_LD_MOBILE = 1_910.0, 1_190.0       # fra prima e seconda soglia
# "Ulteriore detrazione" L. 207/2024 art.1 c.6: 1.000 EUR piatti fra 20k e 32k, poi in
# discesa lineare fino a 40k. Morde su postdoc, RTT e TA, cioe' proprio sulle figure
# che la riforma moltiplica: ignorarla sovrastimerebbe il gettito.
DETR_BONUS_SOGLIE = (20_000.0, 32_000.0, 40_000.0)
DETR_BONUS = 1_000.0
# Sotto i 20.000 la stessa legge prevede una SOMMA INTEGRATIVA (4,8-7,1% del reddito),
# che e' un trasferimento in uscita e non un'imposta. Non e' implementata perche' in
# questo modello NESSUNA figura tassata ci arriva: il piu' povero e' il TA a 28.329 di
# lordo. Chi abbassasse i costi unitari sotto quella soglia dovrebbe aggiungerla.
ADD_REGIONALE = 0.0175         # addizionale regionale, media ponderata (1,23%-3,33%)
ADD_COMUNALE = 0.0065          # addizionale comunale, media ponderata
# ATTENZIONE: le addizionali NON vanno all'erario ma a Regioni e Comuni. Restano
# denaro pubblico e nel consolidato della PA tornano, ma chi ragiona sul bilancio dello
# Stato in senso stretto deve guardare la sola colonna IRPEF. Sono tenute separate
# apposta e non sommate dentro l'IRPEF.

# --- (4) chi NON paga IRPEF --------------------------------------------------
# Esenzioni piene, non agevolazioni: sulle borse di dottorato l'imposta e' zero, non
# ridotta (art. 4 L. 476/1984), e altrettanto valeva per gli assegni di ricerca
# (art. 4 c.3 L. 210/1998). Ha una conseguenza contro-intuitiva che il modello mostra:
# la leva sulla BORSA di dottorato (W_PHD, da 1.195 a 1.600 EUR/mese) e' l'unica spesa
# del piano che non torna NIENTE in IRPEF - torna solo la Gestione separata. Alzare
# una borsa costa allo Stato molto piu' che alzare uno stipendio dello stesso importo.
#
# Gli assegni sono aboliti dalla L. 79/2022 e sostituiti dai contratti di ricerca, che
# sono lavoro dipendente e quindi tassati: nel ramo EPR la transizione e' esplicita nel
# costo (COSTO_EPR_ASSEGNO -> COSTO_EPR_PREC_TGT) e da li' il modello ricava quante
# teste sono ancora esenti in ciascun anno.
#
# Nel ramo UNIVERSITARIO la platea esente e' PIU' LARGA dei soli assegni, e va contata
# tutta. Oltre agli assegni ex art. 22 L. 240/2010 sono esenti anche le BORSE DI
# RICERCA e gli INCARICHI DI RICERCA post-lauream conferiti dalle universita' (borse
# di studio per attivita' di ricerca post-dottorato, art. 6 c.6 L. 398/1989): non sono
# lavoro dipendente, non pagano IRPEF, e nel modello stanno dentro il compartimento
# 'precari' insieme agli assegnisti. Sono una figura che la L. 79/2022 NON ha abolito.
#
# QUANTO PESANO. Sui 43.395 postdoc dello stato iniziale il MUR ne separa 25.113
# (RTD-A 9.222 tassati + assegni 15.891 esenti); gli altri 18.282 sono le figure che
# non separa - co.co.co, borsisti, contratti di ricerca. La quota esente sta quindi
# fra due estremi larghi:
#     0,366  se fossero esenti i soli assegni certi, sull'intero stock
#     0,633  se le figure non separate avessero lo stesso mix di quelle osservabili
#     0,787  se TUTTI i non separati fossero borse o incarichi di ricerca
# Il default e' quello di mezzo, che e' anche l'unica ipotesi che non richiede di
# sapere cio' che il MUR non pubblica. Gli altri due valori sono la sensitivita', e
# l'intervallo e' ampio: e' la principale incertezza del retroflusso dei primi anni.
QUOTA_ESENTE_PREC_UNI = 15_891 / 25_113         # 0,633 - vedi sopra, --quota-esente-postdoc
QUOTA_ESENTE_PREC_UNI_TGT = 0.0                 # a regime: il precariato e' regolarizzato
                                                # in contratti di ricerca, che sono lavoro
                                                # dipendente e quindi tassato. E' un'IPOTESI
                                                # di scenario, non un fatto: borse e
                                                # incarichi di ricerca restano legali e un
                                                # ateneo puo' continuare a usarli. Alzalo
                                                # per vedere quanto costa lasciarli in giro.
#
# ATTENZIONE a cosa questa quota NON risolve. Il modello tiene COSTO['precari'] piatto
# a 45.000 per tutti, mentre un assegno ne costava 22.700: la quota esente corregge il
# REGIME FISCALE delle teste, non il loro prezzo. E' l'unico modo di farlo senza rompere
# la quadratura - separare gli esenti al loro costo vero, tenendo fisso il costo medio a
# 45.000, richiederebbe di attribuire ai contrattisti stipendi da 83.000, che non
# esistono. Il che e' anche il segnale che i 45.000 sono alti per il bacino del 2026:
# sono gia' il costo di un contratto di ricerca, cioe' del punto di ARRIVO della
# transizione, non della media di partenza. Sul retroflusso l'effetto e' di secondo
# ordine (gli esenti pagano zero comunque, e ne resta solo un po' di contributi in
# piu'); sulla SPESA del 2026 no, ma quella e' una questione del ramo costi.
