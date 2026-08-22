"""DataFrame -> figure Plotly interattive per la webapp.

Stesso confine di grafici.py ("nessun calcolo di modello: entrano DataFrame, escono
figure"), ma qui esce un go.Figure invece di un PNG. I due moduli convivono: grafici.py
resta la sorgente delle immagini della CLI e del documento, questo serve il browser.

La differenza che conta non e' il formato, e' l'HOVER: con hovermode="x unified" chi
passa il mouse su un anno legge la colonna intera - tutti i livelli di quell'anno e il
totale - che su un PNG richiederebbe di andare a cercare la tabella.
"""
from __future__ import annotations

import plotly.graph_objects as go

import config as C

# Palette categorica, coerente fra i grafici: lo stesso compartimento ha lo stesso
# colore ovunque compaia, cosi' passare da un tab all'altro non richiede di rileggere
# la legenda.
COL = {"phd": "#7C93C3", "postdoc": "#E8A33D", "rtt": "#5BA88F", "ric_uni": "#3E7CB1",
       "prof": "#1F4E79", "epr_prec": "#C6743A", "epr_ruolo": "#8C5A2B",
       "ta": "#9B8AA6", "attrezz": "#B0B7BE",
       "herd": "#1F4E79", "goverd": "#C6743A", "totale": "#2E7D5B",
       "lordo": "#B3574A", "netto": "#2E7D5B", "obiettivo": "#8A8F98"}

_ASSE = dict(showgrid=True, gridcolor="rgba(128,128,128,.22)", zeroline=False)


def _base(titolo: str, y: str, fine: int | None = None, zero: bool = True) -> go.Figure:
    """zero=True ancora l'asse y allo zero: giusto per le aree impilate, dove le altezze
    si sommano e partire da un fondo mobile mentirebbe sulle proporzioni. Per le linee
    di un rapporto - studenti per docente fra 14 e 21, % di PIL fra 0,55 e 0,95 - e'
    invece sbagliato: schiaccia tutta la variazione che interessa in un terzo di
    grafico. Li' si lascia autoscalare."""
    f = go.Figure()
    f.update_layout(
        title=dict(text=titolo, font=dict(size=16)),
        hovermode="x unified", template="plotly_white",
        margin=dict(l=10, r=10, t=52, b=10), height=440,
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0),
        xaxis=dict(title="", range=[C.ANNO0, fine or C.FINE_GRAFICI], **_ASSE),
        yaxis=dict(title=y, rangemode="tozero" if zero else "normal", **_ASSE),
        hoverlabel=dict(namelength=-1))
    return f


def _area(f: go.Figure, df, col: str, nome: str, colore: str, fmt: str = ",.0f") -> None:
    """Una fascia dello stack. stackgroup fa la somma cumulata, ma hovertemplate mostra
    il valore della SINGOLA fascia: e' quello che si vuole leggere, non il cumulato."""
    f.add_trace(go.Scatter(
        x=df["anno"], y=df[col], name=nome, mode="lines", stackgroup="uno",
        line=dict(width=0.5, color=colore), fillcolor=colore,
        hovertemplate="%{y:" + fmt + "}<extra>" + nome + "</extra>"))


def _linea(f: go.Figure, df, col: str, nome: str, colore: str, fmt: str = ",.0f",
           tratteggio: str | None = None, larghezza: float = 2.4) -> None:
    f.add_trace(go.Scatter(
        x=df["anno"], y=df[col], name=nome, mode="lines",
        line=dict(width=larghezza, color=colore, dash=tratteggio),
        hovertemplate="%{y:" + fmt + "}<extra>" + nome + "</extra>"))


def _obiettivo(f: go.Figure, y: float, testo: str) -> None:
    f.add_hline(y=y, line=dict(color=COL["obiettivo"], width=1.3, dash="dash"),
                annotation_text=testo, annotation_position="top left",
                annotation_font=dict(size=11, color=COL["obiettivo"]))


def _totale(f: go.Figure, df, cols: list[str], nome: str) -> None:
    """Traccia invisibile che aggiunge il totale al riquadro dell'hover. Senza, lo stack
    mostra le fasce ma non la loro somma, che e' il primo numero che si cerca."""
    f.add_trace(go.Scatter(
        x=df["anno"], y=df[cols].sum(axis=1), name=nome, mode="lines",
        line=dict(width=0), showlegend=False,
        hovertemplate="<b>%{y:,.0f}</b><extra><b>" + nome + "</b></extra>"))


