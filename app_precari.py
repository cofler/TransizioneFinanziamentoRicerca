"""Webapp del modello stock-flow dei precari della ricerca (università + EPR).

Pagina di sola lettura: usa le ipotesi centrali di stock_flow_precari.CENTRALE e
stock_flow_epr.CENTRALE, dichiarate in fondo alla pagina. Nessun calcolo vive qui: i
numeri vengono da SF.modello() ed epr.modello(), gli stessi della pipeline che scrive CSV
e report (dove ci sono anche gli intervalli Monte Carlo).

Uso:  streamlit run app_precari.py

Lo stock di oggi delle università, in ordine di preferenza: il monitoraggio giornaliero
locale (../NumeroRicercatoriEmail/nazionale/ricercatori_nazionale.csv), l'aggregato
pubblicato su GitHub (variabile/secret PRECARI_DATI_URL), input/monitoraggio_snapshot.csv.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import stock_flow_epr as epr
import stock_flow_precari as SF

st.set_page_config(page_title="Precari della ricerca: stock e flussi", page_icon="📉",
                   layout="wide", initial_sidebar_state="collapsed")

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
# CALCOLO con le ipotesi centrali (tutto nei moduli del modello)
# =====================================================================================
pu, pe = dict(SF.CENTRALE), dict(epr.CENTRALE)
c = SF.modello(s, pu)
e = epr.modello(pe, hires)
P23 = s["Ra23"] + s["A23"]
P_oggi = s["Ra26"] + s["A26"] + s["N26"]


def _sistema(cu):
    return {"usciti": cu["usciti"] + e["usciti_teste"],
            "stabilizzati": cu["stabilizzati"] + e["in_ruolo"],
            "rimasti": P_oggi + e["P26_teste"],
            "passati": P23 + cu["ingressi_esterni"] + e["passati_teste"]}


sis = _sistema(c)
q = {k_: sis[k_] / sis["passati"] for k_ in ("usciti", "stabilizzati", "rimasti")}
# quota di usciti agli estremi dell'ipotesi piu' incerta (permanenza tra gli assegni)
q_usc = [(lambda x: x["usciti"] / x["passati"])(_sistema(SF.modello(s, {**pu, "D_A": SF.PARAM["D_A"][i]})))
         for i in (2, 0)]
esaurimento = s["A26"] + s["Ra26"] + e["ass26_teste"]
lb = SF.limite_dal_picco(s)
fonte = {"monitoraggio": "monitoraggio giornaliero", "repo dati": "monitoraggio giornaliero",
         "snapshot": "ultimo salvataggio del monitoraggio"}[mon["fonte"]]

# =====================================================================================
# CORPO
# =====================================================================================
st.title("Precari della ricerca pubblica: chi è uscito, chi è entrato in tenure track")
st.markdown(f"Università ed enti pubblici di ricerca, **dicembre 2023 → oggi ({d_oggi})**. "
            "Borse post-laurea e dottorandi esclusi.")
st.caption(f"Stock di oggi delle università: {fonte} di Cerca Università (MUR), mediana degli "
           f"ultimi {len(mon['giorni'])} giorni validi fino al {d_oggi}. "
           "Ipotesi del modello in fondo alla pagina.")

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


t1, t2, t3, t4 = st.tabs(["Esiti", "Andamento", "Enti", "Tabella"])

with t1:
    st.markdown("Da dove si parte e dove si arriva: lo stock del 2023 più i nuovi ingressi, "
                "meno chi è passato in tenure track e chi è uscito, dà lo stock di oggi.")
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
    st.markdown("Stock osservati: serie MUR al 31/12, rilevazioni dell'Excel e, da agosto 2026, "
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
    serie["Contratti e incarichi"] = serie[list(SF.NUOVI_PD)].sum(axis=1)
    COL["Contratti e incarichi"] = COL["nuovi"]
    # stessa finestra dello stock di oggi: mediana degli ultimi N giorni validi
    mobile = serie.rolling(SF.FINESTRA_GIORNI, min_periods=1).median()
    for fig_ in ("Assegnisti", "RTDa", "RTDb", "RTT", "Contratti e incarichi"):
        if fig_ in ("RTDa", "RTDb", "RTT"):
            xs = [c_ for c_ in ("dic22", "dic23", "dic24", "dic25") if xl[fig_].get(c_)]
            a.add_trace(go.Scatter(x=[date_xl[c_] for c_ in xs], y=[xl[fig_][c_] for c_ in xs],
                                   name=f"{fig_} (Excel)", mode="lines+markers",
                                   line=dict(color=COL[fig_], dash="dot")))
        a.add_trace(go.Scatter(x=serie.index, y=serie[fig_], name=f"{fig_}, dato giornaliero",
                               mode="lines", legendgroup=fig_,
                               line=dict(color=COL[fig_], width=1.2, dash="dash")))
        a.add_trace(go.Scatter(x=mobile.index, y=mobile[fig_].round(),
                               name=f"{fig_}, mediana {SF.FINESTRA_GIORNI} giorni",
                               mode="lines", legendgroup=fig_,
                               line=dict(color=COL[fig_], width=3)))
    a.update_layout(hovermode="x unified", yaxis=dict(rangemode="tozero"))
    st.plotly_chart(a, width="stretch", config=CFG)
    st.caption(f"Monitoraggio: tratteggio = dato giornaliero di Cerca Università (solo i giorni "
               f"rilevati per tutti gli atenei); linea piena = mediana degli ultimi "
               f"{SF.FINESTRA_GIORNI} giorni validi, che assorbe i cali spuri di un singolo giorno "
               "ed è il valore usato dal modello. Le somme per area CUN dell'Excel sottostimano gli "
               "assegnisti, perché circa 1.350 contratti e incarichi non hanno un'area CUN.")

with t3:
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

with t4:
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
                       "precari_stock_flow.csv", "text/csv")
    oggi_tab = pd.DataFrame([(k_, v) for k_, v in mon["oggi"].items()], columns=["Figura", "Persone oggi"])
    st.markdown(f"**Stock di oggi nelle università** (mediana dal {SF.data_it(pd.Timestamp(mon['giorni'][0]))} "
                f"al {d_oggi})")
    st.dataframe(oggi_tab, hide_index=True,
                 column_config={"Persone oggi": st.column_config.NumberColumn(format="localized")})

# =====================================================================================
# IPOTESI E METODO (in fondo, sempre visibili)
# =====================================================================================
st.divider()
st.header("Ipotesi e metodo")

st.markdown(f"""
**Identità di bilancio.** Per il pool precario (RTDa, assegnisti, contratti e incarichi):
usciti = stock di dicembre 2023 + nuovi ingressi − stock di oggi − passaggi a RTDb/RTT (o in
ruolo, negli enti). I passaggi interni (assegno → RTDa, rinnovi, assegno → contratto) si
annullano nel totale e servono solo a ripartire i flussi tra le figure.

