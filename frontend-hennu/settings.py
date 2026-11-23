"""Paramètres et textes de l'interface Orion.
Tout ce qui est « réglable » (textes, icônes, délais, fichiers CSS)
se trouve ici pour ne pas avoir à fouiller dans le code.
"""

import os
from pathlib import Path

# API Orion (l'agent RAG tourne dans l'API FastAPI)
API_URL = os.getenv("Orion_API_URL", "http://localhost:8000").rstrip("/")
API_TIMEOUT_SECONDS = 300  # durée maximale d'une réponse

FRONTEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = FRONTEND_DIR.parent
CSS_DIR = FRONTEND_DIR / "static" / "css"

# Ordre de chargement des feuilles de style
CSS_FILES = (
    "tokens.css",
    "animations.css",
    "base.css",
    "layout.css",
    "home.css",
    "chat.css",
    "documents.css",
)

# Identité de l'application
APP_NAME = "Orion"
APP_TAGLINE = "Intelligence réglementaire douanière"
APP_ORGANISATION = "La Douane Béninoise"
PAGE_TITLE = f"{APP_NAME} - Intelligence réglementaire douanière"
PAGE_ICON = "⚖️"
COPYRIGHT_YEAR = 2026

# Routers
HOME_PAGE = "views/home.py"
ASSISTANT_PAGE = "views/assistant.py"
DOCUMENTS_PAGE = "views/documents.py"

# Base documentaire
UPLOAD_MAX_MB = 50
DOCUMENT_STATUS_LABELS = {
    "pending": "En attente de validation",
    "approved": "En file d'attente",
    "processing": "Ingestion en cours",
    "ready": "Publié",
    "failed": "Échec",
    "rejected": "Refusé / retiré",
}
STATUS_REFRESH_SECONDS = 4  # rafraîchissement de l'admin pendant une ingestion

# Contenu de la page d'accueil

HERO_TEXT = (
    "Votre assistant pour comprendre la réglementation douanière béninoise : "
    "posez une question, Orion retrouve les infos applicables, vérifie tout "
    "et vous allège les taches de recherche"
)

# Ce que fait Orion
FEATURES = (
    (
        "travel_explore",
        "Recherche dans milliers de documents",
        "Orion parcourt le Code, les textes et les manuels "
        "pour retrouver les passages utiles à votre question.",
    ),
    (
        "verified",
        "Réponses sourcées",
        "Chaque réponse cite est sourcée et documentées "
        "s'appuie, pour que vous puissiez toujours vérifier.",
    ),
    (
        "translate",
        "Un langage clair",
        "Régimes, procédures, taxes : les notions douanières expliquées "
        "simplement, en français.",
    ),
)

# Comment ça marche : (titre, texte)
HOW_IT_WORKS = (
    ("Vous posez votre question", "En langage courant, comme à un collègue."),
    (
        "Orion analyse les textes",
        "Il reformule la question et recherche les réponses pertinentes.",
    ),
    (
        "Vous recevez une réponse sourcée",
        "Avec les références exactes et les extraits consultés.",
    ),
)

USER_AVATAR = ":material/person:"
ASSISTANT_AVATAR = ":material/balance:"

# Conversation

CHAT_PLACEHOLDER = "De quoi voulez-vous qu'on discute aujourd'hui ?"
NEW_CONVERSATION_TITLE = "New chat"
TITLE_MAX_LENGTH = 42

EXAMPLE_QUESTIONS = (
    (":material/inventory_2:", "Quels sont les régimes suspensifs ?"),
    (":material/directions_car:", "Comment dédouaner un véhicule au Bénin ?"),
    (":material/category:", "Comment qualifier une marchandise ?"),
    (":material/account_balance:","Qu'est-ce que le Prélèvement Communautaire de Solidarité ?",),
)

# Étapes du graphe LangGraph : (nœud, libellé, étape facultative)
# Une étape facultative n'apparaît que si l'agent la parcourt.
AGENT_STEPS = (
    ("analyze_query", "Compréhension de la question", False),
    ("refine_query", "Nouvelle recherche, formulée autrement", True),
    ("retrieve_docs", "Recherche dans les textes douaniers", False),
    ("grade_documents", "Évaluation des documents trouvés", False),
    ("generate_response", "Rédaction de la réponse", False),
    ("verify_answer", "Vérification des sources", False),
)

# Quand l'agent reboucle, ces étapes redeviennent « à faire »
STEPS_RESTARTED_BY = {
    "refine_query": ("retrieve_docs", "grade_documents"),
}

# Effet « machine à écrire » : durée maximale d'affichage d'une réponse
TYPING_MAX_DURATION = 2.5  # secondes
TYPING_MAX_WORD_DELAY = 0.03  # secondes entre deux mots

EMPTY_ANSWER = "Aucune réponse n'a été générée."
ERROR_ANSWER = (
    "Une erreur est survenue pendant le traitement de votre question. "
    "Vous pouvez relancer la question."
)
AGENT_UNAVAILABLE_HINT = (
    "Lancez l'API depuis la racine du projet : "
    "`uvicorn app.api.routes:app --port 8000`"
)
