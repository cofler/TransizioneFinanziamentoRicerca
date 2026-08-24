"""Composizione di STATO STAZIONARIO e frontiera prezzo/quantità.

Nessuna dinamica qui: solo la composizione che l'imbuto di carriera produce a
regime, i costi medi che ne derivano e la frontiera iso-HERD. Questa è la parte del
modello che si puo' risolvere in forma chiusa.

"""
from __future__ import annotations

import config as C

# ============================ COMPOSIZIONE A REGIME ==========================
def eta_ruolo_in(precari_anni: float) -> int:
    """Età d'ingresso in ruolo: fine PhD + precariato + RTT. Un precariato più
    lungo non allunga la vita lavorativa, la sposta in avanti."""
    return int(round(C.ETA_FINE_PHD + precari_anni + C.D_RTT))


def perm_dur(precari_anni: float) -> int:
    """Anni di ruolo effettivi (slot della coorte). A precari_anni=3 vale 28."""
    return max(1, C.ETA_PENS - eta_ruolo_in(precari_anni))


# ---------------------- composizione PO/PA di una coorte ---------------------
def quota_po_coorte(coorte: list[float], soglia: float | None = None) -> float:
    """Quota di ORDINARI in una coorte di professori data per ETÀ, indice 0 = appena
    entrato in ruolo, ultimo indice = ultimo anno prima della pensione.

    Chi ha almeno ANNI_DA_ASSOCIATO anni di ruolo è CANDIDATO a ordinario; di quei
    candidati ne passa la frazione PROMOSSI_PO, il resto resta associato per sempre.

    La soglia da sola non basta perchè implicherebbe che le classi anziane siano
    interamente ordinarie, mentre nel 2024 la classe 65+ è al 64% - più di un terzo dei
    professori va in pensione da associato. La saturazione a PROMOSSI_PO è la parte del
    profilo di promozione che i dati identificano; lo spread dei TEMPI non lo è (vedi
    il blocco PROMOSSI_PO in config), e per questo la soglia resta secca.

    La classe di BORDO entra per la sua parte frazionaria invece di finire tutta da una
    parte: con ~25 classi un arrotondamento sposterebbe la quota di ~4 punti, cioè più
    dell'effetto che questa funzione serve a misurare. È anche l'unico modo perchè la
    calibrazione della soglia abbia una soluzione esatta invece che a scatti - e vale
    ancora identico dopo l'introduzione di PROMOSSI_PO, che è un fattore costante e non
    tocca nè la continuità nè la monotonia in `soglia`.

    A soglia non calibrata usa il ripiego di _soglia(), che su una coorte uniforme
    restituisce esattamente QUOTA_PO: i moduli restano importabili e testabili senza
    aver girato main()."""
    tot = sum(coorte)
    if tot <= 0:
        return C.QUOTA_PO
    s = _soglia(len(coorte), soglia)
    k = int(s)
    pa = sum(coorte[:k]) + (s - k) * (coorte[k] if k < len(coorte) else 0.0)
    return C.PROMOSSI_PO * (tot - pa) / tot


def _ral(scala: list[tuple[int, float]], t: float) -> float:
    """Lordo dipendente alla anzianità t su una scala a GRADINI: si sale di classe
    all'anno indicato e ci si resta fino al successivo. Sotto la prima classe vale la
    prima, sopra l'ultima vale l'ultima - le scale non si estrapolano."""
    v = scala[0][1]
    for anni, lordo in scala:
        if t >= anni:
            v = lordo
    return v


def _anzianita_po(soglia: float) -> float:
    """Anzianità PO di partenza di chi viene promosso dopo `soglia` anni da associato.

    NON zero, e non l'anzianità intera: la regola è il non peggioramento. Chi passa di
    fascia è collocato nella prima classe della nuova fascia che non sia inferiore a
    quanto già percepiva, e da lì riprende a maturare.
    """

    cur = _ral(C.SCALA_PA, soglia)
    for anni, lordo in C.SCALA_PO:
        if lordo >= cur:
            return float(anni)
    return float(C.SCALA_PO[-1][0])


