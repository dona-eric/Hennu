"""Conversion des documents (PDF, DOCX...) en Markdown via l'API Datalab."""

import asyncio
import os
import pathlib

from datalab_sdk import AsyncDatalabClient, ConvertOptions

from app.core.config import DATALAB_API_KEY
from app.core.loger import setup_logging
from app.services.processing.loader import get_files

logger = setup_logging()

DATALAB_URL = "https://www.datalab.to"
DATALAB_TIMEOUT = 300  # secondes

CONVERT_OPTIONS = ConvertOptions(
    output_format="markdown",
    mode="balanced",
    keep_pageheader_in_output=True,
    paginate=True,
    keep_pagefooter_in_output=True,
    exact_transcription=True,
)


def _client() -> AsyncDatalabClient:
    return AsyncDatalabClient(
        api_key=DATALAB_API_KEY,
        base_url=DATALAB_URL,
        timeout=DATALAB_TIMEOUT,
    )


async def _convert_one(file_path: pathlib.Path) -> str:
    async with _client() as client:
        result = await client.convert(str(file_path), options=CONVERT_OPTIONS)
    return result.markdown


def convert_to_markdown(file_path: pathlib.Path) -> str:
    """Convertit UN document en Markdown (utilisé par la base documentaire)."""
    logger.info(f"Conversion Datalab : {file_path.name}")
    return asyncio.run(_convert_one(file_path))


async def convert_documents_per_batch(output_dir: pathlib.Path):
    """Convertit tous les documents de data/ en une seule fois."""
    async with _client() as client:
        files = get_files()
        logger.info(f"Nombres totals de fichiers {len(files)}")

        tasks = [
            client.convert(str(file_path), options=CONVERT_OPTIONS)
            for file_path in files
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for file_path, result in zip(files, results):
            if isinstance(result, Exception):
                logger.error(f"Error processing {file_path.name}: {result}")
            else:
                output_path = output_dir / f"{file_path.stem}.md"
                output_path.write_text(result.markdown, encoding="utf-8")
                print(f"Saved: {output_path}")


if __name__ == "__main__":
    output_dir = pathlib.Path(__file__).resolve().parents[3] / "data/processed_data"
    os.makedirs(output_dir, exist_ok=True)
    asyncio.run(convert_documents_per_batch(output_dir=output_dir))
