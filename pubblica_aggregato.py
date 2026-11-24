"""Pubblica l'aggregato nazionale del monitoraggio nel repo dati, con controllo sui cali.

Legge ../NumeroRicercatoriEmail/nazionale/ricercatori_nazionale.csv (grezzo, per ateneo,
resta locale), ne ricava la serie giornaliera NAZIONALE dei giorni completi (stessa
funzione della pipeline) e la scrive in <repo>/precari_nazionale.csv; se il file e'
cambiato fa commit e push con l'identita' git configurata nel clone.
Nel file ci sono solo totali nazionali per giorno: nessun nome, email o ateneo.

Controllo prima di pubblicare. Ogni giorno nuovo (successivo all'ultimo gia' pubblicato)
e' confrontato con l'ultimo giorno pubblicato; la pubblicazione si FERMA se:
  - una figura nazionale cala piu' di SOGLIA_NAZIONALE (i cali veri osservati, alle
    scadenze di fine mese, arrivano a -9% per gli assegnisti e -7% per gli RTDb);
  - un ateneo (con almeno MIN_ATENEO persone) scende sotto META_ATENEO del suo valore:
    tipico di una pagina caricata a meta' (mai successo nei giorni validi finora).
Se si ferma non scrive nulla nel repo, annota i motivi in output/pubblicazione_log.txt
ed esce con codice 1. Dopo aver controllato, `--forza` pubblica comunque.

Avvisi email (stesse variabili di NumeroRicercatoriEmail/update_sheet.py: SMTP_HOST,
SMTP_PORT, SMTP_USER, SMTP_PASSWORD, ALERT_TO; con Gmail serve una App Password):
  - al primo giorno di blocco (non si ripete ogni giorno finche' resta bloccato);
  - il primo giorno di ogni mese, un riepilogo del mese precedente.
Senza SMTP configurato gli avvisi finiscono solo nel log.

Uso:  python pubblica_aggregato.py [--repo PERCORSO] [--forza] [--no-push]
Pensato per essere chiamato da run_local.ps1 dopo count_nazionale_ricercatori.py.
"""
import argparse
import json
import os
import re
import smtplib
import subprocess
import sys
from datetime import date, datetime
from email.message import EmailMessage
from pathlib import Path

import numpy as np
import pandas as pd

import stock_flow_precari as SF

REPO_DATI = SF.ROOT.parent / "MonitoraggioNazionalePrecari"
NOME_FILE = "precari_nazionale.csv"
LOG = SF.OUTPUT / "pubblicazione_log.txt"
STATO = SF.OUTPUT / "pubblicazione_stato.json"
URL_REPO = "https://github.com/cofler/MonitoraggioNazionalePrecari"
SOGLIA_NAZIONALE = 0.15
META_ATENEO = 0.5
MIN_ATENEO = 20


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


def per_ateneo(path, giorni):
    """Totale docenti (RTDA+RTDB+RTT) e assegni (AR+CR+IPD+IR) per ateneo e giorno."""
    d = pd.read_csv(path, dtype=str)
    d = d[d.data != "data"].copy()
    d["tipo"] = np.where(d["RTDA"].notna() & (d["RTDA"] != ""), "doc", "ass")
    d = d.drop_duplicates(["data", "codice_ateneo", "tipo"], keep="last")
    for c in [*SF.COL_DOC, *SF.COL_ASS]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["tot"] = np.where(d.tipo == "doc", d[list(SF.COL_DOC)].sum(axis=1),
                        d[list(SF.COL_ASS)].sum(axis=1))
    d = d[d.data.isin(giorni)]
    return d.pivot_table(index="data", columns=["ateneo", "tipo"], values="tot")


def anomalie(serie, pubblicata):
    """Motivi di blocco per i giorni nuovi rispetto all'ultimo giorno pubblicato."""
    if pubblicata is None or pubblicata.empty:
        return []
    rif = pubblicata.index[-1]
    nuovi = [g for g in serie.index if g > rif]
    if not nuovi or rif not in serie.index:
        return []
    motivi = []
    base = serie.loc[rif]
    for g in nuovi:
        calo = serie.loc[g] / base - 1
        for col, v in calo[calo < -SOGLIA_NAZIONALE].items():
            motivi.append(f"{g}: {col} nazionale {base[col]} -> {serie.loc[g, col]} ({v:+.0%})")
    at = per_ateneo(SF.MONITORAGGIO_CSV, [rif, *nuovi])
    for g in nuovi:
        prima, dopo = at.loc[rif], at.loc[g]
        crollo = (dopo < META_ATENEO * prima) & (prima >= MIN_ATENEO)
        for (ateneo, tipo) in crollo[crollo].index:
            fig = "docenti RTD/RTT" if tipo == "doc" else "assegni e contratti"
            motivi.append(f"{g}: {ateneo}, {fig} {int(prima[(ateneo, tipo)])} -> "
                          f"{int(dopo[(ateneo, tipo)])}")
    return motivi


def scrivi_log(righe):
    LOG.parent.mkdir(exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"[{datetime.now():%Y-%m-%d %H:%M}] " + "\n    ".join(righe) + "\n")