def _soglia(coorte_len: int, soglia: float | None) -> float:
    """La soglia da usare, con il ripiego per quando non è ancora calibrata: quella che
    su una coorte uniforme dà QUOTA_PO. Serve solo a tenere i moduli importabili e
    testabili senza aver girato main().

    Con la saturazione a PROMOSSI_PO la quota su coorte uniforme è PROMOSSI_PO*(n-s)/n,
    che invertita dà s = n*(1 - QUOTA_PO/PROMOSSI_PO): resta una riga, non serve
    calibrare nulla per il ripiego."""
    s = C.ANNI_DA_ASSOCIATO if soglia is None else soglia
    if s is None:
        s = (1 - C.QUOTA_PO / C.PROMOSSI_PO) * coorte_len
    return max(0.0, min(float(coorte_len), s))


# ============================ BLOCCO SCATTI STIPENDIALI =====================
def _finestre() -> list[tuple[float, float, float]]:
    """Le finestre di blocco ATTIVE, come (primo anno, primo anno DOPO, recupero).

    Sono due e indipendenti - la grande sulla gobba del 2057, la piccola sul gradino di
    fine rampa del 2036 - e ciascuna ha il suo recupero. Una finestra con ANNI < 1 e'
    spenta e non compare. Devono restare DISGIUNTE: _persi() somma finestra per finestra
    e un anno coperto due volte verrebbe tolto due volte (vedi il blocco in config)."""
    f = []
    for da, anni, rec in ((C.SCATTI_BLOCCO_DA, C.SCATTI_BLOCCO_ANNI,
                           C.SCATTI_BLOCCO_RECUPERO),
                          (C.SCATTI_BLOCCO2_DA, C.SCATTI_BLOCCO2_ANNI,
                           C.SCATTI_BLOCCO2_RECUPERO)):
        if anni >= 1:
            f.append((float(da), float(da + anni), rec))
    return f

def _blocco_on() -> bool:
    return bool(_finestre())

def _sovrapposizione(da: float, a1: float, e: float, t: float) -> float:
    return max(0.0, min(t, a1) - max(e, da))

def _persi(e: float, t: float) -> float:
    """Anni di scatto NON maturati da chi è in servizio nell'intervallo [e, t]: la somma
    delle sovrapposizioni con ogni finestra, al netto della quota poi restituita."""
    return sum(_sovrapposizione(da, a1, e, t) * (1.0 - rec)
               for da, a1, rec in _finestre())

def _prima_classe(scala: list[tuple[int, float]], cur: float) -> float:
    for anni, lordo in scala:
        if lordo >= cur:
            return float(anni)
    return float(scala[-1][0])

def _anzianita_po_da(soglia: float, anno: int | None = None) -> float:
    if anno is None or not _blocco_on():
        return _anzianita_po(soglia)
    e = float(anno) - soglia
    adj = soglia - _persi(e, float(anno))
    return _prima_classe(C.SCALA_PO, _ral(C.SCALA_PA, adj))

def _anzianita_liv2_da(s_ii: float, anno: int | None = None) -> float:
    if anno is None or not _blocco_on():
        return _anzianita_liv2(s_ii)
    e = float(anno) - s_ii
    adj = s_ii - _persi(e, float(anno))
    return _prima_classe(C.SCALA_EPR_II, _ral_epr(C.SCALA_EPR_III, adj))

def _anzianita_liv1_da(s_i: float, anno: int | None = None) -> float:
    if anno is None or not _blocco_on():
        return _anzianita_liv1(s_i)
    e = float(anno) - s_i
    adj = s_i - _persi(e, float(anno))
    return _prima_classe(C.SCALA_EPR_I, _ral_epr(C.SCALA_EPR_II, adj))


