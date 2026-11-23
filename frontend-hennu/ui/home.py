"""Page d'accueil : présentation de Orion et de ses modules.

Pas de barre latérale ni de zone de saisie ici : la conversation
s'ouvre sur la route /assistant (carte « Assistant douanier »).
"""

import streamlit as st

from settings import (
    APP_NAME,
    APP_ORGANISATION,
    APP_TAGLINE,
    ASSISTANT_PAGE,
    COPYRIGHT_YEAR,
    DOCUMENTS_PAGE,
    FEATURES,
    HERO_TEXT,
    HOW_IT_WORKS,
)
from ui import templates
from ui.navbar import render_navbar


def render_home() -> None:
    render_navbar()

    st.html(
        templates.hero(APP_NAME, APP_ORGANISATION, APP_TAGLINE, HERO_TEXT)
    )
    _render_hero_actions()

    _heading("Ce que fait Orion", "La douane, à votre porté")
    st.html(templates.features(FEATURES))

    _heading("Comment ça marche", "Trois étapes, une réponse fiable")
    st.html(templates.how_it_works(HOW_IT_WORKS))

    _heading("Modules", "Choisissez votre espace de travail")
    _render_modules()

    st.html(templates.footer(APP_NAME, COPYRIGHT_YEAR))


def _heading(eyebrow: str, title: str) -> None:
    st.html(templates.section_heading(eyebrow, title))


def _render_hero_actions() -> None:
    with st.container(
        key="hero_actions",
        horizontal=True,
        horizontal_alignment="center",
    ):
        st.page_link(
            ASSISTANT_PAGE,
            label="Poser une question",
            icon=":material/chat:",
        )


def _render_modules() -> None:
    assistant, audit, documents = st.columns(3, gap="medium")

    # Carte cliquable : le lien recouvre toute la carte (voir home.css)
    with assistant, st.container(key="module_assistant"):
        st.html(
            templates.module_card(
                "balance",
                "Assistant douanier",
                "Posez vos questions sur la réglementation, les procédures "
                "et le Tarif Extérieur Commun applicables au Bénin.",
                badge="Disponible",
            )
        )
        st.page_link(
            ASSISTANT_PAGE,
            label="Ouvrir l'assistant",
            icon=":material/arrow_forward:",
            icon_position="right",
        )

    with audit, st.container(key="module_audit"):
        st.html(
            templates.module_card(
                "fact_check",
                "Audit & Contrôle",
                "Détection des incohérences dans les déclarations "
                "et vérification de conformité.",
                badge="Bientôt",
            )
        )

    with documents, st.container(key="module_documents"):
        st.html(
            templates.module_card(
                "library_books",
                "Base documentaire",
                "Tous les textes douaniers réunis, consultables en ligne. "
                "Proposez vos propres documents.",
                badge="Disponible",
            )
        )
        st.page_link(
            DOCUMENTS_PAGE,
            label="Explorer la base",
            icon=":material/arrow_forward:",
            icon_position="right",
        )
