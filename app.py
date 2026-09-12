"""Webapp del modello di transizione del finanziamento della ricerca pubblica.

Front-end di scenario.esegui(): la sidebar raccoglie i parametri, il corpo mostra KPI e
grafici interattivi. Nessun calcolo vive qui - se un numero non viene da un DataFrame
del modello, è un bug.

Due livelli di parametri: dodici leve in chiaro, tutto il resto dentro "Impostazioni
avanzate". Chi arriva senza sapere cos'è un GOVERD deve poter muovere le paghe e
vedere cosa succede; chi sa cos'è deve poter arrivare a ogni flag della CLI.
"""
from __future__ import annotations

import streamlit as st

import config as C
import grafici_web as G
import scenario as S
from tabelle import RIGHE_TAB, righe_con_prepens, tabella_scenario

# initial_sidebar_state="expanded": la sidebar NON è un accessorio, è il pannello di
# controllo. Con "auto" Streamlit la richiude sotto una certa larghezza e chi arriva
# vede una pagina di risultati senza alcuna leva visibile.
st.set_page_config(page_title="Transizione del finanziamento della ricerca",
                   page_icon="🔬", layout="wide", initial_sidebar_state="expanded")

ANNO_FINE = C.FINE_GRAFICI

# I preset non sono scorciatoie estetiche: sono le configurazioni che il documento
# discute, e servono a far vedere subito che il modello risponde alle leve.
PRESET: dict[str, dict] = {
    "ADI Manifesto": {},
    "Paghe top-5 europei (x1,65)": {"uplift_ppp": C.UPLIFT_PPP_TOP5},
    "Solo cattedre (nessun ricercatore univ a tempo ind.)": {"quota_ric_uni": 0.0},
    "Senza blocco scatti temporaneo": {"scatti_blocco_anni": 0,
                                                "scatti_blocco2_anni": 0},
    "Postdoc breve (3 anni in media invece che 5)": {"precari_anni": 3.0, "rtt_anni": 5},
}


@st.cache_data(show_spinner="Simulazione in corso...", max_entries=64)
def _run(chiave: tuple, quali: tuple[str, ...]) -> S.Risultato:
    """La chiave è il dict dei parametri reso hashable: Streamlit la usa per la cache,
    quindi tornare su una combinazione già vista non ricalcola nulla."""
    return S.esegui(dict(chiave), quali=quali)


def _kpi(df, col: str, dec: int = 1, scala: float = 1.0):
    """Valore a fine orizzonte grafico e variazione rispetto all'anno base."""
    a = df[df["anno"] == C.ANNO0][col].iloc[0] * scala
    b = df[df["anno"] == ANNO_FINE][col].iloc[0] * scala
    return f"{b:,.{dec}f}", f"{b - a:+,.{dec}f}"


# =====================================================================================
# SIDEBAR
# =====================================================================================
st.sidebar.title("Leve di scenario")

nome_preset = st.sidebar.selectbox(
    "Configurazione di partenza", list(PRESET),
    help="Sceglie un punto di partenza. Ogni leva resta poi modificabile qui sotto.")
base = S.con_default(PRESET[nome_preset])
# Streamlit ricostruisce i widget quando cambia la chiave: legando la key al preset, i
# cursori si riposizionano davvero invece di restare sul valore vecchio.
k = f"_{list(PRESET).index(nome_preset)}"

p: dict = dict(base)

st.sidebar.subheader("Obiettivi di spesa")
p["herd_tgt"] = st.sidebar.slider(
    "HERD - università (% PIL)", 0.30, 1.20, float(base["herd_tgt"]), 0.01, key="h" + k,
    help="Spesa per ricerca del settore universitario. Oggi: 0,36%. L'obiettivo preimpostato 0,68% "
         "è la media degli HERD dei cinque paesi europei già sopra il 3% di spesa totale, riportata al 3%")
p["goverd_tgt"] = st.sidebar.slider(
    "GOVERD - enti pubblici (% PIL)", 0.10, 0.60, float(base["goverd_tgt"]), 0.01,
    key="g" + k,
    help="Spesa per ricerca degli enti pubblici. Oggi 0,21%. L'obiettivo preimpostato 0,23% "
         "è la media degli HERD dei cinque paesi europei già sopra il 3% di spesa totale, riportata al 3%")

