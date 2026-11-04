# streamlit_app.py

from pathlib import Path
import logging

import streamlit as st

from app.RAG.graph import customer_agent


# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
STYLE_FILE = BASE_DIR / "style.css"

st.set_page_config(
    page_title="Hɛnnu AI — Assistant Douanier",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ------------------------------------------------------------------
# Chargement du style
# ------------------------------------------------------------------

def load_css() -> None:
    """Charge le fichier CSS s'il existe."""
    if STYLE_FILE.exists():
        css = STYLE_FILE.read_text(encoding="utf-8")
        st.markdown(
            f"<style>{css}</style>",
            unsafe_allow_html=True,
        )


load_css()


# ------------------------------------------------------------------
# Initialisation de l'agent
# ------------------------------------------------------------------

@st.cache_resource
def get_agent():
    """Initialise l'agent une seule fois."""
    return customer_agent()


try:
    agent = get_agent()
except Exception:
    logger.exception("Impossible d'initialiser l'agent DocMind AI")
    st.error(
        "L'assistant n'a pas pu être initialisé. "
        "Vérifiez la configuration du backend et de Qdrant."
    )
    st.stop()


# ------------------------------------------------------------------
# État de la session
# ------------------------------------------------------------------

def initialize_session() -> None:
    defaults = {
        "messages": [],
        "chat_active": False,
        "pending_prompt": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


initialize_session()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def get_avatar(role: str) -> str:
    return ":material/person:" if role == "user" else "⚖️"


def render_sources(sources: list) -> None:
    """Affiche les sources si elles sont présentes dans la réponse."""
    if not sources:
        return

    with st.expander("📚 Sources documentaires", expanded=False):
        for index, source in enumerate(sources, start=1):
            if isinstance(source, dict):
                title = (
                    source.get("title")
                    or source.get("article")
                    or f"Source {index}"
                )
                content = source.get("content") or source.get("text") or ""
            else:
                title = f"Source {index}"
                content = str(source)

            st.markdown(f"**{title}**")
            if content:
                st.write(content)

            if index < len(sources):
                st.divider()


def render_message(message: dict) -> None:
    """Affiche un message utilisateur ou assistant."""
    role = message["role"]

    with st.chat_message(role, avatar=get_avatar(role)):
        st.markdown(message["content"])

        if role == "assistant":
            render_sources(message.get("sources", []))


def run_agent(question: str) -> tuple[str, list]:
    """Exécute le graphe LangGraph et récupère sa réponse."""
    result = agent.invoke({"user_query": question})

    answer = result.get(
        "response",
        "Aucune réponse n'a été générée.",
    )

    sources = result.get("sources", [])

    return answer, sources


# ------------------------------------------------------------------
# Navigation
# ------------------------------------------------------------------

with st.sidebar:
    st.markdown("## Hɛnnu AI")
    st.caption("Intelligence réglementaire douanière")

    st.divider()

    if st.button(
        "＋ Nouvelle conversation",
        use_container_width=True,
    ):
        st.session_state.messages = []
        st.session_state.chat_active = False
        st.session_state.pending_prompt = None
        st.rerun()

    if st.session_state.chat_active:
        if st.button(
            "← Retour à l'accueil",
            use_container_width=True,
        ):
            st.session_state.chat_active = False
            st.rerun()

    st.divider()

    st.markdown("### Assistant")
    st.caption(
        "Posez vos questions sur les textes, "
        "les procédures et la réglementation douanière."
    )

    st.markdown("### État")
    st.success("Interface disponible")


# ------------------------------------------------------------------
# En-tête
# ------------------------------------------------------------------

st.markdown(
    """
    <div class="docmind-header">
        <h1>Hɛnnu AI</h1>
        <p>
            Intelligence réglementaire douanière —
            La Douane Béninoise
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ------------------------------------------------------------------
# Accueil
# ------------------------------------------------------------------

if not st.session_state.chat_active:
    st.markdown(
        """
        <div style="text-align:center; margin: 2rem 0;">
            <h2>Comment pouvons-nous vous aider ?</h2>
            <p style="color:gray;">
                Explorez les textes et procédures douanières
                avec votre assistant intelligent.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2, gap="large")

    with col1:
        with st.container(border=True):
            st.markdown(
                "<div style='text-align:center;font-size:3rem;'>⚖️</div>",
                unsafe_allow_html=True,
            )

            st.markdown(
                "<h3 style='text-align:center;'>Assistant Douanier</h3>",
                unsafe_allow_html=True,
            )

            st.write(
                "Comprendre la réglementation, les procédures "
                "douanières, le Tarif Extérieur Commun et les "
                "textes applicables au Bénin."
            )

            st.markdown("**Exemples de questions**")

            example_questions = [
                "Quels sont les régimes suspensifs ?",
                "Comment dédouaner un véhicule au Bénin ?",
                "Comment qualifier une marchandise ?",
                "Qu'est-ce que le Prélèvement Communautaire de Solidarité ?",
            ]

            for index, example in enumerate(example_questions):
                if st.button(
                    example,
                    key=f"example_{index}",
                    use_container_width=True,
                ):
                    st.session_state.pending_prompt = example
                    st.session_state.chat_active = True
                    st.rerun()

            if st.button(
                "Ouvrir l'Assistant IA →",
                type="primary",
                use_container_width=True,
            ):
                st.session_state.chat_active = True
                st.rerun()

    with col2:
        with st.container(border=True):
            st.markdown(
                "<div style='text-align:center;font-size:3rem;'>📋</div>",
                unsafe_allow_html=True,
            )

            st.markdown(
                "<h3 style='text-align:center;'>Audit & Contrôle</h3>",
                unsafe_allow_html=True,
            )

            st.write(
                "Analyse des incohérences dans les déclarations "
                "et vérification de conformité."
            )

            st.info("Cette fonctionnalité sera disponible prochainement.")

            st.button(
                "Bientôt disponible",
                disabled=True,
                use_container_width=True,
            )


# ------------------------------------------------------------------
# Mode conversation
# ------------------------------------------------------------------

else:
    # Affichage de l'historique une seule fois
    for message in st.session_state.messages:
        render_message(message)

    # Question issue d'un exemple ou du chat_input
    prompt = st.session_state.pending_prompt

    if prompt:
        st.session_state.pending_prompt = None
    else:
        prompt = st.chat_input(
            "Posez une question sur la réglementation douanière..."
        )

    if prompt:
        st.session_state.messages.append({
            "role": "user",
            "content": prompt,
        })

        render_message({
            "role": "user",
            "content": prompt,
        })

        with st.chat_message("assistant", avatar=get_avatar("assistant")):
            with st.status(
                "Analyse des textes douaniers...",
                expanded=True,
            ) as status:
                st.write("Analyse de votre question...")
                st.write("Recherche des passages pertinents...")
                st.write("Préparation de la réponse...")

                try:
                    answer, sources = run_agent(prompt)

                    status.update(
                        label="Analyse terminée",
                        state="complete",
                        expanded=False,
                    )

                except Exception:
                    logger.exception(
                        "Erreur pendant l'exécution de l'agent"
                    )

                    status.update(
                        label="Erreur lors de l'analyse",
                        state="error",
                        expanded=False,
                    )

                    answer = (
                        "Une erreur est survenue pendant le traitement "
                        "de votre question. Veuillez réessayer."
                    )
                    sources = []

            st.markdown(answer)
            render_sources(sources)

        st.session_state.messages.append({
            "role": "assistant",
            "content": answer,
            "sources": sources,
        })


# ------------------------------------------------------------------
# Footer
# ------------------------------------------------------------------

st.markdown(
    """
    <div class="footer">
        <div class="footer-brand">Hɛnnu AI</div>
        <div class="footer-copyright">
            © 2026 Hɛnnu AI — Tous droits réservés.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)