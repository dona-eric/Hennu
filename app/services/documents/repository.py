"""Lecture et écriture des documents dans la base SQLite."""

from collections.abc import Iterable

from sqlalchemy import func, select

from app.database.models import Document
from app.database.query import SessionLocal, init_db

# Les tables sont créées au premier import (sans effet si elles existent)
init_db()


def create_document(**fields) -> Document:
    document = Document(**fields)
    with SessionLocal() as session:
        session.add(document)
        session.commit()
    return document


def get_document(document_id: str) -> Document | None:
    with SessionLocal() as session:
        return session.get(Document, document_id)


def list_documents(statuses: Iterable[str] | None = None) -> list[Document]:
    """Documents triés par priorité puis par titre (filtrés par statut)."""
    query = select(Document).order_by(Document.priority, Document.title)
    if statuses is not None:
        query = query.where(Document.status.in_(list(statuses)))

    with SessionLocal() as session:
        return list(session.scalars(query))


def update_document(document_id: str, **fields) -> Document:
    with SessionLocal() as session:
        document = session.get(Document, document_id)
        if document is None:
            raise KeyError(f"Document « {document_id} » introuvable")
        for name, value in fields.items():
            setattr(document, name, value)
        session.commit()
        return document


def delete_document(document_id: str) -> None:
    with SessionLocal() as session:
        document = session.get(Document, document_id)
        if document is not None:
            session.delete(document)
            session.commit()


def count_by_status() -> dict[str, int]:
    query = select(Document.status, func.count()).group_by(Document.status)
    with SessionLocal() as session:
        return {status: count for status, count in session.execute(query)}
