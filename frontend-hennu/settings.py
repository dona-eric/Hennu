"""Paramètres et textes de l'interface Hɛnnu.
Tout ce qui est « réglable » (textes, icônes, délais, fichiers CSS)
se trouve ici pour ne pas avoir à fouiller dans le code.
"""

import os
from pathlib import Path

# API Hɛnnu (l'agent RAG tourne dans l'API FastAPI)
API_URL = os.getenv("HENNU_API_URL", "http://localhost:8000").rstrip("/")
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
APP_NAME = "Hɛnnu"
APP_TAGLINE = "Intelligence réglementaire douanière"
APP_ORGANISATION = "La Douane Béninoise"
PAGE_TITLE = f"{APP_NAME} — Intelligence réglementaire douanière"
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
    "posez une question, Hɛnnu retrouve les textes applicables et vous répond "
    "en citant ses sources."
)

# Ce que fait Hɛnnu : (icône Material, titre, texte)
FEATURES = (
    (
        "travel_explore",
        "Recherche dans les textes",
        "Hɛnnu parcourt le Code des Douanes et les manuels de procédures "
        "pour retrouver les passages utiles à votre question.",
    ),
    (
        "verified",
        "Réponses sourcées",
        "Chaque réponse cite les articles et documents sur lesquels elle "
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
        "Hɛnnu analyse les textes",
        "Il reformule la question et recherche les articles pertinents.",
    ),
    (
        "Vous recevez une réponse sourcée",
        "Avec les références exactes et les extraits consultés.",
    ),
)

USER_AVATAR = ":material/person:"
ASSISTANT_AVATAR = ":material/balance:"

# Conversation

CHAT_PLACEHOLDER = "Posez une question sur la réglementation douanière…"
NEW_CONVERSATION_TITLE = "Nouvelle conversation"
TITLE_MAX_LENGTH = 42

EXAMPLE_QUESTIONS = (
    (":material/inventory_2:", "Quels sont les régimes suspensifs ?"),
    (":material/directions_car:", "Comment dédouaner un véhicule au Bénin ?"),
    (":material/category:", "Comment qualifier une marchandise ?"),
    (
        ":material/account_balance:",
        "Qu'est-ce que le Prélèvement Communautaire de Solidarité ?",
    ),
)

# Étapes du graphe LangGraph
AGENT_STEPS = (
    ("analyze_query", "Compréhension de la question"),
    ("retrieve_docs", "Recherche dans les textes douaniers"),
    ("generate_response", "Rédaction de la réponse"),
)

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
