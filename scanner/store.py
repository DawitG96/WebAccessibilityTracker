# -*- coding: utf-8 -*-
"""Importa i risultati di un'analisi automatica (live o statica) nel database del tracker.

L'analisi live si aggancia a quanto già trovato dal codice: le pagine vengono associate alle
rotte, i componenti ai componenti del codice (stesso tag/classe nel DOM) e le rilevazioni del
codice vengono confermate o smentite dal comportamento reale.
"""
import re
from datetime import datetime
from urllib.parse import urlparse

MAX_NOTE_ITEMS = 15
GENERIC = "Altro / Generico"


def _note(items):
    lines = [f"• {n}" for n in dict.fromkeys(items)]
    extra = len(lines) - MAX_NOTE_ITEMS
    return "\n".join(lines[:MAX_NOTE_ITEMS]) + (f"\n… e altre {extra} occorrenze" if extra > 0 else "")


def _merge_note(old, source, block):
    """Sostituisce il blocco della stessa analisi, tiene quelli dell'altra analisi e il testo scritto a mano."""
    keep = [b.strip() for b in re.split(r"(?=\[Analisi automatica )", old or "")
            if b.strip() and not b.startswith(f"[Analisi automatica {source}")]
    return "\n\n".join([block] + keep)


def match_route(path, routes):
    """Rotta del codice più specifica per il percorso (/news/42 → /news/:id), o None."""
    def rx(route):
        parts = [".*" if p.startswith("*") else "[^/]+" if p.startswith(":") else re.escape(p)
                 for p in route.strip("/").split("/") if p]
        return "/" + "/".join(parts) + "/?"
    hits = [r for r in routes or [] if re.fullmatch(rx(r), path or "/")]
    return min(hits, key=lambda r: (10 * r.count("*") + r.count(":"), -len(r)), default=None)


def norm(name):
    return re.sub(r"[^a-z0-9]", "", (name or "").lower())


def code_sources(db, project_id):
    """Rotte e nomi dei componenti trovati dall'analisi del codice, per guidare l'analisi live."""
    routes = [r["route"] for r in db.execute(
        "SELECT route FROM pages WHERE project_id = ? AND route IS NOT NULL", (project_id,))]
    names = [r["source"] for r in db.execute(
        """SELECT DISTINCT c.source FROM components c JOIN pages p ON p.id = c.page_id
           WHERE p.project_id = ? AND c.source IS NOT NULL""", (project_id,))]
    return routes, names


def _history(db, e, status, work, note):
    db.execute("""INSERT INTO history (evaluation_id, old_status, new_status,
                  old_work_status, new_work_status, note) VALUES (?, ?, ?, ?, ?, ?)""",
               (e["id"], e["status"], status, e["work_status"], work, note))


def _apply(db, comp_id, by_code, source, stamp, criteria, stats):
    """Marca non conformi i criteri rilevati; non tocca quelli già valutati a mano come conformi/N.A."""
    for code, notes in by_code.items():
        if code not in criteria:
            continue
        db.execute("INSERT OR IGNORE INTO evaluations (component_id, criterion_id) VALUES (?, ?)",
                   (comp_id, criteria[code]))
        e = db.execute("SELECT * FROM evaluations WHERE component_id = ? AND criterion_id = ?",
                       (comp_id, criteria[code])).fetchone()
        if e["status"] in ("conforme", "non_applicabile"):
            stats["ignorate"] += 1
            continue
        other = "codice" if source == "live" else "live"
        confirmed = e["status"] == "non_conforme" and f"[Analisi automatica {other}" in (e["note"] or "")
        head = f"[Analisi automatica {source}, {stamp}]" + (f" — conferma la rilevazione {other}" if confirmed else "")
        note = _merge_note(e["note"], source, f"{head}\n{_note(notes)}")
        work = e["work_status"] if e["status"] == "non_conforme" and e["work_status"] else "aperta"
        if e["status"] != "non_conforme":
            _history(db, e, "non_conforme", work, f"Analisi automatica ({source})")
        db.execute("""UPDATE evaluations SET status = 'non_conforme', work_status = ?, note = ?,
                      updated_at = datetime('now', 'localtime') WHERE id = ?""", (work, note, e["id"]))
        stats["anomalie"] += 1
        stats["confermate"] += confirmed


