"""Mini modello stock-flow dei precari della ricerca universitaria (dic 2023 -> oggi).

Domanda: dei precari (RTDa, assegnisti, nuovi contratti/incarichi postdoc) quanti sono
passati a RTDb/RTT ("stabilizzati" in senso lato: tenure track) e quanti sono usciti
dal sistema?

Uso:  python stock_flow_precari.py
Output:
  output/precari_stock_flow.csv  tutte le cifre in formato lungo
  output/precari_stock_flow.md   report con metodo, risultati e cautele

Dati:
  ../NumeroRicercatoriEmail/nazionale/ricercatori_nazionale.csv
        monitoraggio giornaliero di cercauniversita.mur.gov.it (task "MonitoraggioPrecari"):
        fornisce lo stock di OGGI (RTDa, RTDb, RTT, assegni, contratti, incarichi) come
        mediana degli ultimi 7 giorni completi. Si aggiorna da solo a ogni esecuzione.
  input/La grande espulsione_2.xlsx           RTDa/RTDb/RTT/RTI/PA (dic22..dic25), assegni
                                              (mag25..feb26); la colonna nov26 resta solo
                                              come confronto (assegni sottostimati, vedi
                                              controllo_aree_assegnisti.py)
  input/docricxclasseetaqualifica_serie.csv   serie MUR (31/12): assegni 2023-2024, confronto fonti
  input/personale_docentericercatorexclassieta.csv  serie MUR per ateneo (solo controllo)
  output/controllo_aree_assegnisti.csv        esito del controllo sulla discrepanza (se presente)

Ipotesi strutturali:
  - solo gli RTDa diventano RTDb; RTDa e RTDb durano 3 anni
  - RTT durano 6 anni (nati nel 2023: nessuna scadenza nella finestra)
  - assegni: durata variabile; dal 2025 vi accedono solo assegnisti gia' esistenti
    (proroghe/rinnovi), nessun RTDa -> assegno; la crescita 2024 e' fatta di persone nuove
  - chi esce da RTDa puo' restare precario solo tramite contratti/incarichi

Identita' contabile del pool precario P = RTDa + assegni + contratti/incarichi:
  uscite = P_inizio + ingressi_esterni - P_fine - passaggi_a_RTDb/RTT
Le transizioni interne (assegno->RTDa, rinnovi, assegno->contratto, RTDa->contratto)
si elidono nel totale ma servono a ripartire i flussi per figura.
"""
import os
import sys
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd

import stock_flow_epr as epr

ROOT = Path(__file__).parent
INPUT = ROOT / "input"
OUTPUT = ROOT / "output"
XLSX = "La grande espulsione_2.xlsx"
MUR = "docricxclasseetaqualifica_serie.csv"
MUR_ATENEI = "personale_docentericercatorexclassieta.csv"

# colonne dell'Excel (0-based) -> etichetta data
COL_XLSX = {2: "dic22", 3: "dic23", 4: "dic24", 5: "mag25", 6: "ago25", 7: "set25",
            8: "ott25", 9: "nov25", 10: "dic25", 11: "feb26", 12: "apr26", 13: "nov26"}
NUOVI_PD = ("Contratti di ricerca", "Incarichi postdoc", "Incarichi di ricerca")
LAB_PD_TOT = "Assegnisti, Contrattisti, Postdoc e Incaricati"


# =================================================================== dati
def leggi_excel():
    ws = openpyxl.load_workbook(INPUT / XLSX, data_only=True).active
    righe = {}
    for r in ws.iter_rows(values_only=True):
        if r[1] and r[1] not in righe:  # prima occorrenza (ΔRTDa compare due volte)
            righe[r[1]] = {lab: r[c] for c, lab in COL_XLSX.items()}
    return righe


def leggi_mur():
    d = pd.read_csv(INPUT / MUR, sep=";", encoding="latin1")
    mappa = {"Ricercatore a tempo determinato L. 240/2010 tipo A": "RTDa",
             "Ricercatore a tempo determinato L. 240/2010 tipo B": "RTDb",
             "Ricercatore a tempo determinato L. 79/2022": "RTT",
             "Ricercatore a tempo indeterminato": "RTI",
             "Professore II fascia (associato)": "PA",
             "Titolare di assegno di ricerca": "Assegni"}
    d["fig"] = d.DESC_QUALIFICA.map(mappa)
    serie = d.dropna(subset=["fig"]).groupby(["ANNO", "fig"]).N_PERS_DR.sum().unstack()
    # controllo incrociato con il secondo file MUR (per ateneo)
    a = pd.read_csv(INPUT / MUR_ATENEI, sep=";", encoding="latin1")
    ass_atenei = a[a.COD_QUALIFICA == "4AR"].groupby("ANNO").N_PERS_DR_E.sum()
    return serie, ass_atenei


MONITORAGGIO_CSV = ROOT.parent / "NumeroRicercatoriEmail" / "nazionale" / "ricercatori_nazionale.csv"
CONTROLLO_AREE_CSV = OUTPUT / "controllo_aree_assegnisti.csv"
COL_DOC = {"RTDA": "RTDa", "RTDB": "RTDb", "RTT": "RTT"}
COL_ASS = {"AR": "Assegnisti", "CR": "Contratti di ricerca", "IPD": "Incarichi postdoc",
           "IR": "Incarichi di ricerca"}
FINESTRA_GIORNI = 7
MESI_IT = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto",
           "settembre", "ottobre", "novembre", "dicembre"]


SNAPSHOT_CSV = INPUT / "monitoraggio_snapshot.csv"
# Aggregato nazionale pubblicato ogni giorno da pubblica_aggregato.py (URL "raw" di GitHub).
# Si imposta con la variabile d'ambiente PRECARI_DATI_URL o, su Streamlit Cloud, con il
# secret di primo livello omonimo (Streamlit li esporta come variabili d'ambiente).
DATI_URL = os.environ.get("PRECARI_DATI_URL", "")


def leggi_monitoraggio(finestra=FINESTRA_GIORNI):
    """Serie giornaliera nazionale dal monitoraggio e stock di oggi (mediana robusta).

    Ordine delle fonti:
      1. CSV grezzo del monitoraggio, se raggiungibile (PC locale); ne salva la serie
         aggregata in input/monitoraggio_snapshot.csv
      2. aggregato pubblicato su GitHub (DATI_URL), aggiornato ogni giorno dal task
      3. lo snapshot nel repo, ultimo ripiego
    Lo stock di oggi e' la mediana degli ultimi `finestra` giorni validi, che assorbe
    i cali spuri di un singolo giorno.
    """
    giornaliera = None
    if MONITORAGGIO_CSV.exists():
        giornaliera = _serie_da_grezzo(MONITORAGGIO_CSV)
        giornaliera.to_csv(SNAPSHOT_CSV, index_label="data")
        fonte = "monitoraggio"
    elif DATI_URL:
        try:
            giornaliera = pd.read_csv(DATI_URL, index_col="data")
            fonte = "repo dati"
        except Exception as e:  # rete giu' o URL sbagliato: si ripiega sullo snapshot
            print(f"Aggregato online non leggibile ({e}): uso lo snapshot", file=sys.stderr)
    if giornaliera is None:
        giornaliera = pd.read_csv(SNAPSHOT_CSV, index_col="data")
        fonte = "snapshot"
    ultimi = giornaliera.tail(finestra)
    oggi = ultimi.median().round().astype(int).to_dict()
    return dict(serie=giornaliera, oggi=oggi, giorni=list(ultimi.index),
                data=pd.Timestamp(ultimi.index[-1]), fonte=fonte)


