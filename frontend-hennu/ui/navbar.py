"""Barre de navigation de la page d'accueil."""

import streamlit as st

from settings import APP_NAME, ASSISTANT_PAGE, DOCUMENTS_PAGE, HOME_PAGE
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

        st.page_link(
            DOCUMENTS_PAGE,
            label="Base documentaire",
            icon=":material/library_books:",
        )

        with st.container(key="nav_cta", width="content"):
            st.page_link(
                ASSISTANT_PAGE,
                label="Ouvrir l'assistant",
                icon=":material/arrow_forward:",
                icon_position="right",
            )
