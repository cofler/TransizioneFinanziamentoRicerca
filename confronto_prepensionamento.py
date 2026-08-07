"""
================================================================================
CONFRONTO PREPENSIONAMENTO: 0 / 2 / 3 / 4 ANNI DI ANTICIPO
================================================================================
Due curve, un pannello ciascuna, per uno scenario alla volta:
  - POSIZIONI: organico totale della ricerca pubblica in teste. È la serie che
    oscilla, e quindi quella su cui si misura se la leva liscia davvero.
  - FFO: maggior fabbisogno annuo a carico dello Stato rispetto al 2026
    (universita' + EPR), la proxy FFO gia' calcolata dal modello.
Due pannelli e non due assi sullo stesso: sono misure di scala diversa, e un
doppio asse y farebbe leggere come coincidenze incroci che non esistono.

COLORE. I quattro casi non sono categorie: sono INTENSITÀ ORDINATE della stessa
misura, piu' un riferimento. Quindi rampa a UNA TINTA chiaro->scuro per 2/3/4
anni, e grafite tratteggiato per la leva spenta - che non e' "il quarto colore"
ma il termine di paragone, e va letto come tale. Rampa verificata coi controlli
ordinali della skill dataviz (porting Python, qui non c'e' node): L monotona
0,764/0,575/0,385, dL adiacenti 0,19 (minimo 0,06), tinta unica entro 3,4 gradi,
contrasto dell'estremo chiaro 2,06:1 (minimo 2,0), CVD adiacente peggiore dE 19,0
e vista normale 19,5, entrambi sopra le soglie. Il passo chiaro sta sotto 3:1
contro il fondo: per questo ogni curva porta l'etichetta scritta accanto, che e'
il rimedio previsto - l'identita' non e' mai solo-colore.

Uso:
    python confronto_prepensionamento.py
    python confronto_prepensionamento.py --scenario FLC --prepens-ades 0.5
================================================================================
"""
from __future__ import annotations

import argparse
import os

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt

# Il modello e' ora diviso in moduli: i VALORI di configurazione vanno letti e
# soprattutto SCRITTI su config (C), perche' e' l'unico oggetto che tutti i moduli
# vedono. Assegnare su un altro modulo non avrebbe effetto sulle funzioni chiamate.
import config as C
import regime as RG
import motore as MO
import calibrazione as CAL
import grafici as G

# rampa ordinale a una tinta + grafite di riferimento (vedi docstring)
RAMPA = ["#86b6ef", "#2a78d6", "#104281"]
RIF = G.INK
FONDO = "#fcfcfb"


def _etichette(anni: tuple, coda: tuple, asimm: tuple, centro: tuple) -> list[str]:
    """'4 anni' basta finche' gli anticipi sono tutti diversi. Quando due serie
    condividono l'anticipo e cambiano in altro, il numero da solo non le distingue
    piu': si aggiunge SOLO il parametro che effettivamente varia, per non appesantire
    le etichette con roba uguale per tutti."""
    lab = [f"{a} anni" for a in anni]
    if len(set(anni)) == len(anni):
        return lab
    if len(set(zip(coda, asimm))) > 1:
        lab = [f"{l} {'a scalare' if (c > 0 or s < 1.0) else 'piatto'}"
               for l, c, s in zip(lab, coda, asimm)]
    if len(set(centro)) > 1:
        lab = [f"{l}, centro {c}" if c is not None else f"{l}, centro sul picco"
               for l, c in zip(lab, centro)]
    return lab


