"""Costanti e parametri di scenario del modello FTE.
"""
from __future__ import annotations
import os

# Tutto cio' che il modello PRODUCE - png e csv - va in una sottocartella dedicata,
# separata dal codice e dai dati di ingresso. Non viene creata qui: la creano gli
# entry point (piano_transizione, confronto_prepensionamento, spesa_pubblica), che
# sono anche gli unici a poterla cambiare con --out. Importare un modulo non deve
# scrivere sul disco.
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)) or ".", "output")

POP_SSP2 = {2025: 58_934.5, 2030: 58_198.5, 2035: 57_549.9, 2040: 56_987.7,
            2045: 56_465.8, 2050: 55_949.2, 2055: 55_223.2, 2060: 54_319.9,
            2065: 53_295.2, 2070: 52_314.4, 2075: 51_487.8, 2080: 50_823.4,
            2085: 50_229.7}

def pop_100k(anno: int) -> float:
    a = min(max(anno, min(POP_SSP2)), max(POP_SSP2))
    nodi = sorted(POP_SSP2)
    lo = max(y for y in nodi if y <= a)
    hi = min(y for y in nodi if y >= a)
    p = POP_SSP2[lo] if lo == hi else (POP_SSP2[lo] + (POP_SSP2[hi] - POP_SSP2[lo])
                                       * (a - lo) / (hi - lo))
    return p / 100.0

POP_100K = 589.34
PIL_MLN = 2_192_182
LAMBDA_HE = 0.70

# alpha = quota di tempo dedicata alla RICERCA; 1-alpha e' la didattica.
#
# IL POSTDOC E' L'UNICA FIGURA CON UN ALPHA CHE SI MUOVE NEL TEMPO, ed e' una LEVA del
# piano come W o P2, non un dato rivisto. Oggi il postdoc insegna (0,75 come RTT e
# ricercatori): e' la situazione osservata, e l'anno base deve riprodurla, altrimenti la
# calibrazione starebbe misurando un sistema che non esiste. A regime il postdoc e' una
# posizione di SOLA RICERCA (1,00): la didattica che oggi gli si scarica addosso e'
# esattamente cio' che il piano vuole togliere. In mezzo c'e' la rampa RAMP, come per
# tutte le altre leve - la didattica non si toglie a nessuno per decreto da un anno
# all'altro, si smette di assegnarla man mano.
#
# Conseguenze, tutte GRADUALI e tutte volute:
#   - il postdoc pesa via via di piu' negli FTE-RICERCA. Nel 2026 no: il gap Eurostat si
#     chiude sui 47.340 precari di sempre, perche' _precari_per_chiudere() lavora sul
#     valore di OGGI;
#   - esce progressivamente dal denominatore del rapporto studenti/docente. Resta in
#     DOCENTI_DID, perche' durante la rampa il suo peso didattico e' ancora > 0.
# Coerente con la proposta di togliere la valutazione della didattica dai concorsi RTT:
# non si puo' pretendere didattica da chi non ha un incarico didattico.
ALPHA_PREC_OGGI = 0.75             # quota-ricerca del postdoc OGGI (un quarto didattica)
ALPHA_PREC_TGT = 1.00              # a regime: sola ricerca, nessuna didattica
ALPHA = {"dottorando": 0.75, "docente": 0.50, "ric_uni": 0.75,
         "RTT": 0.75, "precari": ALPHA_PREC_OGGI}


def alpha_precari(t: int | None = None) -> float:
    """Quota-ricerca del postdoc all'anno t della rampa. t=None vale OGGI, ed e' il
    default giusto per tutto cio' che guarda l'anno base: calibrazione, chiusura del gap
    Eurostat, stato iniziale. Chi vuole il REGIME passa t >= RAMP esplicitamente."""
    if t is None or t <= 0:
        return ALPHA_PREC_OGGI
    if t >= RAMP:
        return ALPHA_PREC_TGT
    return ALPHA_PREC_OGGI + (ALPHA_PREC_TGT - ALPHA_PREC_OGGI) * t / RAMP


