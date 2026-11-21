"""Tables de la base documentaire."""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.query import Base

DEFAULT_PRIORITY = 4


class DocumentStatus(StrEnum):
    """Cycle de vie d'un document.

    pending -> approved -> processing -> ready
                                      -> failed (relançable)
    pending -> rejected
    """

    PENDING = "pending"  # proposé par un utilisateur, à valider
    APPROVED = "approved"  # validé, en attente d'ingestion
    PROCESSING = "processing"  # conversion et indexation en cours
    READY = "ready"  # indexé : utilisé par l'assistant et lisible
    FAILED = "failed"  # échec de l'ingestion
    REJECTED = "rejected"  # refusé par un administrateur


class Document(Base):
    """Un document de la base documentaire (PDF ou DOCX)."""

    __tablename__ = "documents"

    # Pour les documents d'origine : nom du fichier sans extension
    # (c'est aussi le `document_id` des nœuds dans Qdrant)
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text, default="")
    original_name: Mapped[str] = mapped_column(String(300))
    file_path: Mapped[str] = mapped_column(String(500))  # relatif à data/
    file_type: Mapped[str] = mapped_column(String(10))  # "pdf" ou "docx"
    size_bytes: Mapped[int] = mapped_column(default=0)
    page_count: Mapped[int | None] = mapped_column(default=None)
    priority: Mapped[int] = mapped_column(default=DEFAULT_PRIORITY)
    status: Mapped[str] = mapped_column(
        String(20), default=DocumentStatus.PENDING, index=True
    )
    status_message: Mapped[str] = mapped_column(Text, default="")
    chunk_count: Mapped[int | None] = mapped_column(default=None)
    uploaded_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.now, onupdate=datetime.now
    )

    @property
    def is_ready(self) -> bool:
        return self.status == DocumentStatus.READY

    def __repr__(self) -> str:
        return f"Document(id={self.id!r}, status={self.status!r})"
