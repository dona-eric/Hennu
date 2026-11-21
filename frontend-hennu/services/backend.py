"""Pont unique vers le backend Hɛnnu (package `app`).

Le frontend vit dans un sous-dossier du projet : on ajoute la racine
au chemin Python pour pouvoir importer app, quel que soit le dossier
depuis lequel Streamlit est lancé.
"""

import sys

from settings import PROJECT_ROOT

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ces imports doivent venir après la mise à jour du chemin Python
from app.core.loger import setup_logging  # noqa: E402
from app.RAG.graph import customer_agent  # noqa: E402

# Les erreurs sont écrites dans logs/application.log
logger = setup_logging()

__all__ = ["customer_agent", "logger"]
