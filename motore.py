"""Motore stock-flow: lo stato per coorte e la sua evoluzione anno per anno.

Contiene lo Stato, la sua inizializzazione dagli stock osservati, i conteggi
(teste, FTE di ricerca, FTE didattici), la spesa dei due rami contabili e il
ciclo di simulazione. E' l'unico punto in cui il tempo avanza.

CONVENZIONE: i valori di configurazione si leggono SEMPRE come C.NOME, mai importati
per nome. main() li riassegna a runtime (calibrazioni, argomenti da CLI) e solo
l'accesso per attributo vede il rebinding; un `from config import X` catturerebbe una
copia congelata all'import. Le funzioni invece non vengono mai riassegnate e si
importano per nome.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

import config as C
from irpef import ESENTE, Voce, retroflusso
from regime import _epr_in_tgt, _ta_epr, _ta_uni, eta_ruolo_in, kappa

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
    # "Ombra" previdenziale del prepensionamento, indicizzata per ANNI DI ANTICIPO
    # RESIDUI. NON è personale in servizio: non entra in nessun conteggio di teste,
    # FTE, HERD o monte stipendi. Serve solo a non perdere di vista che quelle
    # persone lo Stato le paga lo stesso. Si svuota da sola, una classe all'anno.
    prep_teste: list[float]   # teste uscite in anticipo e ancora "in carico"
    prep_costo: list[float]   # il loro ultimo lordo, per stimarne la pensione


def _p1_hist() -> float:
    """P1 di OGGI, ricavato dallo stock osservato di dottorandi: quota di dottori che
    tenta la carriera. Oggi è alta (il filtro sta a valle, P2_HIST=0,10); a regime
    scende a STAB_PHD perchè il filtro si sposta all'uscita dal dottorato."""
    return (_uni_in0() + _epr_in0()) / (C.PHD_OGGI_REALE / C.D_PHD)


def _uni_in0() -> float:
    """Flusso di postdoc UNIVERSITARI oggi, ricavato dallo STOCK osservato invece che
    dal target di densità: un compartimento con permanenza media PRECARI_ANNI e stock
    PRECARI_OGGI riceve PRECARI_OGGI/PRECARI_ANNI ingressi l'anno.

    Prima era il residuo che faceva quadrare la densità sul valore imposto; così il
    modello non poteva essere falsificato dai dati sull'organico. Adesso sì - e infatti
    lo scarto contro Eurostat esce dichiarato invece che riassorbito."""
    return C.PRECARI_OGGI / C.PRECARI_ANNI


def _epr_in0() -> float:
    """Flusso di contratti di ricerca EPR oggi, dallo stock osservato."""
    return C.EPR_PRECARI_OGGI / C.D_PREC_EPR


def _pd_in0() -> float:
    """Flusso PhD in ingresso oggi: alimenta ENTRAMBI i rami, quindi è la somma
    dei due fabbisogni a valle divisa per la sopravvivenza P1 odierna."""
    return (_uni_in0() + _epr_in0()) / _p1_hist()


def _quota_epr0() -> float:
    """Quota EPR implicita nello stato di partenza (vs QUOTA_EPR a regime)."""
    return _epr_in0() / (_uni_in0() + _epr_in0())


def _coorte(teste: float, eta_in: int) -> list[float]:
    """Distribuisce uno stock su classi d'età con la campana empirica (56, sd 7)."""
    eta = np.arange(eta_in, C.ETA_PENS)
    peso = np.exp(-0.5 * ((eta - 56) / 7) ** 2)
    return list(peso / peso.sum() * teste)


def _init_stato(pd_in0: float) -> Stato:
    perm = _coorte(C.PERM_OGGI, eta_ruolo_in(C.PRECARI_ANNI))
    phd = [pd_in0] * C.D_PHD
    precari = _uni_in0() * C.PRECARI_ANNI
    rtt = [C.P2_HIST * _uni_in0()] * C.D_RTT
    epr_prec = [_epr_in0()] * C.D_PREC_EPR
    epr_ruolo = _coorte(C.EPR_RUOLO_OGGI, C.ETA_RUOLO_EPR)
    # i ricercatori a tempo indeterminato SONO la figura 'ric_uni' che oggi esiste già:
    # ruolo a esaurimento, profilo di ricerca. La riforma non la crea, la ripopola.
    perm_ric = _coorte(C.RIC_UNI_RUOLO_OGGI, eta_ruolo_in(C.PRECARI_ANNI))
    return Stato(phd, precari, rtt, perm, perm_ric, epr_prec, epr_ruolo,
                 [0.0] * C.PREPENS_ANNI, [0.0] * C.PREPENS_ANNI)


