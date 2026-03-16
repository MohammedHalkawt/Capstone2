import warnings
warnings.filterwarnings("ignore")

import numpy as np
import sounddevice as sd
import torchaudio
from chatterbox.tts_turbo import ChatterboxTurboTTS
import threading
import queue
import time
import re

REFERENCE_WAV = "TTS/jarvis-intro-1.wav"

print("Loading model...")
start = time.time()
model = ChatterboxTurboTTS.from_pretrained(device="cuda")
print(f"Model ready in {time.time() - start:.1f}s\n")

def split_sentences(text: str, min_chars: int = 80):
    raw = re.split(r'(?<=[.!?,;])\s+', text.strip())
    raw = [s.strip() for s in raw if s.strip()]

    grouped = []
    buffer = ""

    for sentence in raw:
        if buffer:
            buffer += " " + sentence
        else:
            buffer = sentence

        if len(buffer) >= min_chars:
            grouped.append(buffer)
            buffer = ""

    if buffer:
        if grouped and len(buffer) < min_chars:
            grouped[-1] += " " + buffer
        else:
            grouped.append(buffer)

    return grouped

def generate_chunk(text: str):
    wav = model.generate(text, audio_prompt_path=REFERENCE_WAV)
    audio = wav.squeeze().cpu().numpy()
    return audio

def stream_and_play(text: str):
    chunks = split_sentences(text)
    print(f"Split into {len(chunks)} chunks:")
    for i, s in enumerate(chunks):
        print(f"  {i+1}. {s}")
    print()

    audio_queue = queue.Queue()
    total_start = time.time()

    def generator():
        for i, chunk in enumerate(chunks):
            gen_start = time.time()
            print(f"Generating chunk {i+1}...")
            audio = generate_chunk(chunk)
            print(f"  Ready in {time.time() - gen_start:.1f}s")
            audio_queue.put(audio)
        audio_queue.put(None)

    thread = threading.Thread(target=generator)
    thread.start()

    first = True
    while True:
        audio = audio_queue.get()
        if audio is None:
            break
        if first:
            print(f"\nFirst audio in {time.time() - total_start:.2f}s")
            first = False
        sd.play(audio, samplerate=model.sr)
        sd.wait()

    thread.join()
    print(f"Total time: {time.time() - total_start:.1f}s\n")

while True:
    text = input("Enter text: ").strip()
    if not text:
        continue

    stream_and_play(text)

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