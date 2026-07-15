# -*- coding: utf-8 -*-
"""Istanza Flask condivisa, costanti applicative e variabili globali per i template."""
import os

from flask import Flask

from wcag_data import WCAG_BASE_URL

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "accessibility-tracker-local")

STATUS_LABELS = {
    "da_verificare": "Da verificare",
    "conforme": "Conforme",
    "non_conforme": "Non conforme",
    "non_applicabile": "Non applicabile",
}
WORK_LABELS = {
    "": "—",
    "aperta": "Aperta",
    "in_lavorazione": "In lavorazione",
    "risolta": "Risolta",
    "verificata": "Risolta e verificata",
}
PROJECT_STATUSES = ["In corso", "In attesa", "Completato"]


def _read_version():
    path = os.path.join(os.path.dirname(__file__), "VERSION")
    try:
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "0.0.0"


APP_VERSION = _read_version()


@app.context_processor
def inject_globals():
    return {"STATUS_LABELS": STATUS_LABELS, "WORK_LABELS": WORK_LABELS,
            "PROJECT_STATUSES": PROJECT_STATUSES, "WCAG_BASE_URL": WCAG_BASE_URL,
            "APP_VERSION": APP_VERSION}