def _serie(scenario: str, ades: float, sigma: float, anni: tuple[int, ...],
           coda: tuple[float, ...], asimm: tuple[float, ...],
           centro: tuple) -> tuple[dict[str, pd.DataFrame], tuple]:
    """Una simulazione per ogni anticipo, piu' la baseline a leva spenta.

    La calibrazione va rifatta esattamente come in main() del modello, e NELLO STESSO
    ORDINE: gli stock di partenza, poi il TA, poi la soglia PA->PO (il costo dei
    professori entra nell'HERD ricostruito), poi lambda (che dipende dal TA), poi il
    supporto (residuo su lambda), poi l'overhead EPR (che dipende dal supporto).
    Sono residui, non costanti: saltarne uno o invertirli non da' un errore, da'
    silenziosamente uno scenario diverso da quello che stampa il modello."""
    C.PRECARI_OGGI = MO._precari_per_chiudere()
    C.FTE_OGGI = MO._fte_uni_oggi()
    C.DENS_OGGI = C.FTE_OGGI / C.POP_100K
    C.TA_UNI_OGGI = C.TA_UNI_RATIO * C.FTE_OGGI
    C.TA_EPR_OGGI = C.TA_EPR_RATIO * C.EPR_RICERC_OGGI * C.ALPHA_EPR
    C.STUDENTI_OGGI = C.STUD_DOC_OGGI * MO._fte_didattico(MO._init_stato(0.0))
    C.ANNI_DA_ASSOCIATO = CAL._calibra_anni_da_associato()
    C.LAMBDA_HE = CAL._calibra_lambda_he()
    C.SUPPORTO = CAL._calibra_supporto()
    C.OVH_EPR_SUPP, C.OVH_EPR_ATTR = CAL._calibra_overhead_epr()
    q = C.QUOTA_RIC_UNI
    # gli stessi tre scenari di main(), con le stesse regole: la quota-ricercatori
    # e' una leva del solo terzo scenario, FLC ed ERA restano tutto-cattedre
    C.QUOTA_RIC_UNI = 0.0
    d_era = RG.densita_iso_herd(C.HERD_TGT, 1.0, C.PRECARI_ANNI, C.W_PHD)
    C.QUOTA_RIC_UNI = q
    d_ppp = RG.densita_iso_herd(C.HERD_TGT, C.UPLIFT_PPP, C.PRECARI_ANNI, C.W_PHD)
    C.QUOTA_RIC_UNI = 0.0
    scen = {"FLC": (140.0, 1.0, 0.0),
            "ERA": (d_era, 1.0, 0.0),
            "ERA_PPP_ric": (d_ppp, C.UPLIFT_PPP, q)}
    arg = scen[scenario]

    out = {"spento": MO.simula_senza_prepens(*arg)}
    # salva-e-ripristina, non azzera: i PREPENS_* del modello hanno un default
    # significativo (la configurazione consigliata) e rimetterli a zero qui
    # cambierebbe il comportamento di chiunque importi questo modulo
    salva = {k: getattr(C, k) for k in
             ("PREPENS_ANNI", "PREPENS_ADES", "PREPENS_SIGMA",
              "PREPENS_CODA", "PREPENS_ASIMM", "PREPENS_CENTRO")}
    try:
        C.PREPENS_ADES, C.PREPENS_SIGMA = ades, sigma
        for lab, a, c, s, ce in zip(_etichette(anni, coda, asimm, centro),
                                    anni, coda, asimm, centro):
            C.PREPENS_ANNI, C.PREPENS_CODA, C.PREPENS_ASIMM = a, c, s
            C.PREPENS_CENTRO = ce
            out[lab] = MO.simula(*arg)
    finally:
        for k, v in salva.items():
            setattr(C, k, v)
    return out, arg