# --- ORGANICO ----------------------------------------------------------------------

def organico_uni(df, fine=None) -> go.Figure:
    f = _base("Organico universitario (teste)", "teste", fine)
    for col, nome, c in [("phd_teste", "dottorandi", COL["phd"]),
                         ("postdoc_teste", "postdoc", COL["postdoc"]),
                         ("rtt_teste", "RTT", COL["rtt"]),
                         ("ric_uni_teste", "ricercatori univ.", COL["ric_uni"]),
                         ("prof_teste", "professori PO/PA", COL["prof"])]:
        _area(f, df, col, nome, c)
    _totale(f, df, ["phd_teste", "postdoc_teste", "rtt_teste", "ric_uni_teste",
                    "prof_teste"], "totale universita'")
    return f


def organico_epr_ta(df, fine=None) -> go.Figure:
    f = _base("Enti pubblici di ricerca e personale tecnico-amministrativo (teste)",
              "teste", fine)
    for col, nome, c in [("epr_precari", "EPR contratti di ricerca", COL["epr_prec"]),
                         ("epr_ruolo", "EPR di ruolo", COL["epr_ruolo"]),
                         ("ta_teste", "TA (universita' + enti)", COL["ta"])]:
        _area(f, df, col, nome, c)
    _totale(f, df, ["epr_precari", "epr_ruolo", "ta_teste"], "totale")
    return f


# --- SPESA -------------------------------------------------------------------------

def spesa_stack(df, fine=None) -> go.Figure:
    f = _base("Spesa pubblica per la ricerca (mld EUR/anno, EUR2026 costanti)",
              "mld EUR/anno", fine)
    for col, nome, c in [("budget_univ_mld", "universita', personale", COL["prof"]),
                         ("budget_epr_mld", "enti, personale", COL["epr_ruolo"]),
                         ("attrezz_univ_mld", "universita', attrezzature", COL["attrezz"]),
                         ("attrezz_epr_mld", "enti, attrezzature", COL["ta"])]:
        _area(f, df, col, nome, c, fmt=",.2f")
    _totale(f, df, ["budget_univ_mld", "budget_epr_mld", "attrezz_univ_mld",
                    "attrezz_epr_mld"], "spesa totale (mld)")
    return f


def spesa_pil(df, fine=None) -> go.Figure:
    f = _base("Spesa in % del PIL, contro gli obiettivi", "% PIL", fine, zero=False)
    _linea(f, df, "HERD_%PIL", "HERD (universita')", COL["herd"], ".3f")
    _linea(f, df, "GOVERD_%PIL", "GOVERD (enti)", COL["goverd"], ".3f")
    _linea(f, df, "RS_pubblica_%PIL", "R&S pubblica (HERD+GOVERD)", COL["totale"],
           ".3f", larghezza=3.0)
    _obiettivo(f, C.HERD_TGT, f"obiettivo HERD {C.HERD_TGT:g}%")
    _obiettivo(f, C.GOVERD_TGT, f"obiettivo GOVERD {C.GOVERD_TGT:g}%")
    _obiettivo(f, C.HERD_TGT + C.GOVERD_TGT,
               f"obiettivo pubblico {C.HERD_TGT + C.GOVERD_TGT:g}%")
    return f


def costo_stato(df, fine=None) -> go.Figure:
    """Costo LORDO e costo NETTO del retroflusso fiscale. Le due misure non vanno
    sommate: la seconda e' la prima meno le imposte e i contributi che rientrano."""
    f = _base("Costo aggiuntivo per lo Stato rispetto al 2026 (mld EUR/anno)",
              "mld EUR/anno", fine)
    f.add_trace(go.Scatter(
        x=df["anno"], y=df["dStato_univ_mld"] + df["dStato_epr_mld"],
        name="costo lordo", mode="lines", fill="tozeroy",
        line=dict(width=0.5, color=COL["lordo"]), fillcolor="rgba(179,87,74,.28)",
        hovertemplate="%{y:,.2f}<extra>costo lordo</extra>"))
    _linea(f, df, "dStato_netto_tot_mld",
           "netto del retroflusso (IRPEF + addizionali + contributi + IRAP)",
           COL["netto"], ",.2f", larghezza=3.0)
    _linea(f, df, "dRetro_mld", "retroflusso fiscale", COL["ta"], ",.2f", "dot", 1.8)
    return f


