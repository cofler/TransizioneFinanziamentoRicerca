# Lo scenario ERA PPP — modello, ipotesi, risultati

Documento di riferimento del modello `piano_transizione.py`, **centrato sullo
scenario `ERA_PPP_ric`** (nei grafici: *ERA PPP + ric.univ.*), che è la
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

## 0. Che cos'è lo scenario ERA PPP

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
| **Densità ricercatori pubblici** univ.+enti, **popolazione SSP2** | 156,3 | **239,7** | **221** (media semplice UE27) |
| Densità FTE università (pop. 2026 fissa) | 109,2 | **160,8** | *risultato*, non obiettivo |
| Densità FTE università (popolazione SSP2) | 109,2 | 180,7 | — |
| Densità personale R&S totale con TA (SSP2) | 239,5 | **404,0** | — |
| **HERD (% PIL)** | 0,360 | **0,696** | 0,68 |
| **GOVERD (% PIL)** | 0,209 | **0,256** | 0,23 |
| **R&S pubblica (% PIL)** | 0,568 | **0,952** | 0,91 |
| GERD, con BERD per ipotesi (% PIL) | 1,373 | 3,000 | 3,00 |
| Moltiplicatore paghe W | 1,00 | **1,16** | 1,16 |
| Borsa di dottorato (EUR/mese netti) | 1.195 | **1.656** | 1.656 |
| Componente precaria (% postdoc su personale di ricerca) | 39,0 | **17,7** | — |
| Personale di ruolo università (teste) | 47.877 | **98.545** | — |
| di cui a profilo ricercatore | 4.831 | **32.848** (1/3) | 1/3 |
| Enti pubblici di ricerca, ruolo (teste) | 30.896 | 38.567 | — |
| Personale TA, univ.+enti (FTE) | 48.894 | **85.950** | — |
| Docenti in FTE didattici | 35.749 | **53.408** | — |
| Studenti per docente (FTE) | 19,45 | **13,02** | 14,3 (media UE) |
| Costo aggiuntivo per lo Stato (mld/anno) | — | **+13,3** | — |
| Budget pubblico totale (% PIL) | 0,843 | 1,451 | — |

> **HERD e GOVERD al 2070 stanno sopra il target** (0,696 e 0,256 contro 0,68 e 0,23)
> perché il sistema sta ancora rientrando dal picco del 2057. A stato stazionario
> pieno — 2080 — sono 0,685 e 0,230, cioè esattamente a bersaglio: l'obiettivo di spesa
> è **centrato**, ma dieci anni dopo la fine dei grafici.

> **Calo demografico** L'Italia perde
> il 13,8% di popolazione fra il 2026 e il 2080 (SSP2, §11): lo stesso organico serve
> meno persone, quindi vale una densità più alta.

**Tempi.** Il 90% del divario di densità FTE è colmato entro il **2051** (25 anni). La
spesa aggiuntiva tocca il massimo di **15,0 mld** nel **2057**, è a **13,3 nel 2070** e
rientra a 12,0 a regime: è un'onda demografica, non una scelta (§11).

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
| Postdoc / assegni | 0,75 | 0,25 |
| Dottorandi | 0,75 | escluso |
| Ricercatori degli enti (EPR) | 0,75 | — |
| Personale TA | 0,563 (misurato) | — |

`FTE = Σ (teste_i × α_i)`, e la densità è `FTE / (popolazione/100.000)`.

**I dottorandi NON contano negli FTE** (`PHD_IN_FTE = False`), ma il loro **costo entra
comunque** in HERD e nel budget: la borsa è spesa di R&S comunque la si conti.

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

Chi inizia il postdoc **entro 6 anni dalla laurea magistrale** sta su un **incarico di
ricerca** — lordo amministrazione più basso ed **esente IRPEF** (art. 6 c.6
L. 398/1989) — gli altri su un **contratto di ricerca** pieno e tassato:

| figura | lordo amministrazione | IRPEF | quota delle **persone** | quota dello **stock** |
|---|---|---|---|---|
| **incarico di ricerca** (entro 6 anni dalla magistrale) | **30.000** | **esente** | **65%** | **32,5%** |
| contratto di ricerca | 45.000 | tassato | 35% | 67,5% |
| **costo medio del postdoc** | **40.125** | | | |

