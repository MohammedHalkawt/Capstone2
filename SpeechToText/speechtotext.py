import queue
import sounddevice as sd
import json
import re
from vosk import Model, KaldiRecognizer

MODEL_PATH = "SpeechToText/vosk-model-small-en-us-0.15"
SAMPLE_RATE = 16000

print("Loading model...")
model = Model(MODEL_PATH)
recognizer = KaldiRecognizer(model, SAMPLE_RATE)

recognizer.SetWords(True)
recognizer.SetPartialWords(True)

audio_queue = queue.Queue()
last_partial = ""

# ----------------------------
# TEXT NORMALIZATION
# ----------------------------

number_map = {
    "zero":"0","one":"1","two":"2","three":"3","four":"4","five":"5",
    "six":"6","seven":"7","eight":"8","nine":"9","ten":"10",
    "eleven":"11","twelve":"12","thirteen":"13","fourteen":"14",
    "fifteen":"15","sixteen":"16","seventeen":"17","eighteen":"18",
    "nineteen":"19","twenty":"20"
}

common_corrections = {
    "to hours":"two hours",
    "too hours":"two hours",
    "for hours":"four hours",
    "ate pm":"8 pm",
    "won":"one"
}

def normalize_text(text):

    text = text.lower()

    # fix common homophones
    for wrong, correct in common_corrections.items():
        text = text.replace(wrong, correct)

    # convert number words to digits
    words = text.split()
    words = [number_map.get(w, w) for w in words]
    text = " ".join(words)

    # remove duplicate spaces
    text = re.sub(r'\s+', ' ', text).strip()

    return text

# ----------------------------
# AUDIO CALLBACK
# ----------------------------

def audio_callback(indata, frames, time, status):
    audio_queue.put(bytes(indata))


print("🎤 Speak... (Ctrl+C to stop)\n")

with sd.RawInputStream(
    samplerate=SAMPLE_RATE,
    blocksize=4000,
    dtype="int16",
    channels=1,
    callback=audio_callback
):

    while True:
        data = audio_queue.get()

        if recognizer.AcceptWaveform(data):

            result = json.loads(recognizer.Result())
            final_text = result.get("text", "").strip()

            if final_text:
                final_text = normalize_text(final_text)

                print("\nFINAL:", final_text)
                last_partial = ""

        else:
            partial = json.loads(recognizer.PartialResult())
            partial_text = partial.get("partial", "").strip()

            if partial_text and partial_text != last_partial:
                print("\rLIVE:", partial_text, end="", flush=True)
                last_partial = partial_text