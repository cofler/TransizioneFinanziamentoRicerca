# Modello economico del sistema università e ricerca — spiegazione

Documento di riferimento per il modello `piano_fte_transizione.py` (e i suoi
predecessori `piano_fte_consolidato.py` e `piano_redefinito.py`). Tutti i valori
sono in **EUR2026 costanti**; i costi degli scenari sono **aggiuntivi** rispetto
a oggi, a regime.

---

## 1. La domanda e l'idea centrale

Il modello risponde a due domande intrecciate: **quanti fondi servono per portare
l'Italia dai suoi 99 ricercatori FTE ogni 100.000 abitanti verso i livelli europei
(media dei virtuosi ~140, migliori ~300)**, e **come si distribuisce quello sforzo
tra due leve distinte** — aumentare il *numero* di ricercatori e aumentare le loro
*paghe* fino alla parità di potere d'acquisto coi paesi UE più performanti.

L'idea centrale è che queste due leve — **quantità** e **prezzo** — non si
compensano ma si sommano, e che una terza dimensione nascosta, la **composizione**
del personale (quanti docenti di ruolo vs quanto "ecosistema" di postdoc, tecnici,
ricercatori a termine), determina quanto costa davvero ogni unità di ricerca.

---

## 2. L'unità di misura: FTE

Tutto il modello è espresso in **FTE-ricerca** (full-time-equivalent). È la stessa
base del dato Eurostat citato: i ricercatori in ambito universitario contati come
unità di lavoro equivalenti a tempo pieno, rapportati alla popolazione.

Ogni figura contribuisce alla forza-ricerca in proporzione alla frazione di tempo
che dedica alla ricerca, il coefficiente **α**:

| Figura | α (quota-ricerca) |
|---|---|
| Docente di ruolo (PO/PA) | 0,50 |
| RTT / ricercatore a termine | 0,75 |
| Precari (postdoc/assegni) | 0,75 |

La forza-ricerca del sistema è dunque `FTE = Σ (teste_i × α_i)`, e la **densità** è
`FTE / (popolazione/100.000)`, con popolazione = 58,934 mln → `POP_100K = 589,34`.

**Perché questo risolve la confusione di partenza.** Un conteggio in *teste* dei soli
strutturati (~144/100.000) e un conteggio in *FTE* dei ricercatori (99/100.000)
misurano cose diverse e non vanno mescolati. I ~60.000 docenti di ruolo, ad α 0,50,
valgono 30.000 FTE = ~51/100.000: circa metà del 99. Il resto è ecosistema
(postdoc/assegni ad α 0,75). Ne segue che **il divario 99→140 è in gran parte
"attorno al docente", non di cattedre.**

---

## 3. Le due leve

**Leva Q — quantità.** Portare la densità FTE da 99 al target. Richiede di assumere
più persone; il costo per FTE dipende da *chi* si assume (vedi composizione).

**Leva W — paghe.** L'uplift verso la parità di potere d'acquisto coi 5 paesi che
pagano meglio: media top-5 129.829 / Italia 78.758 = **×1,65**. La leva W si applica
a *tutto* lo stock (non solo ai nuovi ingressi), perché la parità riguarda tutti i
ricercatori. Scala il personale, **non** le attrezzature (prezzate sui mercati
internazionali, non sugli stipendi accademici italiani).

