"""Calibrazione sui dati osservati e diagnostica.

Ricava per RESIDUO i parametri che il modello non misura direttamente (quota-lavoro
dell'HERD, supporto non nominato, overhead degli enti) imponendo che lo stato
iniziale riproduca HERD e GOVERD osservati. Qui stanno anche i test di coerenza.

CONVENZIONE: i valori di configurazione si leggono SEMPRE come C.NOME, mai importati
per nome. main() li riassegna a runtime (calibrazioni, argomenti da CLI) e solo
l'accesso per attributo vede il rebinding; un `from config import X` catturerebbe una
copia congelata all'import. Le funzioni invece non vengono mai riassegnate e si
importano per nome.
"""
from __future__ import annotations

import pandas as pd

import config as C
from regime import (_epr_in_tgt, _ta_epr, _ta_uni, costo_epr_ruolo,
                    epr_in_rimpiazzo, epr_stock_regime, eta_ruolo_in,
                    quota_po_coorte, soglie_epr_tgt)
from motore import (_coorte, _costi, _fte_epr, _fte_ric_uni, _init_stato, _pd_in0,
                    _spesa, _spesa_epr, _teste)

# ============================ ANALISI =======================================
def _tempo_a_regime(df: pd.DataFrame, target: float, soglia: float = 0.90) -> int:
    # confronto col target a POPOLAZIONE FISSA: il target è un obiettivo di organico
    # espresso per 100k abitanti del 2026. Usando la densità SSP2 il traguardo
    # risulterebbe raggiunto in anticipo solo perchè cala il denominatore.
    d0 = df["densita_pop2026"].iloc[0]
    traguardo = d0 + soglia * (target - d0)
    ok = df[df["densita_pop2026"] >= traguardo]
    return int(ok["anno"].iloc[0]) if len(ok) else -1


def _herd_base() -> float:
    """HERD 'oggi' ricostruito dal modello, % PIL (test di calibrazione vs ISTAT 0,36)."""
    return _spesa(_init_stato(_pd_in0()), 1.0, 1.0)["herd_mln"] / C.PIL_MLN * 100


def _herd_assoluto(df: pd.DataFrame) -> float:
    return _herd_base() + df["dHERD_%PIL"].iloc[-1]


def _goverd_base() -> float:
    """GOVERD 'oggi' ricostruito dal modello, % PIL."""
    s = _init_stato(_pd_in0())
    return _spesa_epr(s, 1.0, C.COSTO_EPR_PREC_OGGI)["goverd_mln"] / C.PIL_MLN * 100


def _ric_epr_oggi() -> float:
    """Costo-ricerca (alpha-pesato) dei ricercatori EPR oggi, in euro."""
    s = _init_stato(_pd_in0())
    return (sum(s.epr_ruolo) * costo_epr_ruolo(s.epr_ruolo)
            + sum(s.epr_prec) * C.COSTO_EPR_PREC_OGGI) * C.ALPHA_EPR


def _calibra_overhead_epr() -> tuple[float, float]:
    """Scompone il GOVERD osservato in (residuo, attrezzature) come RESIDUI ASSOLUTI
    rispetto al costo-ricerca dei ricercatori E DEL TA, che ora è esplicito. Prima il
    TA stava tutto dentro OVH_EPR_SUPP: scontarlo qui è obbligatorio, altrimenti si
    conta due volte e il GOVERD di partenza sfora il dato osservato.
    Il residuo resta grande perchè gli EPR sono infrastruttura-intensivi."""
    tot = C.GOVERD_OGGI / 100 * C.PIL_MLN * 1e6
    lavoro = tot * C.LAMBDA_GOV
    ta = _ta_epr(_fte_epr(_init_stato(_pd_in0()))) * C.COSTO_TA
    return max(0.0, lavoro - _ric_epr_oggi() - ta * C.TA_UPLIFT), tot * (1 - C.LAMBDA_GOV)


