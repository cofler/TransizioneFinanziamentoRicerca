"""Palette e figure. Nessun calcolo di modello: entrano DataFrame, escono PNG.

Le scelte di colore sono documentate dove vengono fatte: le due rampe dello stack,
la palette degli scenari e quella della spesa rispondono a vincoli di contrasto
diversi, ed e' il motivo per cui non sono la stessa.
(La funzione di trend si chiama grafico_trend, non grafici: il nome vecchio
collideva con quello del modulo.)

CONVENZIONE: i valori di configurazione si leggono SEMPRE come C.NOME, mai importati
per nome. main() li riassegna a runtime (calibrazioni, argomenti da CLI) e solo
l'accesso per attributo vede il rebinding; un `from config import X` catturerebbe una
copia congelata all'import. Le funzioni invece non vengono mai riassegnate e si
importano per nome.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt

import config as C
from motore import _teste_tot

# ============================ REPORT 2026-2050 ==============================
# Palette: primi tre slot della palette di riferimento (validati all-pairs).
PAL = {"ERA_PPP_ric": "#2a78d6", "ERA": "#eb6834", "FLC": "#1baf7a"}
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#898781", "#e1e0d9"

# Rampa dello stack di composizione. Le fasce NON sono categorie indipendenti ma
# STADI ORDINATI di carriera: una sola tinta a luminosità decrescente verso
# l'alto, non tinte diverse. Volutamente estranea a PAL: i colori degli scenari
# restano riservati alla linea di totale in cima allo stack.
# DUE rampe, non una da sette passi: università e EPR sono settori contabili
# distinti (HERD vs GOVERD). La TINTA dice il settore, la LUMINOSITà lo stadio di
# carriera dentro il settore. Le due famiglie sono INTERLACCIATE, perchè lo stack
# è ordinato per stadio: postdoc EPR accanto ai postdoc universitari, ricercatori
# EPR accanto ai ricercatori universitari. Un'unica rampa a 7 passi non starebbe nei
# vincoli (servirebbero 0,36 di escursione in L tenendo l'estremo chiaro leggibile).
# Verificato con validate_palette.py sulle coppie ADIACENTI nell'ordine di impilamento,
# le sole che si toccano nel disegno: CVD peggiore 9.7 (Ricercatori EPR / RTT), sopra la
# soglia di 8. A vista normale le due coppie più debolli sono Professori / Ricercatori
# univ. a 10.9 e Ricercatori EPR / RTT a 12.4, sotto la soglia categoriale di 15 - che
# una rampa a una tinta non puo' rispettare per costruzione. Per questo ogni fascia
# porta l'etichetta scritta dentro: l'identità non è mai solo-colore.
STACK = [("phd_teste",       "Dottorandi",          "#3f2560"),   # viola = università
         ("postdoc_teste",   "Postdoc univ.",       "#623f88"),
         ("epr_precari",     "Postdoc EPR",         "#720a3b"),   # cremisi = EPR
         ("rtt_teste",       "RTT",                 "#825ba9"),
         ("epr_ruolo",       "Ricercatori EPR",     "#ae3970"),
         ("ric_uni_teste",   "Ricercatori univ.",   "#a17ec6"),
         ("prof_teste",      "Professori (PO/PA)",  "#c0a3da")]

# Grafico di spesa: DUE ENTITà CATEGORIALI (rami di bilancio), non stadi ordinati,
# quindi due tinte e non una rampa. Palette distinta da STACK perchè l'oggetto è
# diverso: li' sono persone, qui sono euro.
# Verificato sulle coppie che si TOCCANO nel disegno: i due riempimenti fra loro stanno
# a ΔE 17.1 a vista normale e 14.5 in CVD; la linea di totale (colore dello scenario)
# contro la fascia EPR che le sta sotto, 21.8 col verde, 27.0 col blu, 27.9 con
# l'arancio. Il test all-pairs segnala il verde di PAL contro il verde università
# (8.5), ma quelle due marche non sono mai adiacenti: l'università è la fascia in
# basso, la linea di totale sta in cima, separate dall'intera banda EPR.
# Quarto campo: la stessa dizione per esteso, ma mandata a capo, per la scrittura
# DENTRO la fascia. Su una riga non entrerebbe nella finestra piatta disponibile.
SPESA = [("dStato_univ_mld", "Università (uscita)", "#249F2F", " "),
         ("dStato_epr_mld",  "Enti pubblici di ricerca (uscita)", "#4f6410",
          " ")]

# Terza fascia: l'IRPEF che quegli stipendi riversano. Disegnata SOTTO LO ZERO, con
# valori negativi, perchè è un flusso di segno opposto a quello delle altre due: quelle
# sono denaro che esce, questa è denaro che rientra. Impilarla sopra la farebbe leggere
# come un costo aggiuntivo; scavarla dentro la spesa la nasconderebbe dentro un ramo di
# bilancio a cui non appartiene. Sotto l'asse è l'unica posizione che dice da sola cosa
# è, senza bisogno della legenda.
# La lettura del disegno diventa allora quella di un saldo: sopra lo zero il costo
# LORDO, sotto il rientro, e il costo NETTO è la differenza fra le due aree - resa
# esplicita dalla linea tratteggiata dentro lo stack, che sta al livello del netto.
#
# Il colore sta fuori dalle due tinte verdi dei rami di bilancio: non è un terzo ramo
# di spesa, è un'altra specie di grandezza, e il colore lo deve dire prima
# dell'etichetta. Sotto lo zero la fascia non ha vicini, quindi la coppia che conta è
# contro il fondo pagina: ΔE2000 35.6. Contro il verde università, che le sta di fronte
# attraverso l'asse, 34.1. Lo stesso colore torna sulla linea tratteggiata del netto,
# che invece sta DENTRO il verde (34.1, sopra i 22.3 che i due verdi hanno fra loro) e
# corre staccata dalla linea di totale dello scenario (23.9 nel caso peggiore, il blu).
SPESA_IRPEF = ("dIRPEF_mld", "Tassazione sul reddito (entrata)", "#29c29c",
               " ")


def grafico_trend(dfs: dict[str, pd.DataFrame], fine: int, path: str,
            titolo: str | None = None) -> None:
    pann = [("densita", "Densità università (FTE/100k)"),
            # 'ruolo' = PO/PA + ricercatori univ.: negli scenari con la quota-ricercatori
            # non sono tutti docenti, quindi l'etichetta non dice "docenti"
            ("ruolo_teste", "Personale di ruolo, PO/PA + ric. (teste)"),
            ("postdoc_teste", "Postdoc università (teste)"),
            ("rtt_teste", "RTT (teste)"),
            ("phd_fuori_accademia", "Dottori/anno fuori accademia (eccedenza)"),
            ("epr_ruolo", "EPR di ruolo (teste)"),
            ("W_paghe", "Moltiplicatore paghe W"),
            ("HERD_%PIL", "HERD (% PIL)"),
            ("GOVERD_%PIL", "GOVERD (% PIL)"),
            # quarta riga: il personale TA, che fino al 2026 stava solo dentro il
            # residuo SUPPORTO e non era rappresentabile
            ("ta_fte", "Personale TA, univ.+enti (FTE)"),
            ("quota_ta", "Quota TA sul personale R&S"),
            ("densita_rs_tot", "Densità personale R&S tot. (FTE/100k)"),
            # quinta riga: il lato DIDATTICA. Le stesse persone dei pannelli sopra,
            # pesate col complemento della quota-ricerca invece che con la quota-ricerca.
            ("fte_didattico", "Docenti (FTE didattici)"),
            ("stud_per_doc", "Studenti per docente (FTE)")]
    fig, axes = plt.subplots(5, 3, figsize=(13.5, 17.2), facecolor="#fcfcfb")
    for ax, (col, tit) in zip(axes.ravel(), pann):
        # spessore decrescente: dove le serie COINCIDONO (EPR, W) restano tutte
        # visibili come bande concentriche invece di nascondersi a vicenda
        for sp, (nome, df) in zip((3.4, 2.2, 1.3), dfs.items()):
            d = df[df["anno"] <= fine]
            ax.plot(d["anno"], d[col], lw=sp, color=PAL[nome],
                    label=nome.replace("_", " "), solid_capstyle="round")
        # la nota "identico" ha senso solo se ci sono più scenari da confrontare
        coincide = len(dfs) > 1 and all(
            np.allclose(df[df["anno"] <= fine][col],
                        list(dfs.values())[0][lambda x: x["anno"] <= fine][col])
            for df in dfs.values())
        ax.set_title(tit + (f"  (identico nei {len(dfs)} scenari)" if coincide else ""),
                     fontsize=10, color=INK, loc="left", pad=8)
        ax.yaxis.set_major_formatter(
            plt.FuncFormatter(lambda v, _: f"{v:,.0f}" if abs(v) >= 1000 else f"{v:g}"))
        if col == "GOVERD_%PIL":                    # riferimento: obiettivo dichiarato
            ax.axhline(C.GOVERD_TGT, lw=1.2, ls=(0, (4, 3)), color=MUTED)
            ax.annotate(f"obiettivo {C.GOVERD_TGT:g}%", (C.ANNO0 + 1, C.GOVERD_TGT),
                        textcoords="offset points", xytext=(0, -11),
                        fontsize=8, color=INK2)
        if col == "stud_per_doc":              # riferimento: la media europea
            ax.axhline(C.STUD_DOC_TGT, lw=1.2, ls=(0, (4, 3)), color=MUTED)
            ax.annotate(f"media UE {C.STUD_DOC_TGT:g}", (C.ANNO0 + 1, C.STUD_DOC_TGT),
                        textcoords="offset points", xytext=(0, -11),
                        fontsize=8, color=INK2)
        if col == "HERD_%PIL":
            ax.axhline(C.HERD_TGT, lw=1.2, ls=(0, (4, 3)), color=MUTED)
            ax.annotate(f"obiettivo ERA {C.HERD_TGT:g}%", (C.ANNO0 + 1, C.HERD_TGT),
                        textcoords="offset points", xytext=(0, -11),
                        fontsize=8, color=INK2)
        ax.grid(True, lw=0.6, color=GRID)
        ax.set_axisbelow(True)
        ax.tick_params(labelsize=8, colors=MUTED, length=0)
        for lato in ("top", "right"):
            ax.spines[lato].set_visible(False)
        for lato in ("left", "bottom"):
            ax.spines[lato].set_color("#c3c2b7")
        if col in ("densita", "ruolo_teste", "postdoc_teste", "rtt_teste",
                   "phd_fuori_accademia", "epr_ruolo", "phd_teste", "ta_fte",
                   "quota_ta", "densita_rs_tot", "fte_didattico", "stud_per_doc"):
            ax.set_ylim(bottom=0)      # conteggi di persone: baseline sempre a zero
        ax.set_facecolor("#fcfcfb")
    # la griglia ha più caselle dei pannelli: quelle in eccesso vanno spente, altrimenti
    # restano cornici vuote con la sola griglia disegnata
    for ax in axes.ravel()[len(pann):]:
        ax.set_visible(False)
    # una sola legenda per l'intera figura: l'identità non è mai solo-colore.
    # Con una serie sola la legenda non serve: è il titolo a nominarla.
    if len(dfs) > 1:
        axes[0][0].legend(fontsize=8.5, frameon=False, labelcolor=INK2, loc="upper left")
    fig.suptitle(titolo or f"Transizione {C.ANNO0}-{fine}: università ed EPR a confronto",
                 fontsize=12.5, color=INK, x=0.008, ha="left", y=0.995)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(path, dpi=140, facecolor="#fcfcfb")
    plt.close(fig)


def grafico_target(dfs: dict[str, pd.DataFrame], target: dict[str, float],
                   etich: dict[str, str], path: str) -> None:
    """Due pannelli di sintesi: densità contro le righe di target, e budget aggiuntivo.
    Stava dentro main() come figura inline; qui sta con gli altri disegni, e main()
    torna a fare solo orchestrazione."""
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.6))
    for nome, df in dfs.items():
        # qui la densità a popolazione FISSA, perchè il pannello ha le righe di target
        ax[0].plot(df["anno"], df["densita_pop2026"], label=etich[nome])
        ax[0].axhline(target[nome], ls=":", lw=0.6, color="grey")
        ax[1].plot(df["anno"], df["dBudget_%PIL"], label=etich[nome])
    ax[0].axhline(C.DENS_OGGI, ls="--", lw=0.8, color="black")
    ax[0].set_title(f"Densità FTE/100k a pop. 2026 fissa (precari_anni={C.PRECARI_ANNI})")
    ax[0].set_xlabel("anno"); ax[0].legend(fontsize=8)
    ax[1].set_title("Budget pubblico aggiuntivo (% PIL)")
    ax[1].set_xlabel("anno"); ax[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def rs_pubblica_oggi_mld() -> float:
    """Spesa in R&S pubblica dell'anno 0, in miliardi: HERD + GOVERD osservati.

    È il metro con cui si leggono gli incrementi di spesa. Un "+13 mld/anno" da solo
    non dice nulla; "+13 mld = +106% di quello che l'Italia spende oggi in ricerca
    pubblica" dice tutto. Ricalcolata dalle costanti, così segue HERD_OGGI e PIL_MLN
    se vengono aggiornati."""
    return (C.HERD_OGGI + C.GOVERD_OGGI) / 100 * C.PIL_MLN / 1000


def _tick_mld_pct(v: float, _pos=None) -> str:
    """Etichetta dell'asse della spesa: miliardi e, fra parentesi, la stessa cifra come
    quota della R&S pubblica di oggi. Le due letture stanno sulla stessa tacca perchè
    sono lo stesso numero in due unità, non due serie da confrontare."""
    base = rs_pubblica_oggi_mld()
    return f"{v:g} ({v / base * 100:.0f}%)" if base else f"{v:g}"


def grafico_ffo(dfs: dict[str, pd.DataFrame], fine: int, path: str,
                titolo: str | None = None) -> None:
    """Maggior fabbisogno annuo a carico dello Stato, in miliardi. PROXY dell'FFO
    aggiuntivo: il modello non ha l'FFO come voce di bilancio (vedi README)."""
    pann = [("dStato_univ_mld", "Università (mld EUR/anno)"),
            ("dStato_epr_mld", "EPR - dotazione aggiuntiva (mld EUR/anno)"),
            (None, "Totale ricerca pubblica (mld EUR/anno)")]
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.4), facecolor="#fcfcfb")
    for ax, (col, tit) in zip(axes, pann):
        for sp, (nome, df) in zip((3.4, 2.2, 1.3), dfs.items()):
            d = df[df["anno"] <= fine]
            y = (d["dStato_univ_mld"] + d["dStato_epr_mld"]) if col is None else d[col]
            ax.plot(d["anno"], y, lw=sp, color=PAL[nome],
                    label=nome.replace("_", " "), solid_capstyle="round")
            ax.annotate(f"{y.iloc[-1]:.1f}", (d["anno"].iloc[-1], y.iloc[-1]),
                        textcoords="offset points", xytext=(4, 0), fontsize=8.5,
                        color=INK2, va="center")
            # Solo sul pannello del TOTALE: la stessa curva al netto dell'IRPEF che
            # quegli stipendi in più pagano. Tratteggiata e nello stesso colore
            # perchè non è un'altra grandezza, è la stessa vista al netto: la
            # distanza fra le due linee È il retroflusso. Sui due pannelli di
            # sinistra non ha senso, il retroflusso non si spacca per capitolo.
            if col is None:
                ax.plot(d["anno"], d["dStato_netto_irpef_mld"], lw=sp * 0.62,
                        color=PAL[nome], ls=(0, (4, 2.2)), solid_capstyle="round")
        ax.axhline(0, lw=1.0, color="#c3c2b7")
        ax.set_title(tit, fontsize=10, color=INK, loc="left", pad=8)
        ax.grid(True, lw=0.6, color=GRID)
        ax.set_axisbelow(True)
        # ogni tacca porta anche la quota della R&S pubblica di oggi
        ax.yaxis.set_major_formatter(plt.FuncFormatter(_tick_mld_pct))
        ax.tick_params(labelsize=8, colors=MUTED, length=0)
        for lato in ("top", "right"):
            ax.spines[lato].set_visible(False)
        for lato in ("left", "bottom"):
            ax.spines[lato].set_color("#c3c2b7")
        ax.set_facecolor("#fcfcfb")
        ax.margins(x=0.10)
    if len(dfs) > 1:      # con una serie sola è il titolo a nominarla
        axes[0].legend(fontsize=8.5, frameon=False, labelcolor=INK2, loc="upper left")
    # legenda dello STILE, non del colore: sul terzo pannello ogni scenario compare due
    # volte, lordo e netto, e sono i tratti a distinguerli
    axes[2].legend(handles=[plt.Line2D([], [], color=MUTED, lw=2.4, label="lordo"),
                            plt.Line2D([], [], color=MUTED, lw=1.6, ls=(0, (4, 2.2)),
                                       label="netto IRPEF")],
                   fontsize=8.5, frameon=False, labelcolor=INK2, loc="upper left")
    fig.suptitle(titolo or "Maggior fabbisogno annuo rispetto a oggi (EUR2026 costanti)",
                 fontsize=12.5, color=INK, x=0.006, ha="left", y=0.99)
    fig.text(0.006, 0.945, f"Sulle tacche: mld EUR/anno e, fra parentesi, la stessa "
             f"cifra come quota della R&S pubblica del {C.ANNO0} "
             f"(HERD+GOVERD = {rs_pubblica_oggi_mld():.1f} mld).\nNel terzo pannello il "
             f"tratteggio è lo stesso fabbisogno al netto della sola IRPEF che i nuovi "
             f"stipendi versano: la distanza fra le due linee è il retroflusso.",
             fontsize=8.5, color=INK2, ha="left", va="top")
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    fig.savefig(path, dpi=140, facecolor="#fcfcfb")
    plt.close(fig)


