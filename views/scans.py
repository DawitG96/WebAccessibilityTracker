# -*- coding: utf-8 -*-
"""Route per l'analisi automatica (live o del codice) di un progetto, eseguita in background."""
import os
import threading
from pathlib import Path
from urllib.parse import urlparse

from flask import flash, redirect, request, url_for

import database
from database import get_db
from extensions import app
from scanner.store import import_results
from services.lookups import get_project

# Un'analisi alla volta per progetto; lo stato vive in memoria finché il server resta acceso.
JOBS = {}


def _session_path(project_id):
    return os.path.join(os.path.dirname(database.DB_PATH), "sessioni", f"progetto-{project_id}.json")


@app.context_processor
def inject_scan():
    return {"scan_job": JOBS.get, "scan_session": lambda pid: os.path.exists(_session_path(pid))}


def _start(project_id, target, *args):
    job = {"stato": "in corso", "log": [], "esito": None}
    JOBS[project_id] = job

    def log(msg):
        job["log"] = (job["log"] + [str(msg)])[-30:]

    def run():
        try:
            target(log, *args)
            job["stato"] = "completata"
        except Exception as e:  # l'errore va mostrato nella pagina, non perso nel thread
            log(f"Errore: {e}")
            job["stato"] = "errore"

    threading.Thread(target=run, daemon=True).start()


def _scan(log, project_id, kind, source, max_pages, session):
    if kind == "live":
        from scanner.live import scan_site
        pages = scan_site(source, max_pages=max_pages, storage_state=session, log=log)
    else:
        from scanner.static import scan_project
        pages = scan_project(source, log=log)
    db = get_db()
    stats = import_results(db, project_id, pages, kind)
    db.close()
    JOBS[project_id]["esito"] = stats
    log(f"Importati: {stats['pagine']} pagine nuove, {stats['componenti']} componenti nuovi, "
        f"{stats['anomalie']} non conformità.")


def _login(log, url, path):
    from scanner.live import interactive_login
    interactive_login(url, path, log=log)


def _project_or_404(platform_slug, project_slug):
    db = get_db()
    project = get_project(db, platform_slug, project_slug)
    db.close()
    return project


@app.route("/platform/<platform_slug>/project/<project_slug>/analisi", methods=["POST"])
def start_scan(platform_slug, project_slug):
    project = _project_or_404(platform_slug, project_slug)
    if not project:
        flash("Progetto non trovato.", "error")
        return redirect(url_for("index"))
    back = redirect(url_for("project_detail", platform_slug=platform_slug, project_slug=project_slug))
    job = JOBS.get(project["id"])
    if job and job["stato"] == "in corso":
        flash("C'è già un'analisi in corso per questo progetto.", "error")
        return back
    kind = request.form.get("modo")
    if kind == "live":
        source = request.form.get("url", "").strip()
        if urlparse(source).scheme not in ("http", "https") or not urlparse(source).netloc:
            flash("Inserisci un URL completo (http:// o https://).", "error")
            return back
        try:
            max_pages = min(max(int(request.form.get("pagine", 10)), 1), 100)
        except ValueError:
            max_pages = 10
        session = _session_path(project["id"]) if request.form.get("usa_sessione") else None
        if session and not os.path.exists(session):
            session = None
    elif kind == "codice":
        source = request.form.get("cartella", "").strip().strip('"')
        if not source or not Path(source).is_dir():
            flash("Cartella del progetto non trovata sul computer che esegue il tracker.", "error")
            return back
        max_pages, session = None, None
    else:
        flash("Modalità di analisi non valida.", "error")
        return back
    _start(project["id"], _scan, project["id"], kind, source, max_pages, session)
    flash("Analisi avviata: i risultati vengono importati al termine.", "ok")
    return back


@app.route("/platform/<platform_slug>/project/<project_slug>/analisi/login", methods=["POST"])
def scan_login(platform_slug, project_slug):
    project = _project_or_404(platform_slug, project_slug)
    if not project:
        flash("Progetto non trovato.", "error")
        return redirect(url_for("index"))
    url = request.form.get("url", "").strip()
    if urlparse(url).scheme not in ("http", "https"):
        flash("Inserisci l'URL della pagina di login (http:// o https://).", "error")
    else:
        _start(project["id"], _login, url, _session_path(project["id"]))
        flash("Si è aperto un browser: effettua il login e chiudi la finestra per salvare la sessione.", "ok")
    return redirect(url_for("project_detail", platform_slug=platform_slug, project_slug=project_slug))
