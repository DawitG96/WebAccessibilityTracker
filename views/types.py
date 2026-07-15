# -*- coding: utf-8 -*-
"""Route per le tipologie di componente e l'elenco dei criteri WCAG."""
from flask import flash, redirect, render_template, request, url_for

from database import get_db
from extensions import app


@app.route("/tipologie")
def types_list():
    db = get_db()
    types = db.execute("""
        SELECT t.*, (SELECT COUNT(*) FROM component_type_criteria x
                     WHERE x.component_type_id = t.id) AS n_criteri
        FROM component_types t ORDER BY t.name""").fetchall()
    db.close()
    return render_template("tipologie.html", types=types)


@app.route("/tipologie/nuova", methods=["GET", "POST"])
@app.route("/tipologie/<int:type_id>", methods=["GET", "POST"])
def type_form(type_id=None):
    db = get_db()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Il nome della tipologia è obbligatorio.", "error")
            db.close()
            return redirect(url_for("types_list"))
        desc = request.form.get("description", "").strip()
        aria = request.form.get("aria_notes", "").strip()
        if type_id is None:
            cur = db.execute("INSERT INTO component_types (name, description, aria_notes) VALUES (?, ?, ?)",
                             (name, desc, aria))
            type_id = cur.lastrowid
        else:
            db.execute("UPDATE component_types SET name = ?, description = ?, aria_notes = ? WHERE id = ?",
                       (name, desc, aria, type_id))
            db.execute("DELETE FROM component_type_criteria WHERE component_type_id = ?", (type_id,))
        for cid in request.form.getlist("criteria"):
            db.execute("INSERT OR IGNORE INTO component_type_criteria VALUES (?, ?)", (type_id, cid))
        db.commit()
        db.close()
        flash("Tipologia salvata.", "ok")
        return redirect(url_for("types_list"))

    ctype = db.execute("SELECT * FROM component_types WHERE id = ?", (type_id,)).fetchone() if type_id else None
    selected = {r["criterion_id"] for r in db.execute(
        "SELECT criterion_id FROM component_type_criteria WHERE component_type_id = ?",
        (type_id,)).fetchall()} if type_id else set()
    criteria = db.execute("SELECT * FROM criteria ORDER BY sort_order").fetchall()
    db.close()
    return render_template("tipologia_form.html", ctype=ctype, criteria=criteria, selected=selected)


@app.route("/criteri")
def criteria_list():
    db = get_db()
    livello = request.args.get("livello", "").upper()
    if livello not in ("A", "AA", "AAA"):
        livello = ""
    query = "SELECT * FROM criteria"
    params = ()
    if livello:
        query += " WHERE level = ?"
        params = (livello,)
    criteria = db.execute(query + " ORDER BY sort_order", params).fetchall()
    counts = {r["level"]: r["n"] for r in
             db.execute("SELECT level, COUNT(*) AS n FROM criteria GROUP BY level").fetchall()}
    db.close()
    return render_template("criteri.html", criteria=criteria, livello=livello, counts=counts)


@app.route("/tipologie/<int:type_id>/elimina", methods=["POST"])
def delete_type(type_id):
    db = get_db()
    used = db.execute("SELECT COUNT(*) FROM components WHERE component_type_id = ?", (type_id,)).fetchone()[0]
    if used:
        flash("Impossibile eliminare: la tipologia è usata da componenti esistenti.", "error")
    else:
        db.execute("DELETE FROM component_types WHERE id = ?", (type_id,))
        db.commit()
        flash("Tipologia eliminata.", "ok")
    db.close()
    return redirect(url_for("types_list"))
