import os
from index import segments_db
from constants import SEM, STORAGE_DIR

from video_description.inference.s3d_infer import *
from video_description.inference.obj_infer import *
from video_description.inference.ocr_infer import *
from video_description.inference.vrd_infer import *

from typing import List

s3d_model = prepare_s3d_model()
obj_model = prepare_obj_infer()
ocr_model = prepare_easyocr()
vrd_model, rlp_objs, rlp_preds = prepare_vrd_model()

keintics_classes = read_s3d_classes() # 400 class for s3d model
coco_names = read_coco_names() # 80 class for faster rcnn model


def unique_list(res: List[List[str]]) -> List[str]:
    return list(set([item for sublist in res for item in sublist]))


async def analyse(id: str, title: str, path: str):
    # TODO: Run an OCR for better results.
    # TODO: Store description per second file [id].dsc
    async with SEM:
        parent_path = os.path.dirname(path)
        ## Get top Actions
        # extracted frames directory, id is unique
        images_dir = os.path.join(parent_path, f"{id}-frames")
        one_clip(path, images_dir)
        predicted_actions = s3d_infer(images_dir, s3d_model, class_names) # top 5 [(class_name, score)]

        ## Save images paths
        images_paths_list = []
        for image_path in os.listdir(images_dir):
          images_paths_list.append(os.path.join(images_dir, image_path))

        ## Get Objects from frames
        # for batch inference to work, images should be in `images_dir/unkonwn/`
        os.mkdir(os.path.join(images_dir, "unknown"))
        os.system(f"cp {images_dir}/*.jpg {images_dir}/unknown/")
        _, objs_labels = obj_batch_infer(images_dir, obj_model, coco_names)[1]
        predicted_objects = unique_list(objs_labels) # list of objects in the video

        ## Get Relations between objects
        rlps = vrd_batch_infer(images_dir, vrd_model, rlp_objs, rlp_preds)
        predicted_relations = unique_list(rlps) # list of relations between objects in the video

        ## Get Text from frames
        easyocr_labels = easyocr_infer(images_paths_list, ocr_model)
        predicted_text = unique_list(easyocr_labels) # list of text in the video

        ## TODO: complete this & save to db
        pass
