# -*- coding: utf-8 -*-
"""Catalogo dei pattern noti (HTML nativo, ruoli ARIA, Angular Material, PrimeNG, Bootstrap).

Per ogni pattern: come riconoscerlo nel DOM, come deve comportarsi da tastiera (WAI-ARIA APG)
e quali criteri WCAG coinvolge. L'analisi live usa i campi tecnici (selettore, tasti, gruppo,
dialog) per i test; «regole» è il testo per chi valuta, a mano o con un agente AI (mappa JSON).
Vengono segnalate come non conformità solo le violazioni WCAG, non le semplici deviazioni dall'APG.
"""

APG = "https://www.w3.org/WAI/ARIA/apg/patterns/"

DIALOG = ("dialog[open],[role=dialog],[role=alertdialog],[aria-modal=true],mat-dialog-container,"
          ".mat-mdc-dialog-container,.p-dialog,.modal.show,.cdk-overlay-pane [role=dialog]")
MODAL = "dialog:modal,[aria-modal=true],mat-dialog-container,.mat-mdc-dialog-container,.p-dialog-mask .p-dialog,.modal.show"

PATTERNS = [
    {"nome": "Link", "riuso": "Link", "selettore": "a[href],[role=link]", "ruoli": {"link": ["Enter"]},
     "criteri": ["2.1.1", "2.4.4", "2.4.7", "1.4.11", "4.1.2"], "apg": APG + "link/",
     "regole": ["Raggiungibile con Tab e attivabile con Invio.",
                "Focus visibile con contrasto ≥ 3:1 rispetto allo stato senza focus.",
                "Testo (o nome accessibile) che dica dove porta; <div>/<span> con role=link devono avere tabindex=0 e gestire Invio."]},
    {"nome": "Bottone", "riuso": "Bottone", "selettore": "button,input[type=button],input[type=submit],input[type=reset],[role=button],"
                                     "[mat-button],[mat-raised-button],[mat-icon-button],[mat-flat-button],p-button,.p-button",
     "ruoli": {"button": ["Enter", " "]},
     "criteri": ["2.1.1", "2.4.7", "1.4.11", "4.1.2"], "apg": APG + "button/",
     "regole": ["Attivabile con Invio e con Spazio.", "Bottoni con sola icona: nome accessibile (aria-label).",
                "Toggle: aria-pressed; apre/chiude contenuti: aria-expanded aggiornato.", "Focus visibile con contrasto ≥ 3:1."]},
    {"nome": "Checkbox / Switch", "riuso": "Form / Campo di input", "selettore": "input[type=checkbox],[role=checkbox],[role=switch],mat-checkbox,"
                                               "mat-slide-toggle,p-checkbox,p-inputswitch,p-toggleswitch",
     "ruoli": {"checkbox": [" "], "switch": [" ", "Enter"]},
     "criteri": ["2.1.1", "4.1.2", "1.3.1", "3.3.2"], "apg": APG + "checkbox/",
     "regole": ["Spazio cambia lo stato e aria-checked si aggiorna.", "Etichetta associata e cliccabile."]},
    {"nome": "Radio group", "selettore": "[role=radiogroup],mat-radio-group,fieldset:has(input[type=radio])",
     "gruppo": {"item": "[role=radio],input[type=radio]", "verso": "verticale"}, "ruoli": {"radio": [" "]},
     "criteri": ["2.1.1", "4.1.2", "1.3.1"], "apg": APG + "radio/",
     "regole": ["Un solo Tab entra nel gruppo; le frecce cambiano la selezione.", "Gruppo con nome (legend o aria-labelledby)."]},
    {"nome": "Dialog / Modale", "selettore": DIALOG, "dialog": True,
     "criteri": ["2.4.3", "2.1.2", "4.1.2", "1.3.1"], "apg": APG + "dialog-modal/",
     "regole": ["All'apertura il focus entra nel dialog.", "Se modale, Tab e Shift+Tab restano dentro il dialog.",
                "Esc chiude (o c'è un bottone di chiusura raggiungibile).", "Alla chiusura il focus torna all'elemento che l'ha aperto.",
                "Nome accessibile (aria-labelledby sul titolo) e aria-modal=true se modale."]},
    {"nome": "Tab", "selettore": "[role=tablist],mat-tab-group,.mat-mdc-tab-group,.p-tabview,.p-tabs,.nav-tabs",
     "gruppo": {"item": "[role=tab]", "verso": "orizzontale"}, "ruoli": {"tab": ["Enter", " "]},
     "criteri": ["2.1.1", "4.1.2", "1.3.1"], "apg": APG + "tabs/",
     "regole": ["Un solo Tab entra nella tablist; frecce sinistra/destra spostano tra le schede.",
                "aria-selected sulla scheda attiva, tabpanel con aria-labelledby."]},
    {"nome": "Menu", "selettore": "[role=menu],[role=menubar],.mat-mdc-menu-panel,.p-menu,.p-menubar,.p-tieredmenu,.dropdown-menu.show",
     "gruppo": {"item": "[role=menuitem],[role=menuitemcheckbox],[role=menuitemradio]", "verso": "verticale"},
     "ruoli": {"menuitem": ["Enter", " "]},
     "criteri": ["2.1.1", "4.1.2", "2.4.3"], "apg": APG + "menubar/",
     "regole": ["Il pulsante che apre il menu ha aria-haspopup e aria-expanded.", "Frecce su/giù tra le voci, Esc chiude e riporta il focus al pulsante.",
                "Per una semplice lista di link di navigazione basta una <ul> di link (niente role=menu)."]},
    {"nome": "Listbox / Select", "selettore": "select,[role=listbox],[role=combobox],mat-select,.p-dropdown,.p-select,p-autocomplete,.p-multiselect",
     "riuso": "Form / Campo di input", "riuso_sel": "select,[role=combobox],mat-select,.p-dropdown,.p-select",
     "gruppo": {"item": "[role=option]", "verso": "verticale"}, "ruoli": {"combobox": ["Enter", "ArrowDown", " "], "option": ["Enter", " "]},
     "criteri": ["2.1.1", "4.1.2", "1.3.1", "3.3.2"], "apg": APG + "combobox/",
     "regole": ["Freccia giù (o Alt+giù) apre l'elenco, le frecce scorrono le opzioni, Invio sceglie, Esc chiude.",
                "aria-expanded sul combobox, aria-activedescendant o focus sull'opzione attiva, etichetta associata."]},
    {"nome": "Slider", "riuso": "Form / Campo di input", "selettore": "[role=slider],input[type=range],mat-slider,p-slider", "slider": True,
     "criteri": ["2.1.1", "4.1.2"], "apg": APG + "slider/",
     "regole": ["Frecce cambiano il valore e aria-valuenow si aggiorna; Home/Fine agli estremi."]},
    {"nome": "Accordion / Disclosure", "selettore": "details,mat-accordion,mat-expansion-panel,.p-accordion,.accordion-button,"
                                                    "[data-bs-toggle=collapse],[aria-controls][aria-expanded]",
     "criteri": ["2.1.1", "4.1.2"], "apg": APG + "accordion/",
     "regole": ["L'intestazione è un bottone: Invio/Spazio aprono e chiudono.", "aria-expanded aggiornato e aria-controls verso il pannello."]},
    {"nome": "Tooltip", "selettore": "[role=tooltip],[mattooltip],[ptooltip],[data-bs-toggle=tooltip],.mat-mdc-tooltip,.p-tooltip",
     "criteri": ["1.4.13", "4.1.2"], "apg": APG + "tooltip/",
     "regole": ["Compare anche al focus, non solo all'hover; Esc lo chiude senza spostare il focus.",
                "Resta visibile se ci si passa sopra col mouse; collegato con aria-describedby."]},
    {"nome": "Tabella", "selettore": "table,[role=grid],[role=table],mat-table,.mat-mdc-table,.p-datatable",
     "criteri": ["1.3.1", "4.1.2"], "apg": APG + "table/",
     "regole": ["Intestazioni <th> (con scope) o role=columnheader; didascalia o nome accessibile.",
                "Griglie interattive (role=grid): frecce tra le celle."]},
    {"nome": "Carosello", "selettore": "[aria-roledescription=carousel i],.carousel,.swiper,.slick-slider,p-carousel,.p-carousel",
     "criteri": ["2.2.2", "2.1.1", "4.1.2"], "apg": APG + "carousel/",
     "regole": ["Se scorre da solo: controllo di pausa raggiungibile da tastiera, e si ferma al focus.",
                "Bottoni avanti/indietro con nome; slide con nome (es. «2 di 5»)."]},
    {"nome": "Notifica / Toast", "selettore": "[role=alert],[role=status],[aria-live]:not([aria-live=off]),mat-snack-bar-container,"
                                              ".mat-mdc-snack-bar-container,.p-toast,.toast",
     "criteri": ["4.1.3", "2.2.1"], "apg": APG + "alert/",
     "regole": ["Il contenitore aria-live esiste già prima del messaggio, così viene annunciato.",
                "Se sparisce da sola, il tempo deve bastare (o il messaggio resta consultabile)."]},
]

# Tasti attesi per i widget personalizzati (non nativi), per ruolo.
ROLE_KEYS = {r: k for p in PATTERNS for r, k in p.get("ruoli", {}).items()}

# Configurazione passata alle sonde nel browser.
PROBE_CONFIG = {
    "dialog": DIALOG,
    "modal": MODAL,
    "roleKeys": ROLE_KEYS,
    "groups": [{"nome": p["nome"], "sel": p["selettore"], **p["gruppo"]} for p in PATTERNS if "gruppo" in p],
    "slider": next(p["selettore"] for p in PATTERNS if p.get("slider")),
    "patterns": {p["nome"]: p["selettore"] for p in PATTERNS},
    # elementi atomici riusati: un solo componente per firma (pattern + tag + classi), con l'elenco delle occorrenze
    "riuso": [{"nome": p["nome"], "sel": p.get("riuso_sel", p["selettore"]), "tipo": p["riuso"]} for p in PATTERNS if "riuso" in p],
}


def rules_for(names):
    """Regole dei pattern presenti in una pagina, per la mappa JSON."""
    return [{k: p[k] for k in ("nome", "selettore", "criteri", "regole", "apg")} for p in PATTERNS if p["nome"] in names]
