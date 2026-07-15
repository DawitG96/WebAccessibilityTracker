# -*- coding: utf-8 -*-
"""Dashboard principale (elenco piattaforme)."""
from flask import render_template

from database import get_db
from extensions import app
from services.stats import platform_stats


@app.route("/")
def index():
    db = get_db()
    platforms = db.execute("SELECT * FROM platforms ORDER BY name").fetchall()
    agg = {pl["id"]: platform_stats(db, pl["id"]) for pl in platforms}
    counts = {pl["id"]: db.execute(
        "SELECT COUNT(*) FROM projects WHERE platform_id = ?", (pl["id"],)).fetchone()[0]
        for pl in platforms}
    db.close()
    return render_template("index.html", platforms=platforms, agg=agg,
                           project_counts=counts)