def _precari_per_chiudere() -> float:
    """Stock di precari che riconcilia l'FTE del modello con RIC_UNI_EUROSTAT.

    Il legame è LINEARE e i precari entrano per DUE vie, non una: direttamente col
    proprio alpha, e indirettamente attraverso lo stock RTT che alimentano
    (RTT = P2_HIST * precari/PRECARI_ANNI * D_RTT). Ignorare la seconda via
    sovrastimerebbe i precari necessari di circa il 4%.

    ATTENZIONE all'effetto collaterale: alzando i precari a P2_HIST invariato si alza
    anche l'RTT ricostruito, che prima dell'operazione coincideva con quello osservato
    a meno dell'1,2%. Chiudere il gap qui costa quella verifica. L'alternativa è tenere
    l'RTT sul dato e lasciare che sia P2_HIST a scendere (vedi la diagnostica in main)."""
    fisso = C.PERM_OGGI * C.ALPHA["docente"] + C.RIC_UNI_RUOLO_OGGI * C.ALPHA["ric_uni"]
    per_prec = C.ALPHA["precari"] + C.ALPHA["RTT"] * C.P2_HIST * C.D_RTT / C.PRECARI_ANNI
    return max(0.0, (C.RIC_UNI_EUROSTAT - fisso) / per_prec)


def _fte_uni_oggi() -> float:
    """FTE-ricercatori universitari dello stato iniziale, RICOSTRUITI dagli stock
    osservati. È la grandezza da confrontare con RIC_UNI_EUROSTAT: se i due numeri non
    coincidono, il modello e la contabilità nazionale non stanno misurando la stessa
    popolazione, e va detto invece che aggiustato con un parametro libero.
    Il flusso PhD non entra (i dottorandi non sono fra i ricercatori, per ipotesi),
    quindi si può costruire lo stato con pd_in0 = 0."""
    return _fte_ric_uni(_init_stato(0.0))


def _ramp(t: int, v0: float, v1: float) -> float:
    return v1 if t >= C.RAMP else v0 + (v1 - v0) * t / C.RAMP


# ---------------------------- prepensionamento ------------------------------
def _prepens_on() -> bool:
    return C.PREPENS_ANNI >= 1 and C.PREPENS_ADES > 0


def _prepens_pesi(anno: int, centro: float) -> list[float]:
    """Adesione dell'anno CLASSE PER CLASSE: l'elemento j-1 è la quota di chi ha
    j anni di anticipo (cioè ETA_PENS-j anni d'età) che lascia in quell'anno.

    Nel tempo è una campana gaussiana, troncata a 3 sigma. Gaussiana e non finestra
    rettangolare perchè un'accensione a gradino sostituirebbe l'onda con due gradini
    - il rimedio produrrebbe lo stesso genere di artefatto che deve curare. Il
    troncamento serve a rendere ESATTA, e non solo trascurabile, l'affermazione che
    fuori dalla finestra la leva è spenta: senza, lo stato stazionario al 2080
    differirebbe dal modello senza leva nella quinta cifra. La metà destra usa
    PREPENS_ASIMM per chiudersi prima.

    Fra le classi il peso è 1 fino all'anticipo concesso nell'anno e 0 oltre, con
    UNA classe a peso frazionario sul bordo: l'anticipo scende con continuità da
    PREPENS_ANNI a 1 lungo PREPENS_CODA anni dopo il centro, invece di saltare da
    una classe all'altra. A coda 0 il peso è lo stesso per tutte le classi e si
    ricade nella leva ad anticipo costante."""
    if not _prepens_on():
        return [0.0] * C.PREPENS_ANNI
    sig = C.PREPENS_SIGMA * (C.PREPENS_ASIMM if anno > centro else 1.0)
    z = (anno - centro) / sig
    if abs(z) > 3.0:
        return [0.0] * C.PREPENS_ANNI
    phi = C.PREPENS_ADES * float(np.exp(-0.5 * z ** 2))
    n_eff = float(C.PREPENS_ANNI)
    if C.PREPENS_CODA > 0 and anno > centro:
        avanz = min(1.0, (anno - centro) / C.PREPENS_CODA)
        n_eff = C.PREPENS_ANNI + (1.0 - C.PREPENS_ANNI) * avanz
    return [phi * min(1.0, max(0.0, n_eff - j + 1.0))
            for j in range(1, C.PREPENS_ANNI + 1)]


