"""Vue conversation : historique, progression de l'agent et réponses."""

import re
import time
from collections.abc import Iterator

import streamlit as st

from services import conversation as session
from services.agent import get_agent, stream_agent
from services.backend import logger
from services.conversation import Conversation, Message, shorten
from settings import (
    AGENT_INIT_ERROR,
    AGENT_STEPS,
    APP_TAGLINE,
    ASSISTANT_AVATAR,
    CHAT_PLACEHOLDER,
    EMPTY_ANSWER,
    ERROR_ANSWER,
    EXAMPLE_QUESTIONS,
    TYPING_MAX_DURATION,
    TYPING_MAX_WORD_DELAY,
    USER_AVATAR,
)
from ui import templates
from ui.sidebar import render_sidebar


def render_assistant_page() -> None:
    """Route /assistant : barre latérale, fil de discussion et saisie."""
    _ensure_agent_ready()

    # Question tapée au clavier ou choisie parmi les exemples
    prompt = st.chat_input(CHAT_PLACEHOLDER, key="prompt_input")
    prompt = prompt or session.pop_pending_prompt()
    if prompt:
        session.submit_question(prompt)

    render_sidebar()

    conversation = session.active_conversation()
    if conversation is None:
        _render_empty_state()
    else:
        render_chat(conversation, answer_last=bool(prompt))


def _ensure_agent_ready() -> None:
    """Charge l'agent ; arrête la page proprement s'il est indisponible."""
    try:
        get_agent()
    except Exception:
        logger.exception("Impossible d'initialiser l'agent Hɛnnu")
        st.error(AGENT_INIT_ERROR, icon=":material/cloud_off:")
        st.stop()


def _render_empty_state() -> None:
    """Écran d'une nouvelle conversation : questions d'exemple."""
    st.html(
        templates.empty_state(
            "Comment puis-je vous aider ?",
            "Posez votre question ci-dessous ou partez d'un exemple.",
        )
    )

    with st.container(key="suggestions"):
        columns = st.columns(2, gap="small")
        for index, (icon, question) in enumerate(EXAMPLE_QUESTIONS):
            with columns[index % 2]:
                st.button(
                    question,
                    key=f"suggestion_{index}",
                    icon=icon,
                    width="stretch",
                    on_click=session.queue_prompt,
                    args=(question,),
                )


def render_chat(conversation: Conversation, answer_last: bool) -> None:
    """Affiche le fil de discussion.

    Si `answer_last` est vrai, la dernière question vient d'être posée :
    on lance l'agent pour y répondre en direct.
    """
    count = len(conversation.messages)
    subtitle = f"{count} {_plural(count, 'message', 'messages')} · {APP_TAGLINE}"
    st.html(templates.chat_header(conversation.title, subtitle))

    for message in conversation.messages:
        render_message(message)

    if answer_last:
        _answer(conversation)
    elif conversation.needs_retry:
        st.button(
            "Relancer la question",
            key="retry",
            icon=":material/refresh:",
            on_click=session.retry_last_question,
            args=(conversation.id,),
        )


def render_message(message: Message) -> None:
    """Affiche un message déjà enregistré."""
    with st.chat_message(message.role, avatar=_avatar(message.role)):
        if message.is_error:
            st.warning(message.content, icon=":material/error:")
        else:
            st.markdown(message.content)

        if message.role == "assistant":
            _render_assistant_details(message)
        else:
            st.html(templates.message_meta([_time(message)]))


# Réponse en direct

def _answer(conversation: Conversation) -> None:
    """Interroge l'agent pour la dernière question et affiche la réponse."""
    question = conversation.last_message.content

    with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
        reply = _run_agent(question)

        if reply.is_error:
            st.warning(reply.content, icon=":material/error:")
        else:
            st.write_stream(_typewriter(reply.content), cursor="▍")

        _render_assistant_details(reply)

    conversation.add(reply)


