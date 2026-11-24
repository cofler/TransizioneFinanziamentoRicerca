# Transizione del finanziamento della ricerca pubblica

Modello stock-flow per coorte del sistema di ricerca pubblico italiano, 2026-2080:
demografia del personale (dottorandi → postdoc → RTT → ruolo, più il ramo degli enti
pubblici di ricerca), spesa in % di PIL (HERD / GOVERD / GERD), scale stipendiali CCNL
e retroflusso fiscale (IRPEF, addizionali, contributi, IRAP).

Si usa in due modi, che calcolano **esattamente la stessa cosa**: una webapp per
esplorare gli scenari e una CLI per il report completo.

## Webapp

```bash
pip install -r requirements.txt
streamlit run app.py
```

Dodici leve in chiaro nella sidebar (obiettivi di spesa, paghe, composizione del ruolo,
durate della carriera, leve di smorzamento), tutte le altre sotto *Impostazioni
avanzate*. I grafici sono interattivi: passando il mouse su un anno si leggono tutti i
livelli di quell'anno insieme al totale.

## Riga di comando

```bash
python piano_transizione.py                    # scenario di default
python piano_transizione.py --help             # ~60 parametri
python piano_transizione.py --uplift-ppp 1.6485 --quota-ric-uni 0 --precari-anni 3
```

Produce il report testuale completo su stdout, tre CSV (una riga per anno, 76 colonne) e
nove PNG in `output/`. È l'unica delle due strade che genera il report narrativo e le
tabelle di diagnostica.

Altri entry point: `confronto_prepensionamento.py` (sweep della leva di
prepensionamento), `spesa_pubblica_rs_eu.py` (serie storica Eurostat),
`md2docx.py` (converte `MODELLO_spiegazione.md` in Word).

## Come è organizzato

```
config.py         costanti e parametri di scenario, con le fonti nei commenti
motore.py         il motore stock-flow: l'unico punto in cui il tempo avanza
regime.py         stato stazionario in forma chiusa, scale stipendiali, frontiera iso-HERD
calibrazione.py   i residui ricavati dal dato osservato
irpef.py          imposte e contributi
tabelle.py        righe delle tabelle di scenario
scenario.py       giuntura parametri → DataFrame, condivisa da CLI e webapp
grafici.py        DataFrame → PNG (CLI)
grafici_web.py    DataFrame → figure Plotly (webapp)
piano_transizione.py  CLI: parametri, report, CSV, PNG
app.py            webapp Streamlit
```

`scenario.py` è il punto in cui i parametri diventano stato del modello. Serve perché
`config.py` è un singleton globale mutabile: la CLI lo scriveva una volta e usciva, la
webapp lo riesegue decine di volte nello stesso processo e da più thread. `applica()`
riparte quindi ogni volta dallo stato pristino di `config` — così due run con parametri
diversi non si contaminano — e `esegui()` serializza l'intera sezione critica con un
lock.

## Documentazione

`MODELLO_spiegazione.md` è il documento di riferimento: ipotesi, calibrazione, risultati
e **limiti dichiarati** dello scenario `ADI_Manifesto_ric`. Include i punti in cui il modello
non raggiunge i suoi obiettivi — il rapporto studenti/docente, che peggiora prima di
migliorare, e il test di validazione sugli RTT, che sbaglia del 31,5%.

Tutti i valori sono in EUR2026 costanti, a PIL fermo. I costi di scenario sono
aggiuntivi rispetto al 2026.

## Stock e flussi dei precari (2023 → oggi)

Modello separato, che non tocca la simulazione: stima quanti precari (RTDa, assegnisti,
contratti e incarichi postdoc; università ed enti) sono passati in tenure track o in
ruolo e quanti sono usciti dal sistema dal dicembre 2023 a oggi.

```bash
python stock_flow_precari.py          # pipeline: output/precari_stock_flow.csv e .md
streamlit run app_precari.py          # webapp con i parametri sui cursori
python controllo_aree_assegnisti.py   # (facoltativo) controllo su Cerca Università
```

| File | Ruolo |
|---|---|
| `stock_flow_precari.py` | modello università, sistema complessivo, CSV e report |
| `stock_flow_epr.py` | modello enti pubblici di ricerca (dati Conto annuale) |
| `app_precari.py` | webapp Streamlit sopra gli stessi due moduli |
| `controllo_aree_assegnisti.py` | verifica perché le somme per area CUN sottostimano gli assegnisti |

Lo stock di oggi delle università viene dal monitoraggio giornaliero di Cerca Università
(`../NumeroRicercatoriEmail/nazionale/ricercatori_nazionale.csv`, task pianificato
"MonitoraggioPrecari"). Ogni esecuzione della pipeline ne salva la serie aggregata in
`input/monitoraggio_snapshot.csv`: dove il monitoraggio non è raggiungibile (webapp in
cloud) si usa lo snapshot. Lo storico viene da `input/La grande espulsione_2.xlsx` e dalla
serie MUR; gli enti dai grafici del Conto annuale e da `input/AssuntiCessati2024.xlsx`.

## Verifica

Dopo una modifica al modello, il test che conta è che la CLI produca gli stessi CSV:

```bash
python piano_transizione.py --out /tmp/dopo
diff /tmp/prima/transizione_ADI_Manifesto_ric.csv /tmp/dopo/transizione_ADI_Manifesto_ric.csv
```