def _goverd_di(ruolo: float, prec: float, c_ruolo: float, c_prec: float) -> float:
    """GOVERD (% PIL) di un organico EPR arbitrario, a overhead residuo fisso. Il TA
    invece SEGUE l'organico secondo TA_ELAST, quindi va ricalcolato ogni volta.

    Il TA_UPLIFT va applicato QUI come lo applicano _calibra_overhead_epr() (che lo
    scala prima di prendere il residuo) e _spesa_epr(): senza, ogni riga della tabella
    risultava piu' bassa di TA_EPR_OGGI * COSTO_TA * (TA_UPLIFT-1) = 368 mln, cioe'
    0,017pp, e la riga 'oggi' non riproduceva GOVERD_OGGI."""
    ric = (ruolo * c_ruolo + prec * c_prec) * C.ALPHA_EPR
    ta = _ta_epr((ruolo + prec) * C.ALPHA_EPR) * C.COSTO_TA * C.TA_UPLIFT
    return (ric + ta + C.OVH_EPR_SUPP + C.OVH_EPR_ATTR) / 1e6 / C.PIL_MLN * 100


def _tabella_stabilizzazione() -> pd.DataFrame:
    """Scomposizione del costo del ramo EPR in tre passi, per isolare cosa costa cosa:
    l'abolizione degli assegni, la stabilizzazione a organico fermo e infine
    l'ESPANSIONE che riporta il GOVERD a target. Solo l'ultima riga è il regime che il
    motore simula; le precedenti servono a dire quanta parte della spesa è riforma del
    precariato e quanta è crescita del sistema."""
    s0 = _init_stato(_pd_in0())
    c_ruolo0 = costo_epr_ruolo(s0.epr_ruolo)
    tot = C.EPR_RUOLO_OGGI + C.EPR_PRECARI_OGGI
    # flusso di CONTRATTI DI RICERCA che tiene fermo l'organico dato P2_EPR: solo una
    # quota supera la Madia, quindi ne servono più di quanti ne uscirebbero dal ruolo.
    # Il canale diretto sta già dentro epr_stock_regime() come blocco fisso.
    intake = epr_in_rimpiazzo()
    ruolo_reg, prec_reg = epr_stock_regime(intake)
    # ...e il flusso che invece porta la spesa a GOVERD_TGT, a paghe ferme: è quello
    # che il motore usa davvero. La differenza fra le due righe è l'ESPANSIONE.
    in_tgt = _epr_in_tgt(1.0)
    ruolo_tgt, prec_tgt = epr_stock_regime(in_tgt)
    # costo per testa del ruolo EPR A REGIME: coorte uniforme e soglie di ARRIVO della
    # rampa, cioe' esattamente il c_ruolo su cui epr_in_iso_goverd() inverte il GOVERD.
    # Le due righe di regime usavano C.COSTO_EPR_RUOLO (73.500, un valore scritto a
    # mano che non corrisponde a nessuna delle due composizioni): con quello la riga
    # dell'espansione non tornava sul GOVERD_TGT che l'ha generata.
    c_ruolo_reg = costo_epr_ruolo([1.0] * int(C.PERM_DUR_EPR), *soglie_epr_tgt())
    righe = [
        ("oggi (mix 50% assegni)", C.EPR_RUOLO_OGGI, C.EPR_PRECARI_OGGI,
         c_ruolo0, C.COSTO_EPR_PREC_OGGI),
        ("assegni -> contratti di ricerca (L.79/2022, senza stabilizzare)",
         C.EPR_RUOLO_OGGI, C.EPR_PRECARI_OGGI, c_ruolo0, C.COSTO_EPR_PREC_TGT),
        ("stabilizzazione oggi (i 6.000 entrano al III, 0-2 anni)",
         C.EPR_RUOLO_OGGI + C.EPR_PRECARI_OGGI, 0.0,
         (C.EPR_RUOLO_OGGI * c_ruolo0 + C.EPR_PRECARI_OGGI * C.COSTO_EPR_INGRESSO) / tot, 0.0),
        (f"a regime, organico fermo: {C.D_PREC_EPR}a contratto -> Madia al "
         f"{C.P2_EPR:.0%} ({intake:,.0f} contratti di ricerca/anno)",
         ruolo_reg, prec_reg, c_ruolo_reg, C.COSTO_EPR_PREC_TGT),
        (f"a regime, ESPANSIONE a GOVERD {C.GOVERD_TGT}% "
         f"({in_tgt:,.0f} contratti di ricerca/anno)",
         ruolo_tgt, prec_tgt, c_ruolo_reg, C.COSTO_EPR_PREC_TGT),
    ]
    out = []
    for nome, r, p, cr, cp in righe:
        g = _goverd_di(r, p, cr, cp)
        out.append({"scenario": nome, "ruolo": round(r), "precari": round(p),
                    "GOVERD_%PIL": round(g, 3),
                    "d_mln": round((g - C.GOVERD_OGGI) / 100 * C.PIL_MLN),
                    "d_budget_mln": round((r * cr + p * cp
                                           - C.EPR_RUOLO_OGGI * c_ruolo0
                                           - C.EPR_PRECARI_OGGI * C.COSTO_EPR_PREC_OGGI) / 1e6)})
    return pd.DataFrame(out)


