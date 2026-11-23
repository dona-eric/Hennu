"""Connexion à la base SQLite locale (documents et métadonnées)."""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "hennu.db"

# check_same_thread=False : l'ingestion tourne dans un thread séparé
engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
)

# expire_on_commit=False : les objets restent lisibles après la session
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Classe mère des tables SQLAlchemy."""


def init_db() -> None:
    """Crée les tables manquantes (sans toucher aux données existantes)."""
    # Import local : enregistre les modèles avant la création des tables
    from app.database import models  # noqa: F401

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(engine)