def alpha(t: int | None = None) -> dict[str, float]:
    """ALPHA dell'anno t: identico a ALPHA tranne il postdoc, che rampa."""
    return {**ALPHA, "precari": alpha_precari(t)}
QUOTA_PO = 0.39

# Frazione di una coorte che arriva a ORDINARIO. Non è 1: nella classe 65+ del 2024
# ci sono 3.716 PO e 2.070 PA, cioè il 36% dei professori va in pensione da associato
# (USTAT, serie storica per classi di età e qualifica).
#
# Il 0,642 grezzo va corretto perchè i PO restano in servizio più a lungo dei PA e sono
# quindi SOVRARAPPRESENTATI nella classe terminale: da quota = pi*d_PO/(pi*d_PO +
# (1-pi)*d_PA) con d = anni passati oltre i 65, l'intervallo identificato è 0,54-0,64
# a seconda di quanto si separano le due permanenze. 0,59 è il punto medio.
#
# È l'UNICA cosa che i dati identificano sul profilo di promozione. Lo spread dei TEMPI
# di promozione non lo è: la dispersione per età osservata mescola i tempi di promozione
# con l'età d'ingresso in ruolo, che ha sd ~6,4 anni (distribuzione per età degli RTD).
# Il modello fissa l'ingresso a eta_ruolo_in() per tutti, quindi buona parte della rampa
# osservata non gli compete - un ordinario di 42 anni non è stato promosso dopo un anno
# di ruolo, è entrato in ruolo a 32. Per questo la promozione resta a soglia secca e si
# corregge solo il livello a cui la soglia satura.
PROMOSSI_PO = 0.59

SCALA_PA = [(0, 56_786), (3, 60_365), (6, 66_149), (9, 70_071), (12, 75_730),
            (15, 78_560), (18, 84_220), (21, 87_050), (24, 92_709), (27, 94_454),
            (30, 97_944), (33, 99_689), (36, 103_179)]
SCALA_PO = [(0, 80_916), (3, 89_076), (6, 94_626), (9, 102_595), (12, 106_580),
            (15, 114_550), (18, 118_535), (21, 126_504), (24, 128_962),
            (27, 133_876), (30, 136_333), (33, 141_248)]

ANNI_DA_ASSOCIATO = None
QUOTA_PO_TGT = 0.50
# Ripiego per costo_docente() a coorte vuota: il valore che la funzione restituisce
# sulla coorte 2026 con la soglia calibrata. Da riallineare se cambiano le scale,
# ETA_PENS o PROMOSSI_PO - era 106.525 con ETA_PENS=68 e senza saturazione.
COSTO_DOCENTE_RIPIEGO = 110_541