> ⚠️ **Le due quote non sono la stessa cosa, e confonderle è l'errore facile.** Il 65% è
> la quota di **persone** che hanno l'opzione; ma **la finestra dei 6 anni si chiude
> durante il postdoc** — chi entra a 32 anni la esaurisce a 33 — quindi l'incarico copre
> solo **2,5 dei 5 anni** di permanenza. Sullo **stock**, che è ciò che il modello prezza
> e tassa, la quota vale `0,65 × 2,5/5 = 0,325`. È la quota di **anni-persona**, non di
> teste. Si muove con `--anni-incarico`, e a `--precari-anni` diverso si riscala da sola.

**Come è stimato il 65%.** Non è osservato: si incrociano due distribuzioni. Il postdoc
inizia alla fine del dottorato, quindi "entro 6 anni dalla magistrale" equivale a
"dottorato conseguito prima dei **33,2** anni" (27,2 + 6).

| età al conseguimento del dottorato | quota |
|---|---|
| meno di 29 anni | 22,2% |
| 29-30 anni | 29,7% |
| 31-35 anni | 31,3% |
| 36 anni e oltre | 16,8% |
| **età media** | **32,6** |

*Fonte: [AlmaLaurea, Profilo dei Dottori di ricerca 2022, Report 2023](https://www.almalaurea.it/sites/default/files/2023-07/dottori_profilo_report2023.pdf), Fig. 3 p. 7 (5.007 dottori, 37 atenei). Età media alla laurea magistrale biennale 27,2 anni: AlmaLaurea, Profilo dei Laureati 2022.*

Interpolando uniformemente dentro le classi, la quota sotto i 33,2 anni è **65,7%**.

> **La stima regge a un controllo indipendente.** Rifatta per **area disciplinare** —
> dove l'età media al dottorato va dai 30,8 anni delle scienze di base ai 34,0 delle
> scienze umane — e poi ripesata sulle quote di area, dà **65,6%**. Due strade diverse
> sullo stesso dato, stesso numero: si usa **0,65**.
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
> laureati) e verosimilmente si laurea prima. La sensitività:
> **26,5 anni → 61,3% | 27,2 → 65,7% | 28,0 → 70,7%**. Si muove con `--quota-incarico`.

> **L'età di fine dottorato del modello è ora quella osservata.** `ETA_FINE_PHD` era 34
> per ipotesi, ed era **incompatibile con questa stessa stima**: a 34 anni si è già a 6,8
> anni dalla laurea magistrale, quindi nessuno sarebbe stato dentro la finestra. Ora vale
> **33** — i 32,6 osservati, arrotondati perché le classi della coorte sono annuali — e il
> divario medio dalla magistrale è **5,4 anni**, coerente con un 65% che ci sta dentro.
> Ne discendono un **ingresso in ruolo a 43 anni** invece di 44 e una **carriera di 26
> anni** invece di 25.

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
| HERD (% PIL) | 0,360 | 0,529 | 0,724 | **0,696** | *0,685* | 0,68 |
| GOVERD (% PIL) | 0,209 | 0,225 | 0,272 | **0,256** | *0,230* | 0,23 |
| R&S pubblica | 0,568 | 0,753 | 0,996 | **0,952** | *0,916* | 0,91 |
| Budget pubblico totale | 0,843 | 1,131 | 1,527 | **1,451** | *1,394* | — |

Il **GOVERD è a target dal 2030**; l'**HERD arriva a 0,68% nel 2054** e lo supera
durante la gobba demografica prima di rientrarci. Il **GERD tocca il 3% nel 2053**, ma
vedi l'avvertenza qui sotto.

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
  attrezzature. È ciò che paga davvero il pubblico, e nel 2080 vale **1,395% del PIL**
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
| Ingressi in tenure track, teste/anno | **2.489** *(6.276 nel 2026 col piano straordinario di transizione)* | **4.811** |
| Stock di RTT (teste) | 4.734 | **18.522** |
| **Componente precaria** (postdoc su personale di ricerca) | **39,0%** | **17,7%** |
| Dottori che escono dall'accademia, all'anno | 4.601 | 9.928 |
| Dottorandi (teste) | 47.000 | 51.056 |

