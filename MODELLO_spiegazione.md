# Lo scenario ADI Manifesto — modello, ipotesi, risultati

Documento di riferimento del modello `piano_transizione.py`, **centrato sullo
scenario `ADI_Manifesto_ric`** (nei grafici: *ADI Manifesto + ric.univ.*), che è la
configurazione di arrivo del progetto. Gli altri due scenari — FLC ed ERA — restano
nel codice come **termini di paragone**: servono a isolare cosa fa ciascuna leva, non
sono proposte alternative.

Tutti i valori sono in **EUR2026 costanti**, a **PIL fermo** (2.192.182 mln, ISTAT
2024). I costi di scenario sono **aggiuntivi rispetto al 2026**.

**I risultati sono riportati al 2070**, che è l'orizzonte dei grafici. La simulazione
prosegue fino al **2080** — serve a verificare che lo stato stazionario sia davvero
raggiunto — e tabelle e CSV restano a orizzonte pieno, ma nel 2070 il sistema sta
ancora **rientrando dalla gobba del 2057** (§11): i valori di quell'anno sono quindi
vicini al regime, non identici a esso.

---

## 0. Che cos'è lo scenario ADI Manifesto

Lo scenario tiene insieme **quattro obiettivi che di solito si presentano come
alternativi**:

1. **spesa** — portare la ricerca pubblica agli obiettivi europei: HERD **0,68%** del
   PIL e GOVERD **0,23%**, cioè **0,91% di R&S pubblica**; questi obiettivi originano dalla media in HERD e GOVERD dei 5 paesi che hanno già superato il **3%** di spesa totale (pubblica + privata) che si sta discutendo con l'**ERA Act**, riportati ad un totale del 3%; è stato applicato anche un leggero scostamento, che sposta uno 0.0.01% di spesa dall'obiettivo HERD originale a quello GOVERD e che aiuta a raggiungere prima una situazione di regime stabile;
2. **paghe** — portare le retribuzioni alla **media europea** dei dottori di ricerca a
   parità di potere d'acquisto (**×1,16**), e la borsa di dottorato da 1.195 a 1.656
   EUR/mese netti (×1,39) agganciandola alle paghe pre-doc rappresentate dagli incarichi di ricerca;
3. **quantità** — portare i **ricercatori pubblici** (università + enti) alla **media
   europea semplice: 221 FTE ogni 100.000 abitanti**, contro i 156 di oggi. È un
   obiettivo esplicito di *organico*, derivato dai dati Eurostat su cui
   il modello si calibra;
4. **carriera** — trasformare il precariato da parcheggio a esito incerto in un
   passaggio a esito dichiarato, e ricostruire il personale tecnico-amministrativo.

Lo fa usando tre leve: oltre a *quantità* e *prezzo* muove la
**composizione** del ruolo, reintroducendo in università una figura di **ricercatore a
tempo indeterminato con inquadramento da ente di ricerca** — carico didattico ridotto
(quota-ricerca 0,75 invece di 0,50) e stipendio su scala EPR — per **un terzo** del
ruolo. Si ignorano quindi tutti i tetti di spesa, blocchi del turnover e limiti alle facoltà assunzionali di atenei e EPR.

### Quello che lo scenario raggiunge 

| | 2026 | **2070** | obiettivo |
|---|---|---|---|
| **Densità ricercatori pubblici** univ.+enti, **popolazione SSP2** | 156,3 | **246,1** | **221** (media semplice UE27) |
| Densità FTE università (pop. 2026 fissa) | 109,2 | **166,5** | *risultato*, non obiettivo |
| Densità FTE università (popolazione SSP2) | 109,2 | 187,1 | — |
| Densità personale R&S totale con TA (SSP2) | 239,5 | **417,3** | — |
| **HERD (% PIL)** | 0,360 | **0,697** | 0,68 |
| **GOVERD (% PIL)** | 0,207 | **0,256** | 0,23 |
| **R&S pubblica (% PIL)** | 0,567 | **0,953** | 0,91 |
| GERD, con BERD per ipotesi (% PIL) | 1,366 | 3,000 | 3,00 |
| Moltiplicatore paghe W | 1,00 | **1,16** | 1,16 |
| Borsa di dottorato (EUR/mese netti) | 1.195 | **1.656** | 1.656 |
| Componente precaria (% postdoc su personale di ricerca) | 39,0 | **17,6** | — |
| Personale di ruolo università (teste) | 47.877 | **94.484** | — |
| di cui a profilo ricercatore | 4.831 | **31.495** (1/3) | 1/3 |
| Enti pubblici di ricerca, ruolo (teste) | 30.896 | 38.544 | — |
| Personale TA, univ.+enti (FTE) | 48.894 | **89.552** | — |
| Docenti in FTE didattici | 35.749 | **43.795** | — |
| Studenti per docente (FTE) | 19,45 | **15,88** ⚠️ | 14,3 (media UE) |
| Costo aggiuntivo per lo Stato (mld/anno) | — | **+12,8** | — |
| Budget pubblico totale (% PIL) | 0,843 | 1,432 | — |

> ⚠️ **Il traguardo sul carico didattico è toccato ma non tenuto.** Il rapporto migliora
> da subito — il massimo di tutta la traiettoria è il 19,45 dell'anno base — tocca 14,3
> nel **2057** al culmine della gobba demografica, e poi **risale a 15,88 nel 2070** e
> 16,21 a regime. Il postdoc smette di fare didattica (§1), il che toglie ~11.800
> FTE-docente dal denominatore: distribuito su venti anni non produce più il
> peggioramento transitorio che si aveva a rampa dieci (21,20 nel 2036), ma la didattica
> del postdoc va comunque **rimpiazzata**, non solo tolta — e a questo organico non lo è
> del tutto. Vedi §10.

> **HERD e GOVERD al 2070 stanno sopra il target** (0,697 e 0,256 contro 0,68 e 0,23)
> perché il sistema sta ancora rientrando dal picco del 2057. A stato stazionario
> pieno — 2080 — sono 0,686 e 0,230, cioè esattamente a bersaglio: l'obiettivo di spesa
> è **centrato**, ma dieci anni dopo la fine dei grafici.

> **Calo demografico** L'Italia perde
> il 13,8% di popolazione fra il 2026 e il 2080 (SSP2, §11): lo stesso organico serve
> meno persone, quindi vale una densità più alta.

**Tempi.** Il 90% del divario di densità FTE è colmato entro il **2051** (25 anni). La
spesa aggiuntiva tocca il massimo di **14,3 mld** nel **2057**, è a **12,8 nel 2070** e
rientra a 11,5 a regime: è un'onda demografica, non una scelta (§11).

---

## 1. L'unità di misura: FTE-ricerca e il coefficiente α

Tutto il modello è espresso in **FTE-ricerca** (full-time-equivalent), la stessa base
del dato Eurostat: le persone contate in proporzione alla frazione di tempo che
dedicano alla ricerca, il coefficiente **α**.

| Figura | α (quota-ricerca) | complemento didattico |
|---|---|---|
| Professore di ruolo (PO/PA) | 0,50 | 0,50 |
| **Ricercatore universitario di ruolo** (`ric_uni`) | **0,75** | 0,25 |
| RTT (tenure track) | 0,75 | 0,25 |
| **Postdoc** | **0,75 → 1,00** (rampa **20a**) | **0,25 → 0,00** |
| Dottorandi | 0,75 | escluso |
| Ricercatori degli enti (EPR) | 0,75 | — |
| Personale TA | 0,563 (misurato) | — |

`FTE = Σ (teste_i × α_i)`, e la densità è `FTE / (popolazione/100.000)`.

**I dottorandi NON contano negli FTE** (`PHD_IN_FTE = False`), ma il loro **costo entra
comunque** in HERD e nel budget: la borsa è spesa di R&S comunque la si conti.

> **Il postdoc è l'unica figura con un α che si muove nel tempo, ed è una LEVA del piano
> come `W` o `P2`.** Oggi il postdoc insegna — 0,75 come RTT e ricercatori — ed è la
> situazione osservata: l'anno base deve riprodurla, altrimenti la calibrazione starebbe
> misurando un sistema che non esiste. **A regime il postdoc è una posizione di sola
> ricerca** (α = 1,00): la didattica che oggi gli si scarica addosso è esattamente ciò che
> il piano vuole togliere. In mezzo c'è una rampa **sua**, `RAMP_ALPHA_PREC = 20` anni,
> il doppio di `RAMP` — la didattica non si toglie a nessuno per decreto da un anno
> all'altro, si smette di assegnarla man mano, e questa in particolare va smessa piano
> perché qualcuno la deve raccogliere (§10). Ne discende, in coerenza, che **la valutazione della didattica esca
> dai concorsi RTT**: non si può pretendere didattica da chi non ha un incarico didattico.
>
> Il fatto che l'α di partenza sia quello di oggi ha una conseguenza importante: **l'anno
> base non cambia**. Il gap Eurostat si chiude sui 47.340 precari di sempre, gli RTT
> ricostruiti restano 4.734 e lo scarto dichiarato del −31,5% resta quello (§13). Tutti
> gli effetti della leva si vedono **lungo la transizione**, non nel 2026.
>
> ⚠️ **E l'effetto principale è sul carico didattico — motivo per cui la rampa è doppia.**
> Spegnere il peso didattico del postdoc toglie ~11.800 FTE-docente dal denominatore,
> mentre il ruolo cresce con i tempi lunghi della carriera. Concentrato in dieci anni il
> disimpegno correva più delle assunzioni e il rapporto studenti/docente **saliva a 21,20
> nel 2036**, sopra il 19,45 di partenza: per un decennio il piano avrebbe *peggiorato*
> la didattica prima di migliorarla. Su venti anni non accade, e **non costa nulla a
> regime** — la rampa è una velocità, non una destinazione: stesso stato stazionario,
> stesse teste ogni anno, traiettorie che coincidono dal 2046 (§10). Resta comunque il
> prezzo esplicito della scelta: **la didattica del postdoc va rimpiazzata, non solo
> tolta**, e non torna stabilmente sotto la media europea.

