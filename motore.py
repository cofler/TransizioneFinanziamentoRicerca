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
from regime import (_epr_in_tgt, _ta_epr, _ta_uni, anni_da_associato_tgt,
                    costo_classe, costo_classe_epr, costo_docente,
                    costo_epr_ruolo, epr_in_diretto, epr_in_phd,
                    eta_ruolo_in, kappa, perm_dur, quota_po_coorte,
                    soglie_epr_oggi, soglie_epr_tgt,
                    soglie_ric_uni_oggi, soglie_ric_uni_tgt)

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
    return (_uni_in0() + _epr_in0_phd()) / (C.PHD_OGGI_REALE / C.D_PHD)


def _uni_in0() -> float:
    """Flusso di postdoc UNIVERSITARI oggi, ricavato dallo STOCK osservato invece che
    dal target di densità: un compartimento con permanenza media PRECARI_ANNI e stock
    PRECARI_OGGI riceve PRECARI_OGGI/PRECARI_ANNI ingressi l'anno.

    Prima era il residuo che faceva quadrare la densità sul valore imposto; così il
    modello non poteva essere falsificato dai dati sull'organico. Adesso sì - e infatti
    lo scarto contro Eurostat esce dichiarato invece che riassorbito."""
    return C.PRECARI_OGGI / C.PRECARI_ANNI


def _epr_in0() -> float:
    """Flusso di contratti di ricerca EPR oggi, dallo stock osservato. È il solo canale
    POSTDOC: serve a costruire lo stato iniziale del compartimento precario."""
    return C.EPR_PRECARI_OGGI / C.D_PREC_EPR


def _epr_in0_tot() -> float:
    """Assunzioni EPR TOTALI oggi, i due canali sommati. Il canale diretto è un rimpiazzo
    costante, quindi vale oggi quanto a regime."""
    return _epr_in0() + epr_in_diretto()


def _epr_in0_phd() -> float:
    """Parte del flusso EPR di oggi che pesa sul bacino dei dottorandi. È il termine da
    usare in tutto ciò che ragiona sul DOTTORATO (P1, quota dei rami); _epr_in0_tot()
    resta quello giusto per le teste assunte."""
    return epr_in_phd(_epr_in0())


def _pd_in0() -> float:
    """Flusso PhD in ingresso oggi: alimenta ENTRAMBI i rami, quindi è la somma
    dei due fabbisogni a valle divisa per la sopravvivenza P1 odierna."""
    return (_uni_in0() + _epr_in0_phd()) / _p1_hist()


def _quota_epr0() -> float:
    """Quota EPR implicita nello stato di partenza (vs QUOTA_EPR a regime). Sul bacino
    dei dottorandi, quindi al netto del canale diretto che non lo richiede."""
    return _epr_in0_phd() / (_uni_in0() + _epr_in0_phd())


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


def _ramp(t: int, v0: float, v1: float, ramp_len: int | None = None) -> float:
    r = C.RAMP_PHD if ramp_len is not None else C.RAMP
    return v1 if t >= r else v0 + (v1 - v0) * t / r


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


def _costi_classe(coorte: list[float], soglia: float | None = None,
                  anno: int | None = None) -> list[float]:
    return costo_classe(len(coorte), soglia, anno)


def _esci_in_anticipo(coorte: list[float], pesi: list[float],
                      costo: float | list[float]) -> tuple[list[float], list[float]]:
    """Applica l'adesione per classe alle ultime PREPENS_ANNI classi d'età, IN
    PLACE. Ritorna (teste, ultimo lordo) indicizzati per ANNI DI ANTICIPO:
    l'indice j contiene chi lascia scoperti j+1 anni di servizio. La classe
    ETA_PENS-1 conta UN anno di anticipo, non zero: sarebbe uscita a fine anno,
    ma esce a inizio anno, e quell'anno di servizio non lo presta.

    `costo` puo' essere UNO per tutta la coorte (ricercatori univ., ruolo EPR: figure
    a stipendio unico) oppure una lista allineata alle classi d'eta'. Serve per i
    professori: chi esce in anticipo e' quasi sempre ordinario, ma "quasi sempre" non
    e' "sempre", e quanto lo sia dipende da dove cade la soglia di promozione - cioe'
    da QUOTA_PO_TGT, che e' una leva. Un costo scalare qui reggeva finche' la soglia
    stava lontana dalla finestra; a QUOTA_PO_TGT bassa le due si avvicinano e
    sovrastimerebbe le pensioni."""
    teste = [0.0] * C.PREPENS_ANNI
    per_classe = costo if isinstance(costo, list) else None
    for j in range(1, min(C.PREPENS_ANNI, len(coorte)) + 1):   # j = anni di anticipo
        q = coorte[-j] * pesi[j - 1]
        coorte[-j] -= q
        teste[j - 1] = q
    # oltre len(coorte) le teste sono zero e il costo e' indifferente, ma va comunque
    # definito: indicizzare la lista fuori range sarebbe un IndexError, non uno zero
    c = [(per_classe[-j] if per_classe and j <= len(per_classe) else
          (per_classe[0] if per_classe else costo))
         for j in range(1, C.PREPENS_ANNI + 1)]
    return teste, [t * c[j] for j, t in enumerate(teste)]


def _quota_precaria(s: Stato, rtt_precario: bool = False) -> float:
    """Quota di personale di ricerca a termine, in percentuale. Dottorandi e TA fuori
    da entrambi i lati; vedi il commento alla colonna componente_precaria per il
    perche' di ogni inclusione ed esclusione.

    `rtt_precario` sposta gli RTT dal denominatore-strutturati al numeratore. Le due
    convenzioni convivono perche' sono entrambe difendibili e danno numeri molto
    diversi a fine transizione: pubblicarne una senza dire quale e' il modo piu'
    facile di rendere il dato incomparabile."""
    postdoc = s.precari + sum(s.epr_prec)
    strutt = sum(s.perm) + sum(s.perm_ric) + sum(s.rtt) + sum(s.epr_ruolo)
    if rtt_precario:
        postdoc, strutt = postdoc + sum(s.rtt), strutt - sum(s.rtt)
    tot = postdoc + strutt
    return 100 * postdoc / tot if tot > 0 else float("nan")


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


