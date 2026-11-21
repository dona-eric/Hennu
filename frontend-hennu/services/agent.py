"""Client HTTP de l'API Hɛnnu (l'agent RAG tourne dans l'API, pas ici).

L'interface reçoit la progression de l'agent en direct grâce à la
route POST /ask/stream (Server-Sent Events).
"""

import json
from collections.abc import Iterator

import httpx

from settings import API_TIMEOUT_SECONDS, API_URL

CONNECT_TIMEOUT = 5  # secondes


class AgentError(Exception):
    """Erreur affichable telle quelle à l'utilisateur."""


def check_api() -> tuple[bool, str]:
    """Vérifie que l'API répond et que l'agent est chargé.

    Renvoie (disponible, message à afficher sinon).
    """
    try:
        response = httpx.get(f"{API_URL}/health", timeout=CONNECT_TIMEOUT)
        response.raise_for_status()
    except httpx.HTTPError:
        return False, f"L'API Hɛnnu est injoignable ({API_URL})."

    if not response.json().get("agent_ready"):
        return False, "L'assistant démarre, réessayez dans quelques instants."
    return True, ""


def stream_agent(question: str) -> Iterator[tuple[str, dict]]:
    """Envoie la question à l'API et renvoie chaque étape terminée.

    Chaque élément produit est un couple (nom du nœud, données produites).
    """
    timeout = httpx.Timeout(API_TIMEOUT_SECONDS, connect=CONNECT_TIMEOUT)
    try:
        with httpx.stream(
            "POST",
            f"{API_URL}/ask/stream",
            json={"question": question},
            timeout=timeout,
        ) as response:
            _raise_for_status(response)
            for event, payload in _read_events(response.iter_lines()):
                if event == "error":
                    raise AgentError(payload.get("message", "Erreur de l'assistant."))
                if event == "step":
                    yield payload["node"], payload.get("data") or {}
    except httpx.TimeoutException as error:
        raise AgentError("L'assistant a mis trop de temps à répondre.") from error
    except httpx.TransportError as error:
        raise AgentError(f"L'API Hɛnnu est injoignable ({API_URL}).") from error


def _raise_for_status(response: httpx.Response) -> None:
    if response.status_code == 422:
        raise AgentError("La question doit contenir entre 3 et 2000 caractères.")
    if response.status_code == 503:
        raise AgentError("L'assistant démarre, réessayez dans quelques instants.")
    if response.is_error:
        raise AgentError(f"Erreur de l'API ({response.status_code}).")


def _read_events(lines: Iterator[str]) -> Iterator[tuple[str, dict]]:
    """Découpe un flux Server-Sent Events en couples (événement, données)."""
    event, data = "message", ""
    for line in lines:
        if line.startswith("event:"):
            event = line[6:].strip()
        elif line.startswith("data:"):
            data += line[5:].strip()
        elif not line and data:  # ligne vide : fin de l'événement
            yield event, json.loads(data)
            event, data = "message", ""