def _ink_su(hex_fondo: str) -> str:
    """Inchiostro per un'etichetta scritta DENTRO una fascia colorata: chiaro sui
    riempimenti scuri, scuro su quelli chiari. Deciso dalla luminanza relativa della
    fascia, non dalla sua posizione nello stack: con due rampe la posizione non dice
    più quanto è scura. Soglia 0,35 = punto in cui i due contrasti si pareggiano."""
    r, g, b = (int(hex_fondo[i:i + 2], 16) / 255 for i in (1, 3, 5))
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in (r, g, b)]
    lum = 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]
    return "#fcfcfb" if lum < 0.35 else INK


def _posa_etichetta(anni: np.ndarray, basso: np.ndarray, alto: np.ndarray,
                    ytop: float, nchar: int, soglia: float) -> tuple[float, float] | None:
    """Dove scrivere un'etichetta DENTRO una fascia di uno stackplot, oppure None se
    non ci sta da nessuna parte.

    Non basta il punto più SPESSO: il testo si estende in orizzontale, e dove la
    fascia sale o scende le sue estremità escono - sopra la linea di totale il fondo
    è pagina, e l'inchiostro chiaro diventa invisibile. Quindi si massimizza lo
    spessore UTILE: l'intersezione della fascia su una finestra larga quanto il testo.
    Restituisce (anno, y) del centro."""
    n = len(anni)
    # mezza larghezza del testo in anni: ~0,46 anni per carattere a fontsize 8.5 su
    # un pannello tipico di questa figura, con un minimo di 3 per le etichette corte.
    # Il margine è volutamente generoso: serve anche a tenere il testo staccato dai
    # bordi del pannello, non solo dentro la fascia.
    w = max(3, int(nchar * 0.46))
    if n <= 2 * w + 1:
        return None
    # i centri candidati stanno a distanza >= w dai bordi: la finestra è sempre piena
    # (altrimenti ai bordi si accorcia, l'intersezione risulta più larga e vince
    # sempre l'estremità, mandando il testo fuori dal pannello)
    best = (-1.0, w, 0.0)
    for i in range(w, n - w):
        y_lo, y_hi = basso[i - w:i + w + 1].max(), alto[i - w:i + w + 1].min()
        if y_hi - y_lo > best[0]:
            best = (y_hi - y_lo, i, (y_lo + y_hi) / 2)
    if best[0] < soglia * ytop:
        return None
    return anni[best[1]], best[2]


