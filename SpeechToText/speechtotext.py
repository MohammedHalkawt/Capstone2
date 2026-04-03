import whisper
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import tempfile
import os

# ----------------------------
# SETTINGS
# ----------------------------

SAMPLE_RATE = 16000
DURATION = 10  # seconds to record, change as needed

# ----------------------------
# LOAD MODEL
# ----------------------------

print("Loading Whisper model... (first time takes a minute)")
model = whisper.load_model("medium").to("cuda")

print("Model ready.\n")
print(f"Model running on: {next(model.parameters()).device}")
# should print: cuda
# ----------------------------
# RECORD FROM MIC
# ----------------------------

def record_audio(duration=DURATION, sample_rate=SAMPLE_RATE):
    print(f"🎤 Recording for {duration} seconds... Speak now!")
    audio = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype="int16"
    )
    sd.wait()  # wait until recording is done
    print("Recording done.\n")
    return audio

# ----------------------------
# TRANSCRIBE
# ----------------------------

def transcribe(audio, sample_rate=SAMPLE_RATE):
    # save to a temp wav file (whisper needs a file)
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp_path = tmp.name
    tmp.close()  # ← close handle BEFORE writing, so Windows doesn't lock it

    wav.write(tmp_path, sample_rate, audio)

    result = model.transcribe(
        tmp_path,
        language="en",
        initial_prompt="The speaker is a university student from Iraq. They may use numbers like 1, 2, 3, 4 and abbreviations like uni, CS, AI, GPA, prof."
    )

    try:
        os.unlink(tmp_path)  # delete temp file after whisper is done
    except PermissionError:
        pass  # if it still fails, not a big deal, OS will clean it up

    return result["text"].strip()

# ----------------------------
# MAIN LOOP
# ----------------------------

print("Press Enter to start recording, Ctrl+C to quit.\n")

while True:
    input("[ Press Enter to speak ]")
    audio = record_audio()
    text = transcribe(audio)
    print(f"You said: {text}\n")