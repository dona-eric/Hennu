"""Base documentaire : point d'entrée unique pour l'interface.

Cycle d'un document proposé par un utilisateur :
    submit_document()  -> en attente de validation (pending)
    approve_document() -> ingestion en arrière-plan (approved -> processing)
                       -> prêt (ready) ou échec (failed, relançable)
    reject_document()  -> refusé (rejected), fichier supprimé
"""

import re
import threading
from uuid import uuid4

from app.core.config import DEFAULT_PRIORITY, DOCUMENTS
from app.core.loger import setup_logging
from app.database.models import Document, DocumentStatus
from app.services.documents import repository, storage
from app.services.processing.ingestion import (
    index_document,
    remove_document_from_index,
)
from app.services.processing.loader import get_files
from app.services.processing.parser import convert_to_markdown

logger = setup_logging()

# Une seule ingestion à la fois : le docstore est un fichier JSON partagé
_ingestion_lock = threading.Lock()

ACTIVE_STATUSES = (DocumentStatus.APPROVED, DocumentStatus.PROCESSING)


# ------------------------------------------------------------------
# Initialisation
# ------------------------------------------------------------------

def init_library() -> None:
    """À appeler une fois au démarrage du serveur."""
    _register_existing_documents()
    _recover_interrupted_ingestions()


def _register_existing_documents() -> None:
    """Enregistre en base les documents d'origine présents dans data/."""
    for path in get_files():
        file_type = storage.file_type_of(path.name)
        if file_type not in storage.ALLOWED_TYPES:
            continue
        if repository.get_document(path.stem) is not None:
            continue

        info = DOCUMENTS.get(path.stem, {})
        converted = storage.markdown_path(path.stem).exists()
        repository.create_document(
            id=path.stem,
            title=info.get("title") or _readable_title(path.stem),
            original_name=path.name,
            file_path=path.name,
            file_type=file_type,
            size_bytes=path.stat().st_size,
            page_count=storage.count_pages(path) if file_type == "pdf" else None,
            priority=info.get("priority", DEFAULT_PRIORITY),
            status=DocumentStatus.READY if converted else DocumentStatus.FAILED,
            status_message="" if converted else "Document non converti : relancez.",
            uploaded_by="Orion",
        )
        logger.info(f"Document d'origine enregistré : {path.name}")


def _recover_interrupted_ingestions() -> None:
    """Une ingestion coupée par un redémarrage passe en échec (relançable)."""
    for document in repository.list_documents(ACTIVE_STATUSES):
        repository.update_document(
            document.id,
            status=DocumentStatus.FAILED,
            status_message="Ingestion interrompue par un redémarrage : relancez-la.",
        )


def _readable_title(stem: str) -> str:
    """« MANUEL-DE-PROCEDURE_X » -> « Manuel de procedure x »."""
    words = re.sub(r"[-_]+", " ", stem).strip()
    return words[:1].upper() + words[1:].lower()


# ------------------------------------------------------------------
# Consultation
# ------------------------------------------------------------------

def published_documents() -> list[Document]:
    """Documents lisibles par le public (indexés et validés)."""
    return repository.list_documents([DocumentStatus.READY])


def all_documents() -> list[Document]:
    return repository.list_documents()


def get_document(document_id: str) -> Document | None:
    return repository.get_document(document_id)


def is_busy() -> bool:
    """Vrai si une ingestion est en attente ou en cours."""
    return bool(repository.list_documents(ACTIVE_STATUSES))


def page_count(document: Document) -> int:
    """Nombre de pages de l'aperçu (calculé puis mémorisé en base)."""
    if document.page_count:
        return document.page_count

    preview = storage.preview_pdf(document)
    if preview is None:
        return 0

    count = storage.count_pages(preview)
    repository.update_document(document.id, page_count=count)
    return count


def page_image(document: Document, page_number: int) -> bytes | None:
    """Image PNG d'une page, ou None si l'aperçu est indisponible."""
    preview = storage.preview_pdf(document)
    if preview is None:
        return None
    return storage.render_page(preview, page_number)


# ------------------------------------------------------------------
# Proposition et validation
# ------------------------------------------------------------------

