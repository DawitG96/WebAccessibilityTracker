# -*- coding: utf-8 -*-
"""Route CRUD per le piattaforme e per la creazione di progetti al loro interno."""
from flask import flash, redirect, render_template, request, url_for

from database import get_db, unique_slug
from extensions import app
from services.lookups import get_platform
from services.stats import platform_stats, project_stats


@app.route("/platform", methods=["POST"])
def new_platform():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Il nome della piattaforma è obbligatorio.", "error")
        return redirect(url_for("index"))
    db = get_db()
    slug = unique_slug(db, "platforms", name, fallback="piattaforma")
    db.execute("INSERT INTO platforms (name, slug, description) VALUES (?, ?, ?)",
               (name, slug, request.form.get("description", "").strip()))
    db.commit()
    db.close()
    flash(f"Piattaforma «{name}» creata. Ora crea il suo primo progetto.", "ok")
    return redirect(url_for("platform_detail", platform_slug=slug))


@app.route("/platform/<platform_slug>")
def platform_detail(platform_slug):
    db = get_db()
    platform = get_platform(db, platform_slug)
    if not platform:
        db.close()
        flash("Piattaforma non trovata.", "error")
        return redirect(url_for("index"))
    projects = db.execute("SELECT * FROM projects WHERE platform_id = ? ORDER BY created_at",
                          (platform["id"],)).fetchall()
    stats = {p["id"]: project_stats(db, p["id"]) for p in projects}
    agg = platform_stats(db, platform["id"])
    db.close()
    return render_template("platform.html", platform=platform, projects=projects,
                           stats=stats, agg=agg)


@app.route("/platform/<platform_slug>/edit", methods=["POST"])
def edit_platform(platform_slug):
    db = get_db()
    platform = get_platform(db, platform_slug)
    if not platform:
        db.close()
        flash("Piattaforma non trovata.", "error")
        return redirect(url_for("index"))
    name = request.form.get("name", "").strip() or "Senza nome"
    slug = platform["slug"]
    if name != platform["name"]:
        slug = unique_slug(db, "platforms", name, exclude_id=platform["id"], fallback="piattaforma")
    db.execute("UPDATE platforms SET name = ?, slug = ?, description = ? WHERE id = ?",
               (name, slug, request.form.get("description", "").strip(), platform["id"]))
    db.commit()
    db.close()
    flash("Piattaforma aggiornata.", "ok")
    return redirect(url_for("platform_detail", platform_slug=slug))


@app.route("/platform/<platform_slug>/delete", methods=["POST"])
def delete_platform(platform_slug):
    db = get_db()
    platform = get_platform(db, platform_slug)
    if not platform:
        db.close()
        flash("Piattaforma non trovata.", "error")
        return redirect(url_for("index"))
    n = db.execute("SELECT COUNT(*) FROM projects WHERE platform_id = ?", (platform["id"],)).fetchone()[0]
    if n:
        db.close()
        flash(f"Impossibile eliminare: la piattaforma contiene {n} progetti. "
              "Elimina o sposta prima i progetti.", "error")
        return redirect(url_for("platform_detail", platform_slug=platform_slug))
    db.execute("DELETE FROM platforms WHERE id = ?", (platform["id"],))
    db.commit()
    db.close()
    flash("Piattaforma eliminata.", "ok")
    return redirect(url_for("index"))


@app.route("/platform/<platform_slug>/project", methods=["POST"])
def new_project(platform_slug):
    db = get_db()
    platform = get_platform(db, platform_slug)
    if not platform:
        db.close()
        flash("Piattaforma non trovata.", "error")
        return redirect(url_for("index"))
    name = request.form.get("name", "").strip()
    if not name:
        db.close()
        flash("Il nome del progetto è obbligatorio.", "error")
        return redirect(url_for("platform_detail", platform_slug=platform_slug))
    slug = unique_slug(db, "projects", name, "platform_id", platform["id"], fallback="progetto")
    db.execute(
        "INSERT INTO projects (name, slug, description, url, platform_id) VALUES (?, ?, ?, ?, ?)",
        (name, slug, request.form.get("description", "").strip(),
         request.form.get("url", "").strip(), platform["id"]))
    db.commit()
    db.close()
    flash(f"Progetto «{name}» creato.", "ok")
    return redirect(url_for("project_detail", platform_slug=platform_slug, project_slug=slug))