def _posa_ripiego(anni: np.ndarray, basso: np.ndarray, alto: np.ndarray,
                  nchar: int) -> tuple[float, float]:
    """Posizione per una fascia TROPPO SOTTILE per contenere il suo testo: il punto più
    spesso, e il testo sborderà sulle fasce vicine. Serve quando la legenda non c'è e
    ogni fascia deve comunque essere nominata; la leggibilità la garantisce l'alone,
    non lo spessore (vedi _scrivi_in_fascia)."""
    # stesso margine dai bordi di _posa_etichetta, cosi' il testo non tocca le cornici;
    # cambia solo il criterio: spessore grezzo invece dell'intersezione su finestra,
    # perchè qui l'intersezione è comunque troppo piccola per contenere il testo
    w = max(3, int(nchar * 0.46)) + 1
    n = len(anni)
    a = min(w, n - 1)
    b = max(n - w, a + 1)
    spess = alto - basso
    i = a + int(np.argmax(spess[a:b]))
    return anni[i], (basso[i] + alto[i]) / 2


def _scrivi_in_fascia(ax, testo: str, posa: tuple[float, float], col: str,
                      sborda: bool) -> None:
    """Etichetta dentro una fascia. Se sborda sulle vicine le si mette un alone del
    colore della fascia stessa: il testo resta leggibile e si legge come appartenente
    alla striscia, non a quelle che invade."""
    eff = ([pe.withStroke(linewidth=2.6, foreground=col)] if sborda else None)
    ax.annotate(testo, posa, fontsize=8.5, ha="center", va="center",
                linespacing=1.35, color=_ink_su(col), path_effects=eff, zorder=7)


