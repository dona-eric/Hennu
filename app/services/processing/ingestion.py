"""Indexation des documents Markdown dans Qdrant et dans le docstore.

Deux modes :
- ingest_documents()          : ré-ingestion complète (vide la collection)
- index_document(...)         : ajout d'UN document (base documentaire)
- remove_document_from_index  : retrait d'UN document
"""

import os
from pathlib import Path

from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.core.schema import BaseNode
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.core.vector_stores import MetadataFilter, MetadataFilters
from llama_index.vector_stores.qdrant import QdrantVectorStore

from app.core.config import DEFAULT_PRIORITY, DOCUMENTS
from app.core.loger import setup_logging
from app.database.models import DocumentStatus
from app.services.configer.call_config import get_config
from app.services.documents import repository
from app.services.embeddings.embeder import IEmbedder
from app.services.embeddings.vector_store import IVectorStore
from app.services.processing.chuncker import chunk_documents

logger = setup_logging()

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MARKDOWN_DIR = PROJECT_ROOT / "data" / "processed_data"
DOCSTORE_DIR = PROJECT_ROOT / "data" / "docstore"
DOCSTORE_PATH = DOCSTORE_DIR / "docstore.json"


# ------------------------------------------------------------------
# Préparation des nœuds
# ------------------------------------------------------------------

def document_metadata(document_id: str) -> tuple[str, int, str]:
    """Titre, priorité et nom du fichier source d'un document.

    La base documentaire fait foi ; à défaut, on utilise DOCUMENTS
    (app/core/config.py) puis des valeurs par défaut.
    """
    document = repository.get_document(document_id)
    if document is not None:
        return document.title, document.priority, document.original_name

    info = DOCUMENTS.get(document_id, {})
    return (
        info.get("title", document_id),
        info.get("priority", DEFAULT_PRIORITY),
        f"{document_id}.md",
    )


def build_document_nodes(
    markdown: str,
    document_id: str,
) -> tuple[list[BaseNode], list[BaseNode]]:
    """Découpe un document et ajoute ses métadonnées à chaque nœud.

    Renvoie (tous les nœuds, nœuds feuilles à indexer dans Qdrant).
    """
    title, priority, source = document_metadata(document_id)
    all_nodes, leaf_nodes = chunk_documents(markdown=markdown)

    for node in all_nodes:
        node.metadata["source"] = source
        node.metadata["document_id"] = document_id
        node.metadata["document_title"] = title
        node.metadata["priority"] = priority

    return all_nodes, leaf_nodes


# ------------------------------------------------------------------
# Accès au docstore et à Qdrant
# ------------------------------------------------------------------

def load_docstore() -> SimpleDocumentStore:
    if DOCSTORE_PATH.exists():
        return SimpleDocumentStore.from_persist_path(persist_path=str(DOCSTORE_PATH))
    return SimpleDocumentStore()


def save_docstore(docstore: SimpleDocumentStore) -> None:
    """Écriture atomique : l'assistant ne lit jamais un fichier à moitié écrit."""
    DOCSTORE_DIR.mkdir(parents=True, exist_ok=True)
    temporary = DOCSTORE_PATH.with_suffix(".json.tmp")
    docstore.persist(persist_path=str(temporary))
    os.replace(temporary, DOCSTORE_PATH)


def _qdrant_store() -> QdrantVectorStore:
    store = IVectorStore.from_config(get_config())
    return QdrantVectorStore(client=store.client, collection_name=store.collection_name)


# ------------------------------------------------------------------
# Ingestion d'un seul document
# ------------------------------------------------------------------

