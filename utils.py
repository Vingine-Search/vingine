import os
import cv2
from constants import STORAGE_DIR


def get_fs_data(id: str):
    no_ext = os.path.join(STORAGE_DIR, id)
    files = [no_ext + ext for ext in ['.asr', '.dsc', '.vtt']]
    return [open(file).read() if os.path.exists(file) else None
            for file in files]

def try_open(file_name: str, default):
    try:
        return open(file_name).read()
    except:
        return default

def get_video_duration(path: str) -> float:
    video = cv2.VideoCapture(path)
    fps = video.get(cv2.CAP_PROP_FPS)
    frm = video.get(cv2.CAP_PROP_FRAME_COUNT)
    return round(frm/fps, 2)