def simula_senza_blocco(dens_target: float, W: float = 1.0,
                        q_ric: float = 0.0) -> pd.DataFrame:
    salva, C.SCATTI_BLOCCO_ANNI = C.SCATTI_BLOCCO_ANNI, 0
    try:
        return simula(dens_target, W, q_ric)
    finally:
        C.SCATTI_BLOCCO_ANNI = salva


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


def _costi(s: Stato, soglia: float | None = None,
           soglie_ric: tuple[float | None, float | None] = (None, None),
           anno: int | None = None) -> dict[str, float]:
    """I COSTO del modello con 'docente' al costo EFFETTIVO della coorte dell'anno.

    Tutto il resto e' un costo unitario di figura e non dipende dallo stato; i
    professori e i ricercatori universitari (ric_uni) si', perche' sono figure che
    il modello tiene come coorte per eta' e che costano in modo diverso a eta'
    diverse. Passare da qui invece che leggere C.COSTO direttamente e' cio' che
    rende la spesa sensibile all'INVECCHIAMENTO dell'organico, che durante la
    transizione e' un effetto di centinaia di milioni.

    `soglia` e' quella DELL'ANNO: durante la rampa si accorcia da ANNI_DA_ASSOCIATO
    verso anni_da_associato_tgt(). A None si usa la soglia calibrata sul 2026, che e'
    quello che serve a chi conta l'anno base (tutta la calibrazione).

    `soglie_ric` sono le due anzianità III->II->I DELL'ANNO per i ricercatori
    universitari: partono da soglie_ric_uni_oggi() e arrivano a soglie_ric_uni_tgt().
    Al default si usa il mix osservato del 2023."""
    return {**C.COSTO,
            "docente": costo_docente(s.perm, soglia, anno),
            "ric_uni": costo_epr_ruolo(s.perm_ric, *soglie_ric, anno)}


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


def _spesa_epr(s: Stato, W: float, costo_prec: float,
               ta_fte: float | None = None,
               soglie: tuple[float | None, float | None] = (None, None),
               anno: int | None = None) -> dict[str, float]:
    """GOVERD del ramo EPR. Contabilità separata da HERD: settori Eurostat diversi.
    Il TA è ora ESPLICITO e cresce con i ricercatori secondo TA_ELAST; OVH_EPR_SUPP
    resta come residuo assoluto di ciò che il modello non nomina, e OVH_EPR_ATTR
    come infrastruttura (acceleratori, grandi impianti), che davvero non scala.

    `soglie` sono le due anzianità III->II->I DELL'ANNO: durante la rampa si spostano
    da soglie_epr_oggi() verso soglie_epr_tgt(). Al default si usa il mix osservato
    del 2023, che è giusto solo per l'anno 0 - vedi il commento sulla rampa in
     simula()."""
    c_ruolo = costo_epr_ruolo(s.epr_ruolo, *soglie, anno)
    pers = sum(s.epr_ruolo) * c_ruolo + sum(s.epr_prec) * costo_prec
    ric = pers * C.ALPHA_EPR                      # quota-ricerca (alpha unico)
    ta = (_ta_epr(_fte_epr(s)) if ta_fte is None else ta_fte)
    W_ta = C.TA_UPLIFT
    ta_ric, ta_pieno = ta * C.COSTO_TA, ta / C.ALPHA_TA * C.COSTO_TA
    return {"goverd_mln": (W * (ric + C.OVH_EPR_SUPP) + W_ta * ta_ric + C.OVH_EPR_ATTR) / 1e6,
            "budget_epr_mln": (W * (pers + C.OVH_EPR_SUPP) + W_ta * ta_pieno
                               + C.OVH_EPR_ATTR) / 1e6,
            # gemella di "attrezz_mln" nel ramo universitario. Qui e' una COSTANTE:
            # OVH_EPR_ATTR sono i grandi impianti, che per costruzione non scalano
            # col personale (vedi il docstring). La quota-attrezzature del ramo EPR
            # cala quindi da sola man mano che l'organico cresce.
            "attrezz_epr_mln": C.OVH_EPR_ATTR / 1e6,
            "ta_fte": ta}


def _epr_pavimento(s: Stato, W: float, costo_prec: float,
                   minimo_pct: float | None,
                   ta_fte: float | None = None,
                   soglie: tuple[float | None, float | None] = (None, None),
                   anno: int | None = None) -> float:
    """Assunzioni STRAORDINARIE in ruolo che tengono il GOVERD dell'anno sopra il
    pavimento (vedi GOVERD_MIN in config). Zero quando la spesa è già sopra.

    Si risolve in forma chiusa perchè il GOVERD è LINEARE nelle teste di ruolo: ogni
    testa in più porta il proprio costo-ricerca e la quota di TA che TA_ELAST le
    attribuisce, entrambi costanti al margine. La parte fissa del TA e i due overhead
    non si muovono, quindi si semplificano nella differenza.

    Entrano in RUOLO e non in contratto di ricerca perchè la conca è adesso: un precario
    assunto oggi diventa ruolo fra D_PREC_EPR anni, quando la conca si è già richiusa da
    sola. È un'assunzione straordinaria, non un canale di reclutamento."""
    if minimo_pct is None:
        return 0.0
    manca = minimo_pct / 100 * C.PIL_MLN * 1e6 - _spesa_epr(s, W, costo_prec, ta_fte=ta_fte,
                                                             soglie=soglie, anno=anno)["goverd_mln"] * 1e6
    if manca <= 0:
        return 0.0
    W_ta = C.TA_UPLIFT
    ta_marg = C.TA_EPR_OGGI * C.TA_ELAST / (C.EPR_RICERC_OGGI * C.ALPHA_EPR)
    c_ruolo = costo_epr_ruolo(s.epr_ruolo, *soglie, anno)
    per_testa = C.ALPHA_EPR * (W * c_ruolo + W_ta * C.COSTO_TA * ta_marg)
    # guadagno proporzionale: chiude solo una frazione del gap ogni anno, per
    # distribuire la risposta su piú coorti invece di creare un unico lump che
    # si ripresenta 29 anni dopo come eco pensionabile
    return manca * C.EPR_PAV_GAIN / per_testa if per_testa > 0 else 0.0


