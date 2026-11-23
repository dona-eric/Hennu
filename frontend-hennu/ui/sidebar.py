"""Barre latérale : navigation et historique des conversations."""

import streamlit as st

from service import conversation as session
from settings import APP_NAME, APP_TAGLINE, HOME_PAGE
from ui import templates


def render_sidebar() -> None:
    active = session.active_conversation()
    conversations = session.recent_conversations()

    with st.sidebar:
        st.html(templates.brand(APP_NAME, APP_TAGLINE))

        with st.container(key="back_home"):
            st.page_link(
                HOME_PAGE,
                label="Retour à l'accueil",
                icon=":material/arrow_back:",
            )

        st.button(
            "Nouvelle conversation",
            key="new_conversation",
            icon=":material/add:",
            type="primary",
            width="stretch",
            on_click=session.new_conversation,
        )

        st.html(templates.section_label("Récentes"))

        with st.container(key="history"):
            if not conversations:
                st.caption("Vos conversations apparaîtront ici.")

            for item in conversations:
                is_active = active is not None and item.id == active.id
                st.button(
                    item.title,
                    key=f"conversation_{item.id}",
                    icon=":material/chat_bubble:",
                    type="secondary" if is_active else "tertiary",
                    width="stretch",
                    on_click=session.open_conversation,
                    args=(item.id,),
                )

        with st.container(key="sidebar_bottom"):
            st.html(templates.status_pill("Base documentaire connectée"))
            if conversations:
                st.button(
                    "Effacer l'historique",
                    key="clear_history",
                    icon=":material/delete_sweep:",
                    type="tertiary",
                    on_click=session.clear_history,
                )