# --- CARRIERE, DIDATTICA, DENSITA' -------------------------------------------------

def carriere(df, fine=None) -> go.Figure:
    f = _base("Precarieta' e composizione dell'organico", "%", fine)
    d = df.copy()
    d["_doc"] = d["quota_docente"] * 100
    d["_p1"] = d["P1_effettivo"] * 100
    _linea(f, d, "componente_precaria", "componente precaria (% postdoc)",
           COL["postdoc"], ".1f")
    _linea(f, d, "componente_precaria_rtt", "idem, con gli RTT fra i precari",
           COL["rtt"], ".1f", "dot", 1.8)
    _linea(f, d, "_doc", "quota di ruolo sull'organico", COL["prof"], ".1f")
    _linea(f, d, "_p1", "P1: dottori che proseguono", COL["ric_uni"], ".1f", "dash", 1.8)
    return f


def didattica(df, fine=None) -> go.Figure:
    """Il grafico che dice la cosa scomoda: il rapporto PEGGIORA prima di migliorare,
    perche' la didattica si toglie al postdoc piu' in fretta di quanto il ruolo cresca.
    L'annotazione sul picco e' calcolata dai dati, non scritta a mano: se i parametri
    cambiano al punto da togliere la gobba, sparisce da se'."""
    f = _base("Studenti per docente (FTE didattici)", "studenti / docente", fine,
              zero=False)
    _linea(f, df, "stud_per_doc", "studenti fermi ai livelli di oggi", COL["prof"], ".2f")
    _linea(f, df, "stud_per_doc_pop", "studenti proporzionali alla popolazione",
           COL["ric_uni"], ".2f", "dot", 1.8)
    _obiettivo(f, C.STUD_DOC_TGT, f"media UE {C.STUD_DOC_TGT:g}")
    _obiettivo(f, C.STUD_DOC_OGGI, f"oggi {C.STUD_DOC_OGGI:g}")
    vis = df[df["anno"] <= (fine or C.FINE_GRAFICI)]
    i = vis["stud_per_doc"].idxmax()
    if vis.loc[i, "stud_per_doc"] > vis["stud_per_doc"].iloc[0]:
        f.add_annotation(
            x=int(vis.loc[i, "anno"]), y=float(vis.loc[i, "stud_per_doc"]),
            text=f"picco {vis.loc[i, 'stud_per_doc']:.1f} nel {int(vis.loc[i, 'anno'])}:"
                 "<br>il rapporto peggiora prima di migliorare",
            showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=1.2, ax=46, ay=-48,
            font=dict(size=11), align="left", bgcolor="rgba(255,255,255,.85)",
            bordercolor=COL["obiettivo"], borderwidth=1, borderpad=4)
    return f


def densita(df, fine=None) -> go.Figure:
    f = _base("Densita' di personale (FTE per 100.000 abitanti)", "FTE / 100k ab.",
              fine, zero=False)
    _linea(f, df, "densita", "ricercatori universita'", COL["prof"], ".1f")
    _linea(f, df, "densita_epr", "ricercatori enti", COL["epr_ruolo"], ".1f")
    _linea(f, df, "densita_ric_pub", "ricercatori pubblici (univ. + enti)",
           COL["totale"], ".1f", larghezza=3.0)
    _linea(f, df, "densita_rs_tot", "personale R&S totale, con il TA", COL["ta"], ".1f",
           "dot", 1.8)
    _obiettivo(f, 221.0, "media semplice UE27: 221")
    return f


# --- confronto fra scenari ---------------------------------------------------------

_TRATTO = {"ERA_PPP_ric": None, "ERA": "dash", "FLC": "dot"}
_COLORE = {"ERA_PPP_ric": COL["totale"], "ERA": COL["herd"], "FLC": COL["lordo"]}


def confronto(dfs: dict, col: str, titolo: str, y: str, fmt: str = ",.0f",
              fine=None) -> go.Figure:
    """Una variabile, tutti gli scenari chiesti. Serve al confronto con FLC/ERA: due
    stack non si possono sovrapporre, due linee si."""
    f = _base(titolo, y, fine)
    for nome, df in dfs.items():
        _linea(f, df, col, nome.replace("_", " "), _COLORE.get(nome, COL["ta"]), fmt,
               _TRATTO.get(nome), 2.8 if nome == "ERA_PPP_ric" else 2.0)
    return f
