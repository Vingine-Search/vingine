import os
import asyncio
import threading
from constants import V_SEM as SEM
from utils import wait_to_inspect

from video_description.inference.s3d_infer import *
from video_description.inference.obj_infer import *
from video_description.inference.ocr_infer import *
from video_description.inference.vrd_infer import *

from scene_detection.main_re import get_scene_seg

from typing import List

s3d_model = None
obj_model = None
ocr_model = None
vrd_model, rlp_objs, rlp_preds = None, None, None

keintics_classes = read_s3d_classes() # 400 class for s3d model
coco_names = read_coco_names() # 80 class for faster rcnn model

async def analyse(id: str, title: str, path: str, duration: float):
    # TODO: Run an OCR for better results. (Done)
    # TODO: Store description per second file [id].dsc (Done)
    async with SEM:
        exp = [None]
        # We are offloading the sync task to another thread so it doesn't block our server async runtime.
        off_server_task = threading.Thread(target=sync_analyse, args=(id, title, path, duration, exp), daemon=True)
        off_server_task.start()
        while off_server_task.is_alive():
            # await to yield the control back to the executor for other tasks to run.
            await asyncio.sleep(0.1)
        off_server_task.join()
        if exp[0] != None:
            raise RuntimeError(exp[0])

def get_content(descriptions, frm, to):
    print(f"from to (index): {frm} {to}")
    # Keep a list of unique descriptions ordered by when they first appeared
    output = []
    for desc in descriptions[frm:to]:
        for sent in desc:
            if sent not in output:
                output.append(sent)
    return ' '.join(output)

def unique_list(res: List[List[str]]) -> List[str]:
    return list(set([item for sublist in res for item in sublist]))

def init_models():
    global s3d_model, obj_model, ocr_model, vrd_model, rlp_objs, rlp_preds
    s3d_model = prepare_s3d_model()
    obj_model = prepare_obj_infer()
    ocr_model = prepare_easyocr()
    #vrd_model, rlp_objs, rlp_preds = prepare_vrd_model()

def describe(path, start=0, end=5):
    global s3d_model, obj_model, ocr_model, vrd_model, rlp_objs, rlp_preds
    if s3d_model is None:
        init_models()

    ## Get top Actions
    # extracted frames directory, id is unique
    images_dir = one_clip(path, fps=10, start=start, end=end)
    unknown_dir = os.path.join(images_dir, "unknown")
    predicted_actions = s3d_infer(images_dir, s3d_model, keintics_classes) # top 5 [(class_name, score)]
    # Keep only the actions with high enough confidence
    predicted_actions = [action[0] for action in predicted_actions if action[1] > 0.2]
    #print(predicted_actions)

    ## Save images paths
    images_paths_list = []
    for image_path in os.listdir(unknown_dir):
        images_paths_list.append(os.path.join(unknown_dir, image_path))

    ## Get Objects from frames
    # for batch inference to work, images should be in `images_dir/unkonwn/`
    # os.mkdir(os.path.join(images_dir, "unknown"))
    # os.system(f"cp {images_dir}/*.jpg {images_dir}/unknown/")
    _, objs_labels = obj_batch_infer(images_dir, obj_model, coco_names)
    predicted_objects = unique_list(objs_labels) # list of objects in the video
    #print(predicted_objects)

    # ## Get Relations between objects
    # rlps = vrd_batch_infer(images_dir, vrd_model, rlp_objs, rlp_preds)
    # predicted_relations = unique_list(rlps) # list of relations between objects in the video

    ## Get Text from frames
    easyocr_labels = easyocr_infer(images_paths_list, ocr_model)
    predicted_text = unique_list(easyocr_labels) # list of text in the video
    #print(predicted_text)

    os.system(f"rm -rf {images_dir}")
    return predicted_actions + predicted_objects + predicted_text

def sync_analyse(id: str, title: str, path: str, duration: float, exp: list):
    try:
        from index import segments_db
        describe_every = 5
        descriptions = []
        duration = int(duration)
        for i in range(0, duration, describe_every):
            # Make sure the last query is 5s as well.
            if i + describe_every > duration:
                i = duration - describe_every
            descriptions.append(describe(path, i, i + describe_every))

        dsc_file = os.path.splitext(path)[0] + '.dsc'
        seg_file = os.path.splitext(path)[0] + '.seg'

        # every description line represents `describe_every` seconds.
        open(dsc_file, 'w').write('\n'.join([','.join(description) for description in descriptions]))

        if duration > 3 * 60:
            try:
                # Segment the video if it's longer than 3 minutes.
                segments = [str(int(s)) for s in get_scene_seg(path)] + [str(duration)]
                open(seg_file, 'w').write(' '.join(segments))
            except Exception as e:
                open(seg_file + '.failed', 'w').write(f"Segmentation Failed: {e}")
                # Fall back to just one segment.
                open(seg_file, 'w').write(str(duration))
        else:
            # Assume it's one segment and don't do any segmentation.
            open(seg_file, 'w').write(str(duration))

        # -------------> INSPECT HERE
        wait_to_inspect(os.path.join(os.path.dirname(path), "video.wait"))

        descriptions = [line.split(',') for line in open(dsc_file).read().split('\n')]
        segments = [int(s) for s in open(seg_file).read().split()]
        open(dsc_file, 'w').write('\n'.join([' '.join(description) for description in descriptions]))

        docs = []
        frm = 0
        for to in segments:
            tos = round(to/describe_every)
            # Make sure we get the last segment as well.
            if to == segments[-1]:
                tos += 1
            docs.append({
                "id": f"{id}_v_{frm}_{to}",
                "video_title": title,
                "segment_title": "",
                "segment_content": get_content(descriptions, round(frm/describe_every), tos)
            })
            # Update the last from.
            frm = to
        segments_db.add_documents(docs)
    except Exception as e:
        exp[0] = f"Video Analysis Failed: {e}"


init_models()