st.sidebar.subheader("Paghe e composizione")
p["uplift_ppp"] = st.sidebar.slider(
    "Moltiplicatore delle paghe", 1.00, 1.80, float(base["uplift_ppp"]), 0.01,
    key="w" + k,
    help="1,00 = rimanere agli stipendi di oggi. 1,16 = raggiungere la media europea a parità di potere d'acquisto. "
         "1,65 = raggiungere la media dei cinque paesi che pagano di più. A spesa fissa, pagare di "
         "più significa assumere di meno (dove la spesa è definita dagli obiettivi HERD e GOVERD)")
p["quota_ric_uni"] = st.sidebar.slider(
    "Quota di ricercatori universitari sul ruolo", 0.0, 1.0,
    float(base["quota_ric_uni"]), 0.05, key="q" + k,
    help="La leva di COMPOSIZIONE: un ricercatore a "
         "tempo indeterminato con inquadramento da ente costa meno di un professore e "
         "fa più ricerca (quota-ricerca 0,75 contro 0,50), quindi rende 2x FTE per "
         "euro. 0 = solo cattedre.")
p["borsa_tgt"] = st.sidebar.slider(
    "Borsa di dottorato (EUR/mese netti)", 1195.0, 2200.0, float(base["borsa_tgt"]),
    5.0, key="b" + k, help=f"Oggi {C.BORSA_OGGI:,.0f} EUR/mese netti.")

st.sidebar.subheader("Carriera")
p["precari_anni"] = st.sidebar.slider(
    "Anni di postdoc", 2.0, 8.0, float(base["precari_anni"]), 0.5, key="pa" + k,
    help="Permanenza media nel postdoc. Allungarla sposta lo stato stazionario: più "
         "precari strutturali e ingresso in ruolo più tardi, quindi carriera di ruolo "
         "più corta.")
p["rtt_anni"] = st.sidebar.slider(
    "Anni di RTT (tenure track)", 3, 8, int(base["rtt_anni"]), 1, key="rt" + k)
p["p2_tgt"] = st.sidebar.slider(
    "P2: quota di postdoc che entra in ruolo", 0.30, 1.00, float(base["p2_tgt"]), 0.05,
    key="p2" + k,
    help="1,00 = nessun filtro dopo il dottorato: chi entra nel postdoc ha la carriera "
         "garantita. Sotto 1 il postdoc resta un passaggio selettivo.")
p["stab_phd"] = st.sidebar.slider(
    "Quota di dottori che resta in accademia", 0.10, 0.60, float(base["stab_phd"]), 0.01,
    key="sp" + k,
    help="Il filtro all'uscita dal dottorato. Insieme a P2 determina P1, cioè quanti "
         "dottori proseguono.")
p["ramp"] = st.sidebar.slider(
    "Anni di rampa delle riforme", 3, 25, int(base["ramp"]), 1, key="rp" + k,
    help="In quanti anni le leve (paghe, P2, flusso di dottorandi) arrivano a regime. "
         "Nessuna si applica di colpo.")

_ra = st.sidebar.slider(
    "Anni per togliere la didattica al postdoc", 0, 30,
    int(base["ramp_alpha_prec"] or 0), 1, key="ra" + k,
    help="Su quanti anni la quota-ricerca del postdoc sale da "
         f"{C.ALPHA_PREC_OGGI:.2f} a {C.ALPHA_PREC_TGT:.2f}, cioè quanto in fretta "
         "gli si toglie la didattica. 0 = segue la rampa generale qui sopra.")
p["ramp_alpha_prec"] = _ra or None

st.sidebar.subheader("Austerità")
scatti = st.sidebar.checkbox(
    "Blocco degli scatti di anzianità", value=int(base["scatti_blocco_anni"]) > 0,
    key="sb" + k,
    help="Misura di austerità dentro un piano di espansione: congela gli scatti salariali per "
         "alcuni anni per professori e ricercatori a tempo indeterminato. " \
         "Accesa per default nel modello per smussare i picchi di spesa transitori.")