**Il pavimento sulla stabilizzazione** (`P2_MIN = 0,50`) scavalca la rampa: modella un
**piano straordinario** che agisce subito invece di arrivare a regime in dieci anni.
Vale ~15.000 stabilizzati nel primo triennio (riprendendo la posizione ADI dall'articolo sul piano straordinario del governo https://www.dottorato.it/un-piano-niente-affatto-straordinario-analisi-delladi-sul-reclutamento-universitario-e-la-programmazione-della-legge-di-bilancio-2026/) contro gli ~8.700 della sola rampa.
Attenzione a cosa **non** fa: lo stock di postdoc è *invariante* al pavimento, perché
l'uscita totale dal compartimento vale `1/precari_anni` qualunque sia P2. Il pavimento
non svuota il precariato più in fretta — **sposta persone dalla porta d'uscita alla
tenure track**. È una redistribuzione a somma zero fra le due porte.

**Perché a regime gli ingressi in tenure track sono 4.811 e non di più.** Non è una
scelta: è il ruolo che li determina. Un organico universitario di 98.545 teste che dura
26 anni richiede 3.790 ingressi l'anno per stare in piedi (infatti lo stock di RTT,
18.522 su 5 anni di contratto, ne immette 3.704), più ~1.100 dal ramo enti.
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
| Professori ordinari | 16.788 | 16,8% | 32.980 | **22,3%** |
| Professori associati | 26.258 | 26,3% | 32.717 | **22,1%** |
| **Ricercatori di ruolo** (`ric_uni`) | 4.831 | 4,8% | **32.848** | **22,2%** |
| RTT (tenure track) | 4.734 | 4,7% | 18.522 | **12,5%** |
| Postdoc / precari | 47.340 | **47,4%** | 30.867 | **20,9%** |
| **Totale** | **99.951** | | **147.934** | |

**Il ribaltamento è questo**: si passa da un sistema in cui **quasi metà delle persone è
precaria** a uno in cui le cinque posizioni pesano **circa un quinto ciascuna**, e il
precariato è il segmento più piccolo assieme agli associati.

### Università — FTE-ricerca

| | 2026 | 2070 |
|---|---|---|
| Professori PO/PA | 33,5% | 34,8% |
| Ricercatori di ruolo | 5,6% | **26,1%** |
| RTT | 5,5% | 14,7% |
| Postdoc | **55,3%** | 24,5% |
| **FTE totali** | **64.202** | **94.526** |

In FTE il ribaltamento è ancora più netto: **il postdoc smette di essere il motore della
ricerca universitaria italiana**. Oggi produce il 55% degli FTE; a fine transizione il
25%, esattamente quanto i ricercatori di ruolo.


### Enti pubblici di ricerca

| | 2026 | 2070 |
|---|---|---|
| Ruolo (teste) | 30.896 (83,7%) | 38.567 (**93,7%**) |
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
| Professore, coorte 2026 | **110.541** |
| Professore, coorte 2070 | **122.751** |
| Ricercatore universitario, a regime | 72.040 |
| Ruolo EPR, a regime | 75.217 |
| RTT | 55.000 |
| **Postdoc università, media pesata** | **40.125** (32,5% incarico a 30.000 + 67,5% contratto a 45.000) |
| Contratto di ricerca EPR (a regime) | 45.000 |
| Dottorando (borsa + contributi) | 22.000 → 30.487 |
| TA (per testa) | 35.000 × 1,6 = 56.000 |

Il professore **rincara dell'11,0%** lungo la transizione: la soglia di promozione si
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
davvero, fra il 2055 e il 2063**, quando la gobba demografica dell'organico di ricerca
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
| TA università (FTE) | 31.357 | 56.836 | 65.198 | **63.941** |
| TA enti (FTE) | 17.537 | 19.927 | 24.802 | **22.010** |
| **TA totale (FTE)** | **48.894** | 76.763 | **90.000** | **85.950** |
| TA totale (teste) | 86.911 | 136.448 | 159.978 | **152.779** |
| Quota TA sul personale R&S | 34,7% | 39,5% | 40,2% | **40,7%** |
| TA per FTE-ricercatore | 0,53 | — | — | **0,69** |

