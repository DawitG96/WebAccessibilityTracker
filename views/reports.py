# -*- coding: utf-8 -*-
"""Route per il report anomalie di progetto e le esportazioni CSV/XLSX."""
from datetime import datetime

from flask import redirect, render_template, send_file, url_for

from database import get_db
from extensions import app
from services import reports as reports_service
from services.lookups import get_project
from services.stats import project_stats


@app.route("/platform/<platform_slug>/project/<project_slug>/report")
def report(platform_slug, project_slug):
    db = get_db()
    project = get_project(db, platform_slug, project_slug)
    if not project:
        db.close()
        return redirect(url_for("index"))
    project_id = project["id"]
    anomalies = reports_service.report_data(db, project_id)
    stats = project_stats(db, project_id)
    histories = reports_service.evaluation_histories(db, anomalies)
    violated = reports_service.violated_criteria(db, project_id)
    db.close()
    return render_template("report.html", project=project, anomalies=anomalies,
                           stats=stats, histories=histories, violated=violated,
                           generated=datetime.now().strftime("%d/%m/%Y %H:%M"))


@app.route("/platform/<platform_slug>/project/<project_slug>/export.csv")
def export_csv(platform_slug, project_slug):
    db = get_db()
    project = get_project(db, platform_slug, project_slug)
    if not project:
        db.close()
        return redirect(url_for("index"))
    anomalies = reports_service.report_data(db, project["id"])
    db.close()
    data, fname = reports_service.build_csv(project, anomalies)
    return send_file(data, mimetype="text/csv", as_attachment=True, download_name=fname)


@app.route("/platform/<platform_slug>/project/<project_slug>/export.xlsx")
def export_xlsx(platform_slug, project_slug):
    db = get_db()
    project = get_project(db, platform_slug, project_slug)
    if not project:
        db.close()
        return redirect(url_for("index"))
    project_id = project["id"]
    anomalies = reports_service.report_data(db, project_id)
    all_rows = reports_service.all_evaluations(db, project_id)
    db.close()
    buf, fname = reports_service.build_xlsx(project, anomalies, all_rows)
    return send_file(buf, as_attachment=True, download_name=fname,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
