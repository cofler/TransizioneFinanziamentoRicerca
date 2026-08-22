### Righe delle tabelle di scenario e loro impaginazione.
 
from __future__ import annotations

import pandas as pd

RIGHE_TAB = [
    ("Densità università (FTE/100k)",      "densita",        1),
    ("Personale di ruolo PO/PA+ric. (teste)", "ruolo_teste", 0),
    ("RTT (teste)",                       "rtt_teste",      0),
    ("Postdoc università (teste)",        "postdoc_teste",  0),
    ("Dottorandi (teste)",                "phd_teste",      0),
    ("Dottori che proseguono/anno",       "phd_prosegue",   0),
    ("Dottori fuori accademia/anno",      "phd_fuori_accademia", 0),
    ("P1 effettivo (prosegue/dottori)",   "P1_effettivo",   2),
    ("Pensionamenti/anno",                "pensionamenti",  0),
    ("EPR di ruolo (teste)",              "epr_ruolo",      0),
    ("EPR precari (teste)",               "epr_precari",    0),
    ("Densità EPR (FTE/100k)",             "densita_epr",    1),
    ("TA università (FTE)",               "ta_uni_fte",     0),
    ("TA enti pubblici (FTE)",            "ta_epr_fte",     0),
    ("TA totale (teste)",                 "ta_teste",       0),
    ("Quota TA sul personale R&S",        "quota_ta",       3),
    ("Componente precaria (% postdoc)",   "componente_precaria", 1),
    ("  idem, con RTT fra i precari (%)", "componente_precaria_rtt", 1),
    ("Professori PO/PA (teste)",          "prof_teste",     0),
    ("  di cui ordinari (teste)",         "po_teste",       0),
    ("  di cui associati (teste)",        "pa_teste",       0),
    ("Quota ordinari sui professori",     "quota_po",       3),
    ("Costo medio professore (EUR)",      "costo_docente",  0),
    ("Docenti (FTE didattici)",           "fte_didattico",  0),
    ("Studenti per docente (FTE)",        "stud_per_doc",   2),
    ("Studenti per docente, stud.~pop.",  "stud_per_doc_pop", 2),
    ("Densità ricercatori pubblici (FTE/100k)", "densita_ric_pub", 1),
    ("Densità personale R&S tot. (FTE/100k)",   "densita_rs_tot",  1),
    ("Moltiplicatore paghe W",            "W_paghe",        2),
    ("Borsa PhD (EUR/mese netti)",        "borsa_mese",     0),
    ("HERD (% PIL)",                      "HERD_%PIL",      3),
    ("GOVERD (% PIL)",                    "GOVERD_%PIL",    3),
    ("R&S pubblica HERD+GOVERD (% PIL)",  "RS_pubblica_%PIL", 3),
    ("BERD imprese - IPOTESI (% PIL)",    "BERD_%PIL",      3),
    ("GERD totale (% PIL)",               "GERD_%PIL",      3),
    ("Spesa R&S pubblica (mln EUR)",      "spesa_RS_mln",   0),
    ("Budget pubblico tot. (% PIL)",      "pubblico_%PIL",  3),
    # --- retroflusso fiscale: la parte di spesa che rientra ---------------------
    # il monte stipendi è la base (le attrezzature non pagano IRPEF), l'IRPEF è la
    # sola imposta erariale, il retroflusso totale aggiunge addizionali, contributi
    # e IRAP. Le due misure NON vanno sommate fra loro: la seconda include la prima.
    ("Monte stipendi lordo ente (mln EUR)", "monte_stip_mln", 0),
    ("Retribuzioni lorde - imponibile (mln EUR)", "ral_mln",  0),
    ("IRPEF erariale (mln EUR)",          "irpef_mln",      0),
    ("Aliquota IRPEF media effettiva",    "aliq_irpef_media", 3),
    ("IRPEF su monte stipendi",           "irpef_quota_stip", 3),
    ("Retroflusso tot. IRPEF+add+contr+IRAP (mln EUR)", "retro_mln", 0),
    ("Retroflusso tot. su monte stipendi", "retro_quota_stip", 3),
]


# Righe che si aggiungono solo quando la leva prepensionamento e' accesa. Stanno qui,
# accanto a RIGHE_TAB, invece che nel chiamante.
RIGHE_PREPENS = [("Prepensionati/anno", "prepensionati", 0),
                 ("Pensioni anticipate in carico (teste)", "prepens_in_carico", 0),
                 ("Costo pensioni anticipate (mln EUR)", "pensioni_anticipate_mln", 0)]


def righe_con_prepens() -> list[tuple[str, str, int]]:
    """RIGHE_TAB con le righe del prepensionamento infilate dopo i pensionamenti.

    Restituisce una lista NUOVA. La versione precedente splicciava RIGHE_TAB sul posto:
    innocuo per la CLI, che gira una volta sola, ma in un processo che rieseguE il
    modello - la webapp - le righe si duplicavano a ogni run."""
    r = list(RIGHE_TAB)
    i = [e for e, _, _ in r].index("Pensionamenti/anno") + 1
    r[i:i] = RIGHE_PREPENS
    return r


def tabella_scenario(df: pd.DataFrame, anni: list[int],
                     righe: list[tuple[str, str, int]] | None = None) -> pd.DataFrame:
    """Trasposta: una riga per variabile, una colonna per anno."""
    v = df[df["anno"].isin(anni)].set_index("anno")
    out = {}
    for etichetta, col, dec in (RIGHE_TAB if righe is None else righe):
        out[etichetta] = [f"{v.loc[a, col]:,.{dec}f}" for a in anni]
    return pd.DataFrame(out, index=anni).T
