"""Paramètres secondaires du projet.

Les configurations essentielles (Qdrant, embedding, LLM, retriever,
reranker) sont dans app/core/free_config.yml, lues par
app/services/configer/call_config.py.

Ce fichier ne garde que les métadonnées des documents et les clés
des services annexes.
"""

import os

import dotenv

# Chargement des clés depuis le fichier .env
dotenv.load_dotenv()


# --- Documents de référence ---
# Clé = nom du fichier Markdown sans ".md".
# priority : 1 = texte en vigueur, cité en premier.
# Les autres fichiers ont DEFAULT_PRIORITY.
DOCUMENTS = {
    "Code-douanier-modifie020-Ori-1": {
        "title": (
            "Code des Douanes du Bénin — Loi n° 2014-20 du 12 septembre 2014, "
            "version modifiée (en vigueur)"
        ),
        "priority": 1,
    },
    "0218005001534958938": {
        "title": (
            "Code des Douanes du Bénin — Loi n° 2014-20 du 12 septembre 2014, "
            "version initiale"
        ),
        "priority": 2,
    },
    "BJ_Code_des_Douanes": {
        "title": (
            "Ancien Code des Douanes du Bénin (ordonnance n° 54 du "
            "21 novembre 1966) et textes d'application"
        ),
        "priority": 3,
    },
}
DEFAULT_PRIORITY = 4


# --- Services annexes ---
DATALAB_API_KEY = os.getenv("marker_api_key")
API_KEY_GROQ = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
TOKEN_HUGGINGFACE = os.getenv("HUGGINGFACE_TOKEN")


# --- Base documentaire ---
# Mot de passe de l'espace d'administration (validation des documents).
# Sans cette variable dans le .env, l'administration est désactivée.
ADMIN_PASSWORD = os.getenv("HENNU_ADMIN_PASSWORD")