def _serie_da_grezzo(path):
    """Il CSV ha due righe per ateneo e giorno: una "docenti" (RTDA/RTDB/RTT) e una
    "assegni" (AR/CR/IPD/IR). Una query fallita e' scritta "ERR"; alcuni giorni sono
    vuoti o duplicati. Un giorno vale per un gruppo di colonne solo se TUTTI gli atenei
    hanno un valore numerico."""
    d = pd.read_csv(path, dtype=str)
    d = d[d.data != "data"].copy()
    d["tipo"] = np.where(d["RTDA"].notna() & (d["RTDA"] != ""), "doc", "ass")
    d = d.drop_duplicates(["data", "codice_ateneo", "tipo"], keep="last")
    serie = {}
    for tipo, cols in (("doc", COL_DOC), ("ass", COL_ASS)):
        x = d[d.tipo == tipo].copy()
        n_atenei = x.groupby("data").size().max()
        for c in cols:
            x[c] = pd.to_numeric(x[c], errors="coerce")
        ok = x.groupby("data")[list(cols)].apply(lambda g: g.notna().all().all() and len(g) == n_atenei)
        tot = x.groupby("data")[list(cols)].sum()[ok]
        serie[tipo] = tot.rename(columns=cols)
    return serie["doc"].join(serie["ass"], how="inner").astype(int)


def data_it(ts):
    return f"{ts.day} {MESI_IT[ts.month - 1]} {ts.year}"


def carica_stock(xl, mur, mon):
    g = lambda lab, c: xl[lab][c]
    o = mon["oggi"]
    return dict(
        Ra23=g("RTDa", "dic23"), Ra24=g("RTDa", "dic24"), Ra26=o["RTDa"],
        Rb23=g("RTDb", "dic23"), Rb24=g("RTDb", "dic24"), Rb26=o["RTDb"],
        T23=g("RTT", "dic23"), T24=g("RTT", "dic24"), T26=o["RTT"],
        A23=int(mur.loc[2023, "Assegni"]), A24=int(mur.loc[2024, "Assegni"]),
        A26=o["Assegnisti"], N26=sum(o[l] for l in NUOVI_PD),
        # mesi dal picco (31/12/2024) a oggi, per il limite inferiore
        mesi_dal_picco=(mon["data"].year - 2024) * 12 + mon["data"].month,
    )


# ============================================================== parametri
# (basso, centrale, alto) -> distribuzioni triangolari nel Monte Carlo
PARAM = {
    "T_out":   (0, 50, 150,        "RTT gia' usciti entro nov26 (PA anticipata, dimissioni)"),
    "early_b": (0.00, 0.05, 0.15,  "quota entrati RTDb 2024-26 gia' passati a PA"),
    "old_a":   (0.03, 0.10, 0.20,  "quota stock RTDa nov26 entrata prima di dic23 (proroga 3+2)"),
    "early_a": (0.00, 0.05, 0.12,  "quota entrati RTDa 2024-26 gia' usciti (es. verso RTT)"),
    "s_T_Ra":  (0.35, 0.45, 0.60,  "quota ingressi RTT provenienti da RTDa"),
    "s_T_PD":  (0.25, 0.40, 0.50,  "quota ingressi RTT provenienti da assegni/postdoc"),
    "r_Ra_PD": (0.50, 0.65, 0.80,  "quota nuovi RTDa che erano assegnisti"),
    "D_A":     (2.0, 3.0, 5.0,     "anni di permanenza della PERSONA nel bacino assegni (rinnovi inclusi)"),
    "n_A":     (0.50, 0.65, 0.80,  "quota contratti/incarichi nov26 a ex assegnisti"),
    "n_Ra":    (0.10, 0.20, 0.30,  "quota contratti/incarichi nov26 a ex RTDa (resto: esterni)"),
}
CENTRALE = {k: v[1] for k, v in PARAM.items()}


# ================================================================ modello
def modello(s, p):
    """Flussi cumulati dic23 -> nov26. s: stock, p: parametri (scalari o array numpy)."""
    f = {}
    # --- tenure track
    f["RTT_in"] = s["T26"] - s["T23"] + p["T_out"]
    f["RTDb_in"] = s["Rb26"] / (1 - p["early_b"])            # tutti da RTDa
    f["RTT_da_RTDa"] = p["s_T_Ra"] * f["RTT_in"]
    f["RTT_da_PD"] = p["s_T_PD"] * f["RTT_in"]
    f["RTT_esterni"] = f["RTT_in"] - f["RTT_da_RTDa"] - f["RTT_da_PD"]
    # --- RTDa (coorti triennali: lo stock finale e' quasi tutto entrato dopo dic23)
    f["RTDa_in"] = s["Ra26"] * (1 - p["old_a"]) / (1 - p["early_a"])
    f["RTDa_out"] = s["Ra23"] + f["RTDa_in"] - s["Ra26"]
    f["RTDa_in_da_PD"] = p["r_Ra_PD"] * f["RTDa_in"]
    f["RTDa_in_esterni"] = f["RTDa_in"] - f["RTDa_in_da_PD"]
    nonTT = f["RTDa_out"] - f["RTDb_in"] - f["RTT_da_RTDa"]
    f["RTDa_a_PD"] = p["n_Ra"] * s["N26"]                    # solo verso contratti/incarichi
    f["RTDa_usciti"] = nonTT - f["RTDa_a_PD"]
    # --- assegni + contratti/incarichi (PD)
    A_in_2024 = (s["A24"] - s["A23"]) + s["A23"] / p["D_A"]  # persone nuove, solo nel 2024
    N_esterni = (1 - p["n_A"] - p["n_Ra"]) * s["N26"]
    f["PD_in_esterni"] = A_in_2024 + N_esterni
    PD23, PD26 = s["A23"], s["A26"] + s["N26"]
    f["PD_usciti"] = (PD23 + f["PD_in_esterni"] + f["RTDa_a_PD"] - PD26
                      - f["RTT_da_PD"] - f["RTDa_in_da_PD"])
    # --- totali
    f["stabilizzati"] = f["RTDb_in"] + f["RTT_da_RTDa"] + f["RTT_da_PD"]
    f["usciti"] = f["RTDa_usciti"] + f["PD_usciti"]
    f["ingressi_esterni"] = f["PD_in_esterni"] + f["RTDa_in_esterni"]
    f["quota_usciti_su_chi_lascia"] = f["usciti"] / (f["usciti"] + f["stabilizzati"])
    # verifica identita' di bilancio del pool
    P23, P26 = s["Ra23"] + PD23, s["Ra26"] + PD26
    chk = P23 + f["ingressi_esterni"] - P26 - f["stabilizzati"] - f["usciti"]
    assert np.allclose(chk, 0), "bilancio del pool non chiude"
    f["_valido"] = ((f["RTDa_usciti"] >= 0) & (N_esterni >= 0) & (f["RTT_esterni"] >= 0)
                    & (f["PD_usciti"] >= 0))
    return f


VOCI = {  # chiave -> descrizione
    "RTDb_in": "Passati a RTDb (tutti da RTDa)",
    "RTT_in": "Ingressi totali in RTT",
    "RTT_da_RTDa": "Passati a RTT da RTDa",
    "RTT_da_PD": "Passati a RTT da assegni/postdoc",
    "RTT_esterni": "RTT da fuori dal pool (estero, altro)",
    "RTDa_in": "Ingressi in RTDa",
    "RTDa_in_da_PD": "Ingressi in RTDa da assegni",
    "RTDa_out": "Uscite da posizione RTDa",
    "RTDa_a_PD": "Ex RTDa passati a contratti/incarichi",
    "RTDa_usciti": "Usciti dal sistema da RTDa",
    "PD_in_esterni": "Ingressi esterni in assegni/postdoc",
    "PD_usciti": "Usciti dal sistema da assegni/postdoc",
    "ingressi_esterni": "Ingressi esterni totali nel pool",
    "stabilizzati": "Stabilizzati (RTDb + RTT da precari)",
    "usciti": "Usciti dal sistema (totale)",
    "quota_usciti_su_chi_lascia": "Quota usciti su chi ha lasciato una posizione precaria",
}


