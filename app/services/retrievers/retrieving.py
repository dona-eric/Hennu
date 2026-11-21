"""Recherche des passages pertinents (Qdrant) et des articles complets."""

import re
from pathlib import Path

from llama_index.core import VectorStoreIndex
from llama_index.core.schema import BaseNode, NodeWithScore
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.vector_stores.qdrant import QdrantVectorStore

from app.core.config import DEFAULT_PRIORITY
from app.core.loger import setup_logging
from app.services.configer.call_config import Configuration, get_config
from app.services.embeddings.embeder import IEmbedder
from app.services.embeddings.vector_store import IVectorStore
from app.services.processing.chuncker import article_number

logger = setup_logging()

DEFAULT_TOP_K = 20
DEFAULT_SCORE_THRESHOLD = 0.0

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DOCSTORE_PATH = PROJECT_ROOT / "data" / "docstore" / "docstore.json"

MAX_ARTICLE_CHARS = 3000

ARTICLE_NUMBER = r"(premier|\d+)\s*(?:er)?\s*(bis|ter|quater)?\b"
ARTICLE_IN_QUESTION = re.compile(
    rf"\barticles?\s+((?:{ARTICLE_NUMBER})(?:\s*(?:,|et)\s*(?:{ARTICLE_NUMBER}))*)",
    re.IGNORECASE,
)
MAX_DIRECT_ARTICLES = 3   # versions d'un même article (code en vigueur, version initiale, ancien code)


class IRetriever:
    """Recherche par le sens dans les passages (chunks) stockés dans Qdrant.

    Les candidats renvoyés seront ensuite triés par le reranker.
    """

    def __init__(
        self,
        vector_store: IVectorStore,
        embedder: IEmbedder,
        similarity_top_k: int = DEFAULT_TOP_K,
        score_threshold: float = DEFAULT_SCORE_THRESHOLD,
    ) -> None:
        self.similarity_top_k = similarity_top_k
        self.score_threshold = score_threshold

        qdrant = QdrantVectorStore(
            client=vector_store.client,
            collection_name=vector_store.collection_name,
        )
        index = VectorStoreIndex.from_vector_store(
            vector_store=qdrant,
            embed_model=embedder.embedding_model(),
        )
        self._retriever = index.as_retriever(similarity_top_k=similarity_top_k)
        logger.info(
            f"Retriever Qdrant prêt (top_k={similarity_top_k}, "
            f"seuil={score_threshold})."
        )

    @classmethod
    def from_config(cls, config: Configuration | None = None) -> "IRetriever":
        """Crée le retriever décrit sous `retriever.params` dans le YAML."""
        config = config or get_config()
        params = config.section("retriever").get("params") or {}

        # Seule la recherche par similarité est prise en charge par Qdrant
        # dans LlamaIndex : un autre « search_type » est ignoré.
        search_type = params.get("search_type", "similarity")
        if search_type != "similarity":
            logger.warning(
                f"search_type « {search_type} » non pris en charge : "
                "recherche par similarité utilisée."
            )

        return cls(
            vector_store=IVectorStore.from_config(config),
            embedder=IEmbedder.from_config(config),
            similarity_top_k=int(params.get("similarity_top_k", DEFAULT_TOP_K)),
            score_threshold=float(
                params.get("score_threshold", DEFAULT_SCORE_THRESHOLD)
            ),
        )

    def retrieve(self, query: str) -> list[NodeWithScore]:
        """Renvoie les passages dont le score dépasse le seuil configuré."""
        candidates = self._retriever.retrieve(query)
        kept = [
            node for node in candidates
            if node.score is None or node.score >= self.score_threshold
        ]
        logger.info(
            f"{len(kept)}/{len(candidates)} candidats Qdrant au-dessus du seuil."
        )
        return kept


def load_docstore() -> SimpleDocumentStore:
    """Charge le docstore qui contient les articles complets (nœuds parents)."""
    if not DOCSTORE_PATH.exists():
        raise FileNotFoundError("Docstore introuvable. Exécute l'ingestion : python ingest.py")

    return SimpleDocumentStore.from_persist_path(persist_path=str(DOCSTORE_PATH))


class ArticleLibrary:
    """Docstore + index des articles, rechargés quand le fichier change.

    Quand un document est ajouté ou retiré via la base documentaire,
    l'assistant voit la nouvelle version sans redémarrer.
    """

    def __init__(self) -> None:
        self._modified_at: float | None = None
        self.docstore = SimpleDocumentStore()
        self.article_index: dict[str, list[BaseNode]] = {}
        self.refresh()

    def refresh(self) -> None:
        """Recharge le docstore s'il a été modifié depuis le dernier chargement."""
        modified_at = DOCSTORE_PATH.stat().st_mtime if DOCSTORE_PATH.exists() else None
        if modified_at == self._modified_at:
            return

        self.docstore = load_docstore()
        self.article_index = build_article_index(self.docstore)
        self._modified_at = modified_at
        logger.info("Docstore (re)chargé.")


def get_parent_article(node: NodeWithScore, docstore: SimpleDocumentStore) -> BaseNode:
    """Remonte du passage (chunk) vers l'article complet, s'il n'est pas trop long."""
    chunk = node.node
    parent_info = chunk.parent_node

    if parent_info is None:
        return chunk

    article = docstore.get_node(parent_info.node_id, raise_error=False)

    if article is None or len(article.get_content()) > MAX_ARTICLE_CHARS:
        return chunk

    return article


def build_article_index(docstore: SimpleDocumentStore) -> dict[str, list[BaseNode]]:
    """Index {numéro d'article: [articles]} des codes, du plus prioritaire au moins prioritaire.

    Seuls les textes principaux sont indexés (pas les décrets en annexe,
    qui ont leur propre numérotation).
    """
    index = {}
    for node in docstore.docs.values():
        metadata = node.metadata
        if metadata.get("node_type") == "ARTICLE" and metadata.get("is_main_text"):
            index.setdefault(metadata["article_number"], []).append(node)

    for nodes in index.values():
        nodes.sort(key=lambda n: n.metadata.get("priority", DEFAULT_PRIORITY))

    logger.info(f"Index des articles : {len(index)} numéros d'articles.")
    return index


def find_articles_in_question(question: str, article_index: dict) -> list[BaseNode]:
    """Si la question cite "article N", renvoie directement cet article (sans recherche vectorielle)."""
    articles = []
    # 1) on repère le groupe "articles 330 et 335", 2) on en extrait chaque numéro
    for match in ARTICLE_IN_QUESTION.finditer(question):
        for number, suffix in re.findall(ARTICLE_NUMBER, match.group(1), re.IGNORECASE):
            key = article_number(number, suffix)
            articles.extend(article_index.get(key, [])[:MAX_DIRECT_ARTICLES])
    return articles
