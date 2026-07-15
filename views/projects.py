# -*- coding: utf-8 -*-
"""Route per il dettaglio progetto e la gestione delle sue pagine."""
from flask import flash, redirect, render_template, request, url_for

from database import get_db, unique_slug
from extensions import app
from services.lookups import get_project
from services.stats import project_stats


@app.route("/platform/<platform_slug>/project/<project_slug>/edit", methods=["POST"])
def edit_project(platform_slug, project_slug):
    db = get_db()
    project = get_project(db, platform_slug, project_slug)
    if not project:
        db.close()
        flash("Progetto non trovato.", "error")
        return redirect(url_for("index"))
    name = request.form.get("name", "").strip() or "Senza nome"
    new_platform_id = int(request.form.get("platform_id") or project["platform_id"])
    slug = project["slug"]
    if name != project["name"] or new_platform_id != project["platform_id"]:
        slug = unique_slug(db, "projects", name, "platform_id", new_platform_id,
                           exclude_id=project["id"], fallback="progetto")
    db.execute(
        "UPDATE projects SET name = ?, slug = ?, description = ?, url = ?, status = ?, platform_id = ? WHERE id = ?",
        (name, slug, request.form.get("description", "").strip(),
         request.form.get("url", "").strip(),
         request.form.get("status", "In corso"), new_platform_id, project["id"]))
    db.commit()
    pl_slug = db.execute("SELECT slug FROM platforms WHERE id = ?", (new_platform_id,)).fetchone()["slug"]
    db.close()
    flash("Progetto aggiornato.", "ok")
    return redirect(url_for("project_detail", platform_slug=pl_slug, project_slug=slug))


@app.route("/platform/<platform_slug>/project/<project_slug>/delete", methods=["POST"])
def delete_project(platform_slug, project_slug):
    db = get_db()
    project = get_project(db, platform_slug, project_slug)
    if project:
        db.execute("DELETE FROM projects WHERE id = ?", (project["id"],))
        db.commit()
        flash("Progetto eliminato.", "ok")
    db.close()
    return redirect(url_for("platform_detail", platform_slug=platform_slug))


@app.route("/platform/<platform_slug>/project/<project_slug>")
def project_detail(platform_slug, project_slug):
    db = get_db()
    project = get_project(db, platform_slug, project_slug)
    if not project:
        db.close()
        flash("Progetto non trovato.", "error")
        return redirect(url_for("index"))
    platforms = db.execute("SELECT * FROM platforms ORDER BY name").fetchall()
    pages = db.execute("""
        SELECT p.*,
          (SELECT COUNT(*) FROM components c WHERE c.page_id = p.id) AS n_componenti,
          (SELECT COUNT(*) FROM evaluations e JOIN components c ON c.id = e.component_id
             WHERE c.page_id = p.id AND e.status = 'non_conforme') AS n_anomalie,
          (SELECT COUNT(*) FROM evaluations e JOIN components c ON c.id = e.component_id
             WHERE c.page_id = p.id AND e.status = 'da_verificare') AS n_da_verificare
        FROM pages p WHERE p.project_id = ? ORDER BY p.created_at""", (project["id"],)).fetchall()
    stats = project_stats(db, project["id"])
    db.close()
    return render_template("project.html", project=project, pages=pages,
                           stats=stats, platforms=platforms)


@app.route("/platform/<platform_slug>/project/<project_slug>/pages/new", methods=["POST"])
def new_page(platform_slug, project_slug):
    db = get_db()
    project = get_project(db, platform_slug, project_slug)
    if not project:
        db.close()
        flash("Progetto non trovato.", "error")
        return redirect(url_for("index"))
    name = request.form.get("name", "").strip()
    if name:
        db.execute("INSERT INTO pages (project_id, name, url, notes) VALUES (?, ?, ?, ?)",
                   (project["id"], name, request.form.get("url", "").strip(),
                    request.form.get("notes", "").strip()))
        db.commit()
        flash(f"Pagina «{name}» aggiunta.", "ok")
    else:
        flash("Il nome della pagina è obbligatorio.", "error")
    db.close()
    return redirect(url_for("project_detail", platform_slug=platform_slug, project_slug=project_slug))
