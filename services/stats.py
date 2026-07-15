# -*- coding: utf-8 -*-
"""Calcolo delle statistiche di conformità per progetti e piattaforme."""

STATS_SELECT = """
    SELECT
      COUNT(e.id) AS totale,
      SUM(e.status = 'conforme') AS conformi,
      SUM(e.status = 'non_conforme') AS non_conformi,
      SUM(e.status = 'da_verificare') AS da_verificare,
      SUM(e.status = 'non_applicabile') AS non_applicabili,
      SUM(e.status = 'non_conforme' AND e.work_status IN ('risolta', 'verificata')) AS risolte,
      SUM(e.status = 'non_conforme' AND cr.level = 'AAA') AS non_conformi_aaa
    FROM evaluations e
    JOIN criteria cr ON cr.id = e.criterion_id
    JOIN components c ON c.id = e.component_id
    JOIN pages p ON p.id = c.page_id
    JOIN projects pr ON pr.id = p.project_id
"""

# Conformità per criterio distinto sul totale dei criteri A/AA esistenti (non sulle
# rilevazioni): un criterio conta una sola volta per l'intero progetto/piattaforma
# anche se violato in più componenti, e i criteri mai rilevati si assumono conformi.
CRITERIA_NON_CONFORMI_SELECT = """
    SELECT COUNT(DISTINCT cr.id) AS n
    FROM evaluations e
    JOIN criteria cr ON cr.id = e.criterion_id
    JOIN components c ON c.id = e.component_id
    JOIN pages p ON p.id = c.page_id
    JOIN projects pr ON pr.id = p.project_id
    WHERE cr.level != 'AAA' AND e.status = 'non_conforme' AND {where}
"""


def _finish_stats(row):
    s = dict(row)
    for k in s:
        s[k] = s[k] or 0
    s["pct_avanzamento"] = round(100 * (s["totale"] - s["da_verificare"]) / s["totale"]) if s["totale"] else 0
    return s


def _pct_conformi(db, where, params):
    totale_aa = db.execute("SELECT COUNT(*) FROM criteria WHERE level != 'AAA'").fetchone()[0]
    non_conformi = db.execute(CRITERIA_NON_CONFORMI_SELECT.format(where=where), params).fetchone()["n"]
    return round(100 * (totale_aa - non_conformi) / totale_aa) if totale_aa else 0


def project_stats(db, project_id):
    s = _finish_stats(db.execute(STATS_SELECT + " WHERE p.project_id = ?", (project_id,)).fetchone())
    s["pct_conformi"] = _pct_conformi(db, "p.project_id = ?", (project_id,))
    return s


def platform_stats(db, platform_id):
    s = _finish_stats(db.execute(STATS_SELECT + " WHERE pr.platform_id = ?", (platform_id,)).fetchone())
    s["pct_conformi"] = _pct_conformi(db, "pr.platform_id = ?", (platform_id,))
    return s