# --- POSTDOC: DUE FIGURE, non una ------------------------------------------
# Il compartimento postdoc non e' omogeneo. Chi inizia il postdoc entro ANNI_FINESTRA_IDR
# anni dalla LAUREA MAGISTRALE sta su un INCARICO DI RICERCA - lordo amministrazione
# piu' basso ed ESENTE IRPEF; gli altri su un contratto di ricerca pieno, tassato.
#
# LA FINESTRA E' 4 ANNI, NON 6. E' una scelta di proposta, non un dato: l'incarico di
# ricerca esente e' uno strumento di INGRESSO, e una finestra lunga lo trasforma in un
# canale di sottoinquadramento per meta' del precariato. A 4 anni resta quello che deve
# essere - il ponte fra dottorato e primo contratto - e tutto il resto del postdoc sta
# su contratto di ricerca pieno e tassato. Il modello ne paga il conto: il postdoc medio
# costa di piu' e la platea esente si assottiglia.
#
# QUOTA_PREC_INCARICO e' STIMATA, non osservata. Si incrociano due distribuzioni:
#   - eta' al conseguimento del DOTTORATO: media 32,6 anni, con 22,2% sotto i 29,
#     29,7% fra 29 e 30, 31,3% fra 31 e 35, 16,8% a 36 e oltre
#     [AlmaLaurea, Profilo dei Dottori di ricerca 2022, Report 2023, Fig.3 p.7]
#   - eta' media alla LAUREA MAGISTRALE biennale: 27,2 anni
#     [AlmaLaurea, Profilo dei Laureati 2022]
# Il postdoc inizia alla fine del dottorato, quindi "entro 4 anni dalla magistrale"
# equivale a "dottorato conseguito prima dei 27,2+4 = 31,2 anni". Interpolando dentro
# le classi si ottiene il 53,1%, da cui 0,53. La soglia cade appena sopra la MEDIANA
# (31,0 anni), ed e' per questo che la quota crolla di 12 punti togliendo 2 anni di
# finestra: si taglia dentro la classe piu' popolata invece che sulla sua coda.
# NB: il controllo indipendente per AREA disciplinare (65,6% contro 65,7%) valeva per la
# finestra a 6 anni e NON si rifa' qui - servirebbero le distribuzioni per area, non le
# sole medie. La stima aggregata a 4 anni sta quindi in piedi da sola.
# SENSITIVITA': l'eta' alla magistrale e' il punto debole (i dottori sono selezionati e
# probabilmente si laureano prima della media), e a finestra corta pesa DI PIU', perche'
# la soglia si muove dentro la classe densa: a 26,5 la quota scende al 44,5%, a 28,0
# sale al 58,2% (a 6 anni l'escursione era 61,3-70,7). Si muove con --quota-incarico.
#
# DUE QUOTE DIVERSE, e confonderle e' l'errore facile:
#   QUOTA_PREC_INCARICO  = quota di PERSONE che hanno l'opzione (0,53, stimata sopra)
#   quota_incarico_stock = quota di ANNI-PERSONA dello stock che ci stanno davvero
# La finestra si chiude DURANTE il postdoc: chi ha l'opzione la usa solo per
# ANNI_INCARICO dei PRECARI_ANNI di permanenza, poi passa al contratto di ricerca. Sullo
# stock - che e' quello che il modello prezza e tassa - la quota vale quindi
# 0,53 x 0,5/5 = 0,053, non 0,53.
#
# ANNI_INCARICO scende da 2,5 a 0,5 per la stessa ragione, ed e' una SOTTRAZIONE, non un
# riscalamento: chiudere la finestra 2 anni prima accorcia di esattamente 2 anni il
# tratto coperto di CHIUNQUE resti dentro. L'incarico di ricerca diventa cosi' una figura
# residuale - mezzo anno a regime, sulla meta' scarsa che ci arriva in tempo - e non piu'
# il regime ordinario del primo biennio di postdoc.
# ONESTA' DEL NUMERO: 2,5 era gia' una stilizzazione ("meta' del postdoc"), non l'output
# di una media sulla distribuzione; l'agente rappresentativo del modello finisce il
# dottorato a ETA_FINE_PHD=33, cioe' 5,8 anni dopo la magistrale, e sarebbe fuori
# finestra da subito sia a 6 anni sia a 4. ANNI_INCARICO vive sulla SOTTOPOPOLAZIONE che
# si dottora presto, non sull'agente medio: e' un parametro di stock, e va letto insieme
# a QUOTA_PREC_INCARICO, mai da solo.
ANNI_FINESTRA_IDR = 4              # anni dalla magistrale entro cui spetta l'incarico
COSTO_PREC_INCARICO = 30_000       # lordo amministrazione, ESENTE IRPEF
COSTO_PREC_CONTRATTO = 45_000      # contratto di ricerca, tassato
QUOTA_PREC_INCARICO = 0.53         # quota di persone che hanno l'opzione
ANNI_INCARICO = 0.5                # anni di postdoc copribili con incarico di ricerca