def costo_classe(n: int, soglia: float | None = None,
                 anno: int | None = None) -> list[float]:
    """Costo lordo ente per testa in ogni classe di anzianità.

    Sopra la soglia la classe non è tutta ordinaria: è la MISCELA fra la quota
    PROMOSSI_PO che è passata di fascia e il resto che resta associato e continua a
    maturare sulla scala PA. Sotto la soglia sono tutti associati.

    La miscela pesa poco sul risultato, e il motivo è istruttivo: per il non
    peggioramento (_anzianita_po) la promozione colloca nella prima classe PO non
    inferiore a quanto già si percepiva, cioè il salto minimo. Un associato con 20 anni
    di anzianità prende 84.220 e un ordinario di classe 0 ne prende 80.916 - l'etichetta
    di fascia, da sola, quasi non muove il costo. A muoverlo è la posizione sulla
    progressione, cioè l'età, che la coorte già porta con sè."""
    s = _soglia(n, soglia)
    off = _anzianita_po(s)
    pi = C.PROMOSSI_PO
    c = []
    for i in range(n):
        t = i + 0.5
        if _blocco_on() and anno is not None:
            e = float(anno) - t
            # chi non viene mai promosso resta sulla scala PA per tutta la carriera
            sal_pa = _ral(C.SCALA_PA, t - _persi(e, float(anno)))
            if t < s:
                c.append(sal_pa)
            else:
                p = float(anno) - (t - s)
                sal_promo = _ral(C.SCALA_PA, s - _persi(e, p))
                po_off = _prima_classe(C.SCALA_PO, sal_promo)
                po_sen = po_off + (t - s) - _persi(p, float(anno))
                c.append(pi * _ral(C.SCALA_PO, po_sen) + (1 - pi) * sal_pa)
        else:
            if t < s:
                c.append(_ral(C.SCALA_PA, t))
            else:
                c.append(pi * _ral(C.SCALA_PO, off + t - s)
                         + (1 - pi) * _ral(C.SCALA_PA, t))
    return [x * C.GROSS_UP_DIP for x in c]


def costo_docente(coorte: list[float], soglia: float | None = None,
                  anno: int | None = None) -> float:
    """Costo lordo ente per TESTA della coorte dei professori: la media della scala
    PESATA SULLE TESTE che stanno in ogni classe d'età.

    È qui che sta la risposta a "non sovrastimare nè sottostimare": non si sceglie un
    numero rappresentativo, si integra la progressione sulla distribuzione per età che
    il modello già simula. Un organico giovane costa poco e uno vecchio costa molto
    senza che nessun parametro debba dirlo."""
    tot = sum(coorte)
    if tot <= 0:
        return C.COSTO["docente"]
    return sum(t * c for t, c in zip(coorte, costo_classe(len(coorte), soglia, anno))) / tot


# ---------------------- composizione LIVELLI EPR ---------------------------
def _ral_epr(scala: list[tuple[int, float]], t: float) -> float:
    v = scala[0][1]
    for anni, costo in scala:
        if t >= anni:
            v = costo
    return v

def _anzianita_liv2(s_ii: float) -> float:
    cur = _ral_epr(C.SCALA_EPR_III, s_ii)
    for anni, costo in C.SCALA_EPR_II:
        if costo >= cur:
            return float(anni)
    return float(C.SCALA_EPR_II[-1][0])

def _anzianita_liv1(s_i: float) -> float:
    cur = _ral_epr(C.SCALA_EPR_II, s_i)
    for anni, costo in C.SCALA_EPR_I:
        if costo >= cur:
            return float(anni)
    return float(C.SCALA_EPR_I[-1][0])

def _soglia_epr(n: int, s_ii: float | None, s_i: float | None) -> tuple[float, float]:
    a2 = C.ANNI_DA_LIV2 if s_ii is None else s_ii
    a1 = C.ANNI_DA_LIV1 if s_i is None else s_i
    if a2 is None:
        a2 = (1 - C.QUOTA_EPR_II - C.QUOTA_EPR_I) * n
    if a1 is None:
        a1 = (1 - C.QUOTA_EPR_I) * n
    return max(0.0, min(float(n), a2)), max(0.0, min(float(n), a1))

