import sys
import tempfile
import os
import whisper
import numpy as np
import scipy.io.wavfile as wav

MODEL_SIZE = "medium"
SAMPLE_RATE = 16000

HALLUCINATION_PHRASES = [
    "they may use numbers",
    "the speaker is a university student",
    "thank you for watching",
    "thanks for watching",
    "please subscribe",
    "subtitles by",
]

print("Loading SpeechToText...", flush=True)
model = whisper.load_model(MODEL_SIZE).to("cuda")
print("READY.", flush=True)

def is_hallucination(text):
    t = text.lower().strip()
    if len(t) < 2:
        return True
    for phrase in HALLUCINATION_PHRASES:
        if phrase in t:
            return True
    return False

def read_exact(n):
    data = b""
    while len(data) < n:
        chunk = sys.stdin.buffer.read(n - len(data))
        if not chunk:
            return None
        data += chunk
    return data

while True:
    header = read_exact(4)
    if header is None:
        break

    length = int.from_bytes(header, byteorder="little")
    pcm_data = read_exact(length)
    if pcm_data is None:
        break

    audio_np = np.frombuffer(pcm_data, dtype=np.int16)

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp_path = tmp.name
    tmp.close()

    wav.write(tmp_path, SAMPLE_RATE, audio_np)

    result = model.transcribe(
        tmp_path,
        language="en",
        initial_prompt="The speaker is a university student from Iraq. They may use numbers like 1, 2, 3, 4 and abbreviations like uni, CS, AI, GPA, prof."
    )

    try:
        os.unlink(tmp_path)
    except PermissionError:
        pass

    text = result["text"].strip()
    no_speech = result.get("segments", [{}])[0].get("no_speech_prob", 0) if result.get("segments") else 0

    if text and not is_hallucination(text) and no_speech < 0.6:
        print("FINAL:", text, flush=True)
    else:
        print("FINAL:", flush=True)