def quota_incarico_stock() -> float:
    """Quota dello STOCK di postdoc su incarico di ricerca, cioe' la quota di
    anni-persona. E' una funzione e non una costante perche' dipende da PRECARI_ANNI,
    che si muove da CLI: a permanenza piu' lunga la stessa finestra copre una frazione
    piu' piccola della carriera precaria. Il min() serve al caso PRECARI_ANNI <=
    ANNI_INCARICO, dove tutto il postdoc sta dentro la finestra."""
    if PRECARI_ANNI <= 0:
        return 0.0
    return QUOTA_PREC_INCARICO * min(1.0, ANNI_INCARICO / PRECARI_ANNI)


def costo_precari() -> float:
    """Costo medio di un postdoc: media delle due figure pesata sugli ANNI-PERSONA.
    E' il valore che il motore usa per la SPESA, mentre irpef.py tiene le due figure
    separate; le due masse coincidono per costruzione, ed e' cio' che fa quadrare la
    scomposizione fiscale col monte stipendi."""
    q = quota_incarico_stock()
    return q * COSTO_PREC_INCARICO + (1 - q) * COSTO_PREC_CONTRATTO


COSTO = {"docente": COSTO_DOCENTE_RIPIEGO,
         "ric_uni": 73_500,
         "RTT": 55_000,
         "precari": 0.0,        # riempito sotto, quando PRECARI_ANNI e' definito
         "dottorando": 22_000}
QUOTA_RIC_UNI = 1 / 3

REDDITO_PHD_IT = 78_758
REDDITO_PHD_EU = 91_343
UPLIFT_PPP_EU = REDDITO_PHD_EU / REDDITO_PHD_IT
UPLIFT_PPP_TOP5 = (sum([153_819, 148_806, 119_119, 113_706, 113_695])
                   / 5) / REDDITO_PHD_IT
UPLIFT_PPP = UPLIFT_PPP_EU
UPLIFT_PPP_CARSA06 = (sum([60_530, 56_721, 56_268, 55_998, 53_358]) / 5) / 34_120
UPLIFT_PPP_CARSA06_UE25 = 40_126 / 34_120
UPLIFT_PPP_PLI24 = 1.349

SHIFT = 0.01
HERD_TGT = 0.69-SHIFT
HERD_OGGI = 0.36

D_RTT = 5
D_PHD = 3
# ETA_PENS è l'età di uscita MEDIA, non il limite di legge: nel modello tutti escono
# lì, quindi il valore giusto è quello che riproduce gli anni-persona osservati.
#
# Stimata dalla serie USTAT con l'identità di popolazione stazionaria applicata alla
# classe aperta 65+ (permanenza media = stock / flusso di uscita), su finestre lunghe
# per smorzare la crescita dello stock: 69,1-69,4 a seconda della finestra (2005-2024,
# 2010-2024, 2015-2024, 2020-2024). Si arrotonda a 69 perchè le classi della coorte
# sono annuali.
#
# La stima è sull'AGGREGATO PO+PA: le promozioni sono un flusso interno e si cancellano.
# Sulle singole fasce non si cancellano e restano solo estremi (PO <= 70,2, PA >= 68,5),
# quindi non si differenzia per fascia. Ed è condizionata all'essere in servizio a 65:
# chi esce prima non entra nel conto, per cui 69 è semmai generoso.
#
# ETA_FINE_PHD è anch'essa OSSERVATA, non assunta: 32,6 anni di età media al
# conseguimento del dottorato [AlmaLaurea, Profilo dei Dottori di ricerca 2022, Report
# 2023, Fig.3 p.7], arrotondati a 33 perché le classi della coorte sono annuali.
# Il vecchio 34 era un'ipotesi, ed era INCOMPATIBILE con la stima della quota a incarico
# di ricerca: a 34 anni si è già a 6,8 anni dalla laurea magistrale (27,2), quindi
# nessuno sarebbe stato dentro la finestra, che allora era di 6 anni. Con 33 il divario
# medio è 5,4 anni e le due parti del modello raccontano la stessa storia.
# Con la finestra portata a 4 anni la coerenza è più debole - 5,4 > 4 - ma il punto non
# cambia di segno: la quota a incarico non è calcolata sull'età MEDIA, è l'integrale
# della distribuzione sotto la soglia, e a 4 anni ci sta dentro la metà che si dottora
# presto. Vedi la nota su ANNI_INCARICO nel blocco POSTDOC.
ETA_FINE_PHD, ETA_PENS = 33, 69