def quota_epr_coorte(coorte: list[float], s_ii: float | None = None,
                     s_i: float | None = None) -> tuple[float, float, float]:
    """Quote di (III, II, I) nella coorte EPR di ruolo, data per età."""
    tot = sum(coorte)
    if tot <= 0:
        return C.QUOTA_EPR_III, C.QUOTA_EPR_II, C.QUOTA_EPR_I
    n = len(coorte)
    a2, a1 = _soglia_epr(n, s_ii, s_i)
    k2, k1 = int(a2), int(a1)
    iii = sum(coorte[:k2]) + (a2 - k2) * (coorte[k2] if k2 < n else 0.0)
    ii = (sum(coorte[k2:k1]) + (a1 - k1) * (coorte[k1] if k1 < n else 0.0)
          if k1 < n else 0.0)
    if k2 < n:
        ii -= (a2 - k2) * (coorte[k2] if k2 < n else 0.0)
    i = tot - iii - ii
    return iii / tot, ii / tot, i / tot

def costo_classe_epr(n: int, s_ii: float | None = None,
                     s_i: float | None = None,
                     anno: int | None = None) -> list[float]:
    a2, a1 = _soglia_epr(n, s_ii, s_i)
    off_ii = _anzianita_liv2(a2)
    off_i = _anzianita_liv1(a1)
    c = []
    for i in range(n):
        t = i + 0.5
        if _blocco_on() and anno is not None:
            e = float(anno) - t
            if t < a2:
                c.append(_ral_epr(C.SCALA_EPR_III, t - _persi(e, float(anno))))
            elif t < a1:
                p2 = float(anno) - (t - a2)
                sal_iii = _ral_epr(C.SCALA_EPR_III, a2 - _persi(e, p2))
                ii_off = _prima_classe(C.SCALA_EPR_II, sal_iii)
                c.append(_ral_epr(C.SCALA_EPR_II,
                                  ii_off + (t - a2) - _persi(p2, float(anno))))
            else:
                p1 = float(anno) - (t - a1)
                p2 = float(anno) - (t - a2)
                sal_iii = _ral_epr(C.SCALA_EPR_III, a2 - _persi(e, p2))
                ii_off_p2 = _prima_classe(C.SCALA_EPR_II, sal_iii)
                sal_ii = _ral_epr(C.SCALA_EPR_II,
                                  ii_off_p2 + (a1 - a2) - _persi(p2, p1))
                i_off = _prima_classe(C.SCALA_EPR_I, sal_ii)
                c.append(_ral_epr(C.SCALA_EPR_I,
                                  i_off + (t - a1) - _persi(p1, float(anno))))
        else:
            if t < a2:
                c.append(_ral_epr(C.SCALA_EPR_III, t))
            elif t < a1:
                c.append(_ral_epr(C.SCALA_EPR_II, off_ii + t - a2))
            else:
                c.append(_ral_epr(C.SCALA_EPR_I, off_i + t - a1))
    return c

def costo_epr_ruolo(coorte: list[float], s_ii: float | None = None,
                    s_i: float | None = None,
                    anno: int | None = None) -> float:
    tot = sum(coorte)
    if tot <= 0:
        return C.COSTO_EPR_RUOLO
    return sum(t * c for t, c in zip(coorte, costo_classe_epr(len(coorte), s_ii, s_i, anno))) / tot

def anni_da_liv2_tgt() -> float:
    return (1 - C.QUOTA_EPR_II_TGT - C.QUOTA_EPR_I_TGT) * C.PERM_DUR_EPR

def anni_da_liv1_tgt() -> float:
    return (1 - C.QUOTA_EPR_I_TGT) * C.PERM_DUR_EPR