def grafico_stack(dfs: dict[str, pd.DataFrame], fine: int, path: str,
                  etich: dict[str, str] | None = None) -> None:
    """Composizione dell'organico della RICERCA PUBBLICA in teste, un pannello per
    scenario. Le fasce sono ordinate per STADIO DI CARRIERA e le due famiglie di colore
    si interlacciano: viola = università (dottorandi -> professori), cremisi = EPR
    (postdoc e ruolo). La tinta dice quindi il settore contabile - HERD contro GOVERD -
    e la luminosità lo stadio dentro il settore.
    La linea di totale in cima allo stack porta il colore che lo scenario ha in tutti
    gli altri grafici; la tratteggiata grafite è la densità FTE/100k sull'asse
    destro."""
    etich = etich or {n: n.replace("_", " ") for n in dfs}
    # con un solo pannello la larghezza minima è dettata dalla legenda, non dal grafico
    fig, axes = plt.subplots(1, len(dfs), figsize=(max(9.0, 5.2 * len(dfs)), 5.4),
                             facecolor="#fcfcfb", sharey=True)
    # asse y comune e IMPOSTO sul massimo degli scenari passati: con sharey
    # l'autoscale dell'ultimo pannello troncherebbe i totali più alti (ERA).
    ytop = max(_teste_tot(df[df["anno"] <= fine]).max() for df in dfs.values()) * 1.06
    for ax, (nome, df) in zip(np.atleast_1d(axes), dfs.items()):
        d = df[df["anno"] <= fine].copy()
        # 'docentè nel modello è la coorte PO/PA; i ricercatori universitari sono
        # una coorte distinta di ruolo, quindi vanno scorporati per non contarli due volte.
        d["prof_teste"] = d["ruolo_teste"] - d["ric_uni_teste"]
        # la fascia ricercatori compare SOLO negli scenari che prevedono la figura
        voci = [(c, lab, col) for c, lab, col in STACK if d[c].max() > 1.0]
        y = np.vstack([d[c].to_numpy() for c, _, _ in voci])
        cum = np.cumsum(y, axis=0)
        # linewidth su fondo pagina = il distacco di 2px fra le fasce contigue
        ax.stackplot(d["anno"], y, colors=[col for _, _, col in voci],
                     labels=[lab for _, lab, _ in voci],
                     edgecolor="#fcfcfb", linewidth=0.9)
        ax.plot(d["anno"], cum[-1], lw=2.4, color=PAL[nome],
                solid_capstyle="round", zorder=5)
        # Etichette dirette su OGNI fascia. Qui non è una scelta di stile: la legenda
        # delle fasce non c'è, quindi se una striscia resta senza nome non è
        # identificabile in nessun modo. Le fasce sottili prendono la posizione di
        # ripiego e l'alone, e il testo sborderà sulle vicine.
        basso = np.vstack([np.zeros(len(d)), cum[:-1]])
        anni = d["anno"].to_numpy()
        for k, (_, lab, col) in enumerate(voci):
            posa = _posa_etichetta(anni, basso[k], cum[k], ytop, len(lab), 0.042)
            _scrivi_in_fascia(ax, lab,
                              posa or _posa_ripiego(anni, basso[k], cum[k], len(lab)),
                              col, sborda=posa is None)
        ax.set_title(etich[nome], fontsize=10, color=INK, loc="left", pad=8)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:,.0f}"))
        ax.grid(True, axis="y", lw=0.6, color=GRID)
        ax.set_axisbelow(True)
        ax.tick_params(labelsize=8, colors=MUTED, length=0)
        for lato in ("top", "right"):
            ax.spines[lato].set_visible(False)
        for lato in ("left", "bottom"):
            ax.spines[lato].set_color("#c3c2b7")
        ax.set_facecolor("#fcfcfb")
        ax.set_xlim(d["anno"].iloc[0], d["anno"].iloc[-1])
        ax.set_ylim(0, ytop)
        # --- densita FTE/100k su asse DESTRO ---
        # Secondo asse y: normalmente da evitare, ma qui le due grandezze sono la
        # stessa cosa contata in due modi (posizioni vs FTE su popolazione SSP2), e il
        # confronto internazionale si fa in FTE/100k. Per non farlo passare per una
        # serie dello stack: grafite tratteggiata, nessuna tinta della palette, e
        # tacche e titolo dell'asse dello stesso inchiostro della linea.
        axr = ax.twinx()
        axr.plot(d["anno"], d["densita"], lw=1.8, ls=(0, (5, 2.5)), color=INK,
                 zorder=6, label="Densità FTE/100k (asse destro)")
        axr.set_ylim(0, max(df[df["anno"] <= fine]["densita"].max()
                            for df in dfs.values()) * 1.10)
        axr.tick_params(labelsize=8, colors=INK, length=0)
        axr.set_facecolor("none")
        for lato in ("top", "left", "bottom"):
            axr.spines[lato].set_visible(False)
        axr.spines["right"].set_color("#c3c2b7")
        # la scala destra è la stessa in tutti i pannelli: tacche e titolo solo
        # sull'ultimo, come fa sharey per l'asse sinistro
        if ax is np.atleast_1d(axes)[-1]:
            axr.set_ylabel("Densità FTE per 100k abitanti (pop. SSP2)", fontsize=8.5,
                           color=INK)
        else:
            axr.set_yticklabels([])
    ass = np.atleast_1d(axes)
    ass[0].set_ylabel("Numero Posizioni", fontsize=8.5, color=INK2)
    # In legenda SOLO la linea dell'asse destro: le fasce sono tutte nominate dentro il
    # grafico, quindi ripeterle in legenda sarebbe ridondante. La tratteggiata invece va
    # dichiarata, perchè è l'unica marca che legge su un'altra scala.
    h_fte = plt.Line2D([], [], lw=1.8, ls=(0, (5, 2.5)), color=INK)
    fig.legend([h_fte], ["Densità FTE per 100k abitanti (asse destro)"], fontsize=8.5,
               frameon=False, labelcolor=INK2, loc="lower center",
               bbox_to_anchor=(0.5, -0.005))
    fig.suptitle(f"Composizione dell'organico della ricerca pubblica, {C.ANNO0}-{fine} "
                 "(posizioni)", fontsize=12.5, color=INK, x=0.006, ha="left", y=0.995)
    # su una figura strettta (un pannello solo) il sottotitolo va su due righe, altrimenti
    # esce dal bordo destro
    stretta = fig.get_figwidth() < 12
    fig.text(0.006, 0.95, "Viola = università (spesa HERD), cremisi = enti pubblici di "
             "ricerca (spesa GOVERD);"
             + ("\n" if stretta else " ")
             + "le fasce sono ordinate per stadio di carriera. La linea in cima allo "
               "stack è il totale.",
             fontsize=8.5, color=INK2, ha="left", va="top", linespacing=1.4)
    fig.tight_layout(rect=(0, 0.055, 1, 0.90 if stretta else 0.92))
    fig.savefig(path, dpi=140, facecolor="#fcfcfb")
    plt.close(fig)


