"""Webapp del modello stock-flow dei precari della ricerca (università + EPR).

Front-end di stock_flow_precari.py e stock_flow_epr.py: la sidebar raccoglie i parametri
non osservabili, il corpo mostra KPI e grafici. Nessun calcolo vive qui: i numeri
vengono da SF.modello() ed epr.modello(), gli stessi della pipeline che scrive CSV e
report. Il Monte Carlo resta nella pipeline; qui si muovono i parametri a mano.

Uso:  streamlit run app_precari.py

Lo stock di oggi delle università viene dal monitoraggio giornaliero di Cerca Università
(../NumeroRicercatoriEmail/nazionale/ricercatori_nazionale.csv) se il PC lo raggiunge,
altrimenti da input/monitoraggio_snapshot.csv, che la pipeline riscrive a ogni esecuzione.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import stock_flow_epr as epr
import stock_flow_precari as SF

st.set_page_config(page_title="Precari della ricerca: stock e flussi", page_icon="📉",
                   layout="wide", initial_sidebar_state="expanded")

COL = {"usciti": "#B3574A", "stabilizzati": "#5BA88F", "rimasti": "#E8A33D",
       "ingressi": "#7C93C3", "stock": "#1F4E79", "Assegnisti": "#E8A33D", "RTDa": "#C6743A",
       "RTDb": "#4E9DD1", "RTT": "#5BA88F", "nuovi": "#9B8AA6", "td": "#8C5A2B"}
CFG = {"displayModeBar": False}
it = SF.it


@st.cache_data(show_spinner="Lettura dei dati...", ttl=3600)
def _dati():
    xl = SF.leggi_excel()
    mur, _ = SF.leggi_mur()
    mon = SF.leggi_monitoraggio()
    return xl, mur, mon, epr.assunti_ingresso_epr()


xl, mur, mon, hires = _dati()
s = SF.carica_stock(xl, mur, mon)
d_oggi = SF.data_it(mon["data"])

# =====================================================================================
# SIDEBAR
# =====================================================================================
PRESET = {
    "Stima centrale": {},
    "Ricircolo interno alto tra assegni (D_A = 5)": {"D_A": 5.0},
    "Ricircolo interno basso tra assegni (D_A = 2)": {"D_A": 2.0},
    "Più tenure track dai precari": {"s_T_Ra": 0.55, "s_T_PD": 0.45, "early_b": 0.10},
}
st.sidebar.title("Ipotesi del modello")
preset = st.sidebar.selectbox("Configurazione di partenza", list(PRESET),
                              help="Imposta i cursori; poi si possono muovere a mano.")
base_u = {**SF.CENTRALE, **PRESET[preset]}
k = "|" + preset  # chiave dei widget: cambiare preset li riporta ai valori del preset

# (min, max, passo, etichetta) - intervalli piu' larghi di quelli del Monte Carlo
CURSORI_U = {
    "D_A": (1.5, 10.0, 0.5, "Anni di permanenza di una persona tra gli assegni"),
    "s_T_Ra": (0.2, 0.8, 0.05, "Quota di nuovi RTT che erano RTDa"),
    "s_T_PD": (0.1, 0.7, 0.05, "Quota di nuovi RTT che erano assegnisti/postdoc"),
    "r_Ra_PD": (0.3, 0.9, 0.05, "Quota di nuovi RTDa che erano assegnisti"),
    "old_a": (0.0, 0.3, 0.01, "Quota di RTDa di oggi entrati prima del 2024 (proroghe)"),
    "early_a": (0.0, 0.2, 0.01, "Quota di nuovi RTDa già usciti in anticipo"),
    "early_b": (0.0, 0.25, 0.01, "Quota di nuovi RTDb già passati ad associato"),
    "n_A": (0.3, 0.9, 0.05, "Quota di contratti/incarichi a ex assegnisti"),
    "n_Ra": (0.0, 0.4, 0.05, "Quota di contratti/incarichi a ex RTDa"),
    "T_out": (0, 300, 10, "RTT già usciti (passaggio anticipato, dimissioni)"),
}
CURSORI_E = {
    "k_teste": (1.0, 1.5, 0.05, "Persone per unità annua"),
    "D": (1.5, 8.0, 0.5, "Anni di permanenza di una persona nel pool"),
    "E_2526": (0, 1000, 50, "Nuovi ingressi 2025-26 (unità annue)"),
    "pnrr_ok": (0.5, 1.0, 0.05, "Quota del calo 'fine PNRR' già avvenuta"),
    "tetto_ok": (0.0, 1.0, 0.05, "Quota del calo 'tetto 30 mesi' già avvenuta"),
    "s_prec": (0.3, 1.0, 0.05, "Quota di assunti in ruolo che erano precari"),
}


def _cursori(cursori, base, descr, chiave):
    p = {}
    for nome, (lo, hi, passo, etichetta) in cursori.items():
        v = base[nome]
        tipo = int if isinstance(passo, int) and isinstance(lo, int) else float
        p[nome] = st.slider(etichetta, tipo(lo), tipo(hi), tipo(v), tipo(passo),
                            key=nome + chiave, help=descr[nome][3])
    return p


st.sidebar.subheader("Università")
with st.sidebar:
    pu = _cursori({k_: CURSORI_U[k_] for k_ in ("D_A", "s_T_Ra", "s_T_PD")}, base_u, SF.PARAM, k)
    with st.expander("Altre ipotesi sulle università"):
        pu |= _cursori({k_: v for k_, v in CURSORI_U.items() if k_ not in pu}, base_u, SF.PARAM, k)
    st.subheader("Enti pubblici di ricerca")
    with st.expander("Ipotesi sugli enti"):
        pe = _cursori(CURSORI_E, epr.CENTRALE, epr.PARAM, k)
    _fonte = {"monitoraggio": "monitoraggio", "repo dati": "aggregato pubblicato dal monitoraggio",
              "snapshot": "snapshot salvato"}[mon["fonte"]]
    st.caption(f"Stock di oggi: {_fonte} "
               f"di Cerca Università, mediana degli ultimi {len(mon['giorni'])} giorni validi "
               f"(fino al {d_oggi}).")

# =====================================================================================
# CALCOLO (tutto nei moduli del modello)
# =====================================================================================
c = SF.modello(s, pu)
e = epr.modello(pe, hires)
P23 = s["Ra23"] + s["A23"]
P_oggi = s["Ra26"] + s["A26"] + s["N26"]
sis = {"usciti": c["usciti"] + e["usciti_teste"],
       "stabilizzati": c["stabilizzati"] + e["in_ruolo"],
       "rimasti": P_oggi + e["P26_teste"],
       "passati": P23 + c["ingressi_esterni"] + e["passati_teste"]}
q = {k_: sis[k_] / sis["passati"] for k_ in ("usciti", "stabilizzati", "rimasti")}
esaurimento = s["A26"] + s["Ra26"] + e["ass26_teste"]
lb = SF.limite_dal_picco(s)

# =====================================================================================
# CORPO
# =====================================================================================
st.title("Precari della ricerca pubblica: chi è uscito, chi è entrato in tenure track")
st.markdown(f"Università ed enti pubblici di ricerca, **dicembre 2023 → oggi ({d_oggi})**. "
            "Borse post-laurea e dottorandi esclusi.")
if not bool(c["_valido"]):
    st.warning("Con queste ipotesi qualche flusso diventa negativo (ad esempio più "
               "passaggi in tenure track di quanti RTDa siano usciti): i numeri non sono coerenti.")

st.subheader("Sistema complessivo")
m = st.columns(4)
m[0].metric("Precari passati per il sistema", it(round(sis["passati"], -2)),
            help="Precari presenti a dicembre 2023 più tutti quelli entrati dopo.")
m[1].metric("Usciti dal sistema", it(round(sis["usciti"], -2)), f"{SF.pct(q['usciti'])} dei passati",
            delta_color="off")
m[2].metric("Entrati in tenure track o in ruolo", it(round(sis["stabilizzati"], -2)),
            f"{SF.pct(q['stabilizzati'])} dei passati", delta_color="off")
m[3].metric("Ancora precari oggi", it(round(sis["rimasti"], -2)),
            f"{SF.pct(q['rimasti'])} dei passati", delta_color="off",
            help="Esclusi RTDb, RTT e borsisti degli enti.")
m = st.columns(4)
m[0].metric("Usciti dalle università", it(round(c["usciti"], -2)),
            f"{SF.pct(c['quota_usciti_su_chi_lascia'])} di chi ha lasciato", delta_color="off")
m[1].metric("Usciti dagli enti", it(round(e["usciti_teste"], -2)),
            f"{SF.pct(e['quota_usciti_su_chi_lascia'])} di chi ha lasciato", delta_color="off")
m[2].metric("Enti: a rischio entro il 2027", it(round(e["a_rischio_2027_teste"], -2)),
            help="Distanza tra lo stock di fine 2026 e lo scenario 2027 del Conto annuale.")
m[3].metric("Figure a esaurimento oggi", it(round(esaurimento, -2)),
            help="Assegnisti (università ed enti) e RTDa: posizioni non più attivabili per persone nuove.")


def _fig(titolo, h=430):
    f = go.Figure()
    f.update_layout(title=dict(text=titolo, font=dict(size=16)), template="plotly_white",
                    height=h, margin=dict(l=10, r=10, t=60, b=10), separators=",.",
                    legend=dict(orientation="h", yanchor="top", y=-0.12, x=0))
    return f


t1, t2, t3, t4, t5, t6 = st.tabs(["Esiti", "Andamento", "Sensitività", "Enti", "Tabella", "Metodo"])

with t1:
    st.markdown("Da dove si parte e dove si arriva: lo stock del 2023 più i nuovi ingressi, "
                "meno chi è passato in tenure track o in ruolo e chi è uscito, dà lo stock di oggi.")
    w = _fig("Università: dal 2023 a oggi")
    voci = [("Precari dic 2023", P23, "absolute"), ("Nuovi ingressi", c["ingressi_esterni"], "relative"),
            ("Passati a RTDb", -c["RTDb_in"], "relative"),
            ("Passati a RTT", -(c["RTT_da_RTDa"] + c["RTT_da_PD"]), "relative"),
            ("Usciti dal sistema", -c["usciti"], "relative"), ("Precari oggi", P_oggi, "total")]
    w.add_trace(go.Waterfall(x=[v[0] for v in voci], y=[v[1] for v in voci],
                             measure=[v[2] for v in voci],
                             text=[it(round(abs(v[1]), -1)) for v in voci], textposition="outside",
                             increasing=dict(marker_color=COL["ingressi"]),
                             decreasing=dict(marker_color=COL["usciti"]),
                             totals=dict(marker_color=COL["stock"]), connector=dict(line_color="#bbb")))
    w.update_layout(showlegend=False)
    st.plotly_chart(w, width="stretch", config=CFG)

    b = _fig("Esiti dei precari passati per il sistema", 360)
    ambiti = ["Università", "Enti", "Totale"]
    dati = {"usciti": [c["usciti"], e["usciti_teste"], sis["usciti"]],
            "stabilizzati": [c["stabilizzati"], e["in_ruolo"], sis["stabilizzati"]],
            "rimasti": [P_oggi, e["P26_teste"], sis["rimasti"]]}
    nomi = {"usciti": "Usciti dal sistema", "stabilizzati": "Tenure track o ruolo",
            "rimasti": "Ancora precari"}
    for k_, vals in dati.items():
        b.add_trace(go.Bar(y=ambiti, x=vals, name=nomi[k_], orientation="h",
                           marker_color=COL[k_], text=[it(round(v, -2)) for v in vals],
                           textposition="inside", hovertemplate="%{y}: %{x:,.0f}<extra>" + nomi[k_] + "</extra>"))
    b.update_layout(barmode="stack", yaxis=dict(autorange="reversed"))
    st.plotly_chart(b, width="stretch", config=CFG)
    st.caption(f"Cifra prudente: dal picco di dicembre 2024 ({it(lb['P_dic24'])} precari "
               f"universitari) sono usciti almeno {it(round(lb['usciti_min'], -2))} persone in "
               f"{s['mesi_dal_picco']} mesi, anche assumendo zero nuovi ingressi.")

with t2:
    st.markdown("Stock osservati: serie MUR al 31/12, colonne dell'Excel e, da agosto 2026, "
                "il monitoraggio giornaliero di Cerca Università.")
    a = _fig("Assegnisti e RTDa nelle università", 460)
    date_xl = {"dic22": "2022-12-31", "dic23": "2023-12-31", "dic24": "2024-12-31",
               "mag25": "2025-05-31", "ago25": "2025-08-31", "set25": "2025-09-30",
               "ott25": "2025-10-31", "nov25": "2025-11-30", "dic25": "2025-12-31",
               "feb26": "2026-02-28"}
    anni = [a_ for a_ in range(2019, 2025) if a_ in mur.index]
    a.add_trace(go.Scatter(x=[f"{a_}-12-31" for a_ in anni], y=[mur.loc[a_, "Assegni"] for a_ in anni],
                           name="Assegnisti (MUR)", mode="lines+markers",
                           line=dict(color=COL["Assegnisti"], dash="dot")))
    xa = [c_ for c_ in date_xl if c_ >= "mag" and xl["Assegni di ricerca"].get(c_)]
    a.add_trace(go.Scatter(x=[date_xl[c_] for c_ in xa], y=[xl["Assegni di ricerca"][c_] for c_ in xa],
                           name="Assegnisti (Excel, somma per area)", mode="markers",
                           marker=dict(color=COL["Assegnisti"], symbol="diamond", size=9)))
    serie = mon["serie"].copy()
    serie.index = pd.to_datetime(serie.index)
    for fig_ in ("Assegnisti", "RTDa", "RTDb", "RTT"):
        if fig_ != "Assegnisti":
            xs = [c_ for c_ in ("dic22", "dic23", "dic24", "dic25") if xl[fig_].get(c_)]
            a.add_trace(go.Scatter(x=[date_xl[c_] for c_ in xs], y=[xl[fig_][c_] for c_ in xs],
                                   name=f"{fig_} (Excel)", mode="lines+markers",
                                   line=dict(color=COL[fig_], dash="dot")))
        a.add_trace(go.Scatter(x=serie.index, y=serie[fig_], name=f"{fig_} (monitoraggio)",
                               mode="lines", line=dict(color=COL[fig_], width=3)))
    nuovi = serie[list(SF.NUOVI_PD)].sum(axis=1)
    a.add_trace(go.Scatter(x=serie.index, y=nuovi, name="Contratti e incarichi (monitoraggio)",
                           mode="lines", line=dict(color=COL["nuovi"], width=3)))
    a.update_layout(hovermode="x unified", yaxis=dict(rangemode="tozero"))
    st.plotly_chart(a, width="stretch", config=CFG)
    st.caption("Le somme per area CUN dell'Excel sottostimano un po' gli assegnisti, perché "
               "escludono chi non ha un'area: vedi il controllo nel report.")

with t3:
    st.markdown("La quota di usciti dipende soprattutto da quanto ricircolo c'è tra un assegno "
                "e l'altro: più a lungo una persona resta tra gli assegni, meno persone nuove "
                "sono entrate nel 2024 e meno ne sono uscite.")
    xs = np.arange(1.5, 10.01, 0.25)
    ys = []
    for D in xs:
        cu = SF.modello(s, {**pu, "D_A": D})
        ys.append((cu["usciti"] + e["usciti_teste"]) /
                  (P23 + cu["ingressi_esterni"] + e["passati_teste"]))
    sfig = _fig("Quota di usciti sui precari passati per il sistema", 400)
    sfig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=COL["usciti"], width=3),
                              name="Usciti / passati", hovertemplate="D_A %{x}: %{y:.1%}<extra></extra>"))
    sfig.add_trace(go.Scatter(x=[pu["D_A"]], y=[q["usciti"]], mode="markers", name="Scelta attuale",
                              marker=dict(size=12, color=COL["stock"])))
    sfig.update_layout(xaxis_title="Anni di permanenza di una persona tra gli assegni (D_A)",
                       yaxis=dict(tickformat=".0%"))
    st.plotly_chart(sfig, width="stretch", config=CFG)

with t4:
    st.markdown("Assegnisti e ricercatori/tecnologi a tempo determinato negli enti, in persone "
                "(unità annue del Conto annuale × fattore di conversione). Borsisti esclusi.")
    k_ = pe["k_teste"]
    anni_e = ["2023", "2024", "Fine 2026 (stima)", "2027 (scenario)"]
    ass = [epr.ASS[2023] * k_, epr.ASS[2024] * k_, e["ass26_teste"], epr.ASS[2027] * k_]
    td = [epr.TD[2023] * k_, epr.TD[2024] * k_, e["td26_teste"], epr.TD[2027] * k_]
    ef = _fig("Precari degli enti pubblici di ricerca", 400)
    ef.add_trace(go.Bar(x=anni_e, y=ass, name="Assegnisti", marker_color=COL["Assegnisti"]))
    ef.add_trace(go.Bar(x=anni_e, y=td, name="Ricercatori e tecnologi TD", marker_color=COL["td"]))
    ef.update_layout(barmode="stack", hovermode="x unified")
    st.plotly_chart(ef, width="stretch", config=CFG)
    st.caption(f"Il valore di 6.000 precari EPR del modello di simulazione corrisponde al picco del 2024: "
               f"implica circa {it(round(e['borsisti_impliciti_se_2024'], -1))} borsisti se riferito al 2024, "
               f"circa {it(round(e['borsisti_impliciti_se_2026'], -1))} se riferito a fine 2026.")

with t5:
    righe = [("Università", SF.VOCI[k_], c[k_]) for k_ in SF.VOCI if not k_.startswith("quota")]
    righe += [("Enti", SF.EVOCI[k_], e[k_]) for k_ in SF.EVOCI
              if not k_.startswith(("quota", "borsisti"))]
    righe += [("Sistema", "Passati per il sistema", sis["passati"]),
              ("Sistema", "Usciti dal sistema", sis["usciti"]),
              ("Sistema", "Entrati in tenure track o in ruolo", sis["stabilizzati"]),
              ("Sistema", "Ancora precari oggi", sis["rimasti"])]
    tab = pd.DataFrame(righe, columns=["Ambito", "Voce", "Persone"])
    tab["Persone"] = tab["Persone"].astype(float).round(0).astype(int)
    st.dataframe(tab, width="stretch", hide_index=True, height=620,
                 column_config={"Persone": st.column_config.NumberColumn(format="localized")})
    st.download_button("Scarica la tabella (CSV)", tab.to_csv(index=False).encode("utf-8-sig"),
                       "precari_scenario.csv", "text/csv")
    oggi_tab = pd.DataFrame([(k_, v) for k_, v in mon["oggi"].items()], columns=["Figura", "Persone oggi"])
    st.markdown(f"**Stock di oggi nelle università** (mediana dal {SF.data_it(pd.Timestamp(mon['giorni'][0]))} "
                f"al {d_oggi})")
    st.dataframe(oggi_tab, hide_index=True,
                 column_config={"Persone oggi": st.column_config.NumberColumn(format="localized")})

with t6:
    st.markdown(f"""