def _esci_in_anticipo(coorte: list[float], pesi: list[float], costo: float
                      ) -> tuple[list[float], list[float]]:
    """Applica l'adesione per classe alle ultime PREPENS_ANNI classi d'età, IN
    PLACE. Ritorna (teste, ultimo lordo) indicizzati per ANNI DI ANTICIPO:
    l'indice j contiene chi lascia scoperti j+1 anni di servizio. La classe
    ETA_PENS-1 conta UN anno di anticipo, non zero: sarebbe uscita a fine anno,
    ma esce a inizio anno, e quell'anno di servizio non lo presta."""
    teste = [0.0] * C.PREPENS_ANNI
    for j in range(1, min(C.PREPENS_ANNI, len(coorte)) + 1):   # j = anni di anticipo
        q = coorte[-j] * pesi[j - 1]
        coorte[-j] -= q
        teste[j - 1] = q
    return teste, [t * costo for t in teste]


def _teste_tot(df: pd.DataFrame) -> pd.Series:
    """Organico totale della ricerca pubblica in teste: è LA serie che oscilla, e
    quindi quella su cui si colloca la finestra e si misura se la leva ha funzionato."""
    return (df["ruolo_teste"] + df["phd_teste"] + df["postdoc_teste"] + df["rtt_teste"]
            + df["epr_precari"] + df["epr_ruolo"])


def simula_senza_prepens(dens_target: float, W: float = 1.0,
                         q_ric: float = 0.0) -> pd.DataFrame:
    """Lo stesso scenario a leva spenta: è il termine di paragone di tutto il resto."""
    salva, C.PREPENS_ADES = C.PREPENS_ADES, 0.0
    try:
        return simula(dens_target, W, q_ric)
    finally:
        C.PREPENS_ADES = salva


def _anno_picco(dens_target: float, W: float, q_ric: float) -> int:
    """Anno del massimo dell'organico SENZA prepensionamento. Va misurato a leva
    spenta, altrimenti dipenderebbe da sè stesso (spostare il picco sposterebbe la
    finestra che lo sta spostando)."""
    df = simula_senza_prepens(dens_target, W, q_ric)
    return int(df.loc[_teste_tot(df).idxmax(), "anno"])


def _centro_finestra(dens_target: float, W: float, q_ric: float) -> int:
    """Centro della finestra ricavato dai dati: il picco MENO gli anni di anticipo.

    Non il picco. Chi esce nell'anno t è assente da t a t+n, quindi l'assenza è in
    ritardo di circa n anni sulle uscite: una finestra centrata sul picco fa cadere
    l'assenza DOPO la gobba, quando la curva base sta già scendendo, e il risultato
    è un buco seguito da un rimbalzo. Misurato su tutti e tre gli scenari a anticipo
    4 e adesione 50%: centrata sul picco lascia un buco di -2,2/-4,1 punti e un
    rimbalzo di 2,3/4,1; a picco-4 il buco e il rimbalzo sono ZERO in tutti e tre,
    la gobba è più bassa che al picco (5,1 contro 5,8 su ERA_PPP_ric) e le uscite
    sono un terzo in meno. A picco-6 si esagera e la gobba risale.
    Usata solo con --prepens-centro-auto: il default è PREPENS_CENTRO, che sui
    parametri di oggi vale esattamente quello che ritorna questa funzione."""
    return _anno_picco(dens_target, W, q_ric) - C.PREPENS_ANNI


def _teste(s: Stato) -> dict[str, float]:
    # due coorti distinte nel ruolo: la conversione avviene per RICAMBIO (i nuovi
    # entrano come ricercatori), non riclassificando i docenti già in servizio.
    return {"dottorando": sum(s.phd),
            "docente": sum(s.perm),
            "ric_uni": sum(s.perm_ric),
            "RTT": sum(s.rtt), "precari": s.precari}


def _fte(s: Stato) -> dict[str, float]:
    fte = {k: t * C.ALPHA[k] for k, t in _teste(s).items()}
    if not C.PHD_IN_FTE:
        fte["dottorando"] = 0.0
    return fte


def _fte_epr(s: Stato) -> float:
    return (sum(s.epr_ruolo) + sum(s.epr_prec)) * C.ALPHA_EPR


def _fte_didattico(s: Stato) -> float:
    """FTE-DOCENTE: le stesse persone del ramo universitario, pesate però per la quota
    di tempo NON dedicata alla ricerca. È il denominatore del rapporto studenti/docenti,
    ed è il complemento esatto degli FTE-ricerca sulle figure che insegnano."""
    return sum(t * (1 - C.ALPHA[k]) for k, t in _teste(s).items() if k in C.DOCENTI_DID)


def _fte_ric_uni(s: Stato) -> float:
    """FTE-ricercatori universitari, dottorandi SEMPRE esclusi. È la base su cui è
    ancorato il TA (Eurostat 2023, sotto l'ipotesi che i dottorandi non siano fra i
    ricercatori), quindi non deve dipendere dal flag PHD_IN_FTE."""
    return sum(v for k, v in _fte(s).items() if k != "dottorando")