def monte_carlo(s, n=50_000, seed=42):
    rng = np.random.default_rng(seed)
    draw = {k: rng.triangular(lo, mo, hi, n) for k, (lo, mo, hi, _) in PARAM.items()}
    mc = modello(s, draw)
    return mc, mc["_valido"]


def sensitivita_churn(s, valori=(2, 3, 4, 5, np.inf)):
    P23 = s["Ra23"] + s["A23"]
    out = []
    for D in valori:
        f = modello(s, dict(CENTRALE, D_A=D))
        out.append(dict(D_A=D, ingressi_esterni=f["ingressi_esterni"], usciti=f["usciti"],
                        usciti_pct_stock23=f["usciti"] / P23,
                        quota_usciti_su_chi_lascia=f["quota_usciti_su_chi_lascia"]))
    return pd.DataFrame(out)


def limite_dal_picco(s):
    """Minimo di uscite dic24 -> oggi assumendo ZERO nuovi ingressi dopo il picco
    e sovrastimando i passaggi in tenure track (85% RTT da precari, RTDb con 5% anticipati)."""
    P24 = s["A24"] + s["Ra24"]
    P26 = s["A26"] + s["N26"] + s["Ra26"]
    tt_max = (s["T26"] - s["T24"]) * 0.85 + s["Rb26"] / 0.95
    return dict(P_dic24=P24, P_oggi=P26, TT_max=tt_max, usciti_min=P24 - P26 - tt_max)


# ============================================================= aggregati
def precari_oggi(mon):
    o = mon["oggi"]
    return {k: o[k] for k in ("Assegnisti", "RTDa", *NUOVI_PD)}


def confronto_excel_monitoraggio(xl, mon):
    """Colonna nov26 dell'Excel contro lo stock di oggi del monitoraggio."""
    o = mon["oggi"]
    nuovi_xl = sum(xl[l]["nov26"] for l in NUOVI_PD)
    righe = [(k, xl[k]["nov26"], o[k]) for k in ("RTDa", "RTDb", "RTT", *NUOVI_PD)]
    righe.append(("Assegnisti", xl[LAB_PD_TOT]["nov26"] - nuovi_xl, o["Assegnisti"]))
    return pd.DataFrame(righe, columns=["figura", "excel_nov26", "monitoraggio"])


def controllo_aree():
    """Esito di controllo_aree_assegnisti.py, se e' stato eseguito."""
    if not CONTROLLO_AREE_CSV.exists():
        return None
    d = pd.read_csv(CONTROLLO_AREE_CSV)
    per_area = d[d.area != "tutte"].groupby("qualifica").n.sum()
    tot, ar = int(per_area["Tutte le qualifiche"]), int(per_area["Assegni di ricerca"])
    nuovi = int(d[d.area == "tutte"].n.sum())
    return dict(data=d.data.iloc[0], tot_area=tot, ar_area=ar, nuovi_con_area=tot - ar,
                nuovi_tutti=nuovi, nuovi_senza_area=nuovi - (tot - ar),
                ar_per_differenza=tot - nuovi)


def confronto_fonti(xl, mur):
    righe = []
    for fig, lab in [("RTDa", "RTDa"), ("RTDb", "RTDb"), ("RTT", "RTT"), ("RTI", "RTI"),
                     ("PA", "Professori Associati")]:
        for anno, col in [(2022, "dic22"), (2023, "dic23"), (2024, "dic24")]:
            x = xl[lab][col]
            m = mur.loc[anno, fig] if fig in mur.columns and anno in mur.index else np.nan
            if x is None or pd.isna(m):
                continue
            righe.append(dict(figura=fig, anno=anno, excel=x, mur=int(m), diff_pct=x / m - 1))
    return pd.DataFrame(righe)


def serie_assegni(xl, mur, mon):
    """Serie assegni: MUR 2020-24 (31/12) + Excel mag25-feb26 + monitoraggio (mediana mensile)."""
    r = [(f"dic{a % 100}", int(mur.loc[a, "Assegni"]), "MUR") for a in range(2020, 2025)]
    for c in ["mag25", "ago25", "set25", "ott25", "nov25", "dic25", "feb26"]:
        r.append((c, xl["Assegni di ricerca"][c], "Excel"))
    m = mon["serie"]["Assegnisti"]
    m.index = pd.to_datetime(m.index)
    for per, v in m.groupby(m.index.to_period("M")).median().items():
        r.append((f"{MESI_IT[per.month - 1][:3]}{per.year % 100}", int(round(v)),
                  "Monitoraggio (mediana del mese)"))
    return pd.DataFrame(r, columns=["data", "assegnisti", "fonte"])


# ================================================================= output
EVOCI = {  # voci EPR -> descrizione
    "P23_teste": "Precari EPR 2023",
    "P24_teste": "Precari EPR 2024 (picco)",
    "P26_teste": "Precari EPR fine 2026",
    "ass26_teste": "di cui assegnisti",
    "td26_teste": "di cui TD ricercatori/tecnologi",
    "P27_teste": "Precari EPR 2027 (scenario del grafico)",
    "ingressi_teste": "Ingressi 2024-26",
    "in_ruolo": "Passati in ruolo 2024-26",
    "usciti_teste": "Usciti dal sistema 2023-26",
    "usciti_min_dal_picco_teste": "Usciti minimi dal picco 2024 (zero ingressi)",
    "a_rischio_2027_teste": "A rischio di uscita entro il 2027",
    "passati_teste": "Passati per il sistema 2023-26",
    "quota_usciti_su_chi_lascia": "Quota usciti su chi ha lasciato una posizione precaria",
    "borsisti_impliciti_se_2024": "Borsisti impliciti nei 6.000 del modello, se riferiti al 2024",
    "borsisti_impliciti_se_2026": "Borsisti impliciti nei 6.000 del modello, se riferiti a fine 2026",
}


def it(x, dec=0):
    """Formato numerico italiano."""
    if isinstance(x, str):
        return x
    s = f"{x:,.{dec}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def art_pct(x, dec=0):
    """Percentuale con l'articolo giusto: "il 46%", "l'84%", "l'11%"."""
    s = pct(x, dec)
    return ("l'" if s[0] == "8" or s.startswith(("11%", "11,", "1%", "1,")) else "il ") + s


def pct(x, dec=0):
    v = round(100 * x, dec)
    return it(v + 0.0, dec) + "%"  # +0.0 evita "-0,0%"


