"""Conversations de l'utilisateur, stockées dans la session Streamlit.

Une session contient plusieurs conversations ; une seule est « active »
à la fois. Si aucune n'est active, l'assistant affiche son écran vide
avec des questions d'exemple.
"""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

import streamlit as st

from settings import NEW_CONVERSATION_TITLE, TITLE_MAX_LENGTH


def _new_id() -> str:
    return uuid4().hex[:10]


def shorten(text: str, max_length: int) -> str:
    """Coupe un texte trop long en ajoutant des points de suspension."""
    text = " ".join(text.split())
    if len(text) <= max_length:
        return text
    return text[: max_length - 1].rstrip() + "…"


@dataclass
class Message:
    """Un message de la conversation (utilisateur ou assistant)."""

    role: str
    content: str
    sources: list[dict] = field(default_factory=list)
    rewritten_query: str = ""
    duration: float | None = None
    is_error: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    id: str = field(default_factory=_new_id)


@dataclass
class Conversation:
    """Un fil de discussion avec l'assistant."""

    title: str = NEW_CONVERSATION_TITLE
    messages: list[Message] = field(default_factory=list)
    id: str = field(default_factory=_new_id)

    def add(self, message: Message) -> None:
        """Ajoute un message ; la première question donne son titre au fil."""
        if not self.messages and message.role == "user":
            self.title = shorten(message.content, TITLE_MAX_LENGTH)
        self.messages.append(message)

    @property
    def last_message(self) -> Message | None:
        return self.messages[-1] if self.messages else None

    @property
    def needs_retry(self) -> bool:
        """Vrai si la dernière question est restée sans réponse valable."""
        last = self.last_message
        return last is not None and (last.role == "user" or last.is_error)


# Accès à l'état de la session

def init_session() -> None:
    """Crée les clés de session au premier chargement."""
    defaults = {
        "conversations": {},
        "active_id": None,
        "pending_prompt": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def active_conversation() -> Conversation | None:
    return st.session_state.conversations.get(st.session_state.active_id)


def recent_conversations() -> list[Conversation]:
    """Conversations de la plus récente à la plus ancienne."""
    return list(reversed(st.session_state.conversations.values()))


def submit_question(question: str) -> Conversation:
    """Ajoute une question à la conversation active (créée si besoin)."""
    conversation = active_conversation()
    if conversation is None:
        conversation = Conversation()
        st.session_state.conversations[conversation.id] = conversation
        st.session_state.active_id = conversation.id

    conversation.add(Message(role="user", content=question))
    return conversation


# Actions déclenchées par les boutons (callbacks Streamlit)

def queue_prompt(prompt: str) -> None:
    """Met une question en attente
    elle sera envoyée au prochain rendu.
    """
    st.session_state.pending_prompt = prompt


def pop_pending_prompt() -> str | None:
    prompt = st.session_state.pending_prompt
    st.session_state.pending_prompt = None
    return prompt


def open_conversation(conversation_id: str) -> None:
    st.session_state.active_id = conversation_id


def new_conversation() -> None:
    """Désactive le fil courant : l'assistant affiche l'écran d'accueil."""
    st.session_state.active_id = None


def clear_history() -> None:
    st.session_state.conversations = {}
    st.session_state.active_id = None


def retry_last_question(conversation_id: str) -> None:
    """Retire la dernière question restée sans réponse et la renvoie."""
    conversation = st.session_state.conversations[conversation_id]

    # On enlève la réponse en erreur, puis la question elle-même
    if conversation.messages and conversation.messages[-1].is_error:
        conversation.messages.pop()
    if conversation.messages and conversation.messages[-1].role == "user":
        queue_prompt(conversation.messages.pop().content)