def _spesa_epr(s: Stato, W: float, costo_prec: float) -> dict[str, float]:
    """GOVERD del ramo EPR. Contabilità separata da HERD: settori Eurostat diversi.
    Il TA è ora ESPLICITO e cresce con i ricercatori secondo TA_ELAST; OVH_EPR_SUPP
    resta come residuo assoluto di ciò che il modello non nomina, e OVH_EPR_ATTR
    come infrastruttura (acceleratori, grandi impianti), che davvero non scala."""
    pers = sum(s.epr_ruolo) * C.COSTO_EPR_RUOLO + sum(s.epr_prec) * costo_prec
    ric = pers * C.ALPHA_EPR                      # quota-ricerca (alpha unico)
    ta = _ta_epr(_fte_epr(s))                   # FTE di TA del settore GOV
    W_ta = W if C.TA_SEGUE_W else 1.0
    ta_ric, ta_pieno = ta * C.COSTO_TA, ta / C.ALPHA_TA * C.COSTO_TA
    return {"goverd_mln": (W * (ric + C.OVH_EPR_SUPP) + W_ta * ta_ric + C.OVH_EPR_ATTR) / 1e6,
            "budget_epr_mln": (W * (pers + C.OVH_EPR_SUPP) + W_ta * ta_pieno
                               + C.OVH_EPR_ATTR) / 1e6,
            "ta_fte": ta}


def _spesa(s: Stato, W: float, W_phd: float = 1.0) -> dict[str, float]:
    teste = _teste(s)
    # il costo-ricerca usa ALPHA anche per i dottorandi esclusi dal conteggio FTE:
    # la borsa è spesa R&S comunque la si conti nel personale.
    # due leve distinte: W sul personale, W_phd sulle borse di dottorato.
    lev = {k: (W_phd if k == "dottorando" else W) for k in teste}
    herd_pers = sum(t * C.ALPHA[k] * C.COSTO[k] for k, t in teste.items())
    herd_pers_w = sum(t * C.ALPHA[k] * C.COSTO[k] * lev[k] for k, t in teste.items())
    full_pers_w = sum(t * C.COSTO[k] * lev[k] for k, t in teste.items())
    # --- personale tecnico-amministrativo, ESPLICITO in FTE ---
    # Il costo-ricerca è FTE*COSTO_TA (l'FTE incorpora già la quota-ricerca); il monte
    # stipendi PIENO, che va nel budget e non in HERD, è (FTE/ALPHA_TA)*COSTO_TA.
    # È la stessa distinzione che il modello fa fra herd_pers e full_pers per i
    # ricercatori, e che il vecchio SUPPORTO non faceva: usava l'importo alpha-pesato
    # in entrambi, sottostimando il budget di un fattore 1/alpha.
    ta = _ta_uni(_fte_ric_uni(s))
    W_ta = W if C.TA_SEGUE_W else 1.0
    ta_ric, ta_pieno = ta * C.COSTO_TA, ta / C.ALPHA_TA * C.COSTO_TA
    # residuo: ciò che il modello ancora non nomina, sul costo-ricerca del
    # personale strutturato (non sulle borse). Sono stipendi, quindi seguono W.
    q_supp = C.SUPPORTO or 0.0
    supp = q_supp * sum(t * C.ALPHA[k] * C.COSTO[k]
                        for k, t in teste.items() if k != "dottorando")
    # attrezzature proporzionali a TUTTO il costo-lavoro di ricerca, TA compreso:
    # un tecnico di laboratorio occupa spazio e strumenti come un ricercatore
    attrezz = (herd_pers + supp + ta_ric) * (1 - C.LAMBDA_HE) / C.LAMBDA_HE
    return {"herd_mln": (herd_pers_w + W * supp + W_ta * ta_ric + attrezz) / 1e6,
            "budget_mln": (full_pers_w + W * supp + W_ta * ta_pieno + attrezz) / 1e6,
            "ta_fte": ta}


