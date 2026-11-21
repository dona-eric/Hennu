"""Fonctions utilitaires du graphe agentic (sans appel au LLM).

Elles sont séparées du graphe pour rester simples à tester.
"""

import json
import re
from typing import Any

# Les sources sont numérotées [1], [2]... dans le contexte et dans la réponse
CITATION = re.compile(r"\[(\d+)\]")


def source_from_node(text_node, score=None, max_chars: int = 6000) -> dict:
    """Transforme un nœud LlamaIndex en source affichable et citable."""
    metadata = text_node.metadata or {}
    article = metadata.get("article_title") or "Passage"
    document = (
        metadata.get("document_title") or metadata.get("source") or "Source inconnue"
    )
    return {
        "node_id": text_node.node_id,
        "title": f"{article} — {document}",
        "article": article,
        "document": document,
        "chapter": metadata.get("chapter") or "",
        "source": metadata.get("source"),
        "document_id": metadata.get("document_id"),
        "score": score,
        "content": text_node.get_content()[:max_chars],
    }


def merge_sources(*groups: list[dict]) -> list[dict]:
    """Fusionne des listes de sources en retirant les doublons (même nœud)."""
    merged, seen = [], set()
    for group in groups:
        for source in group:
            if source["node_id"] not in seen:
                seen.add(source["node_id"])
                merged.append(source)
    return merged


def build_context(sources: list[dict]) -> str:
    """Contexte envoyé au LLM : chaque source porte son numéro [n]."""
    parts = [
        f"[{index}]\n"
        f"Texte : {source['document']}\n"
        f"Chapitre : {source['chapter']}\n"
        f"{source['article']}\n\n"
        f"{source['content']}"
        for index, source in enumerate(sources, start=1)
    ]
    return "\n\n---\n\n".join(parts)


def numbered_excerpts(sources: list[dict], max_chars: int) -> str:
    """Version courte des sources, pour l'évaluation et la vérification."""
    return "\n\n".join(
        f"[{index}] {source['title']}\n{source['content'][:max_chars]}"
        for index, source in enumerate(sources, start=1)
    )


def invalid_citations(answer: str, source_count: int) -> list[int]:
    """Numéros cités dans la réponse qui ne correspondent à aucune source."""
    cited = {int(number) for number in CITATION.findall(answer)}
    return sorted(number for number in cited if not 1 <= number <= source_count)


def parse_json_object(text: str) -> dict[str, Any] | None:
    """Extrait le premier objet JSON d'une réponse de LLM (blocs ``` acceptés).

    Renvoie None si la réponse ne contient pas de JSON valide.
    """
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        value = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None
