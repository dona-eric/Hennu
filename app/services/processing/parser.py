from datalab_sdk import ConvertOptions, AsyncDatalabClient
from app.services.processing.loader import get_files
from app.core.loger import setup_logging
from app.core.config import DATALAB_API_KEY
import asyncio
import pathlib
import os


logger= setup_logging()


async def convert_documents_per_batch(output_dir: pathlib.Path):

    async with AsyncDatalabClient(
        api_key=DATALAB_API_KEY,
        base_url="https://www.datalab.to",  # API endpoint
        timeout=300) as client:

        files = get_files()
        logger.info(f"Nombres totals de fichiers {len(files)}")

        options_convert = ConvertOptions(
            output_format="markdown",
            mode='balanced',
            keep_pageheader_in_output=True,
            paginate=True,
            keep_pagefooter_in_output=True,
            exact_transcription=True
        )
        tasks = [client.convert(str(file_path), options=options_convert) for file_path in files ]
        
        results = await asyncio.gather(
            *tasks, return_exceptions=True)

        for file_path, result in zip(files, results):
            if isinstance(result, Exception):
                logger.error(f"Error processing {file_path.name}: {result}")
            else:
                output_path = pathlib.Path(output_dir / f"{file_path.stem}.md")
                output_path.write_text(result.markdown)
                print(f"Saved: {output_path}")

if __name__=="__main__":
    output_dir = pathlib.Path(__file__).resolve().parents[3] / 'data/processed_data'
    os.makedirs(output_dir, exist_ok=True)
    asyncio.run(convert_documents_per_batch(output_dir=output_dir))


        
