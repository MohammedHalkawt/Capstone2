import re
import sys
import wave
import os
from piper import PiperVoice

VOICE_PATH = "C:/Users/hama2/OneDrive/Documents/GitHub/Capstone2/TextToSpeech/en_US-hfc_male-medium.onnx"

ROMAN = {
    'viii': 'eight', 'vii': 'seven', 'vi': 'six',
    'iv': 'four', 'iii': 'three', 'ii': 'two', 'ix': 'nine',
    'v': 'five', 'x': 'ten'
}

def normalize(text):
    # 1. PRE-PROCESSING: Handle Acronyms (Before lowercasing)
    
    # Create a set of uppercase Roman numerals to check against
    roman_upper = set(k.upper() for k in ROMAN.keys())

    def expand_acronyms(match):
        acronym = match.group(1)
        # If it is a Roman Numeral (e.g., "II", "IV"), leave it alone so the 
        # lowercasing logic below can handle it correctly.
        if acronym in roman_upper:
            return acronym
        # Otherwise, it's an acronym (like "SE", "CS"), spell it out.
        return '. '.join(list(acronym)) + '.'

    # Regex breakdown:
    # \b            : Word boundary
    # ([A-Z]{2,5})  : Match 2 to 5 Uppercase letters (The Acronym)
    # \b            : Word boundary (ensures it's a standalone word)
    # (?! \d{3,4})  : Negative Lookahead - Ensure it is NOT followed by a space and 3-4 digits.
    #                 (We leave "SE 491" alone so your existing logic handles it later)
    text = re.sub(r'\b([A-Z]{2,5})\b(?! \d{3,4})', expand_acronyms, text)

    # 2. Lowercase the text
    text = text.lower()

    # 3. Handle Roman Numerals (Your original logic)
    for roman, word in ROMAN.items():
        text = re.sub(r'\b' + roman.lower() + r'\b', word, text)

    # 4. Handle Codes like "CS101" or "CS 101" (Your original logic)
    # This now works because "SE 491" was skipped in step 1, became "se 491",
    # and is now correctly expanded here.
    text = re.sub(r'\b([a-z]{2,4})(\d{3,4})\b', lambda m: '. '.join(list(m.group(1))) + '. ' + m.group(2), text)
    text = re.sub(r'\b([a-z]{2,4})\s+(\d{3,4})\b', lambda m: '. '.join(list(m.group(1))) + '. ' + m.group(2), text)
    
    # 5. Handle plural digits like "3s" (Your original logic)
    ones = {'1':'one','2':'two','3':'three','4':'four','5':'five',
            '6':'six','7':'seven','8':'eight','9':'nine','0':'zero'}
    text = re.sub(r'\b(\d)s\b', lambda m: ones.get(m.group(1), m.group(1)) + 's', text)
    
    return text

print("Loading TextToSpeech...", flush=True)
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