import warnings
warnings.filterwarnings("ignore")
import os
os.environ["TQDM_DISABLE"] = "1"

import sys
import re
import wave
import numpy as np
import torch
import torchaudio
import scipy.signal as signal
from chatterbox.tts_turbo import ChatterboxTurboTTS

# ---------------- Normalization ----------------
ROMAN = {
    'viii': 'eight', 'vii': 'seven', 'vi': 'six',
    'iv': 'four', 'iii': 'three', 'ii': 'two', 'ix': 'nine',
    'v': 'five', 'x': 'ten'
}

def normalize(text):
    roman_upper = set(k.upper() for k in ROMAN.keys())

    def expand_acronyms(match):
        acronym = match.group(1)
        if acronym in roman_upper:
            return acronym
        return '. '.join(list(acronym)) + '.'

    text = re.sub(r'\b([A-Z]{2,5})\b(?! \d{3,4})', expand_acronyms, text)
    text = text.lower()

    for roman, word in ROMAN.items():
        text = re.sub(r'\b' + roman.lower() + r'\b', word, text)

    text = re.sub(r'\b([a-z]{2,4})(\d{3,4})\b',
                  lambda m: '. '.join(list(m.group(1))) + '. ' + m.group(2), text)
    text = re.sub(r'\b([a-z]{2,4})\s+(\d{3,4})\b',
                  lambda m: '. '.join(list(m.group(1))) + '. ' + m.group(2), text)

    ones = {'1':'one','2':'two','3':'three','4':'four','5':'five',
            '6':'six','7':'seven','8':'eight','9':'nine','0':'zero'}
    text = re.sub(r'\b(\d)s\b', lambda m: ones.get(m.group(1), m.group(1)) + 's', text)
    return text

# ---------------- Load model ----------------
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}", flush=True)

model = ChatterboxTurboTTS.from_pretrained(device=device)

JARVIS_WAV = r"C:\Users\hama2\OneDrive\Desktop\tts\jarvis-intro-1.wav"
SPEED_FACTOR = 1.0  # adjust if needed

print("READY (Jarvis voice cloned)", flush=True)

# ---------------- Main loop ----------------
for line in sys.stdin:
    text = line.strip()
    if not text:
        continue
    text = normalize(text)

    wav = model.generate(
        text,
        audio_prompt_path=JARVIS_WAV,
        cfg_weight=0.3
    )

    wav_numpy = wav.squeeze().cpu().numpy()

    # Speed adjustment
    if SPEED_FACTOR != 1.0:
        new_len = int(len(wav_numpy) / SPEED_FACTOR)
        wav_numpy = signal.resample(wav_numpy, new_len)

    torchaudio.save(
        "tts_out.wav",
        torch.tensor(wav_numpy).unsqueeze(0),
        model.sr
    )

    print("DONE", flush=True)