def submit_document(
    filename: str,
    content: bytes,
    title: str,
    description: str = "",
    uploaded_by: str = "",
) -> Document:
    """Enregistre un document proposé : il attend la validation d'un admin."""
    if not title.strip():
        raise ValueError("Le titre est obligatoire.")

    document_id = uuid4().hex
    relative_path = storage.save_upload(document_id, filename, content)
    file_type = storage.file_type_of(filename)
    pages = None
    if file_type == "pdf":
        try:
            pages = storage.count_pages(storage.DATA_DIR / relative_path)
        except Exception as error:
            (storage.DATA_DIR / relative_path).unlink(missing_ok=True)
            raise ValueError("Le PDF est illisible ou protégé.") from error

    document = repository.create_document(
        id=document_id,
        title=title.strip(),
        description=description.strip(),
        original_name=filename,
        file_path=relative_path,
        file_type=file_type,
        size_bytes=len(content),
        page_count=pages,
        status=DocumentStatus.PENDING,
        uploaded_by=uploaded_by.strip(),
    )
    logger.info(f"Document proposé : {filename} ({document_id})")
    return document


def approve_document(document_id: str) -> None:
    """Valide un document et lance son ingestion en arrière-plan."""
    repository.update_document(
        document_id,
        status=DocumentStatus.APPROVED,
        status_message="En file d'attente…",
    )
    threading.Thread(
        target=_ingest,
        args=(document_id,),
        name=f"ingestion-{document_id}",
        daemon=True,
    ).start()


# Relancer une ingestion en échec revient à la valider de nouveau
retry_document = approve_document


def update_details(document_id: str, title: str, priority: int) -> None:
    """Modifie le titre et la priorité ; un document indexé est ré-indexé."""
    document = repository.update_document(
        document_id,
        title=title.strip(),
        priority=priority,
    )
    # Le titre et la priorité sont copiés dans chaque passage indexé
    if document.status == DocumentStatus.READY:
        approve_document(document_id)


def reject_document(document_id: str, reason: str = "") -> None:
    """Refuse un document proposé : son fichier est supprimé."""
    document = repository.get_document(document_id)
    if document is None:
        return
    storage.delete_files(document)
    repository.update_document(
        document_id,
        status=DocumentStatus.REJECTED,
        status_message=reason.strip() or "Refusé par un administrateur.",
    )


def remove_document(document_id: str) -> None:
    """Retire un document de l'assistant et de la bibliothèque.

    La ligne reste en base (statut « refusé ») : un document d'origine
    n'est ainsi pas ré-enregistré au prochain démarrage.
    """
    document = repository.get_document(document_id)
    if document is None:
        return
    with _ingestion_lock:
        remove_document_from_index(document_id)
    storage.delete_files(document)
    repository.update_document(
        document_id,
        status=DocumentStatus.REJECTED,
        status_message="Retiré de la base documentaire.",
    )


# ------------------------------------------------------------------
# Ingestion (thread d'arrière-plan)
# ------------------------------------------------------------------

def _ingest(document_id: str) -> None:
    with _ingestion_lock:
        document = repository.get_document(document_id)
        if document is None or document.status != DocumentStatus.APPROVED:
            return

        try:
            markdown_file = storage.markdown_path(document_id)
            if not markdown_file.exists():
                _set_progress(document_id, "Conversion du document en texte…")
                markdown = convert_to_markdown(storage.source_path(document))
                markdown_file.parent.mkdir(parents=True, exist_ok=True)
                markdown_file.write_text(markdown, encoding="utf-8")

            _set_progress(document_id, "Indexation dans la base de l'assistant…")
            markdown = markdown_file.read_text(encoding="utf-8")
            chunk_count = index_document(document_id, markdown)

        except Exception as error:
            logger.exception(f"Échec de l'ingestion du document {document_id}")
            repository.update_document(
                document_id,
                status=DocumentStatus.FAILED,
                status_message=f"Échec : {error}"[:500],
            )
            return

        repository.update_document(
            document_id,
            status=DocumentStatus.READY,
            status_message="",
            chunk_count=chunk_count,
        )
        logger.info(f"Document {document_id} prêt ({chunk_count} passages).")


def _set_progress(document_id: str, message: str) -> None:
    repository.update_document(
        document_id,
        status=DocumentStatus.PROCESSING,
        status_message=message,
    )
