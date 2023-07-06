import asyncio


STORAGE_DIR = "vingine_data"
"""The directory in which non-db storable content are stored."""

SEM = asyncio.Semaphore(1)
"""A global semaphore to limit task concurrency."""

WAIT_TO_INSPECT = False