def _refute(db, comp_id, codes, stamp, criteria, stats):
    """Rilevazioni del codice che il live ha verificato senza violazioni tornano «da verificare»."""
    for code in codes:
        if code not in criteria:
            continue
        e = db.execute("""SELECT * FROM evaluations WHERE component_id = ? AND criterion_id = ?
                          AND status = 'non_conforme' AND work_status = 'aperta'""",
                       (comp_id, criteria[code])).fetchone()
        if not e or "[Analisi automatica codice" not in (e["note"] or ""):
            continue
        note = _merge_note(e["note"], "live", f"[Analisi automatica live, {stamp}] — non confermata: sul sito "
                                              "il criterio è stato verificato su questo componente senza violazioni. "
                                              "Controlla a mano.")
        _history(db, e, "da_verificare", "", "Rilevazione del codice non confermata dall'analisi live")
        db.execute("""UPDATE evaluations SET status = 'da_verificare', work_status = '', note = ?,
                      updated_at = datetime('now', 'localtime') WHERE id = ?""", (note, e["id"]))
        stats["smentite"] += 1


def _add_type_criteria(db, comp_id, type_id):
    db.execute("""INSERT OR IGNORE INTO evaluations (component_id, criterion_id)
                  SELECT ?, ctc.criterion_id FROM component_type_criteria ctc
                  JOIN criteria cr ON cr.id = ctc.criterion_id
                  WHERE ctc.component_type_id = ? AND cr.level != 'AAA'""", (comp_id, type_id))


def _page_id(db, project_id, p, stats):
    if p.get("route"):
        row = db.execute("SELECT * FROM pages WHERE project_id = ? AND route = ?", (project_id, p["route"])).fetchone()
        if row:
            if not p["url"].startswith("codice:") and row["url"].startswith("codice:"):
                # la pagina del codice prende l'URL reale e il nome della rotta
                db.execute("UPDATE pages SET url = ?, name = ? WHERE id = ?", (p["url"], p["route"], row["id"]))
            return row["id"]
        if p["url"].startswith("codice:"):
            # rotta già analizzata dal live senza codice: la pagina live diventa la pagina della rotta
            for r in db.execute("SELECT id, url FROM pages WHERE project_id = ? AND route IS NULL AND url LIKE 'http%'",
                                (project_id,)).fetchall():
                if match_route(urlparse(r["url"]).path, [p["route"]]):
                    db.execute("UPDATE pages SET route = ?, name = ? WHERE id = ?", (p["route"], p["route"], r["id"]))
                    return r["id"]
    row = db.execute("SELECT id FROM pages WHERE project_id = ? AND url = ?", (project_id, p["url"])).fetchone()
    if row:
        return row["id"]
    stats["pagine"] += 1
    return db.execute("INSERT INTO pages (project_id, name, url, notes, route) VALUES (?, ?, ?, ?, ?)",
                      (project_id, p["name"], p["url"], p.get("notes", ""), p.get("route"))).lastrowid


def _code_candidates(db, project_id, page_id):
    """Componenti del codice visibili su una pagina: quelli della rotta e quelli del layout comune."""
    rows = db.execute("""SELECT c.*, ct.name AS type_name FROM components c
                         JOIN pages p ON p.id = c.page_id JOIN component_types ct ON ct.id = c.component_type_id
                         WHERE p.project_id = ? AND c.source IS NOT NULL
                           AND (c.page_id = ? OR (p.route IS NULL AND p.url LIKE 'codice:%'))
                         ORDER BY c.page_id = ?""", (project_id, page_id, page_id))
    return {norm(r["source"]): r for r in rows}  # quelli della pagina vincono (ordinati per ultimi)


