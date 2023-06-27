import os
from index import segments_db
from constants import SEM, STORAGE_DIR


async def analyse(id: str, title: str, path: str):
    # TODO: Run an API on the output of the topic segmenter.
    # TODO: Store transcript per second file [id].asr
    # TODO: Store CC [id].vtt
    async with SEM:
        pass
