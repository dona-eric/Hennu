"""Connexion à la base vectorielle Qdrant (section « vector_store » du YAML)."""

import qdrant_client
from qdrant_client.models import Distance, VectorParams

from app.core.loger import setup_logging
from app.services.configer.call_config import Configuration, get_config

logger = setup_logging()


class IVectorStore:
    """Accès à une collection Qdrant."""

    def __init__(
        self,
        url: str,
        api_key: str,
        collection_name: str,
        embedding_dimension: int,
    ) -> None:
        self.url = url
        self.api_key = api_key
        self.collection_name = collection_name
        self.embedding_dimension = embedding_dimension
        self.client = self.client_qdrant()

    @classmethod
    def from_config(cls, config: Configuration | None = None) -> "IVectorStore":
        """Crée le vector store décrit sous `vector_store.params` dans le YAML."""
        config = config or get_config()
        params = config.section("vector_store").get("params") or {}

        return cls(
            url=params["url_qdrant"],
            api_key=params.get("api_key") or None,
            collection_name=params["collection_name"],
            embedding_dimension=int(params["embedding_dimension"]),
        )

    def client_qdrant(self) -> qdrant_client.QdrantClient:
        """Connecte le client Qdrant et crée la collection si elle n'existe pas."""
        try:
            client = qdrant_client.QdrantClient(
                url=self.url,
                api_key=self.api_key,
                timeout=120,
            )
        except Exception as error:
            logger.error(f"Erreur de connexion au client Qdrant : {error}")
            raise

        if client.collection_exists(collection_name=self.collection_name):
            logger.info(f"Collection Qdrant {self.collection_name} trouvée.")
        else:
            logger.warning(f"Collection {self.collection_name} absente : création.")
            self._create_collection(client)
        return client

    def reset_collection(self) -> None:
        """Vide entièrement la collection (avant une ré-ingestion complète)."""
        if self.client.collection_exists(collection_name=self.collection_name):
            self.client.delete_collection(collection_name=self.collection_name)
            logger.info(f"Collection {self.collection_name} supprimée.")
        self._create_collection(self.client)

    def _create_collection(self, client: qdrant_client.QdrantClient) -> None:
        """Crée la collection avec la bonne dimension de vecteurs."""
        client.create_collection(
            self.collection_name,
            vectors_config=VectorParams(
                size=self.embedding_dimension,
                distance=Distance.COSINE,
            ),
        )
        logger.info(
            f"Collection {self.collection_name} créée "
            f"(dimension {self.embedding_dimension})."
        )