### Il termine di paragone europeo

Lo **stesso file** che dà le due ancore italiane
(`doc/rd_p_persocc__custom_22235345_spreadsheet.xlsx`, Eurostat 2023) contiene tutti i
27 paesi. I ricercatori si ottengono per differenza — *Total* meno *Total excluding
researchers* — e per l'Italia il conto torna esattamente sui due numeri che il modello
usa: HES 95.559 − 31.357 = **64.202**, GOV 45.209 − 17.537 = **27.672**.

| Densità ricercatori, 2023 | HES | GOV | **pubblica (HES+GOV)** |
|---|---|---|---|
| EU27, aggregata (somma/somma) | 151,6 | 48,9 | **200,5** |
| EU27, **media semplice dei 27 paesi** | 170,3 | 50,8 | **221,0** |
| EU27, mediana | 160,6 | 47,0 | 215,0 |
| **Italia** | **109,1** | **47,0** | **156,1** |
| Danimarca / Portogallo / Irlanda (testa) | 327 / 297 / 271 | 32 / 17 / 16 | 359 / 314 / 287 |
| Romania / Bulgaria / Cipro (coda) | 34 / 52 / 84 | 36 / 75 / 11 | 70 / 127 / 95 |

**È da qui che viene l'obiettivo di organico: la media semplice del totale pubblico,
221 FTE/100k.** Media *semplice* che
misura "com'è fatto un paese europeo tipico".


Due verifiche incrociate. Sul GOV l'Italia (47,0) è **esattamente sulla mediana
europea** e a due punti dall'aggregata: **il divario italiano è tutto universitario**, ed
è la ragione per cui il grosso dello sforzo di spesa va sull'HERD e non sul GOVERD. E la
densità pubblica che il modello ricostruisce per il 2026 (156,3) coincide con quella
calcolata qui dai dati grezzi (156,1).

---
## 2. Lo stato iniziale: stock osservati, densità come risultato

Il modello **non parte da un target di densità**: parte dagli stock e la densità è ciò
che ne esce. 

| Figura | Teste 2026 | Fonte | FTE |
|---|---|---|---|
| Professori PO+PA | 43.046 | MUR open data 2023 (16.574 PO + 26.472 PA) | 21.523 |
| Ricercatori a tempo indeterminato | 4.831 | MUR 2023, ruolo a esaurimento | 3.623 |
| Postdoc / precari | 47.340 | **variabile di chiusura** | 35.505 |
| RTT | 4.734 | ricostruito da P2 storico | 3.551 |
| **Totale università** | | | **64.202** |
| Ricercatori enti (settore GOV) | 36.896 | Eurostat 2023, 27.672 FTE ÷ α | 27.672 |
| di cui precari | 6.000 | | |
| Dottorandi | 47.000 | iscritti 2024 | (esclusi) |
| Personale TA | 86.911 teste | Eurostat 2023, 48.894 FTE | 48.894 |

**Il precariato è la variabile di chiusura in questo modello.** I 47.340 postdoc non sono un dato: sono
il numero che riconcilia l'FTE ricostruito con il dato Eurostat. Il MUR ne separa 25.113 (RTD-A + assegni); la stima con l'onda
PNRR era ~35.000; il valore di chiusura sta sopra entrambi (+35%) in modo da includere sicuramente anche i borsisti.

> **Perché la chiusura usa l'α di OGGI e non quello di regime.** Il postdoc arriva a α
> 1,00 solo a fine rampa (§1). Se si chiudesse il gap con l'α di regime ne basterebbero
> 36.331 — un numero molto più vicino alla stima PNRR — ma sarebbe **il numero sbagliato**:
> descriverebbe il 2026 con la quota-ricerca del 2036. L'anno base va calibrato su com'è
> il sistema oggi, e oggi i postdoc insegnano.

> Il prezzo della chiusura: con 47.340 precari e `P2_HIST = 0,10` il modello
> genera **4.734 RTT** contro i **6.915 osservati** (RTD-B + L.79/2022, MUR 2023):
> −31,5%. Per tenerli sul dato servirebbe `P2_HIST = 0,146`, cioè una stabilizzazione
> storica più bassa. Coerente, ma allora `P2_HIST` smette di essere un dato e diventa
> un secondo residuo. Il modello preferisce dichiarare lo scarto. `--precari-oggi 35000`
> riporta il precariato alla stima e lascia il gap di densità in vista.

>**Il perimetro "EPR" non sono solo gli enti MUR.** Il settore GOV di Frascati è tutta la PA
che fa ricerca: ISS, ISPRA, CREA, INAIL, IZS, ARPA, regioni, ministeri. Da qui i due
canali di ingresso del §7.

### Il postdoc non è una figura sola: incarico di ricerca e contratto di ricerca

Chi inizia il postdoc **entro 4 anni dalla laurea magistrale** sta su un **incarico di
ricerca** — lordo amministrazione più basso ed **esente IRPEF** (art. 6 c.6
L. 398/1989) — gli altri su un **contratto di ricerca** pieno e tassato:

| figura | lordo amministrazione | IRPEF | quota delle **persone** | quota dello **stock** |
|---|---|---|---|---|
| **incarico di ricerca** (entro 4 anni dalla magistrale) | **30.000** | **esente** | **53%** | **5,3%** |
| contratto di ricerca | 45.000 | tassato | 47% | 94,7% |
| **costo medio del postdoc** | **44.205** | | | |

> **La finestra è 4 anni, ed è una scelta di proposta, non un dato.** L'incarico di
> ricerca esente è uno strumento di **ingresso**: a 6 anni copriva metà del precariato e
> diventava un canale di sottoinquadramento stabile, a 4 resta il ponte fra dottorato e
> primo contratto. Il modello ne paga il conto senza sconti — il postdoc medio passa da
> 40.125 a **44.205** e la platea esente si assottiglia fino a sparire quasi del tutto.

> ⚠️ **Le due quote non sono la stessa cosa, e confonderle è l'errore facile.** Il 53% è
> la quota di **persone** che hanno l'opzione; ma **la finestra si chiude durante il
> postdoc**, quindi l'incarico copre solo **0,5 dei 5 anni** di permanenza. Sullo
> **stock**, che è ciò che il modello prezza e tassa, la quota vale
> `0,53 × 0,5/5 = 0,053`. È la quota di **anni-persona**, non di teste. Si muove con
> `--anni-incarico`, e a `--precari-anni` diverso si riscala da sola.
>
> Il passaggio da 2,5 a 0,5 anni è una **sottrazione, non un riscalamento**: chiudere la
> finestra due anni prima accorcia di esattamente due anni il tratto coperto di chiunque
> resti dentro. Va detto che 2,5 era già una stilizzazione ("metà del postdoc") e non la
> media di una distribuzione: l'agente rappresentativo del modello finisce il dottorato a
> `ETA_FINE_PHD` = 33, cioè 5,8 anni dopo la magistrale, e sarebbe fuori finestra da
> subito sia a 6 anni sia a 4. `ANNI_INCARICO` vive sulla **sottopopolazione** che si
> dottora presto, non sull'agente medio, e va letto insieme alla quota di persone.

**Come è stimato il 53%.** Non è osservato: si incrociano due distribuzioni. Il postdoc
inizia alla fine del dottorato, quindi "entro 4 anni dalla magistrale" equivale a
"dottorato conseguito prima dei **31,2** anni" (27,2 + 4).

| età al conseguimento del dottorato | quota |
|---|---|
| meno di 29 anni | 22,2% |
| 29-30 anni | 29,7% |
| 31-35 anni | 31,3% |
| 36 anni e oltre | 16,8% |
| **età media** | **32,6** |

