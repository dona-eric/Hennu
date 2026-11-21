"""Point d'entrée Streamlit de Orion.

Lancement depuis le dossier frontend-hennu :
    streamlit run main.py

Ce fichier ne fait qu'orchestrer : la logique est dans `services/`,
l'affichage dans `ui/`, les pages dans `views/` et les styles
dans `static/css/`.
"""

import streamlit as st
from service import conversation as session
from settings import ASSISTANT_PAGE, DOCUMENTS_PAGE, HOME_PAGE, PAGE_ICON, PAGE_TITLE
from ui.styles import load_styles


def main() -> None:
    st.set_page_config(
        page_title=PAGE_TITLE,
        page_icon=PAGE_ICON,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    load_styles()
    session.init_session()

    # Trois routes : l'accueil (/), l'assistant (/assistant) et la base documentaire (/documents).
    # La navigation est cachée : on circule via la barre de navigation de l'accueil et la barre latérale de l'assistant.
    pages = [
        st.Page(HOME_PAGE, title="Accueil", icon=":material/home:", default=True),
        st.Page(
            ASSISTANT_PAGE,
            title="Assistant douanier",
            icon=":material/balance:",
            url_path="assistant",
        ),
        st.Page(
            DOCUMENTS_PAGE,
            title="Base documentaire",
            icon=":material/library_books:",
            url_path="documents",
        ),
    ]
    st.navigation(pages, position="hidden").run()

if __name__=='__main__':
    main()
