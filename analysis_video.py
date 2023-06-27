import os
from index import segments_db
from constants import SEM, STORAGE_DIR


async def analyse(id: str, title: str, path: str):
    # TODO: Run an OCR for better results.
    # TODO: Store description per second file [id].dsc
    async with SEM:
        pass
