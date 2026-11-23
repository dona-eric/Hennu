"""Recherche des documents sources à convertir dans data/."""

from pathlib import Path

from app.core.loger import setup_logging

logger = setup_logging(__name__)

data = Path(__file__).resolve().parents[3] / "data" / 'raws'

SOURCE_EXTENSIONS = (".pdf", ".docx", ".txt", ".xlsx")

# Dossiers gérés par la base documentaire : jamais convertis en lot
# (uploads non validés, aperçus PDF générés, sorties du parser)
EXCLUDED_DIRS = {"uploads", "previews", "processed_data", "docstore"}


def get_files() -> list[Path]:
    logger.info("Initialisation de la recherche des fichiers... ")
    files = []

    for ext in SOURCE_EXTENSIONS:
        for path in data.rglob(f"*{ext}"):
            relative_parts = path.relative_to(data).parts[:-1]
            if not EXCLUDED_DIRS.intersection(relative_parts):
                files.append(path)

    return sorted(files)
