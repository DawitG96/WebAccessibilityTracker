# -*- coding: utf-8 -*-
"""
Criteri di successo WCAG 2.2 (livelli A, AA e AAA) — traduzione italiana ufficiale
Fonte: https://www.w3.org/Translations/WCAG22-it/
Tipologie di componente con criteri applicabili e riferimenti WAI-ARIA
Fonte ARIA: https://www.w3.org/TR/wai-aria/

Nota: i criteri AAA sono analizzabili ma NON concorrono al calcolo della conformità.
"""

WCAG_BASE_URL = "https://www.w3.org/Translations/WCAG22-it/#"

# (codice, titolo, livello, principio, anchor) — in ordine numerico: l'ordine
# di questa lista determina il sort_order nel database.
CRITERIA = [
    ("1.1.1", "Contenuti non testuali", "A", "Percepibile", "non-text-content"),
    ("1.2.1", "Solo audio e solo video (preregistrati)", "A", "Percepibile", "audio-only-and-video-only-prerecorded"),
    ("1.2.2", "Sottotitoli (preregistrati)", "A", "Percepibile", "captions-prerecorded"),
    ("1.2.3", "Audiodescrizione o tipo di media alternativo (preregistrato)", "A", "Percepibile", "audio-description-or-media-alternative-prerecorded"),
    ("1.2.4", "Sottotitoli (in tempo reale)", "AA", "Percepibile", "captions-live"),
    ("1.2.5", "Audiodescrizione (preregistrata)", "AA", "Percepibile", "audio-description-prerecorded"),
    ("1.2.6", "Lingua dei segni (preregistrato)", "AAA", "Percepibile", "sign-language-prerecorded"),
    ("1.2.7", "Audiodescrizione estesa (preregistrata)", "AAA", "Percepibile", "extended-audio-description-prerecorded"),
    ("1.2.8", "Tipo di media alternativo (preregistrato)", "AAA", "Percepibile", "media-alternative-prerecorded"),
    ("1.2.9", "Solo audio (in tempo reale)", "AAA", "Percepibile", "audio-only-live"),
    ("1.3.1", "Informazioni e correlazioni", "A", "Percepibile", "info-and-relationships"),
    ("1.3.2", "Sequenza significativa", "A", "Percepibile", "meaningful-sequence"),
    ("1.3.3", "Caratteristiche sensoriali", "A", "Percepibile", "sensory-characteristics"),
    ("1.3.4", "Orientamento", "AA", "Percepibile", "orientation"),
    ("1.3.5", "Identificare lo scopo degli input", "AA", "Percepibile", "identify-input-purpose"),
    ("1.3.6", "Identificare lo scopo", "AAA", "Percepibile", "identify-purpose"),
    ("1.4.1", "Uso del colore", "A", "Percepibile", "use-of-color"),
    ("1.4.2", "Controllo del sonoro", "A", "Percepibile", "audio-control"),
    ("1.4.3", "Contrasto (minimo)", "AA", "Percepibile", "contrast-minimum"),
    ("1.4.4", "Ridimensionamento del testo", "AA", "Percepibile", "resize-text"),
    ("1.4.5", "Immagini di testo", "AA", "Percepibile", "images-of-text"),
    ("1.4.6", "Contrasto (avanzato)", "AAA", "Percepibile", "contrast-enhanced"),
    ("1.4.7", "Sottofondo sonoro basso o non presente", "AAA", "Percepibile", "low-or-no-background-audio"),
    ("1.4.8", "Presentazione visiva", "AAA", "Percepibile", "visual-presentation"),
    ("1.4.9", "Immagini di testo (senza eccezioni)", "AAA", "Percepibile", "images-of-text-no-exception"),
    ("1.4.10", "Ricalcolo del flusso", "AA", "Percepibile", "reflow"),
    ("1.4.11", "Contrasto in contenuti non testuali", "AA", "Percepibile", "non-text-contrast"),
    ("1.4.12", "Spaziatura del testo", "AA", "Percepibile", "text-spacing"),
    ("1.4.13", "Contenuto con Hover o Focus", "AA", "Percepibile", "content-on-hover-or-focus"),
    ("2.1.1", "Tastiera", "A", "Utilizzabile", "keyboard"),
    ("2.1.2", "Nessun impedimento all'uso della tastiera", "A", "Utilizzabile", "no-keyboard-trap"),
    ("2.1.3", "Tastiera (nessuna eccezione)", "AAA", "Utilizzabile", "keyboard-no-exception"),
    ("2.1.4", "Tasti di scelta rapida", "A", "Utilizzabile", "character-key-shortcuts"),
    ("2.2.1", "Regolazione tempi di esecuzione", "A", "Utilizzabile", "timing-adjustable"),
    ("2.2.2", "Pausa, stop, nascondi", "A", "Utilizzabile", "pause-stop-hide"),
    ("2.2.3", "Nessun tempo di esecuzione", "AAA", "Utilizzabile", "no-timing"),
    ("2.2.4", "Interruzioni", "AAA", "Utilizzabile", "interruptions"),
    ("2.2.5", "Riautenticazione", "AAA", "Utilizzabile", "re-authentication"),
    ("2.2.6", "Termine del tempo", "AAA", "Utilizzabile", "timeouts"),
    ("2.3.1", "Tre lampeggiamenti o inferiore alla soglia", "A", "Utilizzabile", "three-flashes-or-below-threshold"),
    ("2.3.2", "Tre lampeggiamenti", "AAA", "Utilizzabile", "three-flashes"),
    ("2.3.3", "Animazione da interazioni", "AAA", "Utilizzabile", "animation-from-interactions"),
    ("2.4.1", "Salto di blocchi", "A", "Utilizzabile", "bypass-blocks"),
    ("2.4.2", "Titolazione della pagina", "A", "Utilizzabile", "page-titled"),
    ("2.4.3", "Ordine del focus", "A", "Utilizzabile", "focus-order"),
    ("2.4.4", "Scopo del collegamento (nel contesto)", "A", "Utilizzabile", "link-purpose-in-context"),
    ("2.4.5", "Differenti modalità", "AA", "Utilizzabile", "multiple-ways"),
    ("2.4.6", "Intestazioni ed etichette", "AA", "Utilizzabile", "headings-and-labels"),
    ("2.4.7", "Focus visibile", "AA", "Utilizzabile", "focus-visible"),
    ("2.4.8", "Posizione", "AAA", "Utilizzabile", "location"),
    ("2.4.9", "Scopo del collegamento (solo collegamento)", "AAA", "Utilizzabile", "link-purpose-link-only"),
    ("2.4.10", "Intestazioni di sezione", "AAA", "Utilizzabile", "section-headings"),
    ("2.4.11", "Focus non nascosto (minimo)", "AA", "Utilizzabile", "focus-not-obscured-minimum"),
    ("2.4.12", "Focus non nascosto (avanzato)", "AAA", "Utilizzabile", "focus-not-obscured-enhanced"),
    ("2.4.13", "Aspetto del focus", "AAA", "Utilizzabile", "focus-appearance"),
    ("2.5.1", "Movimenti del puntatore", "A", "Utilizzabile", "pointer-gestures"),
    ("2.5.2", "Cancellazione delle azioni del puntatore", "A", "Utilizzabile", "pointer-cancellation"),
    ("2.5.3", "Etichetta nel nome", "A", "Utilizzabile", "label-in-name"),
    ("2.5.4", "Azionamento da movimento", "A", "Utilizzabile", "motion-actuation"),
    ("2.5.5", "Dimensione dell'obiettivo (avanzato)", "AAA", "Utilizzabile", "target-size-enhanced"),
    ("2.5.6", "Meccanismi di input simultanei", "AAA", "Utilizzabile", "concurrent-input-mechanisms"),
    ("2.5.7", "Movimenti di trascinamento", "AA", "Utilizzabile", "dragging-movements"),
    ("2.5.8", "Dimensione dell'obiettivo (minimo)", "AA", "Utilizzabile", "target-size-minimum"),
    ("3.1.1", "Lingua della pagina", "A", "Comprensibile", "language-of-page"),
    ("3.1.2", "Parti in lingua", "AA", "Comprensibile", "language-of-parts"),
    ("3.1.3", "Parole inusuali", "AAA", "Comprensibile", "unusual-words"),
    ("3.1.4", "Abbreviazioni", "AAA", "Comprensibile", "abbreviations"),
    ("3.1.5", "Livello di lettura", "AAA", "Comprensibile", "reading-level"),
    ("3.1.6", "Pronuncia", "AAA", "Comprensibile", "pronunciation"),
    ("3.2.1", "Al focus", "A", "Comprensibile", "on-focus"),
    ("3.2.2", "All'input", "A", "Comprensibile", "on-input"),
    ("3.2.3", "Navigazione coerente", "AA", "Comprensibile", "consistent-navigation"),
    ("3.2.4", "Identificazione coerente", "AA", "Comprensibile", "consistent-identification"),
    ("3.2.5", "Cambiamenti su richiesta", "AAA", "Comprensibile", "change-on-request"),
    ("3.2.6", "Aiuto coerente", "A", "Comprensibile", "consistent-help"),
    ("3.3.1", "Identificazione di errori", "A", "Comprensibile", "error-identification"),
    ("3.3.2", "Etichette o istruzioni", "A", "Comprensibile", "labels-or-instructions"),
    ("3.3.3", "Suggerimenti per gli errori", "AA", "Comprensibile", "error-suggestion"),
    ("3.3.4", "Prevenzione degli errori (legali, finanziari, dati)", "AA", "Comprensibile", "error-prevention-legal-financial-data"),
    ("3.3.5", "Aiuto", "AAA", "Comprensibile", "help"),
    ("3.3.6", "Prevenzione degli errori (tutti)", "AAA", "Comprensibile", "error-prevention-all"),
    ("3.3.7", "Inserimento ridondante", "A", "Comprensibile", "redundant-entry"),
    ("3.3.8", "Autenticazione accessibile (minimo)", "AA", "Comprensibile", "accessible-authentication-minimum"),
    ("3.3.9", "Autenticazione accessibile (avanzato)", "AAA", "Comprensibile", "accessible-authentication-enhanced"),
    ("4.1.2", "Nome, ruolo, valore", "A", "Robusto", "name-role-value"),
    ("4.1.3", "Messaggi di stato", "AA", "Robusto", "status-messages"),
]