*Fonte: [AlmaLaurea, Profilo dei Dottori di ricerca 2022, Report 2023](https://www.almalaurea.it/sites/default/files/2023-07/dottori_profilo_report2023.pdf), Fig. 3 p. 7 (5.007 dottori, 37 atenei). Età media alla laurea magistrale biennale 27,2 anni: AlmaLaurea, Profilo dei Laureati 2022.*

Interpolando uniformemente dentro le classi, la quota sotto i 31,2 anni è **53,1%**, da
cui **0,53**. La soglia cade appena sopra la **mediana** (31,0 anni): è per questo che
togliere due anni di finestra costa 12 punti di platea invece di qualcuno — si taglia
**dentro** la classe più popolata, non sulla sua coda.

> **Il controllo per area vale per la finestra a 6 anni, e non si rifà qui.** Rifatta per
> **area disciplinare** e ripesata sulle quote di area, la stima a 6 anni dava **65,6%**
> contro il **65,7%** aggregato: due strade diverse, stesso numero. A 4 anni servirebbero
> le **distribuzioni** per area, non le sole medie, che non sono nella fonte. La stima
> aggregata a 4 anni sta quindi in piedi da sola, e questo è un pezzo di verifica in meno.
>
> | area | età media al dottorato | quota entro 6 anni | peso |
> |---|---|---|---|
> | Scienze di base | 30,8 | 80,7% | 20,3% |
> | Ingegneria | 32,3 | 67,3% | 21,0% |
> | Sc. economiche, giuridiche e sociali | 33,1 | 61,4% | 12,5% |
> | Scienze della vita | 33,1 | 59,6% | 29,3% |
> | Scienze umane | 34,0 | 59,4% | 16,8% |

> ⚠️ **Il punto debole è l'età alla laurea magistrale**, che è una media generale mentre
> i dottori sono una popolazione selezionata (il 68,2% ha 110 e lode contro il 42,0% dei
> laureati) e verosimilmente si laurea prima — **e a finestra corta pesa di più**, perché
> la soglia si sposta dentro la classe densa invece che sulla coda. La sensitività:
> **26,5 anni → 44,5% | 27,2 → 53,1% | 28,0 → 58,2%** (a 6 anni l'escursione era
> 61,3%–70,7%). Si muove con `--quota-incarico`.

> **L'età di fine dottorato del modello è ora quella osservata.** `ETA_FINE_PHD` era 34
> per ipotesi, ed era **incompatibile con questa stessa stima**: a 34 anni si è già a 6,8
> anni dalla laurea magistrale, quindi nessuno sarebbe stato dentro la finestra, che
> allora era di 6 anni. Ora vale
> **33** — i 32,6 osservati, arrotondati perché le classi della coorte sono annuali — e il
> divario medio dalla magistrale è **5,4 anni**, coerente con un 65% che ci sta dentro.
> Ne discendono un **ingresso in ruolo a 43 anni** invece di 44 e una **carriera di 26
> anni** invece di 25.
>
> Con la finestra portata a 4 anni quella coerenza si allenta — 5,4 > 4 — ma non cambia
> di segno: la quota a incarico non si calcola sull'età **media**, è l'integrale della
> distribuzione sotto la soglia, e a 4 anni ci sta dentro la metà che si dottora presto.

---

## 3. Le tre leve dello scenario

### Leva W — le paghe: ×1,16, la media europea

`W` moltiplica **tutto lo stock**, non solo i nuovi ingressi: la parità retributiva
riguarda chi c'è già. Scala il **personale**, non le attrezzature. È **aumentata progressivamente** su 10 anni come le altre leve, non applicata di colpo.

> ### Da dove viene il ×1,16, e la sua verifica indipendente
>
> **Fonte primaria: ReICO — *Research and Innovation Careers Observatory***, iniziativa
> congiunta Commissione europea + OCSE (dal 2024, ERA Policy Agenda Action 4),
> indicatore di reddito dei dottori di ricerca **a parità di potere d'acquisto**
>
> `UPLIFT_PPP_EU = 91.343 (media europea) / 78.758 (Italia) = 1,160`
>
> È il traguardo **"stare nella media"**, non "stare coi migliori". Il rapporto è
> adimensionale: vale a prescindere dall'unità, purché entrambi i valori stiano nella
> stessa e siano aggiustati per il potere d'acquisto.
>
> **Verifica indipendente, a vent'anni di distanza.** Lo studio CARSA, *Remuneration of
> Researchers in the Public and Private Sectors*, Service Contract REM01, Commissione
> europea, DG Research Direzione D, aprile 2007, ISBN 92-79-05602-4
> ([PDF](https://euraxess.ec.europa.eu/sites/default/files/policy_library/final_report.pdf)),
> **Tabella 10 p. 46**, colonna PPS, dati 2006 N=6110: la media UE25 vale 40.126 PPS
> contro 34.120 italiani, cioè **×1,176**, a **−1,4%** dal valore ReICO.
>
> E la conferma vale su **entrambi i panieri**: i 5 paesi UE migliori di CARSA davano
> ×1,658 contro il ×1,649 dei 5 paesi che pagano meglio in ReICO. Due rilevazioni
> indipendenti, due decenni, popolazioni non identiche, **e concordano sia sulla media
> sia sull'estremo**. È il fatto più robusto di tutto il ramo retributivo.


> **NB: La popolazione ReICO sono i dottori di ricerca di tutti i settori**, non i
> ricercatori accademici. Il modello applica `W` a professori, ricercatori, RTT,
> postdoc e borse: è un trasferimento fra popolazioni diverse. CARSA misurava i
> ricercatori, ed è la ragione per cui la coincidenza dei numeri è rassicurante ma non
> dimostrativa.


### Leva della composizione — un terzo del ruolo a profilo ricercatore

`QUOTA_RIC_UNI = 1/3`. La figura `ric_uni` **esiste già**: sono i 4.831 ricercatori a
tempo indeterminato, ruolo a esaurimento con profilo di ricerca. La riforma non la
crea, la **ripopola**.

A regime un ricercatore costa **71.785 EUR** (scala EPR III→II→I, soglie 10 e 20 anni
su una carriera di 25) contro i **120.720** di un professore, e ha α 0,75 contro 0,50:

`FTE per euro: 0,75/71.785 = 2,52 × (0,50/120.720)`

**Un ricercatore così definito rende due volte e mezzo gli FTE-ricerca per euro di un
professore.** La conversione avviene **per ricambio** — i nuovi entrano come
ricercatori — non riclassificando chi è già in servizio.

### Leva TA — il personale tecnico-amministrativo, esplicito ed espansivo

Il TA è **misurato** (Eurostat 2023) e **cresce
più che proporzionalmente** ai ricercatori sia per numeri che per stipendi. Vedi §9.

---

## 5. Gli obiettivi di spesa: HERD, GOVERD e l'ERA Act

### Da dove vengono i due target

L'ancora è la **media di HERD e GOVERD dei paesi europei che hanno già raggiunto e
superato il 3% del PIL in R&S** — il livello di investimento che il prossimo **ERA Act**
potrebbe fissare. Ne escono **HERD 0,69%** e **GOVERD 0,22%**, cioè **0,91% di R&S
pubblica**, contro lo 0,57% odierno (0,360 + 0,209).

Nel codice i due target sono scritti con un cursore:

```python
SHIFT = 0.01
HERD_TGT   = 0.69 - SHIFT   # 0.68
GOVERD_TGT = 0.22 + SHIFT   # 0.23
```

`SHIFT` **sposta un decimo di punto dall'università agli enti lasciando fermo il totale
0,91%**. Per questioni di periodo transitorio, si osserva che il regime stazionario è più rapidamente raggiungibile con questo leggero shift verso gli EPR.

### Cosa raggiunge lo scenario

| | 2026 | 2040 | 2057 (picco) | **2070** | *2080* | obiettivo |
|---|---|---|---|---|---|---|
| HERD (% PIL) | 0,360 | 0,561 | 0,724 | **0,697** | *0,686* | 0,68 |
| GOVERD (% PIL) | 0,207 | 0,225 | 0,269 | **0,256** | *0,230* | 0,23 |
| R&S pubblica | 0,567 | 0,786 | 0,993 | **0,953** | *0,916* | 0,91 |
| Budget pubblico totale | 0,843 | 1,159 | 1,501 | **1,432** | *1,373* | — |

Il **GOVERD è a target dal 2030**; l'**HERD supera lo 0,68% durante la gobba
demografica** e ci rientra sopra a regime. Il **GERD tocca il 3% nel 2053**, ma vedi
l'avvertenza qui sotto.

È l'unica tabella del documento che porta anche il 2080, perché è quella in cui la
differenza conta: **al 2070 la spesa è ancora ~0,03 punti sopra il bersaglio su
entrambi i rami**, ed è il rientro dalla gobba a riportarla esattamente a target dieci
anni dopo. Chi legge i grafici, che si fermano al 2070, vede quindi un piano che *sfora*
il proprio obiettivo, non uno che lo manca.

### Le due contabilità: HERD+GOVERD ≠ budget pubblico (FFO)

Il modello tiene **due misure di costo distinte**:

- **HERD / GOVERD (spesa R&S)** = solo la **quota-ricerca** degli stipendi + il TA in
  FTE-R&S + le attrezzature. La metà-didattica dello stipendio di un professore **non**
  è HERD.
- **Budget pubblico** = **stipendi pieni** (didattica compresa, TA in teste) +
  attrezzature. È ciò che paga davvero il pubblico, e nel 2080 vale **1,371% del PIL**
  contro lo 0,915% di R&S.

Con l'uplift `W` il personale è moltiplicato in entrambe; le attrezzature no.

> **Il 3% del PIL non dipende da nessuna leva di questo modello.** Il BERD — la
> ricerca delle imprese, due terzi del GERD italiano — **non è modellato**: è
> interpolato sull'avanzamento della componente pubblica verso lo 0,91%, con un tetto
> al 3% (`motore._berd`). Il pubblico deve crescere da 0,57% a 0,91% (×1,6); il privato
> da 0,80% a 2,09% (×2,6). **Il 3% è per due terzi una scommessa sull'industria.**

---

## 6. L'imbuto di carriera: durate, filtri e stabilità

Lo **stato stazionario** verso cui il modello tende è la composizione prodotta
dall'imbuto. Nella configurazione corrente:

```
dottorato 3a --(P1 = 0,42)--> postdoc 5a --(P2 = 0,60)--> RTT 5a --(1,00)--> ruolo 26a
                                                                     (43 → 69 anni)
```

| Parametro | Valore | Significato |
|---|---|---|
| `D_PHD` | 3 anni | durata del dottorato |
| `PRECARI_ANNI` | **5 anni** | permanenza media nel precariato post-dottorale |
| `D_RTT` | **5 anni** | contratto di tenure track |
| `ETA_FINE_PHD` | **33** | fine del dottorato: 32,6 osservati (AlmaLaurea, §2) |
| ingresso in ruolo | **43 anni** | 33 + 5 + 5, **ricavato, non assunto** |
| `ETA_PENS` | **69** | età media di uscita, da USTAT (§8) |
| durata del ruolo | **26 anni** | 69 − 43, endogena |
| `P1` | **0,42** | quota di dottori che prosegue in accademia |
| `P2_TGT` | **0,60** | postdoc → RTT, a fine postdoc |
| `S_RTT_PERM` | 1,00 | **chi entra in RTT arriva al ruolo** |
| `STAB_PHD` = P1×P2 | **0,25** | un quarto dei dottori arriva al ruolo |

**Due filtri in serie, entrambi dichiarati.** Il primo all'uscita dal dottorato
(P1 = 0,42: il 58% va altrove), il secondo a fine postdoc (P2 = 0,60: il 40% di chi ha
provato esce dopo **8 anni** fra dottorato e precariato). **Dall'RTT in poi la carriera
è garantita.** `P1` non è un parametro libero: è ricavato dal vincolo di
stabilizzazione, `P1 = STAB_PHD / P2_TGT`.

**Il ricircolo dei precari.** I postdoc sono un compartimento con permanenza media
`PRECARI_ANNI`: ogni anno una quota `P2/PRECARI_ANNI` avanza a RTT e una quota
`(1−P2)/PRECARI_ANNI` esce per attrito. Così lo *stock* di precari può gonfiarsi senza
gonfiare il *flusso* d'ingresso.


### Cosa cambia sulla stabilità, in numeri

| | 2026 | 2070 |
|---|---|---|
| `P2` — stabilizzazione dei postdoc | 0,10 storico → **0,50 già dal 2026** (pavimento) | **0,60** |
| `P1` effettivo — dottori che proseguono | 0,71 | **0,42** |
| Postdoc che passano a tenure track, teste/anno (`P2 × postdoc / 5`) | **4.734** *(col pavimento `P2_MIN` già attivo)* | **3.541** |
| Stock di RTT (teste) | 4.734 | **17.706** |
| **Componente precaria** (postdoc su personale di ricerca) | **39,0%** | **17,6%** |
| Dottori che escono dall'accademia, all'anno | 4.601 | 9.546 |
| Dottorandi (teste) | 47.000 | 49.095 |

**Il pavimento sulla stabilizzazione** (`P2_MIN = 0,50`) scavalca la rampa: modella un
**piano straordinario** che agisce subito invece di arrivare a regime in dieci anni.
Vale ~15.000 stabilizzati nel primo triennio (riprendendo la posizione ADI dall'articolo sul piano straordinario del governo https://www.dottorato.it/un-piano-niente-affatto-straordinario-analisi-delladi-sul-reclutamento-universitario-e-la-programmazione-della-legge-di-bilancio-2026/) contro gli ~8.700 della sola rampa.
Attenzione a cosa **non** fa: lo stock di postdoc è *invariante* al pavimento, perché
l'uscita totale dal compartimento vale `1/precari_anni` qualunque sia P2. Il pavimento
non svuota il precariato più in fretta — **sposta persone dalla porta d'uscita alla
tenure track**. È una redistribuzione a somma zero fra le due porte.

**Perché a regime gli ingressi in tenure track sono quelli e non di più.** Non è una
scelta: è il ruolo che li determina. Un organico universitario di 94.484 teste che dura
26 anni richiede ~3.630 ingressi l'anno per stare in piedi (infatti lo stock di RTT,
17.706 su 5 anni di contratto, ne immette 3.541), più quelli del ramo enti.
Il numero di posti di tenure track **non** è libero — è lo stock di ruolo diviso la
durata della carriera. Per aprirne di più bisogna allargare il ruolo (più spesa) o
accorciare la carriera, non ritoccare `P2`.

> ⚠️ **La quota di dottori che arriva al postdoc SCENDE, da 0,71 a 0,42.** Questo è dovuto all'ipotesi di sistema universitario che precarizza meno e stabilizza di più, e quindi assume meno postdoc ma allo stesso tempo assume più rtt. Servono meno PhD in accademia per questo.

### Il ramo enti: due canali, e solo uno si espande

Il perimetro GOV contiene due popolazioni opposte, e il modello le tiene separate:

- **filiera MUR** — imbuto vero: **5 anni di contratto di ricerca** e stabilizzazione
  ex-Madia per il **60%** (`P2_EPR`);
- **resto del settore GOV** — due terzi del perimetro (ISS, ISPRA, CREA, INAIL, IZS,
  ARPA, regioni, ministeri): recluta **per concorso**, non da un postdoc.

Il canale diretto è ancorato a uno **stock osservato** — `EPR_NON_MUR_OGGI` = 23.840
teste, rimpiazzate a **822 assunzioni l'anno** — e **non si espande**: tutta
l'espansione che il GOVERD finanzia passa dalla filiera MUR, l'unica di cui il modello
conosca la struttura di carriera. Sul bacino dei dottorandi pesa il canale postdoc per
intero più il 50% del diretto; il resto sono concorsi da laurea, su un mercato che il
modello non simula.


| paghe | contratti di ricerca/anno | ruolo a regime | precari | teste totali |
|---|---|---|---|---|
| ×1,00 | 1.200 → 667 | 35.442 | 3.334 | 38.775 (+5% vs oggi) |
| **×1,16** | **1.200 → 512** | **32.740** | **2.558** | **35.298 (−4% vs oggi)** |

A spesa fissa, paghe più alte comprano meno persone; e siccome il canale diretto non si
comprime, **l'aggiustamento lo paga tutto la filiera MUR**.


---

## 7. Le share delle posizioni: chi c'è nel sistema, prima e dopo

### Università — teste (dottorandi e TA esclusi)

| | 2026 | quota | 2080 | quota |
|---|---|---|---|---|
| Professori ordinari | 16.788 | 16,8% | 30.784 | **22,1%** |
| Professori associati | 26.258 | 26,3% | 30.754 | **22,0%** |
| **Ricercatori di ruolo** (`ric_uni`) | 4.831 | 4,8% | **30.769** | **22,1%** |
| RTT (tenure track) | 4.734 | 4,7% | 17.702 | **12,7%** |
| Postdoc / precari | 47.340 | **47,4%** | 29.502 | **21,1%** |
| **Totale** | **99.951** | | **139.511** | |

**Il ribaltamento è questo**: si passa da un sistema in cui **quasi metà delle persone è
precaria** a uno in cui le cinque posizioni pesano **circa un quinto ciascuna**, e il
precariato è il segmento più piccolo assieme agli RTT.

### Università — FTE-ricerca

| | 2026 | 2070 |
|---|---|---|
| Professori PO/PA | 33,5% | 32,2% |
| Ricercatori di ruolo | 5,6% | **24,1%** |
| RTT | 5,5% | 13,6% |
| Postdoc | **55,3%** | 30,1% |
| **FTE totali** | **64.202** | **97.901** |

In FTE il ribaltamento è ancora più netto: **il postdoc smette di essere il motore della
ricerca universitaria italiana**. Oggi produce il 55% degli FTE; a fine transizione il
30%, poco più dei professori.

> ⚠️ **Qui i due lati della leva α si vedono insieme.** In FTE il postdoc del 2070 pesa
> con α 1,00 e non 0,75, quindi la sua quota scende **meno** di quanto scendano le teste
> (da 47.340 a 29.502, §7). Non è un peggioramento della composizione: è la stessa
> persona che conta di più come ricercatore perché non insegna più. Il rovescio sta in
> §10 — quella didattica non è sparita, è passata a qualcun altro.


### Enti pubblici di ricerca

| | 2026 | 2070 |
|---|---|---|
| Ruolo (teste) | 30.896 (83,7%) | 38.544 (**93,7%**) |
| Contratti di ricerca (teste) | 6.000 (16,3%) | 2.606 (**6,3%**) |
| Densità EPR (FTE/100k) | 47,0 | 52,4 |

**Livelli di inquadramento**, come quote del ruolo:

| | oggi (osservato) | regime (obiettivo) |
|---|---|---|
| III livello | 71% | **40%** |
| II livello | 19% | **40%** |
| I livello | 10% | **20%** |

Le soglie di anzianità che realizzano il mix (12,0 anni al II, 24,0 al I su una carriera
di 30) sono **rampate come le altre leve**: la quota è uno stock, non si impone, ci
arriva la coorte. Il costo per testa del ruolo EPR sale di conseguenza a **75.217 EUR**,
ed è quel costo — non i 73.500 nominali — che la frontiera iso-GOVERD usa per calcolare
il fabbisogno.

> **Il ramo enti cresce poco in teste, molto in inquadramento e in stabilità.** La
> densità EPR passa da 47,0 a 52,4 FTE/100k mentre il precariato scende dal 16% al 6,3%
> e due terzi del ruolo salgono dal III livello al II o al I. È l'effetto che i conteggi
> per teste non vedono, ed è la ragione per cui lo 0,23% di GOVERD non compra un
> organico molto più grande: lo compra **meglio pagato e più stabile**.

---

## 8. Il costo del personale: coorti, non costi unitari

I professori e i ricercatori universitari **non hanno un costo unitario**: il modello ne
tiene la coorte per età e ne integra la **progressione stipendiale** (scale CCNL PA e
PO, e III/II/I per gli EPR) sulla distribuzione per età che simula già. Un organico
giovane costa poco e uno vecchio costa molto **senza che nessun parametro debba dirlo**.

| Figura | costo lordo ente (EUR/anno) |
|---|---|
| Professore, coorte 2026 | **111.468** |
| Professore, coorte 2070 | **122.823** |
| Ricercatore universitario, a regime | 72.040 |
| Ruolo EPR, a regime | 75.217 |
| RTT | 55.000 |
| **Postdoc università, media pesata** | **44.205** (5,3% incarico a 30.000 + 94,7% contratto a 45.000) |
| Contratto di ricerca EPR (a regime) | 45.000 |
| Dottorando (borsa + contributi) | 22.000 → 30.487 |
| TA (per testa) | 35.000 × 1,6 = 56.000 |

Il professore **rincara del 10,2%** lungo la transizione: la soglia di promozione si
accorcia, quindi chi è promosso passa più anni sulla scala PO e sale più in alto.

### Due parametri della coorte ricavati da USTAT, non assunti

Serie storica del personale universitario per classe di età e qualifica
(`input/docricxclasseetaqualifica_serie.csv`, 1997-2024).

**Età di uscita — `ETA_PENS = 69`.** Non è il limite di legge: nel modello escono tutti a
quell'età, quindi il valore giusto è quello che riproduce gli **anni-persona osservati**,
cioè l'età *media* di uscita. Si stima con l'identità di popolazione stazionaria sulla
classe aperta 65+ (permanenza media = stock / flusso di uscita), su finestre lunghe:
**69,1-69,4** a seconda della finestra, arrotondato a 69 perché le classi della coorte
sono annuali. La stima è sull'**aggregato PO+PA** — le promozioni sono un flusso interno
e si cancellano — quindi non si differenzia per fascia. Gli enti sono personale
contrattualizzato con regole proprie e tengono `ETA_PENS_EPR = 68`.

**Quota promossa — `PROMOSSI_PO = 0,59`.** Nella classe 65+ del 2024 ci sono 3.716
ordinari e 2.070 associati: **più di un terzo dei professori va in pensione da
associato**. Una soglia di anzianità secca, da sola, implicherebbe invece che le classi
anziane siano interamente ordinarie. Il 0,642 grezzo va corretto perché gli ordinari
restano in servizio più a lungo e sono sovrarappresentati nella classe terminale:
l'intervallo identificato è **0,54-0,64**, e 0,59 ne è il punto medio.

**Cosa i dati NON identificano**: lo *spread dei tempi* di promozione. La dispersione per
età osservata mescola i tempi di promozione con l'età d'ingresso in ruolo (sd ≈ 6,4
anni), e il modello fissa l'ingresso a 43 anni per tutti — un ordinario di 42 anni non è
stato promosso dopo un anno di ruolo, è entrato in ruolo a 32. Per questo la promozione
resta a **soglia secca** e si corregge solo il livello a cui satura.

---

## 9. Il personale tecnico-amministrativo: da residuo a obiettivo

Nelle versioni precedenti il supporto era un **residuo di calibrazione** e viveva in due
forme incoerenti fra loro: nel ramo universitario come moltiplicatore proporzionale
(elasticità 1), nel ramo EPR come valore assoluto (elasticità 0). I dati dicevano il
contrario di quell'asimmetria. Ora il TA è **misurato ed esplicito**.

**Fonte**: Eurostat 2023 `rd_p_persocc`, *Total excluding researchers*, unità FTE, Italia.

| | FTE 2023 | per FTE-ricercatore |
|---|---|---|
| Università (HES) | 31.357 | 0,488 |
| Settore GOV | 17.537 | 0,634 |
| **Totale** | **48.894** | |

`ALPHA_TA = 31.357 / 55.738 = 0,563` FTE-R&S per testa: **misurato**, non ipotizzato
(FTE Eurostat ÷ teste MUR, Focus personale 2023). Il TA è **ancorato al rapporto, non al
livello**: prendere il livello assoluto importerebbe dentro un parametro di
comportamento lo scarto di perimetro fra Eurostat e MUR.

### La regola di crescita, e perché qui è una scelta di policy

```
TA(t) = TA(0) · (1 − TA_ELAST + TA_ELAST · R(t)/R(0))
```

`TA_ELAST = 2,2`: **ricercatori ×2 → TA ×3,2**. È un valore ben sopra 1, e va detto
esplicitamente cosa significa: il modello **non tratta il TA come un overhead da
minimizzare, lo tratta come un obiettivo del piano**. L'Italia parte da un deficit di
supporto accumulato in un decennio di blocco del turnover (MUR: TA −3,9% in dieci anni
contro docenti +13,6%), e la regola recupera quel deficit invece di proiettarlo.

> ⚠️ **Il dato storico italiano è 0,33, e non va usato come parametro normativo.** Fra il
> 2018 e il 2023 i ricercatori universitari sono cresciuti del 23,5% in FTE e il
> personale di supporto del 7,2%. Quel numero misura **il blocco del turnover**, non il
> fabbisogno di supporto della ricerca: proiettarlo significherebbe proiettare
> l'austerità. Ma vale anche il contrario — **2,2 non è una stima, è una decisione**, e
> chi non la condivide ha `--ta-elast` per cambiarla (0 = overhead fisso, 1 =
> proporzionale puro).

**Il tetto.** `TA_CAP = 90.000` FTE totali (università + enti). Non è decorativo: **morde
davvero, fra il 2054 e il 2069**, quando la gobba demografica dell'organico di ricerca
spingerebbe il TA oltre quel livello. Sopra il tetto il TA viene riscalato
proporzionalmente fra i due rami.

**Gli stipendi TA** seguono un moltiplicatore **costante ×1,6** (`TA_UPLIFT`), *non* la
leva `W`. È una scelta difendibile — il gap ReICO è misurato sui dottori di ricerca e non
giustifica un uplift sugli amministrativi — ma va saputa.
*(Nota tecnica: il flag `TA_SEGUE_W` in `config.py` e l'opzione `--ta-segue-w` sono
**inerti**: il motore applica sempre `TA_UPLIFT`. Il flag è residuo di una versione
precedente.)*

### Quello che lo scenario raggiunge sul TA

| | 2026 | 2050 | 2057 (tetto) | 2070 |
|---|---|---|---|---|
| TA università (FTE) | 31.357 | 62.272 | 66.330 | **67.566** |
| TA enti (FTE) | 17.537 | 19.941 | 23.670 | **21.986** |
| **TA totale (FTE)** | **48.894** | 82.213 | **90.000** | **89.552** |
| TA totale (teste) | 86.911 | 146.136 | 159.978 | **159.181** |
| Quota TA sul personale R&S | 34,7% | 40,2% | 39,4% | **41,0%** |
| TA per FTE-ricercatore | 0,53 | — | — | **0,70** |

**+83% di personale tecnico-amministrativo della ricerca**, oltre 72.000 teste in più.
Quasi tutta la crescita è nel ramo universitario: il TA degli enti cresce del 16% e
poi rientra, perché rientra l'organico di ricerca che lo giustifica.

> ⚠️ **La quota di TA sale, e va detto contro cosa.** La media europea della quota di TA
> sul personale R&S è ~24% (media semplice dei 27; 23% mediana), e paesi come Svezia
> (9,5%) o Portogallo (9,2%) stanno molto sotto. L'Italia parte già alta (34,7%) e con
> `TA_ELAST = 2,2` arriva al 40,7%. **Lo scenario non porta l'Italia verso la media
> europea su questo indicatore: la porta nella direzione opposta.** È coerente con
> l'idea che il TA sia sottodimensionato *in valore assoluto* rispetto al fabbisogno,
> non con l'idea di allinearsi a un rapporto europeo. Sono due letture diverse dello
> stesso dato e il modello ne sceglie una.

---

## 10. La didattica: FTE-docenza e carico per studente

Le stesse persone dei conteggi di ricerca, pesate per il **complemento** della
quota-ricerca: chi fa ricerca al 50% insegna al 50%, chi la fa al 75% insegna al 25%. Il
peso si ricava da `ALPHA` invece di essere riscritto a mano, quindi se α cambia il
carico didattico segue. **I dottorandi restano fuori**: fanno tutorato, non sono docenti
nell'indicatore. **Il postdoc invece c'è, con un peso che si spegne**: 0,25 nel 2026 come
oggi, 0,00 dal 2046, rampato su **venti** anni (§1).

| | 2026 | 2036 | 2046 (fine rampa did.) | 2050 | 2070 |
|---|---|---|---|---|---|
| **Docenti in FTE didattici** | **35.749** | 37.489 | 37.670 | 41.573 | **43.795** |
| Studenti per docente (FTE), studenti fermi | **19,45** | 18,55 | 18,46 | 16,73 | **15,88** |
| idem, studenti che seguono la demografia | 19,45 | 18,12 | 17,70 | 15,92 | 14,13 |

### ⚠️ Il traguardo europeo è toccato ma non tenuto, e questa è la conclusione principale della sezione

Il rapporto **migliora da subito**: il massimo di tutta la traiettoria è il **19,45
dell'anno base**, e da lì scende. Tocca il traguardo di 14,3 nel **2057** — minimo 14,14,
al culmine della gobba demografica — e poi **risale a 15,88 nel 2070** e 16,21 a regime.

Il problema quindi non è più l'andata, è **il punto d'arrivo**: il piano chiude il divario
di *ricerca*, non quello di *didattica*, e il 14,3 lo attraversa senza restarci. Il
modello dice anche di quanto manca: per stare a 14,3 a studenti fermi servirebbero
**48.624 FTE-docente** contro i 42.887 del 2080, cioè **~5.700 FTE-docente in più —
l'equivalente di ~11.500 professori a α 0,50**. A demografia proiettata il divario si
chiude (14,02 nel 2080, sotto il traguardo dal 2054), ma è il calo degli studenti a
chiuderlo, non il piano.

**La lettura di policy resta netta: la didattica del postdoc va rimpiazzata, non solo
tolta.** Spegnere il peso didattico del postdoc toglie **~11.800 FTE-docente** dal
denominatore (47.340 × 0,25), e nel frattempo il ruolo cresce con i tempi lunghi della
carriera — fra ingresso in dottorato e ingresso in ruolo passano tredici anni (§11).
Quei posti vanno riassegnati a qualcuno.

> **La gobba non c'è più, ed è una SCELTA, non un risultato.** A rampa dieci anni — cioè
> con il postdoc che si disimpegna alla stessa velocità di tutte le altre leve — il
> rapporto **peggiorava prima di migliorare**: saliva a **21,20 nel 2036**, sopra il 19,45
> di partenza. Il denominatore si svuotava in dieci anni mentre le assunzioni arrivavano
> con tredici anni di ritardo, e per un decennio il piano avrebbe **peggiorato la
> didattica prima di migliorarla**.
>
> Portare la rampa a venti anni lo evita, e **non costa nulla a regime**: la rampa è una
> velocità, non una destinazione. Il target di densità resta 163,69, il 2070 resta
> identico (densità 246,1, HERD 0,697), e dal 2046 le due traiettorie coincidono colonna
> per colonna. Non cambia nemmeno **chi** si assume: le teste sono le stesse in ogni anno.
> Cambia solo quanto il postdoc *pesa*, finché la rampa scorre.
>
> È il motivo per cui questa leva merita di stare fra i parametri e non fra le costanti:
> il costo della gobba didattica è un costo di **percorso**, non di regime, e si paga solo
> scegliendo male la velocità. Si torna al comportamento precedente con
> `--ramp-alpha-prec 0`.

> **Perché il livello di partenza è 35.749 e non 23.639.** Gli **studenti impliciti**
> (695.325) sono ricavati come `19,45 × FTE-docente(2026)`, e l'FTE-docente del 2026 deve
> includere la didattica che i postdoc **fanno davvero oggi**. Calibrare il denominatore
> sul postdoc già a α 1,00 darebbe 459.779 studenti impliciti e un rapporto che scende a
> 10,66: un risultato molto più bello e **falso**, perché avrebbe fatto sparire per
> ipotesi la didattica che il piano deve invece riassegnare a qualcuno.

> **In FTE didattici il rapporto si muove molto meno che in teste**, ed è l'effetto che
> conta. Due forze opposte: la transizione sposta persone dal precariato al ruolo (peso
> 0,25 → 0,50, **2×**), ma la stessa transizione toglie al postdoc il suo 0,25. A rampa
> dieci la seconda vinceva per un decennio; distribuita su venti anni non arriva mai a
> superare la prima, e il saldo resta positivo dall'inizio.

> ⚠️ **Qui il compromesso si paga, ed è giusto dirlo.** Lo scenario ERA — tutto cattedre,
> paghe ferme — arriva a **12,59** studenti per docente nel 2080 contro i **16,21** di
> ADI Manifesto, perché un ricercatore a α 0,75 insegna metà di un professore. **Convertire un
> terzo del ruolo a profilo ricercatore compra FTE di ricerca e costa FTE di didattica**,
> e sommato all'uscita del postdoc dalla didattica è ciò che tiene ADI Manifesto sopra il
> traguardo. Il confronto onesto è con l'alternativa, non col punto di partenza.

*NB: il 19,45 di partenza e il traguardo 14,3 devono venire dallo stesso indicatore,
altrimenti il confronto non è omogeneo. Gli studenti sono **esogeni**: il modello non li
simula, li porta dietro come popolazione di riferimento.*

---

## 11. La dinamica: come ci si arriva, e l'onda

Il modello **simula il percorso anno per anno** con uno stock-flow per coorte di età.
Tutte le leve — stabilizzazione, flussi, paghe, soglie di promozione — sono **rampate**
su `RAMP = 10` anni (la borsa di dottorato su 5, la didattica del postdoc su **20**: §1).

| anno | organico totale | densità (pop. 2026) | spesa aggiuntiva | pensionamenti |
|---|---|---|---|---|
| 2026 | 183.847 | 109,2 | — | 670 |
| 2035 | 206.058 | 137,0 | 6,4 mld | 2.659 |
| **2036** (fine rampa leve) | 205.692 | 137,3 | **6,6 mld** | 2.798 |
| 2041 | 204.515 | 140,6 | 6,4 mld | 2.659 |
| **2046** (fine rampa didattica) | 211.344 | 149,0 | 7,6 mld | 1.517 |
| 2050 | 222.837 | 158,2 | 9,3 mld | 670 |
| **2057** (picco) | **247.854** | **177,1** | **14,3 mld** | 4.734 |
| **2070** | **231.941** | **166,5** | **12,8 mld** | 4.029 |
| *2080 (regime)* | *225.540* | *164,4* | *11,5 mld* | *3.593* |

> **Perché la densità del 2035-2041 è più bassa di quanto ci si aspetti dall'organico.**
> Le teste crescono, ma il postdoc conta ancora come 0,75 FTE-ricerca invece che 1,00:
> la sua rampa dura venti anni, non dieci (§1). È un effetto di **contabilità**, non di
> reclutamento — le teste di quegli anni sono le stesse a rampa dieci — e si esaurisce
> nel 2046, dopo di che le due traiettorie coincidono.

**Tre fatti sulla forma della curva.**

1. **Le durate governano la velocità, non i soldi.** Fra l'ingresso in dottorato e
   l'ingresso in ruolo passano 13 anni, e il ruolo dura 25: lo stock si riempie con
   quella lentezza. Il 90% del gap di densità è colmato nel **2051**, 25 anni dopo
   l'inizio. Non è un piano quinquennale.
2. **La spesa sale prima della densità.** Stabilizzare e pagare costa subito; la
   capacità arriva con dieci anni di ritardo.
3. **C'è un plateau, poi una gobba.** Fra il 2035 e il 2044 la spesa resta ferma sui 6,7-7,2
   mld: l'onda dei pensionamenti della coorte di oggi (picco ~2038) restituisce
   esattamente quello che le nuove assunzioni consumano. Poi, fra il 2050 e il 2057, i
   pensionamenti crollano a 670 l'anno mentre le assunzioni corrono a ritmo di regime, e
   l'organico sale del **+9,9% sopra lo stato stazionario**. Nel 2057 la spesa tocca
   14,3 mld contro gli 11,5 di regime: **2,8 mld di gobba per una quindicina d'anni.**
   **Nel 2070 la gobba è ancora in corso di riassorbimento** (+2,8% di organico, +1,3 mld
   di spesa sopra il regime): è la ragione per cui i valori riportati in questo documento
   sono leggermente più alti di quelli di stato stazionario.

> ⚠️ **La gobba del 2057 è la gobba di oggi, riprodotta.** Una stabilizzazione
> concentrata nella rampa crea una coorte anomala che entra in ruolo tutta insieme e vi
> resta 26 anni — cioè esattamente il meccanismo che ha prodotto l'attuale campana dei
> 50-62enni. **Distribuire la stabilizzazione su più anni è l'unico modo di non
> riprodurre nel 2060 il problema che si sta risolvendo oggi.**

> **C'è anche un gradino minore, nel 2036, e non è demografico.** Nel 2036 tutte le leve
> arrivano a regime **insieme** — `P2`, flusso PhD, paghe `W`, α del postdoc — e la spesa
> fa uno scalino prima che l'onda dei pensionamenti la riporti giù: senza correzioni
> sarebbe 7,53 mld contro i 6,80 del 2041, cioè **0,73 mld di ampiezza**. È un artefatto
> della sincronia delle rampe, non un fatto del sistema, e per questo il modello gli
> dedica una **seconda finestra di blocco degli scatti** (2033-2034, due anni contro i
> cinque della finestra principale): il picco scende a **7,19 mld** e l'ampiezza a
> **0,54** (−26%). Lo stato stazionario non si muove di un euro.
>
> ⚠️ **Il blocco morde in ritardo, ed è ciò che ne determina la collocazione.** Il costo
> per testa dell'anno *Y* dipende dall'anzianità maturata *fino a* Y: bloccare gli scatti
> **nel 2036** non abbassa la spesa del 2036, la abbassa dal 2038 — peggiorando il gradino
> invece di smussarlo (provato: da 0,73 a 0,83). In più le scale stipendiali sono a
> gradini triennali, quindi mezzo anno di anzianità persa spesso non fa cambiare classe a
> nessuno e non si vede affatto. Per abbassare il picco del 2036 la finestra deve aprirsi
> nel **2033** — lo stesso motivo per cui la finestra grande si apre nel 2045 per una
> gobba che sta nel 2057.

**Le due densità, e perché vanno tenute separate.** La popolazione italiana scende del
13,8% fra il 2026 e il 2080 (proiezione **SSP2**, Wittgenstein Centre / IIASA WIC2023 —
[WCDE](https://iiasa.ac.at/models-tools-data/wcde)), quindi lo **stesso organico vale una
densità più alta** col passare del tempo.

| colonna | denominatore | a cosa serve |
|---|---|---|
| `densita` | popolazione dell'anno (SSP2) | la grandezza confrontabile con gli altri paesi in quell'anno |
| `densita_pop2026` | popolazione 2026 fissa | isola l'effetto organico da quello demografico; **è su questa che sono definiti i target** |

Per questo lo scenario, che ha come densità universitaria di riferimento **164**, al 2070
sta a **166,5 a demografia ferma** e a **187,1** con la popolazione proiettata. Il
confronto col riferimento usa sempre `densita_pop2026`.

---

## 12. Il retroflusso fiscale: quanto della spesa torna indietro

L'**86%** della spesa del piano è monte stipendi. Uno stipendio pubblico è in parte una
**partita di giro**: lo Stato lo eroga e se ne riprende subito una quota. Il modulo
`irpef.py` la quantifica.

**Da dove si parte.** I `COSTO_*` del modello sono **costo lordo ente**, non buste paga:
contengono già contributi (32,70%) e IRAP (8,50%). La retribuzione lorda è il costo
diviso **1,412**. Dividere i costi del modello per quel fattore restituisce, uno per uno,
i valori di CCNL — il che rende la scomposizione anche un **controllo dei costi
unitari**, non solo un passaggio di calcolo.

**Tre regole obbligate.**

1. **Pro capite, mai sulle masse.** L'IRPEF è progressiva e convessa: applicare gli
   scaglioni al monte stipendi sottostima il gettito. I professori entrano **una voce
   per classe d'età** — dentro gli associati si va da 56.786 a oltre 100.000 di lordo, e
   su un'imposta progressiva non è un dettaglio.
2. **L'esenzione è una categoria, non un'aliquota.** Borse di dottorato (art. 4
   L. 476/1984), assegni di ricerca (art. 4 c.3 L. 210/1998) **e borse e incarichi di
   ricerca post-lauream** (art. 6 c.6 L. 398/1989) sono **esenti IRPEF**: vanno separati
   per teste.
3. **Le attrezzature restano fuori.** Sono acquisti, non stipendi.

**I numeri dello scenario** (fisco vigente tenuto fermo per 55 anni):

| | 2026 | 2070 |
|---|---|---|
| Monte stipendi lordo ente | 16,23 mld | **28,52 mld** |
| **IRPEF erariale** | **2,40 mld** | **4,78 mld** |
| Aliquota IRPEF media effettiva | 22,7% | **25,8%** |
| IRPEF / monte stipendi | 14,8% | 16,7% |
| + addizionali, contributi, IRAP | 51,0% | **53,2%** |

**Il costo del piano al netto del rientro**, che è la lettura di policy:

| | 2070, mld/**anno** | cumulato 2026-2070, mld |
|---|---|---|
| Maggior costo lordo rispetto al 2026 | **12,8** | **417** |
| al netto della sola IRPEF | 10,5 | 342 (18% rientra) |
| al netto di tutti i prelievi | 6,0 | 197 (53%) |

> ⚠️ **Le due colonne non sono la stessa grandezza.** Il piano vale ~13 mld *all'anno* nel
> 2070; i 417 mld sono la **somma di 45 annualità** in EUR2026 costanti, non
> attualizzata, e crescono da zero lungo la transizione. Confrontarli con una cifra
> annua non ha senso.

> **L'incarico di ricerca non muove quasi più niente, ed è il risultato della finestra a
> 4 anni.** Con la finestra a 6 anni copriva il 32,5% degli anni-persona e valeva un
> punto di retroflusso; a 4 anni ne copre il **5,3%**, il postdoc medio costa 44.205
> invece di 40.125 — cioè quasi il contratto pieno da 45.000 — e la leva è di fatto
> spenta. L'aritmetica dell'esenzione non cambia (un euro esente è un euro che non
> torna): cambia la sua base, che ora è quasi nulla.

**Due risultati non ovvi.**

- Il ritorno fiscale cresce **più che proporzionalmente** alla spesa: l'aliquota media
  effettiva sale dal 22,7% al 25,8%, perché il piano non aggiunge solo teste — le sposta
  dal precariato al ruolo e alza le paghe, e l'IRPEF è progressiva.
- **Le borse di dottorato non tornano.** Nel 2070 sono ~**1,5 mld/anno** completamente
  esenti: alzare una borsa costa allo Stato quasi il doppio, in termini netti, di alzare
  uno stipendio dello stesso importo lordo. Gli **incarichi di ricerca**, dopo la
  riduzione della finestra, non sono più la seconda voce esente che erano: nel 2026 sono
  **2.509 teste** contro le 15.386 di prima.

**Le due figure del postdoc, viste dal fisco.** Un incarico di ricerca a 30.000 di lordo
amministrazione **non paga IRPEF**; un contratto di ricerca a 45.000 ne paga **3.995**.
La quota a incarico è quindi una leva **di spesa prima ancora che di fisco**: sposta
15.000 EUR di costo per testa e 3.995 di gettito, nella stessa direzione.

**La sensitività.** L'incertezza sta nell'età alla laurea magistrale (§2). Sul gettito
l'effetto è ormai **nullo a tre cifre significative**, e non perché l'incertezza sia
piccola — è anzi più ampia che a 6 anni — ma perché il vincolo di 0,5 anni riduce la
quota di stock a un ventesimo: qualunque ipotesi sull'età si scelga, la platea esente
non arriva al 6%.

| quota **persone** | quota **stock** | ipotesi sull'età alla magistrale | costo medio postdoc | IRPEF 2026 | cum. IRPEF |
|---|---|---|---|---|---|
| 0,445 | 0,045 | 26,5 anni | 44.332 | 2,40 mld | 230,9 mld |
| **0,530** | **0,053** | **27,2 anni — in uso** | **44.205** | **2,40 mld** | **230,8 mld** |
| 0,582 | 0,058 | 28,0 anni | 44.127 | 2,40 mld | 230,8 mld |

*(cumulati sull'orizzonte pieno 2026-2080)*

**Cosa NON è.** Non è un moltiplicatore: nessun indotto, nessuna IVA, nessun effetto di
comportamento. È il prelievo meccanico su buste paga che lo Stato sta già pagando, cioè
un **limite inferiore** del ritorno. E addizionali e IRAP vanno a Regioni e Comuni: chi
ragiona sul bilancio dello Stato in senso stretto deve guardare la sola colonna IRPEF,
tenuta separata apposta.

---

## 13. La calibrazione: cosa è misurato e cosa è residuo

L'anno base deve riprodurre i dati osservati. Tre parametri sono **ricavati per
residuo**, in quest'ordine obbligato (invertirli dà una calibrazione incoerente):

| Parametro | Valore ricavato | Cosa impone |
|---|---|---|
| `ANNI_DA_ASSOCIATO` | **9,82 anni** | riproduce la quota di ordinari MUR 2023 (0,390) |
| `LAMBDA_HE` (quota-lavoro dell'HERD) | **0,879** | riproduce HERD 0,36% ISTAT → attrezzature = **12% dell'HERD** |
| `SUPPORTO` (residuo non nominato) | **+1,8%** | chiude quel che resta sul costo-ricerca |
| `OVH_EPR_SUPP` / `OVH_EPR_ATTR` | **460 / 1.381 mln** | riproducono GOVERD 0,21% |

> **`LAMBDA_HE` non è più un'assunzione.** Col TA esplicito il costo del personale di
> ricerca è tutto misurato, quindi la ripartizione lavoro/attrezzature dell'HERD
> osservato **diventa un residuo**. Il vecchio 0,70 non sta in piedi coi TA veri:
> lascerebbe 237 mln per 31.357 FTE di tecnici, cioè 7.568 EUR a testa-anno. Il valore
> ricavato — 0,879 — dice che l'università italiana spende in strumenti il 12%
> dell'HERD. Se uscisse sopra 0,90 varrebbe la pena sospettare i costi unitari, non
> accettarlo.

> ⚠️ **La calibrazione è un sistema chiuso, e il meccanismo va nei due sensi.** Quando
> l'incarico di ricerca fu introdotto a finestra piena, il postdoc costava meno (40.125) e
> il risparmio **non liberava spazio per assumere**: con l'HERD 2026 ancorato allo 0,36%,
> la spesa che il personale non assorbiva veniva riattribuita ai residui, `LAMBDA_HE`
> scendeva a 0,861 e `SUPPORTO` saliva a 2,1% — il risparmio diventava strumenti.
> Accorciando la finestra a 4 anni il postdoc torna a costare quasi il pieno (44.205) e i
> residui si riassorbono nell'altro senso: `LAMBDA_HE` risale a **0,879** e `SUPPORTO`
> torna a **+1,8%**. **L'ancora HERD non si muove**: a cambiare è sempre e solo la
> ripartizione fra personale, strumenti e residuo.

> **Il `SUPPORTO` resta piccolo**: da +12% (quando assorbiva tutto il TA) a **+1,8%**.
> È la misura di quanto il TA esplicito abbia spiegato di ciò che prima era un residuo
> senza nome.

**Verifiche indipendenti** (nessuna delle due è usata per calibrare, quindi sono
informative):

| Test | Modello | Osservato | Scarto |
|---|---|---|---|
| FTE ricercatori universitari 2026 | 64.202 | 64.202 (Eurostat HES 2023) | **0,0%** *(imposto)* |
| RTT 2026 | 4.734 | 6.915 (RTD-B + L.79/2022, MUR 2023) | **−31,5%** |
| Dottorandi 2026 | 47.000 | 47.000 (iscritti 2024) | 0% |
| HERD 2026 | 0,36% | 0,36% (ISTAT) | **0,00 pp** *(imposto)* |
| GOVERD 2026 | 0,21% | 0,21% | 0,00 pp *(imposto)* |

Lo scarto sugli RTT è **il prezzo dichiarato** della chiusura sui precari (§2). È l'unica
verifica veramente libera che il modello ha, e non passa: va tenuta in vista.

---

## 14. Le leve accese e quelle spente

`config.py` contiene diverse leve che lo scenario può usare o no. Nella configurazione
corrente:

| Leva | Stato | Effetto |
|---|---|---|
| **Pavimento sulla stabilizzazione** (`P2_MIN = 0,50`) | **accesa** | piano straordinario, ~15.000 stabilizzati nel primo triennio |
| **Pavimento sul GOVERD** (`GOVERD_MIN`) | **acceso** | 3.261 assunzioni straordinarie in ruolo fra 2040 e 2049, per non far scendere la spesa del ramo enti sotto lo 0,23% una volta raggiunto |
| **Tetto TA** (`TA_CAP = 90.000`) | **acceso** | morde fra il 2055 e il 2062 |
| **Blocco degli scatti, finestra 1** (`SCATTI_BLOCCO_*`) | **acceso** ⚠️ | 5 anni dal 2045 al 2049, recupero 0%: **−0,024 pp di HERD e −0,95 mld di budget nel 2051**; stato stazionario invariato |
| **Blocco degli scatti, finestra 2** (`SCATTI_BLOCCO2_*`) | **acceso** ⚠️ | 2 anni dal 2033 al 2034, recupero 0%: **−0,007 pp di HERD e −0,34 mld nel 2036**; smussa il gradino di fine rampa (§11) |
| **Prepensionamento** (`PREPENS_ANNI = 0`) | **spenta** | — |
| **Inviluppo delle attrezzature** (`ATTREZZ_INVILUPPO = False`) | **spenta** | — |

> ⚠️ **Il blocco degli scatti è acceso di default, e probabilmente non dovrebbe.** È una
> leva di *austerità* — sette anni complessivi di anzianità non maturata, senza recupero —
> dentro uno scenario che serve a dimensionare un piano di espansione. Costa ~0,95 mld nel
> 2051 e ~0,34 nel 2036 e non cambia lo stato stazionario, quindi non falsifica i
> risultati di regime, ma **abbassa la traiettoria negli anni centrali**. Si spegne con
> `--scatti-blocco-anni 0 --scatti-blocco2-anni 0`.
>
> **Le due finestre hanno bersagli diversi**, e vanno valutate separatamente: la prima
> lavora sulla gobba demografica del 2057, la seconda sul gradino di fine rampa del 2036,
> che è un artefatto della sincronia delle rampe e non un fatto demografico. Chi ritiene
> accettabile smussare il secondo ma non la prima può tenere solo la finestra piccola.

### Le due leve spente, in breve

**Prepensionamento.** Una finestra gaussiana di uscite anticipate collocata **prima**
dell'anno di picco dell'organico, per smorzare la gobba del §11 senza toccare lo stato
stazionario. Nelle prove misurate portava la gobba da +13,5% a +5,1% senza scavare
buchi, a patto di centrare la finestra sul **picco meno gli anni di anticipo**: chi esce
nell'anno *t* è assente da *t* a *t+n*, quindi una finestra centrata sul picco fa cadere
l'assenza *dopo* la gobba e produce un buco seguito da un rimbalzo. Si riaccende con
`--prepens-anni 4 --prepens-ades 0.5 --prepens-sigma 4`. ⚠️ **Non è gratis, e sul solo
bilancio della ricerca sembra un risparmio**: chi esce smette di essere personale di
R&S, quindi HERD e monte stipendi *scendono*, ma lo Stato gli paga la pensione per gli
anni non prestati. Le colonne `prepens_*` rendono visibile quel costo, che resta fuori da
HERD/GOVERD perché un pensionato non è personale di ricerca.

**Inviluppo delle attrezzature.** Tratta le discese di spesa dovute alla demografia come
**spesa liberata** e la riversa sulle attrezzature — l'unica voce senza un organico
dietro — per non far oscillare il bilancio della ricerca di due miliardi. Si riaccende
con `ATTREZZ_INVILUPPO = True`. ⚠️ **Con l'inviluppo acceso le righe di obiettivo nei
grafici diventano soglie, non traguardi**: dal 2040 in poi la spesa non è più
dimensionata sull'obiettivo ma sulla regola di non far oscillare il bilancio, quindi
HERD e GOVERD lo superano *per costruzione*. E il supplemento **non paga IRPEF** (le
attrezzature non sono stipendi), quindi è la parte più cara del piano per ogni euro
speso.

---

## 15. Limiti

- **α docente = 0,50 è il parametro più fragile** dell'intero modello, e viene da
  un'indagine ISTAT ferma al **2004-05**. Tutta la densità dipende linearmente da lui.
- **Lo scarto sugli RTT (−31,5%)** è l'unica verifica libera della calibrazione, e non
  passa. È il prezzo della chiusura sui precari (§2), e **non è toccato** dalla rampa su
  α del postdoc, che nell'anno base vale ancora 0,75.
- **`TA_ELAST = 2,2` è una decisione, non una stima**, e porta la quota di TA in
  direzione opposta alla media europea (§9).
- **Il BERD non è modellato**: il 3% del PIL è per due terzi una scommessa
  sull'industria, su cui nessuna leva qui discussa agisce.
- **Compartimento singolo per i precari**: a permanenze molto lunghe (>9-10 anni) perde
  realismo, perché nessuno resta davvero con attrito costante.
- **La quota a incarico di ricerca è media, non per coorte**: il modello tiene il 5,3%
  dei postdoc su incarico per tutto il periodo, invece del 53% che ci sta per 0,5 anni e
  poi passa a contratto. Stessi anni-persona e stesse masse; profilo individuale diverso.
- **Marginale ≈ medio e mix costante**: è una stima di primo ordine. Rendimenti
  decrescenti e colli di bottiglia (spazi, strumenti, tutor) non sono modellati.
- **Gli studenti sono esogeni**: il rapporto studenti/docente è un indicatore portato
  dietro, non una domanda di didattica simulata.
- **L'FFO come voce di bilancio non esiste nel modello**: i costi indicati sono maggiori
  oneri per il personale di ricerca, non una posta di bilancio.
- **Niente eterogeneità**: nessuna differenza fra atenei, aree disciplinari, regioni.
- **Da verificare prima della pubblicazione**: `REDDITO_PHD_EU = 91.343` sulla dashboard
  ReICO (l'intero ramo paghe poggia lì), `COSTO_TA = 35.000` sulle tabelle retributive
  CCNL, e le indennità di ente e valorizzazione professionale escluse dai costi EPR
  (quindi sottostimati).

---

## 16. Come si esegue

Richiede `python3` con `numpy`, `pandas`, `matplotlib` (`pip install -r
requirements.txt`).

```
python3 piano_transizione.py
```

Produce a schermo: stato iniziale e calibrazione, tabella di stabilizzazione EPR,
frontiera iso-HERD, blocco scatti, retroflusso fiscale, traiettorie dei tre scenari e
tabelle complete per FLC ed ADI_Manifesto_ric. In `output/`: `transizione_*.csv` (una riga per
anno, 76 colonne), i grafici di confronto e **quattro grafici del solo scenario
ADI_Manifesto_ric** (`ADI_Manifesto_ric_trend.png`, `_ffo.png`, `_organico.png`, `_spesa.png`).

**In alternativa, la webapp**, che calcola esattamente le stesse cose con grafici
interattivi invece dei PNG e un pannello di parametri invece dei flag:

```
streamlit run app.py
```

Le due strade passano entrambe da `scenario.esegui()`, quindi non possono divergere: la
CLI resta l'unica che produce il report testuale completo e le tabelle di diagnostica.

**Le opzioni che spostano di più il risultato:**

```
--uplift-ppp 1.6485      parità coi 5 paesi che pagano meglio invece che con la media UE
--quota-ric-uni 0        via il compromesso: torna al modello tutto-cattedre
--quota-incarico 0       tutti i postdoc su contratto di ricerca pieno (45.000, tassato)
--precari-anni 3         precariato corto -> regime a cattedre (quota-docente 71%)
--rtt-anni 3             tenure track rapida (ex RTD-B) invece dei 5 anni L.79/2022
--p2-tgt 1.0             nessun filtro a fine postdoc: tutta la selezione sul dottorato
--ta-elast 0.4           TA come overhead invece che come obiettivo
--scatti-blocco-anni 0   spegne il blocco grande sulla gobba del 2057 (acceso di default)
--scatti-blocco2-anni 0  spegne il blocco piccolo sul gradino del 2036 (acceso di default)
--ramp-alpha-prec 0      la didattica del postdoc si spegne in 10 anni invece di 20:
                         riporta la gobba studenti/docente a 21,20 nel 2036 (§10)
--precari-oggi 35000     stima PNRR invece della chiusura, lascia il gap in vista
```

---

## Appendice — file del progetto

| File | Contenuto |
|---|---|
| `piano_transizione.py` | **Entry point da riga di comando**: CLI, report testuale, CSV e PNG |
| `scenario.py` | **La giuntura**: da parametri a DataFrame. Applica i valori a `config`, calibra nell'ordine obbligato e simula. Condivisa da CLI e webapp, così le due non possono divergere |
| `app.py` | **Webapp** Streamlit: pannello dei parametri, KPI e grafici interattivi |
| `config.py` | **Tutti i numeri di input**, con la fonte accanto |
| `regime.py` | Composizione di **stato stazionario**, scale stipendiali, frontiere iso-HERD e iso-GOVERD (tutto in forma chiusa) |
| `motore.py` | **Motore stock-flow**: lo stato per coorte e la sua evoluzione anno per anno. L'unico punto in cui il tempo avanza |
| `calibrazione.py` | Residui ricavati dai dati osservati e diagnostica |
| `irpef.py` | **Retroflusso fiscale**: dal costo lordo ente alla busta paga e all'IRPEF, pro capite |
| `tabelle.py` | Righe e impaginazione delle tabelle di scenario |
| `grafici.py` | Tutti i PNG (CLI) |
| `grafici_web.py` | Le figure Plotly interattive (webapp) |
| `spesa_pubblica_rs_eu.py` | Serie storiche 2000-2024 di HERD+GOVERD per i grandi paesi UE (Eurostat SDG_09_10) |
| `confronto_prepensionamento.py` | Confronto sistematico delle configurazioni della leva di prepensionamento |
| `input/` | Serie USTAT per età e qualifica, assunti e cessati |
| `doc/` | CCNL 2022-2024, dataset Eurostat, sintesi divulgativa |
| `output/` | CSV e PNG prodotti dalle esecuzioni |