if not scatti:
    p["scatti_blocco_anni"] = p["scatti_blocco2_anni"] = 0

# --- avanzate ----------------------------------------------------------------------
st.sidebar.subheader("Impostazioni avanzate")

with st.sidebar.expander("Enti pubblici di ricerca"):
    p["epr_ruolo"] = st.number_input("Ruolo oggi (teste)", 0, 80_000,
                                     int(base["epr_ruolo"]), 100, key="e1" + k)
    p["epr_precari"] = st.number_input("Precari oggi (teste)", 0, 40_000,
                                       int(base["epr_precari"]), 100, key="e2" + k)
    p["epr_non_mur"] = st.number_input("Ricercatori GOV fuori dagli enti MUR", 0, 60_000,
                                       int(base["epr_non_mur"]), 100, key="e3" + k)
    p["costo_epr_ruolo"] = st.number_input("Costo di un ricercatore di ruolo (EUR)",
                                           0, 200_000, int(base["costo_epr_ruolo"]),
                                           500, key="e4" + k)
    p["epr_quota_i_tgt"] = st.slider("Quota obiettivo livello I", 0.0, 0.6,
                                     float(base["epr_quota_i_tgt"]), 0.01, key="e5" + k)
    p["epr_quota_ii_tgt"] = st.slider("Quota obiettivo livello II", 0.0, 0.8,
                                      float(base["epr_quota_ii_tgt"]), 0.01, key="e6" + k)
    p["phd_nel_diretto"] = st.slider("Quota di dottori nel concorso diretto", 0.0, 1.0,
                                     float(base["phd_nel_diretto"]), 0.05, key="e7" + k)
    p["epr_pav_gain"] = st.slider("Guadagno sul pavimento GOVERD", 0.0, 1.0,
                                  float(base["epr_pav_gain"]), 0.05, key="e8" + k)
    p["no_goverd_pavimento"] = st.checkbox("Togli il pavimento di spesa degli enti",
                                           bool(base["no_goverd_pavimento"]),
                                           key="e9" + k)

with st.sidebar.expander("Personale tecnico-amministrativo"):
    p["ta_elast"] = st.slider("Elasticità del TA sui ricercatori", 0.0, 4.0,
                              float(base["ta_elast"]), 0.1, key="t1" + k,
                              help="Quanti TA in più per ogni ricercatore in più.")
    p["costo_ta"] = st.number_input("Costo di un TA (EUR)", 0, 120_000,
                                    int(base["costo_ta"]), 500, key="t2" + k)
    p["ta_uplift"] = st.slider("Moltiplicatore di costo del TA di ricerca", 1.0, 3.0,
                               float(base["ta_uplift"]), 0.05, key="t3" + k)
    p["ta_cap"] = st.number_input("Tetto al numero di TA (0 = quello di config)", 0,
                                  300_000, int(C.TA_CAP), 1_000, key="t4" + k) or None
    p["ta_segue_w"] = st.checkbox("Il TA segue le paghe W", bool(base["ta_segue_w"]),
                                  key="t5" + k)

with st.sidebar.expander("Postdoc e incarichi di ricerca"):
    p["quota_incarico"] = st.slider(
        "Quota di postdoc con diritto all'incarico", 0.0, 1.0,
        float(base["quota_incarico"]), 0.01, key="i1" + k,
        help="L'incarico di ricerca è esente IRPEF e costa meno: muove insieme platea "
             "esente, costo medio del postdoc e spesa.")
    p["anni_incarico"] = st.slider("Anni di postdoc coperti dall'incarico di ricerca", 0.0, 6.0,
                                   float(base["anni_incarico"]), 0.5, key="i2" + k)
    p["costo_phd"] = st.number_input("Costo di un dottorando (EUR)", 0, 80_000,
                                     int(base["costo_phd"]), 500, key="i3" + k)
    p["phd_in_fte"] = st.checkbox("Conta i dottorandi negli FTE",
                                  bool(base["phd_in_fte"]), key="i4" + k)
    p["ramp_phd"] = st.slider("Anni di rampa della borsa", 1, 20, int(base["ramp_phd"]),
                              1, key="i5" + k)

