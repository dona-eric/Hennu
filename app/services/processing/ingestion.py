from pathlib import Path

from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.vector_stores.qdrant import QdrantVectorStore

from app.services.processing.chuncker import chunk_documents
from app.services.embeddings.embeder import embedding_model
from app.services.embeddings.vector_store import client_qdrant
from app.core.loger import setup_logging

logger = setup_logging()

COLLECTION_NAME = "douane"

# À adapter selon l'emplacement de ce fichier.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
MARKDOWN_DIR = PROJECT_ROOT / "data" / "processed_data"
DOCSTORE_DIR = PROJECT_ROOT / "data" / "docstore"



def ingest_documents():
    """Lit les Markdown, construit les nœuds et les indexe dans Qdrant."""

    markdown_files = list(MARKDOWN_DIR.glob("*.md"))

    if not markdown_files:
        raise FileNotFoundError(
            f"Aucun fichier Markdown trouvé dans {MARKDOWN_DIR}"
        )

    logger.info("Nombre de fichiers Markdown : %d", len(markdown_files))

    # chunk_documents doit accepter le répertoire ou les chemins des fichiers.
    all_nodes =[]
    leaf_nodes = []

    for file_md in markdown_files:
        logger.info(f" Trraitment de : %s", {file_md.name})
    
        content = file_md.read_text(encoding='utf-8')
        
        if not content.strip():
            logger.warning("Document vide ignoré : %s", file_md.name)
            continue

        document_nodes, file_leaf_nodes = chunk_documents(
            markdown=content
        )

        # 2. Enrichissement des métadonnées
        for node in document_nodes:
            node.metadata["source"] = file_md.name
            node.metadata["document_id"] = file_md.stem

        all_nodes.extend(document_nodes)
        leaf_nodes.extend(file_leaf_nodes)

    if not leaf_nodes:
        raise ValueError("Aucun nœud feuille généré par le chunker.")

    client = client_qdrant()
    embedding = embedding_model()

    vector_store = QdrantVectorStore(
        client=client,
        collection_name=COLLECTION_NAME,
    )

    storage_context = StorageContext.from_defaults(
        vector_store=vector_store,
    )

    # Conserver les nœuds parents et leurs relations.
    storage_context.docstore.add_documents(all_nodes)

    # Indexer uniquement les nœuds feuilles dans Qdrant.
    vector_index = VectorStoreIndex(
        nodes=leaf_nodes,
        embed_model=embedding,
        storage_context=storage_context,
        show_progress=True,
    )

    logger.info(
        "Ingestion terminée : %d nœuds, %d feuilles",
        len(all_nodes),
        len(leaf_nodes),
    )

    DOCSTORE_DIR.mkdir(parents=True, exist_ok=True)

    storage_context.docstore.persist(
        persist_path=str(DOCSTORE_DIR / "docstore.json")
    )

    logger.info("Ingestion terminée avec succès.")

    return vector_index