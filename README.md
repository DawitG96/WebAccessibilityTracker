# Accessibility Tracker — WCAG 2.2 (A/AA)

Webapp locale per tracciare la valutazione di conformità all'accessibilità di piattaforme web.

Gerarchia: **Piattaforma → Progetti (es. microservizi) → Pagine → Componenti → Criteri WCAG**.
Le piattaforme sono facoltative: un progetto può anche vivere da solo.
Per ogni componente, in base alla tipologia (bottone, navbar, tabella…), viene generata
automaticamente la checklist dei criteri WCAG 2.2 applicabili (livelli A e AA; i criteri
AAA sono opzionali, marcati distintamente ed esclusi dal calcolo di conformità), con i
riferimenti WAI-ARIA da consultare. Ogni criterio può essere marcato come conforme,
non conforme (con motivazione e stato di lavorazione), non applicabile o da verificare.
Report finale delle anomalie stampabile (HTML → PDF) ed esportabile in CSV/Excel.

## Avvio con Docker (consigliato — Windows, Linux, macOS)

```bash
docker compose up -d
```

Poi apri il browser su **http://localhost:8000**

- I dati restano nella cartella `./data/tracker.db` (montata come volume): sopravvivono
  a riavvii e aggiornamenti del container.
- Per fermare: `docker compose down`
- Per ricostruire dopo una modifica al codice: `make up` — incrementa automaticamente la
  patch version nel file `VERSION` (mostrata in fondo alla pagina) e poi esegue
  `docker compose up -d --build`. Il comando `docker compose up -d --build` puro resta
  disponibile ma non incrementa la versione.

## Avvio senza Docker (Python 3.10+)

```bash
pip install -r requirements.txt
python -m playwright install chromium
python app.py
```

Poi apri **http://localhost:8000** (senza Docker l'app ascolta su 127.0.0.1).

## Come si usa

1. (Facoltativo) **Crea una piattaforma** se devi valutare più progetti/microservizi collegati.
2. **Crea un progetto** per l'applicativo da valutare (nome, URL, piattaforma, descrizione).
3. **Aggiungi le pagine** web che compongono il campione di valutazione.
4. Per ogni pagina, **rileva i componenti** scegliendo la tipologia: la checklist dei
   criteri applicabili viene creata automaticamente (spunta «Includi criteri AAA» se vuoi
   valutare anche quelli). Puoi aggiungere o rimuovere criteri dalla checklist di ogni
   singolo componente.
4. Per ogni criterio segna l'**esito**: Conforme / Non conforme / Non applicabile / Da verificare,
   con la motivazione nelle note. Per le non conformità imposta lo **stato di lavorazione**
   (Aperta → In lavorazione → Risolta → Risolta e verificata): ogni cambiamento viene
   registrato nello storico.
5. Dal progetto genera il **Report anomalie** (stampabile o salvabile in PDF dal browser)
   oppure esporta in **CSV** / **Excel**.

Dalla voce di menu **Tipologie componenti** puoi personalizzare le tipologie predefinite
o crearne di nuove, scegliendo quali criteri WCAG associare.

## Analisi automatica

Dalla pagina del progetto (bottone **Avvia analisi automatica…**, che apre un modale) o da riga
di comando con `scan.py`. I risultati vengono importati nel progetto: le pagine e i componenti
trovati vengono creati con la checklist della loro tipologia, e i criteri violati diventano
**non conformi** (stato «Aperta») con le occorrenze nelle note. Le valutazioni già marcate a mano
come conformi o non applicabili non vengono sovrascritte. Ripetere l'analisi aggiorna gli stessi
componenti senza duplicarli.

Di solito basta il **sito live** dall'URL radice. Se il codice è disponibile, nel modale si può
lanciare insieme anche l'analisi del **codice** (prima del live); se qualcuno l'ha già fatta in
passato sul progetto, il live la usa comunque. Senza codice, le pagine sorelle con la stessa
struttura (es. `/regione/piemonte` e `/regione/lombardia`) vengono analizzate una volta sola.
Con il codice, il live si aggancia a quanto trovato:

- ogni URL viene associata alla sua rotta (`/news/42` → `/news/:id`): la pagina del codice prende
  l'URL reale e il crawl analizza una sola URL per rotta, partendo anche dalle rotte note;
