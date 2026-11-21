"""Barre de navigation de la page d'accueil."""

import streamlit as st

from settings import APP_NAME, ASSISTANT_PAGE, HOME_PAGE
from ui import templates


def render_navbar() -> None:
    with st.container(
        key="navbar",
        horizontal=True,
        vertical_alignment="center",
        gap="medium",
    ):
        st.html(templates.nav_brand(APP_NAME), width="content")
        st.space("stretch")

        st.page_link(HOME_PAGE, label="Accueil", icon=":material/home:")

        # Future page : regroupera tous les textes douaniers
        st.button(
            "Base documentaire",
            key="nav_documents",
            icon=":material/library_books:",
            type="tertiary",
            disabled=True,
            help="Bientôt disponible : tous les textes douaniers réunis.",
        )

        with st.container(key="nav_cta", width="content"):
            st.page_link(
                ASSISTANT_PAGE,
                label="Ouvrir l'assistant",
                icon=":material/arrow_forward:",
                icon_position="right",
            )
