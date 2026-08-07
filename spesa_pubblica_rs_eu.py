"""Serie storiche 2000-2024 della spesa pubblica in R&S (HERD + GOVERD, % del PIL).

Fonte: Eurostat SDG_09_10 (estat_sdg_09_10_en.csv), esportazione con unica unita'
PC_GDP. Il dataset è disaggregato per settore di ESECUZIONE (sectperf): sommiamo
HES (Higher Education = HERD) e GOV (Government = GOVERD), cioè la ricerca
ESEGUITA dal settore pubblico. Non è la stessa cosa della ricerca FINANZIATA dal
pubblico: i fondi pubblici che finiscono a imprese (BES) restano fuori, e una quota
di HERD/GOVERD è finanziata da privati e dall'estero. Però è la scomposizione
standard con cui si confrontano i sistemi di ricerca pubblici, ed è l'unica
disponibile in questo dataflow.

Perimetro paesi: media EU27 come riferimento, piu' i soli Stati membri sopra i
30 milioni di abitanti (DE, FR, IT, ES, PL). 

Uso:  python spesa_pubblica_rs_eu.py
Output: spesa_pubblica_rs_eu.png
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import config as C

_QUI = Path(__file__).parent
CSV = next((p for p in (_QUI / "doc" / "estat_sdg_09_10_en.csv",
                        _QUI / "estat_sdg_09_10_en.csv") if p.exists()),
           _QUI / "doc" / "estat_sdg_09_10_en.csv")
OUT = Path(C.OUT) / "spesa_pubblica_rs_eu.png"
ANNO_MIN, ANNO_MAX = 2000, 2024

INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#898781", "#e1e0d9"


PAESI = [("DE", "Germania",   "#2a78d6"),
         ("FR", "Francia",    "#eb6834"),
         ("IT", "Italia",     "#1baf7a"),
         ("ES", "Spagna",     "#eda100"),
         ("PL", "Polonia",    "#e87ba4")]
EU = ("EU27_2020", "EU27", INK2)


def serie() -> pd.DataFrame:
    """Colonne = geo, righe = anno, valori = HERD + GOVERD in % del PIL."""
    d = pd.read_csv(CSV)
    d = d[d["sectperf"].isin(["HES", "GOV"])]
    if set(d["unit"].unique()) != {"PC_GDP"}:
        raise ValueError(f"attese solo osservazioni PC_GDP, trovate {sorted(d['unit'].unique())}")
    p = d.pivot_table(index=["geo", "TIME_PERIOD"], columns="sectperf", values="OBS_VALUE")
    pub = (p["HES"] + p["GOV"]).unstack("geo")
    return pub.loc[ANNO_MIN:ANNO_MAX]


def _sposta(etichette, dy_min):
    """Separa verticalmente le etichette di fine linea che si sovrappongono.
    """
    ys = [y for y, _, _ in etichette]
    for i in range(1, len(ys)):
        if ys[i] - ys[i - 1] < dy_min:
            ys[i] = ys[i - 1] + dy_min
    return ys


def figura(pub: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(11.5, 6.6), dpi=150)
    fig.patch.set_facecolor("#fcfcfb")
    ax.set_facecolor("#fcfcfb")

    anni = pub.index.to_numpy()
    finali = []

    for geo, nome, col in [EU, *PAESI]:
        s = pub[geo].dropna()
        eu = geo == EU[0]
        ax.plot(s.index, s.to_numpy(), color=col, linewidth=2.6 if eu else 2.0,
                linestyle=(0, (5, 2.5)) if eu else "-", zorder=3 if eu else 4,
                solid_capstyle="round", dash_capstyle="round")
        finali.append((float(s.iloc[-1]), f"{nome} | {s.iloc[-1]:.2f}", col))

    finali.sort()
    for (y0, testo, col), y in zip(finali, _sposta(finali, 0.033)):
        ax.plot([anni[-1], anni[-1] + 0.35], [y0, y], color=col, linewidth=1.0,
                alpha=0.55, zorder=2, clip_on=False)
        ax.text(anni[-1] + 0.55, y, testo + "%", color=INK, fontsize=13,
                va="center", ha="left", fontweight="medium")

    ax.set_xlim(ANNO_MIN, ANNO_MAX)
    ax.set_ylim(0.25, 1.10)
    ax.set_xticks(range(ANNO_MIN, ANNO_MAX + 1, 4))
    ax.set_yticks([0.3, 0.5, 0.7, 0.9, 1.1])
    ax.set_yticklabels([f"{v:.1f}%" for v in [0.3, 0.5, 0.7, 0.9, 1.1]])
    ax.grid(axis="y", color=GRID, linewidth=0.9, zorder=0)
    ax.set_axisbelow(True)
    for lato in ("top", "right", "left"):
        ax.spines[lato].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=MUTED, length=0, labelsize=10)

    fig.text(0.055, 0.955, "Spesa in Ricerca e Sviluppo del settore pubblico",
             color=INK, fontsize=16, va="top")
    fig.text(0.055, 0.895, "Ricerca eseguita da università (HERD) ed enti pubblici (GOVERD), "
                           "[% PIL]",
             color=INK2, fontsize=10.5, va="top")

    fig.subplots_adjust(left=0.055, right=0.815, top=0.855, bottom=0.115)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, facecolor=fig.get_facecolor())
    plt.close(fig)


def main() -> None:
    pub = serie()
    colonne = [EU[0]] + [g for g, _, _ in PAESI]
    figura(pub)
    print(pub[colonne].round(2).to_string())
    print(f"\nscritto {OUT.name}")


if __name__ == "__main__":
    main()
