# -*- coding: utf-8 -*-
"""Accessibility Tracker — punto di ingresso applicazione Flask."""
import os

import views  # noqa: F401  registra tutte le route sull'app condivisa
from database import init_db
from extensions import app

if __name__ == "__main__":
    init_db()
    app.run(host=os.environ.get("FLASK_HOST", "127.0.0.1"),
            port=int(os.environ.get("FLASK_PORT", "8000")),
            debug=False)
