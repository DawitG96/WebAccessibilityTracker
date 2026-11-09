# -*- coding: utf-8 -*-
"""Importa i risultati di un'analisi automatica (live o statica) nel database del tracker."""
from datetime import datetime

MAX_NOTE_ITEMS = 15


def _note(items):
    lines = [f"• {n}" for n in dict.fromkeys(items)]
    extra = len(lines) - MAX_NOTE_ITEMS
    return "\n".join(lines[:MAX_NOTE_ITEMS]) + (f"\n… e altre {extra} occorrenze" if extra > 0 else "")


def import_results(db, project_id, pages, source):
    """Crea/aggiorna pagine, componenti (con checklist della tipologia) e non conformità.

    Le valutazioni già marcate a mano come conformi o non applicabili non vengono sovrascritte.
    """
    stamp = datetime.now().strftime("%d/%m/%Y %H:%M")
    types = {r["name"]: r["id"] for r in db.execute("SELECT id, name FROM component_types")}
    criteria = {r["code"]: r["id"] for r in db.execute("SELECT id, code FROM criteria")}
    stats = {"pagine": 0, "componenti": 0, "anomalie": 0, "ignorate": 0}

    for p in pages:
        row = db.execute("SELECT id FROM pages WHERE project_id = ? AND url = ?", (project_id, p["url"])).fetchone()
        if row:
            page_id = row["id"]
        else:
            page_id = db.execute("INSERT INTO pages (project_id, name, url, notes) VALUES (?, ?, ?, ?)",
                                 (project_id, p["name"], p["url"], p.get("notes", ""))).lastrowid
            stats["pagine"] += 1

        for c in p["components"]:
            type_id = types.get(c["type"]) or types["Altro / Generico"]
            row = db.execute("""SELECT id FROM components WHERE page_id = ? AND component_type_id = ?
                                AND name = ? AND location = ?""",
                             (page_id, type_id, c["name"], c["location"])).fetchone()
            if row:
                comp_id = row["id"]
            else:
                comp_id = db.execute(
                    "INSERT INTO components (page_id, component_type_id, name, location, notes) VALUES (?, ?, ?, ?, ?)",
                    (page_id, type_id, c["name"], c["location"], f"Rilevato automaticamente ({source}, {stamp})")
                ).lastrowid
                db.execute("""INSERT INTO evaluations (component_id, criterion_id)
                              SELECT ?, ctc.criterion_id FROM component_type_criteria ctc
                              JOIN criteria cr ON cr.id = ctc.criterion_id
                              WHERE ctc.component_type_id = ? AND cr.level != 'AAA'""", (comp_id, type_id))
                stats["componenti"] += 1

            by_code = {}
            for f in c["findings"]:
                if f["code"] in criteria:
                    by_code.setdefault(f["code"], []).append(f["note"])
            for code, notes in by_code.items():
                db.execute("INSERT OR IGNORE INTO evaluations (component_id, criterion_id) VALUES (?, ?)",
                           (comp_id, criteria[code]))
                e = db.execute("SELECT * FROM evaluations WHERE component_id = ? AND criterion_id = ?",
                               (comp_id, criteria[code])).fetchone()
                if e["status"] in ("conforme", "non_applicabile"):
                    stats["ignorate"] += 1
                    continue
                note = f"[Analisi automatica {source}, {stamp}]\n{_note(notes)}"
                work = e["work_status"] if e["status"] == "non_conforme" and e["work_status"] else "aperta"
                if e["status"] != "non_conforme":
                    db.execute("""INSERT INTO history (evaluation_id, old_status, new_status,
                                  old_work_status, new_work_status, note) VALUES (?, ?, ?, ?, ?, ?)""",
                               (e["id"], e["status"], "non_conforme", e["work_status"], work,
                                f"Analisi automatica ({source})"))
                db.execute("""UPDATE evaluations SET status = 'non_conforme', work_status = ?, note = ?,
                              updated_at = datetime('now', 'localtime') WHERE id = ?""", (work, note, e["id"]))
                stats["anomalie"] += 1
    db.commit()
    return stats
