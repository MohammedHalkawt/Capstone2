import warnings
warnings.filterwarnings("ignore")

import wave
import subprocess
import os
import time
from piper import PiperVoice

OUTPUT_FILE = "output.wav"
INPUT_FILE = "input.txt"

print("Loading Piper model...")
start = time.time()
voice = PiperVoice.load("en_GB-alan-medium.onnx")
print(f"Model ready in {time.time() - start:.1f}s\n")

def synthesize(text: str):
    with wave.open(OUTPUT_FILE, "wb") as wf:
        voice.synthesize_wav(text, wf)

print("TTS ready, watching for input...")
last_text = ""

while True:
    if os.path.exists(INPUT_FILE):
        with open(INPUT_FILE, "r") as f:
            text = f.read().strip()

        if text and text != last_text:
            last_text = text
            print(f"Speaking: {text}")
            synthesize(text)
            subprocess.Popen(["start", OUTPUT_FILE], shell=True)

    time.sleep(0.3)