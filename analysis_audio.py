import os, re
import asyncio
import threading
from constants import SEM
from utils import wait_to_inspect

import tensorflow as tf
gpus = tf.config.experimental.list_physical_devices('GPU')
if gpus:
    for gpu in gpus:
        tf.config.experimental.set_memory_growth(gpu, True)


from audio_analysis.whisper_asr.asr import main as asr, init_asr
from audio_analysis.whisper_asr.bounder import main as bound
from audio_analysis.topic_segmentation.predict_mod import predict, init_topic

tokenizer, model = None, None

async def analyse(id: str, title: str, path: str):
    # TODO: Run an API on the output of the topic segmenter. (Done using some pretrained model, bad performance)
    # TODO: Store transcript per second file [id].asr (Done)
    # TODO: Store CC [id].vtt (Done)
    async with SEM:
        exp = [None]
        # We are offloading the sync task to another thread so it doesn't block our server async runtime.
        off_server_task = threading.Thread(target=sync_analyse, args=(id, title, path, exp), daemon=True)
        off_server_task.start()
        while off_server_task.is_alive():
            # await to yield the control back to the executor for other tasks to run.
            await asyncio.sleep(0.1)
        off_server_task.join()
        if exp[0] != None:
            raise RuntimeError(exp[0])

def init_titler():
    global tokenizer, model
    print("Loading the title generator")
    from transformers import AutoTokenizer, T5ForConditionalGeneration
    tokenizer = AutoTokenizer.from_pretrained("JulesBelveze/t5-small-headline-generator")
    print("Loaded the title generator tokenizer")
    model = T5ForConditionalGeneration.from_pretrained("JulesBelveze/t5-small-headline-generator")
    print("Loaded the title generator model")

def get_title(text: str) -> str:
    global tokenizer, model
    if tokenizer is None:
        init_titler()

    WHITESPACE_HANDLER = lambda k: re.sub('\s+', ' ', re.sub('\n+', ' ', k.strip()))

    input_ids = tokenizer(
        [WHITESPACE_HANDLER(text)],
        return_tensors="pt",
        padding="max_length",
        truncation=True,
        max_length=384
    )["input_ids"]

    output_ids = model.generate(
        input_ids=input_ids,
        max_length=20,
        no_repeat_ngram_size=2,
        num_beams=4
    )[0]

    title = tokenizer.decode(
        output_ids,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=False
    )
    title = title[0].upper() + title[1:]
    return title

def sync_analyse(id: str, title: str, path: str, exp: list):
    try:
        from index import segments_db
        # Load the topic segments.
        base_name = os.path.splitext(path)[0]
        # Generate the vtt & asr & txt files.
        asr(path)
        try:
            # Generate the topics file.
            predict(base_name + '.txt')
        except ValueError:
            # The text might be too short to make up a single batch for topic segmentation.
            # Assume it's one topic and carry on.
            os.system(f"cp {base_name + '.txt'} {base_name + '.topics'}")

        # -------------> INSPECT HERE
        wait_to_inspect(f"Generated topics file: {base_name + '.topics'}", base_name + '.topics')
        # Generate the bounds file.
        bound(base_name + '.topics', base_name + '.asr')
        topics = open(base_name + '.topics').read().split('\n\n')
        bounds = open(base_name + '.bounds').read().split('\n')
        # We don't need these files anymore.
        os.remove(base_name + ".txt")
        os.remove(base_name + '.topics')
        os.remove(base_name + '.bounds')
        # Get the topic text and the start and end time.
        topics = [(txt, int(tim.split()[0]), int(tim.split()[1])) for txt, tim in zip(topics, bounds)]
        docs = [{"id": f"{id}_t_{frm}_{to}",
                    "video_title": title,
                    "segment_title": get_title(txt),
                    "segment_content": txt} for txt, frm, to in topics]
        segments_db.add_documents(docs)
    except Exception as e:
        exp[0] = f"Audio Analysis Failed: {e}"

init_asr()
init_topic()
init_titler()
