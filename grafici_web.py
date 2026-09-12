"""DataFrame -> figure Plotly interattive per la webapp.

Stesso confine di grafici.py ("nessun calcolo di modello: entrano DataFrame, escono
figure"), ma qui esce un go.Figure invece di un PNG. I due moduli convivono: grafici.py
resta la sorgente delle immagini della CLI e del documento, questo serve il browser.

La differenza che conta non è il formato, è l'HOVER: con hovermode="x unified" chi
passa il mouse su un anno legge la colonna intera - tutti i livelli di quell'anno e il
totale - che su un PNG richiederebbe di andare a cercare la tabella.
"""
from __future__ import annotations

import plotly.graph_objects as go

import config as C

# Palette categorica, coerente fra i grafici: lo stesso compartimento ha lo stesso
# colore ovunque compaia, cosi' passare da un tab all'altro non richiede di rileggere
# la legenda.
# I tre gradi del ruolo universitario - ricercatore, associato, ordinario - stanno
# nella stessa famiglia blu con luminosità decrescente: la scala di colore racconta
# la scala di carriera, e le tre fasce restano distinguibili anche da adiacenti.
COL = {"phd": "#7C93C3", "postdoc": "#E8A33D", "rtt": "#5BA88F", "ric_uni": "#4E9DD1",
       "pa": "#2A5F8F", "po": "#12324F",
       "prof": "#1F4E79", "epr_prec": "#C6743A", "epr_ruolo": "#8C5A2B",
       "ta": "#9B8AA6", "attrezz": "#B0B7BE",
       "herd": "#1F4E79", "goverd": "#C6743A", "totale": "#2E7D5B",
       "lordo": "#B3574A", "netto": "#2E7D5B", "obiettivo": "#8A8F98"}

# Modalita' di hover, condivisa da tutti i grafici. E' un flag di modulo e non un
# parametro delle funzioni perche' i grafici sono sette e la leva e' una sola: app.py
# la imposta una volta prima di disegnare. False = nessun riquadro di valori.
#
# Serve perche' su TOUCH il riquadro non si chiude: il dito lo fissa su un anno e non
# esiste il "via il mouse" che su desktop lo fa sparire. Senza un interruttore, chi
# legge da telefono resta con mezzo grafico coperto e nessun modo di scoprirlo.
HOVER: str | bool = "x unified"

_ASSE = dict(showgrid=True, gridcolor="rgba(128,128,128,.22)", zeroline=False)


def _base(titolo: str, y: str, fine: int | None = None, zero: bool = True) -> go.Figure:
    """zero=True ancora l'asse y allo zero: giusto per le aree impilate, dove le altezze
    si sommano e partire da un fondo mobile mentirebbe sulle proporzioni. Per le linee
    di un rapporto - studenti per docente fra 14 e 21, % di PIL fra 0,55 e 0,95 - è
    invece sbagliato: schiaccia tutta la variazione che interessa in un terzo di
    grafico. Li' si lascia autoscalare."""
    f = go.Figure()
    f.update_layout(
        # La fascia in cima e' contesa da tre cose: titolo, legenda e barra strumenti.
        # Su desktop ci stanno; su telefono no, e il modo in cui saltano e' istruttivo.
        # La legenda orizzontale va a capo una voce per riga - organico ne ha otto -
        # e cresce VERSO L'ALTO, quindi si mangia il titolo; la barra strumenti di
        # plotly sta in alto a destra e a schermo stretto finisce sopra il titolo, che
        # nel frattempo occupa quasi tutta la larghezza.
        #
        # Percio' le tre cose si separano invece di spartirsi la stessa banda: il
        # titolo da solo in cima al CONTENITORE, la legenda SOTTO il grafico (dove
        # crescendo verso il basso non incontra nulla, e plotly allarga il margine
        # inferiore da se'), e la barra strumenti spenta da app.py via config.
        #
        # pad.t basso alza il titolo verso il bordo, margin.t alto spinge giu' l'area
        # di disegno: insieme aprono la distanza fra il titolo e cio' che gli sta
        # sotto. height sale di altrettanto, se no la fascia piu' alta si pagherebbe
        # con altrettanto grafico in meno.
        title=dict(text=titolo, font=dict(size=16),
                   yref="container", y=1.0, yanchor="top", pad=dict(t=4)),
        hovermode=HOVER, template="plotly_white",
        margin=dict(l=10, r=10, t=84, b=10), height=486,
        legend=dict(orientation="h", yanchor="top", y=-0.14, xanchor="left", x=0),
        xaxis=dict(title="", range=[C.ANNO0, fine or C.FINE_GRAFICI], **_ASSE),
        yaxis=dict(title=y, rangemode="tozero" if zero else "normal", **_ASSE),
        hoverlabel=dict(namelength=-1))
    return f


