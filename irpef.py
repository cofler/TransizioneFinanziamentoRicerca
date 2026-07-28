"""Retroflusso fiscale: quanta parte della spesa in stipendi torna allo Stato.

La spesa che il modello costruisce fra il 2026 e il 2080 e' quasi tutta monte
stipendi. Uno stipendio pubblico e' pero' in parte una PARTITA DI GIRO: lo Stato lo
eroga e se ne riprende subito una quota come IRPEF, addizionali, contributi
previdenziali e IRAP. Questo modulo ricostruisce quella quota, figura per figura,
partendo dai costi lordo-ente che il motore gia' calcola.

TRE REGOLE, e sono tutte e tre necessarie perche' il numero abbia senso:

  (1) SI PARTE DALLA BUSTA PAGA, NON DALLA SPESA. I COSTO_* del modello sono costo
      per il datore di lavoro: contengono gia' contributi e IRAP. L'IRPEF si calcola
      sulla retribuzione lorda, che e' il costo diviso GROSS_UP_DIP.

  (2) SI CALCOLA PRO CAPITE, MAI SULLE MASSE. L'IRPEF e' progressiva e convessa:
      l'imposta della media e' SEMPRE minore della media delle imposte. Applicare gli
      scaglioni al monte stipendi complessivo, o anche solo al costo medio di una
      figura composita come 'docente' (che mescola PO a 92.068 e PA a 55.240 di
      lordo), sottostima il gettito. Per questo il motore passa qui una lista di VOCI
      omogenee - N teste allo STESSO stipendio - e non un totale.

  (3) L'ESENZIONE E' UNA CATEGORIA, NON UN'ALIQUOTA. Borse di dottorato e assegni di
      ricerca sono esenti IRPEF e stanno fuori dal lavoro dipendente: gross-up
      diverso, niente IRAP, niente detrazioni, imposta ZERO. Vanno separati per teste,
      non trattati con un'aliquota media piu' bassa.

COSA RESTA FUORI, per scelta: consumi indotti, IVA, gettito delle imprese fornitrici,
effetti di offerta di lavoro. Qui c'e' solo l'aritmetica certa di una busta paga che
lo Stato sta gia' pagando. Anche le ATTREZZATURE restano fuori: sono acquisti, non
stipendi, e il loro ritorno fiscale passa da IVA e imposte sui fornitori - che e'
un'altra stima, con altre ipotesi, e non va mescolata a questa.

CONVENZIONE: i valori di configurazione si leggono SEMPRE come C.NOME, mai importati
per nome. main() li riassegna a runtime (calibrazioni, argomenti da CLI) e solo
l'accesso per attributo vede il rebinding; un `from config import X` catturerebbe una
copia congelata all'import. Le funzioni invece non vengono mai riassegnate e si
importano per nome.
"""
from __future__ import annotations

from dataclasses import dataclass

import config as C

DIPENDENTE, ESENTE = "dipendente", "esente"


@dataclass(frozen=True)
class Voce:
    """Un gruppo OMOGENEO di personale: `teste` persone che costano tutte `costo`.

    `costo` e' il costo lordo ente PRO CAPITE gia' levato (W applicato), cioe'
    esattamente quello che il motore mette in budget. `regime` decide sia il gross-up
    sia la tassabilita': ESENTE e' la borsa/assegno (Gestione separata, IRPEF zero),
    DIPENDENTE tutto il resto.

    L'omogeneita' non e' un dettaglio implementativo: e' il requisito che rende
    lecito applicare gli scaglioni. Un gruppo che mescola stipendi diversi va spezzato
    in piu' Voci prima di arrivare qui."""
    nome: str
    teste: float
    costo: float
    regime: str = DIPENDENTE


# ---------------------------- l'imposta, pro capite -------------------------
def irpef_lorda(imponibile: float) -> float:
    """Imposta per scaglioni, prima delle detrazioni."""
    imposta, sotto = 0.0, 0.0
    for soglia, aliquota in C.IRPEF_SCAGLIONI:
        if imponibile <= sotto:
            break
        imposta += (min(imponibile, soglia) - sotto) * aliquota
        sotto = soglia
    return imposta


