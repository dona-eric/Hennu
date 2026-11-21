"""Pont unique vers le backend Hɛnnu (package `app`).

Le frontend vit dans un sous-dossier du projet : on ajoute la racine
au chemin Python pour pouvoir importer app, quel que soit le dossier
depuis lequel Streamlit est lancé.

L'assistant passe par l'API (services/agent.py). Seule la base
documentaire est encore appelée directement, en attendant ses routes.
"""

import sys

from settings import PROJECT_ROOT

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ces imports doivent venir après la mise à jour du chemin Python
from app.core.config import ADMIN_PASSWORD  # noqa: E402
from app.core.loger import setup_logging  # noqa: E402
from app.services.documents import library  # noqa: E402

# Les erreurs sont écrites dans logs/application.log
logger = setup_logging()

__all__ = ["ADMIN_PASSWORD", "library", "logger"]