def soglie_epr_oggi() -> tuple[float, float]:
    """Le due soglie di anzianità III->II->I del 2026: gli override da CLI se ci sono,
    altrimenti quelle implicite nel mix (III, II, I) OSSERVATO."""
    return _soglia_epr(int(C.PERM_DUR_EPR), None, None)

def soglie_epr_tgt() -> tuple[float, float]:
    """Le stesse due soglie a REGIME. Sono queste, e non quelle del 2026, il costo che
    la frontiera iso-GOVERD deve usare - vedi costi_regime() per l'argomento gemello
    sul ramo universitario."""
    return anni_da_liv2_tgt(), anni_da_liv1_tgt()

# ---------------------- ric_uni: STESSA scala EPR (III→II→I) ---------------
def perm_dur_ric() -> int:
    """Anni di ruolo per i ricercatori universitari (ric_uni). Hanno la durata di
    carriera dei professori (stessa età d'ingresso dopo RTT), NON quella EPR."""
    return perm_dur(C.PRECARI_ANNI)

def soglie_ric_uni_oggi() -> tuple[float, float]:
    """Soglie III->II->I per i ricercatori universitari, anno 2026. Stessa logica
    delle EPR, ma calibrate sulla durata di carriera universitaria (perm_dur_ric)
    invece che su PERM_DUR_EPR: a parità di frazioni di mix, gli anni assoluti
    differiscono perchè la carriera è più corta."""
    return _soglia_epr(perm_dur_ric(), None, None)

def soglie_ric_uni_tgt() -> tuple[float, float]:
    """Soglie di REGIME per i ricercatori universitari, stesse quote target EPR."""
    n = perm_dur_ric()
    return (1 - C.QUOTA_EPR_II_TGT - C.QUOTA_EPR_I_TGT) * n, (1 - C.QUOTA_EPR_I_TGT) * n

def coorte_regime() -> list[float]:
    """Coorte di professori a stato stazionario. Flusso d'ingresso costante e nessuna
    uscita prima di ETA_PENS: tutte le classi d'età pesano uguale. Non è un'ipotesi in
    più, è la definizione di stato stazionario del compartimento."""
    return [1.0] * perm_dur(C.PRECARI_ANNI)


def anni_da_associato_tgt() -> float:
    """Soglia di anzianità che, a regime, dà QUOTA_PO_TGT di ordinari.

    Su una coorte uniforme la quota di ordinari è PROMOSSI_PO per la frazione di classi
    sopra la soglia, quindi il conto si inverte ancora in una riga e non serve calibrare
    nulla: soglia = perm_dur * (1 - QUOTA_PO_TGT/PROMOSSI_PO). È il punto d'arrivo della
    rampa; il punto di partenza è ANNI_DA_ASSOCIATO, calibrato sul 2026.

    Ricavata e non scritta a mano perchè perm_dur dipende da ETA_PENS, D_RTT e
    PRECARI_ANNI: un 12 costante smetterebbe di dare il 50/50 al primo che tocca uno
    di quei tre.

    ATTENZIONE al vincolo che PROMOSSI_PO impone: la quota di ordinari non può superare
    la frazione che viene promossa, quindi QUOTA_PO_TGT > PROMOSSI_PO non ha soluzione e
    QUOTA_PO_TGT appena sotto ne ha una che schiaccia la soglia verso zero. Con i valori
    correnti (0,50 contro 0,59) la soglia di regime è corta: il modello sta dicendo che
    il 50/50 non si raggiunge ritardando meno le promozioni, si raggiunge promuovendo
    PRIMA una platea che resta comunque minoritaria. Se la si vuole raggiungere
    allargando la platea, il parametro da muovere è PROMOSSI_PO, non questa soglia."""
    if C.QUOTA_PO_TGT >= C.PROMOSSI_PO:
        raise ValueError(
            f"QUOTA_PO_TGT={C.QUOTA_PO_TGT} non è raggiungibile: solo il "
            f"{C.PROMOSSI_PO:.0%} di una coorte arriva a ordinario. Alzare PROMOSSI_PO.")
    return (1 - C.QUOTA_PO_TGT / C.PROMOSSI_PO) * perm_dur(C.PRECARI_ANNI)


