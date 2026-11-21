"""API Hɛnnu : point d'entrée unique vers l'agent RAG.

Lancement depuis la racine du projet :
    uvicorn app.api.routes:app --host 0.0.0.0 --port 8000

L'agent (modèles d'embedding et de reranking) est chargé une seule
fois au démarrage, puis partagé par toutes les requêtes.
"""

import json
from collections.abc import Iterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from app.api.schemas import AnswerResponse, DocumentBase, QuestionRequest
from app.core.loger import setup_logging
from app.RAG.graph import customer_agent

logger = setup_logging()

# Agent partagé par toutes les requêtes (rempli au démarrage)
_state: dict[str, Any] = {"agent": None}


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Charge l'agent avant d'accepter la première requête."""
    logger.info("API : chargement de l'agent…")
    _state["agent"] = customer_agent()
    logger.info("API : agent prêt.")
    yield


app = FastAPI(
    title="HennuAPI",
    description="API de l'assistant douanier Hɛnnu",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


def get_agent():
    agent = _state["agent"]
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent en cours de chargement.")
    return agent


def to_jsonable(value: Any) -> Any:
    """Rend les données sérialisables en JSON.

    Les scores du reranker sont des numpy.float32, que le module json
    ne sait pas écrire : on les convertit en nombres Python.
    """
    return json.loads(json.dumps(value, default=_json_default))


def _json_default(value: Any) -> Any:
    if hasattr(value, "item"):  # scalaires numpy
        return value.item()
    return str(value)


# Routes

@app.get("/health")
def health():
    return {"status": "ok", "agent_ready": _state["agent"] is not None}


@app.post("/ask", response_model=AnswerResponse)
def ask(request: QuestionRequest):
    """Réponse complète en une seule fois."""
    result = get_agent().invoke({"user_query": request.question})
    return AnswerResponse(
        answer=result.get("response", ""),
        sources=to_jsonable(result.get("sources", [])),
    )


@app.post("/ask/stream")
def ask_stream(request: QuestionRequest):
    """Réponse en flux (Server-Sent Events), étape par étape.

    Événements envoyés :
    - step  : {"node": <nom de l'étape>, "data": <données produites>}
    - error : {"message": <message lisible>}
    - done  : {}
    """
    agent = get_agent()
    return StreamingResponse(
        _stream_steps(agent, request.question),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _stream_steps(agent, question: str) -> Iterator[str]:
    try:
        updates = agent.stream({"user_query": question}, stream_mode="updates")
        for update in updates:
            for node, data in update.items():
                payload = {"node": node, "data": to_jsonable(data or {})}
                yield _sse("step", payload)
    except Exception:
        logger.exception("API : erreur pendant l'exécution de l'agent")
        yield _sse("error", {"message": "Erreur pendant le traitement de la question."})
        return

    yield _sse("done", {})


def _sse(event: str, payload: dict) -> str:
    """Formate un événement Server-Sent Events."""
    data = json.dumps(payload, ensure_ascii=False)
    return f"event: {event}\ndata: {data}\n\n"


@app.post("/search-book/{id}", response_model=DocumentBase)
def search_docs(request: DocumentBase):
    return None
