import warnings
warnings.filterwarnings("ignore")

import torchaudio
import time
import os
from chatterbox.tts_turbo import ChatterboxTurboTTS

OUTPUT_FILE = "output.wav"
REFERENCE_WAV = "jarvis-intro-1.wav"
INPUT_FILE = "input.txt"

print("Loading model... (this takes ~60 seconds, only happens once)")
start = time.time()
model = ChatterboxTurboTTS.from_pretrained(device="cuda")
print(f"Model ready in {time.time() - start:.1f}s\n")

def synthesize(text: str):
    wav = model.generate(
        text,
        audio_prompt_path=REFERENCE_WAV,
        cfg_weight=0.3
    )
    torchaudio.save(OUTPUT_FILE, wav, model.sr)

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
            os.system("start output.wav")

    time.sleep(0.3)