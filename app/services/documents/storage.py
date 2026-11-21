"""Fichiers de la base documentaire : originaux, aperçus PDF et Markdown.

Arborescence (dans data/) :
- *.pdf, *.docx      : documents d'origine
- uploads/<id>.<ext> : documents proposés par les utilisateurs
- previews/<id>.pdf  : DOCX convertis en PDF pour la liseuse
- processed_data/<id>.md : texte extrait par le parser (utilisé par le RAG)
"""

import shutil
import subprocess
from pathlib import Path

import fitz  # PyMuPDF

from app.core.loger import setup_logging
from app.database.models import Document

logger = setup_logging()

DATA_DIR = Path(__file__).resolve().parents[3] / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
PREVIEW_DIR = DATA_DIR / "previews"
MARKDOWN_DIR = DATA_DIR / "processed_data"

ALLOWED_TYPES = ("pdf", "docx")
MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 Mo
PAGE_ZOOM = 1.6  # résolution des pages affichées dans la liseuse
DOCX_CONVERSION_TIMEOUT = 120  # secondes


def file_type_of(filename: str) -> str:
    return Path(filename).suffix.lower().lstrip(".")


def save_upload(document_id: str, filename: str, content: bytes) -> str:
    """Enregistre un fichier proposé ; renvoie son chemin relatif à data/."""
    file_type = file_type_of(filename)
    if file_type not in ALLOWED_TYPES:
        raise ValueError(f"Format non accepté : .{file_type} (PDF ou DOCX).")
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError("Fichier trop volumineux (50 Mo maximum).")
    if file_type == "pdf" and not content.startswith(b"%PDF"):
        raise ValueError("Le fichier n'est pas un PDF valide.")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path = UPLOAD_DIR / f"{document_id}.{file_type}"
    path.write_bytes(content)
    return str(path.relative_to(DATA_DIR))


def source_path(document: Document) -> Path:
    return DATA_DIR / document.file_path


def markdown_path(document_id: str) -> Path:
    return MARKDOWN_DIR / f"{document_id}.md"


def preview_pdf(document: Document) -> Path | None:
    """PDF affiché dans la liseuse (le DOCX est converti une seule fois)."""
    source = source_path(document)
    if document.file_type == "pdf":
        return source if source.exists() else None

    preview = PREVIEW_DIR / f"{document.id}.pdf"
    if preview.exists():
        return preview

    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if soffice is None:
        logger.warning("LibreOffice absent : pas d'aperçu pour les DOCX.")
        return None

    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    converted = PREVIEW_DIR / f"{source.stem}.pdf"
    try:
        subprocess.run(
            [soffice, "--headless", "--convert-to", "pdf",
             "--outdir", str(PREVIEW_DIR), str(source)],
            check=True,
            capture_output=True,
            timeout=DOCX_CONVERSION_TIMEOUT,
        )
    except (subprocess.SubprocessError, OSError) as error:
        logger.error(f"Conversion DOCX -> PDF impossible ({source.name}) : {error}")
        return None

    # LibreOffice garde le nom du fichier source : on le renomme avec l'id
    if converted != preview:
        converted.replace(preview)
    return preview if preview.exists() else None


def count_pages(pdf: Path) -> int:
    with fitz.open(pdf) as document:
        return document.page_count


def render_page(pdf: Path, page_number: int, zoom: float = PAGE_ZOOM) -> bytes:
    """Image PNG d'une page (numérotée à partir de 1)."""
    with fitz.open(pdf) as document:
        page = document.load_page(page_number - 1)
        pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        return pixmap.tobytes("png")


def delete_files(document: Document) -> None:
    """Supprime l'aperçu, le Markdown et, pour un upload, le fichier source."""
    paths = [PREVIEW_DIR / f"{document.id}.pdf", markdown_path(document.id)]
    if document.file_path.startswith("uploads/"):
        paths.append(source_path(document))

    for path in paths:
        path.unlink(missing_ok=True)