def _human(label):
    # ponytail: euristica, le etichette da aria-label/titoli hanno spazi o maiuscole, le classi CSS no
    return label and "«" not in label and label != "Struttura della pagina" and not re.fullmatch(r"[a-z0-9_ -]+", label)


def import_results(db, project_id, pages, source):
    """Crea/aggiorna pagine, componenti (con checklist della tipologia) e non conformità.

    Le valutazioni già marcate a mano come conformi o non applicabili non vengono sovrascritte.
    """
    stamp = datetime.now().strftime("%d/%m/%Y %H:%M")
    types = {r["name"]: r["id"] for r in db.execute("SELECT id, name FROM component_types")}
    criteria = {r["code"]: r["id"] for r in db.execute("SELECT id, code FROM criteria")}
    stats = {"pagine": 0, "componenti": 0, "anomalie": 0, "ignorate": 0, "collegati": 0,
             "confermate": 0, "smentite": 0}
    matched = {}  # componente del codice → rilevazioni e verifiche superate su tutte le pagine live

    for p in pages:
        page_id = _page_id(db, project_id, p, stats)
        cands = _code_candidates(db, project_id, page_id) if source == "live" else {}
        path = urlparse(p["url"]).path or "/"

        own = {}
        for c in p["components"]:
            target = cands.get(c.get("src") or "")
            if target is not None:
                m = matched.setdefault(target["id"], {"row": target, "findings": {}, "passed": set(), "live": []})
                where = "" if target["page_id"] == page_id else f"{path}: "
                for f in c["findings"]:
                    m["findings"].setdefault(f["code"], []).append(where + f["note"])
                m["passed"].update(c.get("passed", []))
                m["live"].append(c)
            else:
                g = own.setdefault((c["type"], c["name"], c["location"]), {**c, "findings": []})
                g["findings"] += c["findings"]

        for c in own.values():
            type_id = types.get(c["type"]) or types[GENERIC]
            if source == "codice":
                row = db.execute("SELECT id FROM components WHERE page_id = ? AND source IS NOT NULL AND location = ?",
                                 (page_id, c["location"])).fetchone()
            else:
                row = db.execute("""SELECT id FROM components WHERE page_id = ? AND component_type_id = ?
                                    AND name = ? AND location = ?""",
                                 (page_id, type_id, c["name"], c["location"])).fetchone()
            if row:
                comp_id = row["id"]
            else:
                comp_id = db.execute(
                    "INSERT INTO components (page_id, component_type_id, name, location, notes, source) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (page_id, type_id, c["name"], c["location"], f"Rilevato automaticamente ({source}, {stamp})",
                     c["name"] if source == "codice" else None)).lastrowid
                _add_type_criteria(db, comp_id, type_id)
                stats["componenti"] += 1
            by_code = {}
            for f in c["findings"]:
                by_code.setdefault(f["code"], []).append(f["note"])
            _apply(db, comp_id, by_code, source, stamp, criteria, stats)

    for comp_id, m in matched.items():
        row, roots = m["row"], [c for c in m["live"] if "«" not in c["name"] and c["type"] != "Struttura pagina / Intestazioni"]
        stats["collegati"] += 1
        if row["type_name"] == GENERIC and roots and roots[0]["type"] in types and roots[0]["type"] != GENERIC:
            db.execute("UPDATE components SET component_type_id = ? WHERE id = ?", (types[roots[0]["type"]], comp_id))
            _add_type_criteria(db, comp_id, types[roots[0]["type"]])
        label = next((c["name"] for c in roots if _human(c["name"])), None)
        if label and row["name"] == row["source"]:
            db.execute("UPDATE components SET name = ? WHERE id = ?", (f"{row['source']} — {label}", comp_id))
        _apply(db, comp_id, m["findings"], source, stamp, criteria, stats)
        _refute(db, comp_id, m["passed"] - set(m["findings"]), stamp, criteria, stats)
    db.commit()
    return stats