def _spesa(s: Stato, W: float, W_phd: float = 1.0,
           soglia: float | None = None,
           soglie_ric: tuple[float | None, float | None] = (None, None),
           ta_fte: float | None = None,
           anno: int | None = None) -> dict[str, float]:
    teste = _teste(s)
    # il costo-ricerca usa ALPHA anche per i dottorandi esclusi dal conteggio FTE:
    # la borsa è spesa R&S comunque la si conti nel personale.
    # due leve distinte: W sul personale, W_phd sulle borse di dottorato.
    lev = {k: (W_phd if k == "dottorando" else W) for k in teste}
    cst = _costi(s, soglia, soglie_ric, anno)
    herd_pers = sum(t * C.ALPHA[k] * cst[k] for k, t in teste.items())
    herd_pers_w = sum(t * C.ALPHA[k] * cst[k] * lev[k] for k, t in teste.items())
    full_pers_w = sum(t * cst[k] * lev[k] for k, t in teste.items())
    # --- personale tecnico-amministrativo, ESPLICITO in FTE ---
    # Il costo-ricerca è FTE*COSTO_TA (l'FTE incorpora già la quota-ricerca); il monte
    # stipendi PIENO, che va nel budget e non in HERD, è (FTE/ALPHA_TA)*COSTO_TA.
    # È la stessa distinzione che il modello fa fra herd_pers e full_pers per i
    # ricercatori, e che il vecchio SUPPORTO non faceva: usava l'importo alpha-pesato
    # in entrambi, sottostimando il budget di un fattore 1/alpha.
    ta = _ta_uni(_fte_ric_uni(s)) if ta_fte is None else ta_fte
    W_ta = C.TA_UPLIFT
    ta_ric, ta_pieno = ta * C.COSTO_TA, ta / C.ALPHA_TA * C.COSTO_TA
    q_supp = C.SUPPORTO or 0.0
    supp = q_supp * sum(t * C.ALPHA[k] * cst[k]
                        for k, t in teste.items() if k != "dottorando")
    attrezz = (herd_pers + supp + ta_ric) * (1 - C.LAMBDA_HE) / C.LAMBDA_HE
    return {"herd_mln": (herd_pers_w + W * supp + W_ta * ta_ric + attrezz) / 1e6,
            "budget_mln": (full_pers_w + W * supp + W_ta * ta_pieno + attrezz) / 1e6,
            # la sola voce ATTREZZATURE, gia' dentro le due masse qui sopra e
            # riportata a parte perche' e' la base su cui si posa l'inviluppo di
            # piano_attrezzature(): la quota-attrezzature del totale si misura da qui
            "attrezz_mln": attrezz / 1e6,
            "ta_fte": ta}


