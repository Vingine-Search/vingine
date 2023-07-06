import os
import utils
import asyncio
import aiofiles
import analysis_audio
import analysis_video

from constants import STORAGE_DIR
from index import info_db, segments_db, IndexDBError
from fastapi import FastAPI, UploadFile, HTTPException


api = FastAPI()
tasks = {}

async def update_status_when_finished(analysis_tasks, id, path):
    """Updates the video status when analysis on it if finished."""
    try:
        await asyncio.gather(*analysis_tasks)
        info_db.update_documents([
            {"id": id, "status": "processed"}
        ])
    except Exception as e:
        # Cancel all the tasks if one of them fails.
        for task in analysis_tasks:
            try:
                task.cancel()
            except:
                pass
        info_db.update_documents([
            {"id": id, "status": f"Analysis Failed ({e})"}
        ])
    tasks.pop(id)
    # Remove the video from the file system after analysis is complete.
    os.remove(path)

@api.post('/analyse')
async def analyse(video: UploadFile, id: str, name: str, analysis_type: str):
    """Runs analysis on a video."""
    # At this point, we are assuming that the extension and file format is correct (handled in the demo backend).
    extension = '.' + video.filename.split(".")[-1]
    os.mkdir(os.path.join(STORAGE_DIR, id))
    path = os.path.join(STORAGE_DIR, id, "video") + extension
    async with aiofiles.open(path, 'wb') as file:
        while contents := await video.read(256 * 1024):
            await file.write(contents)
    analysis_type = analysis_type.replace("both", "audio & video")
    duration = utils.get_video_duration(path)
    info_db.add_documents([{
        "id": id,
        "title": name,
        "type": analysis_type,
        "duration": duration,
        # Variants: "processing", "processed", "error_msg"
        "status": "processing"
    }])
    analysis_tasks = []
    if "audio" in analysis_type:
        analysis_tasks.append(analysis_audio.analyse(id, name, path))
    if "video" in analysis_type:
        analysis_tasks.append(analysis_video.analyse(id, name, path, duration))
    # Fire a call back to update the video status when it's finished.
    tasks[id] = asyncio.create_task(update_status_when_finished(analysis_tasks, id, path))

@api.get('/status')
def status(id: str):
    """Gets the analysis status for a video."""
    try:
        doc = info_db.get_document(id)
        if doc.status == "processing":
            return "Video is still being processed"
        elif doc.status == "processed":
            return f"Video has been fully processed for {doc.type}"
        else:
            raise HTTPException(500, f"Analysis for video '{id}' has failed: {doc.status}")
    except IndexDBError:
        raise HTTPException(404, f"Unknown video '{id}'")

@api.get('/info')
def info(id: str):
    """Loads all video data from the index."""
    try:
        info = info_db.get_document(id)
        if info.status != "processed":
            raise HTTPException(400, "The analysis for this video '{id}' isn't available. Analysis status: {info.status}")
        asr, dsc, vtt = utils.get_fs_data(id)
        # Maximum of 100 combined (topic/visual) segments per video.
        segments = segments_db.search(id, {'limit': 100})['hits']
        scene_segments = []
        topic_segments = []
        for segment in segments:
            _, analysis, frm, to = segment["id"].split("_")
            if analysis == "v":
                scene_segments.append({"from": frm, "to": to, "title": segment["segment_title"]})
            else:
                topic_segments.append({"from": frm, "to": to, "title": segment["segment_title"]})
        return {
            "title": info.title,
            "duration": info.duration,
            "scene_segments": scene_segments,
            "topic_segments": topic_segments,
            "asr": utils.split_lines(asr),
            "dsc": utils.split_lines(dsc),
            "vtt": vtt,
        }
    except IndexDBError:
        raise HTTPException(404, f"Unknown video '{id}'")

@api.get('/search')
def search(query: str):
    """Look up the query in the index."""
    # Cache the info per query since the same video will probably hit multiple times.
    info_cache = {}
    def _get_info(id):
        if id not in info_cache:
            # The ID must be in the info index since it's in the segments one.
            info_cache[id] = info_db.get_document(id)
        return info_cache[id]
    def _mapper(doc):
        id, analysis, frm, to = doc["id"].split("_")
        return {
            "id": id,
            "video_title": _get_info(id).title,
            "from": frm,
            "to": to,
            "duration": _get_info(id).duration,
            "segment_type": "scene" if analysis == "v" else "topic",
            "segment_title": doc["segment_title"],
        }
    result = segments_db.search(query, {'limit': 1000})['hits']
    return list(map(_mapper, result))