- gli elementi del DOM vengono collegati al componente del codice che li genera (tag Angular
  `app-*`, oppure classe/id con lo stesso nome): le rilevazioni live finiscono su quel componente,
  che prende tipologia e nome leggibile dal sito;
- una rilevazione del codice trovata anche dal live viene **confermata**; se invece il live ha
  verificato lo stesso criterio sul componente senza violazioni, torna **da verificare** con una
  nota (solo se è ancora «Aperta» e non toccata a mano).

La cartella del codice viene ricordata per il progetto.

**Sito in esecuzione** (deployato o in localhost), con un browser Chromium reale:

- riconoscimento dei componenti dal DOM e dall'uso (navigazione, menu, dialog e banner
  cookie, caroselli, form, tabelle…); gli elementi con un gestore click vengono letti dal
  browser, così un `<div>` cliccabile viene riconosciuto come controllo;
- regole WCAG 2.0–2.2 A/AA di [axe-core](https://github.com/dequelabs/axe-core) (messaggi in italiano);
- contrasto **misurato sui pixel** per i testi su immagini, gradienti o sovrapposizioni,
  che axe non sa decidere: lo sfondo viene letto da uno screenshot col testo nascosto;
- giro completo con **Tab**: focus visibile (confronto screenshot con e senza focus),
  focus su elementi nascosti o coperti (es. header sticky), trappole da tastiera, cambi di
  pagina al focus;
- elementi cliccabili **non raggiungibili da tastiera** e senza ruolo;
- menu/toggle provati con Invio e Spazio e poi col click: segnala quelli che funzionano solo
  col mouse e quelli che non aggiornano `aria-expanded` (anche in vista mobile);
- reflow a 320px e caroselli che si muovono da soli senza pausa.

Il crawl segue i link dello stesso sito ed evita quelli di logout. Per le **aree
autenticate** usa «Apri il browser per il login» (o `--login` da riga di comando): fai il
login a mano, chiudi la finestra e la sessione viene salvata in `data/sessioni/` per le
analisi successive. Le credenziali non passano mai dal tracker. Il login interattivo
richiede un desktop, quindi non funziona dentro Docker: lì usa un file di sessione
creato da riga di comando.

**Codice sorgente** (Angular, React/Next, Vue/Nuxt, Svelte, HTML): ricava le rotte, segue
l'albero dei componenti caricati da ciascuna (più il layout comune) e analizza i template:
immagini senza alt, elementi cliccabili non nativi senza ruolo/tabindex/tastiera, link e
bottoni senza nome, campi senza etichetta, tabindex positivi, `aria-hidden` su elementi
focalizzabili, iframe senza title, video in autoplay o senza sottotitoli, hover senza
focus, `outline: none` senza alternativa, lingua e zoom in `index.html`. È un'analisi
euristica: contrasto, focus e comportamento reale vanno verificati con l'analisi live.

```bash
python scan.py live https://example.com --pagine 10 --progetto 3
python scan.py live http://localhost:4200 --login --progetto 3
python scan.py codice C:\progetti\mio-frontend --progetto 3
python tests/test_scanner.py    # verifica dell'analisi del codice
```

`--progetto` è l'id del progetto in cui importare (per `live` usa anche rotte e componenti già
trovati dal codice di quel progetto); senza, stampa solo un riepilogo
(`--json file.json` salva i risultati grezzi).

## Fonti

- Criteri di successo: [WCAG 2.2 — traduzione italiana ufficiale](https://www.w3.org/Translations/WCAG22-it/)
- Ruoli, stati e proprietà: [WAI-ARIA 1.2](https://www.w3.org/TR/wai-aria/)

Il database SQLite (`data/tracker.db`) viene creato e popolato al primo avvio con gli
86 criteri (31 A, 24 AA, 31 AAA) e 18 tipologie di componente predefinite. I database
creati con versioni precedenti dell'app vengono migrati automaticamente all'avvio,
senza perdita di dati.

Nota sul calcolo: la percentuale di conformità considera solo i criteri A e AA valutati
(conformi / (conformi + non conformi)); i criteri AAA sono tracciati ma esclusi.