# Gli enti di ricerca sono personale CONTRATTUALIZZATO, con regole di quiescenza loro.
# La stima sopra è sui docenti universitari e non si estende: si lascia il 68 che il
# modello usava prima, per non cambiare i risultati EPR sulla base di un dato che non
# li riguarda.
ETA_PENS_EPR = 68
ETA_INIZIO_PHD = ETA_FINE_PHD - D_PHD
S_RTT_PERM = 1.0

STAB_PHD = 0.25
P2_TGT = 0.60
P1 = min(1.0, STAB_PHD / P2_TGT)

P2_HIST = 0.10
P2_MIN = 0.50
PRECARI_ANNI = 5.0
# ORA che PRECARI_ANNI esiste, il costo medio del postdoc e' calcolabile. main() lo
# ricalcola dopo la CLI, perche' sia --quota-incarico sia --precari-anni lo spostano.
COSTO["precari"] = costo_precari()
QUOTA_ESENTE_PREC_UNI_DEF = quota_incarico_stock()
RAMP = 10
RAMP_PHD = 5
PHD_IN_FTE = False
SUPPORTO = None

BORSA_OGGI, BORSA_TGT = 1195.0, 1656.0
W_PHD = BORSA_TGT / BORSA_OGGI

PERM_OGGI = 43_046
RIC_UNI_RUOLO_OGGI = 4_831
PRECARI_OGGI = 35_000

# Chi entra nel denominatore della DIDATTICA. Il postdoc c'e' ancora, e DEVE esserci:
# il suo peso didattico e' 1-alpha_precari(t), che parte da 0,25 e si azzera solo a fine
# rampa. Toglierlo dalla tupla vorrebbe dire azzerarne la didattica di colpo nel 2026.
DOCENTI_DID = ("docente", "ric_uni", "RTT", "precari")
STUD_DOC_OGGI = 19.45
STUD_DOC_TGT = 14.3
STUDENTI_OGGI = 0.0
RIC_UNI_EUROSTAT = 64_202.0
DENS_OGGI = 0.0
FTE_OGGI = 1.0


ALPHA_EPR = 0.75
D_PREC_EPR = 5
P2_EPR = 0.6
ETA_RUOLO_EPR = ETA_FINE_PHD + D_PREC_EPR
PERM_DUR_EPR = ETA_PENS_EPR - ETA_RUOLO_EPR
EPR_NON_MUR_OGGI = 23_840
PHD_NEL_DIRETTO_EPR = 0.50
RIC_EPR_OGGI = 27_672.0
EPR_PRECARI_OGGI = 6_000
EPR_RICERC_OGGI = round(RIC_EPR_OGGI / ALPHA_EPR)
EPR_RUOLO_OGGI = EPR_RICERC_OGGI - EPR_PRECARI_OGGI

COSTO_EPR_PREC_OGGI = 30_000
COSTO_EPR_PREC_TGT = 45_000
COSTO_EPR_ASSEGNO = 22_700
COSTO_EPR_RUOLO = 73_500
COSTO_EPR_INGRESSO = 48_200

SCALA_EPR_III = [(0, 53107), (3, 57021), (8, 61074), (13, 65248),
                 (17, 72675), (22, 78637), (30, 86268)]
SCALA_EPR_II = [(0, 66627), (3, 72408), (8, 78408), (13, 84416),
                (17, 94540), (22, 102895), (30, 113601)]
SCALA_EPR_I = [(0, 85280), (3, 93390), (8, 101865), (13, 110251),
               (17, 125610), (22, 137210), (30, 152237)]

