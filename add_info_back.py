from index import info_db, segments_db, wait_on
from utils import get_video_duration
from collections import defaultdict

wait_on(info_db.delete_all_documents())

analysis_types = defaultdict(set)
durations = {}
titles = {}
docs = set()

for doc in segments_db.get_documents({"limit": 1000}).results:
    id, analysis, _, _ = doc.id.split("_")
    analysis_types[id].add(analysis)
    if id not in docs:
        docs.add(id)
        durations[id] = get_video_duration(f"../demo/backend/videos/{id}.mp4")
        titles[id] = doc.video_title

def get_type(a):
    if "t" in a and "v" in a:
        return "audio & video"
    if "t" in a:
        return "audio"
    if "v" in a:
        return "video"


info = []
for id in docs:
    info.append({
        "id": id,
        "title": titles[id],
        "type": get_type(analysis_types[id]),
        "duration": durations[id],
        "status": "processed",
    })

wait_on(info_db.add_documents(info))