ALL_CODES = [c[0] for c in CRITERIA]

# Tipologie di componente:
# (nome, descrizione, ruoli/attributi WAI-ARIA di riferimento, [criteri A/AA applicabili])
COMPONENT_TYPES = [
    ("Bottone", "Pulsanti, pulsanti icona, toggle button",
     "role=button; aria-label / aria-labelledby (per bottoni icona); aria-pressed (toggle); aria-disabled; aria-expanded (se apre contenuti)",
     ["1.1.1", "1.4.1", "1.4.3", "1.4.11", "2.1.1", "2.4.7", "2.4.11", "2.5.2", "2.5.3", "2.5.8", "3.2.2", "4.1.2"]),

    ("Link", "Collegamenti testuali, link icona, link 'leggi di più'",
     "role=link; aria-label se il testo non è esplicativo; aria-current per il link attivo",
     ["1.1.1", "1.4.1", "1.4.3", "2.1.1", "2.4.4", "2.4.7", "2.5.3", "2.5.8", "4.1.2"]),

    ("Navbar / Navigazione", "Menu di navigazione principale, header, footer di navigazione",
     "role=navigation (nav); aria-label per distinguere più nav; aria-current=page; aria-expanded / aria-haspopup per sottomenu",
     ["1.3.1", "1.4.3", "2.1.1", "2.4.1", "2.4.3", "2.4.5", "2.4.7", "3.2.3", "3.2.4", "4.1.2"]),

    ("Tabella", "Tabelle dati, tabelle ordinabili, griglie",
     "table, th con scope, caption; role=grid per tabelle interattive; aria-sort per colonne ordinabili; aria-rowcount / aria-colcount",
     ["1.3.1", "1.3.2", "1.4.3", "1.4.10", "2.1.1", "2.4.6", "4.1.2"]),

    ("Form / Campo di input", "Input testo, select, checkbox, radio, textarea e relative etichette",
     "label for / aria-label / aria-labelledby; aria-required; aria-invalid; aria-describedby per errori e istruzioni; autocomplete",
     ["1.3.1", "1.3.5", "1.4.1", "1.4.3", "2.1.1", "2.4.6", "2.4.7", "3.2.2", "3.3.1", "3.3.2", "3.3.3", "3.3.4", "3.3.7", "3.3.8", "4.1.2"]),

    ("Immagine / Icona", "Immagini informative, decorative, grafici, icone",
     "alt appropriato; alt=\"\" o role=presentation se decorativa; role=img per SVG; aria-hidden=true per icone decorative",
     ["1.1.1", "1.4.1", "1.4.5", "1.4.11"]),

    ("Modale / Dialog", "Finestre di dialogo, popup, lightbox",
     "role=dialog / alertdialog; aria-modal=true; aria-labelledby (titolo); gestione focus trap e restituzione focus alla chiusura",
     ["1.3.1", "1.4.3", "2.1.1", "2.1.2", "2.4.3", "2.4.7", "2.4.11", "4.1.2"]),

    ("Menu / Dropdown", "Menu a tendina, menu contestuali, combobox",
     "role=menu / menuitem oppure combobox / listbox / option; aria-expanded; aria-haspopup; aria-activedescendant; aria-selected",
     ["1.3.1", "1.4.3", "1.4.13", "2.1.1", "2.4.3", "2.4.7", "3.2.2", "4.1.2"]),

    ("Tab", "Interfacce a schede",
     "role=tablist / tab / tabpanel; aria-selected; aria-controls; navigazione con frecce; tabindex gestito",
     ["1.3.1", "1.4.3", "2.1.1", "2.4.3", "2.4.7", "4.1.2"]),

    ("Accordion", "Pannelli espandibili / collassabili",
     "button con aria-expanded; aria-controls; region con aria-labelledby",
     ["1.3.1", "1.4.3", "2.1.1", "2.4.7", "4.1.2"]),

    ("Carosello / Slider", "Caroselli di immagini o contenuti, slideshow",
     "role=region con aria-roledescription=carousel; aria-live per aggiornamenti; controlli pausa/avanti/indietro accessibili",
     ["1.1.1", "1.3.1", "2.1.1", "2.2.2", "2.4.3", "2.4.7", "2.5.8", "4.1.2"]),

    ("Video / Audio", "Player multimediali, contenuti audio/video",
     "Controlli accessibili da tastiera; sottotitoli; audiodescrizione; trascrizione; nessun autoplay sonoro senza controllo",
     ["1.1.1", "1.2.1", "1.2.2", "1.2.3", "1.2.4", "1.2.5", "1.4.2", "2.1.1", "2.2.2", "2.3.1"]),

    ("Struttura pagina / Intestazioni", "Titolo pagina, gerarchia heading, landmark, lingua",
     "h1–h6 in ordine gerarchico; landmark (main, banner, contentinfo, complementary); lang su html; skip link",
     ["1.3.1", "1.3.2", "2.4.1", "2.4.2", "2.4.6", "3.1.1", "3.1.2"]),

    ("Testo / Contenuto", "Paragrafi, testo formattato, contenuto informativo",
     "Semantica corretta (em, strong, liste); lang per parti in altra lingua",
     ["1.4.1", "1.4.3", "1.4.4", "1.4.10", "1.4.12", "3.1.1", "3.1.2"]),

    ("Tooltip / Contenuto su hover-focus", "Tooltip, popover informativi",
     "role=tooltip; aria-describedby; contenuto rimovibile, che può essere puntato e persistente (1.4.13)",
     ["1.4.13", "2.1.1", "4.1.2"]),

    ("Notifica / Messaggio di stato", "Alert, toast, messaggi di conferma o errore, live region",
     "role=alert / status; aria-live=polite|assertive; aria-atomic",
     ["1.4.1", "1.4.3", "4.1.3"]),

    ("Breadcrumb / Paginazione", "Percorsi di navigazione, paginazione risultati",
     "nav con aria-label=breadcrumb; aria-current=page; lista ordinata",
     ["1.3.1", "1.4.3", "2.1.1", "2.4.4", "2.4.7", "2.5.8", "4.1.2"]),

    ("Altro / Generico", "Componente non riconducibile alle tipologie predefinite: valutare l'intera checklist",
     "Consultare le WAI-ARIA Authoring Practices per il pattern più vicino",
     [c[0] for c in CRITERIA if c[2] != "AAA"]),
]