def costi_regime() -> dict[str, float]:
    """I COSTO del modello con 'docente' al valore di STATO STAZIONARIO. È questo, e non
    il mix osservato del 2023, il costo che la frontiera iso-HERD deve usare: la
    frontiera è una grandezza di regime, e a regime valgono la coorte uniforme e la
    soglia di ARRIVO della rampa, non quella calibrata sul 2026.

    Con QUOTA_PO_TGT = 0,50 il conto si semplifica a metà e metà, cioè 104.000 EUR per
    testa contro i 98.280 del mix di oggi: +5,8%. È la frontiera che se ne accorge - a
    HERD fisso quel costo in più si paga in densità - ed è il motivo per cui questa
    funzione esiste invece di lasciare che avg_costo legga C.COSTO.

    Anche 'ric_uni' ora segue la scala EPR (III→II→I) invece del costo piatto."""
    coorte = coorte_regime()
    return {**C.COSTO,
            "docente": costo_docente(coorte, anni_da_associato_tgt()),
            "ric_uni": costo_epr_ruolo(coorte, *soglie_ric_uni_tgt())}


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
    # alpha DI REGIME: qui non c'è una rampa da percorrere, è lo stato stazionario.
    # Per il postdoc vale quindi ALPHA_PREC_TGT (sola ricerca), non l'alpha di oggi.
    fte = {k: v * C.alpha_regime()[k] for k, v in teste.items()}
    if not C.PHD_IN_FTE:
        fte["dottorando"] = 0.0        # esclusi dal CONTEGGIO, non dal costo
    return teste, fte


def kappa(P2: float, precari_anni: float) -> float:
    """FTE-ricerca universitari per unità di flusso POSTDOC in ingresso, a regime."""
    return sum(_contrib(P2, precari_anni)[1].values())


def epr_in_diretto() -> float:
    """Flusso COSTANTE del canale diretto: puro rimpiazzo dello stock non-MUR.

    Non è una quota delle assunzioni e non si espande col ramo (vedi EPR_NON_MUR_OGGI
    in config): ISS, ISPRA, CREA, ARPA, regioni e ministeri rimpiazzano chi va in
    pensione, e basta. Tutta l'espansione che il GOVERD finanzia passa quindi dalla
    filiera MUR, che è l'unica di cui il modello conosca la struttura di carriera."""
    return C.EPR_NON_MUR_OGGI / C.PERM_DUR_EPR


def epr_in_phd(epr_in_pd: float) -> float:
    """Flusso EPR che pesa sul bacino dei DOTTORANDI: tutto il canale postdoc più la
    parte del canale diretto che il dottorato lo chiede (PHD_NEL_DIRETTO_EPR). Il resto
    - concorsi da laurea - assume comunque, ma da un mercato che il modello non simula:
    quelle teste entrano in ruolo senza che nessuno le chieda al dottorato italiano."""
    return epr_in_pd + epr_in_diretto() * C.PHD_NEL_DIRETTO_EPR


def epr_stock_regime(epr_in_pd: float) -> tuple[float, float]:
    """Stock EPR di regime (ruolo, precari) dato il flusso del canale POSTDOC.

    Il canale diretto entra come blocco FISSO, non come quota dell'argomento: il ruolo è
    quindi affine in epr_in_pd, non proporzionale. Chi passa dal postdoc ci resta
    D_PREC_EPR anni e ne supera la Madia solo per P2_EPR; il ruolo dura PERM_DUR_EPR anni
    per entrambi i canali - chi entra per concorso lo fa alla stessa età, avendo passato
    altrove gli anni che gli altri fanno da postdoc.

    È P2_EPR<1 a rompere il vecchio conto a "organico costante": lo stesso flusso
    postdoc produce un ruolo dimezzato. Per questo il fabbisogno non si legge più sulle
    teste ma sulla spesa."""
    ruolo = (epr_in_diretto() + epr_in_pd * C.P2_EPR) * C.PERM_DUR_EPR
    return ruolo, epr_in_pd * C.D_PREC_EPR