**Dati osservati.** Stock di dicembre 2023 e 2024 (MUR ed Excel "La grande espulsione"),
stock di oggi (monitoraggio di Cerca Università), crescita degli assegni nel 2024 (MUR),
Conto annuale e assunzioni 2024 per gli enti.

**Ipotesi strutturali.** RTDa e RTDb durano 3 anni e solo gli RTDa diventano RTDb; gli RTT
durano 6 anni, quindi nessuno è arrivato a scadenza nella finestra. Dal 2025 agli assegni
accedono solo assegnisti già esistenti (rinnovi), e la crescita del 2024 è fatta di persone nuove.
""")


def _v(nome, val):
    if nome in ("D_A", "D"):
        return f"{it(val)} anni"
    if nome in ("T_out", "E_2526"):
        return it(val) + (" unità annue" if nome == "E_2526" else " persone")
    if nome == "k_teste":
        return f"{val:.2f}".replace(".", ",")
    return SF.pct(val)


IPOTESI_U = [
    ("D_A", "Permanenza di una persona tra gli assegni, rinnovi inclusi",
     "Assegni di 1-2 anni rinnovabili, con il tetto di legge a 6 anni: la durata cumulata tipica "
     "è di circa 3 anni. È l'ipotesi che pesa di più (vedi sotto)."),
    ("s_T_Ra", "Quota di nuovi RTT che erano RTDa",
     "Gli RTDa in scadenza sono il bacino naturale dei primi concorsi RTT."),
    ("s_T_PD", "Quota di nuovi RTT che erano assegnisti o postdoc",
     "Il resto dei nuovi RTT (15%) viene dall'esterno: estero, enti, impresa."),
    ("r_Ra_PD", "Quota di nuovi RTDa che erano assegnisti",
     "Percorso tipico assegno → RTDa; il resto entra da dottorato o dall'esterno."),
    ("old_a", "Quota degli RTDa di oggi entrati prima del 2024",
     "Contratti prorogati (3 + 2 anni) ancora in corso."),
    ("early_a", "Quota di nuovi RTDa già usciti in anticipo",
     "Passaggi anticipati, soprattutto verso RTT."),
    ("early_b", "Quota di nuovi RTDb già passati ad associato",
     "Valutazione anticipata, possibile ma rara entro i primi anni."),
    ("n_A", "Quota di contratti e incarichi andati a ex assegnisti",
     "Le nuove figure post-riforma assorbono soprattutto chi era già assegnista."),
    ("n_Ra", "Quota di contratti e incarichi andati a ex RTDa",
     "RTDa scaduti che restano con un contratto; il resto (15%) sono persone nuove."),
    ("T_out", "RTT già usciti",
     "Pochi casi in 3 anni: passaggio anticipato ad associato o dimissioni."),
]
IPOTESI_E = [
    ("k_teste", "Persone per unità annua",
     "Il Conto annuale conta unità annue: con contratti infra-annuali le persone sono di più."),
    ("D", "Permanenza di una persona nel pool precario degli enti",
     "Stessa logica degli assegni universitari."),
    ("E_2526", "Nuovi ingressi nel 2025-26",
     "Ingressi residui dopo il picco PNRR del 2024."),
    ("pnrr_ok", "Quota del calo 'fine PNRR' già avvenuta a fine 2026",
     "I progetti PNRR si chiudono entro il 2026."),
    ("tetto_ok", "Quota del calo 'tetto 30 mesi' già avvenuta a fine 2026",
     "Il calo dovuto al tetto di durata si concentra nel 2027."),
    ("s_prec", "Quota di assunti in ruolo che erano precari degli enti",
     "Le assunzioni di ricercatori e tecnologi pescano soprattutto tra i precari interni."),
]

col_u, col_e = st.columns(2)
for col, titolo, lista, val in ((col_u, "Università", IPOTESI_U, pu), (col_e, "Enti pubblici di ricerca", IPOTESI_E, pe)):
    with col:
        st.markdown(f"**Ipotesi sulle grandezze non osservabili: {titolo.lower()}**")
        st.dataframe(pd.DataFrame([(lab, _v(n, val[n]), why) for n, lab, why in lista],
                                  columns=["Ipotesi", "Valore", "Perché"]),
                     hide_index=True, width="stretch")

st.markdown(f"""
**Quanto sono solidi i numeri.** L'ipotesi più incerta è la permanenza tra gli assegni: con
{it(SF.PARAM['D_A'][0])} anni invece di {it(pu['D_A'])} gli usciti sarebbero il
{SF.pct(q_usc[1])} dei passati, con {it(SF.PARAM['D_A'][2])} anni il {SF.pct(q_usc[0])}
(stima centrale: {SF.pct(q['usciti'])}). Indipendentemente dalle ipotesi, dal picco di
dicembre 2024 sono usciti almeno {it(round(lb['usciti_min'], -2))} precari universitari.

**Esclusi:** borse post-laurea, dottorandi, borsisti degli enti.
""")