**+76% di personale tecnico-amministrativo della ricerca**, quasi 66.000 teste in più.
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
nell'indicatore.

| | 2026 | 2050 | 2070 |
|---|---|---|---|
| **Docenti in FTE didattici** | **35.749** | 50.148 | **53.408** |
| Studenti per docente (FTE), studenti fermi | 19,45 | 13,87 | **13,02** |
| idem, studenti che seguono la demografia | 19,45 | 13,20 | 11,59 |

**+49% di capacità didattica**, e il rapporto studenti/docente scende sotto la media
europea di 14,3 nel **2049**.

> **In FTE didattici il rapporto si muove molto meno che in teste**, ed è l'effetto che
> conta. La transizione sposta persone dal precariato (peso didattico 0,25) al ruolo
> (peso 0,50): **ogni stabilizzazione vale il doppio in capacità didattica** di quanto
> valga in teste. È invisibile a chi conta le cattedre.

> ⚠️ **Qui il compromesso si paga, ed è giusto dirlo.** Lo scenario ERA — tutto cattedre,
> paghe ferme — arriva a **10,37** studenti per docente contro i **13,02** di ERA PPP,
> perché un ricercatore a α 0,75 insegna metà di un professore. **Convertire un terzo
> del ruolo a profilo ricercatore compra FTE di ricerca e costa FTE di didattica.** Il
> saldo resta ampiamente positivo rispetto a oggi (19,45 → 13,02) e sotto la media
> europea, ma il confronto onesto è con l'alternativa, non con il punto di partenza.

*NB: il 19,45 di partenza e il traguardo 14,3 devono venire dallo stesso indicatore,
altrimenti il confronto non è omogeneo. Gli studenti sono **esogeni**: il modello non li
simula, li porta dietro come popolazione di riferimento.*

---

## 11. La dinamica: come ci si arriva, e l'onda

Il modello **simula il percorso anno per anno** con uno stock-flow per coorte di età.
Tutte le leve — stabilizzazione, flussi, paghe, soglie di promozione — sono **rampate**
su `RAMP = 10` anni (la borsa di dottorato su 5).

| anno | organico totale | densità (pop. 2026) | spesa aggiuntiva | pensionamenti |
|---|---|---|---|---|
| 2026 | 183.847 | 109,2 | — | 670 |
| 2035 | 208.237 | 130,5 | 6,4 mld | 2.658 |
| 2041 | 208.370 | 132,8 | 6,3 mld | 2.658 |
| 2050 | 228.299 | 149,5 | 9,2 mld | 670 |
| **2057** | **254.468** | **169,8** | **15,0 mld** | 4.734 |
| 2065 | 244.516 | 164,0 | 14,1 mld | 4.101 |
| **2070** | **240.162** | **160,8** | **13,3 mld** | 4.155 |
| *2080 (regime)* | *233.905* | *158,8* | *12,0 mld* | *3.752* |

**Tre fatti sulla forma della curva.**

1. **Le durate governano la velocità, non i soldi.** Fra l'ingresso in dottorato e
   l'ingresso in ruolo passano 13 anni, e il ruolo dura 25: lo stock si riempie con
   quella lentezza. Il 90% del gap di densità è colmato nel **2051**, 25 anni dopo
   l'inizio. Non è un piano quinquennale.
2. **La spesa sale prima della densità.** Stabilizzare e pagare costa subito; la
   capacità arriva con dieci anni di ritardo.
