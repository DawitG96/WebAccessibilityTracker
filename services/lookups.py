# -*- coding: utf-8 -*-
"""Query di lookup condivise tra le view (piattaforma/progetto a partire dallo slug)."""


def get_platform(db, slug):
    return db.execute("SELECT * FROM platforms WHERE slug = ?", (slug,)).fetchone()


def get_project(db, platform_slug, project_slug):
    return db.execute("""SELECT p.*, pl.name AS platform_name, pl.slug AS platform_slug
                         FROM projects p JOIN platforms pl ON pl.id = p.platform_id
                         WHERE pl.slug = ? AND p.slug = ?""",
                      (platform_slug, project_slug)).fetchone()