def grafico_spesa_stack(dfs: dict[str, pd.DataFrame], fine: int, path: str,
                        etich: dict[str, str] | None = None) -> None:
    """VARIAZIONE della spesa pubblica per la ricerca rispetto al 2026, con i due rami
    di bilancio impilati: università e EPR. Parte da zero per costruzione - il livello
    assoluto della baseline 2026 resta fuori dal grafico.
    (I livelli assoluti sono comunque nei CSV, colonne budget_univ_mld e
    budget_epr_mld, se serve rimetterli.)

    Sotto lo zero, in negativo, l'IRPEF che quegli stipendi riversano: è un flusso di
    segno opposto e sta dalla parte opposta dell'asse. Il grafico si legge allora come
    un saldo - lordo sopra, rientro sotto, netto la differenza - e il netto è anche
    disegnato, come tratteggio dentro lo stack. Vedi SPESA_IRPEF per il perchè."""
    etich = etich or {n: n.replace("_", " ") for n in dfs}
    fig, axes = plt.subplots(1, len(dfs), figsize=(max(8.6, 5.0 * len(dfs)), 5.0),
                             facecolor="#fcfcfb", sharey=True)
    ytop = max((df[df["anno"] <= fine][[c for c, _, _, _ in SPESA]].sum(axis=1)).max()
               for df in dfs.values()) * 1.10
    # margine sotto lo zero: il 35% in più del rientro massimo, che è lo spazio per
    # scriverci dentro l'etichetta senza che tocchi il bordo inferiore
    ybot = -max(df[df["anno"] <= fine][SPESA_IRPEF[0]].max()
                for df in dfs.values()) * 1.35
    span = ytop - ybot
    for ax, (nome, df) in zip(np.atleast_1d(axes), dfs.items()):
        d = df[df["anno"] <= fine]
        y = np.vstack([d[c].to_numpy() for c, _, _, _ in SPESA])
        cum = np.cumsum(y, axis=0)
        # il rientro non è mai negativo per costruzione, ma il clip lo garantisce anche
        # se il fisco cambiasse segno in qualche configurazione di parametri
        irp = np.clip(d[SPESA_IRPEF[0]].to_numpy(), 0.0, None)
        ax.stackplot(d["anno"], y, colors=[col for _, _, col, _ in SPESA],
                     labels=[lab for _, lab, _, _ in SPESA],
                     edgecolor="#fcfcfb", linewidth=0.9)
        ax.fill_between(d["anno"], 0.0, -irp, color=SPESA_IRPEF[2],
                        label=SPESA_IRPEF[1], edgecolor="#fcfcfb", linewidth=0.9)
        ax.plot(d["anno"], cum[-1], lw=2.4, color=PAL[nome],
                solid_capstyle="round", zorder=5)
        # il NETTO, cioè il saldo fra le due aree. Tratteggiato e nel colore del
        # rientro perchè è il rientro a produrlo: la distanza fra questa linea e quella
        # di totale è, punto per punto, la profondità della fascia sotto lo zero.
        # il contorno è un path effect e non un edgecolor: le linee non hanno bordo,
        # si stroka il tratto stesso in bianco sotto al colore. Sul tratteggio l'alone
        # segue i singoli trattini, che è quello che serve per staccarli dallo stack
        ax.plot(d["anno"], cum[-1] - irp, lw=1.5, color=PAL[nome],
                ls=(0, (4, 2.2)), solid_capstyle="round", zorder=6,
                path_effects=[pe.withStroke(linewidth=2.5, foreground="#fcfcfb")])
        # lo zero non è più una cornice ma la linea di separazione fra i due segni,
        # quindi porta più inchiostro delle altre
        ax.axhline(0, lw=1.4, color="#8a8981", zorder=7)
        # i valori portano inchiostro di testo, non il colore della serie - tranne
        # quelli del retroflusso, che sono l'eccezione perchè lì il colore È l'etichetta
        ax.annotate(f"Lordo +{cum[-1][-1]:.1f} Mld EUR", (d["anno"].iloc[-1], cum[-1][-1]),
                    textcoords="offset points", xytext=(-2, 16), fontsize=9.5,
                    color=INK, ha="right")
        # alone: questa etichetta cade DENTRO la fascia universitaria, e il colore del
        # retroflusso sul verde regge ma non è brillante (ΔE2000 34.1). L'alone la
        # stacca dal fondo senza doverle cambiare colore - e il colore qui è
        # informazione, dice che il numero appartiene al retroflusso e non alla spesa
        ax.annotate(f"Netto +{cum[-1][-1] - irp[-1]:.1f} Mld EUR",
                    (d["anno"].iloc[-1], cum[-1][-1] - irp[-1]),
                    textcoords="offset points", xytext=(-3, -4), fontsize=8.5,
                    color=INK, ha="right", va="top", zorder=8,
                    path_effects=[pe.withStroke(linewidth=2.6, foreground="#fcfcfb")])
        ax.annotate(f"Tasse -{irp[-1]:.1f} Mld EUR", (d["anno"].iloc[-1], -irp[-1]),
                    textcoords="offset points", xytext=(-2, -3), fontsize=8.5,
                    color=INK, ha="right", va="top")
        # il picco non coincide col valore a regime: l'onda dei pensionamenti lo alza
        # per una ventina d'anni, ed è il numero che conta per la programmazione
        kp = int(np.argmax(cum[-1]))
        # if cum[-1][kp] > cum[-1][-1] * 1.03:
        #    ax.annotate(f"Picco +{cum[-1][kp]:.1f} ({d['anno'].iloc[kp]})",
        #                (d["anno"].iloc[kp], cum[-1][kp]), textcoords="offset points",
        #                xytext=(0, 9), fontsize=8.5, color=INK2, ha="center")
        # etichette dirette dentro le fasce, come nello stack dell'organico. La fascia
        # del rientro entra nella stessa lista con estremi (-irp, 0): sotto lo zero il
        # criterio di posa non cambia, è sempre "dove la fascia è più spessa su una
        # finestra larga quanto il testo". La soglia è però sull'intero SPAN della
        # figura, non sul solo ytop, altrimenti la parte sotto lo zero non conterebbe.
        anni = d["anno"].to_numpy()
        estremi = [(np.zeros(len(d)), cum[0]), (cum[0], cum[1]), (-irp, np.zeros(len(d)))]
        for (lo, hi), (_, _, col, dentro) in zip(estremi, [*SPESA, SPESA_IRPEF]):
            # la larghezza che conta è quella della riga più lunga, non del testo
            nch = max(len(r) for r in dentro.splitlines())
            posa = _posa_etichetta(anni, lo, hi, span, nch, 0.055)
            if posa is None:
                continue
            ax.annotate(dentro, posa, fontsize=8.5, ha="center", va="center",
                        linespacing=1.35, color=_ink_su(col))
        ax.set_title(etich[nome], fontsize=10, color=INK, loc="left", pad=8)
        ax.grid(True, axis="y", lw=0.6, color=GRID)
        ax.set_axisbelow(True)
        # ogni tacca porta anche la quota della R&S pubblica di oggi
        ax.yaxis.set_major_formatter(plt.FuncFormatter(_tick_mld_pct))
        ax.tick_params(labelsize=8, colors=MUTED, length=0)
        for lato in ("top", "right"):
            ax.spines[lato].set_visible(False)
        for lato in ("left", "bottom"):
            ax.spines[lato].set_color("#c3c2b7")
        ax.set_facecolor("#fcfcfb")
        ax.set_xlim(d["anno"].iloc[0], d["anno"].iloc[-1])
        ax.set_ylim(ybot, ytop)
    ass = np.atleast_1d(axes)
    ass[0].set_ylabel("Mld EUR/anno in più rispetto ad oggi (EUR2026)\n",
                      fontsize=8.5, color=INK2)
    h, l = ass[0].get_legend_handles_labels()
    fig.legend(h[::-1], l[::-1], fontsize=8.5, frameon=False, labelcolor=INK2,
               loc="lower center", ncol=len(l), bbox_to_anchor=(0.5, -0.005))
    # titolo su due righe: una riga sola sfora la figura strettta a un pannello
    fig.suptitle(f"Fondi per la ricerca pubblica: variazione annua rispetto al {C.ANNO0}, "
                 "per ramo di bilancio",
                 fontsize=12.5, color=INK, x=0.006, ha="left", y=0.995)
    # come nello stack dell'organico: su una figura stretta (un pannello solo) il
    # sottotitolo va spezzato, altrimenti esce dal bordo destro
    stretta = fig.get_figwidth() < 12
    fig.tight_layout(rect=(0, 0.06, 1, 0.895 if stretta else 0.915))
    fig.savefig(path, dpi=140, facecolor="#fcfcfb")
    plt.close(fig)


def grafici_singolo(nome: str, dfs: dict[str, pd.DataFrame], fine: int, out: str,
                    etich: dict[str, str]) -> list[str]:
    """Gli stessi grafici, ma per UN SOLO scenario, su file separati. Utile per
    metterlo in una slide o in un documento senza il confronto a fianco: le serie
    degli altri due scenari, li', sono rumore."""
    solo = {nome: dfs[nome]}
    lab = etich.get(nome, nome.replace("_", " "))
    file = {"trend":  f"{out}/{nome}_trend.png",
            "ffo":    f"{out}/{nome}_ffo.png",
            "stack":  f"{out}/{nome}_organico.png",
            "spesa":  f"{out}/{nome}_spesa.png"}
    grafico_trend(solo, fine, file["trend"],
            titolo=f"Scenario {lab}: transizione {C.ANNO0}-{fine}")
    grafico_ffo(solo, fine, file["ffo"],
                titolo=f"Scenario {lab}: maggior fabbisogno annuo rispetto a oggi "
                       "(EUR2026 costanti)")
    grafico_stack(solo, fine, file["stack"], etich)
    grafico_spesa_stack(solo, fine, file["spesa"], etich)
    return list(file.values())
