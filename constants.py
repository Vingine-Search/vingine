import asyncio


STORAGE_DIR = "vingine_data"
"""The directory in which non-db storable content are stored."""

A_SEM = asyncio.Semaphore(1)
"""A global semaphore to limit task concurrency."""

V_SEM = asyncio.Semaphore(1)
"""A global semaphore to limit task concurrency."""

WAIT_TO_INSPECT = True