import warnings
warnings.filterwarnings("ignore")

import sys
import re
import torch
import torchaudio
from chatterbox.tts_turbo import ChatterboxTurboTTS

# ---------------- Normalization ----------------
ROMAN = {
    'viii': 'eight', 'vii': 'seven', 'vi': 'six',
    'iv': 'four', 'iii': 'three', 'ii': 'two', 'ix': 'nine',
    'v': 'five', 'x': 'ten'
}

ones = {
    '1':'one','2':'two','3':'three','4':'four','5':'five',
    '6':'six','7':'seven','8':'eight','9':'nine','0':'zero'
}

def normalize(text):
    roman_upper = set(k.upper() for k in ROMAN.keys())

    def expand_acronyms(match):
        acronym = match.group(1)
        if acronym in roman_upper:
            return acronym
        return ' '.join(list(acronym))

    text = re.sub(r'\b([A-Z]{2,5})\b', expand_acronyms, text)
    text = text.lower()
    text = text.replace(':', ',')
    text = text.replace(';', ',')

    for roman, word in ROMAN.items():
        text = re.sub(r'\b' + roman.lower() + r'\b', word, text)

    # Read 3-4 digit numbers digit by digit (e.g. 491 -> "four nine one")
    text = re.sub(r'\b(\d{3,4})\b',
                  lambda m: ' '.join(ones.get(d, d) for d in m.group(0)), text)

    # Single digit followed by s (e.g. 3s -> threes)
    text = re.sub(r'\b(\d)s\b', lambda m: ones.get(m.group(1), m.group(1)) + 's', text)

    return text

# ---------------- Load model ----------------
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}", flush=True)

model = ChatterboxTurboTTS.from_pretrained(device=device)

JARVIS_WAV = r"C:\Users\hama2\OneDrive\Desktop\tts\jarvis-intro-1.wav"

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
        top_k=200,
        temperature=0.8
    )

    wav_numpy = wav.squeeze().cpu().numpy()

    torchaudio.save(
        "tts_out.wav",
        torch.tensor(wav_numpy).unsqueeze(0),
        model.sr
    )

    print("DONE", flush=True)