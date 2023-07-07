import os
import cv2
import time
import subprocess
from constants import STORAGE_DIR, WAIT_TO_INSPECT


def get_fs_data(id: str):
    files = [os.path.join(STORAGE_DIR, id, file) for file in ['video.asr', 'video.dsc', 'video.vtt']]
    return [open(file).read() if os.path.exists(file) else None for file in files]

def split_lines(string: str):
    if string:
        return string.strip().split('\n')

def try_open(file_name: str, default):
    try:
        return open(file_name).read()
    except:
        return default

def get_duration_ffprobe(input_video):
    result = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', input_video], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return round(float(result.stdout), 2)

def get_video_duration(path: str) -> float:
    video = cv2.VideoCapture(path)
    fps = video.get(cv2.CAP_PROP_FPS)
    frm = video.get(cv2.CAP_PROP_FRAME_COUNT)
    if fps == 0 or frm == 0:
        # Fall back to ffprobe (for audio-only files)
        return get_duration_ffprobe(path)
    return round(frm/fps, 2)

def wait_to_inspect(wait_on):
    if WAIT_TO_INSPECT:
        open(wait_on, 'w').write('Remove me when you are done.')
        while os.path.exists(wait_on):
            time.sleep(0.1)
