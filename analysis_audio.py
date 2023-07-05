import os, re
from constants import SEM
#from index import segments_db
from utils import wait_to_inspect

from audio_analysis.whisper_asr.asr import main as asr
from audio_analysis.topic_segmentation.predict_mod import predict
from audio_analysis.whisper_asr.bounder import main as bound


async def analyse(id: str, title: str, path: str):
    # TODO: Run an API on the output of the topic segmenter. (Done using some pretrained model, bad performance)
    # TODO: Store transcript per second file [id].asr (Done)
    # TODO: Store CC [id].vtt (Done)
    async with SEM:
        try:
            # Load the topic segments.
            base_name = os.path.splitext(path)[0]
            # Generate the vtt & asr & txt files.
            asr(path)
            # Generate the topics file.
            predict(base_name + '.txt')

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
            docs = [{"id": f"{id}+t+{frm}+{to}",
                    "video_title": title,
                    "segment_title": get_title(txt),
                    "segment_content": txt} for txt, frm, to in topics]
            segments_db.add_documents(docs)
        except Exception as e:
            raise RuntimeError(f"Audio Analysis Failed: {e}")


tokenizer, model = None, None

def get_title(text: str) -> str:
    global tokenizer, model
    if tokenizer is None:
        print("Loading the title generator")
        from transformers import AutoTokenizer, T5ForConditionalGeneration
        tokenizer = AutoTokenizer.from_pretrained("JulesBelveze/t5-small-headline-generator")
        print("Loaded the title generator tokenizer")
        model = T5ForConditionalGeneration.from_pretrained("JulesBelveze/t5-small-headline-generator")
        print("Loaded the title generator model")

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

def ana(path):
    # Load the topic segments.
    base_name = os.path.splitext(path)[0]
    # Generate the vtt & asr & txt files.
    asr(path)
    # Generate the topics file.
    predict(base_name + '.txt')
    # Generate the bounds file.
    bound(base_name + '.topics', base_name + '.asr')
    # Load the topic segments.
    topics = open(base_name + '.topics').read().split('\n\n')
    bounds = open(base_name + '.bounds').read().split('\n')
    # We don't need these files anymore.
    os.remove(base_name + '.topics')
    os.remove(base_name + '.bounds')
    # Get the topic text and the start and end time.
    topics = [(txt, int(tim.split()[0]), int(tim.split()[1])) for txt, tim in zip(topics, bounds)]
    docs = [{"id": f"{id}+t+{frm}+{to}",
            "segment_title": "",#get_title(txt),
            "segment_content": txt} for txt, frm, to in topics]
    return docs

if __name__ == "__main__":
    import sys
    print(ana(sys.argv[1]))