**Identità di bilancio.** Per il pool precario (RTDa, assegnisti, contratti e incarichi):
usciti = stock 2023 + nuovi ingressi − stock di oggi − passaggi a RTDb/RTT (o in ruolo, negli enti).
I passaggi interni (assegno → RTDa, rinnovi, assegno → contratto) si annullano nel totale.

**Cosa è osservato e cosa è ipotesi.**
- *Osservati:* gli stock di dicembre 2023 (Excel e MUR), lo stock di oggi (monitoraggio di
  Cerca Università), la crescita degli assegni nel 2024 (MUR), i dati del Conto annuale per gli enti.
- *Ipotesi (i cursori):* quanto restano le persone tra gli assegni, da dove vengono i nuovi RTT
  e RTDa, quanta parte dei cali previsti negli enti è già avvenuta.

**Ipotesi strutturali.** RTDa e RTDb durano 3 anni e solo gli RTDa diventano RTDb; gli RTT
durano 6 anni. Dal 2025 agli assegni accedono solo assegnisti già esistenti, e la crescita del
2024 è fatta di persone nuove.

**Dove sono gli intervalli di incertezza.** Il Monte Carlo (p10–p90) è nella pipeline:
`python stock_flow_precari.py` rigenera `output/precari_stock_flow.md` e `.csv`.

**Esclusi:** borse post-laurea, dottorandi, borsisti degli enti.
""")