def _run_agent(question: str) -> Message:
    """Exécute l'agent en affichant sa progression réelle, étape par étape."""
    progress = st.empty()
    done: dict[str, str] = {}
    result: dict = {}
    start = time.perf_counter()

    progress.html(templates.steps(_steps_view(done)))

    try:
        for node, data in stream_agent(question):
            result.update(data)
            done[node] = _step_detail(node, data)
            progress.html(templates.steps(_steps_view(done)))
    except Exception:
        logger.exception("Erreur pendant l'exécution de l'agent")
        progress.empty()
        return Message(role="assistant", content=ERROR_ANSWER, is_error=True)

    progress.empty()
    return Message(
        role="assistant",
        content=result.get("response") or EMPTY_ANSWER,
        sources=result.get("sources", []),
        rewritten_query=result.get("rewritten_user_query", ""),
        duration=time.perf_counter() - start,
    )


def _steps_view(done: dict[str, str]) -> list[tuple[str, str, str]]:
    """Calcule l'état de chaque étape : terminée, en cours ou à venir."""
    view = []
    active_found = False

    for node, label in AGENT_STEPS:
        if node in done:
            view.append((label, done[node], "done"))
        elif not active_found:
            view.append((label, "", "active"))
            active_found = True
        else:
            view.append((label, "", "pending"))

    return view


def _step_detail(node: str, data: dict) -> str:
    """Petit résumé affiché sous une étape terminée."""
    if node == "analyze_query":
        query = data.get("rewritten_user_query", "")
        return f"« {shorten(query, 90)} »" if query else ""

    if node == "retrieve_docs":
        count = len(data.get("sources", []))
        if count == 0:
            return "Aucun texte trouvé"
        return f"{count} {_plural(count, 'texte pertinent', 'textes pertinents')}"

    return "Terminé"


def _typewriter(text: str) -> Iterator[str]:
    """Restitue la réponse mot à mot, comme si elle était tapée."""
    tokens = re.split(r"(\s+)", text)
    delay = min(TYPING_MAX_WORD_DELAY, TYPING_MAX_DURATION / max(len(tokens), 1))

    for token in tokens:
        yield token
        if token.strip():
            time.sleep(delay)


# Détails sous une réponse : sources, méta-données, avis

def _render_assistant_details(message: Message) -> None:
    if message.sources:
        st.html(templates.source_stamps(message.sources))
        _render_sources_expander(message)

    meta_row = st.container(
        horizontal=True,
        vertical_alignment="center",
        key=f"meta_{message.id}",
    )
    with meta_row:
        st.html(templates.message_meta(_meta_parts(message)), width="content")
        if not message.is_error:
            st.feedback(
                "thumbs",
                key=f"feedback_{message.id}",
                on_change=_log_feedback,
                args=(message.id,),
            )


def _render_sources_expander(message: Message) -> None:
    label = f"Consulter les extraits ({len(message.sources)})"

    with st.expander(label, icon=":material/menu_book:"):
        if message.rewritten_query:
            st.html(
                templates.reasoning_note(
                    "Question analysée", message.rewritten_query
                )
            )

        for index, source in enumerate(message.sources, start=1):
            title = source.get("title") or source.get("article") or ""
            content = source.get("content") or source.get("text") or ""
            st.html(templates.excerpt(index, title, content))


def _meta_parts(message: Message) -> list[str]:
    parts = [_time(message)]
    if message.duration is not None:
        parts.append(f"{message.duration:.1f} s".replace(".", ","))
    if message.sources:
        count = len(message.sources)
        parts.append(f"{count} {_plural(count, 'source', 'sources')}")
    return parts


def _log_feedback(message_id: str) -> None:
    """Trace l'avis de l'utilisateur (0 = 👎, 1 = 👍) dans les logs."""
    value = st.session_state.get(f"feedback_{message_id}")
    logger.info(f"Avis utilisateur sur la réponse {message_id} : {value}")


def _plural(count: int, singular: str, plural: str) -> str:
    return plural if count > 1 else singular


def _avatar(role: str) -> str:
    return USER_AVATAR if role == "user" else ASSISTANT_AVATAR


def _time(message: Message) -> str:
    return message.created_at.strftime("%H:%M")
