# -*- coding: utf-8 -*-
"""Analisi automatica di accessibilità da riga di comando.

Esempi:
  python scan.py live https://example.com --pagine 10
  python scan.py live http://localhost:4200 --login       # login manuale, poi analisi autenticata
  python scan.py codice C:\\progetti\\mio-frontend
  python scan.py live https://example.com --progetto 3    # importa i risultati nel progetto con id 3
"""
import argparse
import json
import sys

from database import get_db, init_db
from scanner.store import code_sources, import_results


def main():
    ap = argparse.ArgumentParser(description="Analisi automatica WCAG di un sito o del codice di un progetto frontend.")
    sub = ap.add_subparsers(dest="modo", required=True)
    live = sub.add_parser("live", help="analizza un sito in esecuzione (deployato o in localhost) con un browser reale")
    live.add_argument("url", help="URL di partenza")
    live.add_argument("--pagine", type=int, default=10, help="numero massimo di pagine da analizzare (default 10)")
    live.add_argument("--sessione", help="file di sessione salvato (cookie/localStorage) per le aree autenticate")
    live.add_argument("--login", action="store_true",
                      help="apre un browser visibile per fare il login a mano e salva la sessione prima dell'analisi")
    live.add_argument("--visibile", action="store_true", help="mostra il browser durante l'analisi")
    code = sub.add_parser("codice", help="analizza il sorgente di un progetto (Angular, React, Vue, Svelte, HTML)")
    code.add_argument("cartella", help="cartella radice del progetto (quella con package.json)")
    for p in (live, code):
        p.add_argument("--progetto", type=int, help="id del progetto del tracker in cui importare i risultati")
        p.add_argument("--json", help="salva i risultati grezzi in questo file JSON")
    args = ap.parse_args()

    if args.modo == "live":
        from scanner.live import interactive_login, scan_site
        session = args.sessione
        if args.login:
            session = interactive_login(args.url, session or "data/sessione.json")
        routes = sources = None
        if args.progetto:  # si aggancia a rotte e componenti già trovati dall'analisi del codice
            init_db()
            db = get_db()
            routes, sources = code_sources(db, args.progetto)
            db.close()
        pages = scan_site(args.url, max_pages=args.pagine, storage_state=session, headless=not args.visibile,
                          routes=routes, sources=sources)
        source = "live"
    else:
        from scanner.static import scan_project
        pages = scan_project(args.cartella)
        source = "codice"

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(pages, f, ensure_ascii=False, indent=1, default=lambda b: None)  # screenshot esclusi
    for p in pages:
        n = sum(len(c["findings"]) for c in p["components"])
        print(f"{p['name']}: {len(p['components'])} componenti, {n} rilevazioni")
    if args.progetto:
        init_db()
        db = get_db()
        if not db.execute("SELECT 1 FROM projects WHERE id = ?", (args.progetto,)).fetchone():
            sys.exit(f"Progetto {args.progetto} non trovato.")
        stats = import_results(db, args.progetto, pages, source)
        db.close()
        print(f"Importati: {stats}")


if __name__ == "__main__":
    main()
