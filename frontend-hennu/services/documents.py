"""Accès à la base documentaire depuis l'interface (cache et administration)."""

import hmac

import streamlit as st

from services.backend import ADMIN_PASSWORD, library, logger


@st.cache_resource(show_spinner=False)
def ensure_library_ready() -> bool:
    """Initialise la base une seule fois par serveur (documents d'origine...)."""
    library.init_library()
    return True


@st.cache_data(max_entries=300, show_spinner=False)
def page_image(document_id: str, page_number: int, version: str) -> bytes | None:
    """Image d'une page, mise en cache.

    `version` (date de mise à jour du document) invalide le cache
    quand le document change.
    """
    document = library.get_document(document_id)
    if document is None:
        return None
    return library.page_image(document, page_number)


# ------------------------------------------------------------------
# Administration
# ------------------------------------------------------------------

def admin_enabled() -> bool:
    """L'administration n'existe que si un mot de passe est défini."""
    return bool(ADMIN_PASSWORD)


def is_admin() -> bool:
    return st.session_state.get("is_admin", False)


def login(password: str) -> bool:
    """Vérifie le mot de passe (comparaison à temps constant)."""
    if not admin_enabled():
        return False

    valid = hmac.compare_digest(password.encode(), ADMIN_PASSWORD.encode())
    st.session_state.is_admin = valid
    if not valid:
        logger.warning("Tentative de connexion admin refusée.")
    return valid


def logout() -> None:
    st.session_state.is_admin = False