def main():
    xl = leggi_excel()
    mur, ass_atenei = leggi_mur()
    mon = leggi_monitoraggio()
    d_oggi = data_it(mon["data"])
    giorni = f"{data_it(pd.Timestamp(mon['giorni'][0]))} – {d_oggi}"
    s = carica_stock(xl, mur, mon)
    c = modello(s, CENTRALE)
    mc, ok = monte_carlo(s)
    q = lambda k, p_: float(np.percentile(mc[k][ok], p_))
    sens = sensitivita_churn(s)
    lb = limite_dal_picco(s)
    oggi = precari_oggi(mon)
    conf = confronto_fonti(xl, mur)
    ser_a = serie_assegni(xl, mur, mon)
    conf_mon = confronto_excel_monitoraggio(xl, mon)
    ca = controllo_aree()
    mesi = s["mesi_dal_picco"]

    P23 = s["Ra23"] + s["A23"]
    P26 = sum(oggi.values())
    calo = P23 - P26
    TT23, TT26 = s["Rb23"] + s["T23"], s["Rb26"] + s["T26"]
    punti_stab = calo / P23 * c["stabilizzati"] / (c["stabilizzati"] + c["usciti"])
    punti_usc = calo / P23 - punti_stab
    sens_inf = sens[np.isinf(sens.D_A)].iloc[0]
    mur_ok = all(int(mur.loc[a, "Assegni"]) == int(ass_atenei[a]) for a in range(2020, 2025))

    # ------------------------------------------------------------------ EPR
    hires = epr.assunti_ingresso_epr()
    e = epr.modello(epr.CENTRALE, hires)
    emc = epr.monte_carlo(hires)
    n_e = len(emc["usciti_teste"])
    eq = lambda k, p_: float(np.percentile(np.broadcast_to(np.asarray(emc[k], float), (n_e,)), p_))

    # ------------------------------------------- sistema complessivo (uni + EPR)
    # Monte Carlo combinato: estrazioni indipendenti, sommate una a una
    n_ok = int(ok.sum())
    sis = {"usciti": c["usciti"] + e["usciti_teste"],
           "stabilizzati": c["stabilizzati"] + e["in_ruolo"],
           "rimasti": P26 + e["P26_teste"],
           "passati": P23 + c["ingressi_esterni"] + e["passati_teste"]}
    sis_mc = {"usciti": mc["usciti"][ok] + emc["usciti_teste"][:n_ok],
              "stabilizzati": mc["stabilizzati"][ok] + emc["in_ruolo"][:n_ok],
              "rimasti": P26 + emc["P26_teste"][:n_ok],
              "passati": P23 + mc["ingressi_esterni"][ok] + emc["passati_teste"][:n_ok]}
    for k in ("usciti", "stabilizzati", "rimasti"):
        sis["q_" + k] = sis[k] / sis["passati"]
        sis_mc["q_" + k] = sis_mc[k] / sis_mc["passati"]
    sq = lambda k, p_: float(np.percentile(sis_mc[k], p_))
    sens_sis = [(r.D_A, (r.usciti + e["usciti_teste"]) / (P23 + r.ingressi_esterni + e["passati_teste"]))
                for _, r in sens.iterrows()]
    stock23_sis = P23 + e["P23_teste"]
    esaurimento = s["A26"] + s["Ra26"] + e["ass26_teste"]
    assert np.isclose(sis["passati"], sis["usciti"] + sis["stabilizzati"] + sis["rimasti"])

    # ---------------------------------------------------------------- CSV
    rows = []
    add = lambda sez, voce, val, p10=None, p90=None, unita="persone", nota="": rows.append(
        dict(sezione=sez, voce=voce, valore=val, p10=p10, p90=p90, unita=unita, nota=nota))

    add("stock_2023", "RTDa", s["Ra23"], nota="Excel, dic 2023")
    add("stock_2023", "Assegnisti", s["A23"], nota="MUR, 31/12/2023 (4AR, tutte le eta')")
    add("stock_2023", "Contratti/incarichi postdoc", 0, nota="non ancora esistenti")
    add("stock_2023", "Totale precari", P23)
    add("stock_2023", "RTDb", s["Rb23"], nota="Excel")
    add("stock_2023", "RTT", s["T23"], nota="Excel")
    add("stock_2023", "Totale precari + tenure track", P23 + TT23)
    nota_mon = f"monitoraggio, mediana {len(mon['giorni'])} giorni fino al {mon['data'].date()}"
    for k, v in oggi.items():
        add("precari_oggi", k, v, nota=nota_mon)
    add("precari_oggi", "Totale precari", P26, nota=nota_mon)
    add("precari_oggi", "RTDb", s["Rb26"], nota=nota_mon)
    add("precari_oggi", "RTT", s["T26"], nota=nota_mon)
    add("precari_oggi", "Totale precari + tenure track", P26 + TT26)
    for _, r in conf_mon.iterrows():
        add("confronto_excel_monitoraggio", f"{r.figura}: Excel nov26", r.excel_nov26,
            nota="assegnisti per differenza (formula N6)" if r.figura == "Assegnisti" else "")
        add("confronto_excel_monitoraggio", f"{r.figura}: monitoraggio oggi", r.monitoraggio)
    if ca:
        add("controllo_aree_assegnisti", "Somma per area CUN, tutte le qualifiche", ca["tot_area"], nota=ca["data"])
        add("controllo_aree_assegnisti", "Somma per area CUN, assegni", ca["ar_area"], nota=ca["data"])
        add("controllo_aree_assegnisti", "Contratti e incarichi, tutte le aree", ca["nuovi_tutti"], nota=ca["data"])
        add("controllo_aree_assegnisti", "Contratti e incarichi senza area CUN", ca["nuovi_senza_area"], nota=ca["data"])
        add("controllo_aree_assegnisti", "Assegni per differenza (metodo Excel)", ca["ar_per_differenza"], nota=ca["data"])
    add("calo_2023_2026", "Calo netto precari", -calo)
    add("calo_2023_2026", "Calo netto precari %", -calo / P23, unita="quota")
    add("calo_2023_2026", "Calo netto precari + tenure track", -(P23 + TT23 - P26 - TT26))
    add("calo_2023_2026", "Calo netto precari + tenure track %", -(P23 + TT23 - P26 - TT26) / (P23 + TT23), unita="quota")
    add("calo_2023_2026", "Punti di calo dovuti a stabilizzazioni", -punti_stab, unita="quota",
        nota="ripartizione proporzionale ai flussi in uscita")
    add("calo_2023_2026", "Punti di calo dovuti a uscite", -punti_usc, unita="quota")
    add("calo_2023_2026", "Stabilizzati / stock 2023", c["stabilizzati"] / P23,
        q("stabilizzati", 10) / P23, q("stabilizzati", 90) / P23, "quota")
    add("calo_2023_2026", "Usciti / stock 2023", c["usciti"] / P23,
        q("usciti", 10) / P23, q("usciti", 90) / P23, "quota")
    for k, desc in VOCI.items():
        add("flussi_dic23_oggi", desc, c[k], q(k, 10), q(k, 90),
            "quota" if k.startswith("quota") else "persone", f"chiave modello: {k}")
    for _, r in sens.iterrows():
        D = "inf" if np.isinf(r.D_A) else it(r.D_A)
        add("sensitivita_churn", f"D_A={D} anni: ingressi esterni", r.ingressi_esterni)
        add("sensitivita_churn", f"D_A={D} anni: usciti", r.usciti)
        add("sensitivita_churn", f"D_A={D} anni: usciti / stock 2023", r.usciti_pct_stock23, unita="quota")
        add("sensitivita_churn", f"D_A={D} anni: usciti su chi lascia", r.quota_usciti_su_chi_lascia, unita="quota")
    add("limite_inferiore", "Precari dic 2024 (picco)", lb["P_dic24"], nota="assegni MUR + RTDa Excel")
    add("limite_inferiore", "Precari oggi", lb["P_oggi"])
    add("limite_inferiore", "Passaggi in tenure track dic24-oggi (sovrastima)", lb["TT_max"])
    add("limite_inferiore", "Usciti minimi dic24-oggi", lb["usciti_min"],
        nota=f"{mesi} mesi, assumendo zero nuovi ingressi")
    for _, r in ser_a.iterrows():
        add("serie_assegnisti", r.data, r.assegnisti, nota=r.fonte)
    for _, r in conf.iterrows():
        add("confronto_excel_mur", f"{r.figura} {r.anno}: Excel", r.excel)
        add("confronto_excel_mur", f"{r.figura} {r.anno}: MUR", r.mur)
        add("confronto_excel_mur", f"{r.figura} {r.anno}: differenza Excel/MUR", r.diff_pct, unita="quota")
    for k, (lo, mo, hi, desc) in PARAM.items():
        add("parametri", k, mo, lo, hi, "parametro", desc)

    # --- EPR
    ua, nota_g = "unita' annue", "grafico Conto annuale, borsisti esclusi"
    for a in (2023, 2024, 2027):
        n_ = nota_g + ("; 2027 = scenario" if a == 2027 else "")
        add("epr_dati_grafico", f"Assegnisti {a}", epr.ASS[a], unita=ua, nota=n_)
        add("epr_dati_grafico", f"TD ricercatori/tecnologi {a}", epr.TD[a], unita=ua, nota=n_)
    for fig, lab in (("ass", "assegnisti"), ("td", "TD ricercatori/tecnologi")):
        add("epr_dati_grafico", f"Calo fine PNRR 2024-27, {lab}", -epr.CALO_PNRR[fig], unita=ua)
        add("epr_dati_grafico", f"Calo tetto 30 mesi 2024-27, {lab}", -epr.CALO_TETTO[fig], unita=ua)
    add("epr_dati_grafico", "Assunti III livello (ricercatore+tecnologo), 2024", hires,
        nota="input/AssuntiCessati2024.xlsx, Conto annuale 2024")
    for k, desc in EVOCI.items():
        add("epr_2023_2026", desc, e[k], eq(k, 10), eq(k, 90),
            "quota" if k.startswith("quota") else "persone", f"chiave modello: {k}")
    for k, (lo, mo, hi, desc) in epr.PARAM.items():
        add("epr_parametri", k, mo, lo, hi, "parametro", desc)

    # --- sistema complessivo
    add("sistema_2026", "Precari universita' (oggi)", P26, nota=nota_mon)
    add("sistema_2026", "Precari EPR (fine 2026)", e["P26_teste"], eq("P26_teste", 10), eq("P26_teste", 90),
        nota="stima, borsisti esclusi")
    add("sistema_2026", "Totale precari (esclusi RTDb, RTT, borsisti EPR)", sis["rimasti"],
        sq("rimasti", 10), sq("rimasti", 90))
    add("sistema_2026", "Totale precari + RTDb + RTT", sis["rimasti"] + TT26)
    add("sistema_2026", "Figure a esaurimento (assegni uni+EPR, RTDa)", esaurimento)
    add("sistema_esiti_2023_2026", "Precari presenti nel 2023", stock23_sis)
    for k, desc in (("passati", "Passati per il sistema (stock 2023 + ingressi)"),
                    ("usciti", "Usciti dal sistema"),
                    ("stabilizzati", "Passati a RTDb/RTT (uni) o in ruolo (EPR)"),
                    ("rimasti", "Ancora precari a fine 2026")):
        add("sistema_esiti_2023_2026", desc, sis[k], sq(k, 10), sq(k, 90))
        if k != "passati":
            add("sistema_esiti_2023_2026", desc + " / passati", sis["q_" + k],
                sq("q_" + k, 10), sq("q_" + k, 90), "quota")
    add("sistema_esiti_2023_2026", "Usciti / precari presenti nel 2023", sis["usciti"] / stock23_sis,
        unita="quota")
    for D, v in sens_sis:
        add("sistema_sensitivita", f"D_A={'inf' if np.isinf(D) else it(D)} anni: usciti / passati", v,
            unita="quota", nota="EPR al valore centrale")

    OUTPUT.mkdir(exist_ok=True)
    df = pd.DataFrame(rows)
    num = ["valore", "p10", "p90"]
    df[num] = df[num].astype(float)
    quota = df.unita == "quota"
    df.loc[quota, num] = df.loc[quota, num].round(4)
    df.loc[df.unita == "persone", num] = df.loc[df.unita == "persone", num].round(0)
    df.to_csv(OUTPUT / "precari_stock_flow.csv", index=False, encoding="utf-8-sig")

    # ----------------------------------------------------------- Markdown
    def riga_flusso(k):
        return f"| {VOCI[k]} | {it(round(c[k], -1))} | {it(round(q(k, 10), -1))}–{it(round(q(k, 90), -1))} |"

    tab_oggi = "\n".join(f"| {k} | {it(v)} |" for k, v in oggi.items())
    tab_sens = "\n".join(
        f"| {'∞ (nessuna uscita da assegno nel 2024)' if np.isinf(r.D_A) else it(r.D_A) + ' anni'}"
        f"{' (centrale)' if r.D_A == CENTRALE['D_A'] else ''} | {it(round(r.ingressi_esterni, -2))} | "
        f"{it(round(r.usciti, -2))} | {pct(r.usciti_pct_stock23)} | {pct(r.quota_usciti_su_chi_lascia)} |"
        for _, r in sens.iterrows())
    tab_ass = "\n".join(f"| {r.data} | {it(r.assegnisti)} | {r.fonte} |" for _, r in ser_a.iterrows())
    tab_conf = "\n".join(f"| {r.figura} | {r.anno} | {it(r.excel)} | {it(r.mur)} | {pct(r.diff_pct, 1)} |"
                         for _, r in conf.iterrows())
    fv = lambda x: it(x, 2) if float(x) != int(x) else it(x)
    fmt_par = lambda P: "\n".join(f"| `{k}` | {desc} | {fv(mo)} | {fv(lo)}–{fv(hi)} |"
                                  for k, (lo, mo, hi, desc) in P.items())
    tab_par, tab_epr_par = fmt_par(PARAM), fmt_par(epr.PARAM)
    tab_epr_dati = "\n".join(
        f"| {a}{' (scenario)' if a == 2027 else ''} | {it(epr.ASS[a])} | {it(epr.TD[a])} | "
        f"{it(epr.ASS[a] + epr.TD[a])} |" for a in (2023, 2024, 2027))
    r_e = lambda k, dec=-1: (f"| {EVOCI[k]} | {it(round(e[k], dec))} | "
                             f"{it(round(eq(k, 10), dec))}–{it(round(eq(k, 90), dec))} |")
    r_s = lambda k, desc: (f"| {desc} | {it(round(sis[k], -2))} | {pct(sis['q_' + k])} | "
                           f"{pct(sq('q_' + k, 10))}–{pct(sq('q_' + k, 90))} |")
    lab_D = lambda D: "∞" if np.isinf(D) else it(D) + " anni"
    tab_sens_sis = "\n".join(f"| {lab_D(D)}{' (centrale)' if D == CENTRALE['D_A'] else ''} | {pct(v)} |"
                             for D, v in sens_sis)
    q_min, q_max = min(v for _, v in sens_sis), max(v for _, v in sens_sis)
    tab_conf_mon = "\n".join(f"| {r.figura} | {it(r.excel_nov26)} | {it(r.monitoraggio)} |"
                             for _, r in conf_mon.iterrows())
    if ca:
        txt_ca = f"""**Perché gli assegnisti dell'Excel erano sottostimati** (controllo del {ca['data']}, `controllo_aree_assegnisti.py`). Nell'Excel gli assegnisti erano ricavati come somma per area CUN di tutte le figure, meno i contratti e gli incarichi. Ma contratti e incarichi venivano sottratti con il totale nazionale, che comprende anche chi non ha un'area CUN:
- somma per area, tutte le figure: {it(ca['tot_area'])};
- somma per area, solo assegni: {it(ca['ar_area'])}, quindi contratti e incarichi **con** area CUN: {it(ca['nuovi_con_area'])};
- contratti e incarichi in totale: {it(ca['nuovi_tutti'])}, quindi **{it(ca['nuovi_senza_area'])} senza area CUN** (inquadrati solo sui nuovi settori 2024).

Sottraendo il totale, il metodo dell'Excel dava {it(ca['ar_per_differenza'])} assegnisti invece di circa {it(ca['ar_area'])} con area più quelli senza area. Il monitoraggio somma ateneo per ateneo su tutte le aree e dà {it(s['A26'])}: è il dato corretto, ed è quello usato dal modello."""
    else:
        txt_ca = "Il controllo sulle aree CUN (`controllo_aree_assegnisti.py`) non è stato eseguito: lanciarlo per documentare la discrepanza."

    md = f"""# Precari della ricerca pubblica (università ed EPR): stock e flussi 2023 → oggi

*Report generato da `stock_flow_precari.py` (con il modulo `stock_flow_epr.py`) il {data_it(pd.Timestamp.today())}. Lo stock di oggi delle università viene dal monitoraggio giornaliero di Cerca Università (mediana dei giorni {giorni}). Tutte le cifre sono in `output/precari_stock_flow.csv`.*

## Sintesi

### Sistema complessivo (università + EPR)

- **Precari passati per il sistema tra 2023 e 2026: circa {it(round(sis['passati'], -2))}**, cioè chi c'era nel 2023 ({it(round(stock23_sis, -2))}) più chi è entrato dopo.
- **Esiti:**
  - **usciti dal sistema: circa {it(round(sis['usciti'], -2))}, {art_pct(sis['q_usciti'])}** ({pct(sq('q_usciti', 10))}–{pct(sq('q_usciti', 90))});
  - passati a RTDb/RTT (università) o in ruolo (enti): circa {it(round(sis['stabilizzati'], -2))}, {art_pct(sis['q_stabilizzati'])};
  - ancora precari a fine 2026: circa {it(round(sis['rimasti'], -2))}, {art_pct(sis['q_rimasti'])}.
- **Su 100 precari passati per il sistema, {it(100 * sis['q_usciti'])} sono usciti, {it(100 * sis['q_stabilizzati'])} sono entrati in tenure track o in ruolo e {it(100 * sis['q_rimasti'])} sono ancora precari.** Al variare del ricircolo interno degli assegni, la quota di usciti va dal {pct(q_min)} al {pct(q_max)}.
- **Rispetto ai soli precari presenti nel 2023**, gli usciti valgono {art_pct(sis['usciti'] / stock23_sis)}. Questo rapporto è meno corretto, perché tra gli usciti ci sono anche persone entrate dopo il 2023.
- **Precari oggi: circa {it(round(sis['rimasti'], -2))}** ({it(P26)} nelle università e circa {it(round(e['P26_teste'], -1))} negli enti), esclusi RTDb, RTT e borsisti degli enti. Con RTDb e RTT sono circa {it(round(sis['rimasti'] + TT26, -2))}.
- **Figure a esaurimento: circa {it(round(esaurimento, -2))}** (assegnisti di università ed enti, RTDa). Sono posizioni che non si possono più aprire per persone nuove, quindi è da qui che verranno le prossime uscite.

### Università

- **Precari a dicembre 2023:** {it(P23)} (RTDa {it(s['Ra23'])} + assegnisti {it(s['A23'])}).
- **Precari oggi ({d_oggi}):** {it(P26)}. Il calo netto è di **{it(calo)} persone, cioè −{pct(calo / P23)}**.
- **Stabilizzati** (passati a RTDb o RTT): **circa {it(round(c['stabilizzati'], -1))}**, {art_pct(c['stabilizzati'] / P23)} dello stock 2023 (intervallo {it(round(q('stabilizzati', 10), -1))}–{it(round(q('stabilizzati', 90), -1))}).
- **Usciti dal sistema:** **circa {it(round(c['usciti'], -2))}** ({pct(c['usciti'] / P23)} dello stock 2023; intervallo {it(round(q('usciti', 10), -2))}–{it(round(q('usciti', 90), -2))}). Le uscite superano il calo netto perché nel 2024 la corsa agli assegni ha portato nel sistema circa {it(round(c['ingressi_esterni'], -2))} persone nuove.
- **Ripartizione dei {it(100 * calo / P23, 1)} punti di calo** (in proporzione ai flussi in uscita): {it(100 * punti_stab, 1)} punti dovuti alle stabilizzazioni e {it(100 * punti_usc, 1)} alle uscite.
- **Su chi ha lasciato una posizione precaria, circa {round(4 * c['quota_usciti_su_chi_lascia'])} su 4 sono usciti dal sistema** ({pct(c['quota_usciti_su_chi_lascia'])} nella stima centrale, {pct(sens.quota_usciti_su_chi_lascia.min())}–{pct(sens.quota_usciti_su_chi_lascia.max())} in tutti gli scenari).
- **Cifra prudente:** dal picco di dicembre 2024 ({it(lb['P_dic24'])} precari) sono usciti **almeno {it(round(lb['usciti_min'], -2))}** persone in {mesi} mesi, anche assumendo zero nuovi ingressi.

### Enti pubblici di ricerca (EPR)

- **Usciti dal sistema tra 2023 e 2026: circa {it(round(e['usciti_teste'], -2))}** ({it(round(eq('usciti_teste', 10), -2))}–{it(round(eq('usciti_teste', 90), -2))}), borsisti esclusi. Sono passati in ruolo circa {it(round(e['in_ruolo'], -1))}.
- **{pct(e['quota_usciti_su_chi_lascia'])} di chi ha lasciato una posizione precaria è uscito dal sistema**, una quota più alta che in università perché negli enti si entra in ruolo pochissimo.
- **Precari a fine 2026: circa {it(round(e['P26_teste'], -1))}** (circa {it(round(e['ass26_teste'], -1))} assegnisti e {it(round(e['td26_teste'], -1))} ricercatori e tecnologi a tempo determinato).
- **A rischio di uscita entro il 2027: circa {it(round(e['a_rischio_2027_teste'], -2))}** ({it(round(eq('a_rischio_2027_teste', 10), -2))}–{it(round(eq('a_rischio_2027_teste', 90), -2))}), soprattutto per il tetto di 30 mesi sugli assegni.
- **Il valore di 6.000 precari EPR usato nel modello di simulazione corrisponde al picco del 2024, non al 2026.** Per un anno base 2026 il valore coerente è circa {it(round(e['P26_teste'], -2))} più i borsisti.

## Precari oggi nelle università ({d_oggi})

| Figura | Persone |
|---|---|
{tab_oggi}
| **Totale precari** | **{it(P26)}** |
| RTDb | {it(s['Rb26'])} |
| RTT | {it(s['T26'])} |
| **Totale con tenure track** | **{it(P26 + TT26)}** |

Includendo RTDb e RTT, lo stesso aggregato a dicembre 2023 era {it(P23 + TT23)}: il calo è di {it(P23 + TT23 - P26 - TT26)}, cioè −{pct((P23 + TT23 - P26 - TT26) / (P23 + TT23))}.

Assegnisti ({it(s['A26'])}) e RTDa ({it(s['Ra26'])}) sono figure a esaurimento, che non si possono più attivare per persone nuove. Gli assegni scadranno quasi tutti entro il 2027 e gli RTDa entro il 2028–2029.

Restano esclusi borse post-laurea, dottorandi e personale degli enti pubblici di ricerca.

## Metodo

Il pool precario comprende RTDa, assegnisti e i nuovi contratti di ricerca e incarichi postdoc o di ricerca. Il modello applica un'identità di bilancio sulla finestra dicembre 2023 → {d_oggi}:

> uscite = stock iniziale + ingressi esterni − stock finale − passaggi a RTDb/RTT

I passaggi interni al pool (assegno → RTDa, rinnovi, assegno → contratto, RTDa → contratto) si annullano nel totale. Servono solo a ripartire i flussi per figura.

**Ipotesi strutturali**
- Solo gli RTDa diventano RTDb. RTDa e RTDb durano 3 anni.
- Gli RTT durano 6 anni. La figura nasce nel 2023, quindi nella finestra nessun RTT arriva a scadenza.
- Dal 2025 agli assegni accedono solo assegnisti già esistenti (proroghe e rinnovi). Un RTDa non può passare ad assegno, solo a contratto o incarico.
- La crescita degli assegni nel 2024 (+{it(s['A24'] - s['A23'])}) è fatta per forza di persone nuove: i rinnovi non fanno crescere lo stock.

**Come si stimano i flussi**
- **RTDb:** con contratti di 3 anni, lo stock di {d_oggi} è entrato quasi tutto dopo dicembre 2023. Gli ingressi sono lo stock finale più chi è già passato a PA in anticipo.
- **RTT:** gli ingressi sono l'aumento dello stock, più poche uscite anticipate.
- **RTDa:** lo stock di dicembre 2023 è quasi tutto scaduto entro {d_oggi}, tranne le proroghe 3+2. Gli ingressi sono lo stock finale corretto per le proroghe e per le uscite anticipate.
- **Assegni:** le persone nuove nel 2024 sono la crescita netta più le uscite normali, cioè lo stock 2023 diviso per gli anni di permanenza `D_A`. `D_A` misura la permanenza della persona nel bacino, rinnovi compresi: più è alto, più c'è ricircolo interno e meno sono sia ingressi sia uscite.

I parametri non osservabili variano in un Monte Carlo (50.000 estrazioni, distribuzioni triangolari). Gli intervalli riportati sono p10–p90.

| Parametro | Significato | Centrale | Intervallo |
|---|---|---|---|
{tab_par}

## Risultati: flussi dicembre 2023 → {d_oggi}

| Flusso | Centrale | p10–p90 |
|---|---|---|
{riga_flusso('RTDb_in')}
{riga_flusso('RTT_da_RTDa')}
{riga_flusso('RTT_da_PD')}
{riga_flusso('RTT_esterni')}
| **{VOCI['stabilizzati']}** | **{it(round(c['stabilizzati'], -1))}** | {it(round(q('stabilizzati', 10), -1))}–{it(round(q('stabilizzati', 90), -1))} |
{riga_flusso('RTDa_out')}
{riga_flusso('RTDa_a_PD')}
{riga_flusso('RTDa_usciti')}
{riga_flusso('RTDa_in_da_PD')}
{riga_flusso('PD_usciti')}
| **{VOCI['usciti']}** | **{it(round(c['usciti'], -1))}** | {it(round(q('usciti', 10), -1))}–{it(round(q('usciti', 90), -1))} |
{riga_flusso('ingressi_esterni')}

**Esiti per figura**
- **RTDa:** circa {it(round(c['RTDb_in'] + c['RTT_da_RTDa'], -2))} su {it(round(c['RTDa_out'], -2))} sono passati a RTDb o RTT ({pct((c['RTDb_in'] + c['RTT_da_RTDa']) / c['RTDa_out'])}); circa {it(round(c['RTDa_a_PD'], -1))} sono rimasti precari con un contratto o incarico; circa {it(round(c['RTDa_usciti'], -2))} sono usciti.
- **Assegnisti:** circa {it(round(c['RTT_da_PD'], -1))} sono passati a RTT e circa {it(round(c['RTDa_in_da_PD'], -1))} a RTDa, contro circa {it(round(c['PD_usciti'], -1))} uscite.

**Quanto sono solide le stime.** Le stabilizzazioni sono robuste, perché derivano quasi interamente dagli stock osservati. Le uscite totali dipendono soprattutto da quanti sono entrati con la corsa agli assegni del 2024, quindi dal parametro `D_A`.

## Sensitività al ricircolo interno degli assegni

| `D_A` | Ingressi esterni | Usciti | % sullo stock 2023 | Usciti su chi ha lasciato |
|---|---|---|---|---|
{tab_sens}

Lo scenario `D_A` = ∞ è irrealistico: vorrebbe dire che nel 2024 nessun assegnista ha lasciato il sistema. Fissa però un minimo che il ricircolo non può abbassare. Nel 2024 il pool è cresciuto di {it(lb['P_dic24'] - P23)} persone, e queste sono per forza nuove. Anche in quel caso gli usciti sono circa {it(round(sens_inf.usciti, -2))}.

**Limite inferiore dal picco.** I precari passano da {it(lb['P_dic24'])} a dicembre 2024 a {it(lb['P_oggi'])} al {d_oggi}. Sottraendo una sovrastima dei passaggi in tenure track ({it(round(lb['TT_max'], -1))}) e assumendo zero nuovi ingressi, gli usciti sono **almeno {it(round(lb['usciti_min'], -2))}** in {mesi} mesi.

## Enti pubblici di ricerca (EPR)

**Dati.** I grafici del Conto annuale RGS su assegnisti e ricercatori e tecnologi a tempo determinato negli enti. Le misure sono in **unità annue** (mesi lavorati diviso 12) e **non includono i borsisti**. I valori sono trascritti a mano dal grafico.

| Anno | Assegnisti | Ricercatori e tecnologi TD | Totale |
|---|---|---|---|
{tab_epr_dati}

Dal 2024 al 2027 il grafico scompone il calo in due parti:
- **fine del PNRR:** −{it(epr.CALO_PNRR['ass'])} assegnisti e −{it(epr.CALO_PNRR['td'])} TD;
- **tetto di 30 mesi:** −{it(epr.CALO_TETTO['ass'])} assegnisti e −{it(epr.CALO_TETTO['td'])} TD.

Gli ingressi in ruolo vengono dal Conto annuale 2024 (`input/AssuntiCessati2024.xlsx`): {it(hires)} assunzioni all'anno di ricercatori e tecnologi di III livello.

**Metodo.** Si usa la stessa identità di bilancio delle università: usciti = stock 2023 + ingressi − stock 2026 − passati in ruolo.
- **Stock di fine 2026:** è il valore 2024 meno il calo "fine PNRR", già in buona parte avvenuto, e meno una quota del calo "tetto 30 mesi".
- **Ingressi:** sono la crescita del 2024 più il ricambio normale, cioè lo stock 2023 diviso per gli anni di permanenza `D`, più i pochi ingressi del 2025–26.
- **Persone:** le unità annue si convertono in persone con un fattore `k_teste`, perché molti contratti durano meno di un anno.

| Parametro | Significato | Centrale | Intervallo |
|---|---|---|---|
{tab_epr_par}

**Risultati** (in persone; p10–p90 dal Monte Carlo)

| Voce | Centrale | p10–p90 |
|---|---|---|
{r_e('P23_teste')}
{r_e('P24_teste')}
{r_e('P26_teste')}
{r_e('ass26_teste')}
{r_e('td26_teste')}
{r_e('P27_teste')}
{r_e('ingressi_teste')}
{r_e('in_ruolo')}
| **{EVOCI['usciti_teste']}** | **{it(round(e['usciti_teste'], -1))}** | {it(round(eq('usciti_teste', 10), -1))}–{it(round(eq('usciti_teste', 90), -1))} |
{r_e('usciti_min_dal_picco_teste')}
| **{EVOCI['a_rischio_2027_teste']}** | **{it(round(e['a_rischio_2027_teste'], -1))}** | {it(round(eq('a_rischio_2027_teste', 10), -1))}–{it(round(eq('a_rischio_2027_teste', 90), -1))} |
| {EVOCI['quota_usciti_su_chi_lascia']} | {pct(e['quota_usciti_su_chi_lascia'])} | {pct(eq('quota_usciti_su_chi_lascia', 10))}–{pct(eq('quota_usciti_su_chi_lascia', 90))} |

**Chi resta dopo il 2027.** Nello scenario 2027 restano circa {it(round(e['P27_teste'], -2))} precari, di cui circa {it(round(e['ass27_teste'], -2))} assegnisti. Senza contratti di ricerca che li sostituiscano, anche loro sono a rischio, solo più avanti. Ci sono poi i borsisti, che il grafico non vede.

**Raccordo con il modello di simulazione.** `config.EPR_PRECARI_OGGI` vale 6.000 persone, borsisti inclusi.
- **Se i 6.000 si riferiscono al 2024:** i borsisti impliciti sono circa {it(round(e['borsisti_impliciti_se_2024'], -1))} ({it(round(eq('borsisti_impliciti_se_2024', 10), -1))}–{it(round(eq('borsisti_impliciti_se_2024', 90), -1))}), un numero plausibile.
- **Se si riferiscono a fine 2026:** ne servirebbero circa {it(round(e['borsisti_impliciti_se_2026'], -1))}, un numero non plausibile.

Il valore del modello descrive quindi il picco del 2024. Per un anno base 2026 il valore coerente è circa {it(round(e['P26_teste'], -2))} più i borsisti, cioè circa 3.500–4.000.

## Sistema complessivo: università + EPR

**Esiti dei precari passati per il sistema tra 2023 e 2026**

| Esito | Persone | % sui passati | p10–p90 |
|---|---|---|---|
{r_s('usciti', 'Usciti dal sistema')}
{r_s('stabilizzati', 'Passati a RTDb/RTT (università) o in ruolo (enti)')}
{r_s('rimasti', 'Ancora precari a fine 2026')}
| **Totale passati per il sistema** | **{it(round(sis['passati'], -2))}** | 100% | |

| | Università | Enti | Totale |
|---|---|---|---|
| Usciti dal sistema | {it(round(c['usciti'], -2))} | {it(round(e['usciti_teste'], -2))} | {it(round(sis['usciti'], -2))} |
| Passati a RTDb/RTT o in ruolo | {it(round(c['stabilizzati'], -1))} | {it(round(e['in_ruolo'], -1))} | {it(round(sis['stabilizzati'], -1))} |
| Ancora precari a fine 2026 | {it(P26)} | {it(round(e['P26_teste'], -1))} | {it(round(sis['rimasti'], -1))} |
| **Passati per il sistema** | {it(round(P23 + c['ingressi_esterni'], -2))} | {it(round(e['passati_teste'], -2))} | {it(round(sis['passati'], -2))} |

**Quota di usciti al variare del ricircolo interno degli assegni universitari** (enti al valore centrale)

| `D_A` | Usciti su passati per il sistema |
|---|---|
{tab_sens_sis}

**Precari oggi.** Sono circa {it(round(sis['rimasti'], -2))}, esclusi RTDb, RTT e borsisti degli enti: {it(P26)} nelle università e circa {it(round(e['P26_teste'], -1))} negli enti.
- Con RTDb ({it(s['Rb26'])}) e RTT ({it(s['T26'])}) si arriva a circa {it(round(sis['rimasti'] + TT26, -2))}. La tenure track esiste solo nelle università.
- Le figure a esaurimento sono circa {it(round(esaurimento, -2))}: {it(s['A26'])} assegnisti e {it(s['Ra26'])} RTDa nelle università, circa {it(round(e['ass26_teste'], -1))} assegnisti negli enti.

## Dati e controlli sulle fonti

**Serie degli assegnisti**

| Data | Assegnisti | Fonte |
|---|---|---|
{tab_ass}

- **Le due fonti non hanno una data in comune**, ma si raccordano. Il livello di maggio 2025, da fonte indipendente, conferma il salto MUR del 2024. Il calo da dicembre 2024 a maggio 2025 (circa −650 al mese) è più lento di quello della seconda metà del 2025, coerente con l'assenza di nuovi ingressi.
- **I due file MUR** (serie nazionale e serie per ateneo) {'coincidono' if mur_ok else 'NON coincidono'} sugli assegnisti per tutti gli anni dal 2020 al 2024.
- **Aprile 2026:** le righe per area dell'Excel sommano a 6.797, contro 13.774 a febbraio e circa {it(int(ser_a[ser_a.fonte.str.startswith('Monitoraggio')].assegnisti.iloc[0]))} nel primo mese del monitoraggio. Il valore di aprile è incoerente con il resto della serie (probabilmente un'interrogazione diversa) e non entra nel modello.
- **Righe per area CUN:** sottostimano tutte le figure, perché escludono chi non ha un'area CUN. Per gli assegni la perdita è piccola (circa il 4% a oggi), per contratti e incarichi è grande. La serie Excel 2025 degli assegni potrebbe quindi essere leggermente bassa; nel modello entra solo come controllo.

**Stock di oggi: colonna "nov 2026" dell'Excel contro il monitoraggio**

| Figura | Excel nov 2026 | Monitoraggio, oggi |
|---|---|---|
{tab_conf_mon}

{txt_ca}

**Qualità del monitoraggio.** Il CSV ha giorni con query fallite (ERR), giorni vuoti, giorni duplicati e cali spuri di un solo giorno. Il modello usa solo i giorni in cui tutti gli atenei hanno un valore e prende la mediana degli ultimi {FINESTRA_GIORNI}.

**Excel contro MUR, dove le date coincidono (31/12)**

| Figura | Anno | Excel | MUR | Differenza |
|---|---|---|---|---|
{tab_conf}

RTI e PA coincidono quasi esattamente. Le figure RTD sono più alte nell'Excel del 2–5%, probabilmente per una data di estrazione diversa o per una diversa attribuzione dei contratti L. 79/2022. Gli assegni 2023 vengono dal MUR, gli RTDa dall'Excel. Usando solo dati MUR lo stock 2023 sarebbe {it(int(mur.loc[2023, 'RTDa']) + s['A23'])}: le conclusioni non cambiano.

## Cautele

- **Dati aggregati.** I flussi sono stimati da stock, non osservati persona per persona. Le provenienze degli RTT (45% da RTDa, 40% da assegni, 15% esterni) sono ipotesi.
- **Stock di fine anno.** Chi ha avuto un assegno solo per alcuni mesi tra due rilevazioni non compare. Le persone transitate dal sistema sono quindi più di quelle stimate.
- **Accesso a RTDb.** Si è seguita l'ipotesi "solo da RTDa". Formalmente la L. 240/2010 lo apre anche a chi ha 3 anni di assegno o l'abilitazione scientifica nazionale (ASN). Cambia la provenienza, non il totale degli stabilizzati.
- **Regola sugli assegni nel 2024.** Il vincolo "solo assegnisti già esistenti" è applicato dal 2025. Se valeva già nel 2024, la crescita di quell'anno nel dato MUR andrebbe verificata, perché potrebbe contare i contratti e non le persone.
- **Enti, stock 2026:** il grafico si ferma al 2024 più lo scenario 2027, quindi il 2026 è un punto intermedio. La quota del calo "tetto 30 mesi" già avvenuta a fine 2026 è un'ipotesi (25%, intervallo 0–50%).
- **Enti, unità annue e persone:** il fattore di conversione (1,15, intervallo 1,0–1,3) è un'ipotesi.
- **Enti, ingressi in ruolo:** il dato di assunzione è di un solo anno (2024) e comprende anche agenzie ed enti fuori dal perimetro EPR in senso stretto, una quota piccola.
- **Enti, borsisti:** sono esclusi da tutte le cifre sugli enti.

## Riproducibilità

```
python stock_flow_precari.py
```

Lo script legge i file in `input/`, richiama `stock_flow_epr.py` per gli enti e scrive `output/precari_stock_flow.csv` e `output/precari_stock_flow.md`. I Monte Carlo usano seed fissi (42 per le università, 7 per gli enti). `python stock_flow_epr.py` stampa i soli risultati degli enti.
"""
    (OUTPUT / "precari_stock_flow.md").write_text(md, encoding="utf-8")

    # ------------------------------------------------------------ console
    print(f"Monitoraggio: stock di oggi = mediana {giorni}: {mon['oggi']}")
    print(f"Precari dic23 {P23} -> oggi {P26}: calo {calo} ({calo / P23:.1%})")
    print(f"Stabilizzati {c['stabilizzati']:.0f}  usciti {c['usciti']:.0f}  "
          f"(MC p10-p90 {q('usciti', 10):.0f}-{q('usciti', 90):.0f}, {ok.mean():.0%} estrazioni valide)")
    print(f"Limite inferiore dal picco: {lb['usciti_min']:.0f}")
    print(f"EPR: usciti {e['usciti_teste']:.0f}, in ruolo {e['in_ruolo']:.0f}, "
          f"fine 2026 {e['P26_teste']:.0f}, a rischio 2027 {e['a_rischio_2027_teste']:.0f}")
    print(f"Sistema: passati {sis['passati']:.0f} -> usciti {sis['usciti']:.0f} ({sis['q_usciti']:.1%}), "
          f"stabilizzati {sis['stabilizzati']:.0f} ({sis['q_stabilizzati']:.1%}), "
          f"rimasti {sis['rimasti']:.0f} ({sis['q_rimasti']:.1%}); "
          f"sensitivita' {q_min:.1%}-{q_max:.1%}")
    print(f"Scritti: {OUTPUT / 'precari_stock_flow.csv'}, {OUTPUT / 'precari_stock_flow.md'}")


if __name__ == "__main__":
    main()