with st.sidebar.expander("Stock di partenza e calibrazione"):
    p["perm_oggi"] = st.number_input("Personale di ruolo oggi (teste)", 0, 200_000,
                                     int(base["perm_oggi"]), 100, key="s1" + k)
    p["ric_uni_ruolo_oggi"] = st.number_input("Ricercatori univ. di ruolo oggi", 0,
                                              100_000, int(base["ric_uni_ruolo_oggi"]),
                                              100, key="s2" + k)
    _po = st.number_input("Postdoc oggi (0 = ricavalo dal gap Eurostat)", 0, 200_000, 0,
                          500, key="s3" + k)
    p["precari_oggi"] = _po or None
    p["p2_hist"] = st.slider("P2 storico", 0.0, 1.0, float(base["p2_hist"]), 0.01,
                             key="s4" + k)
    p["p2_min"] = st.slider("P2 minimo lungo la rampa", 0.0, 1.0, float(base["p2_min"]),
                            0.01, key="s5" + k)
    p["quota_po_tgt"] = st.slider("Quota obiettivo di ordinari", 0.0, 1.0,
                                  float(base["quota_po_tgt"]), 0.01, key="s6" + k)
    _lh = st.number_input("lambda HERD (0 = calibra dal dato)", 0.0, 1.0, 0.0, 0.01,
                          key="s7" + k)
    p["lambda_he"] = _lh or None
    _su = st.number_input("Supporto (valore negativo = calibra)", -1.0, 1.0, -1.0, 0.01,
                          key="s8" + k)
    p["supporto"] = None if _su < 0 else _su

with st.sidebar.expander("Blocco degli scatti e attrezzature"):
    if scatti:
        p["scatti_blocco_da"] = st.number_input("1a finestra: primo anno", 2026, 2080,
                                                int(base["scatti_blocco_da"]), 1,
                                                key="d6" + k)
        p["scatti_blocco_anni"] = st.slider("1a finestra: anni", 0, 15,
                                            int(base["scatti_blocco_anni"]), 1,
                                            key="d7" + k)
        p["scatti_blocco2_da"] = st.number_input("2a finestra: primo anno", 2026, 2080,
                                                 int(base["scatti_blocco2_da"]), 1,
                                                 key="d8" + k)
        p["scatti_blocco2_anni"] = st.slider("2a finestra: anni", 0, 15,
                                             int(base["scatti_blocco2_anni"]), 1,
                                             key="d9" + k)
    else:
        st.caption("Blocco scatti spento: accendilo qui sopra per regolare le finestre.")
    p["no_attrezzature"] = st.checkbox("Spegni l'inviluppo delle attrezzature",
                                       bool(base["no_attrezzature"]), key="da" + k)

# Ultimo perchè è la leva più specialistica: non cambia lo stato stazionario, serve
# solo a smorzare l'onda di pensionamenti nel mezzo della transizione.
with st.sidebar.expander("Prepensionamento"):
    p["prepens_anni"] = st.slider(
        "Anni di anticipo", 0, 8, int(base["prepens_anni"]), 1, key="pp" + k,
        help="0 = leva spenta. Anticipa le uscite prima del picco dell'organico, per "
             "smorzare la gobba senza toccare lo stato stazionario.")
    p["prepens_ades"] = st.slider(
        "Adesione al centro della finestra", 0.0, 1.0, float(base["prepens_ades"]),
        0.05, key="pd" + k, help="Quota di eleggibili che accetta.")
    p["prepens_centro_auto"] = st.checkbox("Centra la finestra sul picco automaticamente",
                                           bool(base["prepens_centro_auto"]),
                                           key="d1" + k)
    p["prepens_centro"] = st.number_input("Anno centrale della finestra", 2026, 2080,
                                          int(base["prepens_centro"]), 1, key="d2" + k)
    p["prepens_sigma"] = st.slider("Ampiezza della finestra (sigma, anni)", 1.0, 25.0,
                                   float(base["prepens_sigma"]), 0.5, key="d3" + k)
    p["prepens_asimm"] = st.slider("Asimmetria della finestra", 0.1, 3.0,
                                   float(base["prepens_asimm"]), 0.1, key="d4" + k)
    p["prepens_coda"] = st.slider("Coda della finestra", 0.0, 1.0,
                                  float(base["prepens_coda"]), 0.05, key="d5" + k)