def epr_in_iso_goverd(goverd_pct: float, W: float) -> float:
    W_ta = C.TA_UPLIFT
    r0, p0 = epr_stock_regime(0.0)
    n_ruolo, n_prec = [a - b for a, b in zip(epr_stock_regime(1.0), (r0, p0))]
    c_ruolo = costo_epr_ruolo([1.0] * int(C.PERM_DUR_EPR), *soglie_epr_tgt())
    ta_marg = C.TA_EPR_OGGI * C.TA_ELAST / (C.EPR_RICERC_OGGI * C.ALPHA_EPR)
    A = (W * (r0 * c_ruolo * C.ALPHA_EPR + C.OVH_EPR_SUPP)
         + W_ta * C.COSTO_TA * (C.TA_EPR_OGGI * (1 - C.TA_ELAST)
                                + ta_marg * (r0 + p0) * C.ALPHA_EPR)
         + C.OVH_EPR_ATTR)
    B = C.ALPHA_EPR * (W * (n_ruolo * c_ruolo + n_prec * C.COSTO_EPR_PREC_TGT)
                       + W_ta * C.COSTO_TA * ta_marg * (n_ruolo + n_prec))
    return max(0.0, (goverd_pct / 100 * C.PIL_MLN * 1e6 - A) / B)


def epr_in_rimpiazzo() -> float:
    """Flusso POSTDOC che tiene l'organico EPR sul livello odierno. Il canale diretto ci
    mette già EPR_NON_MUR_OGGI teste, quindi qui si rimpiazza solo la filiera MUR. NON è
    il fabbisogno di regime (vedi _epr_in_tgt): è il termine di paragone che dice quanta
    parte dell'espansione è espansione."""
    r0, p0 = epr_stock_regime(0.0)
    n_ruolo, n_prec = [a - b for a, b in zip(epr_stock_regime(1.0), (r0, p0))]
    return max(0.0, (C.EPR_RICERC_OGGI - r0 - p0) / (n_ruolo + n_prec))


def _epr_in_tgt(W: float = 1.0) -> float:
    """Fabbisogno EPR a regime: il flusso che porta il GOVERD a GOVERD_TGT.

    Non è più il rimpiazzo a organico costante. Il ramo enti ha ora un OBIETTIVO DI
    SPESA (GOVERD_TGT) esattamente come il ramo universitario ha HERD_TGT, e l'organico
    è ciò che ne consegue: se la selezione alla Madia (P2_EPR) fa calare la spesa,
    il modello assume che il ramo si espanda in assunzioni fino a riportarla a target."""
    return epr_in_iso_goverd(C.GOVERD_TGT, W)


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
    cst = costi_regime()          # 'docente' alla composizione PO/PA di regime
    costo = {k: t * C.alpha_regime()[k] * cst[k] / tot for k, t in teste.items()}
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
    per il perchè l'elasticità sta fra 0 e 1 e per l'asintoto che ne consegue."""
    if ric0 <= 0:
        return ta0
    return max(0.0, ta0 * (1 - C.TA_ELAST + C.TA_ELAST * fte_ric / ric0))


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
    c_ta = C.COSTO_TA * (C.TA_UPLIFT + k_attr)
    # TA(R) = fisso + marg*R  ->  budget = R*c_ric + (fisso + marg*R)*c_ta
    fisso, marg = C.TA_UNI_OGGI * (1 - C.TA_ELAST), C.TA_UNI_OGGI * C.TA_ELAST / C.FTE_OGGI
    budget = (herd_pct / 100 * C.PIL_MLN) * 1e6
    fte = max(0.0, (budget - fisso * c_ta) / (c_ric + marg * c_ta))
    return fte / C.POP_100K