def _voci(s: Stato, W: float, W_phd: float, costo_prec: float,
          ta_uni_fte: float, ta_epr_fte: float, q_esente_prec: float = 0.0
          ) -> list[Voce]:
    """Il monte stipendi dell'anno spezzato in gruppi OMOGENEI, per il calcolo IRPEF.

    Non e' una vista alternativa della spesa: e' la STESSA spesa di _spesa() e
    _spesa_epr(), riordinata per aliquota invece che per capitolo. Le masse coincidono
    voce per voce - il test di quadratura in main lo verifica contro budget_mln - e
    l'unica differenza e' che qui le attrezzature non ci sono, perche' non sono
    stipendi e non pagano IRPEF.

    Due scomposizioni non ovvie, entrambe imposte dalla progressivita':
      - i DOCENTI si spezzano in PO e PA. Sul costo medio 98.280 l'imposta sarebbe
        sensibilmente piu' bassa della somma delle imposte di un PO a 92.068 e di un
        PA a 55.240 di lordo, perche' l'IRPEF e' convessa;
      - i PRECARI EPR si spezzano in assegnisti (esenti) e contrattisti (tassati) con
        la quota che riproduce ESATTAMENTE il costo medio dell'anno. Cosi' la
        transizione L.79/2022 - che nel modello e' solo un costo che sale - diventa
        anche cio' che e' davvero: una popolazione che entra nell'IRPEF.

    I POSTDOC UNIVERSITARI si spezzano invece per REGIME FISCALE a costo invariato:
    assegni, borse e incarichi di ricerca sono esenti IRPEF ma nel modello costano
    quanto gli altri, perche' COSTO['precari'] e' un valore unico. Separarli qui e'
    l'unico modo di non far pagare l'imposta a chi per legge non la deve senza rompere
    la quadratura con la spesa; il prezzo e' che agli esenti si attribuisce un costo
    piu' alto del vero. Vedi QUOTA_ESENTE_PREC_UNI in config per la stima e per la
    sensitivita', che su questa voce e' larga.

    I RESIDUI (SUPPORTO universitario, OVH_EPR_SUPP) sono masse di stipendi senza
    teste: entrano come teste-equivalenti al costo del TA, che e' la figura piu'
    plausibile per un supporto non nominato. E' un'ipotesi, e conta: nel ramo EPR quel
    residuo vale ~680 mln, cioe' ~17.000 teste equivalenti."""
    W_ta = W if C.TA_SEGUE_W else 1.0
    c_ta = C.COSTO_TA * W_ta
    teste = _teste(s)
    v = [Voce("PO", teste["docente"] * C.QUOTA_PO, C.COSTO_PO * W),
         Voce("PA", teste["docente"] * (1 - C.QUOTA_PO), C.COSTO_PA * W),
         Voce("ric_uni", teste["ric_uni"], C.COSTO["ric_uni"] * W),
         Voce("RTT", teste["RTT"], C.COSTO["RTT"] * W),
         # assegni, borse e incarichi di ricerca: stesso costo degli altri postdoc
         # (il modello ne tiene uno solo), regime fiscale diverso
         Voce("postdoc esenti", teste["precari"] * q_esente_prec,
              C.COSTO["precari"] * W, ESENTE),
         Voce("postdoc", teste["precari"] * (1 - q_esente_prec),
              C.COSTO["precari"] * W),
         # la borsa e' esente IRPEF: di tutta la leva W_PHD non torna un euro di imposta
         Voce("dottorandi", teste["dottorando"], C.COSTO["dottorando"] * W_phd, ESENTE),
         Voce("TA universita", ta_uni_fte / C.ALPHA_TA, c_ta),
         Voce("EPR ruolo", sum(s.epr_ruolo), C.COSTO_EPR_RUOLO * W),
         Voce("TA enti", ta_epr_fte / C.ALPHA_TA, c_ta)]
    # precari EPR: la quota di assegnisti e' quella che, ai due costi ancorati,
    # ricostruisce il costo medio dell'anno. A costo_prec = COSTO_EPR_PREC_TGT
    # (fine rampa) e' zero: gli assegni non esistono piu'.
    passo = C.COSTO_EPR_PREC_TGT - C.COSTO_EPR_ASSEGNO
    q_ass = min(1.0, max(0.0, (C.COSTO_EPR_PREC_TGT - costo_prec) / passo)) if passo else 0.0
    v += [Voce("assegni EPR", sum(s.epr_prec) * q_ass, C.COSTO_EPR_ASSEGNO * W, ESENTE),
          Voce("contratti ric. EPR", sum(s.epr_prec) * (1 - q_ass),
               C.COSTO_EPR_PREC_TGT * W)]
    # residui: masse di stipendi che il modello non sa nominare, quindi nemmeno
    # contare in teste. Al costo del TA per non attribuirgli stipendi da ricercatore.
    massa = W * (C.SUPPORTO or 0.0) * sum(t * C.ALPHA[k] * C.COSTO[k]
                                          for k, t in teste.items() if k != "dottorando")
    massa += W * C.OVH_EPR_SUPP
    if massa > 0 and c_ta > 0:
        v.append(Voce("supporto non nominato", massa / c_ta, c_ta))
    return [x for x in v if x.teste > 0]