confronta = st.sidebar.checkbox(
    "Confronta con gli scenari FLC ed ERA", False,
    help="Aggiunge i due baseline tutto-cattedre. Costa due simulazioni in più.")

# Barra strumenti di plotly spenta: zoom e pan non servono - l'asse degli anni ha un
# intervallo fisso - e in compenso a schermo stretto le icone finiscono sopra il
# titolo del grafico. Resta il pulsante schermo intero di Streamlit.
CFG = {"displayModeBar": False}

# =====================================================================================
# ESECUZIONE
# =====================================================================================
st.title("Transizione del finanziamento della ricerca pubblica italiana")
st.caption(
    f"Modello stock-flow per coorte, {C.ANNO0}-{C.FINE_GRAFICI}. Valori in "
    f"EUR{C.ANNO0} (adeguamento all'inflazione implicito), a PIL fermo ({C.PIL_MLN:,.0f} mln). I costi di scenario "
    f"sono aggiuntivi rispetto al finanziamento {C.ANNO0}.")

quali = S.NOMI_SCENARI if confronta else ("ADI_Manifesto_ric",)
try:
    res = _run(tuple(sorted(p.items(), key=lambda kv: kv[0])), quali)
except ValueError as e:
    st.error(f"Parametri incoerenti: {e}")
    st.stop()

df = res.dfs["ADI_Manifesto_ric"]
tg, W, q = res.target["ADI_Manifesto_ric"]

# --- KPI ---------------------------------------------------------------------------
st.subheader(f"Situazione al {ANNO_FINE}")
c = st.columns(4)
v, d = _kpi(df, "densita_ric_pub")
c[0].metric("Ricercatori pubblici / 100k ab.", v, d, help="Media semplice UE27: 221")
v, d = _kpi(df, "HERD_%PIL", 3)
c[1].metric("HERD (% PIL)", v, d, help=f"Obiettivo {C.HERD_TGT:g}%")
v, d = _kpi(df, "GOVERD_%PIL", 3)
c[2].metric("GOVERD (% PIL)", v, d, help=f"Obiettivo {C.GOVERD_TGT:g}%")
v, d = _kpi(df, "RS_pubblica_%PIL", 3)
c[3].metric("R&S pubblica (% PIL)", v, d,
            help=f"Obiettivo {C.HERD_TGT + C.GOVERD_TGT:g}%")

c = st.columns(4)
f0, f1 = df[df["anno"] == C.ANNO0].iloc[0], df[df["anno"] == ANNO_FINE].iloc[0]
lordo0 = f0["dStato_univ_mld"] + f0["dStato_epr_mld"]
lordo1 = f1["dStato_univ_mld"] + f1["dStato_epr_mld"]
c[0].metric("Costo lordo (mld/anno)", f"{lordo1:,.1f}", f"{lordo1 - lordo0:+,.1f}",
            help="Maggior costo a carico dello Stato.")
c[1].metric("Costo netto della sola IRPEF (mld/anno)",
            f"{f1['dStato_netto_irpef_mld']:,.1f}",
            f"{f1['dStato_netto_irpef_mld'] - f0['dStato_netto_irpef_mld']:+,.1f}",
            help="L'IRPEF è la sola imposta erariale, cioè l'unica parte del rientro "
                 "che torna allo Stato. Contando anche addizionali, contributi e IRAP "
                 f"- che vanno a regioni, comuni e INPS - il netto scende a "
                 f"{f1['dStato_netto_tot_mld']:,.1f} mld/anno.")
v, d = _kpi(df, "ruolo_teste", 0)
c[2].metric("Personale di ruolo (teste)", v, d)
v, d = _kpi(df, "componente_precaria")
c[3].metric("Componente precaria (%)", v, d, delta_color="inverse",
            help="Quota di postdoc sul personale di ricerca.")

