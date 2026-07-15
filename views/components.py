# -*- coding: utf-8 -*-
"""Route per il dettaglio componente e la relativa checklist di valutazioni WCAG."""
from flask import flash, redirect, render_template, request, url_for

from database import get_db
from extensions import app


@app.route("/componenti/<int:component_id>")
def component_detail(component_id):
    db = get_db()
    comp = db.execute("""
        SELECT c.*, t.name AS type_name, t.aria_notes,
               p.name AS page_name, p.id AS page_id,
               pr.name AS project_name, pr.id AS project_id,
               pr.slug AS project_slug, pl.slug AS platform_slug
        FROM components c
        JOIN component_types t ON t.id = c.component_type_id
        JOIN pages p ON p.id = c.page_id
        JOIN projects pr ON pr.id = p.project_id
        JOIN platforms pl ON pl.id = pr.platform_id
        WHERE c.id = ?""", (component_id,)).fetchone()
    if not comp:
        db.close()
        flash("Componente non trovato.", "error")
        return redirect(url_for("index"))
    evals = db.execute("""
        SELECT e.*, cr.code, cr.title, cr.level, cr.principle, cr.anchor
        FROM evaluations e JOIN criteria cr ON cr.id = e.criterion_id
        WHERE e.component_id = ? ORDER BY cr.sort_order""", (component_id,)).fetchall()
    remaining = db.execute("""
        SELECT * FROM criteria WHERE id NOT IN
          (SELECT criterion_id FROM evaluations WHERE component_id = ?)
        ORDER BY sort_order""", (component_id,)).fetchall()
    hist = db.execute("""
        SELECT h.*, cr.code FROM history h
        JOIN evaluations e ON e.id = h.evaluation_id
        JOIN criteria cr ON cr.id = e.criterion_id
        WHERE e.component_id = ? ORDER BY h.changed_at DESC LIMIT 20""", (component_id,)).fetchall()
    db.close()
    return render_template("component.html", comp=comp, evals=evals,
                           remaining=remaining, history=hist)


@app.route("/componenti/<int:component_id>/valutazioni", methods=["POST"])
def save_evaluations(component_id):
    db = get_db()
    evals = db.execute("SELECT * FROM evaluations WHERE component_id = ?", (component_id,)).fetchall()
    changed = 0
    for e in evals:
        new_status = request.form.get(f"status_{e['id']}", e["status"])
        new_work = request.form.get(f"work_{e['id']}", e["work_status"])
        new_note = request.form.get(f"note_{e['id']}", e["note"]).strip()
        if new_status != "non_conforme":
            new_work = ""
        elif new_status == "non_conforme" and not new_work:
            new_work = "aperta"
        if (new_status, new_work, new_note) != (e["status"], e["work_status"], e["note"]):
            if (new_status, new_work) != (e["status"], e["work_status"]):
                db.execute("""INSERT INTO history (evaluation_id, old_status, new_status,
                              old_work_status, new_work_status, note)
                              VALUES (?, ?, ?, ?, ?, ?)""",
                           (e["id"], e["status"], new_status, e["work_status"], new_work, new_note))
            db.execute("""UPDATE evaluations SET status = ?, work_status = ?, note = ?,
                          updated_at = datetime('now', 'localtime') WHERE id = ?""",
                       (new_status, new_work, new_note, e["id"]))
            changed += 1
    db.commit()
    db.close()
    flash(f"Valutazioni salvate ({changed} aggiornate)." if changed else "Nessuna modifica da salvare.", "ok")
    return redirect(url_for("component_detail", component_id=component_id))


@app.route("/componenti/<int:component_id>/aggiungi-criterio", methods=["POST"])
def add_criterion(component_id):
    crit_id = request.form.get("criterion_id")
    if crit_id:
        db = get_db()
        db.execute("INSERT OR IGNORE INTO evaluations (component_id, criterion_id) VALUES (?, ?)",
                   (component_id, crit_id))
        db.commit()
        db.close()
        flash("Criterio aggiunto alla checklist.", "ok")
    return redirect(url_for("component_detail", component_id=component_id))


@app.route("/valutazioni/<int:eval_id>/rimuovi", methods=["POST"])
def remove_evaluation(eval_id):
    db = get_db()
    row = db.execute("SELECT component_id FROM evaluations WHERE id = ?", (eval_id,)).fetchone()
    db.execute("DELETE FROM evaluations WHERE id = ?", (eval_id,))
    db.commit()
    db.close()
    flash("Criterio rimosso dalla checklist.", "ok")
    return redirect(url_for("component_detail", component_id=row["component_id"]) if row else url_for("index"))
