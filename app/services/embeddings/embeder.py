from app.core.loger import setup_logging
from app.core.config import EMBEDDING_MODEL_NAME
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

logger = setup_logging()



def embedding_model()-> HuggingFaceEmbedding:
    """Initialise le modèle d'embedding HuggingFace."""
    try:
        model_embedding = HuggingFaceEmbedding(
            model_name=EMBEDDING_MODEL_NAME,
            device='cpu'
        )
        logger.info("Modèle d'embedding HuggingFace initialisé avec succès.")
        return model_embedding
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation du modèle d'embedding: {e}")
        raise
