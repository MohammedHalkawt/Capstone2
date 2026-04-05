import sys
import os
from google import genai
from dotenv import load_dotenv
from google.genai import types

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env file")

client = genai.Client(api_key=api_key)
PDF_DIR = os.path.dirname(__file__)

SYSTEM_PROMPT = """You are a university advisor AI — think JARVIS from Iron Man. Calm, composed, subtly witty, never over-eager.
You have been provided with the university's academic calendar and course catalog. Use them to answer student questions accurately.

Rules:
- 1 sentence max, always
- Always assume the student is an undergraduate unless stated otherwise
- Never reference graduate or MBA programs unless explicitly asked
- No filler phrases like "Great question!", "Of course!", or "Certainly!"
- No sign-offs or closing lines after every message
- Dry humor is welcome but rare and short
- Be direct and precise — give the answer, not a lecture
- Only state course codes that appear in the provided documents
- If more detail is needed beyond 1 sentence, tell them to visit the registrar
- If the answer is not in the documents, say so briefly and suggest they contact the registrar
- small talk and jokes can happen and not everything is about the accademics"""

UNI_KEYWORDS = [
    "course", "class", "semester", "credit", "grade", "register",
    "minor", "major", "professor", "deadline", "graduation", "gpa",
    "schedule", "catalog", "prerequisite", "department", "exam",
    "tuition", "fee", "advisor", "degree", "curriculum", "syllabus",
    "enrollment", "transcript", "auis", "university", "college",
    "internship", "capstone", "thesis", "elective", "required"
]


print("Uploading university documents...", flush=True)

file_calendar = client.files.upload(
    file=os.path.join(PDF_DIR, "25-26Calendar.pdf"),
    config={"mime_type": "application/pdf"}
)

file_catalog = client.files.upload(
    file=os.path.join(PDF_DIR, "2026catalog.pdf"),
    config={"mime_type": "application/pdf"}
)

print("Documents uploaded.", flush=True)
print("READY", flush=True)

def needs_pdf(text):
    text_lower = text.lower()
    if any(kw in text_lower for kw in UNI_KEYWORDS):
        return True
    check = client.models.generate_content(
        model="models/gemini-3.1-flash-lite-preview",
        contents=[{
            "role": "user",
            "parts": [{"text": f"Is this question about university, academics, courses, or student life? Answer only yes or no:\n{text}"}]
        }]
    )
    return check.text.strip().lower().startswith("yes")

history = []

for line in sys.stdin:
    text = line.strip()
    if not text:
        continue

    history.append(types.Content(role="user", parts=[types.Part(text=text)]))

    if needs_pdf(text):
        contents = [
            types.Content(role="user", parts=[
                types.Part.from_uri(file_uri=file_calendar.uri, mime_type="application/pdf"),
                types.Part.from_uri(file_uri=file_catalog.uri, mime_type="application/pdf"),
            ]),
            *history,
        ]
    else:
        contents = [*history]

    response = client.models.generate_content(
        model="models/gemini-3.1-flash-lite-preview",
        contents=contents,
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT)
    )

    reply = response.text.strip()
    history.append(types.Content(role="model", parts=[types.Part(text=reply)]))
    print(f"REPLY:{reply}", flush=True)