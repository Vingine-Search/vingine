import json, time
import meilisearch
from utils import try_open
# Re-exported
from meilisearch.errors import MeilisearchApiError as IndexDBError


def wait_on(task):
    while client.get_task(task.task_uid).status not in ["succeeded", "failed"]:
        time.sleep(0.001)

client = meilisearch.Client('http://127.0.0.1:7700', try_open("master_key", None))

wait_on(client.create_index("info"))
info_db = client.index("info")

wait_on(client.create_index("segments"))
segments_db = client.index("segments")

# Set an error status for every video that hasn't been fully processed before shutting down.
interrupted_analysis = [{"id": doc.id, "status": "Analysis Interrupted"}
                        for doc in info_db.get_documents().results
                        if doc.status == "processing"]
if interrupted_analysis:
    info_db.update_documents(interrupted_analysis)

# Info DB configuration:
pass

# Segment DB configuration:
segments_db.update_searchable_attributes([
    # Search by ID is enabled to get all info about a specific video ID.
    "id", "video_title", "segment_content"
])
segments_db.update_displayed_attributes([
    # After searching, we only need the ID and the segment title returned.
    "id", "segment_title"
])
segments_db.update_synonyms(json.loads(try_open("synonyms.json", {})))
segments_db.update_stop_words(json.loads(try_open("stop_words.json", [])))
segments_db.update_typo_tolerance({
    "enabled": True,
    "minWordSizeForTypos": {
        # The minimum word size for accepting 1 typo: [0, twoTypos)
        "oneTypo": 3,
        # The minimum word size for accepting 2 typos: (oneTypo, 255]
        "twoTypos": 5,
    },
    "disableOnAttributes": ["id"],
})
