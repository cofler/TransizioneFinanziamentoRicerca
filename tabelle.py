"""Righe delle tabelle di scenario e loro impaginazione.

Separato dai grafici perche' l'oggetto e' diverso: qui si sceglie COSA riportare e
con quante cifre, non come disegnarlo.

CONVENZIONE: i valori di configurazione si leggono SEMPRE come C.NOME, mai importati
per nome. main() li riassegna a runtime (calibrazioni, argomenti da CLI) e solo
l'accesso per attributo vede il rebinding; un `from config import X` catturerebbe una
copia congelata all'import. Le funzioni invece non vengono mai riassegnate e si
importano per nome.
"""
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
    ("Professori PO/PA (teste)",          "prof_teste",     0),
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
    # il monte stipendi e' la base (le attrezzature non pagano IRPEF), l'IRPEF e' la
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


def tabella_scenario(df: pd.DataFrame, anni: list[int]) -> pd.DataFrame:
    """Trasposta: una riga per variabile, una colonna per anno."""
    v = df[df["anno"].isin(anni)].set_index("anno")
    out = {}
    for etichetta, col, dec in RIGHE_TAB:
        out[etichetta] = [f"{v.loc[a, col]:,.{dec}f}" for a in anni]
    return pd.DataFrame(out, index=anni).T
