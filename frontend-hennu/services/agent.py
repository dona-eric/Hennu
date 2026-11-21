"""Exécution de l'agent RAG, étape par étape."""

from collections.abc import Iterator

import streamlit as st

from services.backend import customer_agent


@st.cache_resource(show_spinner="Chargement de la base documentaire…")
def get_agent():
    """Construit le graphe LangGraph une seule fois pour toute l'application."""
    return customer_agent()


def stream_agent(question: str) -> Iterator[tuple[str, dict]]:
    """Exécute l'agent et renvoie chaque étape dès qu'elle est terminée.

    Chaque élément produit est un couple (nom du nœud, données produites),
    ce qui permet à l'interface d'afficher la progression réelle.
    """
    agent = get_agent()
    updates = agent.stream(
        {
            "user_query": question
        },
        stream_mode="updates"
    )

    for update in updates:
        for node, data in update.items():
            yield node, data or {}