> ### Fonte del ×1,65, e la sua verifica indipendente
>
> **Fonte primaria: ReICO — *Research and Innovation Careers Observatory***, iniziativa
> congiunta Commissione europea + OCSE (dal 2024, ERA Policy Agenda Action 4): 53 paesi,
> oltre 200 indicatori, fra cui il reddito dei dottori di ricerca **a parità di potere
> d'acquisto**
> ([hub](https://www.oecd.org/en/data/insights/data-explainers/2025/06/research-and-innovation-careers-observatory-reico-hub.html),
> [dashboard](https://www.oecd.org/en/data/dashboards/research-and-innovation-careers-observatory-reico.html)
> — oecd.org blocca l'accesso automatico, i dati vanno letti a mano).
> Cinque valori di testa: 153.819, 148.806, 119.119, 113.706, 113.695; Italia 78.758.
> Il rapporto è adimensionale, quindi vale a prescindere dall'unità purché tutti e sei i
> valori stiano nella stessa e siano aggiustati per il potere d'acquisto.
>
> **Verifica indipendente.** Lo stesso rapporto sui cinque paesi UE migliori dello studio
> CARSA, *Remuneration of Researchers in the Public and Private Sectors*, Service Contract
> REM01, Commissione europea, DG Research Direzione D, aprile 2007, ISBN 92-79-05602-4
> ([PDF](https://euraxess.ec.europa.eu/sites/default/files/policy_library/final_report.pdf)),
> **Tabella 10 p. 46**, colonna PPS, dati 2006 N=6110:
>
> `(60.530 AT + 56.721 NL + 56.268 LU + 55.998 BE + 53.358 DE) / 5 / 34.120 IT = 1,658`
>
> Due rilevazioni indipendenti, a vent'anni di distanza, su popolazioni non identiche,
> danno lo stesso gap a meno dello **0,6%**. È il fatto più robusto di tutto il ramo
> retributivo, e vale la pena citarlo così: non un numero, due numeri che convergono.
>
> *(Il deflatore CARSA è dichiarato a p. 45 — `PPS = EUR ÷ coefficiente correttivo` — e i
> coefficienti stanno nell'Annex 4.3, p. 85. **Non** è uno studio MORE: quelli, MORE1 2010
> / MORE2 2013 / MORE4 2021, sono successivi e di altri autori. Versioni precedenti di
> questo documento attribuivano male la fonte.)*
>
> ### ⚠️ Tre avvertenze, da riportare ovunque il numero compaia
>
> **1. Il paniere ReICO non è ristretto all'UE.** I due valori di testa (153.819 e
> 148.806) staccano il terzo di oltre 25 punti percentuali e sono verosimilmente extra-UE
> (Stati Uniti, Svizzera). Il numero va letto come "i 5 paesi che pagano meglio", non "i 5
> paesi UE". Sui soli tre paesi dietro gli outlier il rapporto sarebbe **×1,47**; sul solo
> primo paese, ×1,95. Se il confronto deve restare intra-UE, il paniere va rifatto.
>
> **2. La popolazione ReICO sono i dottori di ricerca di tutti i settori**, non i
> ricercatori accademici. Il modello applica `W` a docenti, RTT, postdoc e borse: è un
> trasferimento fra popolazioni diverse. CARSA misurava i ricercatori, ed è la ragione per
> cui la coincidenza dei due numeri è rassicurante ma non dimostrativa.
>
> **3. È un obiettivo ambizioso per costruzione**: la media dei *cinque migliori*, non la
> media UE. Nella tabella CARSA la media UE25 (40.126 PPS) dava un moltiplicatore di
> **×1,18**, circa un terzo del costo aggiuntivo del ramo paghe. Chi legge "parità PPP"
> nei grafici deve sapere che la parità è **coi migliori**, non con la media.
>
> ### Cosa ha fatto la Commissione fra il 2007 e ReICO
>
> **MORE2, *Remuneration – Cross-Country Report* (WP4), aprile 2013**
> ([PDF](https://euraxess.ec.europa.eu/sites/default/files/policy_library/report_on_case_study_of_researchers_remuneration.pdf)).
> Stesso oggetto, stesso committente. Alla sez. 3.1.1 (p. 21) recensisce lo studio 2007 e
> lo critica: non tiene conto delle differenze di regime fiscale e previdenziale, e «*the
> sampling approach pursued in the study does not lend itself to uncover statistically
> significant differences across sectors and countries*». La critica colpisce proprio
> l'uso che il modello fa di quei dati — confrontare livelli medi fra paesi — e va messa
> in conto se il numero finisce in un documento pubblico. È anche il motivo per cui la
> convergenza con ReICO conta: sposta il peso della prova su una fonte che quella critica
> non ha.
>
> Di conseguenza MORE2 **non ha rifatto la media PPS per paese**: ha sostituito la survey
> con una rete di esperti nazionali e pubblica la Tab. 3.2.1 (p. 38) come *percentuale del
> paese che paga meglio, per stadio R1–R4, in PPP*. MORE3 (2017) e MORE4 (2021) hanno
> spostato la remunerazione dentro le survey come soddisfazione e condizioni di lavoro.
>
> ### Sensitività storica
>
> Tenendo i nominali CARSA del 2006 e riportando il **solo** deflatore al presente (PLI
> Eurostat 2024, consumi individuali, EU27=100:
> [Italia 98,1](https://ec.europa.eu/eurostat/databrowser/view/prc_ppp_ind/default/table?lang=en)
> contro Austria 119,7, Paesi Bassi 121,0, Germania 109,1 — nel 2006 l'Italia costava
> *più* di tutti e tre) il rapporto scende a **×1,349** (`--uplift-ppp 1.349`). È una
> sensitività, non una stima: aggiorna la metà che restringe il gap e lascia ferma quella
> che lo allarga (il gap nominale, con le paghe accademiche italiane bloccate 2011-2015 e
> poi recuperate sotto inflazione). Che ReICO dia ×1,65 sui dati correnti suggerisce che le
> due metà si siano in larga parte compensate.
>
> *Nota tecnica:* non usare i coefficienti correttivi del personale UE (`prc_colc_nat`)
> come deflatore. Pongono Belgio e Lussemburgo = 100 per **convenzione**, essendo le sedi
> di riferimento, e così il Lussemburgo — il paese più caro d'Europa, PLI 150,7 — entra nel
> paniere top-5 come se costasse la media UE. È un artefatto: dà ×1,404, valore da scartare.
>
> **Il prossimo affinamento utile** è un uplift *per figura* invece di uno scalare unico:
> oggi `W` moltiplica allo stesso modo la borsa del dottorando e lo stipendio
> dell'ordinario, e non c'è motivo perché il gap sia lo stesso.

Un risultato importante: **la leva paghe pesa più della leva quantità**, proprio
perché agisce sull'intero organico e non solo sui nuovi. Nel modello statico, per la
media virtuosi a parità PPP, la componente paghe supera la componente quantità.

---

## 4. Lo stato stazionario "cattedre" e l'imbuto di carriera

Lo **stato stazionario** verso cui il modello tende è la composizione prodotta
dall'**imbuto di carriera**: PhD → postdoc → RTT → ruolo, con sopravvivenze P1
(PhD→postdoc, 0,75) e P2 (postdoc→ruolo, 0,67), da cui P1×P2 ≈ 0,50 (metà dei
dottori arriva al ruolo).

In stato stazionario la quota di ogni stadio è proporzionale a
`probabilità × durata`. Poiché il ruolo dura ~28 anni contro i 3 di postdoc e RTT,
lo stadio permanente **domina lo stock**. Pesando per α si ottiene la composizione
"cattedre":

| Stadio | quota FTE |
|---|---|
| postdoc/precari | ~17% |
| RTT | ~12% |
| docente di ruolo | ~71% |

Costo del personale per FTE di questo mix ≈ **159.000 €** (budget pieno), contro
~98.000 € di un mix "ecosistema" (molti postdoc). La differenza — circa 1,6× — è la
leva di politica nascosta: chiudere il divario assumendo professori o costruendo
gruppi attorno a loro. **Attenzione**: il mix ecosistema è economico *proprio perché*
è uno stock permanentemente precario; ridurre la precarietà spinge verso il mix
cattedre, più costoso per FTE. "FTE a basso costo" e "meno precarietà" tirano in
direzioni opposte.

Formula della forza-ricerca per unità di flusso d'ingresso, a regime:

```
κ(P2, precari_anni) = precari_anni·α_precari + P2·D_RTT·α_RTT + P2·PERM_DUR·α_docente
```

con `D_RTT = 3`, `PERM_DUR = 28`. Il flusso d'ingresso a regime per una densità
target D* è `flusso = D*·POP_100K / κ`.

---

## 5. La frontiera iso-HERD (prezzo ↔ quantità)

A **spesa in ricerca fissata** (HERD = quota del PIL), le due leve si scambiano: se
si alzano le paghe, per tenere la stessa % di HERD bisogna *ridurre* il personale.

```
densità(W) = HERD_target / [ avgCOSTO · (W + (1-λ)/λ) ] / POP_100K
```

dove `avgCOSTO` è la quota-ricerca media degli stipendi per FTE (comp. cattedre
≈ 87.078 €) e `λ = 0,70` è la quota-lavoro dell'HERD. A **HERD 0,69% fisso**
(composizione tutto-cattedre, `--quota-ric-uni 0`, come nella tabella che il modello
stampa a schermo):

| Paghe W | Densità FTE/100k | Teste totali |
|---|---|---|
| 1,00 | 183 | ~224.300 |
| 1,30 | 153 | ~187.500 |
| 1,349 (sensitività storica) | 149 | ~182.600 |
| **1,65 (parità PPP)** | **129** | **~157.500** |

Passare alle paghe europee dentro lo stesso 0,69% impone **−30% di personale**: o
183 ricercatori pagati come oggi, o 129 pagati alla europea, per la stessa spesa R&S.
È questo vincolo che il terzo scenario allenta cambiando la *composizione* del ruolo.

---

## 6. La contabilità della spesa: HERD vs budget pubblico

Il modello tiene **due misure di costo distinte** — la confusione tra le due era un
errore delle prime versioni:

- **HERD (spesa R&S)** = solo la *quota-ricerca* degli stipendi + attrezzature:
  `Σ FTE_i·COSTO_i` per il personale, poi `/λ` per aggiungere le attrezzature. È la
  metrica dell'obiettivo ERA (0,69% del PIL). La metà-didattica dello stipendio di un
  docente **non** è HERD.
- **Budget pubblico** = *stipendi pieni* (inclusa la didattica) + attrezzature R&S:
  `Σ teste_i·COSTO_i + attrezzature`. È ciò che paga davvero il Tesoro.

Con l'uplift W, il personale è moltiplicato per W in entrambe; le attrezzature no.

**Conseguenza controintuitiva ma importante**: "stesso HERD" non significa "stesso
costo per lo Stato". Pagare la parità PPP a *meno* persone (146) costa al budget
pubblico un po' *più* (≈0,75% PIL) che pagare come oggi *più* persone (213, ≈0,69%),
perché l'uplift colpisce anche la metà-didattica degli stipendi, che sta fuori
dall'HERD ma dentro il bilancio.

---

## 7. La dinamica: transizione e ricircolo dei precari

Il modello non è solo un conto a regime: **simula il percorso anno per anno** con un
modello stock-flow per coorte/età (dal 2026, orizzonte 50 anni).

- Il **ruolo** è strutturato per età (40→67, pensione a 68), inizializzato con una
  distribuzione a campana centrata sui 56 anni: da qui l'**onda dei pensionamenti**,
  con picco a metà anni '30.
- I **precari** sono un compartimento con **permanenza media `precari_anni`**
  (default 3): ogni anno una quota avanza a RTT (tasso `P2/precari_anni`) e una esce
  per attrito (`(1-P2)/precari_anni`). Così lo *stock* di precari può gonfiarsi senza
  gonfiare il *flusso* d'ingresso.
- Le **leve di policy** (stabilizzazione P2, flusso d'ingresso) sono rampate dai
  valori odierni ai valori di regime su `ramp` anni.

**Il risultato-chiave sulla dinamica**: la composizione parte al ~51% di FTE da ruolo
(oggi, precari-heavy) e converge al ~71% (cattedre) **solo dopo ~28 anni**. Non sono
i soldi a fissare la velocità, è la **durata del ruolo**: una cattedra dura 28 anni,
quindi lo stock di ruolo si riempie con quella lentezza. La densità target FLC (140)
si raggiunge intorno al 2055, quella ERA (213) intorno al 2058: circa **30 anni**,
non un piano quinquennale. La spesa, invece, **sale prima** della densità:
stabilizzare e pagare costa subito, ma la capacità arriva con 6 anni di ritardo
(postdoc→RTT→ruolo) e l'onda pensionamenti sottrae capacità durante l'espansione.

**Effetto del ricircolo (permanenza nel precariato).** Alzando `precari_anni` il
flusso d'ingresso scende a valori realistici, ma lo stato stazionario si sposta *via*
dai cattedre:

| precari_anni | flusso ingresso/anno | quota-docente regime | densità @0,69% (W=1) |
|---|---|---|---|
| 3 | ~11.450 | 71% (cattedre) | 213 |
| 6 | ~6.000 | 61% | 229 |
| 9 | ~4.060 | 53% | 253 |

È un risultato sostanziale: **il precariato prolungato è esso stesso uno stock
strutturale permanente**. Un sistema che tiene le persone 9 anni da precario non
converge mai alla composizione a cattedre. La bassa stabilizzazione storica
(P2 ≈ 0,10) e la lunga permanenza da precario sono la stessa cosa vista da due
angoli, ed entrambe spiegano perché l'Italia è a 99 con una composizione lontana dai
paesi a carriera stabile.

---

## 8. Dati e parametri

**Macro (ISTAT / Eurostat).** PIL 2024 = 2.192.182 mln € — **costante** su tutto
l'orizzonte, quindi le percentuali di PIL sono a PIL fermo; HERD 2023 = 0,36% PIL;
obiettivo ERA HERD = 0,69% PIL.

**Popolazione: proiezione SSP2** (Wittgenstein Centre / IIASA WIC2023, indicatore
`pop`, scenario 2, Italia, tutte le età, entrambi i sessi —
[WCDE](https://iiasa.ac.at/models-tools-data/wcde)). Nodi quinquennali interpolati
linearmente: 58,93 mln nel 2025 → 55,95 nel 2050 → **50,82 nel 2080**, cioè −13,8%.
Il nodo 2025 coincide con la popolazione che il modello già usava, quindi la baseline
non si muove; l'orizzonte 2080 sta dentro i dati (la serie arriva al 2085), quindi non
c'è estrapolazione.

Conseguenza: **due densità distinte nei CSV e nei grafici**, e vanno tenute separate.

| colonna | denominatore | a cosa serve |
|---|---|---|
| `densita` | popolazione dell'anno (SSP2) | è la grandezza confrontabile con gli altri paesi in quell'anno; a organico invariato **sale**, perché scende il denominatore (+16% al 2080) |
| `densita_pop2026` | popolazione 2026 fissa | isola l'effetto organico da quello demografico; è la base su cui sono definiti i **target** di scenario e la frontiera iso-HERD, che sono grandezze di stato stazionario e non hanno un anno |

Per questo la traiettoria supera il target nominale: ERA PPP + ric.univ. ha target 136
e arriva a 136 a demografia ferma, ma a **158** con la popolazione proiettata. Il
confronto col target (`_tempo_a_regime`, il pannello di `transizione_fte.png`) usa
sempre `densita_pop2026`; i grafici di composizione mostrano `densita`, dichiarandolo
nel titolo dell'asse.

**Densità FTE (Openpolis su Eurostat 2021).** Italia 99; media UE ~143 (usata come
"virtuosi" ~140); Danimarca ~300; agli ultimi posti Romania 32, Bulgaria 48.

**Costi lordo ente (€/anno, EUR2026).** Docente = mix PO/PA (0,39×130.000 +
0,61×78.000) ≈ 98.280; RTT 55.000; precari (postdoc/assegni) 45.000. Uplift PPP =
×1,65 (ReICO, Commissione UE + OCSE, top-5 vs Italia sul reddito dei dottori di ricerca
a parità di potere d'acquisto; confermato a ×1,658 da CARSA/REM01 2007 — vedi le tre
avvertenze alla leva W).

**Parametri strutturali (assunzioni esplicite, tutte variabili).**

| Parametro | Valore | Note |
|---|---|---|
| α docente | 0,50 | dall'indagine ISTAT 2004-05 — **il più fragile** |
| α RTT / precari | 0,75 | conservativo |
| λ (quota-lavoro HERD) | 0,70 | HE labour-intensive per metodo ISTAT |
| P1 (PhD→postdoc) | 0,75 | |
| P2 target (postdoc→ruolo) | 0,67 | |
| P2 storico | 0,10 | stabilizzazione odierna, bassa (CLI) |
| durata postdoc / RTT | 3 / 3 anni | |
| durata ruolo | 28 anni | ingresso 40, pensione 68 |
| ruolo oggi | 60.000 teste | stima FLC (CLI) |
| permanenza precari | 3 anni | default, ricircolo (CLI) |

---

## 9. Come si esegue

Richiede `python3` con `numpy`, `pandas`, `matplotlib`. Esecuzione base:

```
python3 piano_fte_transizione.py
```

Parametri da riga di comando (per l'analisi di sensibilità, senza toccare il codice):

```
--p2-hist       stabilizzazione storica            (default 0.10)
--perm-oggi     teste di ruolo oggi                (default 60000)
--precari-anni  permanenza media nel precariato    (default 3)
--ramp          anni di rampa delle leve           (default 6)
```

Esempio (precariato realistico a permanenza lunga):

```
python3 piano_fte_transizione.py --precari-anni 9 --p2-hist 0.10
```

Output: stampa a schermo (frontiera iso-HERD + tabelle di transizione per FLC, ERA a
paghe odierne, ERA a parità PPP), il grafico `transizione_fte.png` e i CSV
`transizione_*.csv`.

---

## 10. Risultati principali

- **Perché 99 e non 144**: i docenti di ruolo, ad α 0,50, danno ~51/100k in FTE;
  il resto fino a 99 è ecosistema. Il divario è di ecosistema, non di cattedre.
- **Le due leve si sommano, non si compensano**; la leva paghe pesa più della
  quantità perché agisce su tutto lo stock.
- **Frontiera iso-HERD**: a 0,69% fisso, la parità PPP impone −32% di personale
  (213 → 146 FTE/100k).
- **Stesso HERD ≠ stesso budget**: la parità a meno persone costa al Tesoro un po'
  più di più persone pagate come oggi (la metà-didattica dell'uplift è fuori HERD).
- **Le durate governano la velocità**: la transizione verso la composizione cattedre
  richiede ~28 anni (la vita di una cattedra), non i soldi; la spesa sale prima della
  densità e l'onda pensionamenti degli anni '30 sottrae capacità.
- **Precariato = stock strutturale**: allungando la permanenza da precario il flusso
  d'ingresso torna realistico ma il regime non è più cattedre — la precarietà è una
  fetta permanente dell'organico e spiega il 99 italiano.

---

## 11. Limiti e prossimi passi

- **Slack di calibrazione**: l'HERD "oggi" ricostruito dal modello vale ~0,28% contro
  lo 0,36% ISTAT (nasce dal mescolare densità Eurostat e spesa ISTAT). I *livelli*
  assoluti di %PIL vanno letti con questa tolleranza; le *differenze* rispetto a oggi
  sono più solide.
- **α docente 0,50** è il parametro più fragile (indagine ISTAT ferma al 2004-05).
- **Compartimento singolo per i precari**: a permanenze molto lunghe (>9-10 anni)
  perde realismo (nessuno resta davvero con attrito costante); da usare con cautela.
- **Marginale ≈ medio e mix costante**: stima di primo ordine; rendimenti decrescenti
  e colli di bottiglia (spazi, strumenti) non modellati.
- **EPR / settore governativo** trattato a parte nelle versioni consolidate; qui la
  dinamica è centrata sul settore universitario.
- Prossimi affinamenti utili: onda pensionamenti da microdati MUR per età reale;
  split del residuo (attrezzature vs organico di supporto) come parametro esplicito;
  integrazione dell'imbuto EPR nel motore dinamico.

---

## Appendice — file del progetto

| File | Contenuto |
|---|---|
| `piano_fte_transizione.py` | **Modello dinamico** (formulazione corrente): transizione stock-flow, ricircolo precari, CLI |
| `piano_fte_consolidato.py` | Modello statico a due leve + frontiera iso-HERD (formulazione-madre) |
| `piano_redefinito.py` | Prima formulazione a obiettivi fissi (densità + stipendio → residuo) |
| `transizione_fte.png` | Grafico dell'evoluzione (densità e budget nel tempo) |
| `transizione_*.csv` | Serie storiche annuali per scenario (FLC, ERA paghe oggi, ERA parità PPP) |