def index_document(document_id: str, markdown: str) -> int:
    """Ajoute un document à Qdrant et au docstore ; renvoie le nombre de passages.

    Les anciens nœuds du document sont d'abord retirés : relancer
    l'indexation ne crée donc jamais de doublons.
    """
    all_nodes, leaf_nodes = build_document_nodes(markdown, document_id)
    if not leaf_nodes:
        raise ValueError("Aucun passage exploitable dans ce document.")

    remove_document_from_index(document_id)

    embedding = IEmbedder.from_config(get_config()).embedding_model()
    index = VectorStoreIndex.from_vector_store(_qdrant_store(), embed_model=embedding)
    index.insert_nodes(leaf_nodes)

    docstore = load_docstore()
    docstore.add_documents(all_nodes)
    save_docstore(docstore)

    logger.info(f"Document {document_id} indexé : {len(leaf_nodes)} passages.")
    return len(leaf_nodes)


def remove_document_from_index(document_id: str) -> None:
    """Retire tous les nœuds d'un document (Qdrant + docstore)."""
    _qdrant_store().delete_nodes(
        filters=MetadataFilters(
            filters=[MetadataFilter(key="document_id", value=document_id)]
        )
    )

    docstore = load_docstore()
    node_ids = [
        node_id
        for node_id, node in docstore.docs.items()
        if node.metadata.get("document_id") == document_id
    ]
    for node_id in node_ids:
        docstore.delete_document(node_id, raise_error=False)
    if node_ids:
        save_docstore(docstore)

    logger.info(f"Document {document_id} retiré de l'index ({len(node_ids)} nœuds).")


# ------------------------------------------------------------------
# Ré-ingestion complète (python ingest.py)
# ------------------------------------------------------------------

def ingest_documents():
    """Lit tous les Markdown, construit les nœuds et reconstruit l'index."""
    markdown_files = sorted(MARKDOWN_DIR.glob("*.md"))
    if not markdown_files:
        raise FileNotFoundError(f"Aucun fichier Markdown trouvé dans {MARKDOWN_DIR}")

    logger.info("Nombre de fichiers Markdown : %d", len(markdown_files))

    all_nodes = []
    leaf_nodes = []
    leaf_counts: dict[str, int] = {}

    for file_md in markdown_files:
        document_id = file_md.stem
        document = repository.get_document(document_id)
        if document is not None and document.status == DocumentStatus.REJECTED:
            logger.info("Document retiré ignoré : %s", file_md.name)
            continue

        content = file_md.read_text(encoding="utf-8")
        if not content.strip():
            logger.warning("Document vide ignoré : %s", file_md.name)
            continue

        logger.info("Traitement de : %s", file_md.name)
        document_nodes, file_leaf_nodes = build_document_nodes(content, document_id)
        all_nodes.extend(document_nodes)
        leaf_nodes.extend(file_leaf_nodes)
        leaf_counts[document_id] = len(file_leaf_nodes)

    if not leaf_nodes:
        raise ValueError("Aucun nœud feuille généré par le chunker.")

    config = get_config()
    store = IVectorStore.from_config(config)
    embedding = IEmbedder.from_config(config).embedding_model()

    # Ré-ingestion complète : on vide la collection pour éviter les doublons
    store.reset_collection()

    vector_store = QdrantVectorStore(
        client=store.client,
        collection_name=store.collection_name,
    )
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # Conserver les nœuds parents et leurs relations
    storage_context.docstore.add_documents(all_nodes)

    # Indexer uniquement les nœuds feuilles dans Qdrant
    vector_index = VectorStoreIndex(
        nodes=leaf_nodes,
        embed_model=embedding,
        storage_context=storage_context,
        show_progress=True,
    )
    save_docstore(storage_context.docstore)

    # La base documentaire reflète ce qui vient d'être indexé
    for document_id, count in leaf_counts.items():
        if repository.get_document(document_id) is not None:
            repository.update_document(
                document_id,
                status=DocumentStatus.READY,
                status_message="",
                chunk_count=count,
            )

    logger.info(
        "Ingestion terminée : %d nœuds, %d feuilles",
        len(all_nodes),
        len(leaf_nodes),
    )
    return vector_index
