from llama_index.core.tools import RetrieverTool, QueryEngineTool
from app.services.embeddings.embeder import embedding_model
from app.services.processing.chuncker import chunk_documents
from app.services.embeddings.vector_store import client_qdrant
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.core.postprocessor import SentenceTransformerRerank
from llama_index.core.query_engine import RetrieverQueryEngine
from app.core.loger import setup_logging
from pathlib import Path

logger = setup_logging()
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DOCSTORE_PATH = PROJECT_ROOT / "data" / "docstore" / "docstore.json"

def create_retriever():

    # initialiser le client

    client = client_qdrant()

    # model embedding
    embedding = embedding_model()

    # store the embeddings vector created apart from data .md to qdrant

    if not client.collection_exists:
        raise RuntimeError(f"La collection qdrant n'existe pas")

    vectore_store = QdrantVectorStore(
        client=client,
        collection_name="douane",
    )

    # Charger les nœuds parents sauvegardés
    if not DOCSTORE_PATH.exists():
        raise FileNotFoundError(
            "Docstore introuvable. Exécute l'ingestion."
        )

    docstore = SimpleDocumentStore.from_persist_path(
        persist_path=str(DOCSTORE_PATH)
    )

    storage_context = StorageContext.from_defaults(
        vector_store=vectore_store,
        docstore=docstore,
    )

    vector_index = VectorStoreIndex.from_vector_store(
        vector_store=vectore_store,
        embed_model=embedding
    )
    

    logger.info("Indexation qdrant terminée")
    # retriever

    retriever_object = vector_index.as_retriever(
        similarity_top_k=30
        )
    # outil tool pour l'agent

    return retriever_object

"""
 Definir un tool de reranking avec un cross-encoder qui analyse le query
 et les documents de Vectorstore pour recuperer les 05/20 meilluers
 candidats

"""

def search_reranking(retriever) -> SentenceTransformerRerank:

    """Applique un cross encoder aux candidats retournes par qdrant"""
    logger.info(f"Initialisation du modèle Reranking")
    reranker = SentenceTransformerRerank(
        top_n=5,
        model='BAAI/bge-reranker-base',
        device='cpu'
    )
    
    return RetrieverQueryEngine.from_args(
        retriever=retriever,
        node_postprocessors=[reranker]
    )


def reranker_tool():

    "Expose le pipeline retrieval + reranking à l'agent"

    
    retriever_object = create_retriever()
    
    query_engine = search_reranking(retriever=retriever_object)

    return QueryEngineTool.from_defaults(
        query_engine=query_engine,
        name='douane_reranker',
        description=(
            "Recherche dans les textes douaniers du Bénin. "
            "Récupère des passages candidats dans Qdrant, les reclasse "
            "avec un cross-encoder et retourne les cinq passages "
            "les plus pertinents pour répondre à la question."
        )
    )