def _voci(s: Stato, W: float, W_phd: float, costo_prec: float,
          ta_uni_fte: float, ta_epr_fte: float, q_esente_prec: float = 0.0,
          soglia: float | None = None,
          soglie_epr: tuple[float | None, float | None] = (None, None),
          soglie_ric: tuple[float | None, float | None] = (None, None),
          anno: int | None = None) -> list[Voce]:
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
    W_ta = C.TA_UPLIFT
    c_ta = C.COSTO_TA * W_ta
    teste = _teste(s)
    # I PROFESSORI ENTRANO UNA VOCE PER CLASSE D'ETA', non due per fascia. La regola (2)
    # di irpef.py chiede gruppi a stipendio OMOGENEO, e con le scale stipendiali PO e PA
    # non lo sono piu': dentro gli associati si va da 56.786 a oltre 100.000 di lordo,
    # che su un'imposta progressiva non e' un dettaglio. Spezzare per classe e' quindi
    # la stessa scelta di prima portata fino in fondo - e non costa nulla, perche' la
    # coorte per eta' il modello ce l'ha gia'.
    # Le classi VUOTE vengono scartate in coda, quindi durante la transizione le voci
    # sono meno delle classi.
    v = [Voce(f"prof. cl.{i}", t, c * W)
         for i, (t, c) in enumerate(zip(s.perm, _costi_classe(s.perm, soglia, anno)))]
    v += [Voce(f"ric. cl.{i}", t, c * W)
          for i, (t, c) in enumerate(zip(s.perm_ric,
              costo_classe_epr(len(s.perm_ric), *soglie_ric, anno)))]
    v += [Voce("RTT", teste["RTT"], C.COSTO["RTT"] * W),
         # DUE FIGURE DISTINTE, non piu' un costo unico con due regimi fiscali:
         # l'incarico di ricerca (entro 6 anni dalla laurea magistrale) costa meno ED e'
         # esente; il contratto di ricerca costa il pieno ed e' tassato. La media pesata
         # dei due e' COSTO['precari'], quindi la quadratura con _spesa() regge.
         Voce("postdoc incarico di ricerca", teste["precari"] * q_esente_prec,
              C.COSTO_PREC_INCARICO * W, ESENTE),
         Voce("postdoc contratto di ricerca", teste["precari"] * (1 - q_esente_prec),
              C.COSTO_PREC_CONTRATTO * W),
         # la borsa e' esente IRPEF: di tutta la leva W_PHD non torna un euro di imposta
         Voce("dottorandi", teste["dottorando"], C.COSTO["dottorando"] * W_phd, ESENTE),
         Voce("TA universita", ta_uni_fte / C.ALPHA_TA, c_ta),
         Voce("EPR ruolo", sum(s.epr_ruolo),
               costo_epr_ruolo(s.epr_ruolo, *soglie_epr, anno) * W),
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
    # stessi costi di _spesa(), soglia compresa: se qui restasse C.COSTO e li' no, le
    # due masse divergerebbero e la quadratura col budget salterebbe. Oggi non si vede
    # solo perche' SUPPORTO si calibra a zero - cioe' e' un bug in attesa di un dato.
    cst = _costi(s, soglia, soglie_ric, anno)
    massa = W * (C.SUPPORTO or 0.0) * sum(t * C.ALPHA[k] * cst[k]
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
    #   - EPR: quanti contratti di ricerca servono per portare il GOVERD a GOVERD_TGT
    #     (il canale diretto è un rimpiazzo costante, non entra nel target)
    # e diviso per P1, perchè solo metà dei dottori prosegue.
    # Entrambi i rami hanno quindi un obiettivo, non un vincolo di organico fermo: il
    # ramo enti è ancorato alla SPESA (0,22% PIL) e l'organico ne è la conseguenza.
    # La leva paghe entra nel conto perchè a GOVERD fisso paghe più alte comprano
    # meno teste - la stessa frontiera prezzo/quantità dell'HERD.
    uni_in_tgt = dens_target * C.POP_100K / kappa(C.P2_TGT, C.PRECARI_ANNI)
    epr_in_tgt = _epr_in_tgt(W)
    # PAVIMENTO: il numero di dottorandi non scende mai sotto quello odierno. Se il
    # fabbisogno accademico ne richiede meno, l'eccedenza NON viene tagliata: esce
    # verso destinazioni non accademiche (imprese, PA), che il modello non simula ma
    # ora contabilizza esplicitamente.
    # sul bacino dei dottorandi il ramo EPR pesa per epr_in_phd(): la parte del canale
    # diretto reclutata per concorso da LAUREA assume comunque, ma da un mercato del
    # lavoro che il modello non simula, e non va chiesta al dottorato.
    pd_in_tgt = max(pd_in0, (uni_in_tgt + epr_in_phd(epr_in_tgt)) / C.P1)
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
    goerd_max_storico = 0.0   # massimo GOVERD raggiunto (senza pavimento)
    for k in range(C.ORIZZONTE + 1):
        anno = C.ANNO0 + k
        # SOGLIA PA->PO dell'anno: parte dal valore calibrato sul 2026 (che riproduce
        # il 39% osservato) e si muove fino a quello che a regime dà QUOTA_PO_TGT -
        # si accorcia se il target è più alto di oggi, si allunga se è più basso.
        # È una leva come W o P2, quindi usa la stessa rampa: nell'anno 0 vale il dato,
        # dall'anno RAMP in poi vale l'obiettivo. Rampare la SOGLIA e non la quota è
        # l'unico modo corretto - la quota è uno stock, non si impone, si aspetta che
        # la coorte ci arrivi. Va calcolata QUI, prima del prepensionamento, che ne ha
        # bisogno per sapere chi sta uscendo.
        sgl = _ramp(k, C.ANNI_DA_ASSOCIATO, anni_da_associato_tgt())
        # SOGLIE III->II->I del ramo EPR, per lo stesso motivo e con la stessa rampa:
        # partono dal mix OSSERVATO (QUOTA_EPR_II/I, 19%/10%) e arrivano a quello di
        # regime (QUOTA_EPR_{II,I}_TGT, 40%/40%). Senza questa riga il motore paga il
        # ruolo EPR al mix del 2023 anche nel 2080 - 69.803 EUR/testa invece dei 75.107
        # su cui epr_in_iso_goverd() ha calcolato il fabbisogno - e il GOVERD di regime
        # si fermava a 0,243% invece di centrare GOVERD_TGT. Le due soglie vanno rampate
        # SEPARATAMENTE e non come una quota: la quota è uno stock, ci arriva la coorte.
        sgl_epr = tuple(_ramp(k, o, t) for o, t in zip(soglie_epr_oggi(),
                                                       soglie_epr_tgt()))
        sgl_ric = tuple(_ramp(k, o, t) for o, t in zip(soglie_ric_uni_oggi(),
                                                        soglie_ric_uni_tgt()))
        # --- prepensionamento: le uscite anticipate avvengono PRIMA di contare lo
        # stock dell'anno, perchè chi aderisce quell'anno non lo presta in servizio.
        # Colpisce le tre coorti di RUOLO (docenti, ricercatori univ., ruolo EPR):
        # RTT e postdoc sono per costruzione lontani dall'età di pensione.
        pesi = _prepens_pesi(anno, centro)
        # ai professori il costo va passato CLASSE PER CLASSE: chi esce in anticipo
        # sono le classi più anziane, quindi quasi tutti ordinari, ma quanto "quasi"
        # dipende da dove la leva ha portato la soglia. A QUOTA_PO_TGT alta la soglia
        # sta lontana dalla finestra e sono tutti PO; a QUOTA_PO_TGT bassa le due si
        # avvicinano e la finestra inizia a pescare anche fra gli associati.
        usc = [_esci_in_anticipo(s.perm, pesi, _costi_classe(s.perm, sgl, anno)),
               _esci_in_anticipo(s.perm_ric, pesi,
                                 costo_classe_epr(len(s.perm_ric), *sgl_ric, anno)),
               _esci_in_anticipo(s.epr_ruolo, pesi,
                                  costo_classe_epr(len(s.epr_ruolo), *sgl_epr, anno))]
        s.prep_teste = [o + sum(u[0][j] for u in usc)
                        for j, o in enumerate(s.prep_teste)]
        s.prep_costo = [o + sum(u[1][j] for u in usc)
                        for j, o in enumerate(s.prep_costo)]
        prep_anno = sum(sum(u[0]) for u in usc)
        # entrambe le leve salariali sono rampate come le altre
        Wk = _ramp(k, 1.0, W)
        # il costo del precario EPR sale comunque: la L.79/2022 abolisce gli assegni
        cp = _ramp(k, C.COSTO_EPR_PREC_OGGI, C.COSTO_EPR_PREC_TGT)
        # GOVERD "naturale" (senza il pavimento): serve a decidere se il pavimento
        # scatta, perchè il vincolo è "una volta raggiunto lo 0,22% non scende più",
        # non "parte dallo 0,21 del 2026".
        goerd_nat = _spesa_epr(s, Wk, cp, soglie=sgl_epr, anno=anno)["goverd_mln"] / C.PIL_MLN * 100
        goerd_max_storico = max(goerd_max_storico, goerd_nat)
        minimo = (C.GOVERD_MIN if goerd_max_storico >= C.GOVERD_MIN
                  else None) if C.GOVERD_MIN is not None else None
        # TA "grezzo" (senza cap): serve per calcolare il fattore di scala se il
        # tetto TA_CAP è superato. Calcolato ORA, prima del pavimento GOVERD, perchè
        # il pavimento aggiunge ruolo EPR e altera il conto.
        ta_uni_raw = _ta_uni(_fte_ric_uni(s))
        ta_epr_raw = _ta_epr(_fte_epr(s))
        ta_raw_tot = ta_uni_raw + ta_epr_raw
        if C.TA_CAP is not None and ta_raw_tot > C.TA_CAP:
            ta_scale = C.TA_CAP / ta_raw_tot
        else:
            ta_scale = 1.0
        # PAVIMENTO sul GOVERD: se la spesa del ramo enti cadrebbe sotto il livello
        # dello 0,22% (e il livello è già stato raggiunto almeno una volta) si assume
        # in più, in ruolo e subito. Va fatto DOPO il prepensionamento (che toglie
        # teste, quindi può essere lui a scavare la conca) e PRIMA di contare la
        # spesa, perchè chi è assunto a inizio anno quell'anno lo presta.
        epr_extra = _epr_pavimento(s, Wk, cp, minimo,
                                   ta_fte=ta_epr_raw * ta_scale, soglie=sgl_epr,
                                   anno=anno)
        s.epr_ruolo[0] += epr_extra
        if epr_extra > 0:
            ta_epr_raw = _ta_epr(_fte_epr(s))
            ta_raw_tot = ta_uni_raw + ta_epr_raw
            if C.TA_CAP is not None and ta_raw_tot > C.TA_CAP:
                ta_scale = C.TA_CAP / ta_raw_tot
        fte = _fte(s)
        fte_tot = sum(fte.values())
        sp = _spesa(s, Wk, _ramp(k, 1.0, C.W_PHD, C.RAMP_PHD), sgl,
                    soglie_ric=sgl_ric, ta_fte=ta_uni_raw * ta_scale, anno=anno)
        spe = _spesa_epr(s, Wk, cp,
                         ta_fte=ta_epr_raw * ta_scale, soglie=sgl_epr, anno=anno)
        # retroflusso fiscale dell'anno: la parte di monte stipendi che rientra
        rf = retroflusso(_voci(s, Wk, _ramp(k, 1.0, C.W_PHD, C.RAMP_PHD), cp,
                               sp["ta_fte"], spe["ta_fte"],
                               _ramp(k, C.QUOTA_ESENTE_PREC_UNI,
                                     C.QUOTA_ESENTE_PREC_UNI_TGT), sgl,
                               soglie_epr=sgl_epr, soglie_ric=sgl_ric, anno=anno))
        pub = (sp["herd_mln"] + spe["goverd_mln"]) / C.PIL_MLN * 100   # HERD + GOVERD
        # --- flussi dell'anno (servono anche come diagnostica in tabella) ---
        P2 = max(C.P2_MIN, _ramp(k, C.P2_HIST, C.P2_TGT))
        pd_in = _ramp(k, pd_in0, pd_in_tgt)
        uni_in_k = _ramp(k, _uni_in0(), uni_in_tgt)
        # RAMPA solo il canale postdoc: il diretto è rimpiazzo di uno stock fermo,
        # quindi vale lo stesso numero in ogni anno della transizione.
        epr_pd_k = _ramp(k, _epr_in0(), epr_in_tgt)
        epr_dir_k = epr_in_diretto()
        # Il ramo EPR compete per i dottori solo con la parte che il dottorato lo
        # richiede; il resto del canale diretto (concorsi da laurea) NON entra in
        # 'serve' e soprattutto NON viene razionato quando i dottori scarseggiano:
        # pesca da un altro mercato, quindi assume anche se il bacino è vuoto.
        epr_phd_k = epr_pd_k + epr_dir_k * C.PHD_NEL_DIRETTO_EPR
        serve, escono = uni_in_k + epr_phd_k, s.phd[-1]
        prosegue = min(serve, escono)
        scala = prosegue / serve if serve > 0 else 0.0
        uni_in = uni_in_k * scala
        # i tre pezzi subiscono razionamenti diversi: solo chi chiede il dottorato viene
        # scalato, quindi la composizione NON si ricava applicando le quote al totale.
        epr_in_prec = epr_pd_k * scala                              # -> contratto ric.
        epr_in_dir = epr_dir_k * (C.PHD_NEL_DIRETTO_EPR * scala     # -> ruolo, subito
                                  + (1 - C.PHD_NEL_DIRETTO_EPR))
        epr_in = epr_in_prec + epr_in_dir
        p1_eff = prosegue / escono if escono > 0 else 0.0
        # ingressi in TENURE TRACK dell'anno: postdoc universitari che passano a RTT, e
        # precari EPR che passano al ruolo (la Madia è l'analogo EPR della tenure track).
        # Calcolati qui e non solo nell'avanzamento in fondo al ciclo, perchè entrano
        # nelle quote di sbocco che il ciclo scrive in tabella.
        adv, ex = P2 / C.PRECARI_ANNI, (1 - P2) / C.PRECARI_ANNI
        stabil = adv * s.precari                       # postdoc -> RTT
        # il ruolo EPR si riempie da DUE canali: la Madia a valle del contratto di
        # ricerca, e il concorso diretto che salta il postdoc (epr_in_dir, già calcolato
        # coi flussi qui sopra perchè entra nelle quote di sbocco in tabella).
        epr_stab = s.epr_prec[-1] * C.P2_EPR + epr_in_dir
        righe.append({
            "phd_prosegue": prosegue,
            "phd_fuori_accademia": max(0.0, escono - prosegue),
            "P1_effettivo": p1_eff,
            # --- SBOCCHI, come quote del flusso di dottori dell'anno ---
            # Stesso denominatore per entrambe: i dottori che escono dal dottorato
            # quell'anno. Al numeratore i due sbocchi dentro la ricerca pubblica:
            #   - postdoc: chi entra nel precariato post-dottorale (postdoc universitari
            #     + contratti di ricerca EPR). Coincide con P1_effettivo, ed è il
            #     complemento a 1 della quota che esce dall'accademia.
            #   - RTT: chi entra in tenure track (RTT universitari + Madia EPR).
            # ATTENZIONE: sono rapporti fra flussi CONTEMPORANEI, non il destino di una
            # coorte. Chi entra in RTT nell'anno t è un postdoc, quindi un dottore di
            # qualche anno prima: la quota dice "quanti posti di tenure track si aprono
            # per ogni dottore che il sistema produce oggi", non "che fine fa questa
            # coorte". A regime, dove i flussi sono stazionari, le due letture
            # convergono e la quota RTT tende a P1xP2.
            "quota_phd_postdoc": prosegue / escono if escono > 0 else float("nan"),
            "quota_phd_rtt": ((stabil + epr_stab) / escono if escono > 0
                              else float("nan")),
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
            # ordinari e associati come SERIE del modello, non come ripartizione fatta
            # a valle: la quota si muove con l'età della coorte, quindi chi legge il
            # CSV o disegna lo stack deve prenderla da qui e non rifarla con QUOTA_PO.
            "po_teste": sum(s.perm) * quota_po_coorte(s.perm, sgl),
            "pa_teste": sum(s.perm) * (1 - quota_po_coorte(s.perm, sgl)),
            "quota_po": quota_po_coorte(s.perm, sgl),
            "costo_docente": costo_docente(s.perm, sgl),
            "anni_da_associato": sgl,
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
            # COMPONENTE PRECARIA: quota di postdoc sul personale di ricerca, in %.
            #
            #   numeratore   postdoc UNIVERSITARI + postdoc EPR
            #   denominatore gli stessi PIU' gli strutturati, cioe' ruolo universitario
            #                (PO/PA + ricercatori), RTT e ruolo EPR
            #
            # E' una QUOTA SU UN TOTALE, non un rapporto fra due popolazioni: sta per
            # costruzione fra 0 e 100 e si legge come "su 100 persone che fanno ricerca,
            # quante sono a termine". Entrambi i rami contabili sono dentro da entrambi
            # i lati - postdoc EPR nel numeratore, ruolo EPR nel denominatore - perche'
            # la precarieta' non e' un fenomeno del solo ramo universitario e spezzarla
            # per settore la renderebbe incomparabile col totale.
            #
            # I DOTTORANDI SONO FUORI da entrambi i lati. Non sono personale ma
            # formazione: contarli fra i precari gonfierebbe l'indicatore con una
            # popolazione che e' precaria per definizione e deve esserlo, contarli fra
            # gli strutturati e' assurdo. Non stanno da nessuna delle due parti.
            #
            # GLI RTT STANNO FRA GLI STRUTTURATI. E' una convenzione e va detta, perche'
            # nel dibattito italiano l'RTT viene spesso contato fra i precari: e' pur
            # sempre un contratto a termine. Qui sta di la' perche' e' una TENURE TRACK
            # - nel modello S_RTT_PERM=1, chi ci entra arriva al ruolo - e metterlo fra
            # i precari misurerebbe la durata della carriera prima del ruolo invece
            # della precarieta' senza sbocco.
            # Chi vuole l'altra convenzione sposti sum(s.rtt) dal denominatore al
            # numeratore. La differenza NON e' costante: e' modesta oggi e grossa a
            # regime, perche' il piano porta gli RTT da 5.786 a 22.236 teste. Vedi la
            # colonna componente_precaria_rtt, che tiene l'altra convenzione a fianco
            # invece di lasciarla da ricalcolare a mano.
            #
            # Il TA resta FUORI da entrambi: non e' personale di ricerca, sta in un
            # perimetro suo (vedi quota_ta), e infilarlo nel denominatore diluirebbe
            # l'indicatore con una popolazione che non ha nulla a che vedere con la
            # precarieta' della carriera accademica.
            "componente_precaria": _quota_precaria(s, rtt_precario=False),
            "componente_precaria_rtt": _quota_precaria(s, rtt_precario=True),
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
            "borsa_mese": C.BORSA_OGGI * _ramp(k, 1.0, C.W_PHD, C.RAMP_PHD),
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
            # assunzioni EPR STRAORDINARIE dell'anno, quelle che il pavimento sul GOVERD
            # impone in più: >0 solo mentre la coorte del 2026 va in pensione.
            "epr_extra_pavimento": epr_extra,
            "densita_epr": _fte_epr(s) / C.POP_100K,
            "dHERD_%PIL": (sp["herd_mln"] - base["herd_mln"]) / C.PIL_MLN * 100,
            "dBudget_%PIL": (sp["budget_mln"] - base["budget_mln"]) / C.PIL_MLN * 100,
            "dGOVERD_%PIL": (spe["goverd_mln"] - base_e["goverd_mln"]) / C.PIL_MLN * 100,
            "dBudgetEPR_%PIL": (spe["budget_epr_mln"] - base_e["budget_epr_mln"]) / C.PIL_MLN * 100,
            # livelli ASSOLUTI di spesa, non incrementi: servono al grafico di spesa
            # pubblica, che parte dal valore 2026 invece che da zero.
            "budget_univ_mld": sp["budget_mln"] / 1000,
            "budget_epr_mld": spe["budget_epr_mln"] / 1000,
            # la voce ATTREZZATURE dei due rami, gia' compresa nei due budget qui
            # sopra. In assoluto e non in differenza dal 2026 perche' serve a fare
            # una QUOTA, e una quota vuole il livello a numeratore e a denominatore.
            "attrezz_univ_mld": sp["attrezz_mln"] / 1000,
            "attrezz_epr_mld": spe["attrezz_epr_mln"] / 1000,
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
        # (adv, ex, stabil, epr_stab sono già stati calcolati sopra, coi flussi)
        rtt_out = s.rtt[-1] * C.S_RTT_PERM             # RTT -> ruolo
        s.phd = [pd_in] + s.phd[:-1]
        s.precari = s.precari + uni_in - stabil - ex * s.precari
        s.rtt = [stabil] + s.rtt[:-1]
        qr = _ramp(k, 0.0, C.QUOTA_RIC_UNI)            # conversione per ricambio
        s.perm = [rtt_out * (1 - qr)] + s.perm[:-1]   # età 67 -> pensione
        s.perm_ric = [rtt_out * qr] + s.perm_ric[:-1]
        s.epr_prec = [epr_in_prec] + s.epr_prec[:-1]
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


def piano_attrezzature(df: pd.DataFrame) -> pd.DataFrame:
    """Aggiunge al risultato di simula() l'INVILUPPO di spesa e la voce attrezzature
    che lo riempie. Vedi il blocco PIANO ATTREZZATURE in config per il perche', e
    ATTREZZ_INVILUPPO per l'interruttore che la rende una funzione identita'.

    Sta QUI e non in grafici.py perche' non e' un modo di disegnare la spesa: e' una
    decisione di politica di bilancio - "quando l'organico costa meno, quei soldi
    restano alla ricerca e vanno in attrezzature" - e come tale finisce nei CSV, non
    solo nei PNG.

    ATTENZIONE: questa funzione RISCRIVE le colonne di spesa che simula() ha appena
    prodotto - HERD_%PIL, GOVERD_%PIL, budget_*_mld, dStato_*_mld e tutto cio' che ne
    discende - perche' il supplemento e' spesa R&S a tutti gli effetti. Le versioni
    "nude", cioe' il solo fabbisogno che l'organico impone, restano disponibili come
    dStato_univ_pers_mld / dStato_epr_pers_mld. Chi legge un CSV deve sapere che le
    colonne di spesa sono POST-inviluppo: non c'e' nessun punto, a valle di main(), in
    cui si vedano ancora quelle di simula().

    E' un POST-PROCESSING e non una colonna di simula() perche' guarda la traiettoria
    INTERA: il primo picco e il livello del tratto piatto sono massimi su finestre di
    anni, e dentro il ciclo, all'anno k, gli anni successivi non esistono ancora.
    Conseguenza da tenere presente: l'inviluppo dipende dall'ORIZZONTE. Con un
    orizzonte piu' corto del 2055 il tratto piatto non esiste e la funzione non
    aggiunge nulla.

    La ricostruzione dell'inviluppo, nell'ordine:
      1. p1 = massimo della spesa totale fino a ATTREZZ_PICCO_1, e l'anno in cui cade
         (il picco VERO, che nei tre scenari sta fra il 2034 e il 2040);
      2. p2 = massimo da ATTREZZ_PICCO_2 in poi. E' il massimo e non il valore
         dell'anno di ancoraggio proprio perche' il picco vero cade uno o quattro anni
         dopo: ancorarsi al 2055 lascerebbe il 2056 sopra l'inviluppo, cioe' una voce
         attrezzature NEGATIVA;
      3. l'inviluppo e' la spesa stessa prima del primo picco, poi piatto a p1 fino a
         ATTREZZ_PICCO_1, poi la retta p1->p2, poi piatto a p2;
      4. il massimo elemento per elemento con la spesa vera. Con gli ancoraggi di
         default non morde in nessuno dei tre scenari - la retta passa sempre sopra la
         curva - ma e' cio' che garantisce che la voce attrezzature non possa mai
         uscire negativa se qualcuno sposta gli ancoraggi o le altre leve.
    """
    # interruttore spento: si restituisce il DataFrame di simula() INTATTO, senza
    # nemmeno le colonne a zero. E' voluto: tabelle e grafici riconoscono l'assenza
    # delle colonne e tornano da soli al disegno di prima (due fasce nel grafico di
    # spesa, nessun pannello di quota nel trend), mentre delle colonne a zero
    # dovrebbero essere riconosciute una per una da ogni consumatore.
    if not C.ATTREZZ_INVILUPPO:
        return df
    tot = (df["dStato_univ_mld"] + df["dStato_epr_mld"]).to_numpy()
    anno = df["anno"].to_numpy()
    a1, a2 = C.ATTREZZ_PICCO_1, C.ATTREZZ_PICCO_2
    pre, post = anno <= a1, anno >= a2
    if not pre.any() or not post.any():
        # orizzonte troppo corto perche' l'inviluppo abbia senso: nessun supplemento,
        # e le colonne ci sono lo stesso cosi' i consumatori a valle non si rompono
        extra = np.zeros(len(anno))
    else:
        p1, p2 = tot[pre].max(), tot[post].max()
        anno_p1 = anno[pre][int(np.argmax(tot[pre]))]
        inv = np.where(anno < anno_p1, tot,
                       np.where(anno <= a1, p1,
                                np.where(anno >= a2, p2,
                                         p1 + (p2 - p1) * (anno - a1) / (a2 - a1))))
        extra = np.maximum(inv, tot) - tot
    df = df.copy()
    df["attrezz_extra_mld"] = extra
    # --- il supplemento e' SPESA R&S, quindi entra in HERD e in GOVERD ---------
    # Le attrezzature che il modello gia' calcolava stanno dentro i due aggregati
    # (il 13% dell'HERD che LAMBDA_HE lascia agli strumenti, e OVH_EPR_ATTR dentro il
    # GOVERD): tenere il supplemento fuori vorrebbe dire comprare strumenti che per
    # Frascati sono R&S e non contarli come R&S. Da qui in poi TUTTE le colonne di
    # spesa lo comprendono - HERD, GOVERD, i due budget, il fabbisogno per ramo.
    #
    # LA RIPARTIZIONE FRA I DUE RAMI E' UNA CONVENZIONE, e va detto: l'inviluppo e'
    # una proprieta' del TOTALE - e' il totale a dover stare piatto - quindi non
    # esiste un ramo a cui il supplemento appartenga. Si distribuisce allora in
    # proporzione all'aggregato R&S di ciascun ramo NELL'ANNO, cioe' si lascia
    # invariato il mix HERD/GOVERD: e' la scelta neutra, l'unica che non aggiunge una
    # seconda decisione di politica dentro la prima. Alternativa scartata: ripartire
    # in proporzione a quanto ciascun ramo ha lasciato cadere. E' piu' aderente al
    # racconto ("la spesa resta dov'era") ma non e' definita ovunque - nel tratto in
    # salita fra i due ancoraggi il ramo universitario non cala affatto, e tutto il
    # supplemento finirebbe sull'EPR, in misura molto superiore a cio' che l'EPR ha
    # liberato.
    herd_mln = df["HERD_%PIL"] / 100 * C.PIL_MLN
    gov_mln = df["GOVERD_%PIL"] / 100 * C.PIL_MLN
    q_univ = (herd_mln / (herd_mln + gov_mln)).to_numpy()
    ex_u, ex_e = extra * q_univ, extra * (1 - q_univ)
    df["attrezz_extra_univ_mld"], df["attrezz_extra_epr_mld"] = ex_u, ex_e
    # le due fasce al NETTO del supplemento, cioe' il fabbisogno che l'organico impone
    # e basta. Servono al grafico di spesa: li' le tre fasce si sommano al totale, e
    # se le prime due lo comprendessero gia' la terza lo conterebbe due volte.
    df["dStato_univ_pers_mld"] = df["dStato_univ_mld"]
    df["dStato_epr_pers_mld"] = df["dStato_epr_mld"]
    pct = 1000 / C.PIL_MLN * 100          # da mld di spesa a punti di % PIL
    for ramo, q in (("univ", ex_u), ("epr", ex_e)):
        df[f"dStato_{ramo}_mld"] += q
        df[f"budget_{ramo}_mld"] += q
        df[f"attrezz_{ramo}_mld"] += q
    df["HERD_%PIL"] += ex_u * pct
    df["GOVERD_%PIL"] += ex_e * pct
    df["dHERD_%PIL"] += ex_u * pct
    df["dGOVERD_%PIL"] += ex_e * pct
    df["dBudget_%PIL"] += ex_u * pct
    df["dBudgetEPR_%PIL"] += ex_e * pct
    df["spesa_RS_mln"] += extra * 1000
    df["pubblico_%PIL"] += extra * pct
    df["RS_pubblica_%PIL"] += extra * pct
    # il BERD e' una FUNZIONE della spesa pubblica (vedi _berd): se il pubblico sale,
    # va rifatto, non lasciato al valore che aveva prima dell'inviluppo. Il GERD ne
    # discende. Sono le uniche due colonne che si RICALCOLANO invece di sommarsi.
    df["BERD_%PIL"] = df["RS_pubblica_%PIL"].map(_berd)
    df["GERD_%PIL"] = df["RS_pubblica_%PIL"] + df["BERD_%PIL"]
    # le attrezzature non pagano IRPEF: il supplemento entra nel costo netto INTERO,
    # a differenza di un euro di stipendio, di cui una parte rientra
    df["dStato_netto_irpef_mld"] += extra
    df["dStato_netto_tot_mld"] += extra
    # il totale a carico dello Stato: e' l'inviluppo, ed e' la curva che il grafico
    # di spesa disegna in cima allo stack
    df["dStato_tot_mld"] = df["dStato_univ_mld"] + df["dStato_epr_mld"]
    # attrezzature TOTALI e spesa totale in valore ASSOLUTO: le due colonne di ramo
    # comprendono gia' il supplemento, quindi qui non si somma piu' nulla
    df["attrezz_tot_mld"] = df["attrezz_univ_mld"] + df["attrezz_epr_mld"]
    df["spesa_tot_mld"] = df["budget_univ_mld"] + df["budget_epr_mld"]
    # LA colonna del pannello di trend: quanta parte della spesa pubblica per la
    # ricerca e' attrezzature invece che stipendi.
    df["quota_attrezz"] = df["attrezz_tot_mld"] / df["spesa_tot_mld"]
    return df


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