def simula(dens_target: float, W: float = 1.0, q_ric: float = 0.0) -> pd.DataFrame:
    _salva_q, C.QUOTA_RIC_UNI = C.QUOTA_RIC_UNI, q_ric
    pd_in0 = _pd_in0()
    # Il flusso PhD è RICAVATO dal fabbisogno a valle dei DUE rami:
    #   - università: quanti postdoc servono per la densità target
    #   - EPR: rimpiazzo a organico costante (il GOVERD è già saturo)
    # e diviso per P1, perchè solo metà dei dottori prosegue.
    uni_in_tgt = dens_target * C.POP_100K / kappa(C.P2_TGT, C.PRECARI_ANNI)
    epr_in_tgt = _epr_in_tgt()
    # PAVIMENTO: il numero di dottorandi non scende mai sotto quello odierno. Se il
    # fabbisogno accademico ne richiede meno, l'eccedenza NON viene tagliata: esce
    # verso destinazioni non accademiche (imprese, PA), che il modello non simula ma
    # ora contabilizza esplicitamente.
    pd_in_tgt = max(pd_in0, (uni_in_tgt + epr_in_tgt) / C.P1)
    # centro della finestra di prepensionamento: quello imposto, oppure - con
    # --prepens-centro-auto - ricavato dal picco dello stesso scenario simulato a
    # leva spenta (una passata in più, non ricorsiva perchè quella passata ha
    # PREPENS_ADES=0 e non rientra mai qui dentro).
    centro = C.PREPENS_CENTRO
    if _prepens_on() and centro is None:
        centro = _centro_finestra(dens_target, W, q_ric)
    s = _init_stato(pd_in0)
    base = _spesa(s, 1.0, 1.0)
    base_e = _spesa_epr(s, 1.0, C.COSTO_EPR_PREC_OGGI)
    base_r = retroflusso(_voci(s, 1.0, 1.0, C.COSTO_EPR_PREC_OGGI,
                               base["ta_fte"], base_e["ta_fte"],
                               C.QUOTA_ESENTE_PREC_UNI))

    righe = []
    for k in range(C.ORIZZONTE + 1):
        anno = C.ANNO0 + k
        # --- prepensionamento: le uscite anticipate avvengono PRIMA di contare lo
        # stock dell'anno, perchè chi aderisce quell'anno non lo presta in servizio.
        # Colpisce le tre coorti di RUOLO (docenti, ricercatori univ., ruolo EPR):
        # RTT e postdoc sono per costruzione lontani dall'età di pensione.
        pesi = _prepens_pesi(anno, centro)
        usc = [_esci_in_anticipo(s.perm, pesi, C.COSTO["docente"]),
               _esci_in_anticipo(s.perm_ric, pesi, C.COSTO["ric_uni"]),
               _esci_in_anticipo(s.epr_ruolo, pesi, C.COSTO_EPR_RUOLO)]
        s.prep_teste = [o + sum(u[0][j] for u in usc)
                        for j, o in enumerate(s.prep_teste)]
        s.prep_costo = [o + sum(u[1][j] for u in usc)
                        for j, o in enumerate(s.prep_costo)]
        prep_anno = sum(sum(u[0]) for u in usc)
        fte = _fte(s)
        fte_tot = sum(fte.values())
        # entrambe le leve salariali sono rampate come le altre
        Wk = _ramp(k, 1.0, W)
        sp = _spesa(s, Wk, _ramp(k, 1.0, C.W_PHD))
        # il costo del precario EPR sale comunque: la L.79/2022 abolisce gli assegni
        cp = _ramp(k, C.COSTO_EPR_PREC_OGGI, C.COSTO_EPR_PREC_TGT)
        spe = _spesa_epr(s, Wk, cp)
        # retroflusso fiscale dell'anno: la parte di monte stipendi che rientra
        rf = retroflusso(_voci(s, Wk, _ramp(k, 1.0, C.W_PHD), cp,
                               sp["ta_fte"], spe["ta_fte"],
                               _ramp(k, C.QUOTA_ESENTE_PREC_UNI,
                                     C.QUOTA_ESENTE_PREC_UNI_TGT)))
        pub = (sp["herd_mln"] + spe["goverd_mln"]) / C.PIL_MLN * 100   # HERD + GOVERD
        # --- flussi dell'anno (servono anche come diagnostica in tabella) ---
        P2 = max(C.P2_MIN, _ramp(k, C.P2_HIST, C.P2_TGT))
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
            "densita": fte_tot / C.pop_100k(anno),
            "pop_mln": C.pop_100k(anno) / 10.0,
            # ... e a popolazione FISSA 2026, per isolare l'effetto organico da quello
            # demografico: la differenza fra le due colonne è tutta demografia.
            "densita_pop2026": fte_tot / C.pop_100k(C.ANNO0),
            # --- personale TA (FTE), esplicito dal 2026 ---
            # densità e quota sono calcolate sul personale R&S TOTALE (ricercatori+TA),
            # che è la grandezza confrontabile con Eurostat; 'densita' resta invece la
            # densità dei soli RICERCATORI, perchè è su quella che sono definiti i target.
            "ta_uni_fte": sp["ta_fte"],
            "ta_epr_fte": spe["ta_fte"],
            "ta_fte": sp["ta_fte"] + spe["ta_fte"],
            "ta_teste": (sp["ta_fte"] + spe["ta_fte"]) / C.ALPHA_TA,
            "quota_ta": ((sp["ta_fte"] + spe["ta_fte"])
                         / (fte_tot + _fte_epr(s) + sp["ta_fte"] + spe["ta_fte"])),
            "densita_ta": (sp["ta_fte"] + spe["ta_fte"]) / C.pop_100k(anno),
            "densita_rs_tot": (fte_tot + _fte_epr(s) + sp["ta_fte"]
                               + spe["ta_fte"]) / C.pop_100k(anno),
            "densita_ric_pub": (fte_tot + _fte_epr(s)) / C.pop_100k(anno),
            "quota_docente": (fte["docente"] + fte["ric_uni"]) / fte_tot,
            # --- carico didattico: studenti per DOCENTE (solo PO/PA) ---
            # due colonne come per la densità: a studenti fermi (isola l'organico) e a
            # studenti che seguono la demografia (proxy grezza, vedi il blocco costanti)
            "prof_teste": sum(s.perm),
            "fte_didattico": _fte_didattico(s),
            "stud_per_doc": (C.STUDENTI_OGGI / _fte_didattico(s)
                             if _fte_didattico(s) > 0 else float("nan")),
            "stud_per_doc_pop": (C.STUDENTI_OGGI * C.pop_100k(anno) / C.pop_100k(C.ANNO0)
                                 / _fte_didattico(s)
                                 if _fte_didattico(s) > 0 else float("nan")),
            "ruolo_teste": sum(s.perm) + sum(s.perm_ric),
            "ric_uni_teste": sum(s.perm_ric),
            "phd_teste": sum(s.phd),
            "postdoc_teste": s.precari,
            "rtt_teste": sum(s.rtt),
            "precari_teste": s.precari + sum(s.rtt),
            # pensionamenti ORDINARI, a ETA_PENS: s.perm[-1] è già al netto di chi
            # è uscito in anticipo quest'anno, quindi le due colonne non si sovrappongono
            "pensionamenti": s.perm[-1] + s.perm_ric[-1],
            "prepensionati": prep_anno,
            # persone che nell'anno prendono la pensione in un anno che avrebbero
            # passato in servizio, e il costo di quelle pensioni. FUORI da HERD,
            # GOVERD e budget: non sono personale di ricerca. Ci sono per non far
            # passare per risparmio netto quello che è uno spostamento di voce.
            "prepens_in_carico": sum(s.prep_teste),
            "pensioni_anticipate_mln": Wk * C.TASSO_SOST * sum(s.prep_costo) / 1e6,
            "W_paghe": Wk,
            "borsa_mese": C.BORSA_OGGI * _ramp(k, 1.0, C.W_PHD),
            "HERD_%PIL": sp["herd_mln"] / C.PIL_MLN * 100,
            "GOVERD_%PIL": spe["goverd_mln"] / C.PIL_MLN * 100,
            "pubblico_%PIL": (sp["budget_mln"] + spe["budget_epr_mln"]) / C.PIL_MLN * 100,
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
            "densita_epr": _fte_epr(s) / C.POP_100K,
            "dHERD_%PIL": (sp["herd_mln"] - base["herd_mln"]) / C.PIL_MLN * 100,
            "dBudget_%PIL": (sp["budget_mln"] - base["budget_mln"]) / C.PIL_MLN * 100,
            "dGOVERD_%PIL": (spe["goverd_mln"] - base_e["goverd_mln"]) / C.PIL_MLN * 100,
            "dBudgetEPR_%PIL": (spe["budget_epr_mln"] - base_e["budget_epr_mln"]) / C.PIL_MLN * 100,
            # livelli ASSOLUTI di spesa, non incrementi: servono al grafico di spesa
            # pubblica, che parte dal valore 2026 invece che da zero.
            "budget_univ_mld": sp["budget_mln"] / 1000,
            "budget_epr_mld": spe["budget_epr_mln"] / 1000,
            # --- RETROFLUSSO FISCALE: la spesa che torna indietro ---------------
            # 'monte_stip' e' la sola parte-stipendi del budget (niente attrezzature),
            # cioe' la base su cui il retroflusso e' definito. Le due colonne di
            # sintesi sono deliberatamente separate: irpef_mln e' la sola imposta
            # erariale, retro_mln e' tutto cio' che rientra nel perimetro pubblico
            # allargato (IRPEF + addizionali locali + contributi + IRAP).
            "monte_stip_mln": rf["costo"] / 1e6,
            "ral_mln": rf["ral"] / 1e6,
            "irpef_mln": rf["irpef"] / 1e6,
            "addizionali_mln": rf["addizionali"] / 1e6,
            "contributi_mln": rf["contributi"] / 1e6,
            "irap_mln": rf["irap"] / 1e6,
            "retro_mln": rf["retro"] / 1e6,
            "irpef_quota_stip": rf["quota_irpef"],
            "retro_quota_stip": rf["quota_retro"],
            "aliq_irpef_media": rf["aliq_media"],
            # gli stessi numeri in DIFFERENZA rispetto al 2026, che e' la lettura di
            # policy: il piano costa dStato_* lordi, ma una parte rientra subito.
            "dIRPEF_mld": (rf["irpef"] - base_r["irpef"]) / 1e9,
            "dRetro_mld": (rf["retro"] - base_r["retro"]) / 1e9,
            "dStato_netto_irpef_mld": ((sp["budget_mln"] - base["budget_mln"]
                                        + spe["budget_epr_mln"] - base_e["budget_epr_mln"])
                                       / 1000 - (rf["irpef"] - base_r["irpef"]) / 1e9),
            "dStato_netto_tot_mld": ((sp["budget_mln"] - base["budget_mln"]
                                      + spe["budget_epr_mln"] - base_e["budget_epr_mln"])
                                     / 1000 - (rf["retro"] - base_r["retro"]) / 1e9),
        })
        # --- avanzamento di un anno ---
        adv, ex = P2 / C.PRECARI_ANNI, (1 - P2) / C.PRECARI_ANNI
        stabil = adv * s.precari                     # postdoc -> RTT
        rtt_out = s.rtt[-1] * C.S_RTT_PERM             # RTT -> ruolo
        epr_stab = s.epr_prec[-1] * C.P2_EPR           # contratto di ricerca -> Madia
        s.phd = [pd_in] + s.phd[:-1]
        s.precari = s.precari + uni_in - stabil - ex * s.precari
        s.rtt = [stabil] + s.rtt[:-1]
        qr = _ramp(k, 0.0, C.QUOTA_RIC_UNI)            # conversione per ricambio
        s.perm = [rtt_out * (1 - qr)] + s.perm[:-1]   # età 67 -> pensione
        s.perm_ric = [rtt_out * qr] + s.perm_ric[:-1]
        s.epr_prec = [epr_in] + s.epr_prec[:-1]
        s.epr_ruolo = [epr_stab] + s.epr_ruolo[:-1]
        # l'ombra previdenziale invecchia con tutti gli altri: chi aveva j anni di
        # anticipo residuo ne ha j-1, e chi ne aveva uno solo compie ETA_PENS ed
        # esce dal conteggio - da li' in poi la sua pensione è una pensione normale.
        # (append-poi-taglia, non taglia-poi-append: a leva spenta la lista è vuota e
        # deve restare vuota, altrimenti si allunga di un elemento all'anno)
        s.prep_teste = (s.prep_teste + [0.0])[1:]
        s.prep_costo = (s.prep_costo + [0.0])[1:]
    C.QUOTA_RIC_UNI = _salva_q
    return pd.DataFrame(righe)
def _berd(pubblico: float) -> float:
    """BERD implicito. IPOTESI, non risultato: il privato avanza verso la sua quota
    del 3% in proporzione all'avanzamento della componente pubblica verso il suo
    punto di riferimento. A pubblico = HERD_RIF+GOVERD_RIF, il 3% è raggiunto."""
    pub0 = C.HERD_OGGI + C.GOVERD_OGGI
    pub_rif = C.HERD_RIF + C.GOVERD_RIF
    berd0 = C.GERD_OGGI - pub0
    berd_tgt = C.GERD_TGT - pub_rif
    if pub_rif <= pub0:
        return berd0
    # SATURA a 1: oltre il punto di ancoraggio l'interpolazione non ha significato,
    # e con una leva di ~4:1 farebbe esplodere il GERD ben oltre il 3%.
    avanz = min(1.0, (pubblico - pub0) / (pub_rif - pub0))
    berd = berd0 + avanz * (berd_tgt - berd0)
    # TETTO: il GERD non supera mai il 3%. Se il pubblico sfora l'ancora, è il
    # privato a non doversi più muovere, non il totale a gonfiarsi.
    return max(0.0, min(berd, C.GERD_TGT - pubblico))