def _posa_etichette(ax, curve: list[tuple[str, np.ndarray, np.ndarray, str]],
                    anni: np.ndarray) -> None:
    """Etichetta diretta su ogni curva. Testo in inchiostro e pallino nel colore
    della serie: l'identita' la porta la marca, non il testo.
    Le quattro serie coincidono fino al 2048 e riconvergono dopo il 2070, quindi
    NON esiste un buon punto per ciascuna: esiste un solo tratto in cui si
    distinguono tutte. Le etichette vanno percio' su UN'UNICA ascissa, quella in
    cui la coppia piu' stretta e' piu' larga possibile, e li' si distanziano in
    verticale quel tanto che basta a non toccarsi - il pallino resta sul valore
    vero, e lo spostamento non puo' confondere le serie perche' preserva l'ordine."""
    lo, hi = ax.get_ylim()
    yn = [(y - lo) / (hi - lo) for _, y, _, _ in curve]
    m, n = len(anni), len(curve)
    bordo = max(3, m // 12)
    # Ascissa unica: dove il fascio e' PIU' APERTO nel complesso (max - min), non
    # dove la coppia piu' stretta e' piu' larga. Col secondo criterio, quando due
    # curve qualsiasi si toccano in ogni punto - come succede appena le serie sono
    # quattro - vince un'ascissa dove sono strette TUTTE, e le etichette escono
    # ammucchiate in un angolo morto. Le sovrapposizioni residue le risolve la
    # spaziatura verticale qui sotto. A destra si lascia respiro: il testo esce a
    # destra del pallino.
    apertura = np.max(np.vstack(yn), axis=0) - np.min(np.vstack(yn), axis=0)
    apertura[:bordo] = -np.inf
    apertura[m - max(bordo, m // 6):] = -np.inf
    k = int(np.argmax(apertura))

    gap = 0.05                                   # altezza di riga in frazione d'asse
    ordine = sorted(range(n), key=lambda i: yn[i][k])
    posy = [yn[i][k] for i in ordine]
    for t in range(1, n):                        # spinge in su chi si sovrappone
        posy[t] = max(posy[t], posy[t - 1] + gap)
    if posy[-1] > 1.0:                           # se sfora in cima, trasla il blocco
        posy = [p - (posy[-1] - 1.0) for p in posy]
    dx = (anni[-1] - anni[0]) * 0.012
    for t, i in enumerate(ordine):
        lab, y, _, col = curve[i]
        ax.plot([anni[k]], [y[k]], "o", ms=5.5, color=col,
                mec=FONDO, mew=1.6, zorder=8)
        # alone del colore del fondo: nel pannello FFO le quattro curve stanno in
        # due mld su venti d'asse, quindi il testo cade per forza sopra le linee
        ax.annotate(lab, (anni[k] + dx, lo + posy[t] * (hi - lo)),
                    ha="left", va="center", fontsize=8.5, color=G.INK2, zorder=7,
                    path_effects=[pe.withStroke(linewidth=2.6, foreground=FONDO)])


def _stile(ax, titolo: str) -> None:
    ax.set_title(titolo, fontsize=10, color=G.INK, loc="left", pad=8)
    ax.grid(True, axis="y", lw=0.6, color=G.GRID)
    ax.set_axisbelow(True)
    ax.tick_params(labelsize=8, colors=G.MUTED, length=0)
    for lato in ("top", "right"):
        ax.spines[lato].set_visible(False)
    for lato in ("left", "bottom"):
        ax.spines[lato].set_color("#c3c2b7")
    ax.set_facecolor(FONDO)
    ax.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda v, _: f"{v:,.0f}" if abs(v) >= 1000 else f"{v:g}"))


def grafico(dfs: dict[str, pd.DataFrame], scenario: str, target: float,
            ades: float, sigma: float, centro: tuple, fine: int, path: str) -> None:
    nomi = list(dfs)
    # La rampa ha tre passi PER SCELTA, non per pigrizia: allungandola i passi si
    # avvicinano, e gia' a sei i ΔE fra adiacenti scendono a ~7 (contro i 19 di
    # adesso), sotto quello che si distingue a vista. Piu' di tre anticipi per
    # volta vanno su due grafici, non su due colori in piu'.
    if len(nomi) - 1 > len(RAMPA):
        raise SystemExit(f"--anni accetta al massimo {len(RAMPA)} valori per grafico "
                         f"(ricevuti {len(nomi)-1}): con piu' curve la rampa non e' "
                         "piu' leggibile. Lancia due volte con gruppi diversi.")
    colori = [RIF] + RAMPA[:len(nomi) - 1]
    fig, axes = plt.subplots(1, 2, figsize=(13.0, 5.2), facecolor=FONDO)
    pann = [
        ("Posizioni: organico totale della ricerca pubblica (teste)",
         lambda d: MO._teste_tot(d)),
        ("Proxy FFO: maggior fabbisogno annuo rispetto al 2026 (mld EUR/anno)",
         lambda d: d["dStato_univ_mld"] + d["dStato_epr_mld"]),
    ]
    for p, (ax, (tit, estrai)) in enumerate(zip(axes, pann)):
        curve = []
        for nome, colore in zip(nomi, colori):
            d = dfs[nome][dfs[nome]["anno"] <= fine]
            anni = d["anno"].to_numpy()
            y = estrai(d).to_numpy()
            # la baseline e' un RIFERIMENTO, non la quarta intensita': tratteggio
            # grafite, come la linea di densita' negli altri grafici del modello
            rif = nome == "spento"
            ax.plot(anni, y, lw=2.0 if not rif else 1.8, color=colore,
                    ls="-" if not rif else (0, (5, 2.5)), solid_capstyle="round",
                    zorder=4 if not rif else 3,
                    label="leva spenta" if rif else f"anticipo {nome}")
            curve.append((("spento" if rif else nome), y, anni, colore))
        _stile(ax, tit)
        ax.set_xlim(anni[0], anni[-1])
        # aria in alto: l'etichetta del picco sta SOPRA la curva e senza margine
        # finirebbe addosso al titolo del pannello
        y0, y1 = ax.get_ylim()
        ax.set_ylim(y0, y1 + 0.06 * (y1 - y0))
        if p == 0:
            # lo stato stazionario: gobba e conca si leggono solo rispetto a questo
            reg = MO._teste_tot(dfs["spento"]).iloc[-1]
            ax.axhline(reg, lw=1.1, ls=(0, (4, 3)), color=G.MUTED, zorder=2)
            ax.annotate(f"stato stazionario {reg:,.0f}", (anni[0] + 1, reg),
                        textcoords="offset points", xytext=(0, 5), fontsize=8,
                        color=G.INK2)
            ax.set_ylim(bottom=min(0.94 * reg, ax.get_ylim()[0]))
        _posa_etichette(ax, curve, anni)

    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, fontsize=8.5, frameon=False, labelcolor=G.INK2,
               loc="lower center", ncol=len(l), bbox_to_anchor=(0.5, -0.005))
    lista = nomi[1:]
    quali = " e ".join(filter(None, [", ".join(lista[:-1]), lista[-1]]))
    fig.suptitle(f"Prepensionamento: {quali} di anticipo - "
                 f"scenario {scenario} (target {target:.0f} FTE/100k)",
                 fontsize=12.5, color=G.INK, x=0.006, ha="left", y=0.995)
    # il centro NON e' il picco: sta al picco meno gli anni di anticipo, ed e' la
    # ragione per cui queste curve non hanno il buco. Scriverlo, non sottintenderlo.
    dove = (f"centrata sul {centro[0]}" if len(set(centro)) == 1
            else "con centro diverso per serie (vedi etichette)")
    fig.text(0.006, 0.938,
             f"Finestra gaussiana (sigma {sigma:g}a) {dove}, "
             f"adesione {ades:.0%} al centro; eleggibili le classi d'eta' fino a "
             f"{C.ETA_PENS - 1} anni.\nIl fabbisogno e' il solo costo del personale di "
             "ricerca: le pensioni anticipate restano fuori da questo grafico.",
             fontsize=8.5, color=G.INK2, ha="left", va="top", linespacing=1.4)
    fig.tight_layout(rect=(0, 0.055, 1, 0.90))
    fig.savefig(path, dpi=140, facecolor=FONDO)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[2])
    ap.add_argument("--scenario", default="ERA_PPP_ric",
                    choices=["FLC", "ERA", "ERA_PPP_ric"])
    # i default seguono il modello: se cambia li' cambiano anche qui, invece di
    # restare due configurazioni consigliate che divergono in silenzio
    ap.add_argument("--prepens-ades", type=float, default=C.PREPENS_ADES)
    ap.add_argument("--prepens-sigma", type=float, default=C.PREPENS_SIGMA)
    ap.add_argument("--anni", type=int, nargs="+", default=[2, 3, C.PREPENS_ANNI])
    ap.add_argument("--coda", type=float, nargs="+", default=None,
                    help="uno per ogni --anni: anni in cui l'anticipo scende a 1 dopo "
                         "il centro (default: tutti 0, anticipo piatto)")
    ap.add_argument("--asimm", type=float, nargs="+", default=None,
                    help="uno per ogni --anni: sigma della meta' destra della finestra "
                         "in multipli di --prepens-sigma (default: tutti 1, simmetrica)")
    ap.add_argument("--centro", type=int, nargs="+", default=None,
                    help="uno per ogni --anni: anno centrale della finestra "
                         f"(default: quello del modello, {C.PREPENS_CENTRO})")
    ap.add_argument("--fine", type=int, default=2080)
    # sottocartella dedicata: il modello scrive gia' una decina di png nella cartella
    # dello script, e questi confronti sono un'altra cosa
    ap.add_argument("--out", default=os.path.join(C.OUT, "prepens"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    coda = a.coda if a.coda is not None else [0.0] * len(a.anni)
    asimm = a.asimm if a.asimm is not None else [1.0] * len(a.anni)
    centro = a.centro if a.centro is not None else [C.PREPENS_CENTRO] * len(a.anni)
    if not len(coda) == len(asimm) == len(centro) == len(a.anni):
        raise SystemExit("--coda, --asimm e --centro devono avere tanti valori quanti --anni")

    dfs, (target, _, _) = _serie(a.scenario, a.prepens_ades, a.prepens_sigma,
                                 tuple(a.anni), tuple(coda), tuple(asimm),
                                 tuple(centro))
    # il gruppo di anticipi entra nel nome: due lanci con gruppi diversi devono
    # produrre due file, non sovrascriversi
    tag = "-".join(str(x) for x in a.anni) + "a"
    if any(c > 0 for c in coda) or any(s < 1.0 for s in asimm):
        tag += "_scalare"
    if any(c is not None for c in centro):
        tag += "_centro" + "-".join(str(c) for c in centro if c is not None)
    path = os.path.join(a.out, f"confronto_prepens_{a.scenario}_{tag}.png")
    grafico(dfs, a.scenario, target, a.prepens_ades, a.prepens_sigma,
            tuple(centro), a.fine, path)

    # tabella di servizio: i numeri che il grafico mostra come forma
    base = dfs["spento"]
    reg = MO._teste_tot(base).iloc[-1]
    picco0 = int(base.anno[MO._teste_tot(base).idxmax()])
    righe = []
    for nome, d in dfs.items():
        t = MO._teste_tot(d)
        dev = (t / reg - 1) * 100
        ffo = d["dStato_univ_mld"] + d["dStato_epr_mld"]
        righe.append({"anticipo": nome,
                      "picco_teste": round(t.max()), "anno_picco": int(d.anno[t.idxmax()]),
                      # tre scostamenti distinti dallo stato stazionario: la conca che
                      # PRECEDE la gobba (c'e' gia' nel modello base), la gobba, e il
                      # buco che la leva puo' scavare DOPO il picco. Solo il terzo e'
                      # colpa della leva, e solo il terzo la coda dell'anticipo cura.
                      "conca_%": round(dev[d.anno.between(2030, 2050)].min(), 1),
                      "gobba_%": round(dev[d.anno.between(2045, 2080)].max(), 1),
                      "buco_dopo_%": round(dev[d.anno > picco0].min(), 1),
                      "escursione_%": round(dev[d.anno >= 2035].max()
                                            - dev[d.anno >= 2035].min(), 1),
                      "uscite_tot": round(d["prepensionati"].sum()),
                      "FFO_max_mld": round(ffo.max(), 2),
                      "FFO_min_post_mld": round(ffo[d.anno > picco0].min(), 2),
                      "FFO_2080_mld": round(ffo.iloc[-1], 2)})
    print(f"scenario {a.scenario} - target {target:.0f} FTE/100k, adesione "
          f"{a.prepens_ades:.0%}, sigma {a.prepens_sigma:g}a, stato stazionario "
          f"{reg:,.0f} teste")
    print(pd.DataFrame(righe).to_string(index=False))
    print(f"\n[grafico] {path}")


if __name__ == "__main__":
    main()
