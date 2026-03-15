import warnings
warnings.filterwarnings("ignore")

import torchaudio
from chatterbox.tts import ChatterboxTTS
import time

OUTPUT_FILE = "output.wav"
REFERENCE_WAV = "jarvis-intro-1.wav"  # ← put your reference WAV file here

print("Loading model... (this takes ~60 seconds, only happens once)")
start = time.time()
model = ChatterboxTTS.from_pretrained(device="cuda")
print(f"Model ready in {time.time() - start:.1f}s\n")

def synthesize(text: str):
    wav = model.generate(text, audio_prompt_path=REFERENCE_WAV)
    torchaudio.save(OUTPUT_FILE, wav, model.sr)

while True:
    text = input("Enter text: ").strip()
    
    if not text:
        print("No text entered, try again.")
        continue

    print("Generating audio...")
    start = time.time()
    synthesize(text)
    print(f"Done in {time.time() - start:.1f}s → saved to {OUTPUT_FILE}")

    choice = input("Press 1 for more, 0 to quit: ").strip()
    
    if choice == "0":
        print("Shutting down.")
        break
    elif choice == "1":
        print()
        continue
    else:
        print("Invalid input, shutting down.")
        break