def invia_email(oggetto, testo):
    """Invia via SMTP; se non configurato o se fallisce, lo annota nel log e prosegue."""
    host, to = os.environ.get("SMTP_HOST"), os.environ.get("ALERT_TO")
    if not host or not to or not os.environ.get("SMTP_PASSWORD"):
        scrivi_log([f"Email non inviata (SMTP non configurato): {oggetto}"])
        return False
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = oggetto, os.environ["SMTP_USER"], to
    msg.set_content(testo)
    try:
        with smtplib.SMTP(host, int(os.environ.get("SMTP_PORT") or 587), timeout=30) as s:
            s.starttls()
            s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
            s.send_message(msg)
    except Exception as e:
        scrivi_log([f"Email non inviata ({e}): {oggetto}"])
        return False
    return True


def leggi_stato():
    try:
        return json.loads(STATO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def salva_stato(stato):
    STATO.parent.mkdir(exist_ok=True)
    STATO.write_text(json.dumps(stato, indent=1), encoding="utf-8")


def riepilogo_mensile(stato, ultimo_pubblicato):
    """Il primo giorno utile di ogni mese manda il riepilogo del mese precedente."""
    mese = date.today().strftime("%Y-%m")
    if stato.get("ultimo_riepilogo") == mese:
        return
    if "ultimo_riepilogo" not in stato:  # prima esecuzione: niente da riassumere
        stato["ultimo_riepilogo"] = mese
        return
    prec = stato["ultimo_riepilogo"]
    righe = LOG.read_text(encoding="utf-8").splitlines() if LOG.exists() else []
    del_mese = [r for r in righe if r.startswith(f"[{prec}")]
    pubbl = sum("Pubblicato" in r for r in del_mese)
    blocchi = sum("BLOCCATO" in r for r in del_mese)
    testo = (f"Riepilogo della pubblicazione automatica, {prec}.\n\n"
             f"Giorni con pubblicazione: {pubbl}\nGiorni bloccati per cali sospetti: {blocchi}\n"
             f"Ultimo giorno pubblicato: {ultimo_pubblicato or 'nessuno'}\n"
             f"Stato attuale: {'BLOCCATO' if stato.get('bloccato') else 'regolare'}\n\n"
             f"Repo: {URL_REPO}\nLog completo: {LOG}\n\n"
             + "\n".join(r for r in del_mese if re.search(r"BLOCCATO|forzato|non inviata", r)))
    if invia_email(f"Monitoraggio precari: riepilogo {prec}", testo):
        stato["ultimo_riepilogo"] = mese


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, default=REPO_DATI, help="clone locale del repo dati")
    ap.add_argument("--forza", action="store_true", help="pubblica anche se il controllo blocca")
    ap.add_argument("--no-push", action="store_true", help="scrive e fa commit, senza push")
    a = ap.parse_args()

    if not SF.MONITORAGGIO_CSV.exists():
        sys.exit(f"Monitoraggio non trovato: {SF.MONITORAGGIO_CSV}")
    if not (a.repo / ".git").exists():
        sys.exit(f"{a.repo} non e' un clone git")

    if not a.no_push:
        git(a.repo, "pull", "--ff-only", "--quiet")
    out = a.repo / NOME_FILE
    pubblicata = pd.read_csv(out, index_col="data", dtype={"data": str}) if out.exists() else None
    serie = SF._serie_da_grezzo(SF.MONITORAGGIO_CSV)

    stato = leggi_stato()
    ultimo = pubblicata.index[-1] if pubblicata is not None and len(pubblicata) else None
    riepilogo_mensile(stato, ultimo)

    motivi = anomalie(serie, pubblicata)
    if motivi and not a.forza:
        scrivi_log(["BLOCCATO: cali sospetti, niente pubblicato. Controlla e poi usa --forza:",
                    *motivi])
        if not stato.get("bloccato"):
            invia_email(
                "Monitoraggio precari: pubblicazione bloccata",
                "La pubblicazione automatica dell'aggregato nazionale si e' fermata per cali "
                "sospetti:\n\n  " + "\n  ".join(motivi) +
                f"\n\nUltimo giorno pubblicato: {ultimo}. L'app resta su quel dato.\n"
                "Se il calo e' vero, pubblica con:\n"
                f"  python {Path(__file__).resolve()} --forza\n\n"
                "Non riceverai altre email finche' il blocco resta attivo.")
        stato["bloccato"] = True
        salva_stato(stato)
        print("Pubblicazione bloccata:\n  " + "\n  ".join(motivi) + f"\nDettagli in {LOG}")
        sys.exit(1)

    stato["bloccato"] = False
    salva_stato(stato)
    serie.to_csv(out, index_label="data", lineterminator="\n")
    git(a.repo, "add", NOME_FILE)
    if not git(a.repo, "status", "--porcelain", "--", NOME_FILE):
        print("Aggregato invariato: niente da pubblicare")
        return
    git(a.repo, "commit", "-m", f"Aggiornamento dati fino al {serie.index[-1]}", "--", NOME_FILE)
    if not a.no_push:
        git(a.repo, "push", "--quiet")
    nota = " (forzato)" if motivi else ""
    scrivi_log([f"Pubblicato{nota}: {len(serie)} giorni, fino al {serie.index[-1]}"])
    print(f"Pubblicati {len(serie)} giorni, fino al {serie.index[-1]}{nota}")


if __name__ == "__main__":
    main()
