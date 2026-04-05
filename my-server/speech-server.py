import sys
import tempfile
import os
import whisper
import numpy as np
import scipy.io.wavfile as wav
import struct

MODEL_SIZE = "medium"
SAMPLE_RATE = 16000

print("Loading Whisper model...", flush=True)
model = whisper.load_model(MODEL_SIZE).to("cuda")
print("Model ready.", flush=True)

def read_exact(n):
    """Read exactly n bytes from stdin, blocking until available."""
    data = b""
    while len(data) < n:
        chunk = sys.stdin.buffer.read(n - len(data))
        if not chunk:
            return None
        data += chunk
    return data

while True:
    # Read 4-byte little-endian length header
    header = read_exact(4)
    if header is None:
        break

    length = struct.unpack("<I", header)[0]

    # Read exactly that many PCM bytes
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
    if text:
        print("FINAL:", text, flush=True)
    else:
        print("FINAL:", flush=True)