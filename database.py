# -*- coding: utf-8 -*-
"""Inizializzazione, migrazione e accesso al database SQLite."""
import os
import re
import sqlite3
import unicodedata

from wcag_data import AAA_EXTRAS, COMPONENT_TYPES, CRITERIA

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "data", "tracker.db"))

SCHEMA_VERSION = 3


def slugify(text, fallback="elemento"):
    """Nome → slug URL-safe (minuscole, trattini, senza accenti)."""
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return text or fallback


def unique_slug(conn, table, name, scope_col=None, scope_val=None, exclude_id=None, fallback="elemento"):
    """Genera uno slug univoco nella tabella (eventualmente entro uno scope, es. la piattaforma)."""
    base = slugify(name, fallback)
    slug, n = base, 2
    while True:
        q, params = f"SELECT id FROM {table} WHERE slug = ?", [slug]
        if scope_col:
            q += f" AND {scope_col} = ?"
            params.append(scope_val)
        if exclude_id is not None:
            q += " AND id != ?"
            params.append(exclude_id)
        if conn.execute(q, params).fetchone() is None:
            return slug
        slug = f"{base}-{n}"
        n += 1

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS platforms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    slug TEXT,
    description TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    slug TEXT,
    description TEXT DEFAULT '',
    url TEXT DEFAULT '',
    status TEXT DEFAULT 'In corso',
    platform_id INTEGER REFERENCES platforms(id),
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    url TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS criteria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    level TEXT NOT NULL,
    principle TEXT NOT NULL,
    anchor TEXT DEFAULT '',
    sort_order INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS component_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT DEFAULT '',
    aria_notes TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS component_type_criteria (
    component_type_id INTEGER NOT NULL REFERENCES component_types(id) ON DELETE CASCADE,
    criterion_id INTEGER NOT NULL REFERENCES criteria(id) ON DELETE CASCADE,
    PRIMARY KEY (component_type_id, criterion_id)
);

CREATE TABLE IF NOT EXISTS components (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id INTEGER NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    component_type_id INTEGER NOT NULL REFERENCES component_types(id),
    name TEXT NOT NULL,
    location TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS evaluations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    component_id INTEGER NOT NULL REFERENCES components(id) ON DELETE CASCADE,
    criterion_id INTEGER NOT NULL REFERENCES criteria(id),
    status TEXT DEFAULT 'da_verificare',      -- da_verificare | conforme | non_conforme | non_applicabile
    work_status TEXT DEFAULT '',              -- per non conformità: aperta | in_lavorazione | risolta | verificata
    note TEXT DEFAULT '',
    updated_at TEXT DEFAULT (datetime('now', 'localtime')),
    UNIQUE (component_id, criterion_id)
);

CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evaluation_id INTEGER NOT NULL REFERENCES evaluations(id) ON DELETE CASCADE,
    old_status TEXT, new_status TEXT,
    old_work_status TEXT, new_work_status TEXT,
    note TEXT DEFAULT '',
    changed_at TEXT DEFAULT (datetime('now', 'localtime'))
);
"""


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _columns(conn, table):
    return {r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _get_version(conn):
    try:
        row = conn.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
        return int(row["value"]) if row else 1
    except sqlite3.OperationalError:
        return 1


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    fresh = not os.path.exists(DB_PATH) or os.path.getsize(DB_PATH) == 0
    conn = get_db()
    old_version = 0 if fresh else _get_version(conn)
    conn.executescript(SCHEMA)

    # --- Migrazioni per database creati con versioni precedenti ---
    if not fresh:
        if "platform_id" not in _columns(conn, "projects"):
            conn.execute("ALTER TABLE projects ADD COLUMN platform_id INTEGER REFERENCES platforms(id)")
        if "sort_order" not in _columns(conn, "criteria"):
            conn.execute("ALTER TABLE criteria ADD COLUMN sort_order INTEGER DEFAULT 0")
        if "slug" not in _columns(conn, "platforms"):
            conn.execute("ALTER TABLE platforms ADD COLUMN slug TEXT")
        if "slug" not in _columns(conn, "projects"):
            conn.execute("ALTER TABLE projects ADD COLUMN slug TEXT")

    # --- Migrazione v3: slug negli URL e ogni progetto appartiene a una piattaforma ---
    # I progetti rimasti senza piattaforma vengono raccolti in una piattaforma "Generale".
    orphans = conn.execute("SELECT id FROM projects WHERE platform_id IS NULL").fetchall()
    if orphans:
        row = conn.execute("SELECT id FROM platforms WHERE name = 'Generale'").fetchone()
        generale_id = row["id"] if row else conn.execute(
            "INSERT INTO platforms (name, description) VALUES ('Generale', "
            "'Piattaforma creata automaticamente per i progetti che ne erano privi.')").lastrowid
        conn.execute("UPDATE projects SET platform_id = ? WHERE platform_id IS NULL", (generale_id,))
    for r in conn.execute("SELECT id, name FROM platforms WHERE slug IS NULL OR slug = ''").fetchall():
        conn.execute("UPDATE platforms SET slug = ? WHERE id = ?",
                     (unique_slug(conn, "platforms", r["name"], fallback="piattaforma"), r["id"]))
    for r in conn.execute("SELECT id, name, platform_id FROM projects WHERE slug IS NULL OR slug = ''").fetchall():
        conn.execute("UPDATE projects SET slug = ? WHERE id = ?",
                     (unique_slug(conn, "projects", r["name"], "platform_id", r["platform_id"],
                                  fallback="progetto"), r["id"]))
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_platforms_slug ON platforms(slug)")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_projects_platform_slug ON projects(platform_id, slug)")

    # --- Seed / aggiornamento criteri WCAG (non duplica, aggiorna titoli e ordine) ---
    for i, (code, title, level, principle, anchor) in enumerate(CRITERIA):
        conn.execute(
            """INSERT INTO criteria (code, title, level, principle, anchor, sort_order)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(code) DO UPDATE SET title=excluded.title, level=excluded.level,
                   principle=excluded.principle, anchor=excluded.anchor, sort_order=excluded.sort_order""",
            (code, title, level, principle, anchor, i),
        )

    # --- Seed tipologie di componente (solo se mancanti: le personalizzazioni restano) ---
    for name, description, aria, crit_codes in COMPONENT_TYPES:
        row = conn.execute("SELECT id FROM component_types WHERE name = ?", (name,)).fetchone()
        if row is None:
            cur = conn.execute(
                "INSERT INTO component_types (name, description, aria_notes) VALUES (?, ?, ?)",
                (name, description, aria),
            )
            type_id = cur.lastrowid
            for code in crit_codes + AAA_EXTRAS.get(name, []):
                conn.execute(
                    """INSERT OR IGNORE INTO component_type_criteria (component_type_id, criterion_id)
                       SELECT ?, id FROM criteria WHERE code = ?""",
                    (type_id, code),
                )

    # --- Migrazione v1 -> v2: aggiunge i criteri AAA alle tipologie predefinite esistenti ---
    if not fresh and old_version < 2:
        for name, codes in AAA_EXTRAS.items():
            row = conn.execute("SELECT id FROM component_types WHERE name = ?", (name,)).fetchone()
            if row:
                for code in codes:
                    conn.execute(
                        """INSERT OR IGNORE INTO component_type_criteria (component_type_id, criterion_id)
                           SELECT ?, id FROM criteria WHERE code = ?""",
                        (row["id"], code),
                    )

    conn.execute("INSERT INTO meta (key, value) VALUES ('schema_version', ?) "
                 "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (str(SCHEMA_VERSION),))
    conn.commit()
    conn.close()
