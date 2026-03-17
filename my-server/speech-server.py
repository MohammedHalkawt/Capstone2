import sys
import json
from vosk import Model, KaldiRecognizer

MODEL_PATH = r"C:\Users\hama2\OneDrive\Documents\GitHub\Capstone2\SpeechToText\vosk-model-small-en-us-0.15"
SAMPLE_RATE = 16000
CHUNK_SIZE = 4000

model = Model(MODEL_PATH)
recognizer = KaldiRecognizer(model, SAMPLE_RATE)

print("READY", flush=True)

while True:
    data = sys.stdin.buffer.read(CHUNK_SIZE)
    if not data:
        break

    if recognizer.AcceptWaveform(data):
        result = json.loads(recognizer.Result())
        text = result.get("text", "")
        if text:
            print("FINAL:", text, flush=True)

# Print anything remaining in the buffer
final = json.loads(recognizer.FinalResult())
text = final.get("text", "")
if text:
    print("FINAL:", text, flush=True)