"""Modèle d'embedding (section « embedder » du YAML)."""

from functools import lru_cache

from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from app.core.loger import setup_logging
from app.services.configer.call_config import Configuration, get_config

logger = setup_logging()

DEFAULT_EMBEDDING_MODEL = "BAAI/bge-m3"
DEFAULT_DIMENSION = 1024
DEFAULT_DEVICE = "cpu"


class IEmbedder:
    def __init__(
        self,
        model_name: str = DEFAULT_EMBEDDING_MODEL,
        dimension: int = DEFAULT_DIMENSION,
        device: str = DEFAULT_DEVICE,
        normalize: bool = True,
    ) -> None:
        self.model_name = model_name
        self.dimension = dimension
        self.device = device
        self.normalize = normalize

    @classmethod
    def from_config(cls, config: Configuration | None = None) -> "IEmbedder":
        """Construit IEmbedder depuis la section `embedder.params` du YAML."""
        config = config or get_config()
        params = config.section("embedder").get("params") or {}

        return cls(
            model_name=params.get("model_name", DEFAULT_EMBEDDING_MODEL),
            dimension=int(params.get("dimension_embedding", DEFAULT_DIMENSION)),
            device=params.get("device", DEFAULT_DEVICE),
            normalize=bool(params.get("normalize_embedding", True)),
        )

    def embedding_model(self) -> HuggingFaceEmbedding:
        """Modèle d'embedding HuggingFace, partagé dans tout le processus."""
        return _load_model(self.model_name, self.device, self.normalize)


@lru_cache(maxsize=2)
def _load_model(model_name: str, device: str, normalize: bool) -> HuggingFaceEmbedding:
    """Charge le modèle une seule fois (l'assistant et l'ingestion le partagent)."""
    try:
        model_embedding = HuggingFaceEmbedding(
            model_name=model_name,
            device=device,
            normalize=normalize,
        )
    except Exception as error:
        logger.error(
            f"Erreur lors de l'initialisation du modèle d'embedding "
            f"({model_name}) : {error}"
        )
        raise

    logger.info(f"Modèle d'embedding initialisé : {model_name} (device={device}).")
    return model_embedding
