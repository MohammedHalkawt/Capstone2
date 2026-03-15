from TTS.api import TTS
import torch

# Load XTTS v2 — downloads model on first run (~1.8GB)
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
tts.to("cuda" if torch.cuda.is_available() else "cpu")

# Your reference WAV — just 3-6 seconds of the voice you want to clone
REFERENCE_VOICE = "jarvis-intro-1.wav"  # your target voice file

def synthesize(text: str, out_path: str = "output.wav"):
    tts.tts_to_file(
        text=text,
        speaker_wav=REFERENCE_VOICE,   # ← this is the cloning part
        language="en",
        file_path=out_path
    )

synthesize("All systems are online. How may I assist you today?")