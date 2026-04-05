import os
import re
import warnings
warnings.filterwarnings("ignore")

import sys
import wave
from piper import PiperVoice

VOICE_PATH = os.path.join(os.path.dirname(__file__), "en_GB-alan-medium.onnx")

ROMAN = {
    'viii': 'eight', 'vii': 'seven', 'vi': 'six',
    'iv': 'four', 'iii': 'three', 'ii': 'two', 'ix': 'nine',
    'v': 'five', 'x': 'ten'
}

def normalize(text):
    # lowercase first so Piper reads "I" as "i" not "1"
    text = text.lower()

    # roman numerals
    for roman, word in ROMAN.items():
        text = re.sub(r'\b' + roman.lower() + r'\b', word, text)
    
    # course codes like swe402 -> s w e 402
    text = re.sub(r'\b([a-z]{2,4})(\d{3,4})\b', lambda m: ' '.join(m.group(1)) + ' ' + m.group(2), text)

    # convert "1s" -> "ones" etc
    ones = {'1':'one','2':'two','3':'three','4':'four','5':'five',
            '6':'six','7':'seven','8':'eight','9':'nine','0':'zero'}
    text = re.sub(r'\b(\d)s\b', lambda m: ones.get(m.group(1), m.group(1)) + 's', text)

    return text


print("Loading Piper model...", flush=True)
voice = PiperVoice.load(VOICE_PATH)
print("READY", flush=True)

for line in sys.stdin:
    text = line.strip()
    if not text:
        continue

    text = normalize(text)

    with wave.open("tts_out.wav", "wb") as wf:
        voice.synthesize_wav(text, wf)

    print("DONE", flush=True)