# Criteri AAA aggiuntivi per tipologia (facoltativi, esclusi dal calcolo di conformità)
AAA_EXTRAS = {
    "Bottone": ["2.4.13", "2.5.5"],
    "Link": ["2.4.9", "2.4.13", "2.5.5"],
    "Navbar / Navigazione": ["2.4.8", "2.4.13"],
    "Tabella": [],
    "Form / Campo di input": ["3.3.5", "3.3.6", "3.3.9"],
    "Immagine / Icona": ["1.4.9"],
    "Modale / Dialog": ["2.4.12", "2.4.13"],
    "Menu / Dropdown": ["2.4.13"],
    "Tab": ["2.4.13"],
    "Accordion": ["2.4.13"],
    "Carosello / Slider": ["2.2.3", "2.3.3", "2.5.5"],
    "Video / Audio": ["1.2.6", "1.2.7", "1.2.8", "1.2.9", "1.4.7", "2.2.3"],
    "Struttura pagina / Intestazioni": ["2.4.8", "2.4.10"],
    "Testo / Contenuto": ["1.4.6", "1.4.8", "1.4.9", "3.1.3", "3.1.4", "3.1.5", "3.1.6"],
    "Tooltip / Contenuto su hover-focus": [],
    "Notifica / Messaggio di stato": ["2.2.4"],
    "Breadcrumb / Paginazione": ["2.4.8"],
    "Altro / Generico": [c[0] for c in CRITERIA if c[2] == "AAA"],
}
