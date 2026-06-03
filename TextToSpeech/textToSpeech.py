import re
import sys
import wave
import torch
from TTS.api import TTS

# ---------------- Normalization (from your Piper script) ----------------
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

# ---------------- Coqui XTTS with Jarvis clone ----------------
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}", flush=True)

# Load XTTS v2 (this model can clone voices)
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)

# Your Jarvis reference audio (make sure the path is correct)
JARVIS_WAV = r"C:\Users\hama2\OneDrive\Desktop\tts\jarvis-intro-1.wav"

print("READY (Jarvis voice cloned)", flush=True)

# Process stdin line by line, exactly like the Piper script
for line in sys.stdin:
    text = line.strip()
    if not text:
        continue
    text = normalize(text)   # reuse your normalizer

    # Synthesize using the cloned voice
    wav_numpy = tts.tts(
        text=text,
        speaker_wav=JARVIS_WAV,
        language="en"
    )

    # Write to a WAV file (16 kHz mono, float32 -> int16)
    with wave.open("tts_out.wav", "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)          # 16‑bit
        wf.setframerate(24000)      # XTTS v2 uses 24 kHz by default
        # Convert float32 array (-1..1) to int16
        int16_data = (wav_numpy * 32767).astype(np.int16).tobytes()
        wf.writeframes(int16_data)

    print("DONE", flush=True)