def detrazione(reddito: float) -> float:
    """Detrazione da lavoro dipendente (art. 13 TUIR) piu' l'ulteriore detrazione
    della L. 207/2024. Si azzerano entrambe entro i 50.000, quindi non toccano il
    personale di ruolo: mordono su postdoc, RTT e TA, che sono le figure che la
    riforma moltiplica di piu'."""
    b1, b2, b3 = C.DETR_LD_SOGLIE
    if reddito <= b1:
        d = C.DETR_LD_BASSA
    elif reddito <= b2:
        d = C.DETR_LD_FISSA + C.DETR_LD_MOBILE * (b2 - reddito) / (b2 - b1)
    elif reddito <= b3:
        d = C.DETR_LD_FISSA * (b3 - reddito) / (b3 - b2)
    else:
        d = 0.0
    k1, k2, k3 = C.DETR_BONUS_SOGLIE
    if k1 < reddito <= k2:
        d += C.DETR_BONUS
    elif k2 < reddito <= k3:
        d += C.DETR_BONUS * (k3 - reddito) / (k3 - k2)
    return d


def scomponi(v: Voce) -> dict[str, float]:
    """Da una Voce alla sua scomposizione fiscale, in EURO e per il gruppo intero.

    Il costo lordo ente si spacca in quattro pezzi che sommano esattamente ad esso:
    retribuzione NETTA (l'unica parte che esce davvero dal perimetro pubblico),
    IRPEF + addizionali, contributi (ente + percettore) e IRAP. La verifica che i
    quattro pezzi sommino al costo e' in _quadratura(), ed e' il test del modulo."""
    dip = v.regime == DIPENDENTE
    gross = C.GROSS_UP_DIP if dip else C.GROSS_UP_BORSA
    ral = v.costo / gross                                  # retribuzione lorda
    aliq_dip = C.ALIQ_CONTR_DIP if dip else C.ALIQ_CONTR_BORSA
    contr_dip = ral * aliq_dip
    contr_ente = v.costo - ral - (ral * C.ALIQ_IRAP if dip else 0.0)
    irap = ral * C.ALIQ_IRAP if dip else 0.0
    imponibile = ral - contr_dip
    if dip:
        # l'imposta non va sotto zero: incapienza, non credito. La somma integrativa
        # sotto i 20.000 (che sarebbe un credito vero) non riguarda questa popolazione
        irpef = max(0.0, irpef_lorda(imponibile) - detrazione(imponibile))
        addiz = imponibile * (C.ADD_REGIONALE + C.ADD_COMUNALE)
    else:
        irpef = addiz = 0.0                                # esenzione piena
    n = v.teste
    return {"teste": n, "costo": v.costo * n, "ral": ral * n,
            "imponibile": imponibile * n, "irpef": irpef * n, "addizionali": addiz * n,
            "contributi": (contr_ente + contr_dip) * n, "irap": irap * n,
            "netto": (imponibile - irpef - addiz) * n}


VOCI_TOT = ("costo", "ral", "imponibile", "irpef", "addizionali", "contributi",
            "irap", "netto", "teste")


def retroflusso(voci: list[Voce]) -> dict[str, float]:
    """Aggrega le Voci di un anno. In EURO; e' il motore a convertire in milioni.

    'retro' e' la somma di TUTTO cio' che rientra nel perimetro pubblico allargato
    (IRPEF + addizionali + contributi + IRAP); 'irpef' da sola e' la sola imposta
    erariale. Le due letture sono diverse e vanno tenute distinte: la prima e' il
    costo netto per la PA consolidata, la seconda e' quello che si vede sul bilancio
    dello Stato."""
    tot = {k: 0.0 for k in VOCI_TOT}
    for v in voci:
        for k, x in scomponi(v).items():
            tot[k] += x
    tot["retro"] = tot["irpef"] + tot["addizionali"] + tot["contributi"] + tot["irap"]
    tot["quota_retro"] = tot["retro"] / tot["costo"] if tot["costo"] else 0.0
    tot["quota_irpef"] = tot["irpef"] / tot["costo"] if tot["costo"] else 0.0
    # aliquota IRPEF media EFFETTIVA sull'imponibile: e' il numero da confrontare con
    # le aliquote di legge, e sta molto sotto perche' ci sono dentro anche gli esenti
    tot["aliq_media"] = tot["irpef"] / tot["imponibile"] if tot["imponibile"] else 0.0
    return tot


def _quadratura(voci: list[Voce]) -> float:
    """Scarto relativo fra il costo lordo ente e la somma dei suoi quattro pezzi.
    Dev'essere zero a meno dell'errore di macchina: se non lo e', la scomposizione
    perde (o inventa) denaro da qualche parte. Usata come test in main."""
    t = retroflusso(voci)
    ricomposto = t["netto"] + t["irpef"] + t["addizionali"] + t["contributi"] + t["irap"]
    return abs(ricomposto / t["costo"] - 1.0) if t["costo"] else 0.0