def _area(f: go.Figure, df, col: str, nome: str, colore: str, fmt: str = ",.0f") -> None:
    """Una fascia dello stack. stackgroup fa la somma cumulata, ma hovertemplate mostra
    il valore della SINGOLA fascia: è quello che si vuole leggere, non il cumulato."""
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
    mostra le fasce ma non la loro somma, che è il primo numero che si cerca."""
    f.add_trace(go.Scatter(
        x=df["anno"], y=df[cols].sum(axis=1), name=nome, mode="lines",
        line=dict(width=0), showlegend=False,
        hovertemplate="<b>%{y:,.0f}</b><extra><b>" + nome + "</b></extra>"))


# --- ORGANICO ----------------------------------------------------------------------

def organico(df, fine=None) -> go.Figure:
    """Tutto il personale di ricerca pubblico in un solo stack.

    Università ed enti stavano su due grafici, e separati non si potevano confrontare:
    l'occhio non somma due assi con scale diverse (~200k contro ~45k), quindi il ramo
    EPR sembrava grande quanto quello universitario. Impilati sullo stesso asse il
    rapporto fra i due si legge da solo.

    L'ordine è la scala di carriera dal basso - dottorandi, postdoc, RTT, ruolo -
    e gli enti si posano sopra, con una famiglia di colori loro (i marroni) perchè
    sono un ramo diverso, non un gradino ulteriore di quello universitario."""
    f = _base("Personale di ricerca pubblico (teste)", "teste", fine)
    bande = [("phd_teste", "dottorandi", COL["phd"]),
             ("postdoc_teste", "postdoc università", COL["postdoc"]),
             ("rtt_teste", "RTT (tenure track)", COL["rtt"]),
             ("ric_uni_teste", "ricercatori univ. a tempo ind.", COL["ric_uni"]),
             ("pa_teste", "professori associati", COL["pa"]),
             ("po_teste", "professori ordinari", COL["po"]),
             ("epr_precari", "enti: contratti di ricerca", COL["epr_prec"]),
             ("epr_ruolo", "enti: personale di ruolo", COL["epr_ruolo"])]
    for col, nome, c in bande:
        _area(f, df, col, nome, c)
    cols = [c for c, _, _ in bande]
    _totale(f, df, cols, "totale personale di ricerca")
    _totale(f, df, cols[:6], "di cui università")
    _totale(f, df, cols[6:], "di cui enti")
    return f


# --- SPESA -------------------------------------------------------------------------

def spesa_stack(df, fine=None) -> go.Figure:
    f = _base("Spesa pubblica per la ricerca (mld EUR/anno, EUR2026 costanti)",
              "mld EUR/anno", fine)
    for col, nome, c in [("budget_univ_mld", "università, personale", COL["prof"]),
                         ("budget_epr_mld", "enti, personale", COL["epr_ruolo"]),
                         ("attrezz_univ_mld", "università, attrezzature", COL["attrezz"]),
                         ("attrezz_epr_mld", "enti, attrezzature", COL["ta"])]:
        _area(f, df, col, nome, c, fmt=",.2f")
    _totale(f, df, ["budget_univ_mld", "budget_epr_mld", "attrezz_univ_mld",
                    "attrezz_epr_mld"], "spesa totale (mld)")
    return f


def spesa_pil(df, fine=None) -> go.Figure:
    f = _base("Spesa in % del PIL, contro gli obiettivi", "% PIL", fine, zero=False)
    _linea(f, df, "HERD_%PIL", "HERD (università)", COL["herd"], ".3f")
    _linea(f, df, "GOVERD_%PIL", "GOVERD (enti)", COL["goverd"], ".3f")
    _linea(f, df, "RS_pubblica_%PIL", "R&S pubblica (HERD+GOVERD)", COL["totale"],
           ".3f", larghezza=3.0)
    _obiettivo(f, C.HERD_TGT, f"obiettivo HERD {C.HERD_TGT:g}%")
    _obiettivo(f, C.GOVERD_TGT, f"obiettivo GOVERD {C.GOVERD_TGT:g}%")
    _obiettivo(f, C.HERD_TGT + C.GOVERD_TGT,
               f"obiettivo pubblico {C.HERD_TGT + C.GOVERD_TGT:g}%")
    return f


def costo_stato(df, fine=None) -> go.Figure:
    """Costo lordo e le DUE misure di costo netto, che non sono intercambiabili.

    L'IRPEF è la sola imposta ERARIALE: è l'unica parte del rientro che torna allo
    Stato. Addizionali, contributi e IRAP tornano a regioni, comuni e INPS - sono
    denaro pubblico, ma non dello stesso bilancio. Un grafico che mostrasse solo il
    netto di TUTTI i prelievi sotto il titolo "costo per lo Stato" farebbe sembrare
    che rientri il 53% di cio' che lo Stato spende, mentre allo Stato rientra il 18%.
    Si mostra quindi la stessa misura del grafico PNG della CLI - il netto della sola
    IRPEF - cosi' webapp e documento non raccontano due storie diverse. Il netto di
    tutti i prelievi resta nella tabella, alla riga "Retroflusso tot.".."""
    # zero=False perchè l'IRPEF si disegna SOTTO l'asse: con rangemode="tozero"
    # la fascia negativa verrebbe tagliata via.
    f = _base("Costo aggiuntivo per lo Stato rispetto al 2026 (mld EUR/anno)",
              "mld EUR/anno", fine, zero=False)
    f.update_yaxes(zeroline=True, zerolinecolor="rgba(90,90,90,.55)", zerolinewidth=1.2)
    f.add_trace(go.Scatter(
        x=df["anno"], y=df["dStato_univ_mld"] + df["dStato_epr_mld"],
        name="costo lordo", mode="lines", fill="tozeroy",
        line=dict(width=0.5, color=COL["lordo"]), fillcolor="rgba(179,87,74,.28)",
        hovertemplate="%{y:,.2f}<extra>costo lordo</extra>"))
    _linea(f, df, "dStato_netto_irpef_mld",
           "netto della sola IRPEF erariale (cio' che torna allo Stato)",
           COL["netto"], ",.2f", larghezza=3.0)
    # L'IRPEF è un'ENTRATA e si disegna sotto lo zero, come nel PNG della CLI: sopra
    # l'asse cio' che esce, sotto cio' che rientra, e la distanza fra il tetto rosso e
    # la linea verde è esattamente la fascia verde acqua ribaltata.
    f.add_trace(go.Scatter(
        x=df["anno"], y=-df["dIRPEF_mld"], name="IRPEF erariale (entrata)",
        mode="lines", fill="tozeroy", line=dict(width=0.5, color="#29C29C"),
        fillcolor="rgba(41,194,156,.45)",
        hovertemplate="%{y:,.2f}<extra>IRPEF erariale (entrata)</extra>"))
    return f


# --- CARRIERE, DIDATTICA, DENSITà -------------------------------------------------

def carriere(df, fine=None) -> go.Figure:
    f = _base("Precarietà e composizione dell'organico", "%", fine)
    d = df.copy()
    # Le due quote sono COMPLEMENTARI per costruzione, ed è voluto: stessa convenzione
    # di componente_precaria - TESTE (non FTE), università PIU' enti, dottorandi e TA
    # fuori da entrambi i lati. Al numeratore dell'una i soli postdoc (universitari +
    # contratti di ricerca EPR), al numeratore dell'altra tutto il ruolo: professori,
    # ricercatori a tempo indeterminato, RTT e personale di ruolo degli enti. Gli RTT
    # stanno fra gli strutturati perchè il tenure track ha l'esito garantito.
    #
    # NON si usa quota_docente, che sembra la stessa cosa e non lo è: quella è in FTE
    # pesati per alpha, esclude gli RTT, guarda la sola università e tiene i dottorandi
    # al denominatore. Messa qui accanto alla precaria darebbe due convenzioni diverse
    # sullo stesso grafico, cioè due linee che non si possono leggere insieme.
    d["_ruolo"] = 100 - d["componente_precaria"]
    _linea(f, d, "componente_precaria",
           "precari = solo postdoc", COL["postdoc"], ".1f")
    _linea(f, d, "_ruolo", "di ruolo = prof + ric. a tempo ind. + RTT",
           COL["prof"], ".1f")
    return f


def didattica(df, fine=None) -> go.Figure:
    """Il grafico che dice la cosa scomoda: il rapporto PEGGIORA prima di migliorare,
    perchè la didattica si toglie al postdoc più in fretta di quanto il ruolo cresca.
    L'annotazione sul picco è calcolata dai dati, non scritta a mano: se i parametri
    cambiano al punto da togliere la gobba, sparisce da sè."""
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
    f = _base("Densità di personale (FTE per 100.000 abitanti)", "FTE / 100k ab.",
              fine, zero=False)
    _linea(f, df, "densita", "ricercatori università", COL["prof"], ".1f")
    _linea(f, df, "densita_epr", "ricercatori enti", COL["epr_ruolo"], ".1f")
    _linea(f, df, "densita_ric_pub", "ricercatori pubblici (univ. + enti)",
           COL["totale"], ".1f", larghezza=3.0)
    _linea(f, df, "densita_rs_tot", "personale R&S totale, con il TA", COL["ta"], ".1f",
           "dot", 1.8)
    _obiettivo(f, 221.0, "media semplice UE27: 221")
    return f


# --- confronto fra scenari ---------------------------------------------------------

_TRATTO = {"ADI_Manifesto_ric": None, "ERA": "dash", "FLC": "dot"}
_COLORE = {"ADI_Manifesto_ric": COL["totale"], "ERA": COL["herd"], "FLC": COL["lordo"]}
# Il nome interno non è un'etichetta: "ADI_Manifesto_ric" letto a schermo diventa un
# "ric" appeso. Le stesse diciture della CLI, cosi' grafici web e PNG si citano fra loro.
_ETICH = {"ADI_Manifesto_ric": "ADI Manifesto + ric.univ.", "ERA": "ERA paghe oggi",
          "FLC": "FLC"}


def confronto(dfs: dict, col: str, titolo: str, y: str, fmt: str = ",.0f",
              fine=None) -> go.Figure:
    """Una variabile, tutti gli scenari chiesti. Serve al confronto con FLC/ERA: due
    stack non si possono sovrapporre, due linee si."""
    f = _base(titolo, y, fine)
    for nome, df in dfs.items():
        _linea(f, df, col, _ETICH.get(nome, nome.replace("_", " ")),
               _COLORE.get(nome, COL["ta"]), fmt,
               _TRATTO.get(nome), 2.8 if nome == "ADI_Manifesto_ric" else 2.0)
    return f