# --- grafici -----------------------------------------------------------------------
def _grafico(nome: str, fn, *args) -> None:
    """Un grafico, con sopra il suo interruttore dei valori.

    Il declic del riquadro dei numeri. Su desktop il riquadro compare al passaggio del
    mouse e sparisce da se'; su TOUCH no - il dito lo fissa su un anno e non esiste un
    "via il mouse" che lo tolga. Due dettagli che non sono dettagli:

    - l'interruttore sta sopra OGNI grafico, non uno solo per pagina. Da telefono si
      legge un grafico alla volta, e il comando che libera quello che stai guardando
      non puo' essere tre schermate piu' su. Per lo stesso motivo non sta in sidebar,
      che su mobile e' chiusa dietro il pulsante ">>".
    - la key del grafico si porta dentro lo stato dell'interruttore. Senza, Streamlit
      AGGIORNA il grafico gia' montato: plotly recepisce la nuova modalita' di hover,
      ma il riquadro aperto col dito resta disegnato dov'e' e spegnere l'interruttore
      sembra non fare nulla. Cambiando key il grafico viene RIMONTATO da zero, e il
      riquadro se ne va insieme al vecchio nodo.

    G.HOVER va impostato PRIMA di costruire la figura: i grafici leggono la modalita'
    dal flag di modulo, non da un parametro.
    """
    on = st.toggle("Mostra i valori sul grafico", True, key="hv_" + nome,
                   help="Il riquadro con i numeri di un singolo anno. Spegnilo per "
                        "liberare il grafico: da telefono è l'unico modo di "
                        "chiuderlo dopo averlo aperto con un tocco.")
    G.HOVER = "x unified" if on else False
    st.plotly_chart(fn(*args), width="stretch", config=CFG, key=f"g_{nome}_{int(on)}")


t1, t2, t4, t5 = st.tabs(["Organico", "Spesa", "Didattica", "Tabella"])

with t1:
    st.markdown("Chi c'è nel sistema, anno per anno. Passa il mouse su un anno - o "
                "toccalo, da telefono - per leggere tutti i livelli insieme; clicca "
                "una voce in legenda per toglierla. Il riquadro dei numeri si chiude "
                "con l'interruttore sopra ciascun grafico.")
    _grafico("organico", G.organico, df, ANNO_FINE)
    st.markdown("La precarietà in quota: quanti stanno in un "
                "compartimento a esito incerto rispetto al totale. ")
    _grafico("carriere", G.carriere, df, ANNO_FINE)
    _grafico("densita", G.densita, df, ANNO_FINE)
    if confronta:
        _grafico("dens_conf", G.confronto, res.dfs, "densita_ric_pub",
                 "Densità di ricercatori pubblici: confronto",
                 "FTE / 100k ab.", ".1f", ANNO_FINE)

with t2:
    st.markdown("Due misure che non vanno sommate fra loro: la spesa in mld è il "
                "bilancio pubblico, la % di PIL è la contabilità Eurostat della R&S.")
    _grafico("spesa_stack", G.spesa_stack, df, ANNO_FINE)
    _grafico("spesa_pil", G.spesa_pil, df, ANNO_FINE)
    _grafico("costo_stato", G.costo_stato, df, ANNO_FINE)
    if confronta:
        _grafico("pil_conf", G.confronto, res.dfs, "RS_pubblica_%PIL",
                 "R&S pubblica in % PIL: confronto", "% PIL", ".3f", ANNO_FINE)

with t4:
    st.markdown(
        f"Il denominatore sono gli FTE **didattici**, cioè le teste pesate per "
        f"`1-alpha`. Il postdoc è l'unico peso che si muove nel tempo: parte da "
        f"{1 - C.alpha_precari(0):.2f} e si azzera a fine rampa, perchè il piano gli "
        f"toglie la didattica.")
    _grafico("didattica", G.didattica, df, ANNO_FINE)
    st.info("Il traguardo della media UE non è raggiunto in tutti gli scenari, e il "
            "rapporto può **peggiorare prima di migliorare**: togliere la didattica al "
            "postdoc può togliere denominatore (persone che fanno didattica) più in fretta di quanto le assunzioni lo "
            "ricostruiscano.")

