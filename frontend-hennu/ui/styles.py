"""Chargement des feuilles de style."""

import streamlit as st

from settings import CSS_DIR, CSS_FILES


def load_styles() -> None:
    """Injecte toutes les feuilles CSS de static/css dans la page."""
    css = "\n".join(
        (CSS_DIR / name).read_text(encoding="utf-8")
        for name in CSS_FILES
        if (CSS_DIR / name).exists()
    )
    # Un st.html qui ne contient que du <style> n'occupe aucune place
    st.html(f"<style>{css}</style>")
