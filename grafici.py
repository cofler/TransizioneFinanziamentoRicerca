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
from regime import anni_da_associato_tgt

# ============================ REPORT 2026-2050 ==============================
# Palette: primi tre slot della palette di riferimento (validati all-pairs).
PAL = {"ADI_Manifesto_ric": "#2a78d6", "ERA": "#eb6834", "FLC": "#1baf7a"}
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
#
# I PROFESSORI SONO DUE FASCE, non una: associati e ordinari. Il passo in più si
# aggiunge IN CIMA alla rampa e non la ricalibra - gli associati tengono il colore che
# la fascia unica aveva prima (#c0a3da), quindi tutte le coppie preesistenti restano
# quelle già validate, e la sola coppia nuova è associati/ordinari. Verificata come le
# altre: ΔE2000 12.3 a vista normale, 9.1 in deutan e 9.8 in protan, sopra la soglia di
# 8 che vale per le coppie adiacenti di una rampa a una tinta. Gli ordinari sono il
# passo più chiaro (L* 85.6) ma non confinano con la pagina: sopra di loro corre sempre
# la linea di totale, che porta il colore dello scenario.
STACK = [("phd_teste",       "Dottorandi",            "#3f2560"),  # viola = università
         ("postdoc_teste",   "Postdoc univ.",         "#623f88"),
         ("epr_precari",     "Postdoc EPR",           "#720a3b"),  # cremisi = EPR
         ("rtt_teste",       "RTT",                   "#825ba9"),
         ("epr_ruolo",       "Ricercatori EPR",       "#ae3970"),
         ("ric_uni_teste",   "Ricercatori univ.",     "#a17ec6"),
         ("pa_teste",        "Professori associati",  "#c0a3da"),
         ("po_teste",        "Professori ordinari",   "#e0d0f0")]

