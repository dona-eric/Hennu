from app.core.config import EMBEDDING_DIMENSION,QDRANT_API_KEY,QDRANT_URL
from app.core.loger import setup_logging
import qdrant_client
from qdrant_client.models import Distance, VectorParams

logger = setup_logging()

def client_qdrant():
    """
        Initialisation du client qdrant 
    
    """
    collection_name = "douane"
    try:
        client = qdrant_client.QdrantClient(
            api_key=QDRANT_API_KEY,
            timeout=120,
            url=QDRANT_URL
        )

        if not client.collection_exists(collection_name=collection_name):
            logger.error(f"La collection n'exist pas dans qdrant. Veuillez en créer")

            client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                            size=EMBEDDING_DIMENSION,
                            distance=Distance.COSINE
                    )
                )
            logger.info(f"La Collection {collection_name} est crée avec succès")
        else:
            logger.error(f"La collection qdrant {collection_name} existe deja")
        return client
    except Exception as e:
        logger.error(f"Erreur de creation ou de connexion au client qqdrant {e}")
        raise e