ANNI_DA_LIV2 = None
ANNI_DA_LIV1 = None
QUOTA_EPR_I = 0.10
QUOTA_EPR_II = 0.19
QUOTA_EPR_III = 0.71
QUOTA_EPR_I_TGT = 0.20
QUOTA_EPR_II_TGT = 0.40
QUOTA_EPR_III_TGT = 0.40

GOVERD_OGGI, GOVERD_TGT = 0.21, 0.22 + SHIFT
GOVERD_MIN = GOVERD_TGT
EPR_PAV_GAIN = 0.25

GERD_OGGI, GERD_TGT = 1.38, 3.00
HERD_RIF, GOVERD_RIF = HERD_TGT, GOVERD_TGT
LAMBDA_GOV = 0.70
OVH_EPR_SUPP = 0.0
OVH_EPR_ATTR = 0.0
PHD_OGGI_REALE = 47_000
ANNO0, ORIZZONTE = 2026, 54
FINE_GRAFICI = 2070

ATTREZZ_INVILUPPO = False
ATTREZZ_PICCO_1 = 2040
ATTREZZ_PICCO_2 = 2055
ATTREZZ_QUOTA_FINE = 2070

TA_UNI_RATIO = 31_357.0 / 64_202.0
TA_EPR_RATIO = 17_537.0 / 27_672.0
TA_UNI_OGGI = 0.0
TA_EPR_OGGI = 0.0
TA_ELAST = 2.2
ALPHA_TA = 31_357.0 / 55_738.0
COSTO_TA = 35_000
TA_CAP = 90_000
TA_UPLIFT = 1.6
TA_SEGUE_W = True

PREPENS_ANNI = 0
PREPENS_ADES = 0.3
PREPENS_CENTRO = 2055
PREPENS_SIGMA = 10.0
PREPENS_CODA = 0.0
PREPENS_ASIMM = 1.0
TASSO_SOST = 0.75

SCATTI_BLOCCO_DA = 2045
SCATTI_BLOCCO_ANNI = 5
SCATTI_BLOCCO_RECUPERO = 0.0

SCATTI_BLOCCO2_DA = 2033
SCATTI_BLOCCO2_ANNI = 2
SCATTI_BLOCCO2_RECUPERO = 0.0

ALIQ_ONERI_ENTE = 0.3270
ALIQ_IRAP = 0.0850
GROSS_UP_DIP = 1.0 + ALIQ_ONERI_ENTE + ALIQ_IRAP
ALIQ_GEST_SEP = 0.3372
GROSS_UP_BORSA = 1.0 + ALIQ_GEST_SEP * 2 / 3
ALIQ_CONTR_DIP = 0.0880
ALIQ_CONTR_BORSA = ALIQ_GEST_SEP / 3
IRPEF_SCAGLIONI = ((28_000.0, 0.23), (50_000.0, 0.35), (float("inf"), 0.43))
DETR_LD_SOGLIE = (15_000.0, 28_000.0, 50_000.0)
DETR_LD_BASSA = 1_955.0
DETR_LD_FISSA, DETR_LD_MOBILE = 1_910.0, 1_190.0
DETR_BONUS_SOGLIE = (20_000.0, 32_000.0, 40_000.0)
DETR_BONUS = 1_000.0
ADD_REGIONALE = 0.0175
# La quota ESENTE dei postdoc universitari non e' piu' un residuo fiscale sul mix
# osservato del 2026 (assegni vs RTD-A): e' la quota a INCARICO DI RICERCA, che ha una
# base strutturale - l'eta' - e quindi NON si esaurisce lungo la rampa. Le due costanti
# restano perche' il motore rampa comunque fra loro; coincidono, quindi la rampa e' piatta.
QUOTA_ESENTE_PREC_UNI = QUOTA_ESENTE_PREC_UNI_DEF
QUOTA_ESENTE_PREC_UNI_TGT = QUOTA_ESENTE_PREC_UNI_DEF

ADD_COMUNALE = 0.0065

# --- ANCORA APERTE (non implementate) --------------------------------------
# tenere la differenza associato - ordinario? solo come costo ma togliere la label?