# Grafico di spesa: ENTITà CATEGORIALI (voci di bilancio), non stadi ordinati,
# quindi tinte distinte e non una rampa. Palette distinta da STACK perchè l'oggetto è
# diverso: li' sono persone, qui sono euro.
# Verificato sulle coppie che si TOCCANO nel disegno: i due riempimenti VERDI fra loro
# stanno a ΔE 17.1 a vista normale e 14.5 in CVD; la linea di totale (colore dello
# scenario) contro la fascia che le sta sotto - che ora è la prugna, non più la fascia
# EPR - 34.2 col verde, 19.9 col blu, 27.6 con l'arancio, e in CVD 22.2 / 12.2 / 25.2.
# Il test all-pairs segnala il verde di PAL contro il verde università (8.5), ma quelle
# due marche non sono mai adiacenti: l'università è la fascia in basso, la linea di
# totale sta in cima, separate dalle altre due bande.
#
# LA TERZA FASCIA NON È UN TERZO RAMO DI BILANCIO, ed è per questo che esce dalla
# famiglia verde: i due verdi dicono CHI spende (università, enti), la prugna dice
# COSA si compra - attrezzature invece che stipendi - ed è una spesa che il piano
# decide, non che l'organico impone (vedi PIANO ATTREZZATURE in config). Una terza
# tinta di verde avrebbe detto "terzo ente", che è esattamente la lettura sbagliata.
# Sta IN CIMA perchè è il residuo: le due fasce sotto sono determinate dall'organico
# dell'anno, questa è ciò che resta da riempire per arrivare all'inviluppo.
# Prugna e non un'altra tinta perchè i vincoli lasciano poco: deve stare a ΔE>=15 da
# entrambi i verdi, dal verde acqua dell'IRPEF e dai TRE colori di scenario, che
# occupano già blu, arancio e verde. Il quadrante viola/magenta è quel che avanza.
# Coppie verificate (normale / CVD peggiore): fascia EPR 25.2 / 16.4, fascia
# università 35.7 / 22.5, IRPEF 37.0 / 26.5, e le tre linee di scenario qui sopra.
# Contro pagina il contrasto è 6.9:1, quindi l'inchiostro dentro la fascia è chiaro.
# Quarto campo: la stessa dizione per esteso, ma mandata a capo, per la scrittura
# DENTRO la fascia. Su una riga non entrerebbe nella finestra piatta disponibile.
# Le due fasce di ramo sono le colonne *_pers_mld, cioè AL NETTO del supplemento: il
# supplemento è già dentro dStato_univ_mld e dStato_epr_mld (piano_attrezzature lo
# ripartisce fra i due rami, perchè è spesa R&S e deve stare in HERD e GOVERD), e
# usare quelle qui lo conterebbe due volte - una dentro il verde, una nella prugna.
# Le tre fasce si sommano quindi esattamente a dStato_tot_mld.
SPESA = [("dStato_univ_pers_mld", "Università (uscita)", "#249F2F", " "),
         ("dStato_epr_pers_mld",  "Enti pubblici di ricerca (uscita)", "#4f6410",
          " "),
         ("attrezz_extra_mld", "Attrezzature e infrastrutture (uscita)", "#853a8c",
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
            # gli sbocchi dei dottori come QUOTE del flusso dell'anno, non come teste:
            # il numero assoluto di eccedenti dipende dalla taglia del dottorato, la
            # quota no, e la quota è quello che si confronta fra scenari. Due serie in
            # un pannello solo: hanno lo stesso denominatore, e la distanza fra le due
            # è la parte di flusso che resta nel precariato senza arrivare al ruolo.
            ("quota_phd_postdoc", "Sbocchi dei dottori (quota del flusso annuo)"),
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
            ("stud_per_doc", "Studenti per docente (FTE)"),
            # ultimo slot della griglia: il rapporto che dice se il piano stabilizza
            # davvero. Sta qui e non fra i pannelli di organico perchè non è un
            # conteggio ma un RAPPORTO, e si legge contro il 100 - non contro lo zero.
            # titolo tenuto CORTO di proposito: questo è l'ultimo pannello a destra e
            # il titolo è ancorato a sinistra, quindi tutto ciò che supera la larghezza
            # del pannello esce dalla figura invece di andare a capo. Il limite pratico
            # è ~53 caratteri; il denominatore ci sta, la definizione completa no e sta
            # nel commento alla colonna in motore.py.
            ("componente_precaria",
             "Componente precaria (% su strutturati + postdoc)"),
            # sesta riga: la spesa che NON è personale. Sta fra i pannelli di trend e
            # non solo nello stack di spesa perchè è una quota e le quote si leggono
            # come serie, non come spessore di una fascia dentro un totale che cresce.
            # Orizzonte più corto degli altri (vedi ATTREZZ_QUOTA_FINE in config).
            ("quota_attrezz", "Attrezzature e infrastrutture (% della spesa)")]
    # su un DataFrame che non è passato da piano_attrezzature() la colonna della quota
    # non c'è: il pannello sparisce e la griglia si accorcia da sola, invece di
    # sollevare un KeyError a metà disegno
    pann = [p for p in pann if all(p[0] in df.columns for df in dfs.values())]
    # la griglia si dimensiona sui pannelli: 3 colonne e quante righe servono. Con 16
    # pannelli sono 6 righe, l'ultima con due caselle vuote che il ciclo in coda spegne.
    nrig = -(-len(pann) // 3)
    fig, axes = plt.subplots(nrig, 3, figsize=(13.5, 3.44 * nrig), facecolor="#fcfcfb")
    for ax, (col, tit) in zip(axes.ravel(), pann):
        # non tutti i pannelli arrivano a fine orizzonte: la quota-attrezzature si
        # ferma prima, perchè oltre quell'anno è il prolungamento piatto dell'inviluppo
        fine_p = min(fine, C.ATTREZZ_QUOTA_FINE) if col == "quota_attrezz" else fine
        # spessore decrescente: dove le serie COINCIDONO (EPR, W) restano tutte
        # visibili come bande concentriche invece di nascondersi a vicenda
        for sp, (nome, df) in zip((3.4, 2.2, 1.3), dfs.items()):
            d = df[df["anno"] <= fine_p]
            ax.plot(d["anno"], d[col], lw=sp, color=PAL[nome],
                    label=nome.replace("_", " "), solid_capstyle="round")
            # seconda serie nello stesso pannello: la quota che arriva alla tenure
            # track. Stesso colore (è lo stesso scenario) e tratto spezzato, come nel
            # pannello del fabbisogno netto: a distinguerle è lo stile, non la tinta.
            if col == "quota_phd_postdoc":
                ax.plot(d["anno"], d["quota_phd_rtt"], lw=sp * 0.62, color=PAL[nome],
                        ls=(0, (4, 2.2)), solid_capstyle="round")
        # la nota "identico" ha senso solo se ci sono più scenari da confrontare, e
        # deve guardare TUTTE le serie del pannello: dove ce ne sono due, una sola
        # coincidente non rende identico il disegno
        cols = [col] + (["quota_phd_rtt"] if col == "quota_phd_postdoc" else [])
        coincide = len(dfs) > 1 and all(
            np.allclose(df[df["anno"] <= fine_p][c],
                        list(dfs.values())[0][lambda x: x["anno"] <= fine_p][c])
            for df in dfs.values() for c in cols)
        ax.set_title(tit + (f"  (identico nei {len(dfs)} scenari)" if coincide else ""),
                     fontsize=10, color=INK, loc="left", pad=8)
        ax.yaxis.set_major_formatter(
            plt.FuncFormatter(lambda v, _: f"{v:,.0f}" if abs(v) >= 1000 else f"{v:g}"))
        if col == "quota_phd_postdoc":
            # quote: l'asse va in percentuale, e il pannello porta la sua legenda di
            # STILE - il colore qui dice lo scenario, come ovunque, quindi la coppia
            # di serie non puo' che distinguersi col tratto
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
            ax.legend(handles=[plt.Line2D([], [], color=MUTED, lw=2.4,
                                          label="restano come postdoc (univ.+EPR)"),
                               plt.Line2D([], [], color=MUTED, lw=1.6, ls=(0, (4, 2.2)),
                                          label="entrano in tenure track (RTT+Madia)")],
                      fontsize=8, frameon=False, labelcolor=INK2, loc="upper right")
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
        if col == "quota_ta":
            # asse in percentuale, come per l'altro pannello di quote: qui il riquadro
            # scrive dei valori in %, e una tacca che dicesse 0,21 accanto a un testo che
            # dice 21% farebbe leggere due unità diverse per la stessa grandezza
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
            # estremi della simulazione scritti per esteso. La curva è quasi piatta -
            # a TA_ELAST=1 lo è per costruzione, e il movimento residuo è solo
            # composizione università/EPR - quindi la distanza fra i due capi non si
            # legge dall'asse: va scritta. Una riga per scenario, una sola se
            # coincidono (stesso criterio della nota nel titolo).
            serie = {n: df[df["anno"] <= fine_p][["anno", col]] for n, df in dfs.items()}
            if coincide:
                serie = dict([next(iter(serie.items()))])
            righe = [
                f"{int(d['anno'].iloc[0])}: {d[col].iloc[0]:.1%}"
                f"   →   {int(d['anno'].iloc[-1])}: {d[col].iloc[-1]:.1%}"
                + ("" if len(serie) == 1 else f"   ({n.replace('_', ' ')})")
                for n, d in serie.items()]
            # in basso a sinistra: con la baseline a zero e la serie intorno al 20% la
            # metà inferiore del pannello è sempre vuota, qualunque scenario
            ax.text(0.03, 0.05, "\n".join(righe), transform=ax.transAxes,
                    fontsize=8.5, color=INK2, ha="left", va="bottom", linespacing=1.5,
                    bbox=dict(boxstyle="round,pad=0.34", facecolor="#fcfcfb",
                              edgecolor="#c3c2b7", linewidth=0.7, alpha=0.92))
        if col == "quota_attrezz":
            # asse in percentuale come gli altri due pannelli di quote
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
            # la quota di PARTENZA, cioè quella che il modello calibra sul 2026: è il
            # metro di tutto il pannello - la curva si legge come "quanto il piano si
            # allontana da com'è spesa oggi la ricerca pubblica" - e senza la riga
            # bisognerebbe andarsela a cercare sul primo punto della serie.
            q0 = list(dfs.values())[0][col].iloc[0]
            ax.axhline(q0, lw=1.2, ls=(0, (4, 3)), color=MUTED)
            ax.annotate(f"quota {C.ANNO0}: {q0:.0%}", (C.ANNO0 + 1, q0),
                        textcoords="offset points", xytext=(0, -11),
                        fontsize=8, color=INK2)
            # i due ancoraggi dell'inviluppo: da qui in poi la curva non è più solo
            # il modello, è la regola di piano. Scritti come tacche sull'asse dei
            # tempi e non come annotazioni, per non aggiungere inchiostro dentro il
            # pannello dove passano le tre serie.
            ax.set_xticks(sorted({C.ANNO0, C.ATTREZZ_PICCO_1, C.ATTREZZ_PICCO_2,
                                  fine_p}))
        # NB: il pannello della componente precaria non porta riga di riferimento, a
        # differenza degli altri. Il riferimento naturale sarebbe il 100% - un postdoc
        # per strutturato -
        # ma la serie parte da 62 e scende, quindi quella riga non verrebbe mai
        # sfiorata e allungherebbe l'asse fino a 100 sprecando meta' pannello. Un
        # riferimento che nessuna curva avvicina non aiuta a leggere, arreda.
        ax.grid(True, lw=0.6, color=GRID)
        ax.set_axisbelow(True)
        ax.tick_params(labelsize=8, colors=MUTED, length=0)
        for lato in ("top", "right"):
            ax.spines[lato].set_visible(False)
        for lato in ("left", "bottom"):
            ax.spines[lato].set_color("#c3c2b7")
        if col in ("densita", "ruolo_teste", "postdoc_teste", "rtt_teste",
                   "quota_phd_postdoc", "epr_ruolo", "phd_teste", "ta_fte",
                   "quota_ta", "densita_rs_tot", "fte_didattico", "stud_per_doc",
                   "componente_precaria", "quota_attrezz"):
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
    destro.
    I professori sono DUE fasce, ordinari e associati, e vengono dal motore già
    separate dalla soglia di anzianità: la loro proporzione cambia nel tempo."""
    etich = etich or {n: n.replace("_", " ") for n in dfs}
    # con un solo pannello la larghezza minima è dettata dalla legenda, non dal grafico
    fig, axes = plt.subplots(1, len(dfs), figsize=(max(9.0, 5.2 * len(dfs)), 5.4),
                             facecolor="#fcfcfb", sharey=True)
    # asse y comune e IMPOSTO sul massimo degli scenari passati: con sharey
    # l'autoscale dell'ultimo pannello troncherebbe i totali più alti (ERA).
    ytop = max(_teste_tot(df[df["anno"] <= fine]).max() for df in dfs.values()) * 1.06
    for ax, (nome, df) in zip(np.atleast_1d(axes), dfs.items()):
        d = df[df["anno"] <= fine].copy()
        # 'po_teste' e 'pa_teste' arrivano GIÀ SPEZZATE dal motore, che applica la
        # soglia di anzianità alla coorte per età: qui non si ripartisce nulla. Il
        # rapporto fra le due fasce si muove nel tempo, e il suo movimento è
        # informazione - è l'organico che ringiovanisce e poi reinvecchia.
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
        #ax.set_title(etich[nome], fontsize=10, color=INK, loc="left", pad=8)
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
    # la seconda riga dice su quale regola poggia lo split PO/PA. Serve: la quota si
    # muove nel disegno, e chi legge deve sapere che a muoverla è l'età della coorte e
    # non un'ipotesi sui concorsi. Sta nel sottotitolo e non in una nota a piè di
    # figura perchè va letta insieme al disegno, non dopo.
    # a soglia non calibrata il motore ricade sul mix congelato, e il sottotitolo deve
    # dire quello: promettere una regola di anzianità che non è stata applicata
    # sarebbe peggio che non dire nulla.
    regola = (f"Si diventa ordinari per anzianità: {C.ANNI_DA_ASSOCIATO:.1f} anni di "
              f"ruolo nel {C.ANNO0} (= il {C.QUOTA_PO:.0%} di ordinari osservato nel "
              f"2023), {anni_da_associato_tgt():.0f} a fine rampa (= "
              f"{C.QUOTA_PO_TGT:.0%} a regime)."
              if C.ANNI_DA_ASSOCIATO is not None else
              f"Ordinari e associati ripartiti a quota fissa {C.QUOTA_PO:.0%}/"
              f"{1 - C.QUOTA_PO:.0%} (MUR 2023): soglia di anzianità non calibrata.")
    fig.tight_layout(rect=(0, 0.055, 1, 0.865 if stretta else 0.895))
    fig.savefig(path, dpi=140, facecolor="#fcfcfb")
    plt.close(fig)


def grafico_spesa_stack(dfs: dict[str, pd.DataFrame], fine: int, path: str,
                        etich: dict[str, str] | None = None) -> None:
    """VARIAZIONE della spesa pubblica per la ricerca rispetto al 2026, con le voci di
    bilancio impilate: università, EPR e attrezzature. Parte da zero per costruzione -
    il livello assoluto della baseline 2026 resta fuori dal grafico.
    (I livelli assoluti sono comunque nei CSV, colonne budget_univ_mld e
    budget_epr_mld, se serve rimetterli.)

    La terza fascia è l'INVILUPPO: la spesa che le due fasce sotto liberano quando
    l'organico si sgonfia e che il piano tiene alla ricerca sotto forma di
    attrezzature, invece di lasciarla scendere. È il motivo per cui il totale qui non
    cala mai dopo il 2055. Vedi piano_attrezzature() in motore.
    Le due fasce di ramo sono AL NETTO del supplemento (colonne *_pers_mld): quello è
    già ripartito fra i due rami dentro dStato_univ_mld e dStato_epr_mld, che è ciò
    che disegna grafico_ffo - i due grafici mostrano quindi lo stesso totale, spezzato
    una volta per RAMO e una volta per NATURA della spesa.

    Sotto lo zero, in negativo, l'IRPEF che quegli stipendi riversano: è un flusso di
    segno opposto e sta dalla parte opposta dell'asse. Il grafico si legge allora come
    un saldo - lordo sopra, rientro sotto, netto la differenza - e il netto è anche
    disegnato, come tratteggio dentro lo stack. Vedi SPESA_IRPEF per il perchè.
    L'IRPEF NON si muove con la terza fascia: le attrezzature non sono stipendi e non
    pagano imposta sul reddito, quindi ogni euro di quella fascia entra nel netto per
    intero."""
    etich = etich or {n: n.replace("_", " ") for n in dfs}
    fig, axes = plt.subplots(1, len(dfs), figsize=(max(8.6, 5.0 * len(dfs)), 5.0),
                             facecolor="#fcfcfb", sharey=True)
    # su un DataFrame che non è passato da piano_attrezzature() non ci sono nè la
    # fascia delle attrezzature nè le colonne di ramo al netto del supplemento: si
    # ricade sulle due fasce di prima, lette dalle colonne piene
    if all("attrezz_extra_mld" in df.columns for df in dfs.values()):
        voci = SPESA
    else:
        voci = [("dStato_univ_mld", *SPESA[0][1:]), ("dStato_epr_mld", *SPESA[1][1:])]
    # 18% di aria sopra il massimo invece del 10% QUANDO c'è l'inviluppo: lì il totale
    # ARRIVA al suo massimo e ci resta, quindi l'etichetta "Lordo", che sta 20 punti
    # sopra la fine della curva, cadrebbe fuori dal pannello col margine di prima. Con
    # le due sole fasce di personale il totale a fine periodo sta ben sotto il picco e
    # il problema non si pone: lì il margine resta quello originale, altrimenti la
    # figura si allungherebbe senza motivo.
    aria = 1.18 if len(voci) > 2 else 1.10
    ytop = max((df[df["anno"] <= fine][[c for c, _, _, _ in voci]].sum(axis=1)).max()
               for df in dfs.values()) * aria
    # margine sotto lo zero: il 35% in più del rientro massimo, che è lo spazio per
    # scriverci dentro l'etichetta senza che tocchi il bordo inferiore
    ybot = -max(df[df["anno"] <= fine][SPESA_IRPEF[0]].max()
                for df in dfs.values()) * 1.35
    span = ytop - ybot
    for ax, (nome, df) in zip(np.atleast_1d(axes), dfs.items()):
        d = df[df["anno"] <= fine]
        y = np.vstack([d[c].to_numpy() for c, _, _, _ in voci])
        cum = np.cumsum(y, axis=0)
        # il rientro non è mai negativo per costruzione, ma il clip lo garantisce anche
        # se il fisco cambiasse segno in qualche configurazione di parametri
        irp = np.clip(d[SPESA_IRPEF[0]].to_numpy(), 0.0, None)
        ax.stackplot(d["anno"], y, colors=[col for _, _, col, _ in voci],
                     labels=[lab for _, lab, _, _ in voci],
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
                    textcoords="offset points", xytext=(-2, 20), fontsize=9.5,
                    color=INK, ha="right")
        # il picco non coincide col valore a regime: l'onda dei pensionamenti lo alza
        # per una ventina d'anni, ed è il numero che conta per la programmazione. Sta
        # sotto il lordo di fine periodo perchè è la stessa grandezza letta altrove
        # sulla curva; il riquadro chiaro lo stacca dalla fascia che gli fa da fondo.
        # SCRITTO SOLO SE C'È: con la fascia delle attrezzature il totale è piatto dal
        # secondo ancoraggio in poi, quindi il picco È il valore di fine periodo e la
        # riga ripeterebbe il numero appena scritto sopra. La soglia di mezzo decimo di
        # miliardo è quella sotto la quale i due numeri si arrotondano uguali.
        kp = int(np.argmax(cum[-1]))
        if cum[-1][kp] - cum[-1][-1] > 0.05:
            ax.annotate(f"(Picco {cum[-1][kp]:.1f} Mld EUR)",
                        (d["anno"].iloc[-1], cum[-1][-1]), textcoords="offset points",
                        xytext=(-2, 15), fontsize=8.5, color=INK2, ha="right", va="top",
                        zorder=8,
                        bbox=dict(boxstyle="round,pad=0.28", facecolor="#fcfcfb",
                                  edgecolor="#c3c2b7", linewidth=0.7, alpha=0.92))
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
        # etichette dirette dentro le fasce, come nello stack dell'organico. La fascia
        # del rientro entra nella stessa lista con estremi (-irp, 0): sotto lo zero il
        # criterio di posa non cambia, è sempre "dove la fascia è più spessa su una
        # finestra larga quanto il testo". La soglia è però sull'intero SPAN della
        # figura, non sul solo ytop, altrimenti la parte sotto lo zero non conterebbe.
        anni = d["anno"].to_numpy()
        # estremi ricavati dalle cumulate invece che scritti a mano: le fasce sopra lo
        # zero sono quante ne ha 'voci', e la fascia del rientro si aggiunge in coda
        estremi = [(b, a) for b, a in zip(np.vstack([np.zeros(len(d)), cum[:-1]]), cum)]
        estremi.append((-irp, np.zeros(len(d))))
        for (lo, hi), (_, _, col, dentro) in zip(estremi, [*voci, SPESA_IRPEF]):
            # la larghezza che conta è quella della riga più lunga, non del testo
            nch = max(len(r) for r in dentro.splitlines())
            posa = _posa_etichetta(anni, lo, hi, span, nch, 0.055)
            if posa is None:
                continue
            ax.annotate(dentro, posa, fontsize=8.5, ha="center", va="center",
                        linespacing=1.35, color=_ink_su(col))
        #ax.set_title(etich[nome], fontsize=10, color=INK, loc="left", pad=8)
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
    # come nello stack dell'organico: su una figura stretta (un pannello solo) il
    # sottotitolo va spezzato, altrimenti esce dal bordo destro
    stretta = fig.get_figwidth() < 12
    h, l = ass[0].get_legend_handles_labels()
    # con la fascia delle attrezzature le voci sono quattro, e su una riga sola non
    # stanno in una figura a un pannello: li' vanno su due colonne, e la fascia in
    # fondo alla figura si allarga di conseguenza
    ncol = len(l) if not stretta or len(l) <= 3 else 2
    righe_leg = -(-len(l) // ncol)
    fig.legend(h[::-1], l[::-1], fontsize=8.5, frameon=False, labelcolor=INK2,
               loc="lower center", ncol=ncol, bbox_to_anchor=(0.5, -0.005))
    # titolo su due righe: una riga sola sfora la figura strettta a un pannello.
    # "per voce" con la fascia delle attrezzature, che voce di bilancio non è: senza,
    # le fasce sono i due rami e basta, e il titolo torna a dire quello.
    fig.suptitle(f"Fondi per la ricerca pubblica: variazione annua rispetto al {C.ANNO0}, "
                 f"per {'voce' if len(voci) > 2 else 'ramo'} di bilancio",
                 fontsize=12.5, color=INK, x=0.006, ha="left", y=0.995)
    fig.tight_layout(rect=(0, 0.06 * righe_leg, 1, 0.895 if stretta else 0.915))
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