3. **C'è un plateau, poi una gobba.** Fra il 2035 e il 2044 la spesa resta ferma sui 6,3
   mld: l'onda dei pensionamenti della coorte di oggi (picco ~2038) restituisce
   esattamente quello che le nuove assunzioni consumano. Poi, fra il 2050 e il 2057, i
   pensionamenti crollano a 670 l'anno mentre le assunzioni corrono a ritmo di regime, e
   l'organico sale del **+8,8% sopra lo stato stazionario**. Nel 2057 la spesa tocca
   15,0 mld contro i 12,0 di regime: **3,0 mld di gobba per una quindicina d'anni.**
   **Nel 2070 la gobba è ancora in corso di riassorbimento** (+2,7% di organico, +1,3 mld
   di spesa sopra il regime): è la ragione per cui i valori riportati in questo documento
   sono leggermente più alti di quelli di stato stazionario.

> ⚠️ **La gobba del 2057 è la gobba di oggi, riprodotta.** Una stabilizzazione
> concentrata nella rampa crea una coorte anomala che entra in ruolo tutta insieme e vi
> resta 26 anni — cioè esattamente il meccanismo che ha prodotto l'attuale campana dei
> 50-62enni. **Distribuire la stabilizzazione su più anni è l'unico modo di non
> riprodurre nel 2060 il problema che si sta risolvendo oggi.**

