# -*- coding: utf-8 -*-
"""Route per il dettaglio pagina e la gestione dei suoi componenti."""
import json
import os

from flask import flash, jsonify, redirect, render_template, request, send_file, url_for

from database import get_db
from extensions import app
from scanner.store import shot_path


@app.route("/pagine/<int:page_id>/elimina", methods=["POST"])
def delete_page(page_id):
    db = get_db()
    row = db.execute("""SELECT pr.slug AS project_slug, pl.slug AS platform_slug
                        FROM pages p JOIN projects pr ON pr.id = p.project_id
                        JOIN platforms pl ON pl.id = pr.platform_id
                        WHERE p.id = ?""", (page_id,)).fetchone()
    db.execute("DELETE FROM pages WHERE id = ?", (page_id,))
    db.commit()
    db.close()
    flash("Pagina eliminata.", "ok")
    return redirect(url_for("project_detail", platform_slug=row["platform_slug"],
                            project_slug=row["project_slug"]) if row else url_for("index"))


@app.route("/pagine/<int:page_id>")
def page_detail(page_id):
    db = get_db()
    page = db.execute("""SELECT p.*, pr.name AS project_name, pr.id AS project_id,
                                pr.slug AS project_slug, pl.slug AS platform_slug
                         FROM pages p JOIN projects pr ON pr.id = p.project_id
                         JOIN platforms pl ON pl.id = pr.platform_id
                         WHERE p.id = ?""", (page_id,)).fetchone()
    if not page:
        db.close()
        flash("Pagina non trovata.", "error")
        return redirect(url_for("index"))
    components = db.execute("""
        SELECT c.*, t.name AS type_name,
          (SELECT COUNT(*) FROM evaluations e WHERE e.component_id = c.id) AS n_criteri,
          (SELECT COUNT(*) FROM evaluations e WHERE e.component_id = c.id AND e.status = 'conforme') AS n_conformi,
          (SELECT COUNT(*) FROM evaluations e WHERE e.component_id = c.id AND e.status = 'non_conforme') AS n_anomalie,
          (SELECT COUNT(*) FROM evaluations e WHERE e.component_id = c.id AND e.status = 'da_verificare') AS n_da_verificare
        FROM components c JOIN component_types t ON t.id = c.component_type_id
        WHERE c.page_id = ? ORDER BY c.created_at""", (page_id,)).fetchall()
    types = db.execute("SELECT * FROM component_types ORDER BY name").fetchall()
    shot = _shot_map(db, page)
    db.close()
    return render_template("page.html", page=page, components=components, types=types, shot=shot)


def _shot_map(db, page):
    """Riquadri dello screenshot con i dati dei componenti (anche quelli del layout comune su altre pagine)."""
    if not page["shot"] or not os.path.exists(shot_path(page["id"])):
        return None
    shot = json.loads(page["shot"])
    ids = sorted({b["id"] for b in shot["boxes"]})
    comps = {r["id"]: dict(r) for r in db.execute(f"""
        SELECT c.id, c.name, c.source, c.location, t.name AS type_name,
          (SELECT GROUP_CONCAT(cr.code, ' ') FROM evaluations e JOIN criteria cr ON cr.id = e.criterion_id
           WHERE e.component_id = c.id AND e.status = 'non_conforme') AS anomalie
        FROM components c JOIN component_types t ON t.id = c.component_type_id
        WHERE c.id IN ({','.join('?' * len(ids))})""", ids)} if ids else {}
    # i riquadri grandi sotto, i piccoli sopra: restano tutti cliccabili
    shot["boxes"] = sorted(({**b, **comps[b["id"]]} for b in shot["boxes"] if b["id"] in comps),
                           key=lambda b: -b["rect"]["w"] * b["rect"]["h"])
    return shot


@app.route("/pagine/<int:page_id>/screenshot")
def page_screenshot(page_id):
    return send_file(shot_path(page_id), mimetype="image/jpeg") if os.path.exists(shot_path(page_id)) else ("", 404)


@app.route("/pagine/<int:page_id>/mappa.json")
def page_map(page_id):
    """Mappa elemento ↔ componente ↔ criteri, per Playwright o un agente AI che deve correggere la pagina."""
    db = get_db()
    page = db.execute("SELECT * FROM pages WHERE id = ?", (page_id,)).fetchone()
    shot = _shot_map(db, page) if page else None
    db.close()
    if not shot:
        return jsonify(error="Nessuna mappa: esegui l'analisi live di questa pagina."), 404
    comps = {}
    for b in shot["boxes"]:
        c = comps.setdefault(b["id"], {
            "id": b["id"], "nome": b["name"], "tipologia": b["type_name"],
            "componente_codice": b["source"], "file": b["location"] if b["source"] else None,
            "non_conformi": (b["anomalie"] or "").split(),
            "url": url_for("component_detail", component_id=b["id"], _external=True), "elementi": []})
        c["elementi"].append({"selettore": b["sel"], "riquadro": b["rect"]})
    return jsonify(pagina={"id": page["id"], "nome": page["name"], "url": page["url"], "rotta": page["route"]},
                   screenshot=url_for("page_screenshot", page_id=page_id, _external=True),
                   dimensioni={"w": shot["w"], "h": shot["h"]}, componenti=list(comps.values()))


@app.route("/pagine/<int:page_id>/componenti/nuovo", methods=["POST"])
def new_component(page_id):
    name = request.form.get("name", "").strip()
    type_id = request.form.get("component_type_id")
    if not name or not type_id:
        flash("Nome e tipologia del componente sono obbligatori.", "error")
        return redirect(url_for("page_detail", page_id=page_id))
    db = get_db()
    cur = db.execute(
        "INSERT INTO components (page_id, component_type_id, name, location, notes) VALUES (?, ?, ?, ?, ?)",
        (page_id, type_id, name, request.form.get("location", "").strip(),
         request.form.get("notes", "").strip()))
    comp_id = cur.lastrowid
    # Genera automaticamente le valutazioni per i criteri applicabili alla tipologia
    include_aaa = 1 if request.form.get("include_aaa") else 0
    db.execute("""INSERT INTO evaluations (component_id, criterion_id)
                  SELECT ?, ctc.criterion_id FROM component_type_criteria ctc
                  JOIN criteria cr ON cr.id = ctc.criterion_id
                  WHERE ctc.component_type_id = ? AND (? = 1 OR cr.level != 'AAA')""",
               (comp_id, type_id, include_aaa))
    db.commit()
    db.close()
    flash(f"Componente «{name}» aggiunto con la checklist dei criteri applicabili.", "ok")
    return redirect(url_for("component_detail", component_id=comp_id))


@app.route("/componenti/<int:component_id>/elimina", methods=["POST"])
def delete_component(component_id):
    db = get_db()
    row = db.execute("SELECT page_id FROM components WHERE id = ?", (component_id,)).fetchone()
    db.execute("DELETE FROM components WHERE id = ?", (component_id,))
    db.commit()
    db.close()
    flash("Componente eliminato.", "ok")
    return redirect(url_for("page_detail", page_id=row["page_id"]) if row else url_for("index"))