with t5:
    anni = [a for a in (2026, 2030, 2035, 2040, 2050, 2060, 2070, 2080)
            if a <= C.ANNO0 + C.ORIZZONTE]
    righe = righe_con_prepens() if p["prepens_anni"] > 0 and p["prepens_ades"] > 0 \
        else RIGHE_TAB
    st.dataframe(tabella_scenario(df, anni, righe), width="stretch")
    st.download_button(f"Scarica la traiettoria completa (CSV, {len(df)} anni x "
                       f"{len(df.columns)} colonne)",
                       df.to_csv(index=False).encode("utf-8"),
                       "transizione_ADI_Manifesto_ric.csv", "text/csv")

# --- trasparenza sulla calibrazione ------------------------------------------------
with st.expander("Come è calibrato questo scenario"):
    cal = res.cal
    st.markdown(f"""
Tre parametri non sono ipotesi ma **residui**, ricavati imponendo che l'anno base
riproduca il dato osservato. 

| parametro | valore | che cos'è | cosa riproduce |
|---|---|---|---|
| anni da associato a ordinario | {cal['anni_da_associato']:.2f} | l'anzianità oltre la quale un associato diventa ordinario | la quota di ordinari osservata ({C.QUOTA_PO:.3f}) |
| **lambda**: quota di HERD che è lavoro | **{cal['lambda_he']:.3f}** | la parte della spesa di ricerca universitaria che sono STIPENDI; il resto ({1 - cal['lambda_he']:.1%}) sono strumenti, materiali, attrezzature | l'HERD ISTAT di oggi ({C.HERD_OGGI}% PIL) |
| supporto (overhead residuo) | {cal['supporto']:+.3f} | quello che il modello non conta per nome: tecnici e amministrativi di ricerca oltre il TA esplicito | il residuo che l'HERD non spiega |
| overhead enti: supporto / attrezzature | {cal['ovh_epr_supp'] / 1e6:,.0f} / {cal['ovh_epr_attr'] / 1e6:,.0f} mln | gli stessi due residui, per il ramo degli enti | il GOVERD di oggi ({C.GOVERD_OGGI}% PIL) |

**Come si legge lambda.** Il modello costruisce il costo del PERSONALE dal basso -
teste per costo unitario per quota-ricerca, più il TA - e da lì risale alla spesa
totale dividendo: `HERD = costo del lavoro / lambda`. Sull'anno base:

| HERD oggi ({C.HERD_OGGI}% del PIL) | {C.HERD_OGGI / 100 * C.PIL_MLN:,.0f} mln |
|---|---|
| di cui lavoro (lambda) | {C.HERD_OGGI / 100 * C.PIL_MLN * cal['lambda_he']:,.0f} mln |
| di cui attrezzature e materiali (1-lambda) | {C.HERD_OGGI / 100 * C.PIL_MLN * (1 - cal['lambda_he']):,.0f} mln |

Una volta che ogni posizione ha un costo esplicito, il monte
stipendi è determinato e l'HERD di oggi osservato, quindi lambda viene derivato di conseguenza.

**Stato di partenza** — postdoc ricavati per chiudere il gap Eurostat:
{cal['precari_oggi']:,.0f} teste; FTE universitari {cal['fte_oggi']:,.0f}, densità
{cal['dens_oggi']:.1f} per 100k abitanti.

**Imbuto** — P1 scende da {cal['p1_hist']:.2f} (oggi) a {cal['p1']:.2f}; la borsa di
dottorato è moltiplicata per {cal['w_phd']:.2f}.

**Scenario ADI_Manifesto_ric** — densità obiettivo {tg:.0f} FTE/100k, paghe x{W:.2f},
quota di ricercatori universitari {q:.0%}.
""")
    if cal["p1_hist"] > 1.0:
        st.warning(
            "P1 storico maggiore di 1: il precariato di partenza è più grande di "
            "quanto il flusso di dottori possa rimpiazzare. Non è un errore di "
            "calibrazione, è la bolla PNRR - uno stock gonfiato da un finanziamento "
            "straordinario e non sostenibile a regime.")

st.caption(
    "Il modello, le ipotesi e i limiti dichiarati sono documentati in "
    "`MODELLO_spiegazione.md`. La stessa simulazione si esegue da riga di comando in locale con "
    "`python piano_transizione.py`, che produce il report testuale completo, i CSV e i "
    "grafici in PNG.")
