import warnings
warnings.filterwarnings("ignore")

import sys
import wave
from piper import PiperVoice

print("Loading Piper model...", flush=True)
voice = PiperVoice.load("en_GB-alan-medium.onnx")
print("READY", flush=True)

for line in sys.stdin:
    text = line.strip()
    if not text:
        continue

    with wave.open("tts_out.wav", "wb") as wf:
        voice.synthesize_wav(text, wf)

    print("DONE", flush=True)