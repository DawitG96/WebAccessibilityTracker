# Accessibility Tracker — WCAG 2.2 (A/AA)

Webapp locale per tracciare la valutazione di conformità all'accessibilità di piattaforme web.

Gerarchia: **Progetto → Pagine → Componenti → Criteri di successo WCAG**.
Per ogni componente, in base alla tipologia (bottone, navbar, tabella…), viene generata
automaticamente la checklist dei criteri WCAG 2.2 (livelli A e AA) applicabili, con i
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
- Per ricostruire dopo una modifica al codice: `docker compose up -d --build`

## Avvio senza Docker (Python 3.10+)

```bash
pip install -r requirements.txt
python app.py
```

Poi apri **http://localhost:8000** (senza Docker l'app ascolta su 127.0.0.1).

## Come si usa

1. **Crea un progetto** per la piattaforma da valutare (nome, URL, descrizione).
2. **Aggiungi le pagine** web che compongono il campione di valutazione.
3. Per ogni pagina, **rileva i componenti** scegliendo la tipologia: la checklist dei
   criteri applicabili viene creata automaticamente. Puoi aggiungere o rimuovere criteri
   dalla checklist di ogni singolo componente.
4. Per ogni criterio segna l'**esito**: Conforme / Non conforme / Non applicabile / Da verificare,
   con la motivazione nelle note. Per le non conformità imposta lo **stato di lavorazione**
   (Aperta → In lavorazione → Risolta → Risolta e verificata): ogni cambiamento viene
   registrato nello storico.
5. Dal progetto genera il **Report anomalie** (stampabile o salvabile in PDF dal browser)
   oppure esporta in **CSV** / **Excel**.

Dalla voce di menu **Tipologie componenti** puoi personalizzare le tipologie predefinite
o crearne di nuove, scegliendo quali criteri WCAG associare.

## Fonti

- Criteri di successo: [WCAG 2.2 — traduzione italiana ufficiale](https://www.w3.org/Translations/WCAG22-it/)
- Ruoli, stati e proprietà: [WAI-ARIA 1.2](https://www.w3.org/TR/wai-aria/)

Il database SQLite (`data/tracker.db`) viene creato e popolato al primo avvio con i
55 criteri A/AA e 18 tipologie di componente predefinite.
