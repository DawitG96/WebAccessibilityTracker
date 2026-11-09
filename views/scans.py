# -*- coding: utf-8 -*-
"""Route per l'analisi automatica (live o del codice) di un progetto, eseguita in background."""
import os
import threading
from pathlib import Path
from urllib.parse import urlparse

from flask import flash, jsonify, redirect, request, url_for

import database
from database import get_db
from extensions import app
from scanner.store import code_sources, import_results
from services.lookups import get_project

# Un'analisi alla volta per progetto; lo stato vive in memoria finché il server resta acceso.
JOBS = {}


def _session_path(project_id):
    return os.path.join(os.path.dirname(database.DB_PATH), "sessioni", f"progetto-{project_id}.json")


@app.context_processor
def inject_scan():
    return {"scan_job": JOBS.get, "scan_session": lambda pid: os.path.exists(_session_path(pid)),
            "scan_dir_ok": lambda d: bool(d) and os.path.isdir(d)}


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


def _scan(log, project_id, code_dir, url, max_pages, session):
    """Prima il codice (rotte e componenti), poi il sito live che si aggancia a quanto trovato."""
    db = get_db()
    try:
        if code_dir:
            from scanner.static import scan_project
            stats = import_results(db, project_id, scan_project(code_dir, log=log), "codice")
            log(f"Codice: {stats['pagine']} pagine nuove, {stats['componenti']} componenti nuovi, "
                f"{stats['anomalie']} non conformità.")
        if url:
            from scanner.live import scan_site
            routes, sources = code_sources(db, project_id)
            pages = scan_site(url, max_pages=max_pages, storage_state=session, log=log, routes=routes, sources=sources)
            stats = import_results(db, project_id, pages, "live")
            log(f"Live: {stats['pagine']} pagine nuove, {stats['componenti']} componenti nuovi, "
                f"{stats['collegati']} collegati al codice, {stats['anomalie']} non conformità "
                f"({stats['confermate']} confermano il codice, {stats['non_riscontrate']} rilevazioni del codice non riscontrate).")
        JOBS[project_id]["esito"] = stats
    finally:
        db.close()


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
    code_dir = url = session = None
    max_pages = 10
    if request.form.get("codice"):
        code_dir = request.form.get("cartella", "").strip().strip('"')
        if not code_dir or not Path(code_dir).is_dir():
            flash("Cartella del progetto non trovata sul computer che esegue il tracker.", "error")
            return back
        db = get_db()
        db.execute("UPDATE projects SET code_dir = ? WHERE id = ?", (code_dir, project["id"]))
        db.commit()
        db.close()
    if request.form.get("live"):
        url = request.form.get("url", "").strip()
        if urlparse(url).scheme not in ("http", "https") or not urlparse(url).netloc:
            flash("Inserisci un URL completo (http:// o https://).", "error")
            return back
        try:
            max_pages = min(max(int(request.form.get("pagine", 10)), 1), 100)
        except ValueError:
            pass
        session = _session_path(project["id"]) if request.form.get("usa_sessione") else None
        if session and not os.path.exists(session):
            session = None
    if not code_dir and not url:
        flash("Scegli almeno un'analisi: codice o sito live.", "error")
        return back
    _start(project["id"], _scan, project["id"], code_dir, url, max_pages, session)
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


@app.route("/analisi/sfoglia", methods=["POST"])
def browse_dir():
    """Finestra nativa di scelta cartella, aperta sul computer che esegue il tracker."""
    try:
        import tkinter
        from tkinter import filedialog
        root = tkinter.Tk()
    except Exception:  # Docker o server senza desktop (o Python senza tkinter)
        return jsonify(error="Finestra di scelta non disponibile qui (es. dentro Docker): incolla il percorso.")
    try:
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.askdirectory(parent=root, title="Cartella del progetto da analizzare")
    finally:
        root.destroy()
    return jsonify(path=os.path.normpath(path) if path else "")
