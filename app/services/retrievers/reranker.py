"""Reranker : trie les passages retrouvés par Qdrant selon leur pertinence.

Un cross-encoder lit la question et chaque passage ensemble, puis leur
donne un score. On ne garde que les `top_n` meilleurs passages.

Les modèles disponibles sont décrits dans app/core/free_config.yml,
section « reranker ».
"""

from llama_index.core.postprocessor import SentenceTransformerRerank
from llama_index.core.schema import NodeWithScore, QueryBundle

from app.core.loger import setup_logging
from app.services.configer.call_config import Configuration, get_config

logger = setup_logging()

DEFAULT_RERANKER = "first_reranker"
DEFAULT_TOP_N = 5
DEFAULT_DEVICE = "cpu"


class IReranker:
    """Cross-encoder qui garde les meilleurs passages parmi les candidats."""

    def __init__(
        self,
        model_name: str,
        top_n: int = DEFAULT_TOP_N,
        device: str = DEFAULT_DEVICE,
    ) -> None:
        self.model_name = model_name
        self.top_n = top_n
        self.device = device

        logger.info(f"Chargement du reranker {model_name} (top_n={top_n}).")
        self._model = SentenceTransformerRerank(
            model=model_name,
            top_n=top_n,
            device=device,
        )

    @classmethod
    def from_config(
        cls,
        name: str = DEFAULT_RERANKER,
        config: Configuration | None = None,
    ) -> "IReranker":
        """Crée le reranker décrit sous `reranker.<name>` dans le fichier YAML."""
        config = config or get_config()
        section = config.section("reranker").get(name)
        if not section:
            raise KeyError(f"Reranker « {name} » absent de la configuration")

        params = section.get("params") or {}
        if "model_name" not in params:
            raise KeyError(f"« model_name » manquant pour le reranker « {name} »")

        return cls(
            model_name=params["model_name"],
            top_n=int(params.get("top_n", DEFAULT_TOP_N)),
            device=params.get("device", DEFAULT_DEVICE),
        )

    def rerank(self, query: str, nodes: list[NodeWithScore]) -> list[NodeWithScore]:
        """Renvoie les `top_n` passages les plus pertinents pour la question."""
        if not nodes:
            return []

        reranked = self._model.postprocess_nodes(
            nodes,
            query_bundle=QueryBundle(query_str=query),
        )
        logger.info(f"{len(reranked)}/{len(nodes)} passages retenus après reranking.")
        return reranked

    def __repr__(self) -> str:
        return f"IReranker(model_name={self.model_name!r}, top_n={self.top_n})"