**Le due densità, e perché vanno tenute separate.** La popolazione italiana scende del
13,8% fra il 2026 e il 2080 (proiezione **SSP2**, Wittgenstein Centre / IIASA WIC2023 —
[WCDE](https://iiasa.ac.at/models-tools-data/wcde)), quindi lo **stesso organico vale una
densità più alta** col passare del tempo.

| colonna | denominatore | a cosa serve |
|---|---|---|
| `densita` | popolazione dell'anno (SSP2) | la grandezza confrontabile con gli altri paesi in quell'anno |
| `densita_pop2026` | popolazione 2026 fissa | isola l'effetto organico da quello demografico; **è su questa che sono definiti i target** |

Per questo lo scenario, che ha come densità universitaria di riferimento **158**, al 2070
sta a **160,8 a demografia ferma** e a **180,7** con la popolazione proiettata. Il
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
| Monte stipendi lordo ente | 16,05 mld | **28,71 mld** |
| **IRPEF erariale** | **2,35 mld** | **4,80 mld** |
| Aliquota IRPEF media effettiva | 22,4% | **25,7%** |
| IRPEF / monte stipendi | 14,6% | 16,7% |
| + addizionali, contributi, IRAP | 49,6% | **53,1%** |

**Il costo del piano al netto del rientro**, che è la lettura di policy:

| | 2070, mld/**anno** | cumulato 2026-2070, mld |
|---|---|---|
| Maggior costo lordo rispetto al 2026 | **13,3** | **419** |
| al netto della sola IRPEF | 10,9 | 344 (18% rientra) |
| al netto di tutti i prelievi | 6,3 | 198 (53%) |

> ⚠️ **Le due colonne non sono la stessa grandezza.** Il piano vale ~13 mld *all'anno* nel
> 2070; i 419 mld sono la **somma di 45 annualità** in EUR2026 costanti, non
> attualizzata, e crescono da zero lungo la transizione. Confrontarli con una cifra
> annua non ha senso.

> **L'incarico di ricerca abbassa il retroflusso, non solo il costo.** Rispetto a un
> postdoc tutto su contratto di ricerca, il piano costa meno (40.125 invece di 45.000 per
> testa) ma ne rientra anche meno: la quota che rientra come IRPEF scende dal 19% al
> **18%**, e quella complessiva dal 55% al **53%**. È l'aritmetica dell'esenzione — un
> euro esente è un euro che non torna — e va messa accanto al risparmio, non al posto suo.

**Due risultati non ovvi.**

- Il ritorno fiscale cresce **più che proporzionalmente** alla spesa: l'aliquota media
  effettiva sale dal 22,4% al 25,7%, perché il piano non aggiunge solo teste — le sposta
  dal precariato al ruolo e alza le paghe, e l'IRPEF è progressiva.
- **Le borse di dottorato non tornano.** Nel 2070 sono **1,56 mld/anno** completamente
  esenti: alzare una borsa costa allo Stato quasi il doppio, in termini netti, di alzare
  uno stipendio dello stesso importo lordo — e lo stesso vale ora per gli **incarichi di
  ricerca**, che aggiungono altri **0,35 mld/anno** di massa esente (10.032 teste).

**Le due figure del postdoc, viste dal fisco.** Un incarico di ricerca a 30.000 di lordo
amministrazione **non paga IRPEF**; un contratto di ricerca a 45.000 ne paga **3.995**.
La quota a incarico è quindi una leva **di spesa prima ancora che di fisco**: sposta
15.000 EUR di costo per testa e 3.995 di gettito, nella stessa direzione.

**La sensitività.** L'incertezza sta nell'età alla laurea magistrale (§2), e l'effetto è
modesto — sia perché i postdoc pagano comunque poca IRPEF, sia perché il vincolo dei
2,5 anni **dimezza già** l'ampiezza della forchetta:

| quota **persone** | quota **stock** | ipotesi sull'età alla magistrale | costo medio postdoc | IRPEF 2026 | cum. IRPEF |
|---|---|---|---|---|---|
| 0,613 | 0,306 | 26,5 anni | 40.402 | 2,35 mld | 228,6 mld |
| **0,650** | **0,325** | **27,2 anni — in uso** | **40.125** | **2,35 mld** | **228,4 mld** |
| 0,707 | 0,353 | 28,0 anni | 39.698 | 2,34 mld | 228,0 mld |

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
| `LAMBDA_HE` (quota-lavoro dell'HERD) | **0,861** | riproduce HERD 0,36% ISTAT → attrezzature = **14% dell'HERD** |
| `SUPPORTO` (residuo non nominato) | **+2,1%** | chiude quel che resta sul costo-ricerca |
| `OVH_EPR_SUPP` / `OVH_EPR_ATTR` | **460 / 1.381 mln** | riproducono GOVERD 0,21% |

> **`LAMBDA_HE` non è più un'assunzione.** Col TA esplicito il costo del personale di
> ricerca è tutto misurato, quindi la ripartizione lavoro/attrezzature dell'HERD
> osservato **diventa un residuo**. Il vecchio 0,70 non sta in piedi coi TA veri:
> lascerebbe 237 mln per 31.357 FTE di tecnici, cioè 7.568 EUR a testa-anno. Il valore
> ricavato — 0,861 — dice che l'università italiana spende in strumenti il 14%
> dell'HERD. Se uscisse sopra 0,90 varrebbe la pena sospettare i costi unitari, non
> accettarlo.

> ⚠️ **La calibrazione è un sistema chiuso, e questo ha una conseguenza controintuitiva.**
> Introdurre l'incarico di ricerca ha reso il postdoc più economico (da 45.000 a 40.125),
> ma **non ha liberato spazio per assumere di più**: siccome l'HERD del 2026 è un'ancora
> fissa allo 0,36%, la spesa che il personale non assorbe più viene **riattribuita ai
> residui** — `LAMBDA_HE` scende da 0,880 a 0,861 (attrezzature dal 12% al 14% dell'HERD)
> e `SUPPORTO` sale da 1,8% a 2,1%. Il risparmio sul postdoc non diventa personale in
> più: diventa strumenti. Che la densità di riferimento risulti comunque **158** invece
> di 160 dipende dall'altro cambiamento — la carriera di ruolo passata da 25 a 26 anni,
> che rende ogni ingresso più "costoso" in anni-persona di ruolo.

> **Il `SUPPORTO` resta piccolo**: da +12% (quando assorbiva tutto il TA) a **+2,1%**.
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
| **Blocco degli scatti** (`SCATTI_BLOCCO_*`) | **acceso** ⚠️ | 5 anni dal 2045 al 2049, recupero 0%: **−0,024 pp di HERD e −0,95 mld di budget nel 2055**; stato stazionario invariato |
| **Prepensionamento** (`PREPENS_ANNI = 0`) | **spenta** | — |
| **Inviluppo delle attrezzature** (`ATTREZZ_INVILUPPO = False`) | **spenta** | — |

> ⚠️ **Il blocco degli scatti è acceso di default, e probabilmente non dovrebbe.** È una
> leva di *austerità* — cinque anni di anzianità non maturata, senza recupero — dentro
> uno scenario che serve a dimensionare un piano di espansione. Costa ~0,95 mld nel 2055 e
> non cambia lo stato stazionario, quindi non falsifica i risultati di regime, ma
> **abbassa la traiettoria negli anni centrali**. Si spegne con
> `--scatti-blocco-anni 0`. *(Il testo di aiuto della CLI dice "default 5 = spento": è
> sbagliato, `_blocco_on()` accende la leva per qualunque valore ≥ 1.)*

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
  passa. È il prezzo della chiusura sui precari.
- **`TA_ELAST = 2,2` è una decisione, non una stima**, e porta la quota di TA in
  direzione opposta alla media europea (§9).
- **Il BERD non è modellato**: il 3% del PIL è per due terzi una scommessa
  sull'industria, su cui nessuna leva qui discussa agisce.
- **Compartimento singolo per i precari**: a permanenze molto lunghe (>9-10 anni) perde
  realismo, perché nessuno resta davvero con attrito costante.
- **La quota a incarico di ricerca è media, non per coorte**: il modello applica il 32,5%
  di anni-persona uniformemente allo stock, invece di seguire ogni persona lungo la sua
  finestra dei 6 anni. Sulle masse è equivalente; sul profilo temporale del singolo no.
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

Richiede `python3` con `numpy`, `pandas`, `matplotlib`.

```
python3 piano_transizione.py
```

Produce a schermo: stato iniziale e calibrazione, tabella di stabilizzazione EPR,
frontiera iso-HERD, blocco scatti, retroflusso fiscale, traiettorie dei tre scenari e
tabelle complete per FLC ed ERA_PPP_ric. In `output/`: `transizione_*.csv` (una riga per
anno, ~75 colonne), i grafici di confronto e **quattro grafici del solo scenario
ERA_PPP_ric** (`ERA_PPP_ric_trend.png`, `_ffo.png`, `_organico.png`, `_spesa.png`).

**Le opzioni che spostano di più il risultato:**

```
--uplift-ppp 1.6485      parità coi 5 paesi che pagano meglio invece che con la media UE
--quota-ric-uni 0        via il compromesso: torna al modello tutto-cattedre
--quota-incarico 0       tutti i postdoc su contratto di ricerca pieno (45.000, tassato)
--precari-anni 3         precariato corto -> regime a cattedre (quota-docente 71%)
--rtt-anni 3             tenure track rapida (ex RTD-B) invece dei 5 anni L.79/2022
--p2-tgt 1.0             nessun filtro a fine postdoc: tutta la selezione sul dottorato
--ta-elast 0.4           TA come overhead invece che come obiettivo
--scatti-blocco-anni 0   spegne il blocco degli scatti (acceso di default)
--precari-oggi 35000     stima PNRR invece della chiusura, lascia il gap in vista
```

---

## Appendice — file del progetto

| File | Contenuto |
|---|---|
| `piano_transizione.py` | **Entry point**: CLI, calibrazione, definizione dei tre scenari, stampe e grafici |
| `config.py` | **Tutti i numeri di input**, con la fonte accanto |
| `regime.py` | Composizione di **stato stazionario**, scale stipendiali, frontiere iso-HERD e iso-GOVERD (tutto in forma chiusa) |
| `motore.py` | **Motore stock-flow**: lo stato per coorte e la sua evoluzione anno per anno. L'unico punto in cui il tempo avanza |
| `calibrazione.py` | Residui ricavati dai dati osservati e diagnostica |
| `irpef.py` | **Retroflusso fiscale**: dal costo lordo ente alla busta paga e all'IRPEF, pro capite |
| `tabelle.py` | Righe e impaginazione delle tabelle di scenario |
| `grafici.py` | Tutti i PNG |
| `spesa_pubblica_rs_eu.py` | Serie storiche 2000-2024 di HERD+GOVERD per i grandi paesi UE (Eurostat SDG_09_10) |
| `confronto_prepensionamento.py` | Confronto sistematico delle configurazioni della leva di prepensionamento |
| `input/` | Serie USTAT per età e qualifica, assunti e cessati |
| `doc/` | CCNL 2022-2024, dataset Eurostat, sintesi divulgativa |
| `output/` | CSV e PNG prodotti dalle esecuzioni |