def _calibra_anni_da_associato() -> float:
    """Anni di ruolo prima della promozione a ordinario, RICAVATI dallo stock del 2023.

    Si cerca la soglia di anzianità che, applicata alla coorte per età del 2026,
    restituisce esattamente la quota di ordinari OSSERVATA (QUOTA_PO = 16.574/43.046).
    Non è una stima della durata media di un'associatura: è la soglia che rende il
    modello coerente col dato MUR nell'anno base. Vedi il blocco ANNI_DA_ASSOCIATO in
    config per perchè l'ancora è il 2026 e non lo stato stazionario.

    La quota è MONOTONA nella soglia - alzarla sposta classi da ordinario ad associato
    e non può fare altro - quindi la bisezione converge sempre e converge all'unica
    soluzione. 60 dimezzamenti su un intervallo di ~24 anni portano l'errore sotto
    1e-17 anni: il limite è la precisione della macchina, non le iterazioni.

    Va chiamata PRIMA di _calibra_lambda_he: il costo dei professori entra nell'HERD
    ricostruito, quindi nel residuo. Sui parametri correnti l'ancora garantisce che il
    costo del 2026 sia identico al vecchio mix e lambda non si muova - ma è una
    proprietà del risultato, non dell'ordine, e l'ordine va rispettato lo stesso."""
    perm0 = _coorte(C.PERM_OGGI, eta_ruolo_in(C.PRECARI_ANNI))
    lo, hi = 0.0, float(len(perm0))
    for _ in range(60):
        mid = (lo + hi) / 2
        # soglia più alta -> meno ordinari: se ne restano troppi, va alzata
        if quota_po_coorte(perm0, mid) > C.QUOTA_PO:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _calibra_lambda_he() -> float:
    """Quota-lavoro dell'HERD, RICAVATA invece che assunta.

    Con il TA esplicito il costo del personale di ricerca è tutto misurato -
    ricercatori a costi di CCNL, borse di dottorato, TA in FTE Eurostat - quindi la
    ripartizione lavoro/attrezzature dell'HERD osservato non è più libera: è un residuo.

    Il vecchio LAMBDA_HE=0,70 non è compatibile con i dati: lascerebbe 237 mln per
    31.357 FTE di tecnici, cioè 7.568 EUR a testa-anno. Il conflitto non è del TA, è
    dell'assunzione sul 30% di attrezzature: per il settore universitario è troppo alta.
    Se il valore ricavato esce sopra 0,90 vale la pena sospettare i costi unitari o
    HERD_OGGI, non accettarlo: significherebbe che l'università non compra strumenti."""
    s = _init_stato(_pd_in0())
    teste = _teste(s)
    # 'docente' al costo effettivo della coorte 2026: con la soglia ancorata sul 2026
    # è per costruzione il vecchio mix, ma passare da _costi() rende la proprietà
    # verificata invece che presunta - e regge se qualcuno forza un'altra soglia.
    cst = _costi(s)
    lavoro = sum(t * C.ALPHA[k] * cst[k] for k, t in teste.items())
    lavoro += _ta_uni(_fte_ric_uni(s)) * C.COSTO_TA * C.TA_UPLIFT
    return lavoro / (C.HERD_OGGI / 100 * C.PIL_MLN * 1e6)


def _calibra_supporto() -> float:
    """Overhead di personale di supporto che porta l'HERD 'oggi' del modello sul dato
    ISTAT. è un RESIDUO: assorbe tutto cio' che il modello non conta esplicitamente
    (tecnici, amministrativi di ricerca), non solo lo stipendio di un tecnico."""
    salva, C.SUPPORTO = C.SUPPORTO, 0.0
    b0 = _herd_base()
    C.SUPPORTO = 1.0
    b1 = _herd_base()
    C.SUPPORTO = salva
    if b1 <= b0:
        return 0.0
    return max(0.0, (C.HERD_OGGI - b0) / (b1 - b0))
